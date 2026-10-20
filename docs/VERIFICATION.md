# Manual verification — gateway coordination (wishlist #15, #18)

These steps need the owner's Windows PC (a live hands process and a
real desktop the owner can touch). They are **live-unverified**: the
gateway logic is covered by `services/gateway/test_coordination.py`
with the hands link stubbed, but the end-to-end behavior below has not
been run against the real hands yet.

Setup: start the packaged app (or the services natively, per the
README quickstart) so the gateway answers on port 5010, and note the
gateway token shown in the app window. In PowerShell below, set
`$T = "<gateway token>"` and use header `X-Relay-Token: $T` on every
call (`curl.exe -H "X-Relay-Token: $T" ...`).

## Hands claim (#15)

1. Claim as session A:
   `curl.exe -X POST http://127.0.0.1:5010/v1/hands/claim -H "X-Relay-Token: $T" -H "Content-Type: application/json" -d "{\"holder\":\"session-a\",\"purpose\":\"manual check\"}"`
   Expect `200` with `"granted": true`.
2. Claim as session B (second terminal): same call with
   `"holder":"session-b"`. Expect `409` naming session-a's claim.
   Repeat with `"queue": true` added. Expect `200`, `"queued": true`,
   `"position": 1`.
3. Release as a stranger: `POST /v1/hands/release` with
   `{"holder":"session-c"}`. Expect `403`.
4. Release as session A: `{"holder":"session-a"}`. Expect `200`,
   `"released": true`.
5. Within 30 s, claim as session C. Expect `409` (reserved for the
   queue head, session-b). Then claim as session B. Expect `200`
   granted.
6. `GET http://127.0.0.1:5010/v1/hands/claim` — expect session-b's
   claim, an empty queue, `"reserved_for": null`. Also check
   `GET /v1/info` carries the same object as `"hands_claim"`.
7. Leave the claim alone past its TTL (or claim with
   `"ttl_seconds": 30` and wait ~35 s), then `GET /v1/hands/claim` —
   expect `"claim": null` (lazy expiry; nothing proactively clears it).

## Queued act (#18)

1. While nobody is touching the PC, send
   `POST http://127.0.0.1:5010/v1/act/queued` with
   `{"op":"move","x":100,"y":100}`. Expect a plain `200` hands answer
   (passthrough, no receipt), and `GET /v1/act/queued` shows no new
   receipt.
2. Have the owner actively use the desktop (moving the mouse /
   typing) and immediately send the same queued act with
   `"hold_seconds": 60` added. If the hands yield, expect `202` with a
   receipt `"id"` and `"state": "held"`.
3. Poll `GET http://127.0.0.1:5010/v1/act/queued/<id>`:
   - Owner stops touching the desktop → the retry lands and the
     receipt settles `"state": "applied"` with `"hands_status": 200`.
   - Owner keeps using the desktop past the hold deadline → the
     receipt settles `"state": "refused-yielded"`.
4. `GET /v1/act/queued/<id>` with a made-up id — expect `404` and
   `"state": "expired"`.
5. Sanity: plain `POST /v1/act` with the same body during owner use
   still returns the hands' `409` immediately (unchanged behavior, no
   receipt).

## File-drop, wait-for, lock/sleep state (wishlist #2, #5, #13)

Automated tests (`services/gateway/test_services.py`,
`services/gateway/test_screen_hash.py`, `hands/test_filedrop_state.py`)
cover validation, hashing, chunking, and state machines with the Windows
layer stubbed. The steps below can only be verified live, on the
operator's Windows PC with the packaged app (or the standalone hands)
running and a gateway configured against it. They were **not** run by
the P3 build — no live Windows desktop was available to it.

## File-drop (#2)

1. Configure an allowlist folder on the hands (config key
   `"filedrop_dirs"` or `HANDS_FILEDROP_DIRS`), restart the hands, and
   confirm an unconfigured hands (allowlist removed) answers
   `POST /filedrop/begin` with 501.
2. Through the gateway, `POST /v1/filedrop` a file larger than 256 KB
   into the allowlisted folder; confirm the file appears at the
   returned `path`, its size and SHA-256 match, and it opens intact.
3. Confirm a drop aimed at a folder outside the allowlist is refused
   and writes nothing.

## Wait-for (#5)

1. `screen_hash_change`: start a `/v1/wait`, then change something
   persistent on screen (open a window) and confirm `held: true`
   arrives promptly; repeat with no change and confirm the timeout
   shape after the requested deadline.
2. `screen_region_change`: repeat with a region covering the changed
   area, and with a region that excludes it (must time out).
3. `window_title`: start a wait for a distinctive title fragment,
   open that application, and confirm `held: true`.
4. `parser_model_loaded`: with the parser running but its weights
   absent, start a wait, then make the weights available / load the
   model and confirm the wait resolves `held: true`.

## Lock / sleep state (#13)

1. With the PC unlocked, read the hands' `GET /state` (and the
   gateway's `GET /v1/info` → `pc_state`): expect `"locked": false`
   and an `idle_seconds` near 0 while actively using the PC.
2. Leave the PC idle for a minute and confirm `idle_seconds` grows.
3. Lock the PC (Win+L) and, from another device on the tailnet, read
   `GET /state` again: expect `"locked": true`. Unlock and confirm it
   flips back to `false`.
4. Confirm `/v1/info` reports `"pc_state": null` (not an error) while
   the hands is stopped.
## Live-only verification steps

Steps that cannot be proven by the test suite and need a real Windows
desktop. The unit tests (hands/test_actuation.py,
services/gateway/test_act_ops.py) stub the Windows layer and prove the
logic only.

## P4 — windows / focus (#3)

- `GET /windows` on the real host: titles, process names, pids and
  `bounds` line up with Task Manager and a screen ruler; multi-monitor:
  `monitor` indices match the actual display containing each window's
  centre (verified against Display Settings arrangement).
- `POST /focus`: a Notepad window titled "Untitled - Notepad" focuses on
  a substring match and comes out of minimised state (SW_RESTORE path).
  **Foreground lock:** `SetForegroundWindow` can be refused when the
  hands has no foreground rights; the classic workaround
  (AttachThreadInput) is deliberately out of scope for P4. If focus
  works from a fresh console but stops working after another app takes
  foreground, that workaround is the next ticket.
- `GET /windows` fallback path: on a Windows host *without* pywin32,
  windows still enumerate (process/pid null).

## P4 — drag (#4)

- Drag a file across the desktop / a window across its title bar: the
  release lands on the target (not just the start point); `duration`
  stretches the move for flaky remoting links.

## P4 — clipboard (#6)

- `POST /clipboard/set` then read the value in a native app (e.g.
  Notepad's Paste): unicode round-trips exactly.
- `GET /clipboard/get` reflects a value copied *in* a Windows app
  (Chrome's address bar, Explorer's Rename) — proves the ctypes read
  path against real CF_UNICODETEXT data, not our own writes.
- Every read visibly logs "clipboard read via relay" in the hands app's
  log area.

## P4 — fast type (#9)

- 500+ chars with a clipboard backend: pastes via Ctrl+V in a fraction
  of the keystroke time, and afterwards the *previous* clipboard value
  is back (Ctrl+V in another app yields the old contents, not the
  typed text).
- Paste into a slow target (a terminal): the 0.1 s settle before
  restore is enough that the pasted text lands complete; if a target
  app ever pastes a truncated fragment, lengthen the settle.
- Gateway timeout: a 5,000-char type through `/v1/act` is not cut off
  by the gateway. The sized formula gives 848 s for it, clamped to the
  600 s cap; the paste path returns long before either. Note the cap
  exists: a pure-keystroke type far beyond ~3,500 chars can outrun
  even the sized timeout — that is accepted P4 behaviour, paste is the
  route for very long text.

## P4 — break + hotkey (#19)

- `/break` against a *live* polling foreground process (e.g. a
  `ping -t` in a console, a TUI dashboard): the process actually
  receives the interrupt — the case `/key` with `"ctrl+c"` never
  solved.
- `/hotkey {"keys": ["alt", "f4"]}` closes a window (use a sacrificial
  one).
## Live verification — steps that need the real Windows desktop

The unit tests (`hands/test_capture_realism.py`,
`services/gateway/test_screen_params.py`,
`services/gateway/test_screen_hash.py`) stub the Windows layer and
prove the logic: validation, rect selection, delay/path planning, and
parameter forwarding. The items below cannot be proven that way — they
need the packaged app (or a split deployment) running on the owner's
multi-monitor PC, with the operator watching the screen. None of them
were verified live by the P5 build; each is written so a pass/fail can
be recorded next to it.

Setup for all items: start the relay, note the gateway token from the
app window, and use `http://127.0.0.1:5010` as the gateway base with
header `X-Relay-Token: <token>`.

## Capture

1. **Three-monitor geometry.** On a 3-monitor setup, `GET /v1/monitors`
   returns 3 rectangles whose x/y/w/h match the Windows display
   settings layout (sizes and relative positions), exactly one marked
   `primary`.
   - [ ] pass / fail — notes:
2. **Per-monitor capture.** For each N in 0..2,
   `GET /v1/screen?monitor=N` returns a PNG of only that monitor, and
   the image dimensions equal that monitor's rectangle. Content check:
   put a distinctive window on each monitor first.
   - [ ] pass / fail — notes:
3. **Region across a negative-origin monitor.** With a monitor arranged
   left of the primary (negative x), request
   `GET /v1/screen?region=<x>,0,200,200` with x inside that monitor and
   confirm the PNG shows that monitor's content (not the primary's,
   not black). Repeat with a region that straddles the boundary
   between the two monitors.
   - [ ] pass / fail — notes:
4. **Legacy frame unchanged.** `GET /v1/screen` with no parameters
   returns the full primary display, as before P5.
   - [ ] pass / fail — notes:

## Input realism

5. **Keystroke jitter feel.** Focus a text editor and
   `POST /v1/act {"op": "type", "text": "<a few sentences>"}`.
   The text should arrive character by character at a human-ish,
   uneven pace (short pauses at spaces, longer after periods), and
   the full text should take noticeably less than runaway time on a
   long paragraph (the budget cap). Compare with
   `{"op": "type", "text": "...", "jitter": false}` — that one should
   appear instantly, as before. Watch a site with bot heuristics only
   if the operator chooses to; no claim is made either way.
   - [ ] pass / fail — notes:
6. **Mouse dynamics feel.** `POST /v1/act {"op": "move", "x": ..., "y": ...}`
   across a long distance: the cursor should travel in a slight curve,
   ease in and out, overshoot by a few pixels and settle exactly on
   the target (hover a small button to judge the landing point). A
   human click (`{"op": "click", ...}`) should hover briefly before
   clicking. Compare with `{"human": false}` — an instant straight
   move, as before.
   - [ ] pass / fail — notes:
7. **Failsafe still wins.** During a long human move/type, slam the
   mouse into a screen corner: pyautogui's FAILSAFE must abort the
   action, exactly as before P5.
   - [ ] pass / fail — notes:
## Verification — live-only steps

Automated tests cover the state machines and contracts on any OS
(Windows APIs are stubbed there). The steps below can only be verified
on a real Windows PC with the packaged app, and were **not** run by the
automated tests.

## P6: find-text, autostart + self-heal, elevation bridge

### Run-key autostart on real login

1. Build/run the packaged app, tick **Start on login**.
2. Confirm the value `Muse Relay v2` exists under
   `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` (regedit or
   `reg query`) and points at the app.
3. Sign out and back in: the app window should appear on login.
4. Untick **Start on login**, confirm the value is gone, and confirm a
   fresh login no longer starts the app.

### Self-heal kill drill

1. Start all services from the packaged app.
2. Kill one app-started service's work out from under it (or otherwise
   make it stop answering) and leave it down.
3. Watch the app log across several self-check cycles: after repeated
   failures the log should show
   `self-heal: restarting <name> after repeated failures` and the
   service should come back.
4. Repeat the kill until the restart budget (3) is used: the log should
   then show the giving-up line once, and no further restarts.
5. Separately: start a copy of a service outside the app first (so the
   app reports "already running elsewhere"), make it fail, and confirm
   the app never restarts it.

### Elevation end-to-end (operator click + UAC)

1. Add an entry to the hands config file's `elevate_allowlist`
   (a harmless program first), start the packaged app.
2. Send `POST /v1/elevate {"name": "<entry name>"}` with the gateway
   token. Confirm a modal **Elevation request** dialog appears in the
   app window naming the request and the exact configured exe/args.
3. Click **No** (Deny): nothing must launch, and
   `GET /v1/elevate/<id>` should report `denied`.
4. Send the request again and click **Yes** (Approve): the Windows UAC
   prompt should appear; confirming it should launch the program
   elevated, and the status should report `launched`. Cancelling UAC
   should report `launch_failed`.
5. Send a request and leave the dialog unanswered past the app's
   handling, then check that an unanswered pending request older than
   120 s reports `expired` and cannot be approved afterwards.
6. Confirm there is no way to launch anything whose name is not in the
   allowlist (unknown name → 404) and that removing the allowlist
   returns 501.


## Integration notes (coordinator, V3 merge of P2–P6)

The five package branches were built in parallel against the same base
and merged in order P2 -> P3 -> P4 -> P5 -> P6. Decisions taken at the
merge, all behavior-level, each covered by the combined test suite:

- **One /type handler (P4 x P5):** the route now unions both packages —
  method auto/paste/keys with clipboard save/restore and keys fallback
  (P4), and the keystroke path applies _plan_key_delays jitter unless
  jitter=false (P5). Response carries both packages' fields
  (method_used/chars/elapsed_seconds + delays_planned/planned_seconds).
  Two P4 test assertions were adjusted to the merged semantics: the
  legacy single-write call shape became per-char writes, `names() ==
  ["write"]` became `set(names()) == {"write"}`, and the test stubs
  time.sleep so 200-char keystroke cases do not take ~20 s each.
- **One _monitor_rects (P4 x P5):** P5's dict shape
  ({"x","y","w","h","primary"}, pyautogui.size() fallback) is the single
  implementation; P4's duplicate tuple version was removed and
  _monitor_for_bounds now reads the dict shape.
- **One forwarding path (P2 x P4):** _forward_act uses
  HANDS_OP_PATHS and the payload-sized _act_timeout, so plain acts and
  queued-act retries share identical routing and timeouts.
- **/v1/monitors (P5)** is served through _proxy_hands_get (P4) instead
  of a hand-rolled passthrough — same statuses, one code path.
- **_reachability (P2 x P3):** returns (hands, parser, pc_state);
  test_coordination's stub was updated to the 3-tuple.
- A cherry-pick seam that separated _fetch_screenshot's signature from
  its body was repaired; py_compile + the full suite verify the result.

## R7.2 fix round — live receipts owed (#26, #27)

1. Clipboard: on the PC, `set RELAY_LIVE_CLIPBOARD=1` then
   `python -m pytest -q tests/test_windows_clipboard_real.py` → 1 passed;
   your clipboard text is unchanged afterwards.
2. /type paste path: focus Notepad, queued `type` of a 200-char text
   (auto → paste): the full text appears; your previous clipboard is back.
3. Hooks: queued `type` of the 40-char Spotify URL with hands off →
   completes, `owner_guard: "hook"` (not a char-12 abort).
4. Press a key while a 40-char type runs → 409 `abort_reason: owner` at
   the next 12-char boundary; nothing typed after it.
5. Win+L during a long type → 409 `abort_reason: locked` at the next
   boundary; after unlock no further characters appear.
6. Repeat 3 with an elevated window (e.g. admin PowerShell) focused and
   note `owner_guard`.
