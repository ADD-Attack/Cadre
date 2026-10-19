"""Tests for the V3-P4 hands actuation routes (wishlist #3, #4, #6, #9, #19).

Runs anywhere — no Windows, no real desktop: fake pyautogui / tkinter
modules are injected into sys.modules BEFORE the hands module is loaded
from its file path, the fake pyautogui records every call, window
enumeration / activation and the clipboard backend are stubbed at their
seams (_enum_windows, _activate_window, _clipboard_backend), and the
routes are exercised through Flask's test client.

    python3 test_actuation.py

Covers: hotkey validation + chord; break chords (and times); drag call
order; type keys/paste paths incl. clipboard save/restore and forced
keys; focus substring / exact / 404; windows route shape; clipboard
get/set, the read being logged, and 501 when unavailable.
"""

import importlib.util
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
HANDS_PATH = os.path.join(HERE, "muse_relay_hands.py")
CONFIG_PATH = os.path.join(HERE, "muse_relay_config.json")
_config_existed = os.path.exists(CONFIG_PATH)

# ------------------------------------------------------------ fakes

calls = []


def _recorder(name):
    def fn(*args, **kwargs):
        calls.append((name, args, kwargs))

    return fn


fake_pag = types.ModuleType("pyautogui")
fake_pag.FAILSAFE = False
fake_pag.PAUSE = 0
for _name in (
    "moveTo", "click", "write", "press", "scroll", "hotkey",
    "mouseDown", "mouseUp",
):
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


class FakeClipboard:
    def __init__(self, initial=""):
        self.store = initial
        self.sets = []

    def get_text(self):
        return self.store

    def set_text(self, text):
        self.sets.append(text)
        self.store = text


def win(title, **kw):
    base = {
        "title": title, "process": "app.exe", "pid": 42,
        "bounds": {"x": 1, "y": 2, "w": 300, "h": 200},
        "monitor": 0, "visible": True, "focused": False,
    }
    base.update(kw)
    return base


def run():
    client = hands.app.test_client()
    failures = []

    def check(name, cond):
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    def names():
        return [c[0] for c in calls]

    orig_backend = hands._clipboard_backend
    orig_enum = hands._enum_windows
    orig_activate = hands._activate_window

    # ------------------------------------------------ hotkey (#19)
    calls.clear()
    r = client.post("/hotkey", json={"keys": []}, headers=AUTH)
    check("hotkey empty list -> 400, nothing pressed",
          r.status_code == 400 and not calls)
    r = client.post("/hotkey", json={"keys": "ctrl,l"}, headers=AUTH)
    check("hotkey non-list -> 400", r.status_code == 400 and not calls)
    r = client.post("/hotkey", json={"keys": ["ctrl", "l"]}, headers=AUTH)
    check("hotkey valid -> hotkey('ctrl','l')",
          r.status_code == 200
          and calls == [("hotkey", ("ctrl", "l"), {})])

    # Auth still gates the new routes.
    r = client.post("/hotkey", json={"keys": ["ctrl", "l"]})
    check("hotkey without secret -> 401", r.status_code == 401)

    # ------------------------------------------------ break (#19)
    calls.clear()
    r = client.post("/break", json={}, headers=AUTH)
    check("break default -> one hotkey('ctrl','c')",
          r.status_code == 200
          and calls == [("hotkey", ("ctrl", "c"), {})])
    calls.clear()
    r = client.post("/break", json={"times": 2}, headers=AUTH)
    check("break times=2 -> chord twice",
          r.status_code == 200
          and calls == [("hotkey", ("ctrl", "c"), {})] * 2)
    calls.clear()
    r = client.post("/break", json={"times": 5}, headers=AUTH)
    check("break times=5 -> 400, nothing pressed",
          r.status_code == 400 and not calls)

    # ------------------------------------------------ drag (#4)
    calls.clear()
    r = client.post("/drag", json={"x1": 10, "y1": 20, "x2": 90, "y2": 80},
                    headers=AUTH)
    check("drag call order down->move->up with default duration",
          r.status_code == 200
          and names() == ["moveTo", "mouseDown", "moveTo", "mouseUp"]
          and calls[0][1] == (10, 20)
          and calls[1][2].get("button") == "left"
          and calls[2][1] == (90, 80)
          and calls[2][2].get("duration") == 0.4
          and calls[3][2].get("button") == "left")
    calls.clear()
    r = client.post("/drag", json={"x1": 10, "y1": 20, "x2": 90},
                    headers=AUTH)
    check("drag missing coord -> 400, nothing pressed",
          r.status_code == 400 and not calls)
    r = client.post("/drag",
                    json={"x1": "a", "y1": 20, "x2": 90, "y2": 80},
                    headers=AUTH)
    check("drag non-numeric coord -> 400", r.status_code == 400 and not calls)

    # ------------------------------------------------ type: keys (#9)
    calls.clear()
    hands._clipboard_backend = lambda: None
    r = client.post("/type", json={"text": "hello"}, headers=AUTH)
    body = r.get_json()
    check("type short text -> keys path (write, method_used keys)",
          r.status_code == 200 and body["method_used"] == "keys"
          and body["chars"] == 5
          and calls == [("write", ("hello",), {"interval": 0.02})])

    # ------------------------------------------------ type: paste (#9)
    clip = FakeClipboard("PREVIOUS")
    hands._clipboard_backend = lambda: clip
    long_text = "x" * 200
    calls.clear()
    r = client.post("/type", json={"text": long_text}, headers=AUTH)
    body = r.get_json()
    check("type 200 chars with clipboard -> paste path",
          r.status_code == 200 and body["method_used"] == "paste"
          and body["chars"] == 200)
    check("paste set clipboard to text then restored previous value",
          clip.sets == [long_text, "PREVIOUS"] and clip.store == "PREVIOUS")
    check("paste used hotkey('ctrl','v') and never write()",
          ("hotkey", ("ctrl", "v"), {}) in calls
          and "write" not in names())

    calls.clear()
    r = client.post("/type", json={"text": long_text, "method": "keys"},
                    headers=AUTH)
    check("type method=keys forces keystrokes even for long text",
          r.status_code == 200 and r.get_json()["method_used"] == "keys"
          and names() == ["write"] and clip.store == "PREVIOUS")

    # Paste requested but no backend -> keys fallback, and it says so.
    hands._clipboard_backend = lambda: None
    calls.clear()
    r = client.post("/type", json={"text": "abc", "method": "paste"},
                    headers=AUTH)
    body = r.get_json()
    check("type method=paste without backend -> keys fallback + note",
          r.status_code == 200 and body["method_used"] == "keys"
          and bool(body.get("note")) and names() == ["write"])

    # Paste path whose clipboard blows up -> keys fallback, not a 500.
    class BoomClipboard:
        def get_text(self):
            raise RuntimeError("boom")

        def set_text(self, text):
            raise RuntimeError("boom")

    hands._clipboard_backend = lambda: BoomClipboard()
    calls.clear()
    r = client.post("/type", json={"text": "y" * 200}, headers=AUTH)
    check("type paste failure falls back to keys (no 500)",
          r.status_code == 200 and r.get_json()["method_used"] == "keys"
          and names() == ["write"])
    hands._clipboard_backend = orig_backend

    # ------------------------------------------------ windows + focus (#3)
    wins = [win("Alpha Editor"), win("Beta - alpha notes"), win("Gamma")]
    hands._enum_windows = lambda: wins
    activated = []
    hands._activate_window = lambda w: activated.append(w)

    r = client.get("/windows", headers=AUTH)
    body = r.get_json()
    check("windows route shape",
          r.status_code == 200 and body["ok"] and len(body["windows"]) == 3
          and body["windows"][0] == {
              "title": "Alpha Editor", "process": "app.exe", "pid": 42,
              "bounds": {"x": 1, "y": 2, "w": 300, "h": 200},
              "monitor": 0, "visible": True, "focused": False})
    check("windows entries carry no private keys",
          all(not any(k.startswith("_") for k in w) for w in body["windows"]))

    r = client.post("/focus", json={"title": "NOTES"}, headers=AUTH)
    check("focus substring (case-insensitive) activates the right window",
          r.status_code == 200 and len(activated) == 1
          and activated[0]["title"] == "Beta - alpha notes"
          and r.get_json()["window"]["title"] == "Beta - alpha notes")

    activated.clear()
    r = client.post("/focus", json={"title": "no such window"}, headers=AUTH)
    check("focus no match -> 404, nothing activated",
          r.status_code == 404 and not activated)

    activated.clear()
    r = client.post("/focus", json={"title": "alpha", "exact": True},
                    headers=AUTH)
    check("focus exact=true rejects a substring-only match",
          r.status_code == 404 and not activated)
    r = client.post("/focus",
                    json={"title": "alpha editor", "exact": True},
                    headers=AUTH)
    check("focus exact=true matches the full title",
          r.status_code == 200 and len(activated) == 1
          and activated[0]["title"] == "Alpha Editor")
    hands._enum_windows = orig_enum
    hands._activate_window = orig_activate

    # Off-Windows the real enumerator yields an empty, supported=false list.
    r = client.get("/windows", headers=AUTH)
    body = r.get_json()
    if os.name != "nt":
        check("windows off-Windows -> empty list, supported false, no 500",
              r.status_code == 200 and body["windows"] == []
              and body.get("supported") is False)

    # ------------------------------------------------ clipboard (#6)
    clip = FakeClipboard("clip contents")
    hands._clipboard_backend = lambda: clip
    while not hands.log_queue.empty():
        hands.log_queue.get_nowait()
    r = client.get("/clipboard/get", headers=AUTH)
    logged = []
    while not hands.log_queue.empty():
        logged.append(hands.log_queue.get_nowait())
    check("clipboard get returns the backend text",
          r.status_code == 200 and r.get_json()["text"] == "clip contents")
    check("clipboard read is written to the hands log queue",
          "clipboard read via relay" in logged)

    r = client.post("/clipboard/set", json={"text": "new text"}, headers=AUTH)
    check("clipboard set stores via the backend",
          r.status_code == 200 and clip.store == "new text")

    hands._clipboard_backend = lambda: None
    r = client.get("/clipboard/get", headers=AUTH)
    check("clipboard get unavailable -> 501",
          r.status_code == 501
          and r.get_json()["error"] == "clipboard unavailable on this host")
    r = client.post("/clipboard/set", json={"text": "x"}, headers=AUTH)
    check("clipboard set unavailable -> 501", r.status_code == 501)
    hands._clipboard_backend = orig_backend

    print("FAILED: " + ", ".join(failures) if failures else "ALL PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    finally:
        # Importing the hands creates its config next to the module when
        # none exists; never leave that artefact behind from a test run.
        if not _config_existed and os.path.exists(CONFIG_PATH):
            os.remove(CONFIG_PATH)
