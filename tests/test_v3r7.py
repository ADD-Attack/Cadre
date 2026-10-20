"""Tests for the R7 fix round — Astra's review of the R6 stack.

Astra returned DEPLOY-NO-GO on R6 with 2 High / 3 Medium / 2 Low
findings, all in the dashboard wiring of muse_relay_v2_app.py. These
tests pin the fixes:

  High 1  a dashboard-build failure inside the health poll must not
          skip health processing / self-heal.
  High 2  a dashboard render failure must not stop the UI queue
          drain — the next drain is always rescheduled.
  Med 1   the poll's dashboard model is built from the gateway
          module bound to the app (claim + receipts flow through).
  Med 2   a contended receipts lock skips the snapshot instead of
          stalling the poll.
  Med 3   the receipts snapshot field-copies rows under the lock.
  Low 1   junk containers / nonfinite values / wrong-typed PC fields
          never raise in the data layer.

RelayApp is driven the way test_v3r2_remaining drives it: a bare
object carrying only the attributes the method under test touches,
with the poll's thread captured and run synchronously.
"""

import importlib.util
import os
import queue
import sys
import threading
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
    name = "muse_relay_v2_app_r7"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


APP = _load_app()


# --- poll driving helpers ---------------------------------------------------


class _CaptureThread:
    """Stands in for threading.Thread: records targets, runs nothing."""

    instances = []

    def __init__(self, target=None, daemon=None, **kw):
        self.target = target
        _CaptureThread.instances.append(self)

    def start(self):
        pass


class _Response:
    def __init__(self, payload):
        self.status_code = 200
        self.text = "ok"
        self._payload = payload

    def json(self):
        return self._payload


class _Root:
    def __init__(self):
        self.after_calls = []

    def after(self, *args, **kwargs):
        self.after_calls.append(args)


def _info_payload(**over):
    info = {
        "ok": True,
        "hands_reachable": True,
        "parser_reachable": True,
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


def _bare_app(gw=None):
    obj = type("A", (), {})()
    obj._poll_running = False
    obj._poll_logged = True
    obj.token = "t"
    obj.root = _Root()
    obj.ui_queue = queue.Queue()
    obj._gateway_module = gw
    obj._hands_module = None
    obj.health_notes = []
    obj._note_health = lambda name, ok: obj.health_notes.append((name, ok))
    obj.set_status = lambda *a: None
    obj.log_line = lambda *a: None
    # _poll re-schedules itself via self.root.after(POLL_MS, self._poll);
    # the bare fake needs the attribute the real instance gets from its
    # class (same pattern as test_v3r2_remaining).
    obj._poll = lambda: None
    return obj


def _run_one_poll(monkeypatch, obj, payload):
    """Run one _poll cycle synchronously with a stubbed gateway GET."""
    _CaptureThread.instances = []
    monkeypatch.setattr(APP.threading, "Thread", _CaptureThread)
    monkeypatch.setattr(APP.requests, "get", lambda *a, **k: _Response(payload))
    APP.RelayApp._poll(obj)
    assert len(_CaptureThread.instances) == 1
    _CaptureThread.instances[0].target()  # _run_poll -> work()
    assert obj._poll_running is False


def _queued(obj):
    out = []
    while True:
        try:
            out.append(obj.ui_queue.get_nowait())
        except queue.Empty:
            return out


def _dashboard_model(obj):
    models = [p for kind, p in _queued(obj) if kind == "dashboard"]
    assert len(models) == 1
    return models[0]


def _fake_gateway(receipts=None, claim=None, queue_list=None, reserved_for=None, lock=None):
    gw = types.SimpleNamespace()
    gw._claim_snapshot = lambda: (claim, queue_list or [], reserved_for)
    gw._receipts = receipts if receipts is not None else {}
    gw._receipts_lock = lock if lock is not None else threading.Lock()
    return gw


# --- Low 1: junk handling in the data layer ---------------------------------


def test_fmt_duration_nonfinite():
    assert APP._fmt_duration(float("inf")) == "?"
    assert APP._fmt_duration(float("-inf")) == "?"
    assert APP._fmt_duration(float("nan")) == "?"
    assert APP._fmt_duration("junk") == "?"
    assert APP._fmt_duration(65) == "1m 05s"


def test_receipt_helpers_junk_containers():
    assert APP.receipt_state_counts(123) == {}
    assert APP.receipt_state_counts("nope") == {}
    assert APP.receipt_state_counts(None) == {}
    assert APP.summarize_receipts(123, time.time()) == []
    assert APP.summarize_receipts(None, time.time()) == []


def test_model_junk_info_payload_does_not_raise():
    # Astra's High-1 trigger shape: /v1/info answered with a JSON list.
    model = APP.build_dashboard_model(["not", "a", "dict"], None, None, None, {}, time.time())
    assert model["services"]["gateway"] == "ok"
    assert model["pc"] is None
    assert model["claim"] is None
    # Diagnostics render must survive the model too.
    assert "gateway ok" in APP.format_diagnostics(model, "21:00:00")


def test_model_normalizes_wrong_typed_pc_fields():
    info = _info_payload(
        pc_state={
            "ok": True,
            "platform": "windows",
            "locked": "false",  # string: truthy junk, must not read as state
            "idle_seconds": float("inf"),
            "probe_failures": "3",
            "probe_ok": "false",  # string "false" must not become "ok"
        }
    )
    model = APP.build_dashboard_model(info, None, [], None, {}, time.time())
    pc = model["pc"]
    assert pc["locked"] is None
    assert pc["idle_seconds"] is None
    assert pc["probe_failures"] is None
    assert pc["probe_state"] == "unknown"
    text = APP.format_diagnostics(model, "21:00:00")
    assert "lock unknown" in text
    assert "yield probe unknown" in text


# --- Medium 3: snapshot field copies ----------------------------------------


def test_snapshot_rows_are_field_copies():
    row = {
        "id": "aaabbbcc",
        "op": "click",
        "state": "held",
        "submitted_at": 100.0,
        "result": {"big": "payload"},
        "hands_status": 200,
    }
    table = {"aaabbbcc": row, "junk": "not-a-dict"}
    snap = APP._snapshot_receipt_rows(table)
    assert snap["aaabbbcc"] == {
        "id": "aaabbbcc",
        "op": "click",
        "state": "held",
        "submitted_at": 100.0,
    }
    assert snap["aaabbbcc"] is not row
    assert snap["junk"] == "not-a-dict"
    # A writer mutating the live row after the snapshot must not leak.
    row["state"] = "applied"
    assert snap["aaabbbcc"]["state"] == "held"
    assert APP._snapshot_receipt_rows(None) == {}
    assert APP._snapshot_receipt_rows([1, 2]) == {}


# --- High 1 / Medium 1 / Medium 2: the poll path -----------------------------


def test_poll_wiring_carries_gateway_claim_and_receipts(monkeypatch):
    now = time.time()
    claim = {"holder": "main", "purpose": "chess", "expires_at": now + 600}
    receipts = {
        "a20255f1": {
            "id": "a20255f1",
            "op": "click",
            "state": "applied",
            "submitted_at": now - 5,
            "result": {"opaque": True},
        }
    }
    gw = _fake_gateway(
        receipts=receipts,
        claim=claim,
        queue_list=[{"holder": "forge", "purpose": "", "enqueued_at": now}],
        reserved_for="forge",
    )
    obj = _bare_app(gw)
    _run_one_poll(monkeypatch, obj, _info_payload())
    model = _dashboard_model(obj)
    assert model["claim"]["holder"] == "main"
    assert model["queue_len"] == 1
    assert model["reserved_for"] == "forge"
    assert model["counts"] == {"applied": 1}
    assert model["feed"][0]["id8"] == "a20255f1"
    assert ("gateway", True) in obj.health_notes
    assert ("hands", True) in obj.health_notes


def test_dashboard_build_failure_does_not_stop_health(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("model exploded")

    monkeypatch.setattr(APP, "build_dashboard_model", boom)
    obj = _bare_app(_fake_gateway())
    _run_one_poll(monkeypatch, obj, _info_payload())
    # Health processing and self-heal ran despite the dashboard failure.
    assert ("gateway", True) in obj.health_notes
    assert ("hands", True) in obj.health_notes
    assert ("parser", True) in obj.health_notes
    assert [k for k, _ in _queued(obj) if k == "dashboard"] == []


def test_poll_survives_list_info_payload(monkeypatch):
    obj = _bare_app(_fake_gateway())
    _run_one_poll(monkeypatch, obj, ["junk", "list", "payload"])
    model = _dashboard_model(obj)
    assert model["pc"] is None
    assert ("gateway", True) in obj.health_notes


def test_snapshot_skips_when_receipt_lock_contended(monkeypatch):
    now = time.time()
    lock = threading.Lock()
    receipts = {
        "a20255f1": {
            "id": "a20255f1",
            "op": "click",
            "state": "applied",
            "submitted_at": now - 5,
        }
    }
    gw = _fake_gateway(receipts=receipts, lock=lock)
    obj = _bare_app(gw)
    assert lock.acquire(timeout=1)
    try:
        start = time.time()
        _run_one_poll(monkeypatch, obj, _info_payload())
        elapsed = time.time() - start
    finally:
        lock.release()
    # Bounded: the poll finished promptly instead of stalling on the
    # lock, the snapshot was skipped, and health still ran.
    assert elapsed < 2.0
    model = _dashboard_model(obj)
    assert model["counts"] == {}
    assert model["feed"] == []
    assert ("gateway", True) in obj.health_notes


# --- High 2: the drain -------------------------------------------------------


class _FakeText:
    def __init__(self):
        self.lines = []

    def config(self, **kw):
        pass

    def insert(self, where, text):
        self.lines.append(text)

    def see(self, where):
        pass


def test_drain_reschedules_after_render_exception():
    obj = type("A", (), {})()
    obj._hands_module = None
    obj.ui_queue = queue.Queue()
    obj.root = _Root()
    obj.log = _FakeText()
    obj._stamp = lambda: "21:00:00"
    obj._drain_queue = lambda: None  # reschedule target on the bare fake

    def bad_render(model):
        raise RuntimeError("render exploded")

    obj._render_dashboard = bad_render
    obj.ui_queue.put(("dashboard", {"services": {}}))
    obj.ui_queue.put(("log", "still alive"))

    APP.RelayApp._drain_queue(obj)  # must not raise

    # The drain rescheduled itself exactly once, in the finally.
    assert len(obj.root.after_calls) == 1
    assert obj.root.after_calls[0][0] == 300
    # The render failure was isolated: the skip was noted and the log
    # message queued behind it was still drained.
    joined = "".join(obj.log.lines)
    assert "UI update skipped (dashboard)" in joined
    assert "still alive" in joined
