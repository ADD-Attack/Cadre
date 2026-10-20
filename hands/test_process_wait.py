"""Run per file: python -m pytest -q hands/test_process_wait.py."""
import ctypes
import importlib.util
from pathlib import Path
import sys
import types
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def modules(tmp_path):
    pag = types.ModuleType("pyautogui")
    tk = types.ModuleType("tkinter")
    tk.Tk = object
    # Import from a temporary copy: no config/log artifacts in the source tree.
    source = tmp_path / "hands.py"
    source.write_bytes((ROOT / "hands/muse_relay_hands.py").read_bytes())
    # R9: the hands loads its sibling motion.py by path.
    (tmp_path / "motion.py").write_bytes((ROOT / "hands/motion.py").read_bytes())
    with patch.dict(sys.modules, {"pyautogui": pag, "tkinter": tk}):
        hands = load("process_test_hands", source)
        gateway = load("process_test_gateway", ROOT / "services/gateway/app.py")
        gateway.TOKEN = "test-token"
        yield hands, gateway


def post(gateway, pid=42):
    return gateway.app.test_client().post(
        "/v1/wait", headers={"X-Relay-Token": "test-token"},
        json={"condition": {"type": "process_exit", "pid": pid},
              "timeout_seconds": 1, "poll_seconds": 0.2},
    )


@pytest.mark.parametrize("pid", [True, 0, -1, 2**32, "42", 1.5])
def test_invalid_pid(modules, pid):
    assert post(modules[1], pid).status_code == 400


@pytest.mark.parametrize("snapshots", [
    [(False, None)],
    [(True, "A"), (False, "A")],
    [(True, "A"), (True, "B")],  # PID reuse: original exited
])
def test_process_exit_end_to_end(modules, snapshots):
    hands, gateway = modules
    values = iter(snapshots)
    client = hands.app.test_client()

    def snapshot(pid):
        running, instance = next(values)
        return {"running": running, "instance": instance}

    def get(url, headers, timeout):
        assert headers == gateway._hands_headers()
        response = client.get("/process/42", headers={"X-Secret": hands.SHARED_SECRET})
        return types.SimpleNamespace(status_code=response.status_code,
                                     json=response.get_json)

    with patch.object(hands, "_process_snapshot", snapshot), \
            patch.object(gateway.requests, "get", get), \
            patch.object(gateway, "time", types.SimpleNamespace(
                monotonic=lambda: 0, sleep=lambda _: None)):
        response = post(gateway)
    assert response.status_code == 200
    assert response.json["held"] is True


@pytest.mark.parametrize("status,body", [
    (403, {}), (500, {}), (200, {}), (200, {"ok": True, "pid": 42,
                                         "running": True, "instance": None}),
])
def test_probe_failure_never_means_exit(modules, status, body):
    gateway = modules[1]
    with patch.object(gateway.requests, "get", return_value=types.SimpleNamespace(
            status_code=status, json=lambda: body)):
        response = post(gateway)
    assert response.status_code == 502
    assert "held" not in response.json


def test_live_process_times_out(modules):
    gateway = modules[1]
    now = [0.0]

    def sleep(delay):
        now[0] += delay

    with patch.object(gateway.requests, "get", return_value=types.SimpleNamespace(
            status_code=200, json=lambda: {"ok": True, "pid": 42,
                                          "running": True, "instance": "A"})), \
            patch.object(gateway, "time", types.SimpleNamespace(
                monotonic=lambda: now[0], sleep=sleep)):
        response = post(gateway)
    assert response.status_code == 200
    assert response.json["held"] is False
    assert response.json["timeout"] is True


def test_hands_auth_and_failure(modules):
    hands = modules[0]
    client = hands.app.test_client()
    with patch.object(hands, "_process_snapshot", side_effect=OSError("denied")) as probe:
        assert client.get("/process/42").status_code == 401
        probe.assert_not_called()
        assert client.get("/process/42", headers={
            "X-Secret": hands.SHARED_SECRET}).status_code == 502


def test_native_probe_closes_handle_on_failure(modules):
    hands = modules[0]

    class Fn:
        def __init__(self, result):
            self.result = result
            self.calls = []

        def __call__(self, *args):
            self.calls.append(args)
            return self.result

    kernel = types.SimpleNamespace(OpenProcess=Fn(123), GetProcessTimes=Fn(0),
                                   WaitForSingleObject=Fn(258), CloseHandle=Fn(1))
    with patch.object(hands, "os", types.SimpleNamespace(name="nt")), \
            patch.object(ctypes, "WinDLL", return_value=kernel, create=True), \
            patch.object(ctypes, "get_last_error", return_value=5, create=True):
        with pytest.raises(OSError):
            hands._process_snapshot(42)
    assert kernel.CloseHandle.calls == [(123,)]
    assert kernel.OpenProcess.calls == [(0x101000, False, 42)]


@pytest.mark.parametrize("error,status", [(87, False), (5, None)])
def test_native_missing_pid_vs_access_denied(modules, error, status):
    hands = modules[0]

    class Fn:
        def __call__(self, *args):
            return 0

    kernel = types.SimpleNamespace(**{
        name: Fn() for name in ("OpenProcess", "GetProcessTimes",
                               "WaitForSingleObject", "CloseHandle")
    })
    with patch.object(hands, "os", types.SimpleNamespace(name="nt")), \
            patch.object(ctypes, "WinDLL", return_value=kernel, create=True), \
            patch.object(ctypes, "get_last_error", return_value=error, create=True):
        if status is False:
            assert hands._process_snapshot(42) == {"running": False, "instance": None}
        else:
            with pytest.raises(OSError):
                hands._process_snapshot(42)
