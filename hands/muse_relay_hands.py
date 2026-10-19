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
  POST /move    {x, y}      move the cursor
  POST /click   {x, y, button}  click
  POST /type    {text}      type text
  POST /key     {key}       press a key ("enter", "tab", "esc", ...)
  POST /scroll  {clicks}    scroll
  Every call except /health needs header  X-Secret: <the app's secret>
"""

import base64
import binascii
import ctypes
import datetime
import hashlib
import hmac
import io
import json
import os
import queue
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


@app.get("/screenshot")
def screenshot():
    img = pyautogui.screenshot()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    resp = send_file(buf, mimetype="image/png")
    resp.headers["X-Screen-Width"] = str(img.size[0])
    resp.headers["X-Screen-Height"] = str(img.size[1])
    return resp


@app.post("/move")
def move():
    d = request.get_json(force=True)
    pyautogui.moveTo(int(d["x"]), int(d["y"]), duration=0.2)
    return {"ok": True}


@app.post("/click")
def click():
    d = request.get_json(force=True)
    pyautogui.click(x=int(d["x"]), y=int(d["y"]), button=d.get("button", "left"))
    return {"ok": True}


@app.post("/type")
def type_text():
    d = request.get_json(force=True)
    pyautogui.write(d["text"], interval=0.02)
    return {"ok": True}


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
