"""R9 wishlist #13 — display-sleep fields on /state (logic only; Windows stubbed)."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def hands():
    path = ROOT / "hands/muse_relay_hands.py"
    spec = importlib.util.spec_from_file_location("r9_display_hands", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _raw(hands, monkeypatch, ss, timeout):
    monkeypatch.setattr(hands, "_probe_display_raw",
                        lambda: {"screensaver": ss, "display_off_after_seconds": timeout})


def test_display_asleep_when_idle_past_timeout(hands, monkeypatch):
    _raw(hands, monkeypatch, False, 600)
    assert hands._display_state(601.0)["display_asleep"] is True


def test_display_awake_before_timeout(hands, monkeypatch):
    _raw(hands, monkeypatch, False, 600)
    assert hands._display_state(5.0)["display_asleep"] is False


def test_timeout_zero_means_never(hands, monkeypatch):
    _raw(hands, monkeypatch, None, 0)
    assert hands._display_state(99999.0)["display_asleep"] is False


def test_unknown_inputs_report_none(hands, monkeypatch):
    _raw(hands, monkeypatch, None, None)
    assert hands._display_state(10.0) == {
        "screensaver": None, "display_off_after_seconds": None, "display_asleep": None}
    _raw(hands, monkeypatch, True, 600)
    assert hands._display_state(None)["display_asleep"] is None


def test_probe_exception_is_contained(hands, monkeypatch):
    def boom():
        raise OSError("x")
    monkeypatch.setattr(hands, "_probe_display_raw", boom)
    assert hands._display_state(1.0)["display_asleep"] is None


def test_non_windows_raw_is_none(hands, monkeypatch):
    monkeypatch.setattr(hands.os, "name", "posix")
    assert hands._probe_display_raw() == {"screensaver": None, "display_off_after_seconds": None}


def test_state_endpoint_carries_fields(hands, monkeypatch):
    monkeypatch.setattr(hands, "_probe_lock_state", lambda: (False, 700.0))
    _raw(hands, monkeypatch, False, 600)
    body = hands.state()
    assert body["display_asleep"] is True
    assert body["screensaver"] is False
    assert body["display_off_after_seconds"] == 600
    assert "probe_ok" in body
