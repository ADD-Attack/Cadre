"""Muse Relay v2 — packaged single-window app (Windows).

Runs the gateway (:5010) and parser (:5011) services in-process and shows
their status in one window, so the relay looks and behaves like a normal
desktop app (avatar icon in the taskbar) instead of two console windows.

On launch it:
  * reads the hands session secret from Downloads\\cursor_relay.py — the
    secret is never stored in this file, logged, or displayed;
  * mints a fresh gateway token for this launch (shown in the window with
    a Copy button; never saved anywhere);
  * starts the parser and gateway with waitress in background threads.

The hands themselves (port 5000) are separate — start them with the
"Muse Relay" desktop icon. This app only reports whether they answer.

Closing the window (or the Stop button) stops both services.
"""

import importlib.util
import os
import queue
import re
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
import requests
import waitress  # noqa: F401
from PIL import Image  # noqa: F401

GATEWAY_PORT = 5010
PARSER_PORT = 5011
HANDS_URL = "http://127.0.0.1:5000"
POLL_MS = 5000


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


def _read_hands_secret():
    """Parse the hands session secret out of Downloads\\cursor_relay.py.

    Returns the secret string, or None when the file/value can't be found.
    The value is only ever placed in the gateway's environment.
    """
    path = os.path.join(os.path.expanduser("~"), "Downloads", "cursor_relay.py")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return None
    m = re.search(r"SHARED_SECRET\s*=\s*[\"']([^\"']+)[\"']", text)
    return m.group(1) if m else None


def _load_service(name, rel_path):
    path = os.path.join(_app_dir(), rel_path)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
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
        root.after(100, self._bootstrap)
        root.after(300, self._drain_queue)

    # ---------- UI ----------
    def _build_ui(self):
        root = self.root
        root.title("Muse Relay v2")
        root.geometry("580x480")
        root.minsize(520, 420)

        frame = tk.Frame(root, padx=12, pady=10)
        frame.pack(fill="x")

        self.parser_status = tk.Label(frame, text="Parser (:5011): starting…", anchor="w")
        self.parser_status.pack(fill="x")
        self.gateway_status = tk.Label(frame, text="Gateway (:5010): starting…", anchor="w")
        self.gateway_status.pack(fill="x")
        self.hands_status = tk.Label(frame, text="Hands (:5000): unknown yet", anchor="w")
        self.hands_status.pack(fill="x")

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
            text="Hands are separate: start them with the Muse Relay desktop icon.",
            padx=12,
            anchor="w",
            fg="#555555",
        ).pack(fill="x", pady=(4, 0))

        self.log = scrolledtext.ScrolledText(root, height=12, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=12, pady=10)

        tk.Button(root, text="Stop", width=14, command=self.stop).pack(pady=(0, 10))

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
    def _bootstrap(self):
        hands_secret = _read_hands_secret()
        if not hands_secret:
            self.log_line(
                "ERROR: could not read the hands secret from Downloads\\cursor_relay.py."
            )
            self.log_line("Services not started. Set up the hands first, then relaunch.")
            self.set_status("parser", "Parser (:5011): not started")
            self.set_status("gateway", "Gateway (:5010): not started")
            return

        self.token = secrets.token_hex(16)
        self._hands_secret = hands_secret
        # The services read their config from the environment at import
        # time, so set it BEFORE importing them.
        os.environ["RELAY_GATEWAY_TOKEN"] = self.token
        os.environ["HANDS_URL"] = HANDS_URL
        os.environ["HANDS_SECRET"] = hands_secret
        os.environ["PARSER_URL"] = f"http://127.0.0.1:{PARSER_PORT}"
        self.token_var.set(self.token)

        self._start_one("parser", "services/parser/app.py", PARSER_PORT)
        self._start_one("gateway", "services/gateway/app.py", GATEWAY_PORT)
        self.root.after(POLL_MS, self._poll)

    def _start_one(self, name, rel_path, port):
        label = "Parser" if name == "parser" else "Gateway"
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
                self.log_line(
                    f"ERROR: port {port} is already answering — the {name} "
                    "service is already running somewhere else. Close the "
                    "other copy first; this copy will not start a duplicate."
                )
                self.set_status(name, f"{label} (:{port}): already running elsewhere")
                return
        try:
            module = _load_service(f"muse_relay_v2_{name}", rel_path)
        except Exception as exc:
            self.log_line(f"ERROR: could not load the {name} service: {exc}")
            self.set_status(name, f"{label} (:{port}): failed to load")
            return
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
            server = waitress.create_server(module.app, host="0.0.0.0", port=port, threads=8)
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
