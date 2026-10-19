"""
Muse Relay -- let Muse drive your Windows mouse/keyboard, with your consent.

One small window. No terminals.

WHAT IT DOES
  - Starts the relay server on 127.0.0.1:5000 (localhost only -- nothing on
    your network can reach it directly).
  - Opens a Cloudflare quick tunnel and shows the URL in the window.
  - Generates a FRESH strong secret on every launch. The old workflow (one
    fixed secret, reused across sessions) is gone: when you close the app,
    that secret stops existing.
  - You paste the URL + secret to Muse in chat when you want a session.
  - Close the window (or press Stop) and everything dies instantly: server,
    tunnel, secret.

SECURITY NOTES
  - This is remote-control software. Only run it while you want Muse
    driving, and keep an eye on the screen.
  - The tunnel URL is reachable by anyone who has it -- the secret is the
    lock. The app makes the secret long and random for you; don't share the
    URL or secret with anyone but Muse.
  - The secret is compared in constant time (hmac.compare_digest), and
    failed guesses are written to the log area so you can see them. After
    10 bad guesses inside 10 minutes, authentication pauses for 5 minutes
    (lockout) -- restart the app to clear it early.
  - Served by Waitress (a production WSGI server) instead of the Flask
    development server.
  - Transport: if Tailscale is installed on this PC, the app uses
    Tailscale Serve -- the relay is then reachable only inside your
    tailnet and there is NO public URL at all. Otherwise it falls back
    to a Cloudflare quick tunnel. Responses carry X-Robots-Tag: noindex
    so tunnel URLs stay out of search indexes.
  - pyautogui.FAILSAFE is on: slam the mouse into any screen corner to
    abort the current action.

WHAT MUSE CAN DO WITH IT (unchanged from cursor_relay.py)
  GET  /health              liveness only, no secret needed
  GET  /screenshot          PNG of your screen
  GET  /monitors            monitor rectangles (virtual-desktop coords)
  POST /move    {x, y}      move the cursor
  POST /click   {x, y, button}  click
  POST /type    {text}      type text
  POST /key     {key}       press a key ("enter", "tab", "esc", ...)
  POST /scroll  {clicks}    scroll
  Every call except /health needs header  X-Secret: <the app's secret>

ADDED IN V3-P4 (wishlist #3, #4, #6, #9, #19) — same X-Secret gate:
  POST /hotkey  {keys: ["ctrl", "l"]}   press a true key chord
  POST /break   {times?: 1..3}          Ctrl+C chord(s) — see its docstring
  POST /drag    {x1, y1, x2, y2, button?, duration?}
  GET  /windows                         list open windows
  POST /focus   {title, exact?}         bring a window to the foreground
  POST /clipboard/set {text}            set the clipboard
  GET  /clipboard/get                   read the clipboard — SENSITIVE: it
                                        stays behind the X-Secret gate and
                                        every read is written to the log
                                        area (see log_line call in the
                                        route), so the operator can see
                                        reads in the app window.
  POST /type also accepts {method: "auto"|"paste"|"keys"}: long text can
  go through the clipboard (paste) instead of slow keystrokes.
CAPTURE + INPUT REALISM (v3)
  GET /screenshot?monitor=N   capture monitor N (0-based) only
  GET /screenshot?region=x,y,w,h
                               capture that rect in virtual-desktop coords
                               (monitor and region are mutually exclusive)
  /type types with per-keystroke jitter by default ({jitter: false}
  restores the old single fast write). /move and /click travel a curved,
  human-like path by default ({human: false} restores the old direct
  move). Both planners are pure functions (_plan_key_delays, _plan_path)
  so the timing/shape logic is testable without a desktop.
"""

import base64
import binascii
import ctypes
import datetime
import hashlib
import hmac
import io
import json
import math
import os
import queue
import random
import re
import secrets as secrets_mod
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import urllib.request
import uuid

import pyautogui
from flask import Flask, request, jsonify, send_file

PORT = 5000

# Fresh per launch, from the OS CSPRNG. 24 bytes -> a 32-character
# URL-safe string (~190 bits). Never stored, never reused.
SHARED_SECRET = secrets_mod.token_urlsafe(24)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.15

# ---------------------------------------------------------------- server

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1_000_000  # requests are tiny JSON

# ---- failed-guess lockout ------------------------------------------------
_fail_lock = threading.Lock()
_fail_times: list = []
_lockout_until = 0.0
MAX_FAILS = 10        # bad secrets allowed inside the window...
FAIL_WINDOW = 600     # ...of 10 minutes, then auth pauses for...
LOCKOUT_SECONDS = 300  # ...5 minutes (restart the app to clear early)


# ---- phone alerts (ntfy) + persistent security log -----------------------
_BASE_DIR = os.path.dirname(
    os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)
)
_CONFIG_PATH = os.path.join(_BASE_DIR, "muse_relay_config.json")
_LOG_FILE = os.path.join(_BASE_DIR, "muse_relay.log")


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _save_config(cfg: dict) -> None:
    try:
        with open(_CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh)
    except Exception:
        pass


_cfg = _load_config()
ALERT_TOPIC = str(_cfg.get("ntfy_topic") or "").strip()
if not ALERT_TOPIC:
    ALERT_TOPIC = "muse-relay-" + secrets_mod.token_hex(6)
    _cfg["ntfy_topic"] = ALERT_TOPIC
    _save_config(_cfg)


def file_log(message: str) -> None:
    try:
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(_LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(f"{stamp} {message}\n")
    except Exception:
        pass


def alert_phone(title: str, message: str) -> None:
    """Best-effort push to the owner's phone via ntfy.sh (topic above)."""

    def _send():
        try:
            req = urllib.request.Request(
                f"https://ntfy.sh/{ALERT_TOPIC}",
                data=message.encode("utf-8"),
                headers={"Title": title, "Tags": "warning"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()


def _auth_locked_out() -> bool:
    return time.monotonic() < _lockout_until


def _record_failure() -> None:
    global _lockout_until
    now = time.monotonic()
    file_log("bad secret attempt")
    with _fail_lock:
        _fail_times[:] = [t for t in _fail_times if now - t < FAIL_WINDOW]
        _fail_times.append(now)
        if len(_fail_times) >= MAX_FAILS:
            _lockout_until = now + LOCKOUT_SECONDS
            _fail_times.clear()
            log_line(
                "LOCKOUT: too many bad secrets -- authentication paused "
                "for 5 minutes"
            )
            file_log("LOCKOUT triggered (10 bad secrets inside 10 minutes)")
            alert_phone(
                "Muse Relay LOCKOUT",
                "Someone just made 10 bad secret guesses at your relay. "
                "Authentication is paused for 5 minutes.",
            )


@app.before_request
def gate():
    if _auth_locked_out():
        return jsonify({"ok": False, "error": "locked out"}), 429
    provided = request.headers.get("X-Secret") or ""
    if not hmac.compare_digest(provided, SHARED_SECRET):
        _record_failure()
        log_line(f"rejected request to {request.path} (bad secret)")
        return jsonify({"ok": False, "error": "bad secret"}), 401


@app.after_request
def noindex(resp):
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp


@app.get("/health")
def health():
    return {"ok": True}


# ---- capture seams ---------------------------------------------------------
# Kept as module-level functions so tests can stub the Windows layer and
# exercise the endpoint logic anywhere.


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint32),
        ("rcMonitor", _RECT),
        ("rcWork", _RECT),
        ("dwFlags", ctypes.c_uint32),
    ]


_MONITORINFOF_PRIMARY = 1


def _monitor_rects():
    """Monitor rectangles in virtual-desktop coordinates.

    Each entry: {"x", "y", "w", "h", "primary"}. Origins can be negative
    (a monitor left of / above the primary). On Windows the list comes
    from EnumDisplayMonitors; anywhere else (or on failure) it falls
    back to a single primary rect from pyautogui.size().
    """
    if os.name == "nt":
        try:
            rects = []
            user32 = ctypes.windll.user32
            enum_proc = ctypes.WINFUNCTYPE(
                ctypes.c_bool,
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.POINTER(_RECT),
                ctypes.c_ssize_t,
            )

            def _cb(hmonitor, _hdc, _clip, _data):
                info = _MONITORINFO()
                info.cbSize = ctypes.sizeof(_MONITORINFO)
                if user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
                    r = info.rcMonitor
                    rects.append(
                        {
                            "x": int(r.left),
                            "y": int(r.top),
                            "w": int(r.right - r.left),
                            "h": int(r.bottom - r.top),
                            "primary": bool(info.dwFlags & _MONITORINFOF_PRIMARY),
                        }
                    )
                return True

            if user32.EnumDisplayMonitors(None, None, enum_proc(_cb), 0) and rects:
                return rects
        except Exception:
            pass  # fall through to the single-rect fallback
    w, h = pyautogui.size()
    return [{"x": 0, "y": 0, "w": int(w), "h": int(h), "primary": True}]


def _grab(rect):
    """Capture rect ({"x","y","w","h"}) or, with None, the full frame.

    pyautogui on Windows captures the virtual desktop, so a region with
    a negative origin works through the same call.
    """
    if rect is None:
        return pyautogui.screenshot()
    return pyautogui.screenshot(
        region=(int(rect["x"]), int(rect["y"]), int(rect["w"]), int(rect["h"]))
    )


def _parse_region(raw):
    """'x,y,w,h' -> rect dict, or None if malformed / non-positive size."""
    try:
        parts = [int(p) for p in str(raw).split(",")]
    except ValueError:
        return None
    if len(parts) != 4 or parts[2] <= 0 or parts[3] <= 0:
        return None
    return {"x": parts[0], "y": parts[1], "w": parts[2], "h": parts[3]}


@app.get("/monitors")
def monitors():
    rects = _monitor_rects()
    return {"ok": True, "monitors": rects, "count": len(rects)}


@app.get("/screenshot")
def screenshot():
    monitor_raw = request.args.get("monitor")
    region_raw = request.args.get("region")
    if monitor_raw is not None and region_raw is not None:
        return jsonify({"ok": False, "error": "pass monitor or region, not both"}), 400
    rect = None
    monitor_idx = None
    region_rect = None
    if monitor_raw is not None:
        try:
            monitor_idx = int(monitor_raw)
        except ValueError:
            return jsonify({"ok": False, "error": "monitor must be an integer"}), 400
        rects = _monitor_rects()
        if monitor_idx < 0 or monitor_idx >= len(rects):
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": f"monitor {monitor_idx} out of range: "
                        f"{len(rects)} monitor(s) available",
                    }
                ),
                400,
            )
        rect = rects[monitor_idx]
    elif region_raw is not None:
        region_rect = _parse_region(region_raw)
        if region_rect is None:
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "region must be 'x,y,w,h' (ints, w and h > 0)",
                    }
                ),
                400,
            )
        rect = region_rect
    img = _grab(rect)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    resp = send_file(buf, mimetype="image/png")
    resp.headers["X-Screen-Width"] = str(img.size[0])
    resp.headers["X-Screen-Height"] = str(img.size[1])
    if monitor_idx is not None:
        resp.headers["X-Screen-Monitor"] = str(monitor_idx)
    if region_rect is not None:
        resp.headers["X-Screen-Region"] = (
            f"{region_rect['x']},{region_rect['y']},"
            f"{region_rect['w']},{region_rect['h']}"
        )
    return resp


# ---- input-realism planners (pure; rng is injected) ------------------------


def _plan_key_delays(text, rng):
    """Per-character typing delays (seconds slept AFTER each character).

    Base delay is uniform in [0.04, 0.16]; a character that ends a word
    (space) adds uniform [0.05, 0.20] and one that ends a sentence
    (. ! ?) adds uniform [0.10, 0.30]. If the total exceeds the budget
    max(5.0, len(text) * 0.16) every delay is scaled down proportionally
    so long pastes stay bounded.
    """
    delays = []
    for ch in text:
        delay = rng.uniform(0.04, 0.16)
        if ch == " ":
            delay += rng.uniform(0.05, 0.20)
        elif ch in ".!?":
            delay += rng.uniform(0.10, 0.30)
        delays.append(delay)
    budget = max(5.0, len(text) * 0.16)
    total = sum(delays)
    if total > budget and total > 0:
        scale = budget / total
        delays = [d * scale for d in delays]
    return delays


def _ease_in_out_cubic(t):
    if t < 0.5:
        return 4 * t * t * t
    return 1 - ((-2 * t + 2) ** 3) / 2


def _bezier(p0, pc, p1, t):
    u = 1 - t
    return (
        u * u * p0[0] + 2 * u * t * pc[0] + t * t * p1[0],
        u * u * p0[1] + 2 * u * t * pc[1] + t * t * p1[1],
    )


def _plan_path(x0, y0, x1, y1, rng):
    """Human-like mouse path: list of (x, y, delay_after) steps.

    Quadratic bezier from start to target, control point pushed off the
    midpoint perpendicular by up to 8% of the distance, parameter eased
    with easeInOutCubic. The first ~85% of steps aim at an overshoot
    point just past the target; the rest settle back to the EXACT
    target, which is always the final step. Total duration is
    clamp(0.25 + d/2500, 0.3, 1.1) seconds, spread evenly across steps.
    A move under 4px is a single step straight to the target.
    """
    dx, dy = x1 - x0, y1 - y0
    dist = math.hypot(dx, dy)
    total = min(1.1, max(0.3, 0.25 + dist / 2500))
    if dist < 4:
        return [(x1, y1, total)]
    n = max(8, min(60, int(dist / 12)))
    offset = rng.uniform(-0.08 * dist, 0.08 * dist)
    ctrl = (
        (x0 + x1) / 2 + (-dy / dist) * offset,
        (y0 + y1) / 2 + (dx / dist) * offset,
    )
    # Overshoot: extend past the target along the bezier's final
    # direction (target - control point).
    fx, fy = x1 - ctrl[0], y1 - ctrl[1]
    flen = math.hypot(fx, fy)
    if flen == 0:
        fx, fy, flen = dx, dy, dist
    over = min(6.0, 0.02 * dist)
    over_pt = (x1 + fx / flen * over, y1 + fy / flen * over)

    n_over = max(1, int(round(n * 0.85)))
    if n_over >= n:
        n_over = n - 1
    points = []
    for i in range(1, n_over + 1):
        t = _ease_in_out_cubic(i / n_over)
        points.append(_bezier((x0, y0), ctrl, over_pt, t))
    n_settle = n - n_over
    for j in range(1, n_settle + 1):
        s = j / n_settle
        points.append(
            (over_pt[0] + (x1 - over_pt[0]) * s, over_pt[1] + (y1 - over_pt[1]) * s)
        )
    points[-1] = (x1, y1)  # exact target, always
    per = total / n
    steps = [(px, py, per) for (px, py) in points]
    # Pin the delay sum to the planned total despite float rounding.
    steps[-1] = (steps[-1][0], steps[-1][1], total - per * (n - 1))
    return steps


def _move_human(x, y, rng=None):
    """Move the cursor to (x, y) along a planned human-like path."""
    rng = rng if rng is not None else random
    x0, y0 = pyautogui.position()
    for sx, sy, delay in _plan_path(x0, y0, x, y, rng):
        pyautogui.moveTo(sx, sy, duration=0)
        time.sleep(delay)


@app.post("/move")
def move():
    d = request.get_json(force=True)
    x, y = int(d["x"]), int(d["y"])
    if d.get("human", True):
        _move_human(x, y)
    else:
        pyautogui.moveTo(x, y, duration=0.2)
    return {"ok": True}


@app.post("/click")
def click():
    d = request.get_json(force=True)
    x, y = int(d["x"]), int(d["y"])
    button = d.get("button", "left")
    if d.get("human", True):
        _move_human(x, y)
        time.sleep(random.uniform(0.05, 0.15))  # hover before the click
    else:
        pyautogui.moveTo(x, y, duration=0.2)
    pyautogui.click(x=x, y=y, button=button)
    return {"ok": True}


@app.post("/type")
def type_text():
    """Type text: clipboard paste for long payloads, jittered keys else.

    {text, method?: "auto"|"paste"|"keys", jitter?: bool}

    Method (wishlist #9): "auto" pastes when the text is over 120 chars
    and a clipboard backend exists — the paste path saves the current
    clipboard and restores it afterwards; "paste" forces that path;
    "keys" forces keystrokes. Any clipboard failure falls back to
    keystrokes instead of failing the request (see "note").

    Jitter (wishlist #16): the keystroke path types per character with
    human-band delays from _plan_key_delays unless jitter is false —
    false restores the original single pyautogui.write(interval=0.02).

    Response: {"ok", "method_used", "chars", "elapsed_seconds",
    "delays_planned", "planned_seconds"} — the delay fields describe the
    keystroke plan (0 on the paste path).
    """
    d = request.get_json(force=True, silent=True) or {}
    text = d.get("text")
    if not isinstance(text, str):
        return jsonify({"ok": False, "error": "text must be a string"}), 400
    method = d.get("method", "auto")
    if method not in ("auto", "paste", "keys"):
        return jsonify({"ok": False, "error": "method must be auto, paste or keys"}), 400
    jitter = bool(d.get("jitter", True))
    started = time.monotonic()
    note = None
    delays = []

    def _keys():
        nonlocal delays
        if jitter:
            delays = _plan_key_delays(text, random)
            for ch, delay in zip(text, delays):
                pyautogui.write(ch)
                time.sleep(delay)
        else:
            pyautogui.write(text, interval=0.02)
        return "keys"

    def _paste():
        backend = _clipboard_backend()
        if backend is None:
            raise RuntimeError("clipboard unavailable on this host")
        saved, readable = None, False
        try:
            saved = backend.get_text()
            readable = True
        except Exception:
            pass  # unreadable clipboard: paste anyway, skip the restore
        backend.set_text(text)
        pyautogui.hotkey("ctrl", "v")
        if readable and saved is not None:
            # Give the target app a beat to consume the paste before the
            # previous clipboard contents go back.
            time.sleep(0.1)
            try:
                backend.set_text(saved)
            except Exception:
                pass
        return "paste"

    if method == "keys":
        method_used = _keys()
    elif method == "paste":
        try:
            method_used = _paste()
        except Exception as exc:
            note = f"paste requested but unavailable ({exc}); used keys"
            method_used = _keys()
    else:  # auto
        if len(text) > 120 and _clipboard_backend() is not None:
            try:
                method_used = _paste()
            except Exception as exc:
                note = f"paste failed ({exc}); used keys"
                method_used = _keys()
        else:
            method_used = _keys()
    resp = {
        "ok": True,
        "method_used": method_used,
        "chars": len(text),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "delays_planned": len(delays),
        "planned_seconds": sum(delays),
    }
    if note:
        resp["note"] = note
    return jsonify(resp)
@app.post("/key")
def key():
    d = request.get_json(force=True)
    pyautogui.press(d["key"])
    return {"ok": True}


@app.post("/scroll")
def scroll():
    d = request.get_json(force=True)
    pyautogui.scroll(int(d.get("clicks", 3)))
    return {"ok": True}


# ---- window titles (wishlist #5) ------------------------------------------

@app.get("/window_titles")
def window_titles():
    try:
        titles = pyautogui.getAllTitles()
    except Exception:
        titles = []
    return {"ok": True, "titles": list(titles) if titles else []}


# ---- lock / idle state (wishlist #13) --------------------------------------

def _probe_lock_state():
    """Probe (locked, idle_seconds) on Windows; (None, None) elsewhere.

    Never raises: any failure returns None for the affected value. The
    Windows calls live here so tests can monkeypatch this one function.
    """
    if os.name != "nt":
        return (None, None)
    locked = None
    idle_seconds = None
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        # Locked check: the input desktop is the Winlogon desktop when locked.
        try:
            handle = user32.OpenInputDesktop(0, False, 0x0100)
            if handle:
                try:
                    buf = ctypes.create_unicode_buffer(256)
                    needed = ctypes.c_ulong(0)
                    if user32.GetUserObjectInformationW(
                        handle, 2, buf, ctypes.sizeof(buf), ctypes.byref(needed)
                    ):
                        locked = buf.value.lower() == "winlogon"
                finally:
                    try:
                        user32.CloseDesktop(handle)
                    except Exception:
                        pass
        except Exception:
            locked = None
        # Idle check: time since last input.
        try:
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

            class _LastInputInfo(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_ulong)]

            info = _LastInputInfo()
            info.cbSize = ctypes.sizeof(_LastInputInfo)
            if user32.GetLastInputInfo(ctypes.byref(info)):
                tick = kernel32.GetTickCount()
                idle_ms = (int(tick) - int(info.dwTime)) & 0xFFFFFFFF
                idle_seconds = idle_ms / 1000.0
        except Exception:
            idle_seconds = None
    except Exception:
        return (locked, idle_seconds)
    return (locked, idle_seconds)


@app.get("/state")
def state():
    platform = "windows" if os.name == "nt" else "other"
    try:
        locked, idle_seconds = _probe_lock_state()
    except Exception:
        locked, idle_seconds = None, None
    return {"ok": True, "platform": platform, "locked": locked, "idle_seconds": idle_seconds}


# ---- file-drop (wishlist #2) ------------------------------------------------
# Allowlist: folders from the hands config file key "filedrop_dirs" (list
# of absolute paths) OR env HANDS_FILEDROP_DIRS (os.pathsep-separated) —
# env wins if set. Default empty -> every filedrop endpoint returns 501.
# File contents are never logged.

_FILEDROP_CHUNK_MAX = 524288
_FILEDROP_MAX_SIZE = 16 * 1024 * 1024
_FILEDROP_TTL = 600  # uploads older than 10 minutes are purged lazily

_uploads: dict = {}
_uploads_lock = threading.Lock()


def _filedrop_dirs():
    env = os.environ.get("HANDS_FILEDROP_DIRS")
    if env is not None:
        if not env.strip():
            return []
        return [os.path.realpath(p) for p in env.split(os.pathsep) if p]
    cfg = _load_config()
    dirs = cfg.get("filedrop_dirs") if isinstance(cfg, dict) else None
    if not isinstance(dirs, list):
        return []
    return [os.path.realpath(str(p)) for p in dirs if str(p)]


def _purge_uploads():
    now = time.time()
    with _uploads_lock:
        stale = [uid for uid, up in _uploads.items() if now - up["created_at"] > _FILEDROP_TTL]
        for uid in stale:
            del _uploads[uid]


def _filedrop_gate():
    """Shared preamble: purge stale uploads, enforce configuration."""
    _purge_uploads()
    if not _filedrop_dirs():
        return (jsonify({"ok": False, "error": "file-drop not configured on the hands"}), 501)
    return None


@app.post("/filedrop/begin")
def filedrop_begin():
    gate_resp = _filedrop_gate()
    if gate_resp is not None:
        return gate_resp
    body = request.get_json(force=True, silent=True) or {}
    folder = body.get("folder")
    filename = body.get("filename")
    size = body.get("size")
    sha256 = body.get("sha256")
    if not isinstance(folder, str) or not folder:
        return jsonify({"ok": False, "error": "folder required"}), 400
    real_folder = os.path.realpath(folder)
    if real_folder not in _filedrop_dirs():
        return jsonify({"ok": False, "error": "folder not in file-drop allowlist"}), 403
    if (
        not isinstance(filename, str)
        or not filename
        or "/" in filename
        or "\\" in filename
        or ".." in filename
    ):
        return jsonify({"ok": False, "error": "filename must be a bare name"}), 400
    if isinstance(size, bool) or not isinstance(size, int) or size < 1 or size > _FILEDROP_MAX_SIZE:
        return jsonify({"ok": False, "error": "size must be an integer in 1..16MB"}), 400
    if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", sha256):
        return jsonify({"ok": False, "error": "sha256 must be a 64-hex string"}), 400
    upload_id = uuid.uuid4().hex
    with _uploads_lock:
        _uploads[upload_id] = {
            "id": upload_id,
            "dir": real_folder,
            "filename": filename,
            "size": size,
            "sha256": sha256.lower(),
            "buffer": bytearray(),
            "created_at": time.time(),
        }
    return jsonify({"ok": True, "upload_id": upload_id, "chunk_max": _FILEDROP_CHUNK_MAX})


@app.post("/filedrop/chunk")
def filedrop_chunk():
    gate_resp = _filedrop_gate()
    if gate_resp is not None:
        return gate_resp
    body = request.get_json(force=True, silent=True) or {}
    upload_id = body.get("upload_id")
    offset = body.get("offset")
    data_b64 = body.get("data_b64")
    with _uploads_lock:
        upload = _uploads.get(upload_id)
    if upload is None:
        return jsonify({"ok": False, "error": "unknown upload_id"}), 404
    expected = len(upload["buffer"])
    if isinstance(offset, bool) or not isinstance(offset, int) or offset != expected:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "offset mismatch",
                    "expected_offset": expected,
                    "expected": expected,
                }
            ),
            409,
        )
    if not isinstance(data_b64, str):
        return jsonify({"ok": False, "error": "data_b64 required"}), 400
    try:
        chunk = base64.b64decode(data_b64, validate=True)
    except (binascii.Error, ValueError):
        return jsonify({"ok": False, "error": "data_b64 is not valid base64"}), 400
    if expected + len(chunk) > upload["size"]:
        return jsonify({"ok": False, "error": "chunk exceeds declared size"}), 400
    with _uploads_lock:
        # Re-check under lock in case a concurrent call appended.
        if len(upload["buffer"]) != expected:
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "offset mismatch",
                        "expected_offset": len(upload["buffer"]),
                        "expected": len(upload["buffer"]),
                    }
                ),
                409,
            )
        upload["buffer"].extend(chunk)
        received = len(upload["buffer"])
    return jsonify({"ok": True, "received": received, "offset": received})


@app.post("/filedrop/commit")
def filedrop_commit():
    gate_resp = _filedrop_gate()
    if gate_resp is not None:
        return gate_resp
    body = request.get_json(force=True, silent=True) or {}
    upload_id = body.get("upload_id")
    with _uploads_lock:
        upload = _uploads.get(upload_id)
    if upload is None:
        return jsonify({"ok": False, "error": "unknown upload_id"}), 404
    data = bytes(upload["buffer"])
    if len(data) != upload["size"]:
        return jsonify({"ok": False, "error": "incomplete upload: size mismatch"}), 400
    digest = hashlib.sha256(data).hexdigest()
    if digest != upload["sha256"]:
        with _uploads_lock:
            _uploads.pop(upload_id, None)
        return jsonify({"ok": False, "error": "sha256 mismatch"}), 400
    final_path = os.path.join(upload["dir"], upload["filename"])
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=upload["dir"], prefix=".filedrop-", suffix=".tmp")
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp_path, final_path)
        tmp_path = None
    except OSError as exc:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return jsonify({"ok": False, "error": f"write failed: {exc}"}), 500
    with _uploads_lock:
        _uploads.pop(upload_id, None)
    return jsonify({"ok": True, "path": final_path, "size": len(data), "sha256": digest})


@app.post("/filedrop/abort")
def filedrop_abort():
    gate_resp = _filedrop_gate()
    if gate_resp is not None:
        return gate_resp
    body = request.get_json(force=True, silent=True) or {}
    upload_id = body.get("upload_id")
    with _uploads_lock:
        existed = _uploads.pop(upload_id, None) is not None
    if not existed:
        return jsonify({"ok": False, "error": "unknown upload_id"}), 404
    return jsonify({"ok": True})
# ------------------------------------------------- V3-P4: chords + break

@app.post("/hotkey")
def hotkey():
    """Press a true key chord, e.g. {"keys": ["ctrl", "l"]}."""
    d = request.get_json(force=True, silent=True) or {}
    keys = d.get("keys")
    if (
        not isinstance(keys, list)
        or not keys
        or not all(isinstance(k, str) and k.strip() for k in keys)
    ):
        return jsonify({"ok": False, "error": "keys must be a non-empty list of strings"}), 400
    pyautogui.hotkey(*keys)
    return {"ok": True}


@app.post("/break")
def break_():
    """Send Ctrl+C as a true chord, 1..3 times (default 1), 0.15s apart.

    Root cause this fixes: the /key op calls pyautogui.press() with ONE
    key name, so sending the string "ctrl+c" to /key was never a real
    chord — press() treats it as a single (nonexistent) key name and
    nothing was interrupted. A long-running / polling foreground process
    therefore could not be stopped through the relay. /break (and
    /hotkey) use pyautogui.hotkey(), which presses the keys together,
    so the interrupt actually lands.
    """
    d = request.get_json(force=True, silent=True) or {}
    times = d.get("times", 1)
    if isinstance(times, bool) or not isinstance(times, int) or not 1 <= times <= 3:
        return jsonify({"ok": False, "error": "times must be an integer 1..3"}), 400
    for i in range(times):
        pyautogui.hotkey("ctrl", "c")
        if i < times - 1:
            time.sleep(0.15)
    return {"ok": True, "times": times}


# ------------------------------------------------------- V3-P4: dragging

@app.post("/drag")
def drag():
    """Press the mouse button at (x1, y1), drag to (x2, y2), release."""
    d = request.get_json(force=True, silent=True) or {}
    try:
        x1, y1, x2, y2 = (int(d[k]) for k in ("x1", "y1", "x2", "y2"))
    except (KeyError, TypeError, ValueError):
        return jsonify({"ok": False, "error": "x1, y1, x2, y2 must be integers"}), 400
    button = d.get("button", "left")
    if button not in ("left", "middle", "right"):
        return jsonify({"ok": False, "error": "button must be left, middle or right"}), 400
    try:
        duration = float(d["duration"]) if d.get("duration") is not None else 0.4
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "duration must be a number"}), 400
    pyautogui.moveTo(x1, y1)
    pyautogui.mouseDown(button=button)
    pyautogui.moveTo(x2, y2, duration=duration or 0.4)
    pyautogui.mouseUp(button=button)
    return {"ok": True}


# ------------------------------------------- V3-P4: windows + focus (#3)

def _monitor_for_bounds(bounds, rects=None):
    """Index of the monitor rect containing the window's centre, else None."""
    if rects is None:
        rects = _monitor_rects()
    cx = bounds["x"] + bounds["w"] / 2
    cy = bounds["y"] + bounds["h"] / 2
    for i, r in enumerate(rects):
        if r["x"] <= cx < r["x"] + r["w"] and r["y"] <= cy < r["y"] + r["h"]:
            return i
    return None


def _process_name(pid):
    """Process image basename for a pid, or None — never raises."""
    if not pid:
        return None
    try:
        import psutil

        return psutil.Process(int(pid)).name() or None
    except Exception:
        pass
    if os.name != "nt":
        return None
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.QueryFullProcessImageNameW.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_wchar), ctypes.POINTER(ctypes.c_ulong),
        ]
        handle = kernel32.OpenProcess(0x1000, False, int(pid))  # QUERY_LIMITED
        if not handle:
            return None
        try:
            size = ctypes.c_ulong(1024)
            buf = ctypes.create_unicode_buffer(size.value)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                return os.path.basename(buf.value) or None
            return None
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return None


def _enum_windows():
    """Raw open-window dicts (the seam tests stub).

    Each dict carries title/process/pid/bounds/monitor/visible/focused
    plus a private "_hwnd" on Windows for _activate_window(). Returns []
    off Windows. Falls back to pyautogui.getAllWindows() (process/pid
    null) when pywin32 is unavailable.
    """
    if os.name != "nt":
        return []
    rects = _monitor_rects()
    try:
        import win32gui
        import win32process
    except Exception:
        wins = []
        try:
            for w in pyautogui.getAllWindows():
                title = getattr(w, "title", "") or ""
                if not title:
                    continue
                bounds = {
                    "x": int(getattr(w, "left", 0) or 0),
                    "y": int(getattr(w, "top", 0) or 0),
                    "w": int(getattr(w, "width", 0) or 0),
                    "h": int(getattr(w, "height", 0) or 0),
                }
                wins.append({
                    "title": title, "process": None, "pid": None,
                    "bounds": bounds,
                    "monitor": _monitor_for_bounds(bounds, rects),
                    "visible": bool(getattr(w, "visible", True)),
                    "focused": bool(getattr(w, "isActive", False)),
                    "_window": w,
                })
        except Exception:
            return []
        return wins
    wins = []
    try:
        foreground = win32gui.GetForegroundWindow()
    except Exception:
        foreground = None

    def _cb(hwnd, _extra):
        try:
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return True
            x, y, x2, y2 = win32gui.GetWindowRect(hwnd)
            bounds = {"x": int(x), "y": int(y), "w": int(x2 - x), "h": int(y2 - y)}
            try:
                _tid, pid = win32process.GetWindowThreadProcessId(hwnd)
            except Exception:
                pid = None
            wins.append({
                "title": title,
                "process": _process_name(pid),
                "pid": int(pid) if pid else None,
                "bounds": bounds,
                "monitor": _monitor_for_bounds(bounds, rects),
                "visible": bool(win32gui.IsWindowVisible(hwnd)),
                "focused": hwnd == foreground,
                "_hwnd": hwnd,
            })
        except Exception:
            pass
        return True

    try:
        win32gui.EnumWindows(_cb, None)
    except Exception:
        return wins
    return wins


def _shape_window(win):
    """Raw _enum_windows() dict -> the public window shape."""
    b = win.get("bounds") or {}
    return {
        "title": win.get("title") or "",
        "process": win.get("process"),
        "pid": win.get("pid"),
        "bounds": {
            "x": int(b.get("x", 0)), "y": int(b.get("y", 0)),
            "w": int(b.get("w", 0)), "h": int(b.get("h", 0)),
        },
        "monitor": win.get("monitor"),
        "visible": bool(win.get("visible", True)),
        "focused": bool(win.get("focused", False)),
    }


def _windows_supported():
    return os.name == "nt"


def _activate_window(win):
    """Bring one raw window dict to the foreground (the seam tests stub).

    On Windows: restore first if minimised, then SetForegroundWindow.
    The well-known foreground-lock workaround (AttachThreadInput) is
    deliberately out of scope here — see docs/VERIFICATION.md.
    """
    if os.name != "nt":
        return
    try:
        import win32con
        import win32gui

        hwnd = win.get("_hwnd")
        if hwnd is None:
            fallback = win.get("_window")
            if fallback is not None:
                try:
                    if getattr(fallback, "isMinimized", False):
                        fallback.restore()
                    fallback.activate()
                except Exception:
                    pass
            return
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass  # best effort: foreground lock can refuse; caller still matched


@app.get("/windows")
def windows():
    raw = _enum_windows()
    resp = {"ok": True, "windows": [_shape_window(w) for w in raw]}
    if not _windows_supported() and not raw:
        resp["supported"] = False
    return jsonify(resp)


@app.post("/focus")
def focus():
    """Focus the first window whose title matches {title}.

    Substring, case-insensitive by default; exact=true requires a full
    (case-insensitive) title match. No match -> 404.
    """
    d = request.get_json(force=True, silent=True) or {}
    title = d.get("title")
    if not isinstance(title, str) or not title.strip():
        return jsonify({"ok": False, "error": "title must be a non-empty string"}), 400
    exact = bool(d.get("exact", False))
    needle = title.casefold()
    for win in _enum_windows():
        candidate = (win.get("title") or "").casefold()
        matched = candidate == needle if exact else needle in candidate
        if matched:
            _activate_window(win)
            return jsonify({"ok": True, "window": _shape_window(win)})
    return jsonify({"ok": False, "error": f"no window matching {title!r}"}), 404


# ---------------------------------------------- V3-P4: clipboard (#6)

CF_UNICODETEXT = 13


class _WindowsClipboardBackend:
    """Clipboard via ctypes user32/kernel32 (CF_UNICODETEXT)."""

    def _setup(self):
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        user32.GetClipboardData.restype = ctypes.c_void_p
        user32.SetClipboardData.restype = ctypes.c_void_p
        user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
        kernel32.GlobalAlloc.restype = ctypes.c_void_p
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        return user32, kernel32

    def get_text(self):
        user32, kernel32 = self._setup()
        if not user32.OpenClipboard(None):
            raise OSError("OpenClipboard failed")
        try:
            handle = user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return ""
            ptr = kernel32.GlobalLock(handle)
            if not ptr:
                return ""
            try:
                return ctypes.wstring_at(ptr)
            finally:
                kernel32.GlobalUnlock(handle)
        finally:
            user32.CloseClipboard()

    def set_text(self, text):
        user32, kernel32 = self._setup()
        data = ctypes.create_unicode_buffer(text)
        if not user32.OpenClipboard(None):
            raise OSError("OpenClipboard failed")
        try:
            user32.EmptyClipboard()
            handle = kernel32.GlobalAlloc(0x0002, data.size)  # GMEM_MOVEABLE
            if not handle:
                raise OSError("GlobalAlloc failed")
            ptr = kernel32.GlobalLock(handle)
            if not ptr:
                raise OSError("GlobalLock failed")
            try:
                ctypes.memmove(ptr, data, data.size)
            finally:
                kernel32.GlobalUnlock(handle)
            if not user32.SetClipboardData(CF_UNICODETEXT, handle):
                raise OSError("SetClipboardData failed")
        finally:
            user32.CloseClipboard()


class _PyperclipBackend:
    def __init__(self, mod):
        self._mod = mod

    def get_text(self):
        return self._mod.paste() or ""

    def set_text(self, text):
        self._mod.copy(text)


def _clipboard_backend():
    """Clipboard backend seam: Windows ctypes, else pyperclip, else None."""
    if os.name == "nt":
        return _WindowsClipboardBackend()
    try:
        import pyperclip

        return _PyperclipBackend(pyperclip)
    except Exception:
        return None


@app.post("/clipboard/set")
def clipboard_set():
    d = request.get_json(force=True, silent=True) or {}
    text = d.get("text")
    if not isinstance(text, str):
        return jsonify({"ok": False, "error": "text must be a string"}), 400
    backend = _clipboard_backend()
    if backend is None:
        return jsonify({"ok": False, "error": "clipboard unavailable on this host"}), 501
    try:
        backend.set_text(text)
    except Exception as exc:
        return jsonify({"ok": False, "error": f"clipboard set failed: {exc}"}), 502
    return {"ok": True}


@app.get("/clipboard/get")
def clipboard_get():
    """Read the clipboard. Sensitive: same X-Secret gate as every hands
    route, and every read is logged (below) so the operator sees it in
    the app window's log area."""
    backend = _clipboard_backend()
    if backend is None:
        return jsonify({"ok": False, "error": "clipboard unavailable on this host"}), 501
    try:
        text = backend.get_text()
    except Exception as exc:
        return jsonify({"ok": False, "error": f"clipboard read failed: {exc}"}), 502
    log_line("clipboard read via relay")
    return jsonify({"ok": True, "text": text if isinstance(text, str) else ""})
# ---- elevation bridge ----------------------------------------------------
# The agent may only NAME a request from the operator's pre-configured
# allowlist (hands config file key "elevate_allowlist":
# {name: {"exe": "...", "args": "..."}} — static strings from the
# operator's config, never from the request). Nothing runs from here:
# the request is queued for the app window, and only the person at the
# PC clicking Approve there resolves it (via _resolve_elevation). There
# is deliberately no auto-approve path, no timeout-approve, and no
# config flag that approves.

ELEVATE_TTL_SECONDS = 120

elevate_queue: "queue.Queue[dict]" = queue.Queue()
_elevations: dict = {}
_elevations_lock = threading.Lock()


def _elevate_allowlist() -> dict:
    """The operator-configured elevation allowlist (name -> exe/args)."""
    try:
        allow = _cfg.get("elevate_allowlist") if isinstance(_cfg, dict) else None
    except Exception:
        return {}
    return allow if isinstance(allow, dict) else {}


def _run_elevated(entry) -> bool:
    """Windows seam: launch entry's exe/args elevated via UAC (runas).

    Returns True only when ShellExecuteW reports success (> 32).
    Off-Windows or on any error, returns False.
    """
    if os.name != "nt":
        return False
    try:
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", entry.get("exe") or "", entry.get("args") or None, None, 1
        )
        return bool(result and result > 32)
    except Exception:
        return False


def _expire_if_stale(entry) -> None:
    if entry.get("state") == "pending" and (
        time.time() - float(entry.get("created_at") or 0) > ELEVATE_TTL_SECONDS
    ):
        entry["state"] = "expired"


def _resolve_elevation(eid, approved) -> bool:
    """Resolve a pending request. Called only by the app's dialog.

    Returns True when a pending request was resolved, False for an
    unknown or already-resolved/expired id (no-op).
    """
    with _elevations_lock:
        entry = _elevations.get(eid)
        if entry is None or entry.get("state") != "pending":
            return False
        _expire_if_stale(entry)
        if entry.get("state") != "pending":
            return False
        if not approved:
            entry["state"] = "denied"
            return True
        try:
            launched = bool(_run_elevated(entry))
        except Exception:
            launched = False
        entry["state"] = "launched" if launched else "launch_failed"
        return True


@app.post("/elevate")
def elevate():
    d = request.get_json(force=True, silent=True) or {}
    name = d.get("name") or ""
    allow = _elevate_allowlist()
    if not allow:
        return jsonify({"ok": False, "error": "elevation not configured"}), 501
    spec_entry = allow.get(name)
    if not isinstance(spec_entry, dict):
        return jsonify({"ok": False, "error": "unknown elevation name"}), 404
    eid = uuid.uuid4().hex
    entry = {
        "id": eid,
        "name": name,
        "exe": str(spec_entry.get("exe") or ""),
        "args": str(spec_entry.get("args") or ""),
        "state": "pending",
        "created_at": time.time(),
    }
    with _elevations_lock:
        _elevations[eid] = entry
    elevate_queue.put(dict(entry))
    return jsonify({"ok": True, "id": eid, "state": "pending"})


@app.get("/elevate/<eid>")
def elevate_status(eid):
    with _elevations_lock:
        entry = _elevations.get(eid)
        if entry is None:
            return jsonify({"ok": False, "error": "unknown elevation id"}), 404
        _expire_if_stale(entry)
        return jsonify(
            {
                "ok": True,
                "id": entry["id"],
                "name": entry["name"],
                "state": entry["state"],
            }
        )


# ---------------------------------------------------------------- UI glue

log_queue: "queue.Queue[str]" = queue.Queue()
url_queue: "queue.Queue[str]" = queue.Queue()

URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def log_line(text: str) -> None:
    log_queue.put(text)


class RelayApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.server = None
        self.tunnel_proc = None
        self.transport = None
        self.stopping = False

        root.title("Muse Relay")
        root.resizable(False, False)
        self._set_icon()

        pad = {"padx": 10, "pady": 4}
        self.status = tk.StringVar(value="Starting…")
        tk.Label(root, textvariable=self.status, font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", **pad
        )

        tk.Label(root, text="Tunnel URL:").grid(row=1, column=0, sticky="e", **pad)
        self.url_var = tk.StringVar(value="(waiting for cloudflared…)")
        tk.Entry(root, textvariable=self.url_var, width=52, state="readonly").grid(
            row=1, column=1, **pad
        )
        tk.Button(root, text="Copy", command=lambda: self._copy(self.url_var.get())).grid(
            row=1, column=2, **pad
        )

        tk.Label(root, text="Secret:").grid(row=2, column=0, sticky="e", **pad)
        self.secret_var = tk.StringVar(value=SHARED_SECRET)
        tk.Entry(root, textvariable=self.secret_var, width=52, state="readonly").grid(
            row=2, column=1, **pad
        )
        tk.Button(
            root, text="Copy", command=lambda: self._copy(self.secret_var.get())
        ).grid(row=2, column=2, **pad)

        tk.Label(root, text="Alert topic (ntfy):").grid(row=3, column=0, sticky="e", **pad)
        self.topic_var = tk.StringVar(value=ALERT_TOPIC)
        topic_entry = tk.Entry(root, textvariable=self.topic_var, width=52)
        topic_entry.grid(row=3, column=1, **pad)
        topic_entry.bind("<FocusOut>", self._save_topic)
        topic_entry.bind("<Return>", self._save_topic)
        tk.Label(root, text="phone alerts").grid(row=3, column=2, **pad)

        tk.Label(
            root,
            text="Paste the URL and the secret to Muse to start a session.\n"
            "Closing this window ends the session and destroys the secret.",
            justify="left",
            fg="#555",
        ).grid(row=4, column=0, columnspan=3, sticky="w", **pad)

        self.log = tk.Text(root, width=78, height=8, state="disabled")
        self.log.grid(row=5, column=0, columnspan=3, **pad)

        tk.Button(root, text="Stop and close", command=self.shutdown).grid(
            row=6, column=0, columnspan=3, pady=8
        )
        root.protocol("WM_DELETE_WINDOW", self.shutdown)

        if os.name == "nt":
            try:
                # ES_CONTINUOUS | ES_SYSTEM_REQUIRED: stay reachable while away
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
                log_line("keeping this PC awake while the relay runs")
            except Exception:
                pass
        log_line(f"phone alerts: subscribe to ntfy topic '{ALERT_TOPIC}' on your phone")
        log_line(f"session secret generated ({len(SHARED_SECRET)} chars)")

        threading.Thread(target=self._run_server, daemon=True).start()
        threading.Thread(target=self._run_tunnel, daemon=True).start()
        self._poll()

    def _set_icon(self):
        try:
            base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
            icon = os.path.join(base, "muse.ico")
            if os.path.exists(icon):
                self.root.iconbitmap(icon)
        except Exception:
            pass  # icon is decoration; never let it block startup

    def _save_topic(self, _event=None):
        global ALERT_TOPIC
        topic = self.topic_var.get().strip()
        if topic and topic != ALERT_TOPIC:
            ALERT_TOPIC = topic
            cfg = _load_config()
            cfg["ntfy_topic"] = topic
            _save_config(cfg)
            log_line(f"phone alert topic set to {topic}")

    def _copy(self, text: str):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def _run_server(self):
        try:
            try:
                from waitress import create_server

                self.server = create_server(app, host="127.0.0.1", port=PORT, threads=8)
                log_line(f"relay server (Waitress) listening on 127.0.0.1:{PORT}")
                self.server.run()
            except ImportError:
                from werkzeug.serving import make_server

                self.server = make_server("127.0.0.1", PORT, app, threaded=True)
                log_line(
                    f"relay server (Werkzeug fallback) listening on 127.0.0.1:{PORT}"
                )
                self.server.serve_forever()
        except Exception as exc:  # e.g. port already in use
            log_line(f"SERVER ERROR: {exc}")

    def _run_tunnel(self):
        flags = 0
        if os.name == "nt":
            flags = subprocess.CREATE_NO_WINDOW
        # Preferred transport: Tailscale Serve -- tailnet only, no public URL.
        ts = shutil.which("tailscale")
        if ts:
            try:
                subprocess.run(
                    [ts, "serve", "--bg", str(PORT)],
                    capture_output=True,
                    text=True,
                    creationflags=flags,
                    timeout=30,
                )
                out = subprocess.run(
                    [ts, "status", "--json"],
                    capture_output=True,
                    text=True,
                    creationflags=flags,
                    timeout=30,
                ).stdout
                dns = json.loads(out)["Self"]["DNSName"].rstrip(".")
                self.transport = "tailscale"
                url_queue.put(f"https://{dns}")
                log_line("transport: Tailscale Serve (tailnet only, no public URL)")
                return
            except Exception as exc:
                log_line(f"Tailscale Serve failed ({exc}); falling back to Cloudflare")
        # Fallback transport: Cloudflare quick tunnel (public URL).
        exe = shutil.which("cloudflared")
        if not exe:
            log_line(
                "cloudflared not found on PATH. Install it with: "
                "winget install cloudflare.cloudflared"
            )
            return
        try:
            self.tunnel_proc = subprocess.Popen(
                [exe, "tunnel", "--url", f"http://127.0.0.1:{PORT}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=flags,
            )
            for line in self.tunnel_proc.stdout:
                m = URL_RE.search(line)
                if m:
                    url_queue.put(m.group(0))
        except Exception as exc:
            log_line(f"TUNNEL ERROR: {exc}")

    def _poll(self):
        try:
            while True:
                self._append_log(log_queue.get_nowait())
        except queue.Empty:
            pass
        try:
            while True:
                url = url_queue.get_nowait()
                self.url_var.set(url)
                self.status.set("Running — paste the URL and secret to Muse")
                self._append_log(f"tunnel is up: {url}")
        except queue.Empty:
            pass
        if not self.stopping:
            self.root.after(200, self._poll)

    def _append_log(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", text.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def shutdown(self):
        self.stopping = True
        try:
            if self.transport == "tailscale":
                ts = shutil.which("tailscale")
                if ts:
                    subprocess.run(
                        [ts, "serve", "reset"],
                        capture_output=True,
                        timeout=15,
                    )
            if self.tunnel_proc is not None:
                self.tunnel_proc.terminate()
        except Exception:
            pass
        if os.name == "nt":
            try:
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            except Exception:
                pass
        self.root.destroy()
        os._exit(0)  # server threads are daemons; exit ends them too


def main():
    root = tk.Tk()
    RelayApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
