# R9 Stage 2 — human-like pointer system + idle jiggler (design note)

Wishlist #24, #28, #29, #30, built as ONE system: `hands/motion.py` (pure
planners, seeded-rng deterministic, no input injection) + integration in
`hands/muse_relay_hands.py` (the only place pyautogui is called).

## Flags (constraint d)
| Flag | Default | Env (wins) | Config key (`muse_relay_config.json`) |
|---|---|---|---|
| Human motion | ON | `HANDS_HUMAN_MOTION` | `human_motion` |
| Jiggler | OFF | `HANDS_JIGGLER` | `jiggler_enabled` (also `POST /jiggler {enabled}`; merge-written) |
A request's `"human": false` still forces the legacy path for that act.

## Rule → code
| Rule | Where |
|---|---|
| #29 cubic Bezier, 1–2 random control points | `motion._control_points`, `motion._cubic`, `motion._segment` |
| #29 Fitts velocity (slow start, fast middle by distance, hard stop) | `motion.fitts_duration`, `motion._progress` (min-jerk on a warped clock) |
| #29 wind/Perlin tremor | `motion._ValueNoise`, applied in `_segment`, tapered to 0 at both ends |
| #29 40–120 ms pause on target | `motion.hover_delay` → `hands.click`, `hands.drag` |
| #29 Gaussian landing in target box | `motion.landing_point` ← `/click {w,h}` |
| #29 click down→up 50–150 ms | `motion.click_hold` → `hands.click` (mouseDown / sleep / mouseUp) |
| #29 scroll in chunks with pauses | `motion.plan_scroll` → `hands.scroll` |
| #24 arc + sway, velocity jitter, light overshoot + settle | `motion.plan_move` overshoot branch; per-tick clock jitter in `_segment` |
| #24 per-act randomness, no fixed curve | every parameter drawn per call from the rng |
| #24 budget ≤ +0.5 s per click | `motion.click_budget` / `fit_click_timing` (degrades attention → travel ≥0.12 s → hover → hold) |
| #30.1 attention buffer 200–700 ms by text volume | `motion.attention_delay` ← `/click {attention, text_chars}` (`/move` opt-in) |
| #30.2 idle drift after 30–60 s, 1–3 px / lazy drift | `motion.jiggle_start_after`, `motion.plan_jiggle`, `hands._Jiggler` |
| #30.3 ~15 % structural miss 5–10 px + fast correction | `motion.plan_move` miss branch |
| #30.4 input mutex + 150–300 ms hand travel | `motion.InputMutex` = `hands._INPUT`, held by move/click/drag/scroll/type/key/hotkey/break |
| #30.5 no teleport on context switch | `/focus` never moves the cursor (`_activate_window` has no pointer calls); every human move is a path |
| #30.6 target size sets speed | `fitts_duration(dist, width)`; `/click {w,h}` passes min(w,h) |
| #28 intensity decays with idle | `plan_jiggle`: size ~e^(−t/240 s), wait grows with t; both randomized |
| #28.1 owner input kills instantly, resets idle | `_Jiggler.step`: owner idle < start → end; pointer not where the jiggler left it → end; `_move` checks position after every step and aborts mid-path |
| #28.2 jiggler motion is not owner activity | `motion.SelfInputLedger` (`hands._LEDGER`): spans recorded from GetTickCount BEFORE injecting; `_yield_if_active` uses `owner_idle`. No post-injection GetLastInputInfo probe, so a failed probe cannot strand a stale self baseline |
| #28.3 jiggle paths follow #24 rules | `_Jiggler._move` uses `motion.plan_move` |

## Budget reading (constraint a)
"Current per-click time" = the pre-R9 human click at its fastest:
clamp(0.25 + d/2500, 0.3, 1.1) + 0.05 s hover. New attention + travel +
hover + hold ≤ that + 0.5 s, enforced per click and reported in the
`/click` response (`timing.budget`).

## Scope limits (honest)
- The ledger covers jiggler input only. The hands' own act input is
  not on the ledger (that is the R7.2 type-abort domain; the fix round
  owns it).
- The jiggler resets the OS idle clock, so it keeps the display awake
  and delays lock by inactivity — that is its purpose; `/state`
  `display_asleep` follows the raw OS idle accordingly.
- Feel/realism on the real desktop is unverified here (stubs only).
