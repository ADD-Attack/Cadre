"""R9 Stage 3 — the relay window as a local web UI (wishlist #23).

Drives RelayApp + build_ui_server headless through Flask's test
client (no window, no services). The native pywebview shell and the
look itself need the real desktop — see docs/VERIFICATION.md "R9 web
GUI".
"""
import importlib.util
import queue
import re
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
KEY = "k" * 43
HOST = {"Host": "127.0.0.1:5999"}
H = {"X-UI-Key": KEY, **HOST}


@pytest.fixture(scope="module")
def appmod():
    spec = importlib.util.spec_from_file_location("r9_gui_app", ROOT / "muse_relay_v2_app.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Root:
    def __init__(self):
        self.after_calls = []

    def after(self, ms, fn, *args):
        self.after_calls.append((ms, fn))


@pytest.fixture
def relay(appmod, monkeypatch):
    monkeypatch.setattr(appmod, "_autostart_enabled", lambda: False)
    r = appmod.RelayApp(_Root())
    r._drain_queue_once = lambda: appmod.RelayApp._drain_queue(r)
    return r


@pytest.fixture
def client(appmod, relay):
    ui = appmod.build_ui_server(relay, KEY, [5999])
    return ui.test_client()


def _drain(relay):
    relay._drain_queue_once()


# ------------------------------------------------------------ one GUI

def test_app_has_no_tk_and_no_autostart_of_services(appmod, relay):
    src = (ROOT / "muse_relay_v2_app.py").read_text(encoding="utf-8")
    assert "import tkinter" not in src and "from tkinter" not in src
    assert not hasattr(appmod, "tk")
    _drain(relay)
    v = relay.view()
    assert v["started"] is False and relay.servers == {}
    assert any("Press Start" in e["line"] for e in v["log"])
    assert all("not started" in t for t in v["status"].values())


def test_build_bundles_ui_motion_and_webview():
    bat = (ROOT / "build_app.bat").read_text(encoding="utf-8")
    assert '--add-data "ui;ui"' in bat
    assert '--add-data "hands\\motion.py;hands"' in bat
    assert "pywebview" in bat and "--hidden-import webview" in bat


# ------------------------------------------------------- server guards

def test_api_requires_ui_key(client):
    assert client.get("/api/state", headers=HOST).status_code == 401
    assert client.get("/api/state", headers={"X-UI-Key": "wrong", **HOST}).status_code == 401
    assert client.get("/api/state", headers=H).status_code == 200


def test_foreign_host_rejected(client):
    r = client.get("/api/state", headers={"X-UI-Key": KEY, "Host": "evil.example:5999"})
    assert r.status_code == 403
    r = client.get("/api/state", headers={"X-UI-Key": KEY, "Host": "127.0.0.1:6000"})
    assert r.status_code == 403  # wrong port: not this window's server


def test_index_and_assets_served_with_csp(client):
    r = client.get("/", headers=HOST)
    assert r.status_code == 200 and b"Muse Relay" in r.data
    csp = r.headers["Content-Security-Policy"]
    assert "script-src 'self'" in csp and "unsafe-inline" not in csp
    assert r.headers["Cache-Control"] == "no-store"
    for name in ("app.js", "app.css"):
        assert client.get(f"/assets/{name}", headers=HOST).status_code == 200
    assert client.get("/assets/../muse_relay_v2_app.py", headers=HOST).status_code == 404


def test_page_has_no_inline_script_or_handlers_and_js_never_uses_innerhtml():
    html = (ROOT / "ui/index.html").read_text(encoding="utf-8")
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html)
    assert not re.search(r"\son[a-z]+\s*=", html)
    js = (ROOT / "ui/app.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js and "outerHTML" not in js and "insertAdjacentHTML" not in js
    assert "eval(" not in js


# ------------------------------------------------------------- state

def test_state_log_paging(client, relay):
    relay.log_line("one")
    relay.log_line("two")
    _drain(relay)
    v = client.get("/api/state", headers=H).get_json()
    seq = v["log_seq"]
    assert [e["line"].split("] ", 1)[1] for e in v["log"]][-2:] == ["one", "two"]
    relay.log_line("three")
    _drain(relay)
    v2 = client.get(f"/api/state?since={seq}", headers=H).get_json()
    assert [e["line"].split("] ", 1)[1] for e in v2["log"]] == ["three"]


def test_status_updates_reach_view(client, relay):
    relay.set_status("hands", "Hands (:5000): reachable")
    _drain(relay)
    assert client.get("/api/state", headers=H).get_json()["status"]["hands"] == "Hands (:5000): reachable"


def test_log_is_bounded(appmod, relay):
    for i in range(appmod.LOG_KEEP + 50):
        relay._append_log(f"l{i}")
    assert len(relay._log) == appmod.LOG_KEEP


def test_drain_always_reschedules(relay):
    relay.ui_queue.put(("status", ("nope", "x")))  # bad target
    relay.ui_queue.put(("log", "after"))
    before = len(relay.root.after_calls)
    _drain(relay)
    assert len(relay.root.after_calls) == before + 1
    lines = [l for _, l in relay._log]
    assert any("UI update skipped (status)" in l for l in lines)
    assert "after" in lines


# ------------------------------------------------------------- start/stop

def test_start_only_on_explicit_request(client, relay, monkeypatch):
    calls = []
    monkeypatch.setattr(relay, "_start_all", lambda: calls.append(1))

    class T:
        def __init__(self, target=None, **k):
            self.t = target

        def start(self):
            self.t()

    monkeypatch.setattr(threading, "Thread", T)
    assert calls == []
    assert client.post("/api/start", headers=H).get_json()["ok"]
    assert calls == [1]
    relay._started = True
    assert client.post("/api/start", headers=H).get_json()["already"] is True
    assert calls == [1]


def test_stop_is_scheduled_after_answer(client, relay):
    r = client.post("/api/stop", headers=H)
    assert r.get_json()["ok"]
    assert any(fn == relay.stop for _, fn in relay.root.after_calls)


def test_stop_is_reentrant_safe(appmod, relay, monkeypatch):
    exits = []
    monkeypatch.setattr(appmod.os, "_exit", lambda code: exits.append(code))
    quits = []
    relay.on_quit = lambda: (quits.append(1), relay.stop())  # window-close re-enters
    relay.stop()
    assert quits == [1] and exits == [0]


# ------------------------------------------------------------- token

def test_token_flow(client, relay):
    r = client.get("/api/token", headers=H)
    assert r.status_code == 409
    relay.token = "abcd" * 8
    assert client.get("/api/token", headers=H).get_json()["token"] == "abcd" * 8
    v = client.get("/api/state", headers=H).get_json()
    assert v["token_ready"] is True
    assert "abcd" * 8 not in str(v)  # state never carries the token


def test_start_all_sets_token_without_logging_it(appmod, relay, monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "_load_or_create_hands_secret", lambda: ("h" * 40, "saved"))
    monkeypatch.setattr(appmod, "_load_or_create_gateway_token", lambda: ("t" * 32, "created"))
    monkeypatch.setattr(relay, "_start_one", lambda name: None)
    appmod.RelayApp._start_all(relay)
    _drain(relay)
    assert relay.token == "t" * 32 and relay._started
    assert all("t" * 32 not in l and "h" * 40 not in l for _, l in relay._log)


# ------------------------------------------------------- diagnostics

def test_diagnostics_before_and_after_model(appmod, client, relay):
    assert client.post("/api/diagnostics", headers=H).status_code == 409
    relay._last_model = appmod.build_dashboard_model(None, None, None, None, {}, 0)
    body = client.post("/api/diagnostics", headers=H).get_json()
    assert body["ok"] and "Muse Relay diagnostics" in body["text"]


def test_model_carries_r9_desktop_fields(appmod):
    info = {
        "hands_reachable": True, "parser_reachable": True,
        "pc_state": {"locked": False, "idle_seconds": 1.0, "probe_ok": True, "probe_failures": 0,
                     "owner_idle_seconds": 90.0, "display_asleep": False, "human_motion": True,
                     "jiggler": {"enabled": True, "active": True, "moves": 4, "owner_kills": 1}},
    }
    m = appmod.build_dashboard_model(info, None, [], None, {}, 0)
    assert m["pc"]["owner_idle_seconds"] == 90.0
    assert m["pc"]["jiggler"] == {"enabled": True, "active": True, "moves": 4, "owner_kills": 1}
    text = appmod.format_diagnostics(m, "x")
    assert "Desktop: display on · jiggler drifting" in text
    junk = dict(info, pc_state=dict(info["pc_state"], jiggler="on", display_asleep="no",
                                    owner_idle_seconds=float("nan")))
    m = appmod.build_dashboard_model(junk, None, [], None, {}, 0)
    assert m["pc"]["jiggler"] is None and m["pc"]["display_asleep"] is None
    assert m["pc"]["owner_idle_seconds"] is None


# ----------------------------------------------------------- autostart

def test_autostart_toggle(appmod, client, relay, monkeypatch):
    calls = []
    monkeypatch.setattr(appmod, "_set_autostart", lambda e: calls.append(e) or True)
    assert client.post("/api/autostart", json={"enabled": True}, headers=H).get_json()["ok"]
    assert calls == [True]
    assert client.post("/api/autostart", json={"enabled": "yes"}, headers=H).status_code == 400


# ------------------------------------------------------------- jiggler

def test_jiggler_needs_started_services(client):
    r = client.post("/api/jiggler", json={"enabled": True}, headers=H)
    assert r.status_code == 409


def test_jiggler_goes_through_hands_route_with_secret(appmod, client, relay, monkeypatch):
    relay._started = True
    relay._hands_secret = "s" * 40
    seen = {}

    class R:
        status_code = 200

        def json(self):
            return {"ok": True}

    def post(url, json=None, headers=None, timeout=None):
        seen.update(url=url, json=json, headers=headers)
        return R()

    monkeypatch.setattr(appmod.requests, "post", post)
    assert client.post("/api/jiggler", json={"enabled": True}, headers=H).get_json()["ok"]
    assert seen["url"].endswith("/jiggler") and seen["json"] == {"enabled": True}
    assert seen["headers"] == {"X-Secret": "s" * 40}


# ------------------------------------------------------------ elevation

class _Hands:
    def __init__(self):
        self._elevations = {}
        self._elevations_lock = threading.Lock()
        self.elevate_queue = queue.Queue()
        self.log_queue = queue.Queue()
        self.calls = []

    def request(self, eid):
        self._elevations[eid] = {"state": "pending"}
        self.elevate_queue.put({"id": eid, "name": "fw-rule", "exe": "netsh.exe", "args": "advfirewall"})

    def _resolve_elevation(self, eid, approved):
        self.calls.append((eid, approved))
        self._elevations[eid]["state"] = "approved" if approved else "denied"
        return True


def test_elevation_shown_then_resolved_only_by_window(client, relay):
    hands = _Hands()
    relay._hands_module = hands
    hands.request("e1")
    _drain(relay)
    v = client.get("/api/state", headers=H).get_json()
    assert [e["id"] for e in v["elevations"]] == ["e1"]
    assert v["elevations"][0]["exe"] == "netsh.exe"
    assert hands.calls == []  # nothing is approved by showing it
    assert relay._elevation_dialog_open is True
    r = client.post("/api/elevation/e1", json={"approved": "yes"}, headers=H)
    assert r.status_code == 400 and hands.calls == []
    r = client.post("/api/elevation/e1", json={"approved": False}, headers=H)
    assert r.get_json() == {"ok": True, "state": "denied"}
    assert hands.calls == [("e1", False)]
    assert client.post("/api/elevation/e1", json={"approved": True}, headers=H).status_code == 404
    assert hands.calls == [("e1", False)]
    assert relay._elevation_dialog_open is False


def test_elevation_requires_ui_key(client, relay):
    hands = _Hands()
    relay._hands_module = hands
    hands.request("e2")
    _drain(relay)
    assert client.post("/api/elevation/e2", json={"approved": True}, headers=HOST).status_code == 401
    assert hands.calls == []


def test_expired_elevation_card_is_withdrawn(client, relay):
    hands = _Hands()
    relay._hands_module = hands
    hands.request("e3")
    _drain(relay)
    hands._elevations["e3"]["state"] = "expired"  # hands TTL ran out
    _drain(relay)
    assert client.get("/api/state", headers=H).get_json()["elevations"] == []
    assert any("no decision made in time" in l for _, l in relay._log)


def test_pending_elevation_blocks_hands_restart(appmod, relay):
    relay._elevation_dialog_open = True
    assert appmod.RelayApp._skip_restart(relay, "hands") is True
