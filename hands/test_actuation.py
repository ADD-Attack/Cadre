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
keys; the mid-type owner-abort re-check against a fake last-input tick
(R7.2); focus substring / exact / 404; windows route shape; clipboard
get/set, the read being logged, and 501 when unavailable; the Windows
clipboard backend's call shape against faked dlls (R7.2).
"""

import ctypes
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

# Integration (V3-P4 + V3-P5 merged /type): the keystroke path now applies
# jittered per-char delays by default, so real sleeps would make the
# 200-char keystroke cases take ~20s each. Sleeps are timing, not logic —
# stub them out for this test process.
hands.time.sleep = lambda _seconds: None

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
          and calls == [("write", (ch,), {}) for ch in "hello"])

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
          and set(names()) == {"write"} and clip.store == "PREVIOUS")

    # Paste requested but no backend -> keys fallback, and it says so.
    hands._clipboard_backend = lambda: None
    calls.clear()
    r = client.post("/type", json={"text": "abc", "method": "paste"},
                    headers=AUTH)
    body = r.get_json()
    check("type method=paste without backend -> keys fallback + note",
          r.status_code == 200 and body["method_used"] == "keys"
          and bool(body.get("note")) and set(names()) == {"write"})

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
          and set(names()) == {"write"})
    hands._clipboard_backend = orig_backend

    # ------------------------------------------ type re-check (R7.2, #27)
    # The F7 mid-type abort must tell owner input from the type's own
    # keystrokes. A virtual last-input tick models the session: our
    # writes stamp it, a scripted owner event stamps it during a chosen
    # inter-char sleep, and _probe_dwtime reads it back.
    check("_dw_advanced: strictly newer tick reads advanced",
          hands._dw_advanced(200, 100) is True
          and hands._dw_advanced(100, 200) is False
          and hands._dw_advanced(100, 100) is False)
    check("_dw_advanced: wrap-safe across the 32-bit tick boundary",
          hands._dw_advanced(5, 0xFFFFFFF8) is True
          and hands._dw_advanced(0xFFFFFFF8, 5) is False)

    # jitter=False stays the single pyautogui.write, untouched by the
    # re-check machinery.
    calls.clear()
    hands._clipboard_backend = lambda: None
    r = client.post("/type", json={"text": "hello", "method": "keys",
                                   "jitter": False}, headers=AUTH)
    check("type jitter=false -> one write(text, interval=0.02)",
          r.status_code == 200
          and calls == [("write", ("hello",), {"interval": 0.02})])

    class _InputClock:
        def __init__(self, owner_on_sleep=None):
            self.tick = 100000
            self.dw = self.tick - 5001  # last input ~5 s before the door
            self.sleeps = 0
            self.owner_on_sleep = owner_on_sleep

        def probe(self):
            return self.dw

        def write(self, ch):
            calls.append(("write", (ch,), {}))
            self.tick += 10
            self.dw = self.tick  # our keystroke is the freshest input

        def sleep(self, _seconds):
            self.sleeps += 1
            if self.sleeps == self.owner_on_sleep:
                self.tick += 10
                self.dw = self.tick  # the owner's key lands in this pause

    orig_write = fake_pag.write
    orig_sleep_stub = hands.time.sleep
    orig_probe_dwtime = hands._probe_dwtime
    url40 = "https://www.spotify.com/account/privacy/"
    try:
        # (a) Only our own keystrokes move dwTime: all 40 chars land.
        clock = _InputClock()
        fake_pag.write = clock.write
        hands.time.sleep = clock.sleep
        hands._probe_dwtime = clock.probe
        calls.clear()
        r = client.post("/type", json={"text": url40, "method": "keys"},
                        headers=AUTH)
        body = r.get_json()
        written = "".join(c[1][0] for c in calls if c[0] == "write")
        check("type 40 chars, own keystrokes only -> completes, no abort",
              r.status_code == 200 and body["ok"] is True
              and body["method_used"] == "keys" and body["chars"] == 40
              and written == url40)

        # (b) Owner input during the pause after char 18: the type
        # aborts at the next 12-char boundary (24) with the honest
        # partial, and nothing past the boundary is typed.
        clock = _InputClock(owner_on_sleep=18)
        fake_pag.write = clock.write
        hands.time.sleep = clock.sleep
        hands._probe_dwtime = clock.probe
        calls.clear()
        r = client.post("/type", json={"text": url40, "method": "keys"},
                        headers=AUTH)
        body = r.get_json()
        written = "".join(c[1][0] for c in calls if c[0] == "write")
        check("type owner input mid-type -> 409 type_aborted at char 24",
              r.status_code == 409 and body["ok"] is False
              and body["error_code"] == "type_aborted"
              and body["aborted"] is True and body["chars_typed"] == 24
              and body["chars"] == 40 and written == url40[:24])
    finally:
        fake_pag.write = orig_write
        hands.time.sleep = orig_sleep_stub
        hands._probe_dwtime = orig_probe_dwtime
        hands._clipboard_backend = orig_backend

    # ------------------------------------------------ windows + focus (#3)
    wins = [win("Alpha Editor"), win("Beta - alpha notes"), win("Gamma")]
    hands._enum_windows = lambda: wins
    activated = []
    hands._activate_window = lambda w: activated.append(w) or True

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

    # --------------------------------- windows clipboard backend (R7.2)
    # _WindowsClipboardBackend never runs off Windows, which is how
    # the data.size AttributeError shipped (#26). Fake the _setup dll
    # pair + ctypes.memmove and pin the exact call shape.
    clip_log = []

    class _FakeUser32:
        def OpenClipboard(self, arg):
            clip_log.append(("OpenClipboard", (arg,)))
            return 1

        def EmptyClipboard(self):
            clip_log.append(("EmptyClipboard", ()))
            return 1

        def SetClipboardData(self, fmt, handle):
            clip_log.append(("SetClipboardData", (fmt, handle)))
            return handle

        def CloseClipboard(self):
            clip_log.append(("CloseClipboard", ()))
            return 1

    class _FakeKernel32:
        def GlobalAlloc(self, flags, nbytes):
            clip_log.append(("GlobalAlloc", (flags, nbytes)))
            return 4242

        def GlobalLock(self, handle):
            clip_log.append(("GlobalLock", (handle,)))
            return 8192

        def GlobalUnlock(self, handle):
            clip_log.append(("GlobalUnlock", (handle,)))
            return 1

    def _fake_memmove(ptr, data, nbytes):
        clip_log.append(("memmove", (ptr, len(data), nbytes)))

    win_clip = hands._WindowsClipboardBackend()
    win_clip._setup = lambda: (_FakeUser32(), _FakeKernel32())
    clip_text = "https://www.spotify.com/account/privacy/"
    expect_nbytes = ctypes.sizeof(ctypes.create_unicode_buffer(clip_text))
    orig_memmove = ctypes.memmove
    ctypes.memmove = _fake_memmove
    try:
        win_clip.set_text(clip_text)
        clip_error = None
    except Exception as exc:  # the pre-fix AttributeError lands here
        clip_error = exc
    finally:
        ctypes.memmove = orig_memmove
    check("windows clipboard set_text runs clean against the faked dlls",
          clip_error is None)
    check("windows clipboard order open->empty->alloc->lock->move->unlock->set->close",
          [entry[0] for entry in clip_log] == [
              "OpenClipboard", "EmptyClipboard", "GlobalAlloc",
              "GlobalLock", "memmove", "GlobalUnlock",
              "SetClipboardData", "CloseClipboard"])
    by_name = {entry[0]: entry[1] for entry in clip_log}
    check("windows clipboard GlobalAlloc gets GMEM_MOVEABLE + sizeof bytes",
          by_name.get("GlobalAlloc") == (0x0002, expect_nbytes))
    check("windows clipboard memmove moves the whole buffer, byte count sizeof",
          by_name.get("memmove") == (8192, len(clip_text) + 1, expect_nbytes))
    check("windows clipboard SetClipboardData gets CF_UNICODETEXT + the handle",
          by_name.get("SetClipboardData") == (13, 4242))

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
