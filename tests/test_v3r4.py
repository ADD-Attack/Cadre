"""Muse Relay v3 R4 improvement-round tests.

Covers: F2 (pyautogui.PAUSE), F3 (expect_focus guard), F4 (receipt
for every queued act + terminal-first eviction), F5 (/break and
/clipboard/set behind the yield), F6 (locked desktop yields), F7
(mid-type abort), F11 (structured error_code classification),
F12 (parser non-JSON guard). Loads the service modules by path,
mirroring tests/test_v3r2_remaining.py.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(rel, tag="v3r4"):
    path = ROOT / rel
    name = tag + "_" + "_".join(path.with_suffix("").parts[-3:])
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gateway():
    mod = _load("services/gateway/app.py")
    mod.TOKEN = "test-token"
    return mod


@pytest.fixture(scope="module")
def hands():
    return _load("hands/muse_relay_hands.py")


def _status(resp):
    return resp[1] if isinstance(resp, tuple) else resp.status_code


def _body(resp):
    return resp[0].get_json() if isinstance(resp, tuple) else resp.get_json()


# ------------------------------------------------------------------ F2

def test_pause_is_zero_after_hands_import():
    pag = sys.modules["pyautogui"]
    pag.PAUSE = 0.15  # the old global tax; importing the hands must clear it
    _load("hands/muse_relay_hands.py", tag="v3r4_pause")
    assert pag.PAUSE == 0


# ------------------------------------------------------------- F5 + F6

def test_break_and_clipboard_set_are_act_paths(hands):
    assert "/break" in hands._ACT_PATHS
    assert "/clipboard/set" in hands._ACT_PATHS


def test_break_yields_while_owner_active(hands, monkeypatch):
    monkeypatch.setattr(hands, "_probe_lock_state", lambda: (False, 0.2))
    monkeypatch.delenv("HANDS_YIELD_IDLE_SECONDS", raising=False)
    calls = []
    monkeypatch.setattr(hands.pyautogui, "hotkey", lambda *a, **k: calls.append(a))
    with hands.app.test_request_context("/break", method="POST", json={}):
        resp = hands.break_()
    assert _status(resp) == 409
    assert _body(resp)["error_code"] == "yield"
    assert calls == []


def test_locked_desktop_yields(hands, monkeypatch):
    # Locked with a huge idle: before R4 this "applied" into the
    # Winlogon desktop and reported success.
    monkeypatch.setattr(hands, "_probe_lock_state", lambda: (True, 999.0))
    called = {"down": 0}
    monkeypatch.setattr(
        hands.pyautogui, "mouseDown", lambda **k: called.__setitem__("down", 1)
    )
    with hands.app.test_request_context(
        "/drag", method="POST", json={"x1": 0, "y1": 0, "x2": 1, "y2": 1, "duration": 0}
    ):
        resp = hands.drag()
    assert _status(resp) == 409
    assert _body(resp)["error_code"] == "locked"
    assert called["down"] == 0


def test_yield_response_carries_error_code(hands, monkeypatch):
    monkeypatch.setattr(hands, "_probe_lock_state", lambda: (False, 0.2))
    monkeypatch.delenv("HANDS_YIELD_IDLE_SECONDS", raising=False)
    with hands.app.test_request_context(
        "/move", method="POST", headers={"X-Secret": hands.SHARED_SECRET}
    ):
        resp = hands.gate()
    assert _status(resp) == 409
    assert _body(resp)["error_code"] == "yield"


# ------------------------------------------------------------------ F3

def _stub_foreground(hands, monkeypatch, title="Muse — Chat", process="chrome.exe"):
    monkeypatch.setattr(
        hands,
        "_enum_windows",
        lambda: [{"title": title, "process": process, "focused": True}],
    )
    monkeypatch.setattr(hands, "_probe_lock_state", lambda: (None, None))


def test_focus_guard_refuses_wrong_window(hands, monkeypatch):
    _stub_foreground(hands, monkeypatch)
    with hands.app.test_request_context(
        "/click",
        method="POST",
        json={"x": 1, "y": 2, "expect_focus": "Chess Analysis"},
        headers={"X-Secret": hands.SHARED_SECRET},
    ):
        resp = hands.gate()
    assert _status(resp) == 409
    assert _body(resp)["error_code"] == "foreground_changed"


def test_focus_guard_allows_matching_window(hands, monkeypatch):
    _stub_foreground(hands, monkeypatch)
    with hands.app.test_request_context(
        "/click",
        method="POST",
        json={"x": 1, "y": 2, "expect_focus": {"title": "Muse", "process": "chrome"}},
        headers={"X-Secret": hands.SHARED_SECRET},
    ):
        assert hands.gate() is None


def test_focus_guard_inert_without_expectation(hands, monkeypatch):
    _stub_foreground(hands, monkeypatch)
    with hands.app.test_request_context(
        "/click",
        method="POST",
        json={"x": 1, "y": 2},
        headers={"X-Secret": hands.SHARED_SECRET},
    ):
        assert hands.gate() is None


def test_focus_guard_fails_closed_when_foreground_unknown(hands, monkeypatch):
    monkeypatch.setattr(hands, "_enum_windows", lambda: [])
    monkeypatch.setattr(hands, "_probe_lock_state", lambda: (None, None))
    with hands.app.test_request_context(
        "/click",
        method="POST",
        json={"x": 1, "y": 2, "expect_focus": "Anything"},
        headers={"X-Secret": hands.SHARED_SECRET},
    ):
        resp = hands.gate()
    assert _status(resp) == 409
    assert _body(resp)["error_code"] == "foreground_changed"


def test_focus_matches_units(hands):
    win = {"title": "Chess Analysis — Chess.com", "process": "chrome.exe"}
    assert hands._focus_matches("chess analysis", win)
    assert hands._focus_matches({"process": "CHROME"}, win)
    assert not hands._focus_matches("Calculator", win)
    assert not hands._focus_matches({}, win)
    assert not hands._focus_matches("chess", None)


# ------------------------------------------------------------------ F7

def test_type_aborts_midway_when_owner_activates(hands, monkeypatch):
    # R7.2 (wishlist #27): the re-check no longer consults the idle
    # probe — GetLastInputInfo counts the type's own keystrokes, so
    # the old fake (idle drops at the 24-char re-check) scripted the
    # type aborting on ITSELF. The scenario is unchanged (the owner
    # sits down mid-type; the type aborts at the next 12-char
    # boundary with the honest partial), but it is driven through the
    # dwTime seam: our writes stamp the tick, and the owner's key
    # stamps it during the pause after char 18.
    state = {"tick": 100000, "dw": 94999, "sleeps": 0}

    def probe_dwtime():
        return state["dw"]

    def write(*a, **k):
        writes.append(1)
        state["tick"] += 10
        state["dw"] = state["tick"]  # our keystroke is the freshest input

    def sleep(_s):
        state["sleeps"] += 1
        if state["sleeps"] == 18:
            state["tick"] += 10
            state["dw"] = state["tick"]  # the owner just sat down

    monkeypatch.setattr(hands, "_probe_lock_state", lambda: (None, None))
    monkeypatch.setattr(hands, "_probe_dwtime", probe_dwtime)
    monkeypatch.setattr(hands.time, "sleep", sleep)
    writes = []
    monkeypatch.setattr(hands.pyautogui, "write", write)
    with hands.app.test_request_context(
        "/type",
        method="POST",
        json={"text": "x" * 40, "method": "keys", "jitter": True},
    ):
        resp = hands.type_text()
    body = _body(resp)
    assert _status(resp) == 409
    assert body["error_code"] == "type_aborted"
    assert body["chars_typed"] == 24
    assert len(writes) == 24
    # The abort must NOT be yield-classified by either mechanism, or a
    # queued retry would re-type the whole payload.
    assert "yield" not in body["error"]
    assert "user active" not in body["error"]


def test_type_completes_when_owner_stays_away(hands, monkeypatch):
    monkeypatch.setattr(hands, "_probe_lock_state", lambda: (None, None))
    monkeypatch.setattr(hands.time, "sleep", lambda s: None)
    writes = []
    monkeypatch.setattr(
        hands.pyautogui, "write", lambda *a, **k: writes.append(1)
    )
    with hands.app.test_request_context(
        "/type",
        method="POST",
        json={"text": "y" * 30, "method": "keys", "jitter": True},
    ):
        resp = hands.type_text()
    body = _body(resp)
    assert body["ok"] is True
    assert body["chars"] == 30
    assert len(writes) == 30


# ----------------------------------------------------------------- F11

def test_yield_conflict_prefers_error_code(gateway):
    f = gateway._is_yield_conflict
    assert f(409, {"error": "desktop locked", "error_code": "locked"}) is True
    assert f(409, {"error": "user active", "error_code": "yield"}) is True
    # The latent prose trap: text says "user active" but the code says
    # this is a hard refusal — the code wins.
    assert (
        f(
            409,
            {
                "error": "user active window could not be focused",
                "error_code": "foreground_changed",
            },
        )
        is False
    )
    assert (
        f(409, {"error": "typing aborted", "error_code": "type_aborted"}) is False
    )


def test_yield_conflict_substring_fallback(gateway):
    f = gateway._is_yield_conflict
    assert f(409, {"error": "user active — control yielded"}) is True
    assert f(409, {"error": "desktop locked — control yielded"}) is True
    assert f(409, {"error": "boom"}) is False
    assert f(200, {"error": "user active", "error_code": "yield"}) is False
    assert f(409, {"error": None}) is False


def test_pump_holds_on_locked_code(gateway, monkeypatch):
    receipt = {
        "id": "r-lock",
        "state": "held",
        "op": "click",
        "deadline": 1100.0,
        "updated_at": 0,
    }
    gateway._pending_payloads["r-lock"] = {"x": 1}
    monkeypatch.setattr(
        gateway,
        "_forward_act",
        lambda op, payload: (
            409,
            {
                "ok": False,
                "error": "desktop locked — control yielded",
                "error_code": "locked",
            },
        ),
    )
    out = gateway._pump_receipt(receipt, 1000.0)
    assert out["state"] == "held"
    assert "r-lock" in gateway._pending_payloads
    gateway._pending_payloads.pop("r-lock", None)


def test_pump_fails_on_foreground_code_despite_prose(gateway, monkeypatch):
    receipt = {
        "id": "r-fg",
        "state": "held",
        "op": "click",
        "deadline": 1100.0,
        "updated_at": 0,
    }
    gateway._pending_payloads["r-fg"] = {"x": 1}
    monkeypatch.setattr(
        gateway,
        "_forward_act",
        lambda op, payload: (
            409,
            {
                "ok": False,
                "error": "user active window could not be focused",
                "error_code": "foreground_changed",
            },
        ),
    )
    out = gateway._pump_receipt(receipt, 1000.0)
    assert out["state"] == "failed"
    gateway._pending_payloads.pop("r-fg", None)


# ------------------------------------------------------------------ F4

def _queued_client(gateway, monkeypatch, forward):
    gateway._receipts.clear()
    gateway._pending_payloads.clear()
    monkeypatch.setattr(gateway, "_forward_act", forward)
    monkeypatch.setattr(gateway, "_ensure_receipt_thread", lambda: None)
    return gateway.app.test_client()


def test_queued_direct_apply_files_receipt(gateway, monkeypatch):
    client = _queued_client(
        gateway, monkeypatch, lambda op, payload: (200, {"ok": True})
    )
    resp = client.post(
        "/v1/act/queued",
        json={"op": "click", "x": 1, "y": 2},
        headers={"X-Relay-Token": "test-token"},
    )
    assert resp.status_code == 200
    rid = resp.get_json()["id"]
    assert gateway._receipts[rid]["state"] == "applied"
    assert rid not in gateway._pending_payloads
    got = client.get(
        f"/v1/act/queued/{rid}", headers={"X-Relay-Token": "test-token"}
    )
    assert got.status_code == 200
    assert got.get_json()["state"] == "applied"


def test_queued_direct_failure_files_receipt_failed(gateway, monkeypatch):
    client = _queued_client(
        gateway,
        monkeypatch,
        lambda op, payload: (500, {"ok": False, "error": "hands exploded"}),
    )
    resp = client.post(
        "/v1/act/queued",
        json={"op": "click", "x": 1, "y": 2},
        headers={"X-Relay-Token": "test-token"},
    )
    assert resp.status_code == 500
    rid = resp.get_json()["id"]
    assert gateway._receipts[rid]["state"] == "failed"


def test_queued_yield_still_holds_with_payload(gateway, monkeypatch):
    client = _queued_client(
        gateway,
        monkeypatch,
        lambda op, payload: (
            409,
            {
                "ok": False,
                "error": "user active — control yielded",
                "error_code": "yield",
            },
        ),
    )
    resp = client.post(
        "/v1/act/queued",
        json={"op": "click", "x": 1, "y": 2},
        headers={"X-Relay-Token": "test-token"},
    )
    assert resp.status_code == 202
    rid = resp.get_json()["id"]
    assert gateway._receipts[rid]["state"] == "held"
    assert gateway._pending_payloads[rid] == {"x": 1, "y": 2}


def test_receipt_eviction_prefers_terminal(gateway):
    gateway._receipts.clear()
    gateway._pending_payloads.clear()
    held = {"id": "held-0", "state": "held", "op": "click"}
    gateway._store_receipt(held, {"x": 1})
    for i in range(gateway.RECEIPT_MAX):
        gateway._store_receipt(
            {"id": f"t-{i}", "state": "applied", "op": "click"}
        )
    gateway._store_receipt({"id": "t-new", "state": "applied", "op": "click"})
    assert "held-0" in gateway._receipts
    assert gateway._pending_payloads.get("held-0") == {"x": 1}
    assert "t-new" in gateway._receipts
    assert len(gateway._receipts) == gateway.RECEIPT_MAX
    gateway._receipts.clear()
    gateway._pending_payloads.clear()


# ----------------------------------------------------------------- F12

class _NonJsonResp:
    status_code = 500

    def json(self):
        raise ValueError("no json")


def test_parse_non_json_parser_reply_is_json_error(gateway, monkeypatch):
    gateway.TOKEN = "test-token"
    monkeypatch.setattr(
        gateway.requests, "post", lambda *a, **k: _NonJsonResp()
    )
    client = gateway.app.test_client()
    resp = client.post(
        "/v1/parse",
        json={"image_b64": "AAAA"},
        headers={"X-Relay-Token": "test-token"},
    )
    assert resp.status_code == 500
    body = resp.get_json()
    assert body["ok"] is False
    assert body["error"] == "parser returned 500"


def test_find_non_json_parser_reply_is_json_error(gateway, monkeypatch):
    gateway.TOKEN = "test-token"
    monkeypatch.setattr(
        gateway.requests, "post", lambda *a, **k: _NonJsonResp()
    )
    client = gateway.app.test_client()
    resp = client.post(
        "/v1/find",
        json={"image_b64": "AAAA", "text": "OK"},
        headers={"X-Relay-Token": "test-token"},
    )
    assert resp.status_code == 500
    assert resp.get_json()["error"] == "parser returned 500"
