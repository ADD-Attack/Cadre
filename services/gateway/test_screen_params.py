"""Tests for the monitor/region screen params + /v1/monitors (v3 P5).

Runs anywhere with the gateway's deps installed — no live hands needed:
_fetch_screenshot is stubbed with a synthetic PNG and requests.get is
stubbed for the /v1/monitors passthrough.

    python3 test_screen_params.py

Covers: ?monitor / ?region are forwarded from /v1/screen and
/v1/screen/hash to the hands fetch; a malformed region is a 400 without
the fetch being called; a no-param call still invokes the fetch with
zero arguments (the test_screen_hash.py stubs rely on that);
/v1/monitors passes the hands reply through and maps the usual errors
(503 no secret, 502 unreachable / bad secret).
"""

import os
import sys
from io import BytesIO

os.environ.setdefault("RELAY_GATEWAY_TOKEN", "test-token")
os.environ.setdefault("HANDS_SECRET", "test-secret")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app as gateway  # noqa: E402
import requests  # noqa: E402
from PIL import Image  # noqa: E402

TOKEN = {"X-Relay-Token": "test-token"}


def make_png():
    buf = BytesIO()
    Image.new("RGB", (120, 100), (24, 24, 32)).save(buf, format="PNG")
    return buf.getvalue()


PNG = make_png()
fetch_calls = []


def recording_fetch(*args, **kwargs):
    fetch_calls.append((args, kwargs))
    return PNG, "image/png", None


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.ok = status_code < 400

    def json(self):
        return self._payload


def run():
    client = gateway.app.test_client()
    failures = []

    def check(name, cond):
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    orig_fetch = gateway._fetch_screenshot
    gateway._fetch_screenshot = recording_fetch
    try:
        fetch_calls.clear()
        r = client.get("/v1/screen?monitor=1", headers=TOKEN)
        check(
            "/v1/screen?monitor=1 forwards monitor=1",
            r.status_code == 200 and fetch_calls[-1] == ((), {"monitor": 1}),
        )

        fetch_calls.clear()
        r = client.get("/v1/screen/hash?region=1,2,3,4&mask_bottom=10", headers=TOKEN)
        check(
            "/v1/screen/hash?region=... forwards the region string",
            r.status_code == 200 and fetch_calls[-1] == ((), {"region": "1,2,3,4"}),
        )

        fetch_calls.clear()
        r = client.get("/v1/screen", headers=TOKEN)
        check(
            "/v1/screen with no params calls the fetch with zero arguments",
            r.status_code == 200 and fetch_calls[-1] == ((), {}),
        )

        fetch_calls.clear()
        r = client.get("/v1/screen?region=1,2,0,4", headers=TOKEN)
        check(
            "invalid region (w=0) -> 400, fetch never called",
            r.status_code == 400 and fetch_calls == [],
        )
        r = client.get("/v1/screen/hash?region=bad", headers=TOKEN)
        check(
            "malformed region on hash -> 400, fetch never called",
            r.status_code == 400 and fetch_calls == [],
        )
    finally:
        gateway._fetch_screenshot = orig_fetch

    # The real _fetch_screenshot validates the region before any request.
    with gateway.app.app_context():
        out = gateway._fetch_screenshot(region="1,2,0,4")
    check(
        "real _fetch_screenshot rejects a bad region with a 400 tuple",
        out[0] is None and out[2][1] == 400,
    )

    # ---- /v1/monitors passthrough ---------------------------------------
    orig_get = requests.get
    monitors_payload = {
        "ok": True,
        "monitors": [{"x": 0, "y": 0, "w": 1920, "h": 1080, "primary": True}],
        "count": 1,
    }
    seen = {}

    def fake_get(url, headers=None, timeout=None):
        seen["url"] = url
        return FakeResponse(200, monitors_payload)

    requests.get = fake_get
    try:
        r = client.get("/v1/monitors", headers=TOKEN)
        check(
            "/v1/monitors passes the hands reply through",
            r.status_code == 200
            and r.get_json() == monitors_payload
            and seen["url"].endswith("/monitors"),
        )
    finally:
        requests.get = orig_get

    def boom(url, headers=None, timeout=None):
        raise requests.RequestException("no route")

    requests.get = boom
    try:
        r = client.get("/v1/monitors", headers=TOKEN)
        check("/v1/monitors unreachable hands -> 502", r.status_code == 502)
    finally:
        requests.get = orig_get

    def unauthorized(url, headers=None, timeout=None):
        return FakeResponse(401, {"ok": False, "error": "bad secret"})

    requests.get = unauthorized
    try:
        r = client.get("/v1/monitors", headers=TOKEN)
        check("/v1/monitors hands 401 -> 502", r.status_code == 502)
    finally:
        requests.get = orig_get

    saved_secret = gateway.HANDS_SECRET
    gateway.HANDS_SECRET = ""
    try:
        r = client.get("/v1/monitors", headers=TOKEN)
        check("/v1/monitors with no hands secret -> 503", r.status_code == 503)
    finally:
        gateway.HANDS_SECRET = saved_secret

    print("FAILED: " + ", ".join(failures) if failures else "ALL PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
