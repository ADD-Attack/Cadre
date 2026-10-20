"""Tests for GET /v1/screen/hash and the /v1/screen ETag (wishlist #14).

Runs anywhere with the gateway's deps installed — no live hands needed:
the screenshot fetch is stubbed with synthetic PNGs.

    python3 test_screen_hash.py

Covers: token auth still enforced; the hash ignores changes inside the
masked bottom strip; the hash changes when persistent content changes;
stable mode ignores a blinking-caret-sized transient; /v1/screen serves
an ETag and answers a matching If-None-Match with 304.
"""

import os
import sys
from io import BytesIO

os.environ.setdefault("RELAY_GATEWAY_TOKEN", "test-token")
os.environ.setdefault("HANDS_SECRET", "test-secret")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app as gateway  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

TOKEN = {"X-Relay-Token": "test-token"}
W, H = 120, 100  # synthetic frame; mask_bottom=10 in tests -> 90 rows hashed


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


def with_masked_change(d):
    # Change confined to the bottom 10 rows (inside the mask).
    d.rectangle([0, H - 10, W - 1, H - 1], fill=(250, 250, 250))


def with_caret(d):
    # A 4x4 bright block above the mask — one phase of a blinking caret.
    d.rectangle([60, 20, 63, 23], fill=(255, 255, 255))


class Stub:
    """Serves queued PNGs through the gateway's fetch helper."""

    def __init__(self, frames):
        self.frames = list(frames)

    def __call__(self):
        frame = self.frames.pop(0) if len(self.frames) > 1 else self.frames[0]
        return frame, "image/png", None


def run():
    client = gateway.app.test_client()
    failures = []

    def check(name, cond):
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    def get_hash(frames, query="mask_bottom=10", headers=TOKEN):
        gateway._fetch_screenshot = Stub(frames)
        return client.get(f"/v1/screen/hash?{query}", headers=headers)

    # Auth: no token -> 401 (the gate covers the new route too).
    r = get_hash([png(base)], headers={})
    check("hash endpoint requires the gateway token", r.status_code == 401)

    # Basic shape.
    r = get_hash([png(base)])
    body = r.get_json()
    check("hash returns ok + 64-hex digest",
          r.status_code == 200 and body["ok"] and len(body["hash"]) == 64)
    h_base = body["hash"]

    # A change inside the masked strip must not move the hash.
    r = get_hash([png(with_masked_change)])
    check("masked-strip change is ignored", r.get_json()["hash"] == h_base)

    # Persistent content above the mask must move it.
    r = get_hash([png(with_block)])
    check("content change moves the hash", r.get_json()["hash"] != h_base)
    h_block = r.get_json()["hash"]

    # Without stable mode a caret blink DOES move the hash (documents
    # why stable mode exists).
    r = get_hash([png(with_caret)])
    check("unstable hash sees a caret blink", r.get_json()["hash"] != h_base)

    # Stable mode: blink in only one of the two samples is composited
    # away; the same pair in the other phase order agrees.
    r1 = get_hash([png(base), png(with_caret)], query="mask_bottom=10&stable=1")
    r2 = get_hash([png(with_caret), png(base)], query="mask_bottom=10&stable=1")
    check("stable hash ignores a caret blink",
          r1.get_json()["hash"] == r2.get_json()["hash"])
    check("stable hash of blank pair equals plain hash",
          r1.get_json()["hash"] == h_base)

    # Stable mode still sees persistent content.
    r = get_hash([png(with_block), png(with_block)], query="mask_bottom=10&stable=1")
    check("stable hash sees persistent content", r.get_json()["hash"] == h_block)

    # /v1/screen: ETag present, and If-None-Match short-circuits.
    gateway._fetch_screenshot = Stub([png(base)])
    r = client.get("/v1/screen", headers=TOKEN)
    etag = r.headers.get("ETag")
    check("screen serves an ETag", r.status_code == 200 and bool(etag))
    r = client.get("/v1/screen", headers={**TOKEN, "If-None-Match": etag})
    check("matching If-None-Match gets 304 with no body",
          r.status_code == 304 and len(r.get_data()) == 0)
    r = client.get("/v1/screen", headers={**TOKEN, "If-None-Match": '"deadbeef"'})
    check("stale If-None-Match gets the full frame", r.status_code == 200)

    print("FAILED: " + ", ".join(failures) if failures else "ALL PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
