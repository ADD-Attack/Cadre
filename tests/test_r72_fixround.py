"""R7.2 fix round — Astra DEPLOY-NO-GO findings 1-3 (+5, 6) and the
Grok stale-baseline finding, against hands.type_text().

Two virtual sessions drive the guard:
  * HookSession — the provenance path (low-level hooks): our writes are
    INJECTED events, the owner's are not. Timestamps are irrelevant.
  * DwSession   — the dwTime fallback: one virtual GetTickCount clock;
    _probe_dwtime / _tick_ms read it.
Windows itself is stubbed; the live receipts are in docs/VERIFICATION.md.
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
URL40 = "https://www.spotify.com/account/privacy/"


@pytest.fixture(scope="module")
def hands():
    spec = importlib.util.spec_from_file_location("r72fix_hands", ROOT / "hands/muse_relay_hands.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _status(resp):
    return resp[1] if isinstance(resp, tuple) else resp.status_code


def _body(resp):
    return resp[0].get_json() if isinstance(resp, tuple) else resp.get_json()


class HookSession:
    """Counters as the LL hooks would keep them."""

    def __init__(self, owner_in_write=None, owner_on_sleep=None, deaf=False, die_at=None):
        self.owner = 0
        self.injected = 0
        self.written = []
        self.sleeps = 0
        self.owner_in_write = owner_in_write
        self.owner_on_sleep = owner_on_sleep
        self.deaf = deaf
        self.die_at = die_at

    def snapshot(self):
        if self.die_at is not None and len(self.written) >= self.die_at:
            return None
        return (self.owner, self.injected)

    def write(self, ch, *a, **k):
        self.written.append(ch)
        if not self.deaf:
            self.injected += 1  # the relay's SendInput: flagged INJECTED
        if self.owner_in_write == len(self.written):
            self.owner += 1  # owner key lands before write() returns

    def sleep(self, _s):
        self.sleeps += 1
        if self.sleeps == self.owner_on_sleep:
            self.owner += 1


class DwSession:
    """One GetTickCount clock; dwTime stamps; scripted failures/delays."""

    def __init__(self, owner_on_sleep=None, fail_probe_after_write=None, delay_publish=None,
                 owner_late_after_write=None, backward_at=None):
        self.tick = 100000
        self.dw = self.tick - 5001
        self.written = []
        self.sleeps = 0
        self.pending = None  # a stamp that publishes late
        self.owner_on_sleep = owner_on_sleep
        self.fail_probe_after_write = fail_probe_after_write or set()
        self.delay_publish = delay_publish or set()
        self.owner_late_after_write = owner_late_after_write
        self.backward_at = backward_at
        self._in_post_probe = False

    def probe(self):
        if self._in_post_probe and len(self.written) in self.fail_probe_after_write:
            self._in_post_probe = False
            return None
        self._in_post_probe = False
        return self.dw

    def tick_ms(self):
        return self.tick

    def write(self, ch, *a, **k):
        self.written.append(ch)
        self.tick += 10
        n = len(self.written)
        if n in self.delay_publish:
            self.pending = self.tick + 5  # our stamp shows up after the probe
        else:
            self.dw = self.tick
        if self.backward_at == n:
            self.dw = self.tick - 3000  # Microsoft: dwTime need not increase
        self._in_post_probe = True

    def sleep(self, _s):
        self.sleeps += 1
        self.tick += 50  # inter-key sleeps are 40-160 ms (_plan_key_delays)
        if self.pending is not None:
            self.dw, self.pending = self.pending, None
        if self.owner_on_sleep == self.sleeps:
            self.tick += 10
            self.dw = self.tick
        if self.owner_late_after_write == self.sleeps:
            self.dw = self.tick  # 50 ms after our write ended: past the grace


def _run(hands, monkeypatch, session, text=URL40, locked_after=None, mode="hook"):
    monkeypatch.setattr(hands, "_probe_lock_state", lambda: (None, None))
    if locked_after is None:
        monkeypatch.setattr(hands, "_probe_locked", lambda: False)
    else:
        monkeypatch.setattr(hands, "_probe_locked", lambda: len(session.written) >= locked_after)
    monkeypatch.setattr(hands._owner_monitor, "ensure_started", lambda wait=0.5: False)
    if mode == "hook":
        monkeypatch.setattr(hands, "_owner_input_snapshot", session.snapshot)
        monkeypatch.setattr(hands, "_probe_dwtime", lambda: None)
        monkeypatch.setattr(hands, "_tick_ms", lambda: None)
    else:
        monkeypatch.setattr(hands, "_owner_input_snapshot", lambda: None)
        monkeypatch.setattr(hands, "_probe_dwtime", session.probe)
        monkeypatch.setattr(hands, "_tick_ms", session.tick_ms)
    monkeypatch.setattr(hands.pyautogui, "write", session.write)
    monkeypatch.setattr(hands.time, "sleep", session.sleep)
    with hands.app.test_request_context(
        "/type", method="POST", json={"text": text, "method": "keys", "jitter": True}
    ):
        resp = hands.type_text()
    return _status(resp), _body(resp)


# ======================================================= required (verbatim)

def test_owner_input_between_injection_and_postwrite_probe_aborts(hands, monkeypatch):
    # Finding 1: the relay event, then a distinct owner event, both
    # before write 18 returns. Provenance says the second is the
    # owner's; the type stops at the next boundary (24), nothing after.
    s = HookSession(owner_in_write=18)
    status, body = _run(hands, monkeypatch, s)
    assert status == 409
    assert body["error_code"] == "type_aborted" and body["abort_reason"] == "owner"
    assert body["chars_typed"] == 24 and body["owner_guard"] == "hook"
    assert "".join(s.written) == URL40[:24]


def test_type_aborts_on_lock_without_input(hands, monkeypatch):
    # Finding 2: lock after char 18, owner-input timestamps unchanged.
    s = DwSession()
    status, body = _run(hands, monkeypatch, s, locked_after=18, mode="dwtime")
    assert status == 409
    assert body["abort_reason"] == "locked" and "locked" in body["error"]
    assert body["chars_typed"] == 24 and len(s.written) == 24
    assert "".join(s.written) == URL40[:24]
    assert "yield" not in body["error"]  # never queue-retried (prefix landed)


@pytest.mark.parametrize("mode", ["hook", "dwtime"])
def test_owner_input_after_char12_aborts_before_char13(hands, monkeypatch, mode):
    # Finding 3: owner event during the sleep after char 12.
    s = HookSession(owner_on_sleep=12) if mode == "hook" else DwSession(owner_on_sleep=12)
    status, body = _run(hands, monkeypatch, s, mode=mode)
    assert status == 409
    assert body["chars_typed"] == 12
    assert "".join(s.written) == URL40[:12]


# ======================================================== Grok replication

def test_single_failed_postwrite_probe_does_not_self_abort(hands, monkeypatch):
    # One failed post-write probe (None) after char 5 used to leave the
    # baseline stale; char 6's own stamp then read as the owner and the
    # type aborted at char 12. Owner never touches anything here.
    s = DwSession(fail_probe_after_write={5})
    status, body = _run(hands, monkeypatch, s, mode="dwtime")
    assert status == 200 and body["ok"] is True
    assert "".join(s.written) == URL40


def test_repeated_probe_failures_do_not_self_abort(hands, monkeypatch):
    s = DwSession(fail_probe_after_write={3, 5, 11, 12, 23, 24})
    status, body = _run(hands, monkeypatch, s, mode="dwtime")
    assert status == 200 and "".join(s.written) == URL40


def test_probe_failure_then_recovery_still_detects_owner(hands, monkeypatch):
    s = DwSession(fail_probe_after_write={5}, owner_on_sleep=18)
    status, body = _run(hands, monkeypatch, s, mode="dwtime")
    assert status == 409 and body["chars_typed"] == 24


# ============================================================ Finding 5

def test_relay_event_published_after_postwrite_probe_does_not_self_abort(hands, monkeypatch):
    s = DwSession(delay_publish={6, 12, 13, 24, 30})
    status, body = _run(hands, monkeypatch, s, mode="dwtime")
    assert status == 200 and "".join(s.written) == URL40


def test_backward_timestamp_is_not_owner_activity(hands, monkeypatch):
    s = DwSession(backward_at=9)
    status, body = _run(hands, monkeypatch, s, mode="dwtime")
    assert status == 200 and "".join(s.written) == URL40


def test_owner_input_past_publish_grace_is_detected(hands, monkeypatch):
    s = DwSession(owner_late_after_write=14)
    status, body = _run(hands, monkeypatch, s, mode="dwtime")
    assert status == 409 and body["chars_typed"] == 24


def test_dw_advanced_exact_half_range(hands):
    assert hands._dw_advanced(0x7FFFFFFF, 0) is True
    assert hands._dw_advanced(0x80000000, 0) is False
    assert hands._dw_advanced(0, 0) is False
    assert hands._dw_advanced(0x7FFFFFFE, 0xFFFFFFFF) is True
    assert hands._dw_advanced(0x7FFFFFFF, 0xFFFFFFFF) is False


# ================================================================ hooks

def test_hook_mode_own_injected_input_never_aborts(hands, monkeypatch):
    s = HookSession()
    status, body = _run(hands, monkeypatch, s)
    assert status == 200 and body["owner_guard"] == "hook"
    assert "".join(s.written) == URL40


def test_hook_mode_owner_on_sleep_18_aborts_at_24(hands, monkeypatch):
    s = HookSession(owner_on_sleep=18)
    status, body = _run(hands, monkeypatch, s)
    assert status == 409 and body["chars_typed"] == 24


def test_deaf_hooks_degrade_to_dwtime(hands, monkeypatch):
    # Hooks that never see our own injected keys are presumed removed by
    # Windows; the guard must not trust their silence.
    s = HookSession(deaf=True)
    monkeypatch.setattr(hands, "_probe_dwtime", lambda: 5)
    monkeypatch.setattr(hands, "_tick_ms", lambda: 10)
    status, body = _run(hands, monkeypatch, s)
    # _run re-patches _probe_dwtime to None in hook mode; with no dwTime
    # either, the guard ends in "none" — and still completes honestly.
    assert status == 200 and body["owner_guard"] in ("dwtime", "none")


def test_hook_thread_dying_mid_op_degrades(hands, monkeypatch):
    s = HookSession(die_at=7)
    status, body = _run(hands, monkeypatch, s)
    assert status == 200 and body["owner_guard"] in ("dwtime", "none")


def test_lock_check_is_lock_only_not_self_triggering_idle(hands, monkeypatch):
    # The old boundary check read idle ~0 after our own keys and
    # aborted on itself. After the door, the idle probe reports 0 s
    # (our keystrokes) — the type must still finish.
    s = HookSession()
    calls = {"n": 0}

    def lock_state():
        calls["n"] += 1
        return (None, None) if calls["n"] == 1 else (False, 0.0)

    monkeypatch.setattr(hands, "_probe_locked", lambda: False)

    def run_with_idle():
        monkeypatch.setattr(hands._owner_monitor, "ensure_started", lambda wait=0.5: False)
        monkeypatch.setattr(hands, "_owner_input_snapshot", s.snapshot)
        monkeypatch.setattr(hands, "_probe_lock_state", lock_state)
        monkeypatch.setattr(hands.pyautogui, "write", s.write)
        monkeypatch.setattr(hands.time, "sleep", s.sleep)
        with hands.app.test_request_context(
            "/type", method="POST", json={"text": URL40, "method": "keys", "jitter": True}
        ):
            return hands.type_text()

    resp = run_with_idle()
    assert _status(resp) == 200 and "".join(s.written) == URL40
    assert calls["n"] == 1  # only the door consulted the idle probe


def test_monitor_inert_off_windows(hands, monkeypatch):
    monkeypatch.setattr(hands.os, "name", "posix")
    m = hands._OwnerInputMonitor()
    assert m.snapshot() is None and m.ensure_started(wait=0) is False


# ============================================================ Finding 6

def test_lock_and_idle_share_one_last_input_acquisition(hands, monkeypatch):
    monkeypatch.setattr(hands.os, "name", "nt")
    monkeypatch.setattr(hands, "_last_input_raw", lambda: (1000, 4000))
    monkeypatch.setattr(hands, "_probe_locked_raw", lambda: False)
    assert hands._probe_lock_state_raw() == (False, 3.0)
    assert hands._probe_dwtime_raw() == 1000
    monkeypatch.setattr(hands, "_last_input_raw", lambda: (0xFFFFFF00, 0x100))
    assert hands._probe_lock_state_raw() == (False, 0.512)
    monkeypatch.setattr(hands, "_last_input_raw", lambda: (None, None))
    monkeypatch.setattr(hands, "_probe_locked_raw", lambda: True)
    assert hands._probe_lock_state_raw() == (True, None)


def test_probe_locked_is_the_raw_lock_only(hands, monkeypatch):
    monkeypatch.setattr(hands, "_probe_locked_raw", lambda: True)
    monkeypatch.setattr(hands, "_last_input_raw", lambda: (_ for _ in ()).throw(AssertionError("idle consulted")))
    assert hands._probe_locked() is True


def test_publish_grace_blind_window_is_bounded_and_documented(hands, monkeypatch):
    # Residual (fallback only): owner input within _DW_PUBLISH_GRACE_MS
    # of our write is attributed to the write. Pin the bound so it
    # cannot silently grow; the hook path has no such window.
    assert hands._DW_PUBLISH_GRACE_MS <= 30


# ============================================================ Finding 4

class _Fn:
    def __init__(self, ret=1, log=None, name=""):
        self.ret, self.log, self.name = ret, log, name
        self.argtypes = None
        self.restype = None

    def __call__(self, *a):
        if self.log is not None:
            self.log.append(self.name)
        return self.ret


class _Dll:
    def __init__(self, log, **rets):
        self._log, self._rets = log, rets

    def __getattr__(self, name):
        fn = _Fn(self._rets.get(name, 1), self._log, name)
        setattr(self, name, fn)
        return fn


def _windll(monkeypatch, hands, log, **rets):
    user32 = _Dll(log, **{k: v for k, v in rets.items() if k in ("SetClipboardData", "OpenClipboard")})
    kernel32 = _Dll(log, GlobalAlloc=rets.get("GlobalAlloc", 0x7FFF_0000_1000), GlobalLock=0x7FFF_0000_2000)
    monkeypatch.setattr(hands.ctypes, "windll", type("W", (), {"user32": user32, "kernel32": kernel32})(), raising=False)
    monkeypatch.setattr(hands.ctypes, "memmove", lambda *a: None)
    return user32, kernel32


def test_clipboard_setup_declares_pointer_sized_handles(hands, monkeypatch):
    log = []
    user32, kernel32 = _windll(monkeypatch, hands, log)
    hands._WindowsClipboardBackend()._setup()
    vp = hands.ctypes.c_void_p
    assert kernel32.GlobalUnlock.argtypes == [vp]
    assert kernel32.GlobalFree.argtypes == [vp]
    assert kernel32.GlobalLock.argtypes == [vp]
    assert kernel32.GlobalAlloc.restype is vp
    assert user32.GetClipboardData.restype is vp
    assert user32.SetClipboardData.argtypes == [hands.ctypes.c_uint, vp]


def test_clipboard_frees_memory_when_set_fails(hands, monkeypatch):
    log = []
    _windll(monkeypatch, hands, log, SetClipboardData=0)
    with pytest.raises(OSError):
        hands._WindowsClipboardBackend().set_text("x")
    assert "GlobalFree" in log and log[-1] == "CloseClipboard"


def test_clipboard_does_not_free_memory_the_clipboard_owns(hands, monkeypatch):
    log = []
    _windll(monkeypatch, hands, log)
    hands._WindowsClipboardBackend().set_text("https://www.spotify.com/account/privacy/")
    assert "GlobalFree" not in log
