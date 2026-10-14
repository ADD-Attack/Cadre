"""Muse Relay v2 — packaged single-window app (Windows).

One icon, one button: the window opens idle, and pressing Start brings
up all three relay services in this one process —

  * hands   on 127.0.0.1:5000  (hands/muse_relay_hands.py, headless: no
    separate window, no tunnel — localhost only, as designed)
  * gateway on :5010           (the agent-facing API)
  * parser  on :5011           (screen parsing)

The status lines show each service; the log shows what happened.

Secrets:
  * The gateway token is minted fresh for every launch and shown in the
    window with a Copy button; it is never saved anywhere.
  * The hands secret is owned by this app and persists per machine at
    %USERPROFILE%\\.muse-relay-v2\\hands-secret.txt — generated on first
    run, reused after that (delete the file to rotate). It is never
    logged or displayed. The app hands the same value to the gateway
    and to the in-process hands, which is the whole point of bundling
    them: gateway and hands can no longer disagree about the secret,
    and the old v1 relay app (with its per-launch secret buried in
    Downloads\\cursor_relay.py) is not needed at all.

Stop (or closing the window) stops all three services.
"""

import importlib.util
import os
import queue
import secrets
import socket
import sys
import threading
import time
import tkinter as tk
from tkinter import scrolledtext

# These imports look unused; they exist so PyInstaller bundles the
# dependencies the service modules need when they are loaded at runtime.
import flask  # noqa: F401
import pyautogui  # noqa: F401
import requests
import waitress  # noqa: F401
from PIL import Image  # noqa: F401

HANDS_PORT = 5000
GATEWAY_PORT = 5010
PARSER_PORT = 5011
HANDS_URL = "http://127.0.0.1:5000"
POLL_MS = 5000

SERVICE_FILES = {
    "hands": "hands/muse_relay_hands.py",
    "parser": "services/parser/app.py",
    "gateway": "services/gateway/app.py",
}
SERVICE_PORTS = {"hands": HANDS_PORT, "parser": PARSER_PORT, "gateway": GATEWAY_PORT}
SERVICE_HOSTS = {"hands": "127.0.0.1", "parser": "0.0.0.0", "gateway": "0.0.0.0"}
SERVICE_LABELS = {"hands": "Hands", "parser": "Parser", "gateway": "Gateway"}


def _app_dir():
    """Folder that holds services/ and (when frozen) sits next to the exe."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _icon_path():
    for base in (getattr(sys, "_MEIPASS", None), _app_dir()):
        if base:
            cand = os.path.join(base, "muse-avatar.ico")
            if os.path.isfile(cand):
                return cand
    return None


def _hands_secret_path():
    return os.path.join(os.path.expanduser("~"), ".muse-relay-v2", "hands-secret.txt")


def _load_or_create_hands_secret():
    """Return (secret, origin) for the app-owned hands secret.

    origin is "saved" (read back from disk), "created" (first run — a
    new secret was generated and saved), or "ephemeral" (the save failed,
    so this launch uses an unsaved secret). The value itself is never
    logged or displayed; it only goes to the gateway and the hands.
    """
    path = _hands_secret_path()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            saved = fh.read().strip()
        if len(saved) >= 16:
            return saved, "saved"
    except OSError:
        pass
    value = secrets.token_urlsafe(32)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(value + "\n")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass  # best effort (on Windows this only toggles read-only)
        return value, "created"
    except OSError:
        return value, "ephemeral"


def _service_path(rel_path):
    """Find a service module: bundled inside the exe first, then beside it."""
    for base in (getattr(sys, "_MEIPASS", None), _app_dir()):
        if base:
            cand = os.path.join(base, rel_path)
            if os.path.isfile(cand):
                return cand
    return None


def _load_service(name, rel_path):
    path = _service_path(rel_path)
    if path is None:
        raise FileNotFoundError(rel_path)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class RelayApp:
    def __init__(self, root):
        self.root = root
        self.token = None
        self._hands_secret = None
        self._hands_module = None
        self._started = False
        self._poll_logged = False
        self.servers = {}
        self.ui_queue = queue.Queue()
        self._build_ui()
        icon = _icon_path()
        if icon:
            try:
                root.iconbitmap(icon)
            except tk.TclError:
                pass
        root.protocol("WM_DELETE_WINDOW", self.stop)
        root.after(300, self._drain_queue)
        self.log_line("Press Start to run all three services in this window.")

    # ---------- UI ----------
    def _build_ui(self):
        root = self.root
        root.title("Muse Relay v2")
        root.geometry("580x480")
        root.minsize(520, 420)

        frame = tk.Frame(root, padx=12, pady=10)
        frame.pack(fill="x")

        self.hands_status = tk.Label(frame, text="Hands (:5000): not started", anchor="w")
        self.hands_status.pack(fill="x")
        self.gateway_status = tk.Label(frame, text="Gateway (:5010): not started", anchor="w")
        self.gateway_status.pack(fill="x")
        self.parser_status = tk.Label(frame, text="Parser (:5011): not started", anchor="w")
        self.parser_status.pack(fill="x")

        tok = tk.Frame(root, padx=12)
        tok.pack(fill="x", pady=(6, 0))
        tk.Label(tok, text="Gateway token (this launch only):").pack(anchor="w")
        row = tk.Frame(tok)
        row.pack(fill="x")
        self.token_var = tk.StringVar(value="")
        entry = tk.Entry(row, textvariable=self.token_var, state="readonly")
        entry.pack(side="left", fill="x", expand=True)
        tk.Button(row, text="Copy", command=self._copy_token).pack(side="left", padx=(6, 0))

        tk.Label(
            root,
            text="One button runs the hands, gateway, and parser — no other app needed.",
            padx=12,
            anchor="w",
            fg="#555555",
        ).pack(fill="x", pady=(4, 0))

        btns = tk.Frame(root, padx=12)
        btns.pack(fill="x", pady=(8, 0))
        self.start_button = tk.Button(
            btns,
            text="Start",
            width=16,
            font=("Segoe UI", 11, "bold"),
            command=self._start_all,
        )
        self.start_button.pack(side="left")
        tk.Button(btns, text="Stop", width=14, command=self.stop).pack(
            side="left", padx=(8, 0)
        )

        self.log = scrolledtext.ScrolledText(root, height=12, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=12, pady=10)

    def _copy_token(self):
        if self.token:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.token)

    # ---------- helpers ----------
    def _stamp(self):
        return time.strftime("%H:%M:%S")

    def log_line(self, msg):
        self.ui_queue.put(("log", f"[{self._stamp()}] {msg}"))

    def set_status(self, which, text):
        self.ui_queue.put(("status", (which, text)))

    def _drain_queue(self):
        # Forward anything the in-process hands logged (bad-secret
        # rejections, lockouts) into this window's log.
        hands = self._hands_module
        if hands is not None:
            try:
                while True:
                    self.ui_queue.put(
                        ("log", f"[{self._stamp()}] hands: {hands.log_queue.get_nowait()}")
                    )
            except queue.Empty:
                pass
        try:
            while True:
                kind, payload = self.ui_queue.get_nowait()
                if kind == "log":
                    self.log.config(state="normal")
                    self.log.insert("end", payload + "\n")
                    self.log.see("end")
                    self.log.config(state="disabled")
                elif kind == "status":
                    which, text = payload
                    label = {
                        "parser": self.parser_status,
                        "gateway": self.gateway_status,
                        "hands": self.hands_status,
                    }[which]
                    label.config(text=text)
        except queue.Empty:
            pass
        self.root.after(300, self._drain_queue)

    # ---------- services ----------
    def _start_all(self):
        if self._started:
            return
        self._started = True
        self.start_button.config(state="disabled")

        hands_secret, origin = _load_or_create_hands_secret()
        secret_path = _hands_secret_path()
        if origin == "saved":
            self.log_line(f"Hands secret loaded from {secret_path} (value not shown).")
        elif origin == "created":
            self.log_line(
                f"First run: created the hands secret at {secret_path} (value not shown)."
            )
        else:
            self.log_line(
                f"WARNING: could not save the hands secret to {secret_path}; "
                "using a one-launch secret instead."
            )

        self.token = secrets.token_hex(16)
        self._hands_secret = hands_secret
        # The services read their config from the environment at import
        # time, so set it BEFORE importing them.
        os.environ["RELAY_GATEWAY_TOKEN"] = self.token
        os.environ["HANDS_URL"] = HANDS_URL
        os.environ["HANDS_SECRET"] = hands_secret
        os.environ["PARSER_URL"] = f"http://127.0.0.1:{PARSER_PORT}"
        self.token_var.set(self.token)

        self._start_one("hands")
        self._start_one("parser")
        self._start_one("gateway")
        self.root.after(POLL_MS, self._poll)

    def _start_one(self, name):
        label = SERVICE_LABELS[name]
        port = SERVICE_PORTS[name]
        host = SERVICE_HOSTS[name]
        # Refuse to duplicate a service that is already answering on the
        # port. A bare bind is not a reliable check on Windows (socket
        # reuse can let a second listener attach silently, after which
        # callers reach the stale copy and auth fails mysteriously) —
        # a connect probe is. Found the hard way on 2026-10-13: two
        # leftover console services held 5010/5011 for hours while the
        # packaged app bound alongside them and never got a request.
        with socket.socket() as probe:
            probe.settimeout(0.5)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                hint = (
                    " (an old v1 Muse Relay window counts — close it)"
                    if name == "hands"
                    else ""
                )
                self.log_line(
                    f"ERROR: port {port} is already answering — the {name} "
                    f"service is already running somewhere else{hint}. Close the "
                    "other copy first; this copy will not start a duplicate."
                )
                self.set_status(name, f"{label} (:{port}): already running elsewhere")
                return
        try:
            module = _load_service(f"muse_relay_v2_{name}", SERVICE_FILES[name])
        except Exception as exc:
            self.log_line(f"ERROR: could not load the {name} service: {exc}")
            self.set_status(name, f"{label} (:{port}): failed to load")
            return
        if name == "hands":
            # Same idea as the gateway config below: assign directly on
            # the module, don't rely on it having generated a matching
            # secret itself. Its gate() reads this global per request.
            module.SHARED_SECRET = self._hands_secret
            self._hands_module = module
            self.log_line(
                "Hands config check: module_match=%s module_len=%s"
                % (
                    module.SHARED_SECRET == self._hands_secret,
                    len(module.SHARED_SECRET or ""),
                )
            )
        if name == "gateway":
            # Configure the gateway directly as well as via the
            # environment. The module reads env at import time; in the
            # packaged (frozen) build this explicit assignment is the
            # guarantee that the running config matches this window —
            # a packaged build was observed rejecting the app's own
            # token when it relied on the environment alone.
            module.TOKEN = self.token
            self.log_line(
                "Gateway config check: env_match=%s module_match=%s module_len=%s"
                % (
                    os.environ.get("RELAY_GATEWAY_TOKEN") == self.token,
                    module.TOKEN == self.token,
                    len(module.TOKEN or ""),
                )
            )
            module.HANDS_URL = HANDS_URL
            module.HANDS_SECRET = self._hands_secret
            module.PARSER_URL = f"http://127.0.0.1:{PARSER_PORT}"
        try:
            server = waitress.create_server(module.app, host=host, port=port, threads=8)
        except OSError as exc:
            self.log_line(
                f"ERROR: port {port} is already in use — the {name} service is "
                f"probably already running. Close the other copy first. ({exc})"
            )
            self.set_status(name, f"{label} (:{port}): port already in use")
            return
        except Exception as exc:
            self.log_line(f"ERROR: could not start the {name} service: {exc}")
            self.set_status(name, f"{label} (:{port}): failed to start")
            return
        self.servers[name] = server
        thread = threading.Thread(target=server.run, name=f"{name}-server", daemon=True)
        thread.start()
        self.log_line(f"{label} service started on port {port}.")
        self.set_status(name, f"{label} (:{port}): running")

    def _poll(self):
        def work():
            try:
                r = requests.get(
                    f"http://127.0.0.1:{GATEWAY_PORT}/v1/info",
                    headers={"X-Relay-Token": self.token or ""},
                    timeout=2,
                )
                if not self._poll_logged:
                    self._poll_logged = True
                    self.log_line(f"Gateway self-check: HTTP {r.status_code}.")
                    self.log_line(f"Gateway self-check body: {r.text[:70]!r}")
                data = r.json()
                hands = bool(data.get("hands_reachable"))
                parser = bool(data.get("parser_reachable"))
            except Exception:
                hands = None
                parser = None
            if hands is None:
                self.set_status("hands", "Hands (:5000): no answer from gateway")
            else:
                self.set_status(
                    "hands",
                    "Hands (:5000): reachable" if hands else "Hands (:5000): not reachable",
                )
                self.set_status(
                    "parser",
                    "Parser (:5011): running, reachable"
                    if parser
                    else "Parser (:5011): running, not answering",
                )

        threading.Thread(target=work, daemon=True).start()
        self.root.after(POLL_MS, self._poll)

    def stop(self):
        for name, server in list(self.servers.items()):
            try:
                server.close()
            except Exception:
                pass
        self.servers.clear()
        try:
            self.root.destroy()
        finally:
            os._exit(0)


def main():
    root = tk.Tk()
    RelayApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
