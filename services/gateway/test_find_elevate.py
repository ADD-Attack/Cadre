"""Tests for POST /v1/find and the /v1/elevate forwards (wishlist #12, #8).

Runs anywhere with the gateway's deps installed — no live parser or
hands needed: gateway.requests.post/get are stubbed.

    python3 test_find_elevate.py

Covers: token auth still enforced; /v1/find forwards the body and
returns the parser's JSON/status; /v1/elevate forwards only the name;
GET /v1/elevate/<id> passes through; a hands 401 maps to 502; missing
HANDS_SECRET is 503; an unreachable hands is 502.
"""

import os
import sys

os.environ.setdefault("RELAY_GATEWAY_TOKEN", "test-token")
os.environ.setdefault("HANDS_SECRET", "test-secret")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app as gateway  # noqa: E402
import requests  # noqa: E402

TOKEN = {"X-Relay-Token": "test-token"}


class FakeResp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._payload


class Stub:
    """Records calls and returns a canned response (or raises)."""

    def __init__(self, resp=None, exc=None):
        self.resp = resp
        self.exc = exc
        self.calls = []

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.exc is not None:
            raise self.exc
        return self.resp


def run():
    client = gateway.app.test_client()
    failures = []
    real_post, real_get = gateway.requests.post, gateway.requests.get

    def check(name, cond):
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    try:
        # --- /v1/find -------------------------------------------------
        stub = Stub(FakeResp(200, {"ok": True, "matches": [], "count": 0}))
        gateway.requests.post = stub
        r = client.post(
            "/v1/find",
            json={"image_b64": "AAAA", "text": "Save"},
            headers=TOKEN,
        )
        check("/v1/find returns parser JSON/status",
              r.status_code == 200 and r.get_json()["count"] == 0)
        url, kwargs = stub.calls[-1]
        check("/v1/find posts to PARSER_URL/find",
              url == f"{gateway.PARSER_URL}/find")
        check(
            "/v1/find forwards image_b64/text/case_sensitive",
            kwargs["json"] == {
                "image_b64": "AAAA",
                "text": "Save",
                "case_sensitive": False,
            },
        )
        r = client.post(
            "/v1/find",
            json={"image_b64": "AAAA", "text": "Save", "case_sensitive": True},
            headers=TOKEN,
        )
        check("/v1/find forwards case_sensitive=True",
              stub.calls[-1][1]["json"]["case_sensitive"] is True)

        # Parser status passthrough (e.g. its 501 honesty response).
        gateway.requests.post = Stub(
            FakeResp(501, {"ok": False, "error": "parser model not loaded"})
        )
        r = client.post(
            "/v1/find", json={"image_b64": "AAAA", "text": "x"}, headers=TOKEN
        )
        check("/v1/find passes through parser 501",
              r.status_code == 501 and r.get_json()["ok"] is False)

        # Auth: no token -> 401.
        r = client.post("/v1/find", json={"image_b64": "AAAA", "text": "x"})
        check("/v1/find requires the gateway token", r.status_code == 401)

        # --- /v1/elevate ----------------------------------------------
        stub = Stub(FakeResp(200, {"ok": True, "id": "abc123", "state": "pending"}))
        gateway.requests.post = stub
        r = client.post("/v1/elevate", json={"name": "notepad-elevated"}, headers=TOKEN)
        check("/v1/elevate returns hands JSON/status",
              r.status_code == 200 and r.get_json()["id"] == "abc123")
        url, kwargs = stub.calls[-1]
        check("/v1/elevate posts to HANDS_URL/elevate",
              url == f"{gateway.HANDS_URL}/elevate")
        check("/v1/elevate forwards only the name",
              kwargs["json"] == {"name": "notepad-elevated"})
        check("/v1/elevate sends the hands secret header",
              kwargs["headers"].get("X-Secret") == "test-secret")

        # GET passthrough.
        get_stub = Stub(
            FakeResp(200, {"ok": True, "id": "abc123", "name": "notepad-elevated",
                           "state": "launched"})
        )
        gateway.requests.get = get_stub
        r = client.get("/v1/elevate/abc123", headers=TOKEN)
        check("GET /v1/elevate/<id> passes through",
              r.status_code == 200 and r.get_json()["state"] == "launched")
        check("GET /v1/elevate/<id> hits the hands status route",
              get_stub.calls[-1][0] == f"{gateway.HANDS_URL}/elevate/abc123")

        # Auth on the new routes.
        r = client.post("/v1/elevate", json={"name": "x"})
        check("/v1/elevate requires the gateway token", r.status_code == 401)
        r = client.get("/v1/elevate/abc123")
        check("GET /v1/elevate/<id> requires the gateway token",
              r.status_code == 401)

        # Hands 401 -> 502 (secret mismatch style).
        gateway.requests.post = Stub(FakeResp(401, {"ok": False, "error": "bad secret"}))
        r = client.post("/v1/elevate", json={"name": "x"}, headers=TOKEN)
        check("hands 401 maps to gateway 502",
              r.status_code == 502 and "does not match" in r.get_json()["error"])
        gateway.requests.get = Stub(FakeResp(401, {"ok": False, "error": "bad secret"}))
        r = client.get("/v1/elevate/abc123", headers=TOKEN)
        check("hands 401 on status maps to gateway 502", r.status_code == 502)

        # Hands unreachable -> 502.
        gateway.requests.post = Stub(exc=requests.RequestException("boom"))
        r = client.post("/v1/elevate", json={"name": "x"}, headers=TOKEN)
        check("unreachable hands maps to 502", r.status_code == 502)

        # No HANDS_SECRET -> 503.
        saved = gateway.HANDS_SECRET
        gateway.HANDS_SECRET = ""
        try:
            r = client.post("/v1/elevate", json={"name": "x"}, headers=TOKEN)
            check("no HANDS_SECRET maps to 503", r.status_code == 503)
            r = client.get("/v1/elevate/abc123", headers=TOKEN)
            check("no HANDS_SECRET on status maps to 503", r.status_code == 503)
        finally:
            gateway.HANDS_SECRET = saved
    finally:
        gateway.requests.post, gateway.requests.get = real_post, real_get

    print("FAILED: " + ", ".join(failures) if failures else "ALL PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
