"""R9 sweep — #20 foreground auto-pin for held acts, #21 applied_via,
#22 response-integrity header. Windows layer stubbed; logic only."""
import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOKEN = {"X-Relay-Token": "test-token"}
YIELD = {"ok": False, "error": "user active — control yielded", "error_code": "yield"}


def _load(rel, tag):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(tag, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gateway():
    mod = _load("services/gateway/app.py", "r9sweep_gateway")
    mod.TOKEN = "test-token"
    return mod


@pytest.fixture(scope="module")
def hands():
    return _load("hands/muse_relay_hands.py", "r9sweep_hands")


@pytest.fixture
def client(gateway, monkeypatch):
    gateway._receipts.clear()
    gateway._pending_payloads.clear()
    monkeypatch.setattr(gateway, "_ensure_receipt_thread", lambda: None)
    yield gateway.app.test_client()
    gateway._receipts.clear()
    gateway._pending_payloads.clear()


# ------------------------------------------------------------------ #20 hands

def test_focus_matches_hwnd(hands):
    win = {"title": "Chess", "process": "chrome.exe", "_hwnd": 77}
    assert hands._focus_matches({"hwnd": 77}, win) is True
    assert hands._focus_matches({"hwnd": 78}, win) is False
    assert hands._focus_matches({"hwnd": "junk"}, win) is False
    assert hands._focus_matches({"hwnd": 77, "title": "other"}, win) is False


def test_yield_409_carries_foreground_hwnd(hands, monkeypatch):
    monkeypatch.setattr(hands, "_probe_lock_state", lambda: (False, 0.2))
    monkeypatch.setattr(hands, "_enum_windows",
                        lambda: [{"title": "a", "focused": False, "_hwnd": 1},
                                 {"title": "b", "focused": True, "_hwnd": 42}])
    with hands.app.test_request_context("/click", method="POST", json={}):
        resp, status = hands._yield_if_active()
    assert status == 409
    assert resp.get_json()["foreground_hwnd"] == 42
    assert resp.get_json()["error_code"] == "yield"


def test_yield_409_without_foreground_omits_hwnd(hands, monkeypatch):
    monkeypatch.setattr(hands, "_probe_lock_state", lambda: (False, 0.2))
    monkeypatch.setattr(hands, "_enum_windows", lambda: [])
    with hands.app.test_request_context("/click", method="POST", json={}):
        resp, status = hands._yield_if_active()
    assert "foreground_hwnd" not in resp.get_json()


def test_focus_guard_refuses_changed_hwnd(hands, monkeypatch):
    monkeypatch.setattr(hands, "_enum_windows",
                        lambda: [{"title": "chat", "focused": True, "_hwnd": 9}])
    with hands.app.test_request_context(
            "/click", method="POST", json={"x": 1, "y": 1, "expect_focus": {"hwnd": 42}}):
        resp, status = hands._focus_guard()
    assert status == 409
    assert resp.get_json()["error_code"] == "foreground_changed"


# ---------------------------------------------------------------- #20 gateway

def test_held_act_is_pinned_to_reported_hwnd(gateway, client, monkeypatch):
    monkeypatch.setattr(gateway, "_forward_act",
                        lambda op, p: (409, dict(YIELD, foreground_hwnd=42)))
    r = client.post("/v1/act/queued", json={"op": "click", "x": 1, "y": 2}, headers=TOKEN)
    assert r.status_code == 202
    rid = r.get_json()["id"]
    assert gateway._pending_payloads[rid]["expect_focus"] == {"hwnd": 42}
    rec = client.get(f"/v1/act/queued/{rid}", headers=TOKEN).get_json()
    assert rec["pinned_foreground"] is True
    assert rec["param_keys"] == ["x", "y"]


def test_pinned_retry_into_other_window_fails_not_applies(gateway, client, monkeypatch):
    calls = []

    def forward(op, p):
        calls.append(dict(p))
        if len(calls) == 1:
            return 409, dict(YIELD, foreground_hwnd=42)
        assert p["expect_focus"] == {"hwnd": 42}
        return 409, {"ok": False, "error": "foreground changed — act refused",
                     "error_code": "foreground_changed"}

    monkeypatch.setattr(gateway, "_forward_act", forward)
    rid = client.post("/v1/act/queued", json={"op": "click", "x": 1, "y": 2},
                      headers=TOKEN).get_json()["id"]
    out = gateway._pump_receipt(gateway._receipts[rid], 1e12 - 1)
    assert out["state"] == "failed"


def test_caller_expect_focus_wins(gateway, client, monkeypatch):
    monkeypatch.setattr(gateway, "_forward_act",
                        lambda op, p: (409, dict(YIELD, foreground_hwnd=42)))
    rid = client.post("/v1/act/queued",
                      json={"op": "type", "text": "x", "expect_focus": "Chess"},
                      headers=TOKEN).get_json()["id"]
    assert gateway._pending_payloads[rid]["expect_focus"] == "Chess"
    assert gateway._receipts[rid]["pinned_foreground"] is False


def test_focus_op_is_never_pinned(gateway, client, monkeypatch):
    monkeypatch.setattr(gateway, "_forward_act",
                        lambda op, p: (409, dict(YIELD, foreground_hwnd=42)))
    rid = client.post("/v1/act/queued", json={"op": "focus", "title": "Chess"},
                      headers=TOKEN).get_json()["id"]
    assert "expect_focus" not in gateway._pending_payloads[rid]


def test_older_hands_without_hwnd_still_holds_unpinned(gateway, client, monkeypatch):
    monkeypatch.setattr(gateway, "_forward_act", lambda op, p: (409, dict(YIELD)))
    rid = client.post("/v1/act/queued", json={"op": "click", "x": 1, "y": 2},
                      headers=TOKEN).get_json()["id"]
    assert "expect_focus" not in gateway._pending_payloads[rid]
    assert gateway._receipts[rid]["state"] == "held"


# ------------------------------------------------------------------- #21

def test_direct_apply_reports_applied_via_direct(gateway, client, monkeypatch):
    monkeypatch.setattr(gateway, "_forward_act", lambda op, p: (200, {"ok": True}))
    rid = client.post("/v1/act/queued", json={"op": "click", "x": 1, "y": 2},
                      headers=TOKEN).get_json()["id"]
    rec = client.get(f"/v1/act/queued/{rid}", headers=TOKEN).get_json()
    assert rec["state"] == "applied" and rec["applied_via"] == "direct"


def test_held_then_applied_reports_after_hold(gateway, client, monkeypatch):
    seq = [(409, dict(YIELD)), (200, {"ok": True})]
    monkeypatch.setattr(gateway, "_forward_act", lambda op, p: seq.pop(0))
    rid = client.post("/v1/act/queued", json={"op": "click", "x": 1, "y": 2},
                      headers=TOKEN).get_json()["id"]
    out = gateway._pump_receipt(gateway._receipts[rid], 0)
    assert out["state"] == "applied" and out["applied_via"] == "after-hold"


def test_direct_failure_has_no_applied_via(gateway, client, monkeypatch):
    monkeypatch.setattr(gateway, "_forward_act", lambda op, p: (500, {"ok": False}))
    rid = client.post("/v1/act/queued", json={"op": "click", "x": 1, "y": 2},
                      headers=TOKEN).get_json()["id"]
    assert gateway._receipts[rid]["applied_via"] is None


# ------------------------------------------------------------------- #22

def test_every_json_response_carries_body_digest(gateway, client):
    for path in ("/health", "/v1/act/queued", "/v1/act/queued/nope"):
        r = client.get(path, headers=TOKEN)
        data = r.get_data()
        assert data, path
        assert r.headers["X-Body-SHA256"] == hashlib.sha256(data).hexdigest(), path
        assert int(r.headers["Content-Length"]) == len(data), path


def test_unauthorized_response_is_also_marked(client):
    r = client.get("/v1/act/queued")
    assert r.status_code == 401
    assert r.headers["X-Body-SHA256"] == hashlib.sha256(r.get_data()).hexdigest()


def test_torn_body_is_detectable(client):
    r = client.get("/health", headers=TOKEN)
    assert hashlib.sha256(b"").hexdigest() != r.headers["X-Body-SHA256"]
