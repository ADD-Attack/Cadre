# R7.2 fix round — answer to Astra's DEPLOY-NO-GO on `22a9080` (+ Grok)

Branch `v3-r7-2-fix-20261020`, based on `v3-r7-2-20261019` @ `22a9080`. Nothing deployed.
All code is in `hands/muse_relay_hands.py`; tests in `tests/test_r72_fixround.py` unless noted.

## Mechanism
Finding 1 says timestamp attribution cannot be made reliable, so the
primary guard is now **event provenance**: `_OwnerInputMonitor` installs
WH_KEYBOARD_LL + WH_MOUSE_LL hooks in its own message-loop thread and
counts events by the INJECTED flag (LLKHF_INJECTED / LLMHF_INJECTED).
All relay input is SendInput (pyautogui), so it is flagged; the owner's
is not. `_TypeOwnerGuard` (mode `hook`) compares the owner counter with
its value at type start — an owner event inside one of our `write()`
calls is still counted as the owner's.

The dwTime mechanism remains only as the fallback (`dwtime` mode: hooks
unavailable, failed to install, died, or deaf to our own injected keys)
with the Grok and Finding 5 fixes. Off Windows the guard is `none`
(inert, like the door). Every /type response reports `owner_guard`.

## Finding → fix → proof
| Finding | Fix (code) | Test |
|---|---|---|
| 1 High: post-write probe adopts owner input | provenance counters (`_OwnerInputMonitor`, `_TypeOwnerGuard` hook mode) | `test_owner_input_between_injection_and_postwrite_probe_aborts` (owner event inside write 18 → 409, chars_typed 24, exactly 24 written) |
| 2 High: lock protection removed | lock-only `_probe_locked()` at every 12-char boundary (never the idle half) | `test_type_aborts_on_lock_without_input` (lock after 18, timestamps unchanged → 409 `abort_reason: locked`, exactly 24); `test_lock_check_is_lock_only_not_self_triggering_idle` |
| 3 Medium: boundary before fresh sample | `guard.sample()` runs first in each iteration, then the boundary decision | `test_owner_input_after_char12_aborts_before_char13` [hook, dwtime] (→ 12 typed, first 12 only) |
| Grok: one failed post-write probe → stale baseline → self-abort at 12 | a None post-write probe invalidates the baseline (`self_dw = None`); an unknown baseline never reads as owner; next good probe re-baselines | `test_single_failed_postwrite_probe_does_not_self_abort`, `test_repeated_probe_failures_do_not_self_abort`, `test_probe_failure_then_recovery_still_detects_owner` |
| 5 Medium: dwTime assumptions | delayed publication: an advance stamped ≤ write-end tick + `_DW_PUBLISH_GRACE_MS` (30) is ours; backward stamps never count (`_dw_advanced`); hook liveness check degrades deaf/dead hooks | `test_relay_event_published_after_postwrite_probe_does_not_self_abort`, `test_backward_timestamp_is_not_owner_activity`, `test_owner_input_past_publish_grace_is_detected`, `test_dw_advanced_exact_half_range`, `test_deaf_hooks_degrade_to_dwtime`, `test_hook_thread_dying_mid_op_degrades`, `test_publish_grace_blind_window_is_bounded_and_documented` |
| 4 Medium: clipboard fake ≠ Windows | `_setup` now declares pointer-sized argtypes for GlobalUnlock/GlobalFree/GlobalAlloc/GetClipboardData/OpenClipboard (a 64-bit handle above 2³¹ raised ArgumentError before); memory is GlobalFree'd if SetClipboardData fails | `test_clipboard_setup_declares_pointer_sized_handles`, `test_clipboard_frees_memory_when_set_fails`, `test_clipboard_does_not_free_memory_the_clipboard_owns`; **release evidence still owed:** `tests/test_windows_clipboard_real.py::test_windows_clipboard_real_roundtrip` (empty / URL / non-BMP, independent UTF-16 read-back, clipboard saved+restored) — skips unless run on the PC with `RELAY_LIVE_CLIPBOARD=1` |
| 6 Low: duplicated GetLastInputInfo | one acquisition `_last_input_raw()` used by `_probe_dwtime_raw` and `_probe_lock_state_raw`; lock detection independent (`_probe_locked_raw`) | `test_lock_and_idle_share_one_last_input_acquisition`, `test_probe_locked_is_the_raw_lock_only` |
| 7 Low: mutation before try | `hands/test_actuation.py`: backend mutation + jitter=false request moved inside the protected `try` | file runs ALL PASS |

## Residual risks (attack these)
1. Hooks are unverified on the real desktop: install, INJECTED flags for pyautogui's SendInput, behaviour with an elevated foreground window (UIPI), and Windows silently removing a slow hook (the parser shares the process/GIL). The liveness check (no injected events seen after 2 writes → `dwtime`) is the guard against a dead hook.
2. Fallback blind window: in `dwtime` mode, owner input inside a write or within 30 ms after it is still attributed to the write (Finding 1's class, bounded and pinned by test). `owner_guard` in every response makes the mode visible.
3. Other injected sources (remote tools, the R9 jiggler) count as "not owner" under provenance — by design.
4. Reconcile at apply: the R9 branch adds `_INPUT`/`_type_dispatch` around the same `type_text`; the type loop here replaces the loop body only.
