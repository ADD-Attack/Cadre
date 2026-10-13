# Muse Relay v2 — execution brief for Claude Opus 5.5

_You are Claude Opus 5.5, working in the repo `ADD-Attack/muse-relay-v2`.
Your job: complete the work packages below, in order, testing as you go,
and commit your work. This file is your spec — if something here conflicts
with the code, trust the code for current state and this file for intent,
and note the conflict in your handoff report._

_Intended run context: an Opus 5.5 coding session (for example a
Muse / OpenRouter-backed setup). API keys and tokens are supplied by
the operator's environment — never write one into this repo._

## Non-negotiables

- **Docker is optional, never required.** Both services are plain Python
  and must keep running natively on Windows. The compose file is an
  alternative deployment path, not the design.
- **The hands never run in Docker.** They need the interactive Windows
  desktop session. Do not containerize them, and do not design around a VM.
- **No secrets or personal data in the repo.** No tokens, session secrets,
  live tunnel URLs, IP addresses, email addresses, or home addresses —
  in code, docs, tests, logs, or commit messages. Refer to "the owner" /
  "the operator", never a person's name, outside the LICENSE file.
- **Do not weaken the security model.** Gateway: token auth with
  constant-time comparison and failed-guess lockout. Hands: a fresh
  session secret per launch. Nothing listens publicly by default;
  Tailscale is the preferred transport. A public tunnel is a fallback,
  never the design.
- **Do not break existing contracts casually.** The hands API
  (screenshot / move / click / type / key / scroll, `X-Secret` auth) and
  the parser set-of-marks contract (numbered elements with bbox + center)
  are relied on by the gateway. Extend them; if you must change one,
  update gateway + docs + tests in the same commit.
- **Never fake verification.** If a step needs the owner's physical PC, a
  GPU, or an account you don't have, implement everything that can be
  implemented, write the exact manual verification step down, and say
  plainly that it is unverified. A claim without a run behind it is a bug.

## Current state (starting point — verify against the code)

- `services/gateway/` — Flask + Waitress. Token auth + lockout;
  `/health`, `/v1/info` (backend reachability), `/v1/screen` (proxies the
  hands screenshot), `/v1/act` (forwards move/click/type/key/scroll),
  `/v1/parse` (forwards to the parser). The gateway reaches the hands via
  the `HANDS_URL` and `HANDS_SECRET` environment values.
- `services/parser/` — Flask + Waitress. Loads OmniParser v2 weights
  (icon detector, optional Florence captioner) from its models directory
  when present (`fetch_weights.py` downloads them; heavy deps are in
  `requirements-model.txt`). With no detector loaded, `/parse` returns
  501 — deliberately, so a driver never mistakes "no model" for "empty
  screen".
- `hands/` — the v1 packaged Windows app carried forward: screenshot,
  mouse, keyboard, per-session generated secret, lockout with phone
  alerts, Tailscale Serve preferred.
- Smoke-tested so far: gateway against a mock hands (auth rejection,
  screenshot proxying, action forwarding, wrong-secret error path) and
  the parser's honest not-loaded state. **Not yet proven:** end-to-end
  against the real hands on the owner's PC, and parser detection with
  real weights on a GPU.

## Work packages (do them in this order)

### WP0 — Windows end-to-end smoke script
Add a script (PowerShell or Python) that starts the parser and gateway
natively, checks `/health` and `/v1/info`, and — when the hands app is
running — pulls one screenshot and performs one harmless action through
the gateway. It prints a clear pass/fail per check and never prints a
secret.
**Done when:** one command on a Windows PC produces the report; when the
hands are not running it says exactly that instead of failing obscurely.

### WP1 — UIA endpoint in the hands
Add UI Automation to the hands (pywinauto): an endpoint returning the
control tree of the foreground window / desktop (name, control type,
bounding rect, center, automation id, enabled, off-screen), and an act
endpoint that clicks / invokes / sets text on an element by id from that
tree. Same session-secret auth as the existing endpoints. Add the
matching gateway route.
**Done when:** the tree for Notepad and File Explorer comes back with
usable rects, a named control in a test window is activated through UIA
(not pixels), and the pixel endpoints are unregressed.

### WP2 — Custom-tools registry in the gateway
A small registry where named tools can be registered and invoked through
the gateway (auth'd, allowlisted by name, every call logged). Ship two
or three safe tools first — for example launching an allowlisted app,
and reading window titles. Office/COM automation may be added behind an
optional import; it must not become a hard dependency.
**Done when:** tools are invokable through the gateway, unregistered
names are rejected, calls appear in the log, and unit tests with mocks
cover registration + rejection.

### WP3 — Batched actions (speculative multi-action support)
Extend `/v1/act` with a batch form: an ordered list of actions executed
in sequence, stopping at the first failure, returning a per-step result,
with an optional screenshot after the final step. Document the contract
in the README. (Motivation: planners can emit 3–5 steps per model call
instead of one round-trip per click.)
**Done when:** a batch runs in order, a failing step halts the batch and
is identified in the response, and the single-action form is unchanged.

### WP4 — Audit log + trajectory recording
The gateway records each session's actions to a local JSONL trajectory:
timestamp, op, target summary, result, and a screenshot hash (not full
screenshots by default). The storage directory is configurable, secrets
never appear in the log, and the format is documented so a failed run
can be replayed and debugged.
**Done when:** a smoke run produces a complete trajectory file, a secret
scan of the file comes back clean, and the README documents where logs
live and how they are rotated or deleted.

### WP5 — Browser element-index adapter (interface only)
Design and stub an adapter interface for browser surfaces in the
browser-use style: numbered DOM elements the planner can act on by
index, with a domain allowlist enforced by the adapter. Do not pull a
browser driver into the gateway's core dependencies; a real integration
belongs behind an optional extra.
**Done when:** the interface, the allowlist rule, and a fake-adapter
test exist, and the README marks real browser integration as optional
and not yet wired.

### WP6 — Spike only: nested desktop + host/app agent split
Research-only. Write `docs/SPIKE-NESTED-DESKTOP.md` assessing a
Picture-in-Picture style nested desktop (agent works in a nested
session, owner keeps theirs) and a host/app agent split for this relay:
feasibility on current Windows, security implications, and a clear
recommendation. **Do not implement either** — the spike's acceptance
criteria are what a future decision gets made on.

## Definition of done (every work package)

- Code + tests/smoke coverage for the new behavior; existing smoke
  behavior unregressed (`python -m py_compile` clean on touched files;
  gateway/parser run against the mock hands without errors).
- README and this file updated in the same commit: the package's box
  gets checked, and any new operator step (env value, command, manual
  check) is written down where an operator will actually find it.
- A secret scan of the diff comes back clean (no tokens, secrets,
  URLs-with-secrets, IPs, emails, addresses).

## Commit protocol

- Work on a branch named `opus-5-5-roadmap`; do not commit directly to
  `main`.
- Small commits: one work package per commit at most, split further when
  a package has separable steps. Message format: `WP<n>: <what changed>`.
- Run the relevant tests before each commit. If a test cannot run in
  your environment (needs Windows, a GPU, or the real hands), say so in
  the commit body and add the manual step to `docs/VERIFICATION.md`.
- Never commit: `.env` files, model weights, screenshots containing
  personal data, trajectory logs, build artifacts, or `__pycache__`.
- Push the branch when each work package lands. Do **not** merge to
  `main` yourself — the merge is the owner's call. Your final handoff
  (below) is what he reviews.

## Handoff report (end of run)

Report, in this order:
1. Work packages completed, with the commit hash for each.
2. Tests actually run and their results — and which verifications are
   still manual-only, with the exact steps for the owner to run them.
3. Anything you changed about the contracts in "Non-negotiables", or
   "none".
4. Open risks or follow-ups you noticed but did not fix.

## Rejected alternative (do not resurrect without new evidence)

Assembling off-the-shelf engines instead of building this: UFO² as the
desktop engine pointed at a custom model endpoint + a browser-use CLI +
Relay v1 as the fallback. It was weighed on 2026-10-13 and the build was
chosen. The steal list that seeded the work packages above came from
browser-use, UFO², and OmniParser; the packages are the durable form of
that list.
