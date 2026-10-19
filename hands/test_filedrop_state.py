"""Tests for hands P3: POST /filedrop/*, GET /state, GET /window_titles.

Runs anywhere: fake pyautogui/tkinter modules are injected into
sys.modules BEFORE the hands module is loaded from its file path, so no
Windows desktop (or display) is needed. The Windows lock probe is
monkeypatched — the honest surface here is validation, hashing, state
machines, and allowlists.

    python3 test_filedrop_state.py

Note: importing the hands module may create muse_relay_config.json next
to it (its per-launch alert-topic config). This test deletes that file
afterwards when it did not exist before the run; never commit it.
"""

import base64
import hashlib
import importlib.util
import os
import shutil
import sys
import tempfile
import types

HANDS_DIR = os.path.dirname(os.path.abspath(__file__))
HANDS_PATH = os.path.join(HANDS_DIR, "muse_relay_hands.py")
CONFIG_PATH = os.path.join(HANDS_DIR, "muse_relay_config.json")
CONFIG_EXISTED_BEFORE = os.path.exists(CONFIG_PATH)
LOG_PATH = os.path.join(HANDS_DIR, "muse_relay.log")
LOG_EXISTED_BEFORE = os.path.exists(LOG_PATH)


def _fake_pyautogui():
    mod = types.ModuleType("pyautogui")
    mod.FAILSAFE = False
    mod.PAUSE = 0
    mod.getAllTitles = lambda: ["Alpha Window", "Beta - Editor"]
    mod.screenshot = lambda: None
    mod.moveTo = lambda *a, **k: None
    mod.click = lambda *a, **k: None
    mod.write = lambda *a, **k: None
    mod.press = lambda *a, **k: None
    mod.scroll = lambda *a, **k: None
    return mod


def _fake_tkinter():
    mod = types.ModuleType("tkinter")

    class _Widget:
        def __init__(self, *a, **k):
            pass

        def grid(self, *a, **k):
            pass

    class Tk(_Widget):
        pass

    class StringVar:
        def __init__(self, *a, **k):
            self._v = k.get("value", "")

        def get(self):
            return self._v

        def set(self, v):
            self._v = v

    mod.Tk = Tk
    mod.StringVar = StringVar
    mod.Label = _Widget
    mod.Entry = _Widget
    mod.Button = _Widget
    mod.Text = _Widget
    return mod


def _load_hands():
    sys.modules["pyautogui"] = _fake_pyautogui()
    sys.modules["tkinter"] = _fake_tkinter()
    spec = importlib.util.spec_from_file_location("muse_relay_hands_under_test", HANDS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run():
    failures = []

    def check(name, cond):
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    hands = _load_hands()
    drop_dir = tempfile.mkdtemp(prefix="filedrop-allowed-")
    outside_dir = tempfile.mkdtemp(prefix="filedrop-outside-")
    try:
        client = hands.app.test_client()
        secret = {"X-Secret": hands.SHARED_SECRET}

        def post(path, payload):
            return client.post(path, json=payload, headers=secret)

        def begin(folder, filename, data, sha=None):
            return post(
                "/filedrop/begin",
                {
                    "folder": folder,
                    "filename": filename,
                    "size": len(data),
                    "sha256": sha if sha is not None else hashlib.sha256(data).hexdigest(),
                },
            )

        # ---- /state shape, monkeypatched probe ----
        hands._probe_lock_state = lambda: (True, 42)
        r = client.get("/state", headers=secret)
        body = r.get_json()
        check("/state returns the documented shape",
              r.status_code == 200 and body["ok"] is True
              and body["platform"] in ("windows", "other")
              and body["locked"] is True and body["idle_seconds"] == 42)
        hands._probe_lock_state = lambda: (None, None)
        body = client.get("/state", headers=secret).get_json()
        check("/state passes through None probe values without a 500",
              body["locked"] is None and body["idle_seconds"] is None)

        # ---- /window_titles ----
        r = client.get("/window_titles", headers=secret)
        check("/window_titles returns the (fake) titles",
              r.status_code == 200 and r.get_json()["titles"] == ["Alpha Window", "Beta - Editor"])

        # ---- filedrop is 501 when unconfigured ----
        os.environ.pop("HANDS_FILEDROP_DIRS", None)
        # The config file created at import carries no filedrop_dirs key.
        r = begin(drop_dir, "x.bin", b"abc")
        check("unconfigured filedrop begin -> 501",
              r.status_code == 501 and r.get_json()["ok"] is False)
        r = post("/filedrop/abort", {"upload_id": "whatever"})
        check("unconfigured filedrop abort -> 501", r.status_code == 501)

        # Configure the allowlist via env pointing at a tmp dir.
        os.environ["HANDS_FILEDROP_DIRS"] = drop_dir

        # ---- begin validation ----
        data = b"hello file-drop world" * 10
        r = begin(outside_dir, "x.bin", data)
        check("begin rejects a folder outside the allowlist",
              r.status_code == 403 and r.get_json()["ok"] is False)
        r = begin(drop_dir, "../evil", data)
        check("begin rejects filename '../evil'", r.status_code == 400)
        r = begin(drop_dir, "a/b", data)
        check("begin rejects filename 'a/b'", r.status_code == 400)
        r = begin(drop_dir, "a\\b", data)
        check("begin rejects filename with a backslash", r.status_code == 400)
        r = begin(drop_dir, "", data)
        check("begin rejects an empty filename", r.status_code == 400)
        r = post("/filedrop/begin",
                 {"folder": drop_dir, "filename": "x.bin", "size": 0,
                  "sha256": hashlib.sha256(b"").hexdigest()})
        check("begin rejects size 0", r.status_code == 400)
        r = post("/filedrop/begin",
                 {"folder": drop_dir, "filename": "x.bin", "size": 10,
                  "sha256": "not-hex"})
        check("begin rejects a non-64-hex sha256", r.status_code == 400)

        # ---- chunk offset / unknown ids ----
        r = begin(drop_dir, "offset.bin", data)
        check("begin happy path returns upload_id + chunk_max",
              r.status_code == 200 and r.get_json()["upload_id"]
              and r.get_json()["chunk_max"] == 524288)
        uid = r.get_json()["upload_id"]
        r = post("/filedrop/chunk",
                 {"upload_id": uid, "offset": 5,
                  "data_b64": base64.b64encode(data[:5]).decode("ascii")})
        body = r.get_json()
        check("chunk with a wrong offset -> 409 with the expected offset",
              r.status_code == 409 and body["expected_offset"] == 0)
        r = post("/filedrop/chunk",
                 {"upload_id": "no-such-id", "offset": 0,
                  "data_b64": base64.b64encode(b"x").decode("ascii")})
        check("chunk with an unknown upload id -> 404", r.status_code == 404)
        r = post("/filedrop/abort", {"upload_id": "no-such-id"})
        check("abort with an unknown upload id -> 404", r.status_code == 404)
        r = post("/filedrop/abort", {"upload_id": uid})
        check("abort drops a known upload", r.status_code == 200 and r.get_json()["ok"])
        r = post("/filedrop/commit", {"upload_id": uid})
        check("commit after abort -> 404", r.status_code == 404)

        # ---- commit with the wrong sha: 400 and no file ----
        wrong_sha = hashlib.sha256(b"different bytes, same length ....").hexdigest()
        # Ensure the wrong digest differs but the size still matches data.
        assert wrong_sha != hashlib.sha256(data).hexdigest()
        r = begin(drop_dir, "badsha.bin", data, sha=wrong_sha)
        uid = r.get_json()["upload_id"]
        r = post("/filedrop/chunk",
                 {"upload_id": uid, "offset": 0,
                  "data_b64": base64.b64encode(data).decode("ascii")})
        check("chunk at the correct offset is accepted", r.status_code == 200)
        r = post("/filedrop/commit", {"upload_id": uid})
        check("commit with a wrong sha -> 400", r.status_code == 400)
        check("wrong-sha commit writes no file",
              not os.path.exists(os.path.join(drop_dir, "badsha.bin")))

        # ---- happy path: bytes on disk match ----
        r = begin(drop_dir, "good.bin", data)
        uid = r.get_json()["upload_id"]
        half = len(data) // 2
        post("/filedrop/chunk",
             {"upload_id": uid, "offset": 0,
              "data_b64": base64.b64encode(data[:half]).decode("ascii")})
        post("/filedrop/chunk",
             {"upload_id": uid, "offset": half,
              "data_b64": base64.b64encode(data[half:]).decode("ascii")})
        r = post("/filedrop/commit", {"upload_id": uid})
        body = r.get_json()
        final = os.path.join(drop_dir, "good.bin")
        check("commit happy path returns path/size/sha",
              r.status_code == 200 and body["ok"] and body["path"] == final
              and body["size"] == len(data)
              and body["sha256"] == hashlib.sha256(data).hexdigest())
        with open(final, "rb") as fh:
            on_disk = fh.read()
        check("committed file bytes on disk match", on_disk == data)

        # Auth still enforced on the new routes.
        r = client.get("/state", headers={})
        check("hands routes still require the X-Secret", r.status_code == 401)
    finally:
        os.environ.pop("HANDS_FILEDROP_DIRS", None)
        shutil.rmtree(drop_dir, ignore_errors=True)
        shutil.rmtree(outside_dir, ignore_errors=True)
        if not CONFIG_EXISTED_BEFORE and os.path.exists(CONFIG_PATH):
            os.remove(CONFIG_PATH)
        if not LOG_EXISTED_BEFORE and os.path.exists(LOG_PATH):
            os.remove(LOG_PATH)

    print("FAILED: " + ", ".join(failures) if failures else "ALL PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
