"""Muse Relay v3 R5 tests — F10 probe-health accounting.

The wrapper counts consecutive FULL probe failures (locked and idle
both None) on Windows only, flips probe_ok at 3, logs once per
degradation (edge-triggered), and resets on any successful or partial
probe. /state carries the health fields.
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(rel):
    path = ROOT / rel
    name = "v3r5_" + "_".join(path.with_suffix("").parts[-3:])
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def hands():
    return _load("hands/muse_relay_hands.py")


@pytest.fixture(autouse=True)
def _reset_health(hands):
    hands._probe_failures = 0
    hands._probe_degraded_logged = False
    yield
    hands._probe_failures = 0
    hands._probe_degraded_logged = False


def _as_windows(hands, monkeypatch, raw):
    monkeypatch.setattr(hands.os, "name", "nt")
    monkeypatch.setattr(hands, "_probe_lock_state_raw", raw)
    logs = []
    monkeypatch.setattr(hands, "log_line", lambda msg: logs.append(msg))
    monkeypatch.setattr(hands, "file_log", lambda msg: None)
    return logs


def test_failures_accumulate_and_flip_probe_ok(hands, monkeypatch):
    _as_windows(hands, monkeypatch, lambda: (None, None))
    hands._probe_lock_state()
    hands._probe_lock_state()
    assert hands._probe_health() == {"probe_failures": 2, "probe_ok": True}
    hands._probe_lock_state()
    assert hands._probe_health() == {"probe_failures": 3, "probe_ok": False}


def test_degradation_logs_once_per_episode(hands, monkeypatch):
    logs = _as_windows(hands, monkeypatch, lambda: (None, None))
    for _ in range(6):
        hands._probe_lock_state()
    assert len(logs) == 1
    assert "DEGRADED" in logs[0]
    # Recovery clears the flag: a NEW degradation logs again.
    monkeypatch.setattr(hands, "_probe_lock_state_raw", lambda: (False, 42.0))
    hands._probe_lock_state()
    assert hands._probe_health() == {"probe_failures": 0, "probe_ok": True}
    monkeypatch.setattr(hands, "_probe_lock_state_raw", lambda: (None, None))
    for _ in range(3):
        hands._probe_lock_state()
    assert len(logs) == 2


def test_partial_probe_result_counts_as_success(hands, monkeypatch):
    _as_windows(hands, monkeypatch, lambda: (None, None))
    hands._probe_lock_state()
    hands._probe_lock_state()
    monkeypatch.setattr(hands, "_probe_lock_state_raw", lambda: (None, 5.0))
    hands._probe_lock_state()
    assert hands._probe_health() == {"probe_failures": 0, "probe_ok": True}


def test_off_windows_never_counts(hands, monkeypatch):
    # os.name is NOT patched to nt here: (None, None) is the designed
    # off-Windows result, not a failure.
    monkeypatch.setattr(hands, "_probe_lock_state_raw", lambda: (None, None))
    for _ in range(5):
        hands._probe_lock_state()
    assert hands._probe_health() == {"probe_failures": 0, "probe_ok": True}


def test_state_carries_probe_health(hands, monkeypatch):
    monkeypatch.setattr(hands, "_probe_lock_state", lambda: (None, None))
    with hands.app.test_request_context("/state"):
        body = hands.state()
    assert body["ok"] is True
    assert body["probe_failures"] == 0
    assert body["probe_ok"] is True
