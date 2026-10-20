"""Tests for capture variants + input realism (wishlist #10, #11, #16, #17).

Runs anywhere — no Windows desktop needed: fake pyautogui / tkinter
modules are injected into sys.modules BEFORE the hands module is loaded
from its file path, and the Windows seams (_monitor_rects, _grab) are
stubbed at the module boundary. What is tested is the logic: parameter
validation, rect selection, the pure delay/path planners, and the
param forwarding into pyautogui.

    python3 test_capture_realism.py

Note: importing the hands module may create muse_relay_config.json (and
a bad-secret probe creates muse_relay.log) next to it; both are removed
again at the end if they did not exist before the run. Never commit
either file.
"""

import importlib.util
import os
import random
import sys
import time as real_time
import types

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- fake pyautogui / tkinter, injected before the hands import -----------

calls = {"screenshot": [], "write": [], "moveTo": [], "click": [], "press": [], "scroll": []}
state = {"position": (0, 0)}

fake_pag = types.ModuleType("pyautogui")
fake_pag.FAILSAFE = False
fake_pag.PAUSE = 0


def _screenshot(region=None):
    calls["screenshot"].append(region)
    return Image.new("RGB", (64, 48), (10, 20, 30))


def _move_to(x, y, duration=None):
    calls["moveTo"].append((x, y, duration))


def _click(x=None, y=None, button="left"):
    calls["click"].append((x, y, button))


def _write(*args, **kwargs):
    calls["write"].append((args, kwargs))


fake_pag.screenshot = _screenshot
fake_pag.size = lambda: (1920, 1080)
fake_pag.position = lambda: state["position"]
fake_pag.moveTo = _move_to
fake_pag.click = _click
fake_pag.write = _write
fake_pag.press = lambda k: calls["press"].append(k)
fake_pag.scroll = lambda c: calls["scroll"].append(c)
sys.modules["pyautogui"] = fake_pag

fake_tk = types.ModuleType("tkinter")


class _Tk:
    pass


fake_tk.Tk = _Tk
fake_tk.StringVar = object
fake_tk.Label = object
fake_tk.Entry = object
fake_tk.Button = object
fake_tk.Text = object
sys.modules["tkinter"] = fake_tk

_CONFIG = os.path.join(HERE, "muse_relay_config.json")
_LOG = os.path.join(HERE, "muse_relay.log")
_config_preexisted = os.path.exists(_CONFIG)
_log_preexisted = os.path.exists(_LOG)

spec = importlib.util.spec_from_file_location(
    "muse_relay_hands", os.path.join(HERE, "muse_relay_hands.py")
)
hands = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hands)

AUTH = {"X-Secret": hands.SHARED_SECRET}
RECTS = [
    {"x": 0, "y": 0, "w": 1920, "h": 1080, "primary": True},
    {"x": -1280, "y": 0, "w": 1280, "h": 1024, "primary": False},
]

orig_monitor_rects = hands._monitor_rects
orig_grab = hands._grab

grab_calls = []


def fake_grab(rect):
    grab_calls.append(rect)
    if rect is None:
        return Image.new("RGB", (100, 50), (1, 2, 3))
    return Image.new("RGB", (rect["w"], rect["h"]), (4, 5, 6))


class FakeTime:
    """Module-time stand-in: records sleeps, keeps a real monotonic."""

    def __init__(self):
        self.sleeps = []
        self.monotonic = real_time.monotonic
        self.time = real_time.time

    def sleep(self, seconds):
        self.sleeps.append(seconds)


class MaxRng:
    """uniform() always returns the upper bound — worst-case delays."""

    def uniform(self, a, b):
        return b


def run():
    client = hands.app.test_client()
    failures = []

    def check(name, cond):
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    # ---- /monitors ------------------------------------------------------
    hands._monitor_rects = lambda: [dict(r) for r in RECTS]
    r = client.get("/monitors", headers=AUTH)
    body = r.get_json()
    check(
        "/monitors shape + count",
        r.status_code == 200
        and body["ok"]
        and body["count"] == 2
        and body["monitors"] == RECTS,
    )
    r = client.get("/monitors")  # no secret
    check("/monitors still requires the secret", r.status_code == 401)

    # Fallback seam: no Windows enumeration -> one primary rect.
    rects = orig_monitor_rects()
    check(
        "_monitor_rects fallback is a single primary rect from pyautogui.size()",
        rects == [{"x": 0, "y": 0, "w": 1920, "h": 1080, "primary": True}],
    )

    # ---- /screenshot variants -------------------------------------------
    hands._monitor_rects = lambda: [dict(r) for r in RECTS]
    hands._grab = fake_grab
    grab_calls.clear()

    r = client.get("/screenshot?monitor=1", headers=AUTH)
    check(
        "?monitor=1 grabs rect 1 and sets X-Screen-Monitor",
        r.status_code == 200
        and grab_calls[-1] == RECTS[1]
        and r.headers.get("X-Screen-Monitor") == "1"
        and r.headers.get("X-Screen-Width") == "1280"
        and r.headers.get("X-Screen-Height") == "1024",
    )

    r = client.get("/screenshot?monitor=9", headers=AUTH)
    err = (r.get_json() or {}).get("error", "")
    check("?monitor=9 -> 400 listing the count", r.status_code == 400 and "2" in err)

    r = client.get("/screenshot?region=10,20,300,200", headers=AUTH)
    check(
        "?region grabs that rect and sets X-Screen-Region",
        r.status_code == 200
        and grab_calls[-1] == {"x": 10, "y": 20, "w": 300, "h": 200}
        and r.headers.get("X-Screen-Region") == "10,20,300,200"
        and r.headers.get("X-Screen-Width") == "300",
    )

    r = client.get("/screenshot?region=bad", headers=AUTH)
    check("?region=bad -> 400", r.status_code == 400)
    r = client.get("/screenshot?region=1,2,0,4", headers=AUTH)
    check("?region with w=0 -> 400", r.status_code == 400)
    r = client.get("/screenshot?monitor=0&region=1,2,3,4", headers=AUTH)
    check("monitor+region together -> 400", r.status_code == 400)

    grab_calls.clear()
    r = client.get("/screenshot", headers=AUTH)
    check(
        "no params -> _grab(None) legacy frame, no variant headers",
        r.status_code == 200
        and grab_calls == [None]
        and "X-Screen-Monitor" not in r.headers
        and "X-Screen-Region" not in r.headers
        and r.headers.get("X-Screen-Width") == "100",
    )

    # ---- _grab seam -------------------------------------------------------
    calls["screenshot"].clear()
    orig_grab(None)
    orig_grab({"x": 10, "y": 20, "w": 300, "h": 200})
    check(
        "_grab forwards region tuple only when a rect is given",
        calls["screenshot"] == [None, (10, 20, 300, 200)],
    )

    # ---- _plan_key_delays -------------------------------------------------
    delays = hands._plan_key_delays("abcdefgh", random.Random(0))
    check(
        "key delays: per-char, base within [0.04, 0.16]",
        len(delays) == 8 and all(0.04 <= d <= 0.16 for d in delays),
    )
    check(
        "key delays: deterministic for the same seed",
        delays == hands._plan_key_delays("abcdefgh", random.Random(0)),
    )
    delays = hands._plan_key_delays("a b.", MaxRng())
    check(
        "key delays: space and sentence-end add their allowances",
        abs(delays[1] - 0.36) < 1e-9 and abs(delays[3] - 0.46) < 1e-9,
    )
    text500 = "word " * 100
    delays = hands._plan_key_delays(text500, random.Random(0))
    check(
        "key delays: 500-char total within budget",
        len(delays) == 500 and sum(delays) <= max(5.0, 500 * 0.16) + 1e-9,
    )
    delays = hands._plan_key_delays("a " * 250, MaxRng())
    check(
        "key delays: over-budget plan scales down to the budget",
        abs(sum(delays) - 80.0) < 1e-6,
    )

    # ---- /type execution paths --------------------------------------------
    fake_time = FakeTime()
    hands.time = fake_time
    try:
        calls["write"].clear()
        fake_time.sleeps.clear()
        r = client.post("/type", json={"text": "hello", "jitter": False}, headers=AUTH)
        check(
            "jitter=false: single legacy write, no per-char sleeps",
            r.status_code == 200
            and calls["write"] == [(("hello",), {"interval": 0.02})]
            and fake_time.sleeps == [],
        )

        calls["write"].clear()
        fake_time.sleeps.clear()
        r = client.post("/type", json={"text": "hi"}, headers=AUTH)
        body = r.get_json()
        check(
            "jitter default: per-char writes with a sleep after each",
            r.status_code == 200
            and calls["write"] == [(("h",), {}), (("i",), {})]
            and len(fake_time.sleeps) == 2
            and body["delays_planned"] == 2
            and abs(body["planned_seconds"] - sum(fake_time.sleeps)) < 1e-9,
        )
    finally:
        hands.time = real_time

    # ---- _plan_path ---------------------------------------------------------
    path = hands._plan_path(0, 0, 800, 0, random.Random(1))
    check(
        "path: final step is exactly the target",
        (path[-1][0], path[-1][1]) == (800, 0),
    )
    check(
        "path: 800px move has many steps and a curve (off-line midpoint)",
        len(path) > 8 and any(abs(p[1]) > 1 for p in path[1:-1]),
    )
    # R9: overshoot / structural miss / direct is drawn per movement, so
    # across seeds some paths must leave the target and come back.
    excursions = 0
    for seed in range(40):
        p = hands._plan_path(0, 0, 800, 0, random.Random(seed))
        if max(q[0] for q in p) > 800.5 or any(abs(q[1]) > 4 for q in p[-6:-1]):
            excursions += 1
    check("path: overshoot/miss happens on some (not all) movements",
          0 < excursions < 40)
    total = sum(p[2] for p in path)
    check("path: Fitts travel time is plausible (0.2-1.2 s)", 0.2 <= total <= 1.2)
    check(
        "path: deterministic for the same seed",
        path == hands._plan_path(0, 0, 800, 0, random.Random(1)),
    )
    tiny = hands._plan_path(0, 0, 2, 0, random.Random(1))
    check(
        "path: tiny move (2px) is a single step at the target",
        len(tiny) == 1 and (tiny[0][0], tiny[0][1]) == (2, 0),
    )

    # ---- /move and /click, human on/off -------------------------------------
    fake_time = FakeTime()
    hands.time = fake_time
    try:
        calls["moveTo"].clear()
        r = client.post("/move", json={"x": 50, "y": 60, "human": False}, headers=AUTH)
        check(
            "/move human=false: legacy moveTo(duration=0.2)",
            r.status_code == 200 and calls["moveTo"] == [(50, 60, 0.2)],
        )

        state["position"] = (0, 0)
        calls["moveTo"].clear()
        r = client.post("/move", json={"x": 200, "y": 0}, headers=AUTH)
        check(
            "/move human (default): multi-step path ending exactly on target",
            r.status_code == 200
            and len(calls["moveTo"]) > 1
            and (calls["moveTo"][-1][0], calls["moveTo"][-1][1]) == (200, 0),
        )

        calls["moveTo"].clear()
        calls["click"].clear()
        r = client.post("/click", json={"x": 10, "y": 20, "human": False}, headers=AUTH)
        check(
            "/click human=false: legacy moveTo(duration=0.2), no path steps",
            r.status_code == 200
            and calls["moveTo"] == [(10, 20, 0.2)]
            and calls["click"] == [(10, 20, "left")],
        )

        state["position"] = (0, 0)
        calls["moveTo"].clear()
        calls["click"].clear()
        fake_time.sleeps.clear()
        downs, ups = [], []
        fake_pag.mouseDown = lambda x=None, y=None, button="left": downs.append((x, y, button))
        fake_pag.mouseUp = lambda x=None, y=None, button="left": ups.append((x, y, button))
        r = client.post("/click", json={"x": 300, "y": 0}, headers=AUTH)
        # attention + one sleep per path step + hover + hold
        check(
            "/click human: attention, path, hover, then down/hold/up on target",
            r.status_code == 200
            and len(calls["moveTo"]) > 1
            and (calls["moveTo"][-1][0], calls["moveTo"][-1][1]) == (300, 0)
            and downs == [(300, 0, "left")] and ups == [(300, 0, "left")]
            and len(fake_time.sleeps) == len(calls["moveTo"]) + 3,
        )
    finally:
        hands.time = real_time

    print("FAILED: " + ", ".join(failures) if failures else "ALL PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    finally:
        if not _config_preexisted and os.path.exists(_CONFIG):
            os.remove(_CONFIG)
        if not _log_preexisted and os.path.exists(_LOG):
            os.remove(_LOG)
