"""Muse Relay v2 — packaged single-window app (Windows).

One icon, one button: the window opens idle, and pressing Start brings
up all three relay services in this one process —

  * hands   on 127.0.0.1:5000  (hands/muse_relay_hands.py, headless: no
    separate window, no tunnel — localhost only, as designed)
  * gateway on :5010           (the agent-facing API)
  * parser  on :5011           (screen parsing)

The status lines show each service; the log shows what happened.

Secrets:
  * The gateway token persists per machine at
    %USERPROFILE%\\.muse-relay-v2\\gateway-token.txt — generated on first
    run, reused after that (delete the file to rotate). It is shown in
    the window with a Copy button so the operator can hand it to the
    agent once; after that, the same token keeps working across
    relaunches, which is what lets the agent keep hands while the
    owner is away from the PC.
  * The hands secret is owned by this app and persists per machine at
    %USERPROFILE%\\.muse-relay-v2\\hands-secret.txt — generated on first
    run, reused after that (delete the file to rotate). It is never
    logged or displayed. The app hands the same value to the gateway
    and to the in-process hands, which is the whole point of bundling
    them: gateway and hands can no longer disagree about the secret,
    and the old v1 relay app (with its per-launch secret buried in
    Downloads\\cursor_relay.py) is not needed at all.

Stop (or closing the window) stops all three services.

R6 (wishlist #23, first revision) adds a dashboard section to the
window: service tiles, the hands claim + queue state, the PC lock /
idle / yield-probe state, a live feed of recent act receipts, and a
one-click diagnostics summary (button copies it to the clipboard).
The dashboard's data layer is a set of pure functions
(build_dashboard_model and friends) so it is testable headless; the
full "super AAA" interface pass is a separate wishlist item (#25).
"""

import importlib.util
import math
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
SERVICE_HOSTS = {"hands": "127.0.0.1", "parser": "127.0.0.1", "gateway": "0.0.0.0"}
SERVICE_LABELS = {"hands": "Hands", "parser": "Parser", "gateway": "Gateway"}

AUTOSTART_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_VALUE_NAME = "Muse Relay v2"


def _winreg():
    """Seam: the winreg module on Windows, None anywhere else."""
    try:
        import winreg

        return winreg
    except Exception:
        return None


def _autostart_command():
    """Command string written to the Run key."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    script = os.path.abspath(__file__)
    return f'"{sys.executable}" "{script}"'


def _autostart_enabled():
    wr = _winreg()
    if wr is None:
        return False
    key = None
    try:
        key = wr.OpenKey(wr.HKEY_CURRENT_USER, AUTOSTART_RUN_KEY)
        value, _kind = wr.QueryValueEx(key, AUTOSTART_VALUE_NAME)
        return bool(value)
    except Exception:
        return False
    finally:
        if key is not None:
            try:
                wr.CloseKey(key)
            except Exception:
                pass


def _set_autostart(enabled):
    """Write/remove the Run-key value. False (no raise) off-Windows."""
    wr = _winreg()
    if wr is None:
        return False
    key = None
    try:
        key = wr.CreateKey(wr.HKEY_CURRENT_USER, AUTOSTART_RUN_KEY)
        if enabled:
            wr.SetValueEx(
                key, AUTOSTART_VALUE_NAME, 0, wr.REG_SZ, _autostart_command()
            )
        else:
            try:
                wr.DeleteValue(key, AUTOSTART_VALUE_NAME)
            except Exception:
                pass  # already absent — disabled is the goal state
        return True
    except Exception:
        return False
    finally:
        if key is not None:
            try:
                wr.CloseKey(key)
            except Exception:
                pass


class ServiceHealth:
    """Self-heal state machine for one service (pure; no I/O).

    note(ok) -> "none" | "restart" | "give_up". Consecutive failures
    are counted; at 3 in a row it returns "restart" (counter resets,
    restart budget decrements). The budget is 3 restarts; once it is
    exhausted the next 3-failure streak returns "give_up" exactly once
    and then "none". A success resets the consecutive-failure count
    (not the restart budget).
    """

    def __init__(self, max_consecutive=3, max_restarts=3):
        self.max_consecutive = max_consecutive
        self.max_restarts = max_restarts
        self._consecutive = 0
        self._restarts = 0
        self._gave_up = False

    def note(self, ok):
        lock = getattr(self, "_note_lock", None)
        if lock is None:
            lock = self._note_lock = threading.Lock()
        with lock:
            if ok:
                self._consecutive = 0
                return "none"
            self._consecutive += 1
            if self._consecutive < self.max_consecutive:
                return "none"
            self._consecutive = 0
            if self._restarts < self.max_restarts:
                self._restarts += 1
                return "restart"
            if not self._gave_up:
                self._gave_up = True
                return "give_up"
            return "none"


# ---- dashboard data layer (R6, wishlist #23) ---------------------------
# Pure functions: gateway /v1/info payload + the gateway module's
# in-process claim snapshot and receipts table in, a plain model dict
# out. No I/O, no tkinter — the poll thread builds the model, the UI
# thread renders it, and tests exercise it headless.


def _fmt_duration(seconds):
    """Compact duration: 5 -> '5s', 65 -> '1m 05s', 3661 -> '1h 01m'.

    Non-numeric and nonfinite inputs render as "?" (R7: float("inf")
    used to raise OverflowError out of round()).
    """
    try:
        value = float(seconds)
    except (TypeError, ValueError):
        return "?"
    if not math.isfinite(value):
        return "?"
    total = int(max(0, round(value)))
    if total < 60:
        return f"{total}s"
    if total < 3600:
        return f"{total // 60}m {total % 60:02d}s"
    return f"{total // 3600}h {(total % 3600) // 60:02d}m"


def _receipt_entries(receipts):
    """Row list from a receipts table.

    Accepts a dict (its values), a list/tuple, or any other
    iterable of rows (generators, dict-values views, ...).
    Strings/bytes, None, numbers and other non-iterables yield []
    — the data layer honors its "junk -> empty" contract and
    never raises on a malformed container (R7/R7.1).
    """
    if isinstance(receipts, dict):
        return list(receipts.values())
    if isinstance(receipts, (list, tuple)):
        return list(receipts)
    if isinstance(receipts, (str, bytes)):
        return []
    try:
        return list(receipts)
    except TypeError:
        return []


_RECEIPT_ROW_FIELDS = ("id", "op", "state", "submitted_at")


def _snapshot_receipt_rows(table):
    """Field-copied snapshot of the gateway receipts table.

    The caller holds the gateway's receipts lock. Each dict row is
    copied field-by-field into a fresh dict, so the dashboard
    builders never read a row that a gateway writer is mutating
    after the lock is released (R7). Non-dict rows pass through —
    the builders skip them.
    """
    snap = {}
    if not isinstance(table, dict):
        return snap
    for rid, row in table.items():
        if isinstance(row, dict):
            snap[rid] = {k: row[k] for k in _RECEIPT_ROW_FIELDS if k in row}
        else:
            snap[rid] = row
    return snap


def summarize_receipts(receipts, now, limit=8):
    """Newest-first feed rows from a receipts dict (or iterable).

    Rows: {"id8", "op", "state", "age_s"}. Entries missing any of
    id/op/state/submitted_at are skipped — the feed renders what it
    can prove, never a half-row.
    """
    entries = _receipt_entries(receipts)
    rows = []
    for r in entries:
        if not isinstance(r, dict):
            continue
        rid, op, state = r.get("id"), r.get("op"), r.get("state")
        submitted = r.get("submitted_at")
        if not rid or not op or not state or not isinstance(submitted, (int, float)):
            continue
        rows.append(
            {
                "id8": str(rid)[:8],
                "op": str(op),
                "state": str(state),
                "age_s": max(0.0, float(now) - float(submitted)),
                "_submitted": float(submitted),
            }
        )
    rows.sort(key=lambda row: row["_submitted"], reverse=True)
    for row in rows:
        del row["_submitted"]
    return rows[:limit]


def receipt_state_counts(receipts):
    """{state: count} over the receipts table ({} for none/junk)."""
    entries = _receipt_entries(receipts)
    counts = {}
    for r in entries:
        if isinstance(r, dict) and r.get("state"):
            counts[str(r["state"])] = counts.get(str(r["state"]), 0) + 1
    return counts


def build_dashboard_model(info, claim, queue, reserved_for, receipts, now):
    """Assemble the dashboard model from one poll's worth of state.

    info: the gateway /v1/info payload, or None when the gateway did
    not answer. claim/queue/reserved_for: the gateway module's
    _claim_snapshot() triple (claim dict or None, FIFO list, holder
    name or None). receipts: the gateway's receipts table.
    """
    # R7: a non-dict payload (e.g. a JSON list from /v1/info) is
    # normalized here instead of raising on .get() — the gateway
    # answered, so it is not "down", but nothing in the payload can
    # be trusted field-by-field.
    info_dict = info if isinstance(info, dict) else {}
    services = {"gateway": "down" if info is None else "ok"}
    if info is None:
        services["hands"] = "unknown"
        services["parser"] = "unknown"
        pc = None
    else:
        services["hands"] = "ok" if info_dict.get("hands_reachable") else "down"
        services["parser"] = "ok" if info_dict.get("parser_reachable") else "down"
        pc_state = info_dict.get("pc_state")
        if isinstance(pc_state, dict):
            failures = pc_state.get("probe_failures")
            locked = pc_state.get("locked")
            idle = pc_state.get("idle_seconds")
            probe_ok = pc_state.get("probe_ok")
            # R7: PC fields are type-normalized at this boundary. A
            # wrong-typed value (the string "false", an infinite
            # idle) becomes None / "unknown" — it must neither reach
            # the renderer's strict dict lookups nor read as healthy.
            pc = {
                "locked": locked if isinstance(locked, bool) else None,
                "idle_seconds": (
                    float(idle)
                    if isinstance(idle, (int, float))
                    and not isinstance(idle, bool)
                    and math.isfinite(idle)
                    else None
                ),
                "probe_failures": (
                    failures
                    if isinstance(failures, int) and not isinstance(failures, bool)
                    else None
                ),
                "probe_state": (
                    "unknown"
                    if not isinstance(probe_ok, bool)
                    else ("ok" if probe_ok else "degraded")
                ),
            }
        else:
            pc = None
    claim_model = None
    if isinstance(claim, dict) and claim.get("holder"):
        expires_at = claim.get("expires_at")
        claim_model = {
            "holder": str(claim["holder"]),
            "purpose": str(claim.get("purpose") or ""),
            "expires_in_s": (
                max(0.0, float(expires_at) - float(now))
                if isinstance(expires_at, (int, float))
                and not isinstance(expires_at, bool)
                and math.isfinite(expires_at)
                else None
            ),
        }
    return {
        "services": services,
        "claim": claim_model,
        "queue_len": len(queue) if isinstance(queue, list) else 0,
        "reserved_for": str(reserved_for) if reserved_for else None,
        "pc": pc,
        "feed": summarize_receipts(receipts, now),
        "counts": receipt_state_counts(receipts),
    }


def format_diagnostics(model, stamp):
    """One-click diagnostics text (clipboard + log) from a model."""
    svc = model.get("services", {})
    lines = [
        f"Muse Relay diagnostics — {stamp}",
        "Services: gateway {g} · hands {h} · parser {p}".format(
            g=svc.get("gateway", "?"), h=svc.get("hands", "?"), p=svc.get("parser", "?")
        ),
    ]
    claim = model.get("claim")
    if claim:
        text = f"Claim: {claim['holder']}"
        if claim["purpose"]:
            text += f" — {claim['purpose']}"
        if claim["expires_in_s"] is not None:
            text += f" (expires in {_fmt_duration(claim['expires_in_s'])})"
        lines.append(text)
    else:
        lines.append("Claim: none")
    extra = []
    if model.get("queue_len"):
        extra.append(f"queue: {model['queue_len']} waiting")
    if model.get("reserved_for"):
        extra.append(f"reserved for: {model['reserved_for']}")
    if extra:
        lines.append(" · ".join(extra))
    pc = model.get("pc")
    if pc is None:
        lines.append("PC: unknown (hands unreachable)")
    else:
        locked = {True: "LOCKED", False: "unlocked", None: "lock unknown"}[pc["locked"]]
        idle = (
            "idle unknown"
            if pc["idle_seconds"] is None
            else f"owner idle {_fmt_duration(pc['idle_seconds'])}"
        )
        probe = {
            "ok": "yield probe OK",
            "degraded": f"yield probe DEGRADED ({pc['probe_failures']} failures)",
            "unknown": "yield probe unknown",
        }[pc["probe_state"]]
        lines.append(f"PC: {locked} · {idle} · {probe}")
    counts = model.get("counts", {})
    if counts:
        total = sum(counts.values())
        detail = " · ".join(f"{state} {counts[state]}" for state in sorted(counts))
        lines.append(f"Receipts: {total} total — {detail}")
    else:
        lines.append("Receipts: none yet")
    return "\n".join(lines)


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


def _gateway_token_path():
    return os.path.join(os.path.expanduser("~"), ".muse-relay-v2", "gateway-token.txt")


def _load_or_create_gateway_token():
    """Return (token, origin) for the per-machine gateway token.

    Same load-or-create pattern as the hands secret: origin is "saved"
    (read back from disk), "created" (first run — a new token was
    generated and saved), or "ephemeral" (the save failed, so this
    launch falls back to an unsaved token). The value is shown in the
    window (the operator copies it to the agent) but never logged.
    """
    path = _gateway_token_path()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            saved = fh.read().strip()
        if len(saved) >= 16:
            return saved, "saved"
    except OSError:
        pass
    value = secrets.token_hex(16)
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
        self._gateway_module = None
        self._last_model = None
        self._started = False
        self._poll_logged = False
        self.servers = {}
        self._health = {name: ServiceHealth() for name in SERVICE_FILES}
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
        root.geometry("760x680")
        root.minsize(680, 560)

        frame = tk.Frame(root, padx=12, pady=10)
        frame.pack(fill="x")

        self.hands_status = tk.Label(frame, text="Hands (:5000): not started", anchor="w")
        self.hands_status.pack(fill="x")
        self.gateway_status = tk.Label(frame, text="Gateway (:5010): not started", anchor="w")
        self.gateway_status.pack(fill="x")
        self.parser_status = tk.Label(frame, text="Parser (:5011): not started", anchor="w")
        self.parser_status.pack(fill="x")

        self._build_dashboard(root)

        tok = tk.Frame(root, padx=12)
        tok.pack(fill="x", pady=(6, 0))
        tk.Label(tok, text="Gateway token (saved on this machine):").pack(anchor="w")
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

        autostart_row = tk.Frame(root, padx=12)
        autostart_row.pack(fill="x", pady=(4, 0))
        self.autostart_var = tk.BooleanVar(value=_autostart_enabled())
        tk.Checkbutton(
            autostart_row,
            text="Start on login",
            variable=self.autostart_var,
            command=self._toggle_autostart,
        ).pack(side="left")

        self.log = scrolledtext.ScrolledText(root, height=12, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=12, pady=10)

    # ---------- dashboard (R6, wishlist #23) ----------
    def _build_dashboard(self, root):
        dash = tk.LabelFrame(root, text="Dashboard", padx=10, pady=8)
        dash.pack(fill="x", padx=12, pady=(8, 0))

        tiles = tk.Frame(dash)
        tiles.pack(fill="x")
        self._tile_dots = {}
        self._tile_texts = {}
        for name in ("hands", "gateway", "parser"):
            tile = tk.Frame(tiles, relief="groove", borderwidth=1, padx=8, pady=4)
            tile.pack(side="left", fill="x", expand=True, padx=(0, 6))
            dot = tk.Label(tile, text="●", fg="#999999", font=("Segoe UI", 13))
            dot.pack(side="left")
            text = tk.Label(
                tile,
                text=f"{SERVICE_LABELS[name]} (:{SERVICE_PORTS[name]}): not started",
                anchor="w",
                font=("Segoe UI", 9),
            )
            text.pack(side="left", fill="x", expand=True)
            self._tile_dots[name] = dot
            self._tile_texts[name] = text

        self.dash_claim = tk.Label(
            dash, text="Claim: —", anchor="w", font=("Segoe UI", 9)
        )
        self.dash_claim.pack(fill="x", pady=(6, 0))
        self.dash_pc = tk.Label(dash, text="PC: —", anchor="w", font=("Segoe UI", 9))
        self.dash_pc.pack(fill="x")

        feed_head = tk.Frame(dash)
        feed_head.pack(fill="x", pady=(6, 0))
        tk.Label(feed_head, text="Recent acts", font=("Segoe UI", 9, "bold")).pack(
            side="left"
        )
        self.dash_counts = tk.Label(feed_head, text="", anchor="e", fg="#555555")
        self.dash_counts.pack(side="right")
        self.dash_feed = tk.Text(
            dash, height=8, state="disabled", wrap="none", font=("Consolas", 9)
        )
        self.dash_feed.pack(fill="x")

        tk.Button(
            dash, text="Copy diagnostics", command=self._copy_diagnostics
        ).pack(anchor="e", pady=(6, 0))

    def _render_dashboard(self, model):
        self._last_model = model
        colors = {"ok": "#1e9e50", "down": "#cc3333", "unknown": "#999999"}
        words = {"ok": "running", "down": "not answering", "unknown": "unknown"}
        for name, state in model["services"].items():
            self._tile_dots[name].config(fg=colors.get(state, "#999999"))
            self._tile_texts[name].config(
                text=(
                    f"{SERVICE_LABELS[name]} (:{SERVICE_PORTS[name]}): "
                    f"{words.get(state, state)}"
                )
            )
        claim = model["claim"]
        if claim:
            text = f"Claim: {claim['holder']}"
            if claim["purpose"]:
                text += f" — {claim['purpose']}"
            if claim["expires_in_s"] is not None:
                text += f" (expires in {_fmt_duration(claim['expires_in_s'])})"
        else:
            text = "Claim: none"
        if model["queue_len"]:
            text += f" · queue: {model['queue_len']} waiting"
        if model["reserved_for"]:
            text += f" · reserved for: {model['reserved_for']}"
        self.dash_claim.config(text=text)

        pc = model["pc"]
        if pc is None:
            self.dash_pc.config(text="PC: unknown (hands unreachable)")
        else:
            locked = {True: "LOCKED", False: "unlocked", None: "lock unknown"}[
                pc["locked"]
            ]
            idle = (
                "idle unknown"
                if pc["idle_seconds"] is None
                else f"owner idle {_fmt_duration(pc['idle_seconds'])}"
            )
            probe = {
                "ok": "yield probe OK",
                "degraded": f"yield probe DEGRADED ({pc['probe_failures']} failures)",
                "unknown": "yield probe unknown",
            }[pc["probe_state"]]
            color = "#cc3333" if (pc["locked"] or pc["probe_state"] == "degraded") else ""
            self.dash_pc.config(
                text=f"PC: {locked} · {idle} · {probe}", fg=color or "#000000"
            )

        counts = model["counts"]
        if counts:
            detail = " · ".join(
                f"{state} {counts[state]}" for state in sorted(counts)
            )
            self.dash_counts.config(text=f"{sum(counts.values())} total — {detail}")
        else:
            self.dash_counts.config(text="no acts yet")
        lines = [
            f"{row['id8']}  {row['op']:<13} {row['state']:<15} "
            f"{_fmt_duration(row['age_s'])} ago"
            for row in model["feed"]
        ]
        self.dash_feed.config(state="normal")
        self.dash_feed.delete("1.0", "end")
        self.dash_feed.insert("end", "\n".join(lines) if lines else "(no acts yet)")
        self.dash_feed.config(state="disabled")

    def _copy_diagnostics(self):
        if self._last_model is None:
            self.log_line("Diagnostics: nothing to report yet — start the services first.")
            return
        text = format_diagnostics(self._last_model, self._stamp())
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.log_line("Diagnostics copied to the clipboard.")

    def _copy_token(self):
        if self.token:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.token)

    def _toggle_autostart(self):
        enabled = bool(self.autostart_var.get())
        ok = _set_autostart(enabled)
        if ok:
            self.log_line(
                f"Start on login {'enabled' if enabled else 'disabled'} "
                f"({AUTOSTART_VALUE_NAME} in HKCU Run key)."
            )
        else:
            self.log_line(
                "Start on login could not be changed "
                "(autostart is only available on Windows)."
            )

    # ---------- helpers ----------
    def _stamp(self):
        return time.strftime("%H:%M:%S")

    def log_line(self, msg):
        self.ui_queue.put(("log", f"[{self._stamp()}] {msg}"))

    def set_status(self, which, text):
        self.ui_queue.put(("status", (which, text)))

    def _handle_elevation_request(self, hands, req):
        """Show one elevation request to the person at the PC.

        The dialog is the ONLY approval path: it names the request and
        the exact configured exe/args, Yes approves (runs ELEVATED),
        No denies (does nothing). The dialog result — and nothing
        else — is passed to the hands module's resolver.
        """
        if not isinstance(req, dict):
            return
        eid = req.get("id")
        name = req.get("name") or ""
        exe = req.get("exe") or ""
        args = req.get("args") or ""
        self._elevation_dialog_open = True
        try:
            from tkinter import messagebox

            approved = bool(
                messagebox.askyesno(
                    "Elevation request",
                    f"Elevation request: {name}\n\n"
                    f"Would run ELEVATED:\n{exe} {args}\n\n"
                    "Approve (Yes) runs it ELEVATED. Deny (No) does nothing.",
                )
            )
        except Exception:
            approved = False  # no dialog, no approval — deny by default
        finally:
            self._elevation_dialog_open = False
        try:
            resolved = hands._resolve_elevation(eid, approved)
        except Exception as exc:
            self.log_line(f"Elevation request '{name}': resolver failed ({exc})")
            return
        state = "unresolved"
        try:
            elevations = getattr(hands, "_elevations", {})
            lk = getattr(hands, "_elevations_lock", None)
            if lk is None:
                found = elevations.get(eid)
            else:
                with lk:
                    found = elevations.get(eid)
            if isinstance(found, dict) and found.get("state"):
                state = found["state"]
        except Exception:
            pass
        self.log_line(f"Elevation request '{name}': state={state} (resolved={resolved})")

    def _drain_queue(self):
        # R7: the next drain is ALWAYS scheduled (finally), and each
        # queued message is handled in isolation — one bad dashboard
        # model or status update must not stop the drain, which also
        # carries the status and log updates.
        try:
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
                # Elevation requests from the hands: each one is shown to
                # the person at the PC for an explicit Approve/Deny click.
                elevate_queue = getattr(hands, "elevate_queue", None)
                if elevate_queue is not None:
                    try:
                        while True:
                            req = elevate_queue.get_nowait()
                            self._handle_elevation_request(hands, req)
                    except queue.Empty:
                        pass
            try:
                while True:
                    kind, payload = self.ui_queue.get_nowait()
                    try:
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
                        elif kind == "dashboard":
                            self._render_dashboard(payload)
                    except Exception as exc:
                        # Isolated: note the skip in the log and keep
                        # draining the remaining messages.
                        try:
                            self.log.config(state="normal")
                            self.log.insert(
                                "end",
                                f"[{self._stamp()}] UI update skipped ({kind}): {exc}\n",
                            )
                            self.log.see("end")
                            self.log.config(state="disabled")
                        except Exception:
                            pass
            except queue.Empty:
                pass
        finally:
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

        gateway_token, token_origin = _load_or_create_gateway_token()
        token_path = _gateway_token_path()
        if token_origin == "saved":
            self.log_line(f"Gateway token loaded from {token_path} (value not shown).")
        elif token_origin == "created":
            self.log_line(
                f"First run: created the gateway token at {token_path} (value not shown)."
            )
        else:
            self.log_line(
                f"WARNING: could not save the gateway token to {token_path}; "
                "using a one-launch token instead."
            )

        self.token = gateway_token
        self._hands_secret = hands_secret
        # The services read their config from the environment at import
        # time, so set it BEFORE importing them.
        os.environ["RELAY_GATEWAY_TOKEN"] = self.token
        os.environ["HANDS_URL"] = HANDS_URL
        os.environ["HANDS_SECRET"] = hands_secret
        os.environ["PARSER_URL"] = f"http://127.0.0.1:{PARSER_PORT}"
        self.token_var.set(self.token)

        self._health = {name: ServiceHealth() for name in SERVICE_FILES}
        self._start_one("hands")
        self._start_one("parser")
        self._start_one("gateway")
        self.root.after(POLL_MS, self._poll)

    def _start_one(self, name):
        locks = getattr(self, "_start_locks", None)
        if locks is None:
            locks = self._start_locks = {}
        lock = locks.setdefault(name, threading.Lock())
        with lock:
            return self._start_one_locked(name)

    def _start_one_locked(self, name):
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
            # R9 (#28): the jiggler thread idles unless its flag is on.
            starter = getattr(module, "start_jiggler", None)
            if callable(starter):
                starter()
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
            self._gateway_module = module
        try:
            # R4 (F9): match the gateway module's 32 — long-poll
            # endpoints must not starve act traffic of threads.
            server = waitress.create_server(module.app, host=host, port=port, threads=32)
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

    def _skip_restart(self, name):
        """Do not restart a process that still holds live coordination."""
        if name == "hands" and getattr(self, "_elevation_dialog_open", False):
            return True
        if name == "hands":
            module = getattr(self, "_hands_module", None)
            table, lock_name, bad = "_elevations", "_elevations_lock", "pending"
        elif name == "gateway":
            module = getattr(self, "_gateway_module", None)
            table, lock_name, bad = "_receipts", "_receipts_lock", "held"
        else:
            return False
        if module is None:
            return False
        rows = getattr(module, table, None) or {}
        lk = getattr(module, lock_name, None)

        def busy():
            return any(isinstance(v, dict) and v.get("state") == bad for v in rows.values())

        if lk is None:
            return busy()
        with lk:
            return busy()

    def _note_health(self, name, ok):
        """Feed one liveness result into a service's self-heal machine."""
        health = self._health.get(name)
        if health is None:
            return
        action = health.note(bool(ok))
        if action == "restart":
            if self._skip_restart(name):
                self.log_line(
                    f"self-heal: not restarting {name} — it holds live receipts or a pending elevation"
                )
                return
            # Only ever restart a service WE started. A service that
            # was "already running elsewhere" is not in self.servers,
            # so it is never touched here.
            if name in self.servers:
                self.log_line(
                    f"self-heal: restarting {name} after repeated failures"
                )
                server = self.servers.pop(name, None)
                if server is not None:
                    try:
                        server.close()
                    except Exception:
                        pass
                if name == "hands":
                    # R9: the reload makes a fresh module (and jiggler);
                    # the old module's jiggler thread must not live on.
                    stopper = getattr(self._hands_module, "stop_jiggler", None)
                    if callable(stopper):
                        stopper()
                self._start_one(name)
        elif action == "give_up":
            self.log_line(
                f"self-heal: giving up on {name} — repeated failures "
                "continued after the restart budget was used; it will "
                "not be restarted automatically again."
            )

    def _poll(self):
        if getattr(self, "_poll_running", False):
            self.root.after(POLL_MS, self._poll)
            return
        self._poll_running = True

        def work():
            gateway_answered = False
            info_data = None
            try:
                r = requests.get(
                    f"http://127.0.0.1:{GATEWAY_PORT}/v1/info",
                    headers={"X-Relay-Token": self.token or ""},
                    timeout=2,
                )
                gateway_answered = True
                if not self._poll_logged:
                    self._poll_logged = True
                    self.log_line(f"Gateway self-check: HTTP {r.status_code}.")
                    self.log_line(f"Gateway self-check body: {r.text[:70]!r}")
                data = r.json()
                info_data = data
                hands = bool(data.get("hands_reachable"))
                parser = bool(data.get("parser_reachable"))
            except Exception:
                hands = None
                parser = None
            # Dashboard model (R6): claim snapshot + receipts come from
            # the gateway module in-process (same data /v1/info and
            # /v1/act/queued serve); best-effort — a missing module or
            # a locked table must never break the health poll.
            # R7: the whole dashboard operation is isolated in its
            # own try — any failure here (a junk /v1/info payload, a
            # raising model builder) skips the dashboard for this
            # poll only; health processing and self-heal below
            # always run.
            try:
                claim = queue_list = reserved_for = None
                receipts = {}
                gw = getattr(self, "_gateway_module", None)
                if gw is not None:
                    try:
                        claim, queue_list, reserved_for = gw._claim_snapshot()
                    except Exception:
                        claim = queue_list = reserved_for = None
                    try:
                        table = getattr(gw, "_receipts", None) or {}
                        lk = getattr(gw, "_receipts_lock", None)
                        if lk is not None:
                            # Bounded acquire (R7): a contended lock
                            # skips the snapshot this poll instead of
                            # stalling the poll ahead of self-heal.
                            # Rows are field-copied under the lock so
                            # the builders never read a row a gateway
                            # writer is mutating after release.
                            if lk.acquire(timeout=0.2):
                                try:
                                    receipts = _snapshot_receipt_rows(table)
                                finally:
                                    lk.release()
                        else:
                            receipts = _snapshot_receipt_rows(table)
                    except Exception:
                        receipts = {}
                model = build_dashboard_model(
                    info_data, claim, queue_list, reserved_for, receipts, time.time()
                )
                self.ui_queue.put(("dashboard", model))
            except Exception:
                pass
            # Self-heal: gateway liveness is "HTTP answered at all".
            # If the gateway itself is down, hands/parser health is
            # unknown — note a failure only for the gateway then, so
            # one outage does not cascade-restart everything.
            self._note_health("gateway", gateway_answered)
            if gateway_answered and hands is not None:
                self._note_health("hands", hands)
                self._note_health("parser", parser)
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

        def _run_poll():
            try:
                work()
            finally:
                self._poll_running = False

        threading.Thread(target=_run_poll, daemon=True).start()
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
