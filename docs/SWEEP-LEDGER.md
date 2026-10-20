# R9 wishlist sweep — per-item ledger (Opus takeover, 2026-10-20)

Branch `v3-r9-20261020`; base `d562912` (main `61ff473` = live R7.1 + #5). Source text: docs/WISHLIST-FULL.md.
Status: done (this round) / already-done (landed before R9; evidence = commit + passing test file) / not-applicable / deferred / R7.2 (owned by the fix round, branch from `22a9080`).
Test runs are per file with `../relay-wishlist/.venv/bin/python` (pytest files via `-m pytest -q`, script files run directly → "ALL PASS"). Windows-live behaviour is stub-tested only; live steps in docs/VERIFICATION.md. Nothing deployed.

| # | Item | Status | Evidence / notes |
|---|------|--------|------------------|
| 1 | Persistent gateway token | already-done | `b0981db` (V3-R3); `muse_relay_v2_app.py` `_load_or_create_gateway_token`; test_gateway_token.py ALL PASS |
| 2 | File-drop op | already-done | `e765781` (V3-P3); hands `/filedrop/*`, gateway `/v1/filedrop`; hands/test_filedrop_state.py ALL PASS |
| 3 | Window inventory + focus | already-done | `9a6caea` (V3-P4); hands `/windows` `/focus`, gateway `/v1/windows`; hands/test_actuation.py, services/gateway/test_act_ops.py ALL PASS |
| 4 | Drag op | already-done (motion upgraded in #24) | `9a6caea`; hands `/drag`; test_actuation.py, test_act_ops.py ALL PASS |
| 5 | Wait-for op | already-done (+R9 hardening) | `e765781` + Astra R9 `d562912` (authenticated process-exit wait, PID identity); hands/test_process_wait.py 18 passed; producer/Windows verification outstanding |
| 6 | Clipboard ops | already-done; set-path crash = #26 | `9a6caea`; `/clipboard/set` `/clipboard/get`, `/v1/clipboard`; test_act_ops.py ALL PASS |
| 7 | Autostart + self-heal | already-done | `192d8c3` (V3-P6); app `AUTOSTART_RUN_KEY`, `_set_autostart`; test_app.py ALL PASS. GUI toggle re-homed in #23 |
| 8 | Elevation bridge | already-done | `192d8c3`; hands `/elevate`, gateway `/v1/elevate`; hands/test_elevation.py, test_find_elevate.py ALL PASS. Approval dialog re-homed in #23 |
| 9 | Fast text injection + sized timeout | already-done | `9a6caea`; gateway `_act_timeout`; test_act_ops.py ALL PASS |
| 10 | All-monitors capture | already-done | `ab67c18` (V3-P5); hands `/monitors`, `/screenshot` monitor param; hands/test_capture_realism.py ALL PASS |
| 11 | Region capture native res | already-done | `ab67c18`; test_capture_realism.py, services/gateway/test_screen_params.py ALL PASS |
| 12 | Find-text op | already-done | `192d8c3`; parser `/find`, gateway `/v1/find`; services/parser/test_find.py ALL PASS |
| 13 | Lock/sleep state | done | lock in `e765781`; display-sleep gap closed `1adf4e8`: /state adds screensaver, display_off_after_seconds, display_asleep; tests/test_r9_display_state.py 7 passed; live step VERIFICATION.md #13 step 5 |
| 14 | Conditional hash endpoint | already-done | `f40dc5a`; `/v1/screen/hash` stable=1 + ETag; services/gateway/test_screen_hash.py ALL PASS |
| 15 | Hands claim flag + queue | already-done | `95f99f6` (V3-P2); `/v1/hands/claim` `/release`; services/gateway/test_coordination.py ALL PASS. GUI surface in #23 |
| 16 | Keystroke jitter | already-done | `ab67c18`; hands `_plan_key_delays` (40–160 ms + word/sentence pauses, bounded); test_capture_realism.py ALL PASS. Type-abort bug = #27 (R7.2) |
| 17 | Realistic mouse movement | already-done → superseded by #24 | `ab67c18` `_plan_path`/`_move_human`; replaced by the #24/#29/#30 system |
| 18 | Yielded-input accounting | already-done | `95f99f6` + R4 `2684e04`; `/v1/act/queued` held/applied/refused-yielded/expired; test_coordination.py, test_receipt_eviction.py ALL PASS |
| 19 | Reliable break for TUIs | already-done | `9a6caea`; hands `/break` (true Ctrl+C chord), `/hotkey`; test_actuation.py ALL PASS; live chord check in VERIFICATION.md |
| 20 | Foreground re-verification for held acts | done | opt-in `expect_focus` guard existed (R4 F3). R9 closes the "capture at submit" gap: hands yield-409 carries `foreground_hwnd` (`_foreground_hwnd`), gateway `act_queued` pins held acts with `expect_focus {"hwnd"}` (caller's own wins; focus op exempt), `_focus_matches` matches hwnd exactly → retry into another window settles `failed`. tests/test_r9_sweep_acts.py |
| 21 | Receipt for every act | done | every submission files a receipt since R4 F4; R9 adds `applied_via` = `direct` / `after-hold` (null if not applied) per the wish's applied-direct / applied-after-hold split. tests/test_r9_sweep_acts.py |
| 22 | Auditable empty reads | done | audit: no gateway JSON route returns an empty 2xx body. R9 `integrity` after_request: explicit Content-Length + `X-Body-SHA256` on every buffered response, so a torn or emptied read is detectable as torn. tests/test_r9_sweep_acts.py. Proxy-side origin still unverified (needs live tailnet check) |
| 23 | Relay GUI — web UI in app window | pending | Stage 3; Tk dashboard first revision is `3ae718b`/`98057f8` |
| 24 | Human-like pointer motion | pending | Stage 2 |
| 25 | Opus GUI pass | deferred by owner | audit only. Note: the 2026-10-20 05:23 resolution routes the web-UI build through #23; #25 stays open for a later owner call |
| 26 | clipboard_set crash on PC | R7.2 | still present on this branch (`data.size` in `_WindowsClipboardBackend`); the fix is `22a9080` (sizeof) under the R7.2 fix round |
| 27 | type false-abort at char 12 + sequence scatter | R7.2 (a); (b) partly closed by #20 | (a) is R7.2 Findings 1–3 + the Grok stale-`self_dw` finding. (b) held acts are now auto-pinned per act (#20); a caller can still pin a whole sequence with `expect_focus` on every act |
| 28 | Idle jiggler, decaying intensity | pending | Stage 2 |
| 29 | Movement-realism reference | pending | satisfied by conforming #24/#28 |
| 30 | Behavioral layer | pending | satisfied by conforming #24/#28 |
