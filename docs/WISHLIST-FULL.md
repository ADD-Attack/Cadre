# Hands & Eyes — running wishlist

**Edition v7 — 2026-10-19** — 19 wishes (Hands 1–9, Eyes 10–14,
Coordination 15, Input realism 16–17, Reliability 18–19).

**Status 2026-10-19: the whole list is now implemented on branch `v3`
of muse-relay-v2** (canonical repo; HEAD a8c12ff incl. V3-R1 + V3-R2,
PUSHED to ADD-Attack/Cadre refs/heads/v3, verified 16:17 CDT).
#1 done 2026-10-17; #14 in f40dc5a; the rest in V3-P2..P6 commits
(95f99f6, e765781, 9a6caea, ab67c18, 192d8c3 + integration commits),
plus V3-R1 (ebe2806): fixes from a Grok 4.7 x-high review of the tree
(16 findings, 0 critical; 4 of 6 Highs fixed, incl. the parser's
0.0.0.0 bind and a queued-act eviction bug that could fire an op with
an empty body; full text in ~/workspace/relay-v3-grok-review/).
Full suite: 15 test files, 273 checks, ALL PASS (independently
re-run on the integrated tree; py_compile clean). Everything
Windows-live (real desktop actuation, UAC prompt, multi-monitor
geometry, lock detection, OmniParser weights) is stub-tested only —
exact manual verification steps live in the repo's
docs/VERIFICATION.md. Live verification awaits an app rebuild +
a hands session on Abraham.
Also 2026-10-19: Forge's `wishlist-build-20261019` line is superseded
by this v3 pick (the Forge one-shot stalled mid-item-14; the v3 branch
above is the implementation of record), and the phase-1 landing cron
has been cancelled — no landing/phase-1 job exists in the scheduler
(verified 2026-10-19 14:08 CDT autonomy scan, cron.list).

Capabilities Muse wants added to Muse Relay v2 (hands = actuation via the
gateway, eyes = screenshot/parser). Muse adds an entry whenever real work hits
a limitation, with the date and the incident that motivated it. Christopher
reviews and picks; nothing here is a promise or a schedule.

## Hands (actuation)

1. **Persistent gateway token** — DONE 2026-10-17 (patch: token load-or-create
   at `~/.muse-relay-v2/gateway-token.txt`, mirroring the hands secret).
   Motivated by: the per-launch token locked the agent out after any
   relaunch, breaking "hands stay up the entire time I'm at work."
2. **File-drop op** — gateway op to write a small file (agent → a named PC
   folder), chunked + hash-verified. Motivated by 2026-10-17: delivering a
   5.8 KB patch to Abraham needed a whole fleet order to Michael; the gateway
   itself could have carried it.
3. **Window inventory + focus op** — list open windows (title, process,
   bounds, monitor) and raise/focus one by title. Motivated by the standing
   lesson "no assumption-based desktop driving": today I navigate by
   coordinates and screenshots; a window list replaces blind taskbar clicks.
4. **Drag op** — press-move-release as one op (sliders, window moves, text
   selection, drawing). Current ops (move/click/type/key/scroll/hotkey)
   can't do it.
5. **Wait-for op** — block until a condition holds (window title appears,
   process exits, screen region changes), with timeout. Replaces
   screenshot-polling loops when launching apps or waiting on builds.
6. **Clipboard ops** — set clipboard text (long URLs/text instead of typing)
   and read clipboard (Christopher copies something on the PC, agent picks it
   up without chat). Read side is sensitive — same trust level as other ops.
7. **Autostart + self-heal** — option to start the relay app on Windows
   login, plus a small supervisor that relaunches it if the gateway health
   check fails. Token persistence (item 1) is what makes a relaunch
   recoverable while Christopher is at work.
8. **Elevation bridge** — a way to ask the person at the PC for one UAC
   approval for a named command (firewall edits etc. need an elevated
   shell; today those steps are Christopher's hands or nothing).
9. **Fast text injection + a type timeout that fits it** — the type op
   injects ~6 chars/sec and the gateway's 30s hands timeout kills a long
   type mid-string with the tail silently missing. Motivated by
   2026-10-17: installing Blender on Abraham meant chunking one
   PowerShell line into ~100-char pieces with a screenshot check between
   chunks. Want: clipboard-speed injection (ties to item 6) or an act
   timeout sized to the payload.
   Addendum 2026-10-17 afternoon (Christopher's catch): two 480p preview
   renders each cost ~4 minutes of chunk-typing for a ~1,150-char Blender
   command — his question: "why don't you send txt files to copy paste or
   bat files?" Workaround adopted same day: scripts ship as ONE
   remote-storage zip (the hunyuan-bootstrap route) and Abraham pulls
   them with a single short typed Invoke-WebRequest line (~20 s of typing
   regardless of script size). A relay file-drop / clipboard-set op
   would retire the workaround entirely.

## Eyes (perception)

10. **All-monitors capture** — Abraham has 3 monitors; screenshots return one
   1920×1080 screen. Want: per-monitor capture or a stitched all-screens
   image, plus which monitor a window lives on.
11. **Region capture at native resolution** — `/v1/screen?region=x,y,w,h`
    so small text (dialogs, token fields, error lines) is readable without
    a full-screen downscale.
12. **Find-text op (parser)** — give the parser a string, get back screen
    coordinates of its occurrences ("the Create API key button"), so
    driving is anchored to labels instead of guessed pixels.
13. **Lock/sleep state in `/v1/info`** — report whether the PC is locked or
    the display is asleep, so the agent knows actions won't land before
    trying them.
14. **Conditional hash endpoint** — IMPLEMENTED 2026-10-19 on the local
    `v3` branch of muse-relay-v2 (commit f40dc5a, not yet pushed):
    `GET /v1/screen/hash` with `mask_bottom` + `stable=1` (two samples
    ~0.65 s apart, per-pixel minimum — phase-independent), and an ETag /
    If-None-Match 304 on `/v1/screen`. 11 synthetic tests pass; live
    verification against the real hands awaits an app rebuild.
    Original wish: `GET /v1/screen/hash` returning the
    SHA-256 of the taskbar-masked frame (or If-None-Match semantics on
    `/v1/screen`), so a watcher can poll a tiny hash at ~5 Hz and fetch
    the full PNG only when the hash changes. Motivated by 2026-10-18:
    an independent speed review of the live walkthrough loop measured
    detection at ~3 s of an 8–14 s step cycle, floored by 1 Hz full-PNG
    polls through the tunnel (~0.85 s per 1920×1080 frame); a hash
    endpoint cuts detection to ~1 s (~2 s/step saved) and nearly
    eliminates all-day polling traffic. Christopher's note the same
    evening: once this ships, the watcher-side persistent-connection
    speedup (keep-alive polls instead of a fresh tunnel per fetch) is
    redundant — the endpoint supersedes it.
  Addendum 2026-10-19 (live Grok wiring walk): even client-side hashing
  false-fires — the watcher reported CHANGED repeatedly on byte-identical
  full frames during the walk; the real pixel churn is the terminal's
  blinking caret, which sits ABOVE the bottom-80px taskbar mask whenever
  a terminal is full-screen. The endpoint should offer a
  blink-insensitive mode (e.g. hash two frames ~600 ms apart and report
  the stable hash, or mask small high-frequency regions) so "changed"
  means content changed, not "the caret blinked."
- 2026-10-17: No way to pull a window onto monitor 1. Explorer kept restoring on another monitor while opening Michael's workspace folder for Christopher; hands captures monitor 1 only, the act API has no hotkey/combo op (single-key press only, no Win+Shift+Arrow) and no window-list/move op. Wished: an op to list windows with their monitor, and move/foreground a window onto the captured display.

## Coordination

15. **Hands claim flag + queue** — a gateway-visible claim record (who holds
    hands, for what job, since when) that a session sets on claim, clears on
    release, and every session reads before driving; plus a simple queue so a
    second session's bounded job can wait its turn instead of colliding.
    Motivated by 2026-10-19: three Muse chats (main, Forge chat, Tech help 2)
    all had business on the one desktop in the same morning — main on the
    wishlist, Forge chat wanting a bounded app-server restart, Tech help 2
    waiting on the PC for a Grok Bot install — and the only arbiter was
    Christopher relaying between chats. Relay v2 has no lock: two drivers at
    once would interleave clicks into garbage. NOT item 13 — item 13 reports
    the PC's lock/sleep state; this is about which *session* holds the hands.

## Input realism (Hands)

16. **Realistic keystroke jitter (type op)** — human-like timing instead of
    the type op's uniform machine cadence: randomized per-key delays in a
    human band (roughly 40–160 ms), slightly longer pauses at word and
    sentence boundaries, natural rhythm variation across the payload. Keep
    the payload's total time bounded and reported, like item 9's fast-type
    work. Motivated by 2026-10-19 (Christopher's direction): main typed a
    ~700-char prompt into Gemini at a perfectly even ~6 chars/sec; Gemini's
    generation died and the tab reset to an empty chat before any answer
    rendered. Christopher's hypothesis: the non-human input signature got
    the session flagged. Cause unverified — but the cadence is objectively
    machine-like, and any site running bot heuristics will read it the
    same way.
17. **Realistic mouse movement (move/click ops)** — human pointer dynamics
    instead of instant teleports and straight constant-speed lines: eased
    acceleration and deceleration, a slight curve to the path, small
    overshoot-and-settle on the target, a brief hover before the click
    lands. Motivated by 2026-10-19 (Christopher's direction), same
    incident as item 16: every pointer move in the Gemini session was a
    teleport. Pairs with 16 — input realism is one signature, not two.

## Reliability (actuation truthfulness)

18. **Yielded-input accounting** — when the takeover interlock yields,
    act calls are refused (409) and the input is simply LOST; in a
    multi-op sequence (click, then type) the caller gets per-call
    receipts but no way to make the sequence atomic or replayable, and
    a type refused mid-plan leaves the driver unsure what state the
    screen is in. Want: an optional queued act form — ops submitted
    while yielded are held (bounded, e.g. 30 s) and executed in order
    once control returns, with one receipt per op saying
    applied / refused-yielded / expired — or at minimum a single
    "sequence id" so a driver can ask "did step N land?" Motivated by
    2026-10-19 10:47: mid-wiring, Christopher touched his own mouse; my
    click+type for the corrected OAuth command returned yielded and
    vanished; the run only recovered because the error text was read
    carefully and the step re-issued by hand.
19. **A reliable break for foreground TUIs** — driving a terminal that
    is running a full-screen/polling TUI (the OpenClaw CLI's OAuth
    wait), the key op's ctrl+c did not interrupt the process and a
    ctrl+shift+t chord did not open a new Windows Terminal tab; the
    only exit was waiting out the flow's own 30-minute timeout.
    Whether the gap is chord encoding in the key op or TUI signal
    handling, a driver needs one verified way to break a foreground
    process (a dedicated break op, or chords proven against Windows
    Terminal + a polling Node TUI). Motivated by 2026-10-19
    11:17–11:20, the expired-device-code recovery.
20. **Foreground re-verification for held acts** — a queued act held by
    the yield fires into whatever window is foreground when the yield
    clears, with no memory of where it was aimed. Motivated by
    2026-10-19 16:55 CDT: a queued Reset click, held ~30 s while
    Christopher worked in another window, applied into the Muse chat
    window's approvals sidebar instead of the chess page it targeted
    (harmless landing, wrong window). Want: capture the foreground
    window identity at submit; at apply time, if the foreground has
    changed, refuse (or hold for the target window) instead of firing
    blind.
21. **Uniform act accounting — a receipt for every act** —
    `POST /v1/act/queued` returns a receipt id only when the first
    attempt yields; a direct apply returns a plain 200 with no id, so
    a driver has no single place to ask "did it land?" Motivated by
    2026-10-19 17:01–17:04 CDT: a driver polling for a receipt that
    was never created sat blind ~3 minutes while both its clicks had
    already applied. Want: every queued submission returns an id and
    leaves a terminal record (applied-direct / applied-after-hold /
    refused-yielded / failed) under the same query path.
22. **Auditable empty reads** — gateway GETs through the tailnet proxy
    intermittently return empty bodies with a success status (receipt
    polls and /v1/info, 2026-10-19 live test), and a driver cannot
    distinguish "empty but valid" from a torn response. Origin
    unverified (gateway vs proxy). Want: the gateway response path
    audited for empty-body paths, and a response-integrity marker
    (strict content-length, or a checksum header) so torn reads are
    detectable as torn.
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
25. **Opus GUI pass for the relay** — Christopher's direction 2026-10-19
    19:14: the R6 build includes the interface's FIRST revision by Muse
    (item 23), and the full Opus-grade ("bad ass, super AAA") GUI pass
    STAYS on this wishlist as its own item for later — not part of the
    R6 build. Pick it up when Christopher calls for it.

## #26 — clipboard_set crashes on the PC build (found 2026-10-19, Spotify tab task)
POST /v1/act/queued {"op":"clipboard_set","text":"https://www.spotify.com/account/privacy/"} returned ok:false with "clipboard set failed: 'c_wchar_Array_41' object has no attribute 'size'" — the hands clipboard write path (pywin32) is broken for this input; the clipboard was never set (a following ctrl+v pasted nothing). Blocks the safe URL-delivery pattern (paste full text instead of typing).

## #27 — type op false-abort + queued acts scatter across foreground windows (found 2026-10-19)
(a) Queued type of a 40-char URL aborted at exactly char 12 twice in one night ("owner became active — typing aborted"), elapsed ~1.4 s both times — deterministic, and the owner was verifiably hands-off (phone photos, idle >90 s). The F7p1 abort re-check appears to trip on the type's own injected keystrokes ~1.3–1.5 s in. (b) Worse: a queued multi-act sequence (ctrl+l, then type) fired its acts into DIFFERENT foreground windows seconds apart — ctrl+l in the Spotify window, the type's 12 chars into a New Tab in the chat window on another part of the desktop. Queued sequences need foreground pinning (F3 expect_focus on every act of a sequence, aborting the rest on mismatch) before they are safe for multi-step browser work. Receipt ids: type aborts ed6d09e6 (hold 30) and 6d750dbf (hold 60); clipboard fail 16d643eb.

## #28 — Realistic mouse jiggler, intensity decays with idle length (Christopher's direction 2026-10-20 00:15)
A relay-side mouse jiggler that moves the pointer in small, human-like motions while the PC is unattended, with intensity that DECREASES the longer the idle lasts: more frequent and larger movements in the first minutes of idle, tapering to rare micro-movements after long idle (a person settles over time; a constant-rate jiggler is itself a robotic signature). Hard constraints: (1) real owner input kills it instantly and resets the idle clock — it never fights the owner; (2) its own injected motion must NOT register as owner activity in the yield/idle probe (WP0b) — the probe has to distinguish jiggler motion from owner motion, or queued acts will start yielding against the jiggler itself; (3) movement paths follow item 24's human-like rules (arc, sway, velocity jitter, light overshoot + settle), randomized per movement, never a fixed pattern.

## #29 — Movement-realism implementation reference (Gemini notes, via Christopher 2026-10-20 05:13)
Christopher pasted a Gemini write-up on human-like cursor movement into the main chat as reference for this list. Full text saved at ~/workspace/hands-eyes-gemini-mouse-realism-20261020.md. It governs the implementation of #24 (pointer motion) and #28 (jiggler motion). What it adds beyond #24's existing spec: cubic Bezier paths with 1–2 randomized control points; a Fitts's Law velocity profile (slow start, fast middle scaled by distance, hard deceleration into the target); Perlin/wind noise injected along the path; a 40–120 ms pause on target before the click fires; landing points Gaussian-distributed inside the target's bounding box (center-weighted, occasional edge hits) instead of always dead-center; click down/up duration randomized 50–150 ms; scrolling in variable chunks with pauses instead of a single jump.

## #30 — Behavioral layer for pointer work (Gemini notes #2, via Christopher 2026-10-20 05:18)
Second Gemini reference: where #29 covers per-path coordinate physics, this covers the session life-cycle that behavioral scorers actually grade. Full text at ~/workspace/hands-eyes-gemini-mouse-behavior-20261020.md. Rules: (1) attention buffer — 200–700 ms context-aware hesitation before moving toward a newly rendered target, scaling with on-screen text volume; (2) idle drift — after 30–60 s without action, 1–3 px organic jitters or lazy drifts (this is the behavioral core of the #28 jiggler — the two items should be built as one system); (3) structural overshoot error rate — ~15% of approaches miss the box by 5–10 px and correct with a fast secondary curve (beyond #24/#29's path-level overshoot); (4) input mutex — never mouse + keys simultaneously; 150–300 ms hand-travel delay between keyboard and mouse actions; (5) context-switch physics — cursor never teleports on tab/window switches; it stays put or exits/re-enters at a screen edge; (6) Fitts extension — target SIZE dictates the speed profile, tiny targets get a slower, longer settle. Context answers noted for the builder: this relay drives ONE owner session on one PC (Abraham) — no multi-profile orchestration; keyboard typing profiles ARE in scope alongside mouse (the type op; see #27) — a dedicated typing-profile entry may be worth splitting out when this gets built.

## Resolution note — #23/#25 GUI route DECIDED (2026-10-20 05:23 CDT)
Christopher asked whether the relay app could get a GUI that "doesn't look like it's VBA" — the current window is Tkinter, and Tk's Windows widgets are that era's look. He picked the recommended route: a LOCAL WEB UI in an app window (locally served HTML/CSS/JS dashboard in a native window shell, pywebview-style), over PySide6/Qt and over a CustomTkinter reskin. This supersedes #23's earlier builder pin (Muse first build / Opus refinement): under his 2026-10-20 direction, ASTRA implements the GUI as Stage 3 of the R9 round (dashboard scope per #23), and because Astra is this round's builder, the independent pre-deploy review goes to a fresh Opus session. Stage order: R7.2 fix round → R9 motion/jiggler → R9 web GUI (deadline 2026-10-21 17:00 CDT).
