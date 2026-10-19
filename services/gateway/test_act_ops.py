"""Tests for the V3-P4 gateway act ops (wishlist #3, #4, #6, #9, #19).

Runs anywhere — no live hands needed: gateway.requests.post / .get are
monkeypatched with recorders.

    python3 test_act_ops.py

Covers: HANDS_OPS contains the new ops; act() forwards drag to /drag
and clipboard_set to /clipboard/set (the one renamed path); the sized
act timeout for type; GET /v1/windows passthrough.
"""

import os
import sys

os.environ.setdefault("RELAY_GATEWAY_TOKEN", "test-token")
os.environ.setdefault("HANDS_SECRET", "test-secret")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app as gateway  # noqa: E402

TOKEN = {"X-Relay-Token": "test-token"}


class FakeResp:
    def __init__(self, body, status=200):
        self._body = body
        self.status_code = status
        self.ok = status < 400

    def json(self):
        return self._body


def run():
    client = gateway.app.test_client()
    failures = []

    def check(name, cond):
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    check("HANDS_OPS contains the new ops",
          {"hotkey", "break", "drag", "focus", "clipboard_set"}
          <= gateway.HANDS_OPS)
    check("existing ops are still present",
          {"move", "click", "type", "key", "scroll"} <= gateway.HANDS_OPS)

    posts = []

    def fake_post(url, json=None, headers=None, timeout=None):
        posts.append({"url": url, "json": json, "timeout": timeout})
        return FakeResp({"ok": True})

    orig_post, orig_get = gateway.requests.post, gateway.requests.get
    gateway.requests.post = fake_post
    try:
        r = client.post("/v1/act",
                        json={"op": "drag", "x1": 1, "y1": 2, "x2": 3, "y2": 4},
                        headers=TOKEN)
        check("act drag forwards to hands /drag with payload intact",
              r.status_code == 200 and len(posts) == 1
              and posts[0]["url"].endswith("/drag")
              and posts[0]["json"] == {"x1": 1, "y1": 2, "x2": 3, "y2": 4})

        posts.clear()
        r = client.post("/v1/act",
                        json={"op": "clipboard_set", "text": "hi"},
                        headers=TOKEN)
        check("act clipboard_set forwards to hands /clipboard/set",
              r.status_code == 200 and len(posts) == 1
              and posts[0]["url"].endswith("/clipboard/set")
              and posts[0]["json"] == {"text": "hi"})

        posts.clear()
        r = client.post("/v1/act", json={"op": "hotkey", "keys": ["ctrl", "l"]},
                        headers=TOKEN)
        check("act hotkey forwards to the identity path /hotkey",
              r.status_code == 200 and posts[0]["url"].endswith("/hotkey"))

        r = client.post("/v1/act", json={"op": "nonsense"}, headers=TOKEN)
        check("act unknown op still -> 400", r.status_code == 400)

        posts.clear()
        r = client.post("/v1/act", json={"op": "type", "text": "z" * 600},
                        headers=TOKEN)
        check("act passes the sized timeout through for long type",
              r.status_code == 200 and posts[0]["timeout"] == 115)
    finally:
        gateway.requests.post = orig_post

    # ------------------------------------------------ sized timeout (#9)
    t = gateway._act_timeout("type", {"text": "z" * 600})
    check("_act_timeout type 600 chars -> > 30 and <= 600", 30 < t <= 600)
    check("_act_timeout type short -> 30",
          gateway._act_timeout("type", {"text": "hi"}) == 30)
    check("_act_timeout click -> 30",
          gateway._act_timeout("click", {"x": 1, "y": 2}) == 30)
    check("_act_timeout type huge -> capped at 600",
          gateway._act_timeout("type", {"text": "z" * 100000}) == 600)

    # ------------------------------------------------ /v1/windows proxy
    gets = []

    def fake_get(url, headers=None, timeout=None):
        gets.append(url)
        return FakeResp({"ok": True, "windows": [{"title": "Alpha"}]})

    gateway.requests.get = fake_get
    try:
        r = client.get("/v1/windows", headers=TOKEN)
        check("GET /v1/windows passes the hands response through",
              r.status_code == 200
              and r.get_json()["windows"] == [{"title": "Alpha"}]
              and gets and gets[0].endswith("/windows"))
        r = client.get("/v1/windows")
        check("GET /v1/windows requires the gateway token",
              r.status_code == 401)

        gets.clear()
        gateway.requests.get = lambda url, headers=None, timeout=None: (
            gets.append(url), FakeResp({"ok": True, "text": "clip"}))[1]
        r = client.get("/v1/clipboard", headers=TOKEN)
        check("GET /v1/clipboard proxies hands /clipboard/get",
              r.status_code == 200 and r.get_json()["text"] == "clip"
              and gets[0].endswith("/clipboard/get"))
    finally:
        gateway.requests.get = orig_get

    print("FAILED: " + ", ".join(failures) if failures else "ALL PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
