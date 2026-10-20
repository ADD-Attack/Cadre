"""Tests for the R6 dashboard data layer (wishlist #23, first revision).

The dashboard's model builders are pure functions in
muse_relay_v2_app.py; they are exercised headless with the same
stub-and-importlib-from-file pattern test_app.py uses. RelayApp
itself is never instantiated (it builds a live Tk window).
"""

import importlib.util
import os
import sys
import time
import types

# --- fake tkinter (+ scrolledtext submodule) ------------------------------
_fake_tk = types.ModuleType("tkinter")
_fake_tk.Tk = object
_fake_tk.TclError = Exception
_fake_scrolled = types.ModuleType("tkinter.scrolledtext")
_fake_scrolled.ScrolledText = object
_fake_tk.scrolledtext = _fake_scrolled
sys.modules["tkinter"] = _fake_tk
sys.modules["tkinter.scrolledtext"] = _fake_scrolled

# --- fake pyautogui --------------------------------------------------------
_fake_gui = types.ModuleType("pyautogui")
_fake_gui.FAILSAFE = False
_fake_gui.PAUSE = 0
sys.modules["pyautogui"] = _fake_gui


def _load_app():
    path = os.path.join(os.path.dirname(__file__), "..", "muse_relay_v2_app.py")
    name = "muse_relay_v2_app_r6"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


APP = _load_app()

NOW = 1792454000.0


def _receipt(rid, op, state, age_s, **extra):
    r = {
        "id": rid,
        "op": op,
        "state": state,
        "submitted_at": NOW - age_s,
        "updated_at": NOW - age_s,
        "hold_seconds": 25,
        "hands_status": 200,
        "result": None,
    }
    r.update(extra)
    return r


def test_fmt_duration():
    assert APP._fmt_duration(5) == "5s"
    assert APP._fmt_duration(59) == "59s"
    assert APP._fmt_duration(65) == "1m 05s"
    assert APP._fmt_duration(600) == "10m 00s"
    assert APP._fmt_duration(3661) == "1h 01m"
    assert APP._fmt_duration(-3) == "0s"
    assert APP._fmt_duration(None) == "?"


def test_summarize_receipts_orders_and_limits():
    receipts = {
        "a": _receipt("aaabbbcc", "click", "applied", 50),
        "b": _receipt("bbaabbcc", "type", "held", 5),
        "c": _receipt("ccbbccdd", "move", "applied", 30),
    }
    rows = APP.summarize_receipts(receipts, NOW)
    assert [r["id8"] for r in rows] == ["bbaabbcc", "ccbbccdd", "aaabbbcc"]
    assert rows[0]["op"] == "type" and rows[0]["state"] == "held"
    assert rows[0]["age_s"] == 5
    assert len(APP.summarize_receipts(receipts, NOW, limit=2)) == 2


def test_summarize_receipts_skips_junk():
    receipts = {
        "ok": _receipt("aaabbbcc", "click", "applied", 10),
        "junk": {"id": None, "op": "click"},
        "nope": "not-a-dict",
        "missing": {"id": "zz", "op": "move", "state": "applied"},
    }
    rows = APP.summarize_receipts(receipts, NOW)
    assert len(rows) == 1
    assert rows[0]["id8"] == "aaabbbcc"


def test_summarize_receipts_empty():
    assert APP.summarize_receipts({}, NOW) == []
    assert APP.summarize_receipts(None, NOW) == []


def test_receipt_state_counts():
    receipts = {
        "a": _receipt("aa", "click", "applied", 1),
        "b": _receipt("bb", "type", "applied", 2),
        "c": _receipt("cc", "move", "held", 3),
        "junk": "x",
    }
    assert APP.receipt_state_counts(receipts) == {"applied": 2, "held": 1}
    assert APP.receipt_state_counts({}) == {}


def _full_info(**over):
    info = {
        "ok": True,
        "hands_url": "http://127.0.0.1:5000",
        "hands_secret_configured": True,
        "hands_reachable": True,
        "parser_url": "http://127.0.0.1:5011",
        "parser_reachable": True,
        "hands_claim": None,
        "pc_state": {
            "ok": True,
            "platform": "windows",
            "locked": False,
            "idle_seconds": 42.0,
            "probe_failures": 0,
            "probe_ok": True,
        },
    }
    info.update(over)
    return info


def test_model_all_healthy():
    claim = {
        "holder": "main",
        "purpose": "chess benchmark",
        "since": NOW - 600,
        "expires_at": NOW + 1200,
    }
    receipts = {"a": _receipt("a20255f1", "click", "applied", 12)}
    model = APP.build_dashboard_model(_full_info(), claim, [], None, receipts, NOW)
    assert model["services"] == {"gateway": "ok", "hands": "ok", "parser": "ok"}
    assert model["claim"]["holder"] == "main"
    assert model["claim"]["purpose"] == "chess benchmark"
    assert abs(model["claim"]["expires_in_s"] - 1200) < 1
    assert model["queue_len"] == 0 and model["reserved_for"] is None
    assert model["pc"]["probe_state"] == "ok"
    assert model["pc"]["locked"] is False
    assert model["feed"][0]["id8"] == "a20255f1"
    assert model["counts"] == {"applied": 1}


def test_model_gateway_down_and_pc_degraded():
    model = APP.build_dashboard_model(None, None, None, None, {}, NOW)
    assert model["services"] == {
        "gateway": "down",
        "hands": "unknown",
        "parser": "unknown",
    }
    assert model["pc"] is None
    assert model["claim"] is None

    info = _full_info(
        hands_reachable=False,
        parser_reachable=False,
        pc_state={
            "ok": True,
            "platform": "windows",
            "locked": True,
            "idle_seconds": 65.0,
            "probe_failures": 3,
            "probe_ok": False,
        },
    )
    model = APP.build_dashboard_model(
        info,
        None,
        [{"holder": "forge", "purpose": "", "enqueued_at": NOW}],
        "forge",
        {},
        NOW,
    )
    assert model["services"]["hands"] == "down"
    assert model["pc"]["probe_state"] == "degraded"
    assert model["pc"]["probe_failures"] == 3
    assert model["pc"]["locked"] is True
    assert model["queue_len"] == 1
    assert model["reserved_for"] == "forge"


def test_model_claimless_and_probe_unknown():
    info = _full_info(pc_state=None)
    model = APP.build_dashboard_model(info, None, [], None, {}, NOW)
    assert model["claim"] is None
    assert model["pc"] is None


def test_format_diagnostics_healthy():
    model = APP.build_dashboard_model(
        _full_info(),
        {"holder": "main", "purpose": "chess benchmark", "expires_at": NOW + 720},
        [],
        None,
        {"a": _receipt("a20255f1", "click", "applied", 12)},
        NOW,
    )
    text = APP.format_diagnostics(model, "19:42:07")
    assert "Muse Relay diagnostics — 19:42:07" in text
    assert "gateway ok" in text and "hands ok" in text and "parser ok" in text
    assert "main — chess benchmark" in text
    assert "expires in 12m 00s" in text
    assert "unlocked" in text and "owner idle 42s" in text
    assert "yield probe OK" in text
    assert "Receipts: 1 total — applied 1" in text


def test_format_diagnostics_gateway_down():
    model = APP.build_dashboard_model(None, None, None, None, {}, NOW)
    text = APP.format_diagnostics(model, "19:42:07")
    assert "gateway down" in text
    assert "Claim: none" in text
    assert "PC: unknown (hands unreachable)" in text
    assert "Receipts: none yet" in text
