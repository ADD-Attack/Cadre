# Astra implementation packet — R7.2 fix round + R9 wishlist build + R9 web GUI
Assembled 2026-10-20 by Muse (operator/producer) for a fresh Astra session.
Owner direction (Christopher, 2026-10-20 05:21 CDT): **Astra implements this round** — you are the builder, not the reviewer.

## Role + rules (read first)

1. You implement **three stages, in order**: Stage 1 (R7.2 fix round), Stage 2 (R9 human-like pointer system + jiggler), Stage 3 (R9 relay web GUI). Do not start a later stage's code before delivering the earlier stage's report, but DO deliver all three — each stage gets its own report message in this session.
2. For each stage you return **COMPLETE code**: full replacement contents for every changed or new file, or unified diffs clearly anchored to the named base commit — plus all new/changed tests. Code is delivered in your session replies. Nothing is deployed by you; the producer applies, tests, and deploys producer-side.
3. Because you are the builder this round, the independent pre-deploy review will be a **fresh Opus session** that has not seen this session. Write every report so a reviewer can verify each claim **from the code alone**: name the mechanism, the invariant it restores, and the test that proves it. Claims a reviewer cannot trace to code will be treated as unproven.
4. A status report without code is a **non-answer**. If you are blocked, say exactly what input is missing and deliver everything that is not blocked.
5. Test convention (repo-standing): tests run **per file** with `~/workspace/relay-test-venv/bin/python` (one pytest process across all test dirs errors via tkinter fake interference). Any test file that installs `sys.modules` fakes must restore them. Match this convention in every test you add or change, and state the per-file commands you ran (or would run) and their results.
6. Deadlines (America/Chicago): Stage 1 — **today 2026-10-20, 09:30 CDT**. Stage 2 — **today 2026-10-20, 17:00 CDT**. Stage 3 — **tomorrow Wed 2026-10-21, 17:00 CDT**.

## Report format (every stage)

- What was built (mechanism-level, not marketing).
- Files changed/added, each with the complete contents or anchored diff.
- Tests added/changed and their results as you ran or reasoned them, per file.
- Open risks and anything a reviewer should attack first.

---
# STAGE 1 — R7.2 fix round

**Base:** branch `v3-r7-2-20261019` @ commit `22a9080` in repo `muse-relay-v2`. That commit = clipboard `ctypes.sizeof` fix + type dwTime re-check in `hands/muse_relay_hands.py`.
**Your own verdict on that commit was DEPLOY-NO-GO** (you reviewed it 2026-10-19; the producer read and recorded it). Findings 1–3 block. Fix findings 1–3 and add the three fix-proving tests the verdict names, **verbatim**:

- `test_owner_input_between_injection_and_postwrite_probe_aborts`
- `test_type_aborts_on_lock_without_input`
- `test_owner_input_after_char12_aborts_before_char13`

The verdict's exact requirements for each finding (including its reproduction details and acceptance shape) are quoted in full below — build to those words, not to a summary. Findings 4–7 are NOT in this stage's blocking scope, but finding 4's real-Windows clipboard roundtrip receipt and finding 5's hardening tests should be noted in your report as still-owed release evidence if your fix touches those areas.

## The verdict — Findings section, complete and verbatim

## Findings

### 1. High — Post-write sampling can adopt owner input as “ours”
**Location:** `type_text()`, `dw_after` → `self_dw`.

The comment “that stamp is ours by construction” is false. An owner event occurring after injection but before the post-write probe becomes the new baseline without setting `owner_seen`. This includes input during any pause inside `pyautogui.write()`, not just same-tick input.

The new fake guarantees writes synchronously set `dwTime` and puts owner input only in the subsequent explicit sleep. It excludes precisely this race.

A standalone reproduction with owner input on a **distinct tick inside write 18** completes all 40 characters with `owner_seen=False`.

**Exact fix-proving test:** `test_owner_input_between_injection_and_postwrite_probe_aborts` — inject the relay event, then a distinct-tick owner event before `write()` returns. Require owner detection and a 409 partial at the next boundary, with no writes beyond it. Repeat against the real Windows injection path. Timestamp-only post-write attribution cannot reliably distinguish these events; the fix needs trustworthy event provenance or a revised mechanism.

### 2. High — Mid-type lock protection is removed
**Location:** replacement of `_yield_if_active()`.

A lock transition with no new session input does not advance `dwTime`. The loop therefore continues instead of aborting. A desktop lock and owner activity are separate conditions; fixing self-generated idle activity should not remove lock checking.

Continued attempts may also make the reported typed count misleading and can resume landing characters after an unlock.

**Exact fix-proving test:** `test_type_aborts_on_lock_without_input` — start unlocked; lock after character 18 while keeping owner-input timestamps unchanged. Require 409 and exactly 24 attempted characters, none beyond that boundary. Use a lock-only check, not the old self-triggering idle check.

### 3. Medium — Boundary check runs before the fresh owner sample
**Location:** start of the character loop.

If owner input lands during the sleep after character 12, the boundary check sees the previous `owner_seen=False`. The subsequent probe detects activity, but characters 13–24 still execute.

The standalone reproduction confirms **24 characters**, not 12. For a shorter remaining payload, the operation may finish successfully despite detecting owner activity.

**Exact fix-proving test:** `test_owner_input_after_char12_aborts_before_char13` — owner event during sleep 12; require 409, `chars_typed=12`, and exactly the first 12 characters written. Sample before evaluating the boundary.

### 4. Medium — Clipboard fake proves the regression fix, not Windows integration
**Location:** `_WindowsClipboardBackend.set_text()` and its new test.

`ctypes.sizeof(data)` is the correct byte count, including the terminating NUL. Using the same count for allocation and copying fixes the reported `AttributeError`.

The fake genuinely executes `set_text()` and would catch the old `.size` error. However, it bypasses:

- `_setup()` and its native signatures/pointer widths.
- Real allocation, memory copying, and clipboard ownership.
- Windows UTF-16 representation; host `c_wchar` width can differ.

The stub records `memmove` arguments without verifying copied content. This is a good **unit regression**, not proof of the Windows path.

**Release evidence needed:** `test_windows_clipboard_real_roundtrip` on the target Windows build, using the real backend: empty text, the supplied URL, and non-BMP Unicode. Independently read back exact content and verify the `/type` paste path. Preserve and restore the test clipboard.

### 5. Medium — `dwTime` assumptions exceed the API guarantee
**Location:** `_dw_advanced()` and raw probe.

The `& 0xFFFFFFFF` masking and half-range comparison are correct modular arithmetic for forward advances below `2³¹` milliseconds. The supplied wrap test is valid.

However, Microsoft explicitly documents that `GetLastInputInfo` timestamps need not increase, including because of input-thread timing and injected input. Arithmetic correctness does not establish input ownership or synchronous publication. [Microsoft documentation](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getlastinputinfo)

Per-character sampling improves detection during explicit sleeps, and the sticky flag preserves **already detected** activity. Neither prevents post-write masking. The documented same-tick blind spot is real but understates the actual blind window.

Add delayed-publication, backward-timestamp, probe-failure/recovery, and exact half-range tests. In particular, test whether a relay event published after the post-write probe produces another self-abort.

### 6. Low — Probe seam is reasonable; duplication needs coverage

The `_probe_dwtime()` / `_probe_dwtime_raw()` split is a useful test seam. The native structure is appropriate on Windows.

Duplicating `GetLastInputInfo` plumbing creates drift risk with `_probe_lock_state_raw()`. Prefer shared low-level timestamp acquisition while keeping lock detection independent. The packet does not include that existing raw implementation or R8, so exact parity and probe-health integration remain unverified.

### 7. Low — Restoration is mostly sound, with one exposed interval

The main clock test restores `write`, `sleep`, the probe, and clipboard backend in `finally`. The clipboard test restores global `ctypes.memmove` in `finally`. Pytest’s `monkeypatch` handles the changed F7 test correctly.

However, `_clipboard_backend = lambda: None` is installed **before** the main `try`, encompassing the jitter-disabled request. An exception there bypasses restoration. Move that mutation and request inside the protected scope. Shared-module mutations of `time.sleep` and `ctypes.memmove` also assume these tests run without concurrent consumers.

## Gate conclusion

**Do not deploy this combined revision.** Fix and prove findings 1–3, then obtain real Windows clipboard and typing receipts. The `sizeof` change itself is sound; the supplied tests do not establish the replacement typing guard’s correctness.

## Current code you are patching against (branch `v3-r7-2-20261019` @ `22a9080`, `hands/muse_relay_hands.py`)

### `_yield_if_active()` — the door check the R7.2 loop replaced at boundaries (context for finding 2: lock + idle live here; the fix needs a lock-only check, not this self-triggering idle check)

```python
def _yield_if_active():
    """409 and do not run the op when the owner was active recently.

    _probe_lock_state is the only seam: (locked, idle_seconds), or
    (None, None) off Windows / on failure. None idle means inactive.
    Yield only when idle_seconds < HANDS_YIELD_IDLE_SECONDS (default 5).

    R4 (F6): a LOCKED desktop also yields — acts injected at the
    Winlogon desktop go nowhere yet reported success, so queued
    receipts settled "applied" for input that never landed. The 409
    carries error_code "locked" so the gateway holds and retries the
    act until unlock instead of settling it (F11: the code, not the
    prose, is the contract; the prose keeps the word "yielded" so an
    older gateway still classifies it by substring).
    """
    try:
        threshold = float(os.environ.get("HANDS_YIELD_IDLE_SECONDS", "5"))
    except (TypeError, ValueError):
        threshold = 5.0
    locked, idle_seconds = _probe_lock_state()
    if locked is True:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "desktop locked — control yielded",
                    "error_code": "locked",
                }
            ),
            409,
        )
    if idle_seconds is not None and idle_seconds < threshold:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "user active — control yielded",
                    "error_code": "yield",
                }
            ),
            409,
        )
    return None

```

### `type_text()` — contains the R7.2 `_keys()` dwTime loop that findings 1–3 are about

```python
def type_text():
    """Type text: clipboard paste for long payloads, jittered keys else.

    {text, method?: "auto"|"paste"|"keys", jitter?: bool}

    Method (wishlist #9): "auto" pastes when the text is over 120 chars
    and a clipboard backend exists — the paste path saves the current
    clipboard and restores it afterwards; "paste" forces that path;
    "keys" forces keystrokes. Any clipboard failure falls back to
    keystrokes instead of failing the request (see "note").

    Jitter (wishlist #16): the keystroke path types per character with
    human-band delays from _plan_key_delays unless jitter is false —
    false restores the original single pyautogui.write(interval=0.02).

    Response: {"ok", "method_used", "chars", "elapsed_seconds",
    "delays_planned", "planned_seconds"} — the delay fields describe the
    keystroke plan (0 on the paste path).
    """
    refused = _yield_if_active()
    if refused is not None:
        return refused
    d = request.get_json(force=True, silent=True) or {}
    text = d.get("text")
    if not isinstance(text, str):
        return jsonify({"ok": False, "error": "text must be a string"}), 400
    method = d.get("method", "auto")
    if method not in ("auto", "paste", "keys"):
        return jsonify({"ok": False, "error": "method must be auto, paste or keys"}), 400
    jitter = bool(d.get("jitter", True))
    started = time.monotonic()
    note = None
    delays = []

    typed = 0

    def _keys():
        nonlocal delays, typed
        if jitter:
            delays = _plan_key_delays(text, random)
            # R4 (F7) re-checked the yield every 12 chars so a long
            # type gated only at the door cannot interleave relay
            # keystrokes with the owner's for the op's whole duration.
            # R7.2 (wishlist #27): that re-check consulted
            # _yield_if_active(), whose idle probe counts this type's
            # OWN injected keystrokes as session input — after 12 of
            # our own chars the idle read ~0 and the type aborted on
            # itself, owner or no owner. Track dwTime instead: sample
            # it after each keystroke (that stamp is ours by
            # construction) and flag owner input when a later sample
            # is strictly newer than the stamp our last keystroke
            # explains. The abort still lands on the same 12-char
            # boundaries and reports the same partial, so the response
            # contract is unchanged. Accepted blind spot: an owner
            # event inside the same tick as one of our keystrokes is
            # indistinguishable from that keystroke. Off Windows / on
            # probe failure dwTime is None and the re-check is inert,
            # like the door's.
            self_dw = _probe_dwtime()
            owner_seen = False
            for ch, delay in zip(text, delays):
                if typed and typed % 12 == 0 and owner_seen:
                    break
                if self_dw is not None:
                    dw_now = _probe_dwtime()
                    if dw_now is not None and _dw_advanced(dw_now, self_dw):
                        owner_seen = True
                pyautogui.write(ch)
                dw_after = _probe_dwtime()
                if dw_after is not None:
                    self_dw = dw_after
                time.sleep(delay)
                typed += 1
        else:
            pyautogui.write(text, interval=0.02)
            typed = len(text)
        return "keys"

    def _paste():
        backend = _clipboard_backend()
        if backend is None:
            raise RuntimeError("clipboard unavailable on this host")
        saved, readable = None, False
        try:
            saved = backend.get_text()
            readable = True
        except Exception:
            pass  # unreadable clipboard: paste anyway, skip the restore
        try:
            backend.set_text(text)
            pyautogui.hotkey("ctrl", "v")
            if readable:
                # Give the target app a beat to consume the paste before the
                # previous clipboard contents go back.
                time.sleep(0.1)
        finally:
            if readable and saved is not None:
                try:
                    backend.set_text(saved)
                except Exception:
                    pass
        return "paste"

    if method == "keys":
        method_used = _keys()
    elif method == "paste":
        try:
            method_used = _paste()
        except Exception as exc:
            note = f"paste requested but unavailable ({exc}); used keys"
            method_used = _keys()
    else:  # auto
        if len(text) > 120 and _clipboard_backend() is not None:
            try:
                method_used = _paste()
            except Exception as exc:
                note = f"paste failed ({exc}); used keys"
                method_used = _keys()
        else:
            method_used = _keys()
    if method_used == "keys" and typed < len(text):
        return (
            jsonify(
                {
                    "ok": False,
                    # Deliberately NOT yield-classified (error_code is
                    # not "yield"/"locked", and the prose avoids the
                    # legacy substrings): some chars already landed, so
                    # a queued retry of the whole payload would
                    # double-type the prefix. The receipt settles
                    # failed with chars_typed; the caller re-submits
                    # text[chars_typed:].
                    "error": f"owner became active — typing aborted at char {typed}",
                    "error_code": "type_aborted",
                    "aborted": True,
                    "chars_typed": typed,
                    "chars": len(text),
                    "method_used": "keys",
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "delays_planned": len(delays),
                    "planned_seconds": sum(delays[:typed]),
                }
            ),
            409,
        )
    resp = {
        "ok": True,
        "method_used": method_used,
        "chars": len(text),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "delays_planned": len(delays),
        "planned_seconds": sum(delays),
    }
    if note:
        resp["note"] = note
    return jsonify(resp)
```

### dwTime / lock probes — `_probe_dwtime`, `_probe_dwtime_raw`, `_dw_advanced`, `_probe_lock_state`, `_probe_lock_state_raw`

```python
def _probe_dwtime():
    """The session's last-input timestamp (ms tick), or None.

    Tests monkeypatch THIS function (the seam, mirroring
    _probe_lock_state); the raw Windows call is _probe_dwtime_raw.
    """
    return _probe_dwtime_raw()


def _probe_dwtime_raw():
    """dwTime from GetLastInputInfo on Windows; None elsewhere/failure."""
    if os.name != "nt":
        return None
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]

        class _LastInputInfo(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_ulong)]

        info = _LastInputInfo()
        info.cbSize = ctypes.sizeof(_LastInputInfo)
        if user32.GetLastInputInfo(ctypes.byref(info)):
            return int(info.dwTime)
    except Exception:
        pass
    return None


def _dw_advanced(dw, baseline):
    """True when last-input tick `dw` is strictly newer than `baseline`.

    dwTime is a 32-bit millisecond tick (wraps ~49.7 days); the
    modular difference reads advances under half the range as newer
    and anything else as older / wrapped noise.
    """
    return 0 < ((int(dw) - int(baseline)) & 0xFFFFFFFF) < 0x80000000


# ---- probe health (R5, F10) -------------------------------------------
# The yield trusts the lock/idle probe completely: a (None, None)
# result reads as "owner inactive", so a silently broken probe (a
# Windows change, a permissions shift, a bad cast) disables the
# owner's override with no signal anywhere. Count consecutive FULL
# failures on Windows; /state reports probe_ok so the degradation is
# a visible state (it rides to the gateway's /v1/info pc_state), and
# the third consecutive failure logs a line to the app window — the
# channel the owner actually sees. Whether the yield should fail
# CLOSED on a degraded probe is the owner's policy call; silently
# failing open was the one option that had to go.
_probe_failures = 0
_probe_degraded_logged = False


def _probe_lock_state():
    """(locked, idle_seconds) with probe-health accounting (R5, F10).

    Tests monkeypatch THIS function (the seam); the raw Windows probe
    is _probe_lock_state_raw.
    """
    global _probe_failures, _probe_degraded_logged
    result = _probe_lock_state_raw()
    if os.name == "nt":
        locked, idle_seconds = result
        if locked is None and idle_seconds is None:
            _probe_failures += 1
            if _probe_failures >= 3 and not _probe_degraded_logged:
                _probe_degraded_logged = True
                log_line(
                    "YIELD SENSOR DEGRADED: the lock/idle probe has "
                    "failed 3 times in a row - act yields cannot be "
                    "trusted until it recovers"
                )
                file_log("probe degraded: 3 consecutive lock/idle probe failures")
        else:
            _probe_failures = 0
            _probe_degraded_logged = False
    return result


def _probe_health():
    return {"probe_failures": _probe_failures, "probe_ok": _probe_failures < 3}


def _probe_lock_state_raw():
    """Probe (locked, idle_seconds) on Windows; (None, None) elsewhere.

    Never raises: any failure returns None for the affected value. The
    Windows calls live here so tests can monkeypatch _probe_lock_state.
    """
    if os.name != "nt":
        return (None, None)
    locked = None
    idle_seconds = None
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        # Locked check: the input desktop is the Winlogon desktop when locked.
        try:
            handle = user32.OpenInputDesktop(0, False, 0x0100)
            if handle:
                try:
                    buf = ctypes.create_unicode_buffer(256)
                    needed = ctypes.c_ulong(0)
                    if user32.GetUserObjectInformationW(
                        handle, 2, buf, ctypes.sizeof(buf), ctypes.byref(needed)
                    ):
                        locked = buf.value.lower() == "winlogon"
                finally:
                    try:
                        user32.CloseDesktop(handle)
                    except Exception:
                        pass
        except Exception:
            locked = None
        # Idle check: time since last input.
        try:
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

            class _LastInputInfo(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_ulong)]

            info = _LastInputInfo()
            info.cbSize = ctypes.sizeof(_LastInputInfo)
            if user32.GetLastInputInfo(ctypes.byref(info)):
                tick = kernel32.GetTickCount()
                idle_ms = (int(tick) - int(info.dwTime)) & 0xFFFFFFFF
                idle_seconds = idle_ms / 1000.0
        except Exception:
            idle_seconds = None
    except Exception:
        return (locked, idle_seconds)
    return (locked, idle_seconds)


@app.get("/state")
```

### Clipboard backend — `_WindowsClipboardBackend`, `_PyperclipBackend`, `_clipboard_backend`, `clipboard_set`, `clipboard_get` (the sizeof fix the verdict calls sound; included so your tests/report can reference the real path)

```python
class _WindowsClipboardBackend:
    """Clipboard via ctypes user32/kernel32 (CF_UNICODETEXT)."""

    def _setup(self):
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        user32.GetClipboardData.restype = ctypes.c_void_p
        user32.SetClipboardData.restype = ctypes.c_void_p
        user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
        kernel32.GlobalAlloc.restype = ctypes.c_void_p
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        return user32, kernel32

    def get_text(self):
        user32, kernel32 = self._setup()
        if not user32.OpenClipboard(None):
            raise OSError("OpenClipboard failed")
        try:
            handle = user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return ""
            ptr = kernel32.GlobalLock(handle)
            if not ptr:
                return ""
            try:
                return ctypes.wstring_at(ptr)
            finally:
                kernel32.GlobalUnlock(handle)
        finally:
            user32.CloseClipboard()

    def set_text(self, text):
        user32, kernel32 = self._setup()
        data = ctypes.create_unicode_buffer(text)
        # R7.2 (wishlist #26): a c_wchar array has no .size attribute —
        # the byte count is ctypes.sizeof(data). The old data.size read
        # raised AttributeError on every real Windows call, so
        # /clipboard/set (and the /type paste path) could never set the
        # clipboard on the PC; it shipped because this backend never
        # runs off Windows and no test faked _setup.
        nbytes = ctypes.sizeof(data)
        if not user32.OpenClipboard(None):
            raise OSError("OpenClipboard failed")
        try:
            user32.EmptyClipboard()
            handle = kernel32.GlobalAlloc(0x0002, nbytes)  # GMEM_MOVEABLE
            if not handle:
                raise OSError("GlobalAlloc failed")
            ptr = kernel32.GlobalLock(handle)
            if not ptr:
                raise OSError("GlobalLock failed")
            try:
                ctypes.memmove(ptr, data, nbytes)
            finally:
                kernel32.GlobalUnlock(handle)
            if not user32.SetClipboardData(CF_UNICODETEXT, handle):
                raise OSError("SetClipboardData failed")
        finally:
            user32.CloseClipboard()


class _PyperclipBackend:
    def __init__(self, mod):
        self._mod = mod

    def get_text(self):
        return self._mod.paste() or ""

    def set_text(self, text):
        self._mod.copy(text)


def _clipboard_backend():
    """Clipboard backend seam: Windows ctypes, else pyperclip, else None."""
    if os.name == "nt":
        return _WindowsClipboardBackend()
    try:
        import pyperclip

        return _PyperclipBackend(pyperclip)
    except Exception:
        return None


@app.post("/clipboard/set")
def clipboard_set():
    d = request.get_json(force=True, silent=True) or {}
    text = d.get("text")
    if not isinstance(text, str):
        return jsonify({"ok": False, "error": "text must be a string"}), 400
    backend = _clipboard_backend()
    if backend is None:
        return jsonify({"ok": False, "error": "clipboard unavailable on this host"}), 501
    try:
        backend.set_text(text)
    except Exception as exc:
        return jsonify({"ok": False, "error": f"clipboard set failed: {exc}"}), 502
    return {"ok": True}


@app.get("/clipboard/get")
def clipboard_get():
    """Read the clipboard. Sensitive: same X-Secret gate as every hands
    route, and every read is logged (below) so the operator sees it in
    the app window's log area."""
    backend = _clipboard_backend()
    if backend is None:
        return jsonify({"ok": False, "error": "clipboard unavailable on this host"}), 501
    try:
        text = backend.get_text()
    except Exception as exc:
        return jsonify({"ok": False, "error": f"clipboard read failed: {exc}"}), 502
    log_line("clipboard read via relay")
    return jsonify({"ok": True, "text": text if isinstance(text, str) else ""})
# ---- elevation bridge ----------------------------------------------------
# The agent may only NAME a request from the operator's pre-configured
# allowlist (hands config file key "elevate_allowlist":
# {name: {"exe": "...", "args": "..."}} — static strings from the
# operator's config, never from the request). Nothing runs from here:
# the request is queued for the app window, and only the person at the
# PC clicking Approve there resolves it (via _resolve_elevation). There
# is deliberately no auto-approve path, no timeout-approve, and no
# config flag that approves.

ELEVATE_TTL_SECONDS = 120

elevate_queue: "queue.Queue[dict]" = queue.Queue()
_elevations: dict = {}
_elevations_lock = threading.Lock()


```

## Existing test file covering type + clipboard — `hands/test_actuation.py` @ `22a9080`, complete

This is a script-style suite (a `run()` with `check()` assertions, executed per file). The R7.2 dwTime clock scenario and the faked-dll Windows clipboard test live here; your three new fix-proving tests must fit this file's conventions (or a sibling file in the same style) and its fake-restoration discipline.

```python
"""Tests for the V3-P4 hands actuation routes (wishlist #3, #4, #6, #9, #19).

Runs anywhere — no Windows, no real desktop: fake pyautogui / tkinter
modules are injected into sys.modules BEFORE the hands module is loaded
from its file path, the fake pyautogui records every call, window
enumeration / activation and the clipboard backend are stubbed at their
seams (_enum_windows, _activate_window, _clipboard_backend), and the
routes are exercised through Flask's test client.

    python3 test_actuation.py

Covers: hotkey validation + chord; break chords (and times); drag call
order; type keys/paste paths incl. clipboard save/restore and forced
keys; the mid-type owner-abort re-check against a fake last-input tick
(R7.2); focus substring / exact / 404; windows route shape; clipboard
get/set, the read being logged, and 501 when unavailable; the Windows
clipboard backend's call shape against faked dlls (R7.2).
"""

import ctypes
import importlib.util
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
HANDS_PATH = os.path.join(HERE, "muse_relay_hands.py")
CONFIG_PATH = os.path.join(HERE, "muse_relay_config.json")
_config_existed = os.path.exists(CONFIG_PATH)

# ------------------------------------------------------------ fakes

calls = []


def _recorder(name):
    def fn(*args, **kwargs):
        calls.append((name, args, kwargs))

    return fn


fake_pag = types.ModuleType("pyautogui")
fake_pag.FAILSAFE = False
fake_pag.PAUSE = 0
for _name in (
    "moveTo", "click", "write", "press", "scroll", "hotkey",
    "mouseDown", "mouseUp",
):
    setattr(fake_pag, _name, _recorder(_name))
fake_pag.screenshot = lambda: None
fake_pag.getAllWindows = lambda: []
sys.modules["pyautogui"] = fake_pag

fake_tk = types.ModuleType("tkinter")


class _Dummy:
    def __init__(self, *a, **k):
        pass


for _name in ("Tk", "StringVar", "Label", "Entry", "Button", "Text"):
    setattr(fake_tk, _name, _Dummy)
sys.modules["tkinter"] = fake_tk

spec = importlib.util.spec_from_file_location("muse_relay_hands", HANDS_PATH)
hands = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hands)

# Integration (V3-P4 + V3-P5 merged /type): the keystroke path now applies
# jittered per-char delays by default, so real sleeps would make the
# 200-char keystroke cases take ~20s each. Sleeps are timing, not logic —
# stub them out for this test process.
hands.time.sleep = lambda _seconds: None

AUTH = {"X-Secret": hands.SHARED_SECRET}


class FakeClipboard:
    def __init__(self, initial=""):
        self.store = initial
        self.sets = []

    def get_text(self):
        return self.store

    def set_text(self, text):
        self.sets.append(text)
        self.store = text


def win(title, **kw):
    base = {
        "title": title, "process": "app.exe", "pid": 42,
        "bounds": {"x": 1, "y": 2, "w": 300, "h": 200},
        "monitor": 0, "visible": True, "focused": False,
    }
    base.update(kw)
    return base


def run():
    client = hands.app.test_client()
    failures = []

    def check(name, cond):
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    def names():
        return [c[0] for c in calls]

    orig_backend = hands._clipboard_backend
    orig_enum = hands._enum_windows
    orig_activate = hands._activate_window

    # ------------------------------------------------ hotkey (#19)
    calls.clear()
    r = client.post("/hotkey", json={"keys": []}, headers=AUTH)
    check("hotkey empty list -> 400, nothing pressed",
          r.status_code == 400 and not calls)
    r = client.post("/hotkey", json={"keys": "ctrl,l"}, headers=AUTH)
    check("hotkey non-list -> 400", r.status_code == 400 and not calls)
    r = client.post("/hotkey", json={"keys": ["ctrl", "l"]}, headers=AUTH)
    check("hotkey valid -> hotkey('ctrl','l')",
          r.status_code == 200
          and calls == [("hotkey", ("ctrl", "l"), {})])

    # Auth still gates the new routes.
    r = client.post("/hotkey", json={"keys": ["ctrl", "l"]})
    check("hotkey without secret -> 401", r.status_code == 401)

    # ------------------------------------------------ break (#19)
    calls.clear()
    r = client.post("/break", json={}, headers=AUTH)
    check("break default -> one hotkey('ctrl','c')",
          r.status_code == 200
          and calls == [("hotkey", ("ctrl", "c"), {})])
    calls.clear()
    r = client.post("/break", json={"times": 2}, headers=AUTH)
    check("break times=2 -> chord twice",
          r.status_code == 200
          and calls == [("hotkey", ("ctrl", "c"), {})] * 2)
    calls.clear()
    r = client.post("/break", json={"times": 5}, headers=AUTH)
    check("break times=5 -> 400, nothing pressed",
          r.status_code == 400 and not calls)

    # ------------------------------------------------ drag (#4)
    calls.clear()
    r = client.post("/drag", json={"x1": 10, "y1": 20, "x2": 90, "y2": 80},
                    headers=AUTH)
    check("drag call order down->move->up with default duration",
          r.status_code == 200
          and names() == ["moveTo", "mouseDown", "moveTo", "mouseUp"]
          and calls[0][1] == (10, 20)
          and calls[1][2].get("button") == "left"
          and calls[2][1] == (90, 80)
          and calls[2][2].get("duration") == 0.4
          and calls[3][2].get("button") == "left")
    calls.clear()
    r = client.post("/drag", json={"x1": 10, "y1": 20, "x2": 90},
                    headers=AUTH)
    check("drag missing coord -> 400, nothing pressed",
          r.status_code == 400 and not calls)
    r = client.post("/drag",
                    json={"x1": "a", "y1": 20, "x2": 90, "y2": 80},
                    headers=AUTH)
    check("drag non-numeric coord -> 400", r.status_code == 400 and not calls)

    # ------------------------------------------------ type: keys (#9)
    calls.clear()
    hands._clipboard_backend = lambda: None
    r = client.post("/type", json={"text": "hello"}, headers=AUTH)
    body = r.get_json()
    check("type short text -> keys path (write, method_used keys)",
          r.status_code == 200 and body["method_used"] == "keys"
          and body["chars"] == 5
          and calls == [("write", (ch,), {}) for ch in "hello"])

    # ------------------------------------------------ type: paste (#9)
    clip = FakeClipboard("PREVIOUS")
    hands._clipboard_backend = lambda: clip
    long_text = "x" * 200
    calls.clear()
    r = client.post("/type", json={"text": long_text}, headers=AUTH)
    body = r.get_json()
    check("type 200 chars with clipboard -> paste path",
          r.status_code == 200 and body["method_used"] == "paste"
          and body["chars"] == 200)
    check("paste set clipboard to text then restored previous value",
          clip.sets == [long_text, "PREVIOUS"] and clip.store == "PREVIOUS")
    check("paste used hotkey('ctrl','v') and never write()",
          ("hotkey", ("ctrl", "v"), {}) in calls
          and "write" not in names())

    calls.clear()
    r = client.post("/type", json={"text": long_text, "method": "keys"},
                    headers=AUTH)
    check("type method=keys forces keystrokes even for long text",
          r.status_code == 200 and r.get_json()["method_used"] == "keys"
          and set(names()) == {"write"} and clip.store == "PREVIOUS")

    # Paste requested but no backend -> keys fallback, and it says so.
    hands._clipboard_backend = lambda: None
    calls.clear()
    r = client.post("/type", json={"text": "abc", "method": "paste"},
                    headers=AUTH)
    body = r.get_json()
    check("type method=paste without backend -> keys fallback + note",
          r.status_code == 200 and body["method_used"] == "keys"
          and bool(body.get("note")) and set(names()) == {"write"})

    # Paste path whose clipboard blows up -> keys fallback, not a 500.
    class BoomClipboard:
        def get_text(self):
            raise RuntimeError("boom")

        def set_text(self, text):
            raise RuntimeError("boom")

    hands._clipboard_backend = lambda: BoomClipboard()
    calls.clear()
    r = client.post("/type", json={"text": "y" * 200}, headers=AUTH)
    check("type paste failure falls back to keys (no 500)",
          r.status_code == 200 and r.get_json()["method_used"] == "keys"
          and set(names()) == {"write"})
    hands._clipboard_backend = orig_backend

    # ------------------------------------------ type re-check (R7.2, #27)
    # The F7 mid-type abort must tell owner input from the type's own
    # keystrokes. A virtual last-input tick models the session: our
    # writes stamp it, a scripted owner event stamps it during a chosen
    # inter-char sleep, and _probe_dwtime reads it back.
    check("_dw_advanced: strictly newer tick reads advanced",
          hands._dw_advanced(200, 100) is True
          and hands._dw_advanced(100, 200) is False
          and hands._dw_advanced(100, 100) is False)
    check("_dw_advanced: wrap-safe across the 32-bit tick boundary",
          hands._dw_advanced(5, 0xFFFFFFF8) is True
          and hands._dw_advanced(0xFFFFFFF8, 5) is False)

    # jitter=False stays the single pyautogui.write, untouched by the
    # re-check machinery.
    calls.clear()
    hands._clipboard_backend = lambda: None
    r = client.post("/type", json={"text": "hello", "method": "keys",
                                   "jitter": False}, headers=AUTH)
    check("type jitter=false -> one write(text, interval=0.02)",
          r.status_code == 200
          and calls == [("write", ("hello",), {"interval": 0.02})])

    class _InputClock:
        def __init__(self, owner_on_sleep=None):
            self.tick = 100000
            self.dw = self.tick - 5001  # last input ~5 s before the door
            self.sleeps = 0
            self.owner_on_sleep = owner_on_sleep

        def probe(self):
            return self.dw

        def write(self, ch):
            calls.append(("write", (ch,), {}))
            self.tick += 10
            self.dw = self.tick  # our keystroke is the freshest input

        def sleep(self, _seconds):
            self.sleeps += 1
            if self.sleeps == self.owner_on_sleep:
                self.tick += 10
                self.dw = self.tick  # the owner's key lands in this pause

    orig_write = fake_pag.write
    orig_sleep_stub = hands.time.sleep
    orig_probe_dwtime = hands._probe_dwtime
    url40 = "https://www.spotify.com/account/privacy/"
    try:
        # (a) Only our own keystrokes move dwTime: all 40 chars land.
        clock = _InputClock()
        fake_pag.write = clock.write
        hands.time.sleep = clock.sleep
        hands._probe_dwtime = clock.probe
        calls.clear()
        r = client.post("/type", json={"text": url40, "method": "keys"},
                        headers=AUTH)
        body = r.get_json()
        written = "".join(c[1][0] for c in calls if c[0] == "write")
        check("type 40 chars, own keystrokes only -> completes, no abort",
              r.status_code == 200 and body["ok"] is True
              and body["method_used"] == "keys" and body["chars"] == 40
              and written == url40)

        # (b) Owner input during the pause after char 18: the type
        # aborts at the next 12-char boundary (24) with the honest
        # partial, and nothing past the boundary is typed.
        clock = _InputClock(owner_on_sleep=18)
        fake_pag.write = clock.write
        hands.time.sleep = clock.sleep
        hands._probe_dwtime = clock.probe
        calls.clear()
        r = client.post("/type", json={"text": url40, "method": "keys"},
                        headers=AUTH)
        body = r.get_json()
        written = "".join(c[1][0] for c in calls if c[0] == "write")
        check("type owner input mid-type -> 409 type_aborted at char 24",
              r.status_code == 409 and body["ok"] is False
              and body["error_code"] == "type_aborted"
              and body["aborted"] is True and body["chars_typed"] == 24
              and body["chars"] == 40 and written == url40[:24])
    finally:
        fake_pag.write = orig_write
        hands.time.sleep = orig_sleep_stub
        hands._probe_dwtime = orig_probe_dwtime
        hands._clipboard_backend = orig_backend

    # ------------------------------------------------ windows + focus (#3)
    wins = [win("Alpha Editor"), win("Beta - alpha notes"), win("Gamma")]
    hands._enum_windows = lambda: wins
    activated = []
    hands._activate_window = lambda w: activated.append(w) or True

    r = client.get("/windows", headers=AUTH)
    body = r.get_json()
    check("windows route shape",
          r.status_code == 200 and body["ok"] and len(body["windows"]) == 3
          and body["windows"][0] == {
              "title": "Alpha Editor", "process": "app.exe", "pid": 42,
              "bounds": {"x": 1, "y": 2, "w": 300, "h": 200},
              "monitor": 0, "visible": True, "focused": False})
    check("windows entries carry no private keys",
          all(not any(k.startswith("_") for k in w) for w in body["windows"]))

    r = client.post("/focus", json={"title": "NOTES"}, headers=AUTH)
    check("focus substring (case-insensitive) activates the right window",
          r.status_code == 200 and len(activated) == 1
          and activated[0]["title"] == "Beta - alpha notes"
          and r.get_json()["window"]["title"] == "Beta - alpha notes")

    activated.clear()
    r = client.post("/focus", json={"title": "no such window"}, headers=AUTH)
    check("focus no match -> 404, nothing activated",
          r.status_code == 404 and not activated)

    activated.clear()
    r = client.post("/focus", json={"title": "alpha", "exact": True},
                    headers=AUTH)
    check("focus exact=true rejects a substring-only match",
          r.status_code == 404 and not activated)
    r = client.post("/focus",
                    json={"title": "alpha editor", "exact": True},
                    headers=AUTH)
    check("focus exact=true matches the full title",
          r.status_code == 200 and len(activated) == 1
          and activated[0]["title"] == "Alpha Editor")
    hands._enum_windows = orig_enum
    hands._activate_window = orig_activate

    # Off-Windows the real enumerator yields an empty, supported=false list.
    r = client.get("/windows", headers=AUTH)
    body = r.get_json()
    if os.name != "nt":
        check("windows off-Windows -> empty list, supported false, no 500",
              r.status_code == 200 and body["windows"] == []
              and body.get("supported") is False)

    # ------------------------------------------------ clipboard (#6)
    clip = FakeClipboard("clip contents")
    hands._clipboard_backend = lambda: clip
    while not hands.log_queue.empty():
        hands.log_queue.get_nowait()
    r = client.get("/clipboard/get", headers=AUTH)
    logged = []
    while not hands.log_queue.empty():
        logged.append(hands.log_queue.get_nowait())
    check("clipboard get returns the backend text",
          r.status_code == 200 and r.get_json()["text"] == "clip contents")
    check("clipboard read is written to the hands log queue",
          "clipboard read via relay" in logged)

    r = client.post("/clipboard/set", json={"text": "new text"}, headers=AUTH)
    check("clipboard set stores via the backend",
          r.status_code == 200 and clip.store == "new text")

    hands._clipboard_backend = lambda: None
    r = client.get("/clipboard/get", headers=AUTH)
    check("clipboard get unavailable -> 501",
          r.status_code == 501
          and r.get_json()["error"] == "clipboard unavailable on this host")
    r = client.post("/clipboard/set", json={"text": "x"}, headers=AUTH)
    check("clipboard set unavailable -> 501", r.status_code == 501)
    hands._clipboard_backend = orig_backend

    # --------------------------------- windows clipboard backend (R7.2)
    # _WindowsClipboardBackend never runs off Windows, which is how
    # the data.size AttributeError shipped (#26). Fake the _setup dll
    # pair + ctypes.memmove and pin the exact call shape.
    clip_log = []

    class _FakeUser32:
        def OpenClipboard(self, arg):
            clip_log.append(("OpenClipboard", (arg,)))
            return 1

        def EmptyClipboard(self):
            clip_log.append(("EmptyClipboard", ()))
            return 1

        def SetClipboardData(self, fmt, handle):
            clip_log.append(("SetClipboardData", (fmt, handle)))
            return handle

        def CloseClipboard(self):
            clip_log.append(("CloseClipboard", ()))
            return 1

    class _FakeKernel32:
        def GlobalAlloc(self, flags, nbytes):
            clip_log.append(("GlobalAlloc", (flags, nbytes)))
            return 4242

        def GlobalLock(self, handle):
            clip_log.append(("GlobalLock", (handle,)))
            return 8192

        def GlobalUnlock(self, handle):
            clip_log.append(("GlobalUnlock", (handle,)))
            return 1

    def _fake_memmove(ptr, data, nbytes):
        clip_log.append(("memmove", (ptr, len(data), nbytes)))

    win_clip = hands._WindowsClipboardBackend()
    win_clip._setup = lambda: (_FakeUser32(), _FakeKernel32())
    clip_text = "https://www.spotify.com/account/privacy/"
    expect_nbytes = ctypes.sizeof(ctypes.create_unicode_buffer(clip_text))
    orig_memmove = ctypes.memmove
    ctypes.memmove = _fake_memmove
    try:
        win_clip.set_text(clip_text)
        clip_error = None
    except Exception as exc:  # the pre-fix AttributeError lands here
        clip_error = exc
    finally:
        ctypes.memmove = orig_memmove
    check("windows clipboard set_text runs clean against the faked dlls",
          clip_error is None)
    check("windows clipboard order open->empty->alloc->lock->move->unlock->set->close",
          [entry[0] for entry in clip_log] == [
              "OpenClipboard", "EmptyClipboard", "GlobalAlloc",
              "GlobalLock", "memmove", "GlobalUnlock",
              "SetClipboardData", "CloseClipboard"])
    by_name = {entry[0]: entry[1] for entry in clip_log}
    check("windows clipboard GlobalAlloc gets GMEM_MOVEABLE + sizeof bytes",
          by_name.get("GlobalAlloc") == (0x0002, expect_nbytes))
    check("windows clipboard memmove moves the whole buffer, byte count sizeof",
          by_name.get("memmove") == (8192, len(clip_text) + 1, expect_nbytes))
    check("windows clipboard SetClipboardData gets CF_UNICODETEXT + the handle",
          by_name.get("SetClipboardData") == (13, 4242))

    print("FAILED: " + ", ".join(failures) if failures else "ALL PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    finally:
        # Importing the hands creates its config next to the module when
        # none exists; never leave that artefact behind from a test run.
        if not _config_existed and os.path.exists(CONFIG_PATH):
            os.remove(CONFIG_PATH)

```

**Stage 1 deliverable:** fixes for findings 1–3 in `hands/muse_relay_hands.py` (complete file or anchored diff), the three named tests added and passing per-file, plus the stage report. If your mechanism for finding 1 differs from timestamp attribution (the verdict warns timestamp-only post-write attribution cannot reliably distinguish the events), say so explicitly and show the provenance mechanism in the code.
---
# STAGE 2 — R9 wishlist build: human-like pointer system + jiggler

**Base:** NEW branch `v3-r9-20261020` off the Stage-1 tip (your fixed R7.2). Same repo.

Implement the human-like pointer system and the idle jiggler specified by wishlist items #24, #28, #29, #30 (full text below). The two Gemini reference documents behind #29/#30 are summarized into concrete parameters after the wishlist text — build to those numbers.

## Wishlist #24 (full text)

24. **Human-like pointer motion for clicks and drags** — Christopher's
    direction 2026-10-19 18:39, during the R4 chess benchmark (whose
    clicks move in straight lines at constant speed — visibly robotic).
    His spec, verbatim in substance: clicks and drags should move like
    a human — more arc and sway in the path, acceleration and velocity
    jitter and variation, random light overshoot of the target with a
    settle-back — **even if it costs up to 0.5 sec per click on top of
    the current per-click time** (his explicit latency budget,
    clarified 18:40: additional to what it is now — R4's benchmark
    median is 5.14s submit-to-applied, mostly yield wait). Applies to
    the move/click/drag path in the
    hands service; per-act variation must be random, not a fixed curve
    (a fixed curve is just a new signature).
## Wishlist #28, #29, #30 (full text, incl. the #23/#25 GUI resolution note that follows them)

## #28 — Realistic mouse jiggler, intensity decays with idle length (Christopher's direction 2026-10-20 00:15)
A relay-side mouse jiggler that moves the pointer in small, human-like motions while the PC is unattended, with intensity that DECREASES the longer the idle lasts: more frequent and larger movements in the first minutes of idle, tapering to rare micro-movements after long idle (a person settles over time; a constant-rate jiggler is itself a robotic signature). Hard constraints: (1) real owner input kills it instantly and resets the idle clock — it never fights the owner; (2) its own injected motion must NOT register as owner activity in the yield/idle probe (WP0b) — the probe has to distinguish jiggler motion from owner motion, or queued acts will start yielding against the jiggler itself; (3) movement paths follow item 24's human-like rules (arc, sway, velocity jitter, light overshoot + settle), randomized per movement, never a fixed pattern.

## #29 — Movement-realism implementation reference (Gemini notes, via Christopher 2026-10-20 05:13)
Christopher pasted a Gemini write-up on human-like cursor movement into the main chat as reference for this list. Full text saved at ~/workspace/hands-eyes-gemini-mouse-realism-20261020.md. It governs the implementation of #24 (pointer motion) and #28 (jiggler motion). What it adds beyond #24's existing spec: cubic Bezier paths with 1–2 randomized control points; a Fitts's Law velocity profile (slow start, fast middle scaled by distance, hard deceleration into the target); Perlin/wind noise injected along the path; a 40–120 ms pause on target before the click fires; landing points Gaussian-distributed inside the target's bounding box (center-weighted, occasional edge hits) instead of always dead-center; click down/up duration randomized 50–150 ms; scrolling in variable chunks with pauses instead of a single jump.

## #30 — Behavioral layer for pointer work (Gemini notes #2, via Christopher 2026-10-20 05:18)
Second Gemini reference: where #29 covers per-path coordinate physics, this covers the session life-cycle that behavioral scorers actually grade. Full text at ~/workspace/hands-eyes-gemini-mouse-behavior-20261020.md. Rules: (1) attention buffer — 200–700 ms context-aware hesitation before moving toward a newly rendered target, scaling with on-screen text volume; (2) idle drift — after 30–60 s without action, 1–3 px organic jitters or lazy drifts (this is the behavioral core of the #28 jiggler — the two items should be built as one system); (3) structural overshoot error rate — ~15% of approaches miss the box by 5–10 px and correct with a fast secondary curve (beyond #24/#29's path-level overshoot); (4) input mutex — never mouse + keys simultaneously; 150–300 ms hand-travel delay between keyboard and mouse actions; (5) context-switch physics — cursor never teleports on tab/window switches; it stays put or exits/re-enters at a screen edge; (6) Fitts extension — target SIZE dictates the speed profile, tiny targets get a slower, longer settle. Context answers noted for the builder: this relay drives ONE owner session on one PC (Abraham) — no multi-profile orchestration; keyboard typing profiles ARE in scope alongside mouse (the type op; see #27) — a dedicated typing-profile entry may be worth splitting out when this gets built.

## Resolution note — #23/#25 GUI route DECIDED (2026-10-20 05:23 CDT)
Christopher asked whether the relay app could get a GUI that "doesn't look like it's VBA" — the current window is Tkinter, and Tk's Windows widgets are that era's look. He picked the recommended route: a LOCAL WEB UI in an app window (locally served HTML/CSS/JS dashboard in a native window shell, pywebview-style), over PySide6/Qt and over a CustomTkinter reskin. This supersedes #23's earlier builder pin (Muse first build / Opus refinement): under his 2026-10-20 direction, ASTRA implements the GUI as Stage 3 of the R9 round (dashboard scope per #23), and because Astra is this round's builder, the independent pre-deploy review goes to a fresh Opus session. Stage order: R7.2 fix round → R9 motion/jiggler → R9 web GUI (deadline 2026-10-21 17:00 CDT).
## Concrete parameters (distilled from the two Gemini reference documents)

Per-path physics (#29):
- Cubic Bezier path with 1–2 randomized control points; no straight-line travel.
- Fitts's Law velocity profile: slow start (inertia), fast middle with peak velocity scaled by distance, hard deceleration into the target.
- Perlin/wind noise injected into x/y along the path (micro-tremor, never a smooth analytic curve alone).
- Pause on target before click: random 40–120 ms.
- Landing point: Gaussian-distributed inside the target bounding box (center-weighted, occasional edge hits); never always dead-center.
- Click duration (down→up): random 50–150 ms.
- Scrolling: variable chunks with tiny pauses, never a single teleport jump.

Behavioral layer (#30):
- Attention buffer: before moving toward a newly rendered target, a random context-aware hesitation of 200–700 ms, scaling up with the amount of on-screen text to "read".
- Idle drift: after 30–60 s without an action, minute organic jitters (1–3 px) or lazy sweeping drifts across empty space. (This is the jiggler's behavioral core — build motion system + jiggler as ONE system.)
- Structural overshoot error rate: ~15% of approaches intentionally miss the target box by 5–10 px, then correct with a hyper-fast secondary deceleration curve before clicking.
- Input mutex: never mouse motion simultaneous with keystrokes; enforce 150–300 ms hand-travel delay when sequencing keyboard → mouse or mouse → keyboard.
- Context-switch physics: on tab/window focus change the cursor does NOT teleport — it stays at its last position or exits/re-enters at a screen edge.
- Fitts extension: target SIZE dictates speed — large targets fast and loose; tiny targets (close buttons, checkboxes) explicitly slower with a longer settle.

## Hard constraints (from the wishlist — non-negotiable)

(a) **Latency budget (owner-set):** the human-like motion adds **at most +0.5 s per click** over the current per-click time. Any parameter that would exceed the budget must degrade gracefully (shorter path embellishment), not blow the budget.
(b) **Jiggler:** intensity **DECREASES** with idle length (frequent/larger early, rare micro-movements later — never a constant rate). Real owner input kills the jiggler **instantly** and resets the idle clock. Jiggler motion must **NOT** register as owner activity in the WP0b yield/idle probe — the probe must distinguish jiggler-injected motion from owner input, or queued acts will yield against the jiggler itself.
(c) **Randomization:** every movement's parameters are drawn per movement; never a fixed pattern or a fixed curve (a fixed curve is just a new signature).
(d) **Feature flags:** the motion system and the jiggler sit behind separate flags — motion flag **default ON**, jiggler flag **default OFF**.

## Existing motion code you build on (`hands/muse_relay_hands.py` @ Stage-1 base)

The hands service already has `_plan_key_delays`, `_ease_in_out_cubic`, `_bezier`, `_plan_path`, `_move_human`, `move()`, `click()`, `drag()` — extend/replace coherently; do not bolt on a parallel system that disagrees with these seams.

```python
def _plan_key_delays(text, rng):
    """Per-character typing delays (seconds slept AFTER each character).

    Base delay is uniform in [0.04, 0.16]; a character that ends a word
    (space) adds uniform [0.05, 0.20] and one that ends a sentence
    (. ! ?) adds uniform [0.10, 0.30]. If the total exceeds the budget
    max(5.0, len(text) * 0.16) every delay is scaled down proportionally
    so long pastes stay bounded.
    """
    delays = []
    for ch in text:
        delay = rng.uniform(0.04, 0.16)
        if ch == " ":
            delay += rng.uniform(0.05, 0.20)
        elif ch in ".!?":
            delay += rng.uniform(0.10, 0.30)
        delays.append(delay)
    budget = max(5.0, len(text) * 0.16)
    total = sum(delays)
    if total > budget and total > 0:
        scale = budget / total
        delays = [d * scale for d in delays]
    return delays


def _ease_in_out_cubic(t):
    if t < 0.5:
        return 4 * t * t * t
    return 1 - ((-2 * t + 2) ** 3) / 2


def _bezier(p0, pc, p1, t):
    u = 1 - t
    return (
        u * u * p0[0] + 2 * u * t * pc[0] + t * t * p1[0],
        u * u * p0[1] + 2 * u * t * pc[1] + t * t * p1[1],
    )


def _plan_path(x0, y0, x1, y1, rng):
    """Human-like mouse path: list of (x, y, delay_after) steps.

    Quadratic bezier from start to target, control point pushed off the
    midpoint perpendicular by up to 8% of the distance, parameter eased
    with easeInOutCubic. The first ~85% of steps aim at an overshoot
    point just past the target; the rest settle back to the EXACT
    target, which is always the final step. Total duration is
    clamp(0.25 + d/2500, 0.3, 1.1) seconds, spread evenly across steps.
    A move under 4px is a single step straight to the target.
    """
    dx, dy = x1 - x0, y1 - y0
    dist = math.hypot(dx, dy)
    total = min(1.1, max(0.3, 0.25 + dist / 2500))
    if dist < 4:
        return [(x1, y1, total)]
    n = max(8, min(60, int(dist / 12)))
    offset = rng.uniform(-0.08 * dist, 0.08 * dist)
    ctrl = (
        (x0 + x1) / 2 + (-dy / dist) * offset,
        (y0 + y1) / 2 + (dx / dist) * offset,
    )
    # Overshoot: extend past the target along the bezier's final
    # direction (target - control point).
    fx, fy = x1 - ctrl[0], y1 - ctrl[1]
    flen = math.hypot(fx, fy)
    if flen == 0:
        fx, fy, flen = dx, dy, dist
    over = min(6.0, 0.02 * dist)
    over_pt = (x1 + fx / flen * over, y1 + fy / flen * over)

    n_over = max(1, int(round(n * 0.85)))
    if n_over >= n:
        n_over = n - 1
    points = []
    for i in range(1, n_over + 1):
        t = _ease_in_out_cubic(i / n_over)
        points.append(_bezier((x0, y0), ctrl, over_pt, t))
    n_settle = n - n_over
    for j in range(1, n_settle + 1):
        s = j / n_settle
        points.append(
            (over_pt[0] + (x1 - over_pt[0]) * s, over_pt[1] + (y1 - over_pt[1]) * s)
        )
    points[-1] = (x1, y1)  # exact target, always
    per = total / n
    steps = [(px, py, per) for (px, py) in points]
    # Pin the delay sum to the planned total despite float rounding.
    steps[-1] = (steps[-1][0], steps[-1][1], total - per * (n - 1))
    return steps


def _move_human(x, y, rng=None):
    """Move the cursor to (x, y) along a planned human-like path."""
    rng = rng if rng is not None else random
    x0, y0 = pyautogui.position()
    for sx, sy, delay in _plan_path(x0, y0, x, y, rng):
        pyautogui.moveTo(sx, sy, duration=0)
        time.sleep(delay)


@app.post("/move")
def move():
    d = request.get_json(force=True)
    x, y = int(d["x"]), int(d["y"])
    if d.get("human", True):
        _move_human(x, y)
    else:
        pyautogui.moveTo(x, y, duration=0.2)
    return {"ok": True}


@app.post("/click")
def click():
    d = request.get_json(force=True)
    x, y = int(d["x"]), int(d["y"])
    button = d.get("button", "left")
    if d.get("human", True):
        _move_human(x, y)
        time.sleep(random.uniform(0.05, 0.15))  # hover before the click
    else:
        pyautogui.moveTo(x, y, duration=0.2)
    pyautogui.click(x=x, y=y, button=button)
    return {"ok": True}


@app.post("/type")

# ---- drag() ----

def drag():
    """Press the mouse button at (x1, y1), drag to (x2, y2), release."""
    refused = _yield_if_active()
    if refused is not None:
        return refused
    d = request.get_json(force=True, silent=True) or {}
    try:
        x1, y1, x2, y2 = (int(d[k]) for k in ("x1", "y1", "x2", "y2"))
    except (KeyError, TypeError, ValueError):
        return jsonify({"ok": False, "error": "x1, y1, x2, y2 must be integers"}), 400
    button = d.get("button", "left")
    if button not in ("left", "middle", "right"):
        return jsonify({"ok": False, "error": "button must be left, middle or right"}), 400
    try:
        duration = float(d["duration"]) if d.get("duration") is not None else 0.4
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "duration must be a number"}), 400
    pyautogui.moveTo(x1, y1)
    down = False
    try:
        # Mark first so a mouseDown/move failure still releases the button.
        # duration 0 is real; do not coerce it with `or 0.4`.
        down = True
        pyautogui.mouseDown(button=button)
        pyautogui.moveTo(x2, y2, duration=duration)
    finally:
        if down:
            pyautogui.mouseUp(button=button)
    return {"ok": True}


# ------------------------------------------- V3-P4: windows + focus (#3)

def _monitor_for_bounds(bounds, rects=None):
    """Index of the monitor rect containing the window's centre, else None."""
```

**Stage 2 deliverable:** new module(s) + integration into the hands act path (move/click/drag, and the type/sequencing paths where the input mutex applies) + tests (per-file green under the repo convention) + a short design note mapping **each wishlist rule → the code location that implements it**. **Deadline: today 2026-10-20, 17:00 CDT.**
---
# STAGE 3 — R9 relay GUI rebuild: local web UI in an app window

**Base:** same branch as Stage 2 — `v3-r9-20261020`, on top of your Stage 2 work.
**Owner's decision (2026-10-20 05:23 CDT):** the relay app's Tkinter window is replaced by a **local web UI** — a locally served HTML/CSS/JS dashboard presented in a native app window shell (pywebview or an equivalent native-window wrapper around the local page). This route supersedes wishlist #23's earlier builder pin (see the resolution note in the wishlist text above). The owner's words for the current Tk window: it looks like VBA. The replacement must look and feel like a designed, modern local app — wishlist #23's bar: "super AAA."

## Scope (wishlist #23)

23. **Super-AAA interface for the relay app** — Christopher's direction
    2026-10-19 18:20, mid-R4-deploy: "next revision needs a bad ass
    interface, super AAA." The current app window is functional-minimal.
    Want: a designed dashboard — service health (gateway/hands/parser),
    claim + yield state, probe health, a live act/receipts feed,
    one-click diagnostics — with AAA polish throughout. Tier pinned by
    Christopher the same minute: "thats an opus task for sure."
    Correction 18:21, same evening: the FIRST revision is Muse's —
    design + first build — with Opus on refinement passes after.
    Rides the R6 round, alongside the F1 decision.
## Behavioral requirements (hard — these preserve how the app actually works)

1. **No auto-start, ever.** The current app does NOT start services on launch: the window opens idle and waits for its Start button ("Press Start to run all three services in this window"). The web UI must preserve **explicit Start/Stop control** of the three services (gateway / hands / parser), with each service's live state visible exactly as the current tiles show it.
2. **Existing config + token flow keep working.** The app reads/writes `muse_relay_config.json` and the per-launch gateway token flow (token generated/loaded by the app, shown in the window for the operator to copy, never logged). The web UI must not break the config file's shape or the token's lifecycle.
3. **One GUI.** The Tkinter window is removed or fully superseded — no dual GUIs, no leftover Tk entry point.
4. **Everything the Tk window does today must have a web-UI home:** service tiles + status lines, the scrolling log, hands claim + queue state, PC lock / probe state, receipts summary, one-click diagnostics (copy to clipboard), copy-token, the elevation-request approval dialog (the ONLY approval path for elevated runs — preserve its semantics exactly: a named request from the operator's allowlist, resolved only by a person in the window), and the "Start on login" toggle.

## Current app file — structure + UI sections (`muse_relay_v2_app.py` @ Stage-1 base, 1210 lines)

The app imports tkinter at line 50 and owns Start/Stop + tiles + log behavior. Full def/class outline:

```
80: def _winreg():
90: def _autostart_command():
98: def _autostart_enabled():
117: def _set_autostart(enabled):
145: class ServiceHealth:
156: def __init__(self, max_consecutive=3, max_restarts=3):
163: def note(self, ok):
191: def _fmt_duration(seconds):
211: def _receipt_entries(receipts):
235: def _snapshot_receipt_rows(table):
255: def summarize_receipts(receipts, now, limit=8):
286: def receipt_state_counts(receipts):
296: def build_dashboard_model(info, claim, queue, reserved_for, receipts, now):
374: def format_diagnostics(model, stamp):
426: def _app_dir():
433: def _icon_path():
442: def _hands_secret_path():
446: def _load_or_create_hands_secret():
476: def _gateway_token_path():
480: def _load_or_create_gateway_token():
511: def _service_path(rel_path):
521: def _load_service(name, rel_path):
532: class RelayApp:
533: def __init__(self, root):
557: def _build_ui(self):
621: def _build_dashboard(self, root):
667: def _render_dashboard(self, model):
734: def _copy_diagnostics(self):
743: def _copy_token(self):
748: def _toggle_autostart(self):
763: def _stamp(self):
766: def log_line(self, msg):
769: def set_status(self, which, text):
772: def _handle_elevation_request(self, hands, req):
822: def _drain_queue(self):
887: def _start_all(self):
937: def _start_one(self, name):
945: def _start_one_locked(self, name):
1031: def _skip_restart(self, name):
1056: def _note_health(self, name, ok):
1089: def _poll(self):
1190: def stop(self):
1203: def main():
```

Module docstring (the app's own description of its behavior contract):

```python
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
```

`RelayApp.__init__` + Tk UI construction + dashboard build/render (the window you are replacing):

```python
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

```

Service start machinery (`_start_all`, `_start_one`, `_start_one_locked`):

```python
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

```

`stop()` + `main()`:

```python
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
```

**Stage 3 deliverable:** the web UI — served dashboard assets (HTML/CSS/JS) + the local server wiring in the app + the native window shell + the Tk removal — with tests and/or smoke notes under the repo's per-file convention (the existing app test files are `test_app.py` and `tests/test_v3r6.py` / `test_v3r7.py`; extend or supersede them coherently and say which). A reviewer must be able to confirm from your code alone that Start/Stop semantics, config shape, and token flow are unchanged. **Deadline: Wed 2026-10-21, 17:00 CDT.**
