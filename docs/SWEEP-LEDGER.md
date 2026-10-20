# R9 wishlist sweep — per-item ledger (Opus takeover, 2026-10-20)

Branch `v3-r9-20261020`; base `d562912`. Status values: done / already-done / not-applicable / in-progress / pending / deferred (audit-only).
Evidence column cites commit, file:line, or test name. Nothing deployed.

| # | Item | Status | Evidence / notes |
|---|------|--------|------------------|
| 1–4 | (text not in WISHLIST-EXTRACT; auditing against code + ROADMAP) | pending | — |
| 5 | Process-exit wait | done (Astra) | `d562912`; 18 local tests + gateway services suite pass; producer/Windows verification outstanding |
| 6–12 | (text not in extract; audit pending) | pending | — |
| 13 | Display-sleep reporting | in-progress | gap identified by Astra, not implemented — first item |
| 14 | (text not in extract; audit pending) | pending | — |
| 15 | Hands claim flag + queue | pending | |
| 16 | Keystroke jitter (type op) | pending | likely already-done (V3-P4/P5 jittered per-char delays) — verify |
| 17 | Realistic mouse movement | pending | superseded/merged into #24 Stage 2 |
| 18 | Yielded-input accounting | pending | |
| 19 | Reliable break for foreground TUIs | pending | |
| 20 | Foreground re-verification for held acts | pending | |
| 21 | Receipt for every act | pending | |
| 22 | Auditable empty reads | pending | |
| 23 | Relay GUI (web UI in app window) — Stage 3 | pending | Opus owns |
| 24 | Human-like pointer motion — Stage 2 | pending | |
| 25 | Opus GUI pass | deferred by owner | audit only, no implementation |
| 26–27 | (text not in extract; audit pending) | pending | |
| 28 | Mouse jiggler, idle-decayed intensity — Stage 2 | pending | |
| 29 | Movement-realism reference | pending | satisfied by conforming #24/#28 |
| 30 | Behavioral layer for pointer work | pending | satisfied by conforming #24/#28 |

## Open questions
- Wishlist text for #1–#14 and #26–#27 is not in docs/; audit uses ROADMAP.md, VERIFICATION.md and code. Producer: send the full hands-eyes-wishlist.md if verbatim text is needed for evidence.
