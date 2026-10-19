"""Tests for P3: POST /v1/filedrop, POST /v1/wait, /v1/info pc_state.

Runs anywhere with the gateway's deps installed — no live hands needed:
the hands post-call seam is faked in memory, screenshot fetches are
scripted, and requests.get is stubbed for the parser and /state probes.

    python3 test_services.py

Covers: filedrop chunking for >256KB payloads, sha forward/verify, hands
errors surfacing; wait-for hash/region change held, no-change timeout,
window titles (unsupported + held), parser model-loaded sequencing,
unknown condition type 400; /v1/info pc_state present and null when the
hands is down.
"""

import base64
import hashlib
import os
import sys
import time
from io import BytesIO

os.environ.setdefault("RELAY_GATEWAY_TOKEN", "test-token")
os.environ.setdefault("HANDS_SECRET", "test-secret")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app as gateway  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

TOKEN = {"X-Relay-Token": "test-token"}
W, H = 120, 100


def png(draw_fn):
    img = Image.new("RGB", (W, H), (24, 24, 32))
    draw_fn(ImageDraw.Draw(img))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def base(_d):
    pass


def with_block(_d):
    _d.rectangle([10, 10, 40, 40], fill=(200, 60, 60))


class Stub:
    """Serves queued PNGs through _fetch_screenshot's (png, ctype, err) shape."""

    def __init__(self, frames):
        self.frames = list(frames)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if len(self.frames) > 1:
            return self.frames.pop(0), "image/png", None
        return self.frames[0], "image/png", None


class FakeHands:
    """Fake the hands filedrop begin/chunk/commit in memory.

    Implements the `post` callable seam: post(path, payload) -> (status, dict).
    """

    def __init__(self):
        self.uploads = {}
        self.chunk_calls = []
        self.begin_calls = []
        self.fail_begin = None  # (status, body) to fail begin with

    def __call__(self, path, payload):
        if path == "/filedrop/begin":
            if self.fail_begin is not None:
                return self.fail_begin
            uid = f"upload-{len(self.uploads)}"
            self.uploads[uid] = {
                "folder": payload["folder"],
                "filename": payload["filename"],
                "size": payload["size"],
                "sha256": payload["sha256"],
                "buffer": bytearray(),
            }
            self.begin_calls.append(payload)
            return 200, {"ok": True, "upload_id": uid, "chunk_max": 524288}
        if path == "/filedrop/chunk":
            uid = payload["upload_id"]
            if uid not in self.uploads:
                return 404, {"ok": False, "error": "unknown upload_id"}
            up = self.uploads[uid]
            if payload["offset"] != len(up["buffer"]):
                return 409, {
                    "ok": False,
                    "error": "offset mismatch",
                    "expected_offset": len(up["buffer"]),
                }
            chunk = base64.b64decode(payload["data_b64"], validate=True)
            up["buffer"].extend(chunk)
            self.chunk_calls.append(len(chunk))
            return 200, {"ok": True, "received": len(up["buffer"])}
        if path == "/filedrop/commit":
            uid = payload["upload_id"]
            if uid not in self.uploads:
                return 404, {"ok": False, "error": "unknown upload_id"}
            up = self.uploads[uid]
            if len(up["buffer"]) != up["size"]:
                return 400, {"ok": False, "error": "incomplete upload"}
            digest = hashlib.sha256(bytes(up["buffer"])).hexdigest()
            if digest != up["sha256"]:
                del self.uploads[uid]
                return 400, {"ok": False, "error": "sha256 mismatch"}
            path_out = f"/hands/{up['folder']}/{up['filename']}"
            del self.uploads[uid]
            return 200, {"ok": True, "path": path_out, "size": up["size"], "sha256": digest}
        raise AssertionError(path)


def fake_wait_response(frames):
    def _get(url, **kw):
        raise AssertionError("requests.get should not be called here")
    return _get


def run():
    client = gateway.app.test_client()
    failures = []

    def check(name, cond):
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    # ---------------- filedrop ----------------
    data = bytes(range(256)) * 2344  # 600_064 bytes, > 256KB -> 3 chunks
    assert len(data) > 256 * 1024
    sha = hashlib.sha256(data).hexdigest()

    fake = FakeHands()
    body, status = gateway._filedrop_via_hands("/Drop", "big.bin", data, sha, post=fake)
    check("filedrop helper: multi-chunk payload commits ok", status == 200 and body["ok"])
    check("filedrop helper: chunking happened for >256KB payload",
          len(fake.chunk_calls) >= 3 and all(c <= 256 * 1024 for c in fake.chunk_calls))
    check("filedrop helper: total chunk bytes equal payload",
          sum(fake.chunk_calls) == len(data))
    check("filedrop helper: sha forwarded to hands begin",
          fake.begin_calls and fake.begin_calls[0]["sha256"] == sha)
    check("filedrop helper: commit returned path/size/sha",
          body.get("path") and body["size"] == len(data) and body["sha256"] == sha)

    # Route through Flask: the helper seam is gateway._hands_post, which
    # tests can replace exactly like test_screen_hash stubs _fetch_screenshot.
    original_post = gateway._hands_post
    try:
        fake = FakeHands()
        gateway._hands_post = fake
        r = client.post(
            "/v1/filedrop",
            json={
                "folder": "D:\\Drops",
                "filename": "big.bin",
                "data_b64": base64.b64encode(data).decode("ascii"),
            },
            headers=TOKEN,
        )
        body = r.get_json()
        check("v1/filedrop route: one-shot succeeds", r.status_code == 200 and body["ok"])
        check("v1/filedrop route: sha forwarded from route", body["sha256"] == sha)
        check("v1/filedrop route: chunked through the fake hands",
              len(fake.chunk_calls) >= 3)

        # Supplied-but-wrong sha is rejected before touching the hands.
        fake = FakeHands()
        gateway._hands_post = fake
        r = client.post(
            "/v1/filedrop",
            json={
                "folder": "D:\\Drops",
                "filename": "small.bin",
                "data_b64": base64.b64encode(b"x").decode("ascii"),
                "sha256": "0" * 64,
            },
            headers=TOKEN,
        )
        check("v1/filedrop: supplied sha mismatch -> 400",
              r.status_code == 400 and r.get_json()["ok"] is False)
        check("v1/filedrop: sha mismatch sent nothing to hands",
              not fake.begin_calls)

        # Hands errors surface with their status.
        fake = FakeHands()
        fake.fail_begin = (403, {"ok": False, "error": "folder not in file-drop allowlist"})
        gateway._hands_post = fake
        r = client.post(
            "/v1/filedrop",
            json={
                "folder": "C:\\Nope",
                "filename": "a.bin",
                "data_b64": base64.b64encode(b"abc").decode("ascii"),
            },
            headers=TOKEN,
        )
        check("v1/filedrop: hands error surfaces with its status",
              r.status_code == 403 and r.get_json()["error"] == "folder not in file-drop allowlist")

        # Auth still enforced.
        r = client.post("/v1/filedrop", json={}, headers={})
        check("v1/filedrop requires the gateway token", r.status_code == 401)
    finally:
        gateway._hands_post = original_post

    # ---------------- wait-for: screen_hash_change ----------------
    gateway._fetch_screenshot = Stub([png(base), png(base), png(with_block)])
    r = client.post(
        "/v1/wait",
        json={"condition": {"type": "screen_hash_change"}, "timeout_seconds": 5, "poll_seconds": 0.2},
        headers=TOKEN,
    )
    body = r.get_json()
    check("wait hash-change: held on third poll (A, A, B)",
          r.status_code == 200 and body["ok"] and body["held"] is True
          and body["condition"] == {"type": "screen_hash_change"})

    gateway._fetch_screenshot = Stub([png(base)] * 40)
    t0 = time.monotonic()
    r = client.post(
        "/v1/wait",
        json={"condition": {"type": "screen_hash_change"}, "timeout_seconds": 1, "poll_seconds": 0.2},
        headers=TOKEN,
    )
    elapsed = time.monotonic() - t0
    body = r.get_json()
    check("wait no-change: timeout, held=false",
          r.status_code == 200 and body["held"] is False and body.get("timeout") is True)
    check("wait no-change: waited_seconds near timeout", 1.0 <= body["waited_seconds"] <= 3.0
          and elapsed >= 0.9)

    # Region change: masked to the block's area.
    gateway._fetch_screenshot = Stub([png(base), png(base), png(with_block)])
    r = client.post(
        "/v1/wait",
        json={
            "condition": {"type": "screen_region_change", "region": [0, 0, 60, 60]},
            "timeout_seconds": 5,
            "poll_seconds": 0.2,
        },
        headers=TOKEN,
    )
    body = r.get_json()
    check("wait region-change: held when region pixels move", body["held"] is True)

    # Region change confined OUTSIDE the region is not held (short timeout).
    gateway._fetch_screenshot = Stub([png(base), png(with_block)])
    r = client.post(
        "/v1/wait",
        json={
            "condition": {"type": "screen_region_change", "region": [70, 70, 40, 20]},
            "timeout_seconds": 1,
            "poll_seconds": 0.2,
        },
        headers=TOKEN,
    )
    check("wait region-change: change outside region times out",
          r.get_json()["held"] is False)

    # Unknown type -> 400 immediately.
    t0 = time.monotonic()
    r = client.post(
        "/v1/wait", json={"condition": {"type": "nope"}, "timeout_seconds": 5}, headers=TOKEN
    )
    check("wait unknown condition type -> 400",
          r.status_code == 400 and (time.monotonic() - t0) < 1.0)

    # window_title: hands 404 -> immediate unsupported, don't burn timeout.
    original_fetch_titles = gateway._fetch_window_titles
    try:
        gateway._fetch_window_titles = lambda: (None, 404)
        t0 = time.monotonic()
        r = client.post(
            "/v1/wait",
            json={"condition": {"type": "window_title", "contains": "Editor"},
                  "timeout_seconds": 10, "poll_seconds": 0.2},
            headers=TOKEN,
        )
        body = r.get_json()
        check("wait window_title: hands 404 -> immediate unsupported",
              body["ok"] is False and "window titles" in body["error"]
              and (time.monotonic() - t0) < 1.0)

        # Scripted titles: held when a matching title appears.
        seq = [[], ["Desktop"], ["Untitled - Editor"]]
        gateway._fetch_window_titles = lambda: (seq.pop(0) if len(seq) > 1 else seq[0], 200)
        r = client.post(
            "/v1/wait",
            json={"condition": {"type": "window_title", "contains": "Editor"},
                  "timeout_seconds": 5, "poll_seconds": 0.2},
            headers=TOKEN,
        )
        check("wait window_title: held when a title contains the text",
              r.get_json()["held"] is True)
    finally:
        gateway._fetch_window_titles = original_fetch_titles

    # parser_model_loaded: scripted requests.get -> False, False, True.
    original_get = gateway.requests.get
    try:
        seq = [False, False, True]

        class _Resp:
            status_code = 200

            def __init__(self, loaded):
                self._loaded = loaded

            def json(self):
                return {"ok": True, "model_loaded": self._loaded}

        def fake_get(url, **kw):
            assert "/health" in url
            return _Resp(seq.pop(0) if len(seq) > 1 else seq[0])

        gateway.requests.get = fake_get
        r = client.post(
            "/v1/wait",
            json={"condition": {"type": "parser_model_loaded"},
                  "timeout_seconds": 5, "poll_seconds": 0.2},
            headers=TOKEN,
        )
        check("wait parser_model_loaded: held when health flips true",
              r.get_json()["held"] is True)
    finally:
        gateway.requests.get = original_get

    # ---------------- /v1/info pc_state ----------------
    original_probe = gateway._probe
    original_fetch_state = gateway._fetch_pc_state
    try:
        gateway._probe = lambda url, headers=None: True
        gateway._fetch_pc_state = lambda: {
            "ok": True, "platform": "windows", "locked": True, "idle_seconds": 42.0
        }
        gateway._probe_cache.update({"hands": None, "parser": None, "pc_state": None, "at": 0.0})
        r = client.get("/v1/info", headers=TOKEN)
        body = r.get_json()
        check("v1/info includes pc_state from the hands probe",
              body["pc_state"] is not None and body["pc_state"]["locked"] is True
              and body["pc_state"]["idle_seconds"] == 42.0)
        check("v1/info existing fields unchanged",
              body["hands_reachable"] is True and body["parser_reachable"] is True
              and "hands_url" in body and "parser_url" in body)

        # Hands down -> pc_state null.
        gateway._probe = lambda url, headers=None: False
        gateway._fetch_pc_state = lambda: {"ok": True, "platform": "windows"}
        gateway._probe_cache.update({"hands": None, "parser": None, "pc_state": None, "at": 0.0})
        r = client.get("/v1/info", headers=TOKEN)
        body = r.get_json()
        check("v1/info: pc_state null when hands down",
              body["hands_reachable"] is False and body["pc_state"] is None)
    finally:
        gateway._probe = original_probe
        gateway._fetch_pc_state = original_fetch_state
        gateway._probe_cache.update({"hands": None, "parser": None, "pc_state": None, "at": 0.0})

    print("FAILED: " + ", ".join(failures) if failures else "ALL PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
