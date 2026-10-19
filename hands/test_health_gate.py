"""Tests for the V3-R1 hands /health gate exemption (Grok review High #5).

The bug: the hands before_request gate applied the failed-guess
lockout AND the secret check to /health as well, contradicting the
file's own contract ("liveness only, no secret needed"). Worse, the
gateway probes /health to judge reachability — during a lockout the
probe read "down", and a supervisor restart on that false signal
would wipe the very lockout state protecting the service.

    python3 test_health_gate.py

Follows test_actuation.py's pattern: fake pyautogui/tkinter modules
are injected before the hands module is loaded from its file path.
"""

import importlib.util
import os
import sys
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
HANDS_PATH = os.path.join(HERE, "muse_relay_hands.py")


def _recorder(name):
    def fn(*args, **kwargs):
        return None

    return fn


fake_pag = types.ModuleType("pyautogui")
fake_pag.FAILSAFE = False
fake_pag.PAUSE = 0
for _name in ("moveTo", "click", "write", "press", "scroll", "hotkey",
              "mouseDown", "mouseUp"):
    setattr(fake_pag, _name, _recorder(_name))
fake_pag.screenshot = lambda: None
fake_pag.getAllWindows = lambda: []
sys.modules["pyautogui"] = fake_pag

fake_tk = types.ModuleType("tkinter")


class _Dummy:
    def __init__(self, *a, **k):
        pass


for _name in ("Tk", "StringVar", "Label", "Entry", "Button", "Text"):
    setattr(fake_tk, _name, _Dummy)
sys.modules["tkinter"] = fake_tk

spec = importlib.util.spec_from_file_location("muse_relay_hands", HANDS_PATH)
hands = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hands)

AUTH = {"X-Secret": hands.SHARED_SECRET}


def run():
    client = hands.app.test_client()
    failures = []

    def check(name, cond):
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    r = client.get("/health")
    check("health answers 200 with no secret at all",
          r.status_code == 200 and r.get_json().get("ok") is True)

    r = client.get("/windows")
    check("control: a real route without the secret is still 401",
          r.status_code == 401)

    # Force the lockout state the gate checks.
    hands._lockout_until = time.monotonic() + 300
    try:
        r = client.get("/health")
        check("health answers 200 during a lockout",
              r.status_code == 200 and r.get_json().get("ok") is True)
        r = client.get("/health", headers=AUTH)
        check("health answers 200 during a lockout even with the secret",
              r.status_code == 200)
        r = client.get("/windows", headers=AUTH)
        check("control: real routes stay locked out (429) during a lockout",
              r.status_code == 429)
    finally:
        hands._lockout_until = 0.0

    r = client.get("/windows", headers=AUTH)
    check("control: real routes work again once the lockout clears",
          r.status_code == 200)

    print("FAILED: " + ", ".join(failures) if failures else "ALL PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
