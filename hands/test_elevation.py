"""Tests for the hands elevation bridge (wishlist #8).

Runs anywhere: pyautogui/tkinter are stubbed before import, the
Windows launch seam (_run_elevated) is stubbed, and approval/denial is
driven through _resolve_elevation directly — the same function the
app window's dialog calls. Nothing is ever launched here.

    python3 test_elevation.py

Note: importing the hands module may create muse_relay_config.json
next to it (its first-run alert-topic behaviour); the test deletes it
again in cleanup and it must never be committed.
"""

import os
import sys
import time
import types

# Stub the desktop modules before importing the hands module.
_fake_gui = types.ModuleType("pyautogui")
_fake_gui.FAILSAFE = False
_fake_gui.PAUSE = 0
sys.modules.setdefault("pyautogui", _fake_gui)
_fake_tk = types.ModuleType("tkinter")
_fake_tk.Tk = object
sys.modules.setdefault("tkinter", _fake_tk)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import muse_relay_hands as hands  # noqa: E402

HEADERS = {"X-Secret": None}  # filled in after import


def run():
    client = hands.app.test_client()
    failures = []

    def check(name, cond):
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    HEADERS["X-Secret"] = hands.SHARED_SECRET
    real_allowlist = hands._elevate_allowlist
    real_run = hands._run_elevated
    try:
        # Unconfigured allowlist -> 501.
        hands._elevate_allowlist = lambda: {}
        r = client.post("/elevate", json={"name": "anything"}, headers=HEADERS)
        check("unconfigured allowlist returns 501", r.status_code == 501)

        hands._elevate_allowlist = lambda: {
            "notepad-elevated": {"exe": "notepad.exe", "args": ""}
        }

        # Unknown name -> 404.
        r = client.post("/elevate", json={"name": "nope"}, headers=HEADERS)
        check("unknown name returns 404", r.status_code == 404)

        # Auth still enforced (no secret -> 401 from the gate).
        r = client.post("/elevate", json={"name": "notepad-elevated"})
        check("elevate requires the hands secret", r.status_code == 401)

        # Create -> pending, and the request lands on elevate_queue.
        while not hands.elevate_queue.empty():
            hands.elevate_queue.get_nowait()
        r = client.post(
            "/elevate", json={"name": "notepad-elevated"}, headers=HEADERS
        )
        body = r.get_json()
        check("create returns ok + id + pending",
              r.status_code == 200 and body["ok"] and body["id"]
              and body["state"] == "pending")
        eid = body["id"]
        check("request was queued for the app window",
              hands.elevate_queue.qsize() == 1)
        queued = hands.elevate_queue.get_nowait()
        check("queued request carries name + configured exe/args",
              queued["id"] == eid and queued["name"] == "notepad-elevated"
              and queued["exe"] == "notepad.exe")

        r = client.get(f"/elevate/{eid}", headers=HEADERS)
        check("GET shows pending",
              r.status_code == 200 and r.get_json()["state"] == "pending"
              and r.get_json()["name"] == "notepad-elevated")

        # Deny -> denied; a second resolve is a no-op.
        check("deny resolves", hands._resolve_elevation(eid, False) is True)
        r = client.get(f"/elevate/{eid}", headers=HEADERS)
        check("GET shows denied", r.get_json()["state"] == "denied")
        check("resolving a resolved id is a no-op False",
              hands._resolve_elevation(eid, True) is False)
        check("resolving an unknown id is a no-op False",
              hands._resolve_elevation("deadbeef", True) is False)

        # Approve with launch seam True -> launched.
        r = client.post(
            "/elevate", json={"name": "notepad-elevated"}, headers=HEADERS
        )
        eid2 = r.get_json()["id"]
        hands._run_elevated = lambda entry: True
        check("approve resolves", hands._resolve_elevation(eid2, True) is True)
        r = client.get(f"/elevate/{eid2}", headers=HEADERS)
        check("GET shows launched", r.get_json()["state"] == "launched")

        # Approve with launch seam False -> launch_failed.
        r = client.post(
            "/elevate", json={"name": "notepad-elevated"}, headers=HEADERS
        )
        eid3 = r.get_json()["id"]
        hands._run_elevated = lambda entry: False
        check("failed approve resolves",
              hands._resolve_elevation(eid3, True) is True)
        r = client.get(f"/elevate/{eid3}", headers=HEADERS)
        check("GET shows launch_failed",
              r.get_json()["state"] == "launch_failed")

        # Expiry: a pending request older than 120s reads as expired.
        r = client.post(
            "/elevate", json={"name": "notepad-elevated"}, headers=HEADERS
        )
        eid4 = r.get_json()["id"]
        hands._elevations[eid4]["created_at"] = time.time() - 121
        r = client.get(f"/elevate/{eid4}", headers=HEADERS)
        check("stale pending request shows expired",
              r.get_json()["state"] == "expired")
        check("an expired request cannot be resolved",
              hands._resolve_elevation(eid4, True) is False)

        # Unknown id -> 404.
        r = client.get("/elevate/deadbeef", headers=HEADERS)
        check("GET unknown id returns 404", r.status_code == 404)
    finally:
        hands._elevate_allowlist = real_allowlist
        hands._run_elevated = real_run
        # Import side effects: never leave (or commit) the hands
        # config / log files the module may have created.
        base = os.path.dirname(os.path.abspath(__file__))
        for name in ("muse_relay_config.json", "muse_relay.log"):
            try:
                os.remove(os.path.join(base, name))
            except OSError:
                pass

    print("FAILED: " + ", ".join(failures) if failures else "ALL PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
