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

