# TAKEOVER BRIEF — Muse Relay build (Opus session, 2026-10-20)

You are the builder for the Muse Relay update, taking over from Astra (paused by owner direction). You work in the shared clone:

- Workspace: /home/openclaw/.openclaw/workspace-studio-3d/relay-r9-20261020
- Branch: v3-r9-20261020, HEAD at takeover: d56291224c33fd9cf32bfbb2162dfbe71a77447a (on main 61ff473)
- Live build on the owner's PC is R7.1. NOTHING you produce is deployed by you. No deployment, no PC-side changes.

## Files in this folder (docs/)
- IMPL-PACKET.md — the full implementation packet (86 KB): wishlist item specs, stage structure, test conventions, acceptance criteria. This is your primary spec.
- WISHLIST-EXTRACT.md — the owner's wishlist text for items #15–#22 and #25 (verbatim from hands-eyes-wishlist.md).

## Astra's state at handoff (verbatim)
Clone /home/openclaw/.openclaw/workspace-studio-3d/relay-r9-20261020, branch v3-r9-20261020, HEAD d56291224c33fd9cf32bfbb2162dfbe71a77447a on main 61ff473; #5 process-exit wait complete (authenticated hands probe, PID-reuse detection; 18 local tests passed, gateway services suite all pass; producer/Windows verification outstanding); wishlist audit in progress, no finalized per-item ledger; #13 display-sleep reporting gap identified, not implemented; everything else untouched incl. GUI and R7.2 fixes; working tree clean, nothing deployed; artifacts in workspace root: relay-full-20261020.bundle (verified), relay-r9-component-01.patch. #25 deferred-by-owner.

## Scope and order (owner-directed, do not reorder)
1. FIRST: the full wishlist sweep, items #1–#30, with a per-item completion ledger (done / already-done / not-applicable, with evidence per item). Stages 2+3 of the packet are inside the sweep. Items #29 and #30 are satisfied by conforming #24/#28 implementations (per the packet). Item #25 is DEFERRED BY OWNER — audit only, do not implement.
2. The GUI is part of the sweep and it is YOUR job (owner: "make sure opus does the GUI too"): a local web UI in an app window — locally served HTML/CSS/JS in a native shell. Hard requirements: preserve explicit Start/Stop (the app never auto-starts services on launch), muse_relay_config.json compatibility, the per-launch gateway-token flow, and no dual GUI (one GUI only).
3. LAST: the R7.2 fix round (branch v3-r7-2-20261019, commit 22a9080 is the base under review). It must answer Astra's independent review (DEPLOY-NO-GO): Finding 1 — post-write probe can adopt owner input as baseline (required test: test_owner_input_between_injection_and_postwrite_probe_aborts); Finding 2 — mid-type lock protection removed (required test: test_type_aborts_on_lock_without_input); Finding 3 — boundary check runs before fresh owner sample (required test: test_owner_input_after_char12_aborts_before_char13); Findings 4–7 — real-Windows clipboard roundtrip receipt, dwTime hardening tests. PLUS the Grok replication finding: a single failed post-write dwTime probe (None) leaves self_dw stale, so the op's own keystroke advance reads as owner activity and the type self-aborts at char 12 — fix and add a regression test.

## Rules
- Commit your work on branch v3-r9-20261020 (fix round on its own branch per the packet). Working tree clean at each delivery point.
- Tests: one pytest process per test file (the suites interfere if run in one process); test files must restore any sys.modules fakes they install.
- Keep the per-item ledger current in the workspace as you go — it is the delivery artifact for the sweep.
- You are on claude-cli / claude-opus-5-5, thinking low (owner-set). Work steadily; do not stop to ask questions the packet answers.

## Deadlines (America/Chicago)
- Wishlist sweep (incl. GUI): Wed 2026-10-21 17:00 CDT
- R7.2 fix round: Thu 2026-10-22 12:00 CDT

## ACK required
Reply with: (1) git log --oneline -3 and git status from the clone, (2) the order of work restated in your own words, (3) the first item you are starting.
