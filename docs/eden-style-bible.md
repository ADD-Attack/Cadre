# DIRECT STRIKE — STYLE BIBLE (the "look handbook")

_Status: LIVE direction (locked by Brick 2026-09-08). Direction: **COLORFUL / WARM** — board
`ds-direction-colorful-warm` (reference image in agency media dir). This is the durable spec every
screen + every future visual change diffs against. If a change would create a NEW look direction not
covered here, STOP → generate + show + let Brick lock it FIRST (per "show before build" habit rule).
Existing AUTONOMY.md governs how I act; this file governs how the GAME LOOKS.

**SCOPE — THIS IS THE COMPREHENSIVE HANDBOOK FOR THE WHOLE GAME LOOK.** It is NOT just the battlefield
backdrop. It covers EVERYTHING visual: battlefield field + sky, the SHOP/unit-card panel, unit & core
sprite art, resource nodes, menus + start screen, reward/upgrade screens, deck/relic screens, end/
victory screens, FX/glows — every screen and every visual change diffs against THIS file. The backdrop
rules are one section of it, not the whole. If a screen or art type has no rules yet below, that is a
GAP (generate GUI/art references → show Brick → lock → fill this file) — do not silently ship an
unguided look for any screen.

**⚠️ STYLE ONLY, NOT FEATURES (Brick 22:58).** The boards in this bible describe how a screen LOOKS —
backdrop/art/glass/typo/spacing/color/motion. They do NOT dictate feature or logic changes, and they do
NOT justify changing gameplay when it wouldn't make sense. Diff/fix passes (A6/A7) match a screen's
VISUAL/aesthetic presentation to its board; they never re-scope or regress units, economy, roles, flow,
map, or systems to fit a picture. If a board implies a feature that shouldn't exist or clashes with real
logic, keep the feature intact and approximate the look with unlocked/available art.

**📐 THE ACCEPTANCE TEST — THIS FILE MUST DICTATE A WHOLE SCREENSHOT.** The bible is only"done" when,
given THIS file + the name of any one screen, you can reconstruct what the ENTIRE rendered screenshot
of that screen looks like — not just its palette chips. That means for every screen it must pin down:
(1) the exact layout/zones of that screen and how elements are arranged on it; (2) the palette for the
screen's panels, borders, text, cards and its backdrop if it has one; (3) per-element styling (buttons,
cards, bars, frames, health bars, icons) incl. hover/disabled/selected states; (4) how the UI layer sits
against whatever is behind it (per Design Law #1) — i.e. UI cutting through, vs a menu standing alone;
and (5) any unit/core/backdrop art that appears in that frame. A re-skin of a screen is only approved
when the bible rules for that screen are complete enough to predict that full frame, and the rendered
result matches the prediction when verified live. If the bible cannot yet dictate the whole shot for a
screen, that screen is marked PENDING + a GAP below and stays that way until locked.

---

## THE ONE-SENTENCE VIBE
High-energy, saturated, clearly faction-coded sci-fi: **teal-vs-ember** war on a vivid battlefield,
viewed through a **rich deep-indigo UI** that is unmistakably distinct from the field. NOT grey, NOT
washed out, NOT one flat dark wash everywhere. Every screen should feel alive and designed.

## DESIGN LAW #1 — THE UI VERSUS THE FIELD *MUST* DIFFER
Brick's core complaint was screens all blending into one boring dark-blue/grey wash. So:
- **Battlefield = "dirty" saturation** — ground/sky mixed toward browns/greys + smoke/dust haze,
  bottom-lit / back-lit by the contested center glow.
- **Shop/UI panels + menus = "pure" saturation + glass-on-screen** — high-chroma, NO atmospheric haze,
  100% OPAQUE panel backgrounds so UI visually CUTS THROUGH the battlefield haze and never flattens
  into it. Top-down lighting: 1px top-edge highlight on panels, 2px bottom inner shadow.

## LOCKED HEX PALETTE (from Brick-approved board)
### Faction & combat accents
- Ally/Human TEAL: base `#18B5B5` · highlight `#8EFFFF` (projectiles, high-energy) · shadow `#0E6666`
- Enemy/Alien EMBER-RED: base `#FF3B3B` · orange `#FF8A00` (sub-accent/eyes) · deep blood `#6A0D0D`
- Contested-center glow: core `#FFFFFF` · inner `#FFF79A` · outer `#FFD700` (gold/fire halo)

### Environment — battle sky backdrop
- Top dark `#140B1F` → mid teal haze `#2D4F5A` → horizon dusty magenta `#6D2C4E`

### Environment — battlefield ground
- Ally side cool: `#153C44` → `#246D7D`
- Enemy side warm: `#631522` → `#A22E3C`
- Craters/impact pits: `#0C0C0C`

### UI / shop / panels  (COLOR-SYSTEM AUDIT PASS 2026-09-08 20:22 — separation enforced)
Brick: "UI system colors are way too similar / don't match the ui bible [shop board]." Board audit found these REAL
collisions — each role color below is now forced to a SEPARATE luminance/hue window so no two mental models bleed together:

**SURFACE LADDER (dark→light→dark “booth/well” rhythm — fixed from Brick 20:32 “all too close”):**
The board layers by ALTERNATING fill values, not by hairline steps. Copy that: same-family hues but REAL value jumps.
- Panel base `#0B0B2E` (deep midnight indigo, subtle darker-at-bottom gradient) — the LOWEST/OUTER layer.
- Card fill `#23234F` (NOT `#16163F` — that still sat in the same near-black band as the panel). Card body is a plainly
  LIGHTER indigo-grey so it reads as a raised slab over the panel even with borders muted (dark→light step).
- Recessed lip: a THIN darker inner stroke (`#0B0F2F`-ish) just inside the glowing border before the card fill = a subtle
  “groove” that detaches the fill from the border (per board).
- Sprite inset / unit well `#05051A` (near-black navy) — the DEEPEST layer again (light→dark step back in): the character
  looks like it stands in a dark booth window behind the card surface.
- Panel edge / inner-glow `#2D2D7F`-family — thin bright-indigo line lifting the whole panel.
  RULE: the THREE key tones (panel / card / well) should read at a glance as distinct bands — panel deep navy → card
  clearly-lighter indigo-grey → well near-black. If they blur, it's WRONG (Brick 20:32). Lighten card or darken well until the
  dark→light→dark rhythm is unmistakable even at a distance with borders off.

**CARD BORDER LADDER (rarity must NOT reuse the currency color):**
- Ally border `#1CC7C7` TEAL — only for ally identity/card frame + Deploy action.
- Enemy border `#FF4A4A` · rare/magic `#E026FF` (keep; see magenta-vs-gas guard below).
- RULE: borders never equal the currency or stat-fill colors.

**CURRENCY / ECONOMIC (must NOT collide with identity teal or stat yellow):**
- Mineral diamond `◆` = ICE-BLUE `#A0EFFF` (NOT the teal `#1CC7C7`/`#00FFD8` — audit's #1 collision: currency, unit
  border and Deploy were all the same teal → "teal wash"; cost and identity were inseparable).
- Gas icon `◈` = ember red-orange `#FF7A1A` family (NOT violet, NOT magenta — must not sit near the rare-magenta peak).

**STAT vs TAG vs CURRENCY hud (data hierarchy):**
- Stat bars `#FFCC00` bright yellow — values only.
- Role tag (RANGED etc) = a SEPARATE cool grey-ink outline `#9FB4C7`, NOT yellow (was identical `#FFD700` to the
  stat bars → "sea of yellow"; tag is a category, bars are a measure).
- Gold-luxury accent `#FFD324` — reserved for RARE/luxury reward framing ONLY, never a body stat fill.
  RULE: yellow(measure) ≠ gold(luxury) ≠ tag(cool-grey outline) ≠ currency(ice-blue diamond / ember gas).

**READABILITY / ACCESSIBILITY (locked/collapsed states must stay legible):**
- Disabled / unaffordable card fill `#3E3E6A`, but its text/lock icon LIGHT `#C7C7E0` (audit: RECRUIT-lock text was
  ~same luminosity as panel → invisible on dark monitors). NO pure-`#000` text on any dark panel.

**MAGENTA-VS-GAS guard:** rare-magenta `#E026FF` (Shock frames) vs the ember gas `◈` now sit at opposite ends
(magenta high-blue-violet / gas warm-orange) — never let a purple into the gas slot.

### Secondary system accents
- Gold-LUXURY `#FFD324` · magenta/rare `#FF00FF` (Shock/magic frames) · green/exp `#00FF66` (XP/scout lens)
- Mineral diamond `◆` ice-blue `#A0EFFF` · gas `◈` ember `#FF7A1A` · primary labels `#FFFFFF`
- Stat values `#FFCC00` · role tags cool-grey `#9FB4C7` · disabled fill `#3E3E6A` + light text `#C7C7E0`

## LOCKED TYPOGRAPHY — the type system (added 2026-09-12; **REVISED 2026-09-12 by Brick, ×2**)
**GAP FILLED, THEN RE-LOCKED, THEN SOURCING UNLOCKED.** The first pass codified whatever the live build
happened to ship (`'Segoe UI'`) and banned custom faces. **Brick overruled that the same day: "We will make our
own font and also have a title png. Fuck boring text."** Then, 2026-09-12 17:53, **Brick lifted the source
restriction: "Get rid of that typeface restriction in the style bible."** The lock is now about the *result*
(match this bible, ship offline), **not** about who drew the glyphs.

**THE FACE — matching this bible, offline-baked. Source is OPEN.**
- **Title / wordmark = an IMAGE (`title.png`).** Drawn art, not typeset text — any lettering we want. Baked into
  the bundle. (Build task: SCRUM R8.)
- **UI text = a real embedded face, baked into the one-file bundle** (embedded TTF/OTF, or a bitmap glyph
  atlas). A fixed asset, not a download.
- **Where the face comes from is no longer restricted.** Either is allowed: **(a) ship an open-licensed face
  as-is** (SIL OFL 1.1 / CC0 / public domain), or **(b) use one as a base and draw our own glyphs on it.**
  Hand-drawing every glyph from scratch is NOT required. _Rationale: our fully hand-drawn face failed twice_
  _(`D`≈`O`≈`0` in `1bf2ae4`, then the `R`)._
- **License duty (the only sourcing rule left):** verify the license AT THE SOURCE, confirm it permits
  commercial use + embedding + modification, and **ship the license text with the bundle**. Avoid "free font"
  sites with no clear license; **CC-BY is discouraged for fonts** (attribution-in-a-binary is awkward). A
  modified OFL derivative must **not** use the original's Reserved Font Name.
- **Still banned at runtime: third-party webfonts / CDN font links / any network font fetch.** The rule that
  SURVIVES is the *offline* one — zero network, zero FOUT. **Baking a licensed font FILE into our bundle does
  NOT violate this; fetching one at runtime does.**
- Two faces are allowed: a **display** face (titles/hero) + a **UI** face (labels/body).
- Fallback stack in CSS is last-resort only, if our face ever fails to load: `system-ui, sans-serif`.

**THE ADOPTED FACE — `Saira Condensed`, SIL OFL 1.1, shipped AS-IS (DECIDED 2026-09-12 18:35, Brick).**
- **UI face = Saira Condensed, unmodified: no rename, no redraw.** Shipping it as-is is what keeps the Reserved
  Font Name "Saira" legal — a *modified* OFL derivative would be the only case required to drop that name.
- **Weights present: `400` Regular · `600` SemiBold · `700` Bold · `800` ExtraBold · `900` Black.** This is the
  face that finally satisfies the WEIGHT LADDER below; the retired hand-drawn face had a single master and
  structurally could not.
- **Files:** `rogueds/fonts/sairacondensed/{SairaCondensed-Regular,SemiBold,Bold,ExtraBold,Black}.ttf` + `OFL.txt`.
  License verified at the origin: upstream `google/fonts`, directory `ofl/sairacondensed`
  (Copyright 2016 The Saira Project Authors). OFL 1.1 permits commercial use, embedding, and modification.
- **`OFL.txt` MUST ship inside any bundle that embeds the face.**
- **RETIRED:** our hand-drawn `DirectStrikeUI.ttf` + its generator `build_face.py` + its specimen set
  (commit `84dd0a1`). Recorded reason: the face failed twice — `D`≈`O`≈`0`, then the `R` — because glyphs were
  being assembled from rectangles/polygons instead of drawn outlines. Superseded, not destroyed: recoverable at
  `.trash/ai-face-2026-09-12/`.
- ⚠️ **GAP: the display/slant requirement is NOT yet met.** The weights we shipped are the uprights; Saira
  Condensed keeps its Italics in the upstream `SairaCondensed-Italic*` files we did **not** take. Until we add
  them (or slant deliberately), any *slanted* title is a skew, not the real italic — decide once, on the record.
- ✅ **WIRED AND LIVE (R12, 2026-09-12 18:50).** The face is in the real build, not just on a board.
  `tools/gen_font_data.mjs` base64s all 5 weights (binds each via OS/2 `usWeightClass`, inlines `OFL.txt`);
  `build.mjs` emits the **whole 5-rule `@font-face` block** (the old single `__FONT_DATA_URI__` slot could not
  carry a ladder); `shell.html` declares 400/600/700/800/900, re-points `--ui-font`, and adds
  `button,input,select,textarea{font-family:inherit}`; `src/mapui.mjs` re-pointed. Commits `661d264` / `7bbebb8`,
  deploy clone `58fac5b`; proof harness `tools/probe-font.mjs`. Live at
  `https://add-attack.github.io/direct-strike/` — md5 `b778430e5628f37c3fb765cbaafe8d5e`, local build == served
  bytes (verified independently of the do-er's report).
- ⚠️ **TWO TRAPS THIS WIRING EXPOSED — do not reintroduce either:**
  **(1) The `OFL.txt` text must ship from `<head>`, NEVER inside `<style>`.** Its body contains bare `--` and `<`
  sequences ("Version 1.1 - 26 February 2007") that abort CSS parsing from that point on — `:root` and `body`
  die and the entire UI silently falls back to Times New Roman **while the font still reports as loaded**. A
  font-probe alone will NOT catch this; only the screenshot will.
  **(2) `<button>` does NOT inherit `font-family`.** Without the explicit inherit rule every menu button renders
  in the fallback face even though the `@font-face` is perfectly valid.
- ⚠️ **STILL OPEN — the wordmark generator.** `fonts/eden_wordmark.py` (R8 `title.png` lane) still reads the
  deleted `fonts/DirectStrikeUI.ttf`. The UI face is wired; the wordmark path is not. Re-point it to a real face
  or keep the wordmark as drawn art — and settle the italic question above in the same pass.
- **Bundle cost, expected and accepted:** 5 real weights moved the deployed file **~9.34 MB → ~9.98 MB**
  (~626 KB of base64 replacing the old single ~95 KB master). That is the price of a real weight ladder.

**STYLE OF THE FACE — must match the LOCKED `menu-board.jpg`.**
- Display/title: heavy, **condensed, slanted (italic), ALL-CAPS** — hard angular arcade-poster letterforms.
- UI labels/buttons: **blocky condensed military caps**, tight spacing, squared terminals.
- Body/meta: same family language, no ornament.

**WEIGHT LADDER (of the SHIPPED face) — heavy by design; this is a loud arcade UI, not editorial.**
- `900` — hero numerals + the largest titles ONLY (victory/run-end scale).
- `800` — **the workhorse**: all UI labels, buttons, chips, panel headers, most screen titles.
- `700` — secondary labels, sub-headers.
- `600` — body / support copy.
- `400` — raw prose only. **Never** on a button, label, chip, or heading.
- RULE: nothing a user *operates* sits below 600. Nothing below display scale gets 900.

**SIZE LADDER — the only allowed px values:**
`9 · 10 · 10.5 · 11 · 11.5 · 12 · 12.5 · 13 · 14 · 15 · 16 · 18 · 20 · 22 · 24 · 26 · 30`
- **Body / meta cluster = 10–13px; `12px` is the default label size.** Panel headers = 14–16.
- Screen titles = 20–30. Boot/hero display = the two shipped clamps: `clamp(30px,6vw,62px)` /
  `clamp(34px,7vw,64px)`.
- ⚠️ **KNOWN DRIFT (snap on next touch, do not extend):** the build currently also ships `9 / 10.6 / 11.4 /
  12.4 / 13.5 / 17 / 19px`. These are off-ladder. Fix them to the nearest ladder value when you next edit
  that screen; never introduce a NEW off-ladder size.

**CASE + TRACKING RULE — this is what makes it read "arcade":**
- `text-transform: uppercase` on **all** labels, chips, buttons, headers and stat tags. Sentence case is for
  prose only.
- **ALL-CAPS ⇒ WIDE tracking** (`1.0–2.6px`; bigger caps = wider).
- **Mixed/lowercase ⇒ TIGHT tracking** (`0.2–0.6px`).
- Never wide-track lowercase; never tight-track caps. Mismatch here is the most common tell of un-reviewed type.

**LINE-HEIGHT:** display/one-line titles `0.95–1.1` · labels/chips/buttons `1.15–1.35` · body copy `1.35–1.5`.

**CONTRAST hook:** the type color follows the palette + the READABILITY rule above — e.g. disabled card text stays
`#C7C7E0` on `#3E3E6A`; never pure `#000` on a dark panel. Type never introduces a color of its own.

**TEXT TREATMENT — shaded fill + thin black border (LOCKED by Brick 2026-09-12 18:41, recorded 18:42).**
Applies to **display + button/label type sitting on dark panels** (menu / HUD chrome). This is *paint on the same
outline*, not glyph work — no new font file, no re-bake, fully offline.
- **Fill = a subtle vertical gradient in a warm OFF-WHITE. Never `#FFF`.** Stops, top→bottom:
  **`#F0EDE7` → `#E3DFD6` → `#C4BEB2`.** The top stop sits at ~92% lightness (down from pure white) with the hue
  curved **~2 points off neutral toward the amber accent** — that curve is what makes it read *cream*, not grey.
  Saturation stays far below anything that reads as a colour; the type still introduces no hue of its own.
- **Gradient scope = per text-line bounding box**, not per panel, so a multi-line stack shades evenly instead of
  the last row falling into shadow.
- **Border = a thin black stroke, ~`1.4px` visible.** Implement by drawing the stroke at **2× width (`2.8px`)
  UNDERNEATH the fill layer**; the fill covers the inner half, leaving a clean ~1.4px outside edge. This sidesteps
  the `-webkit-text-stroke` centring problem, where the stroke eats into the glyph itself.
- **Ground shadow (supporting, keeps the type off the glass):** the same text blurred `~2.4px`, `#000` at `~42%`
  opacity, offset ~`1px` down.
- ⚠️ **BORDER SCALES WITH SIZE.** `1.4px` is right at **20px and up** (titles, buttons). In the **10–13px body/meta
  cluster** a `1.4px` border clogs the counters on `A` / `R` / `8` — drop to **`~0.8px`**, or keep the shade and
  omit the border. The border is **decoration, not a weight crutch**: the shipped face has real 400–900 weights.
- **Reference render:** `rogueds/art_probe/sbs/styleguide-vs-offwhite-font.png` (left = locked style-guide menu
  board, right = the treated face). Generator: `rogueds/art_probe/sbs/make_styled_font.js`.

_(Machine-check note: `tools/style-lint.mjs` lints HEX only today — typography is not yet automated. This
section is written parseable so a type-lint pass can follow the same pattern as the palette linter.)_

## PERFECT SPRITE SHAPE — hero/unit silhouette + FACTION-INTERNAL COLOR language (LOCKED by Brick)
Brick's canonical sprite reference (label **"perfect sprite shape"**) = `ds-sprite-shape-perfect---393fffe0-...png` (a concept mockup of the live field: teal ally core/base + barrier + humans down to the orange enemy core/cannon, center contested glow, teal-diamond minerals + purple gas crystals, shop strip + top HUD). It locks BOTH the unit shape language AND exposes a differentiation gap Brick explicitly wants fixed.

### The shape language (KEEP — it reads well at a glance):
- Humans/aligned read as **ROUNDED + TECH**: covered visored "astronaut" helmets, boxy plate armor, clean right angles, rifles/carbines held two-handed, humanoid.
- Aliens/enemy read as **JAGGED + ORGANIC**: sharp flame/spike head-and-shoulder protrusions, spindly limbs, glowing yellow-orange eyes, aggressive silhouettes.
- **"Chunky-Slim" hybrid proportions** (semi-SD): thin limbs but slightly oversized joints/heads/hands = sturdy but readable, not spindly.
- **Iconic helmet + iconic weapon per role** so even in pure silhouette each unit class is tellable (round fishbowl vs pointed crest vs flat heavy inset head; short-thick vs long-thin vs heavy-cannon weapon).
- Thick dark outer stroke (~1.5-2pt `#000`) on every unit so they pop off the darker field (matches UNIT-vs-ENV rule 2).

### FACTION-INTERNAL COLOR DIFFERENTIATION (Brick's fix request — DO THIS on the live roster):
- ⚠️ GAP: human/allied units are currently MONOCHROMATIC teal — infantry vs mech vs scout are the SAME body color, so at distance they "muddy" together despite good silhouettes. Brick: **"humans need more color differentiation."**
- RULE: keep TEAL `#18B5B5` as the all-aligned PRIMARY faction color, but give EVERY human role a **secondary ROLE/class accent** so class reads by color first, shape second.
- **✅ LOCKED 2026-09-09 (Brick): SCAVENGER WORKER = WARM AMBER-GOLD, NOT TEAL.** The all-**Scavenger worker** (`rebels_node`) keeps its warm golden-amber/ochre chassis from the LIVE build (`~#A88221`→`#C49927` family) as its BUILDER/ECO identity — do NOT re-tint the worker to teal. Rationale (Brick): the builder reads best as a distinct utilitarian warm tint so econ pops at a glance; its dome+claw silhouette + non-combat role prevent confusion with the ember enemy. Scope of exception: the WORKER ONLY. ALL other human combat units (node/g/s/r/t/b/w/u combat castes) remain teal `#18B5B5` + their role accent. Amber on the rebel side = the worker/eco unit only, never a combatant.
- **RULE (LOCKED 2026-09-09 Brick): per-role HUMAN accents REQUIRED.** Every human combat unit carries a distinct secondary ROLE-accent (on shoulder/helmet/weapon/visor) so each caste is identifiable AT A GLANCE — the silhouette alone isn't enough. See the per-role accent palette in the PERFECT SPRITE SHAPE section. Keep the accent SMALL (never recolors the core teal body) so the teal-vs-ember faction split stays first to read; do NOT use the enemy's ember-orange `#FF7A1A` as a combatant accent; green on humans = healing/organic signal only (medic).

## UNIT VERSUS ENVIRONMENT — 3 layering rules (keep silhouettes readable over busy bg)
1. **Rim light:** ally unit 2px `#8EFFFF` top-left; enemy unit 2px `#FF9D42` top-right.
2. **Black outer stroke:** ~1.5-2pt `#000000` on all units to pop off the painterly field.
3. **Floor contact glow:** teal (ally) / red (enemy) at feet, 40% "hard-light" blend, to seat unit
   without losing silhouette. Keep the CENTER lane clear for readability where units actually clash.

## APPLIED MAPPING (what this means for each real screen — keep updated as we re-skin)
_(Each re-skin must build + keep 35/35 test suite green + deploy + verify LIVE, then note it here._
_Field slice status: battlefield now shows the RICH+COHESIVE generated backdrop v3 (baked + live); the
_ROGUE-style UI/menu/unit panels are still being punched to the palette below — keep filling these in.)_
- Battlefield backdrop: [DONE — A3 LIVE-FRAME live (2026-09-08): the dark full-bleed AI "poster" no longer overrides the field; the deterministic WARM field (warm dusty sky -> ochre/amber horizon band; warm earth field #8c7b52→#6d5a38→#3f3426 with torn-earth pits; teal ally-left #18B5B5 soak -> ember enemy-right #FF7A1A soak -> hot gold/ember contested centre) renders in EVERY environment so the live game == the DOM-shim-tested field. Poster art kept in bundle behind LIVE_FRAME_POSTER=false.] (see backdrop tier above)
- Battlefield ground band: [DONE — A3 warm field, teal-left/ember-right + contested centre live]
- Battle sky: [DONE — A3 warm dusty battle-haze sky #2a1d13→#a26a34 live]
- Shop/unit-card panel: [DONE — LOCKED via `ds-gui-shop-concept` board (Brick ✓ 19:28); re-skin live panel to match] (rules in GUI section above)
- Unit/allied sprite art (human vs alien + role differentiation): [DIRECTION LOCKED — "perfect sprite shape" ref `ds-sprite-shape-perfect` (Brick ✓ 20:00) + FACTION-INTERNAL COLOR access in UNIT section above; ▶ REBEL ROSTER POST-RESET (LOCKED 2026-09-09): rebel HUMANOID troopers re-derive off the one canonical human base (soldier-first, one at a time, Brick thumbs-up each; g first). EXCEPTION: ARMOR Pal `t` is a MECH/walker machine = its own chassis, NOT an armored human-base variant (Brick). ALIEN 8 FROZEN. Do NOT regen off one-off shape refs] (alien diff already strong)
- Battlefield field-with-units/towers (combat-frame guide): **LOCKED — LIVE-FRAME proportions v2**
  `ds-field-liveframe---8a1f4bee-d7cc-4ed8-ad3f-689e973ad6b9.jpg` / `field-liveframe.jpg` (Brick ✓ **2026-09-08 21:12 "PERFECT!"** via boards/ grid).
  This resolves the poster-scale flaw of the earlier Warm-Comic board and — combined with the palette/colors + good-composition + perfect-sprite-shape
  locks below — completes the FULL style-gate set (shop/map/deck/reward/menu/end/battlefield all now LOCKED). Verifier (vision) confirmed the board reads as
  REAL live RTS gameplay, not cinematic: largest units ~1/8-1/9 of image height; ~55-60 small units (a real army across the field); two core bases at the
  far left+right edges ~1/7 field width (bases, not looming towers); slim deep-indigo UI strip on bottom ~8 — 15% w/ unit icons + resource counters
  (Design Law #1 pure-glass cut-through, warm field above); 3-4 top-down/oblique strategy camera over an open battlefield; warm golden/umber field,
  teal-army LEFT (#18B5B5, human role-diff accents) vs ember-aliens RIGHT (#FF7A1A —> #FFB03A, jagged spike silhouettes); human mech/rifle/scout squads w/
  thin 2px dark outlines + tiny role markers; shared point-defense towers, glowing core buildings at flanks, mid-field turrets/crystal/craters.
  EARLIER v1 `ds-field-warmcomic---7ebc9128-054b-44a9-98a0-def79150f693.jpg` REJECTED/SUPERSEDED (poster-scale, kept as reference).
  - The one non-negotiable that the v1 failed and v2 fixed = PROPORTION (below).**
  - **⚠️ PROPORTION RULE (Brick 21:03 + 21:12)**: "a sprite in an army can't take up 1.4 of the screen." A battlefield image is only correct when units
    read SMALL (~1/9 of height each), one of many across a wide open field between flank bases — never poster/hero scale. Anchor ANY future field render to
    the LIVE game geometry: field ≈ 900w × 520h, in-game unit sprites ≈ 55-60px ≈ 1/9 field height. Bake this principle into every live-field render and
    concept board alike. NO poster-scale units ever again.
- Reward/upgrade + card/deck + relic UI: [PENDING]
- Menus/start screen + end/victory screens: [MENU DONE — 2026-09-13, palette+geometry below; END / VICTORY+DEFEAT LOCKED — see dedicated GUI section below]

## MENU / START SCREEN — LOCKED PALETTE + GEOMETRY (2026-09-13, Brick's calls)
Measured off the rendered Godot build (not off the board) — every value below is byte-verified in `menu_v2.png`.

**Container + surface (REVISED 2026-09-13, Brick item 7 — "2 strong asks"):**
- **Menu container fill = `#0A0B28`** (10,11,40). The button container and any button that shares the container
  fill are BOTH `#0A0B28`. ⚠️ This explicitly supersedes the old `#03060D` value that container + ghost buttons +
  background all shared (they read as one flat black).
- **Background** is still `#03060D` for now — Brick is ambivalent and expected to re-point it at the style-guide
  reference image later, so do NOT treat the background as locked.
- **Unselected difficulty chip fill = `#03060D`** (item 9) — i.e. the chip sits at the BACKGROUND value when idle,
  so "selected" is what lifts it to the grey `#3E3E6A`. Chips keep the cool-grey border so they still read as a control.

**Button palette (idle / un-hovered = the DEFAULT state):**
- **Idle fill (primary buttons: START/DEPLOY, LOAD/CONTINUE) = `#252A4A`** (37,42,74). Reads as a raised indigo-grey slab.
  ⚠️ SUPERSEDES the old `#0B0B2E` panel-base value for BUTTONS; the panel/card ladder keeps its own roles.
- **Idle border = `#8A96C0`** (138,150,192) — cool desaturated indigo-grey. Confirmed against the menu board (sampled `#8A95C3`).
  ⚠️ A near-match to the old role-tag grey `#9FB4C7`; keep them distinct in use (tag = text outline, `#8A96C0` = button edge).
- **Hover** lift: fill `#333A66`, border `#C8D8FF`, plus the cyan halo (`shadow_color #739EEF @0.45`, `shadow_size 16`).
- **Pressed:** fill `#191D34`, border back to `#8A96C0`.
- **Soft/ghost buttons (TRAINING HALL, OPTIONS) = container fill, no halo.** Fill `#030614`, same `#8A96C0` border. Rules: *any button whose action is secondary shares the container fill and loses the halo*; primary actions get the `#252A4A` raised fill.
- **Difficulty chips (EASY/STANDARD/HARD):** UNSELECTED = `#03060D` (background value, item 9); SELECTED = grey `#3E3E6A` (62,62,106) — the grey reuses the existing DISABLED fill value deliberately; grey = meta/settings, never the teal identity or the currency hues.

**Button text treatment:**
- **Face: `Saira Condensed` — buttons/labels use ExtraBold (800); nothing operable below 800.** The Godot build
  shipped with NO font at all (Godot's default face) until 2026-09-13; the five TTF weights + `OFL.txt` now live at
  `assets/fonts/` in the project, bound via a `FontVariation` so tracking is settable.
- **Kerning: TIGHT.** `FontVariation.spacing_glyph` = negative (start at `-1`, push to `-2` for caps headers) for
  the blocky military-caps look. This is the "closer kerning" knob — do not add positive tracking on caps.
- Title (primary line): cream `#F0EDE7`-family, bold, ALL-CAPS.
- Subtitle inside the button: **exactly 75% of the title size**, color **`#90BEBE`** (muted teal-cyan) — a *text* tone only; it must NOT be used as a border/fill or it collides with ally teal `#18B5B5`.
- **Every button label carries a black outline (`Color(0,0,0)`, `outline_size 2`) — 2px.** Counters stay clean at button sizes (24px title / 22px secondary). Do not go above 2px; at the 10–13px body cluster drop to the `~0.8px` guidance in the type section.

**Geometry (locked):**
- Primary buttons `370×80` · secondary buttons `370×60` · difficulty chips `118×38` in a 3-up row (8px gaps).
- Button container inner padding **35px top + 35px on both sides**; the container's bottom edge **meets the buttons — 0px bottom margin**, and the two lower chips touch the container edge.
- Subtitle→title size ratio 0.75·1.0; 14px vertical gap between buttons.

**Wordmark (`title_wordmark_v4`, 2026-09-13):**
- **Gradient fill** — top `#F9F3D1` (pale warm cream) → bottom `#9BCCDA` (light blue). NOT a flat fill.
- **Directional cartoon border, `#0A0F22` default ink: 4px top / 5px sides / 7px bottom.** The asymmetry is the look
  (heavier underside reads as a printed/painted weight).
- **Adjacent letters within a word are JOINED — their borders touch and merge into one silhouette.** Do NOT
  re-space or kern glyphs apart; the merge is correct and intended. Only the WORD spaces separate.
  ⚠️ VERIFY THIS BY MEASUREMENT, NOT BY EYE: threshold the alpha channel, take the x-height band (middle ~64% of
  the mark's ink rows), and count full-height background corridors — **2 corridors = letters joined (correct)**;
  a corridor per letter gap = kerning is broken. Vision models misread the gradient as gaps; the corridor count is
  the authority. Same class of trap as the SABLE/`#03060D` flat-black blend above.
- **Stencil breaks are KEPT** — the distressed cuts through `R`/`E`/`D` are the design's character ("crunchy"),
  and they survive the border because the border is drawn around the WORD silhouette, not per-glyph.
- **Slant = subtle baked shear** (lean, not a hard italic) — applied at build time, shipped in the PNG.

## Reference artwork — FULL CATALOG (all in `/home/openclaw/.openclaw/media/tool-image-generation/`)
Not committed to the repo — they are references for prompt-extraction reuse. Grouped by what they cover.
If a board/look is used, note it here so the set stays searchable.

### Direction boards (broad — each ALSO contains UI/menus in the composition)
- **LOCKED: COLORFUL / WARM** `ds-direction-colorful-warm---8c5221fd-fb36-42b1-98df-11977a91b8bf.jpg` —
  vibrant comic/neon-retro: glowing borders, unit cards w/ stats, Buy/Deploy buttons, health bars,
  ornate card-based REWARD screen. THIS is the primary GUI reference (shop card + reward UI live here).
- `ds-direction-cold-strategic---47b97c1d-1795-49ab-b6f8-8a101fa009a9.jpg` (rejected; alt = flat blueprint UI)
- `ds-direction-moody-neon---3e060dce-fa1e-45a3-a0fe-44a298d6c6d4.jpg` (rejected; alt = neon wireframe UI)

### Dedicated GUI concept boards (per-screen, generated → Brick LOCKED → then coded)
- **LOCKED: SHOP/UNIT-CARD PANEL — labeled "GOOD UI"** `ds-gui-shop-concept---19ab32d5-a5b7-4f59-994e-7078e64ec4a8.jpg` (Brick
  2026-09-08 19:28 ✓ lock; **20:15 ✓ "this one needs to be labeled good ui"**). Dedicated COLORFUL/WARM mock: deep-indigo `#0B0B2E` glass panel (inset `#05051A`, card fill
  `#11113D`) CUTTING THROUGH a dimmer/dirtier battlefield backdrop (Design Law #1); header/map-stub; teal-diamond
  mineral + gas currency readout; horizontal row of unit-cards each w/ sprite + name + role tag + stat bars (vibrant
  `#FFCC00`) + `◆/◈` cost + DEPLOY button; ally cards glowing teal `#1CC7C7` border, rare `#E026FF` (Shock Trooper),
  locked/unaffordable cards DIMMED/desaturated `#3E3E6A`. In code the gas icon must be ember red-orange NOT violet.
- **LOCKED: MAP / ROUTE-SELECT SCREEN — FTL-style mesh + creeping fog + varied events**
  `ds-map-route-ftl---763fa833-cc53-4199-a4a5-383df3f4962d.jpg` (Brick ✓ 2026-09-08 20:40 "yes lock that"). [DONE — A4 2026-09-08: #mapOv route fork coded to this board — star-space backdrop, CLEARED cyan route-thread → current node, ring-accent forks, glyph legend, bottom fog, kept sparser than board per clutter caveat.] The FTL-style
  branch/route-select layer over the choice-node model in `src/map.mjs`. Rules (verified on-brief before lock):
  - **FTL MAP GRAMMAR**: top-to-bottom progression through horizontal BANDS; a woven MESH/web of node circles where paths
    split AND rejoin (not a straight line); 2-4 forward choices per band.
  - **FOG OF WAR**: earlier map explored from the top; the lower/unexplored region sits under a drifting dark shroud whose soft
    LEADING EDGE advances. An exit/chokepoint-node at that fog edge may be HALF-shrouded / get swallowed by the incoming fog
    (Brick exact ask: FTL's exit coverable by incoming fog).
  - **VISITED vs AHEAD**: thick cyan tracing line links visited nodes → current "you are here" node; unvisited forward paths thinner
    grey; some future choices still under the fog.
  - **VARIED EVENT NODES (like FTL)**: different node types carry different small glyphs + ring accent colors — battle/elite, shop/supply,
    upgrade, relic/treasure, hazard, and a '?'/unknown. Legend teaches the glyph→reward mapping (Brick 20:19 "different events on the
    map, just like FTL"). Event colors follow the map accent legend below, NOT the UI/field primaries.
  - **UI/panel**: slim deep-indigo GLASS sidebar/footer (surfaces per COLOR GUIDE: panel `#0B0B2E`, lighter tooltip/card `#23234F`,
    light `#FFFFFF`/`#A0EFFF` text) carrying run header, node-type LEGEND, current-node tooltip, currencies — same family as GOOD-UI shop.
  - ⚠️ **CLUTTER CAVEAT (Brick 20:41)**: the reference BOARD is **too cluttered** — too many nodes/lines/badges competing. The LIVE
    map must be cleaner/sparser than the board: fewer overlapping lines, clearer gap between route threads, rest space so the eye rests
    on the real decision (next node choice) instead of a busy mesh. Keep FTL grammar + fog + events, but AIR IT OUT — this was flagged
    as a real flaw to fix in the build, not a look to copy wholesale.
  - **Rings/accents (distinct windows, no teal-wash / no yellow-sea)**: friendly/neutral teal `#1CC7C7`-family, fight/elite ember
    `#FF4A4A`/`#FF7A1A`, rare/boss/exit GOLD `#FFD324` (luxury only), '?'/unknown cool-grey `#9FB4C7`; mineral `◆` ice-blue `#A0EFFF`,
    gas `◈` ember. Map field on deep indigo `#0B0B2E` space w/ subtle star/nebula (comic-clean, cool, uncrowded).
- **LOCKED: DECK / RELIC COLLECTION SCREEN — rooster grid + owned relics**
  `ds-deck-board---b3591380-3fb7-48ca-8630-e79407b09708.jpg` (Brick ✓ 2026-09-08 20:55 "I said I liked the deck, you should have locked it" —
  locked retroactively, my slip for not locking immediately when he said "I like this one" 20:53). Rules (verified on-brief):
  - **Frame**: deep-indigo glass family per COLOR GUIDE (dark panel `#0B0B2E` -> lighter card `#23234F` -> near-black well `#05051A`,
    thin glowing borders + recessed lip). AIRY/uncrowded.
  - **LEFT/main: unit DECK grid** (~8 cards) — each card = teal-army human sprite (`#18B5B5`) in a dark well, unit name + role-tag
    pill (cool-grey `#9FB4C7` outline; WORKER/SCOUT/MARINE/RANGED/HEAVY/TANK/MEDIC), small stat pips/bars bright-yellow `#FFCC00`
    (values only). Per-type ROLE-ACCENT color-diff (game rule, ca177db): scout/worker green lens, heavy/tank steel-grey-white trim +
    bulky frame, ranged/marine yellow equipment — all still read teal-army. Ally border teal `#1CC7C7`.
  - **RIGHT panel: RELICS** — vertical stack/list of owned relic chips: small relic icon + name + 1-line effect. Use the GAME's REAL
    relic names (Overclock Core = faster actions, Nano Forge = cheaper upgrades, Rapid Harvest = more minerals, Lazarus Array = revive
    on fall, plus Breaker/Frugal/Harden/Mender/Nursery/Pack/Power). Gold `#FFD324` ONLY as rare-relic border accent; normal relics
    lighter-indigo-grey border + ice-blue `#A0EFFF` glyph.
  - **Discovery**: a `'?'` LOCKED/unknown relic shown as a dark question-mark silhouette (cool-grey `#9FB4C7`) — signals the relic POOL.
  - **TOP bar**: screen title (e.g. "COMMAND DECK") + currency `◆` ice-blue / `◈` ember top; run/campaign-depth readout; bottom-right
    CLOSE button (deep-indigo glass w/ ice-blue accent), consistent w/ other boards.
- **LOCKED: REWARD / PICK-A-REWARD SCREEN — clone of the SHOP skeleton**
  `ds-reward-board-v2---fc5f844d-c5b8-4510-830b-f3794e89bebf.jpg` (via GitHub boards/ grid; Brick ✓ 2026-09-08 21:01 after first
  pass 20:53 "should look like this [shop]"). Structural CLONE of the LOCKED shop screen — differs only in heading + content
  (reward choices instead of purchasable units). Same single central floating rounded MODAL over deep-indigo `#0B0B2E` space;
  header top-LEFT (big white all-caps "PICK A REWARD" + pill CURRENCY bar directly under: ice-blue `◆` `#A0EFFF` + ember `◈`
  `#FF7A1A`); ONE horizontal row of THREE reward cards (15-20px gutters) each w/ shop card anatomy: name bold caps + grey
  sub-line; REcessed darker WELL (teal-army sprite offset-LEFT, role pill TOP-RIGHT cool-grey `#9FB4C7`, bright-yellow `#FFCC00`
  stat pips BOTTOM-RIGHT); CTA button at card bottom. One card SELECTED w/ brighter teal `#1CC7C7` glow. Bottom-right legend pill
  outside panel ('REWARD — CLAIM ONE'). Role-color-diff per game rule (yellow ranged / steel heavy / green scout, all teal-army).
- **LOCKED: START / MAIN-MENU SCREEN**
  `ds-menu-board---9eb76db0-c628-4674-8fd3-ff9549b893af.jpg` (Brick ✓ 2026-09-08 21:01 via GitHub grid). Big DIRECT STRIKE comic
  title lockup; teaser clash splash BEHIND translucent glass (teal-army vs ember ENEMY FRONT key art, not live play); glass menu w/
  START/DEPLOY primary (teal glow) + LOAD/CONTINUE + TRAINING + OPTIONS; Easy/Standard/Hard segmented chips (Easy selected);
  faction teal-shield vs ember-sigil emblems; currency. Deep-indigo glass family, AIRY.
- **LOCKED: END / VICTORY+DEFEAT SCREEN**
  `ds-end-board---5795c184-a3c7-4d73-9ad4-d268bfd1e1b7.jpg` (Brick ✓ 2026-09-08 21:01 via GitHub grid). Two-panel result frame:
  LEFT VICTORY (warm gold `#FFD324` header, teal win art/laurels, stat chips battle-cleared/minerals `◆` ice-blue/gas `◈`, CONTINUE/
  NEXT NODE primary teal + SHOW DECK) vs RIGHT DEFEAT (ember `#FF4A4A` header, dimmed jagged alien menace + cracked smoking teal
  core, somber chips 'your core fell in battle X', RETRY NODE hopeful primary + END RUN). Warm-wins/ember-loses split, family-matched.

The two-panel board is a side-by-side visual reference for two mutually exclusive runtime outcome variants; runtime displays exactly one outcome at a time, never Victory and Defeat simultaneously. Existing flow-specific actions remain authoritative: non-final win → Reward screen / Continue; final Victory → New Campaign; Defeat → Retry Node / End Run. ‘CONTINUE / NEXT NODE’ is reference shorthand, not a new action or progression rule. Defeat has no Victory/Scrap award row; authoritative loss award is 0.
- (Pending per-screen boards: NONE currently open in the shop/UI frame set — all of shop/map/deck/reward/menu/end now LOCKED. Remaining
  BIG OPEN = battlefield FIELD look (see battlefield section): colors+design approved 21:01, PROPORTIONS need to read as real gameplay.)

### Combat-frame composition reference (GOOD COMPOSITION — Brick ✓ 20:11)
- **COMPOSITION LOCK (Warm Comic merge frame)** `siege-merge-Ccolors.jpg` (Brick: posted it noting **"this is good
  composition, still lacking color differentiation"**).This locks the frame COMPOSITION that worked (NOT the full style/color
  — style lock still in flight as siege A/B/C vs Warm Comic). Rules distilled from what made it read well:
  - **Lateral tug-of-war layout**: bases/cores at far LEFT (teal/human) and RIGHT (ember/alien) flanks; distance between = the push.
  - **85/15 split**: playfield ~top 85% of frame height; dedicated bottom ~15% UI strip footer.
  - **3-plane depth**: foreground lane = hottest contrast + thickest outlines; midground (bases/horizon) = thinner; background
    (cliffs/monoliths) = low-contrast hazy no-outline atmos. 3/4 oblique view of units (front+side visible) to aid silhouette read.
  - **Center-of-interest = the lower-center contested glow + the projectile tracers**: keep hot white/gold center glow + arcing
    tracer lines connecting the flanks that point the eye across the midline; action converges on the capture point.
  - **Split-complementary temp zones**: cool-teal lighting washes the left half, warm-ember the right half, with a NEUTRAL ground
    band in the middle so either side's units pop when crossing the midline. Dark foreground "trench" separates field from UI.
  - **REPEATED GAP (color diff) — RESOLVED/LOCKED 2026-09-09 (Brick).** The OLD live state was humans internally monochromatic teal (variety only via value) — that was the GAP/problem, NOT a rule. Brick: "no per-role accents is very wrong, we want per-role accents for visibility." **RULE: EVERY human unit carries a clear secondary ROLE accent so role reads by COLOR FIRST, silhouette second** (which unit is which at a glance). Human base armor stays teal `#18B5B5` + the single per-role accent. Enforced on any reskin to a locked style. (Worker carve-out: the Scavenger builder is amber-gold-bodied — separate LOCKED note; that IS its role accent.)

### 👮 HUMAN ROSTER — SINGLE CANONICAL BASE MODEL (LOCKED 2026-09-09 Brick)
> **THE reset rule this replaces:** Brick flagged that the roster drifted (all 16 castes regenerated off DIFFERENT shape
> refs → same world, mismatched silhouettes). Fix, mandated by Brick: **ONE canonical human base model, derived to fill
> the roster ONE role at a time** so every human unit reads as "same soldier, different gear," not different people.

- **LOCKED 2026-09-09 (Brick "Base is good")**: the rebel HUMANOID troopers derive from THE single canonical human base sprite.
  **EXCEPTION (Brick 2026-09-09 "Armor Pal was cool too... it's not just a human so it wouldn't be a modified base"):** the tank role `t`
  = **ARMOR Pal / Paladin-Mech** (the heavy round-bodied walker MECH — beetle-tank with one central dome cockpit + 2 stubby legs + a fat
  cannon arm) is a MACHINE, NOT a human in armor — it is its OWN chassis (keep it mechanical), do NOT derive it as "human base + armor."
- **The base** (source of truth for every human derive):
  - Raw canonical render: media dir `human_base_chassis---candidate---fde0df61-...jpg` (clean, accent-free)
  - Display/trim sprite: curated at `art_probe/base_model/human_base_full.png` (482×619, ~22×28 px30)
  - Clean no-ghost shape anchor: `v2_rebels_g_teal_proof---4840467e-...jpg` (Brick-approved direction proof; the weapon-hold
    + posture/rifle family the base carries; NEVER regenerate off a ghosted sprite — see militia lesson)
- **Canonical base visual spec (FREEZE on every derive):** a single teal `#18B5B5` rebel trooper, calm combat-ready
  neutral stance facing RIGHT, standard compact rifle at low-ready two-handed; plain ACCENT-FREE defaults (no role trim —
  each derived unit adds its ONE role accent). Bold readable silhouette, thick black 2-3px outline, FLAT SOLID magenta
  `#FF00FF` bg, tight-but-not-clipped crop, small dark elliptical ground shadow at feet ONLY, single figure (no ghost/
  dup/enlarged backdrop/reflection/watermark/text). Head/helmet + torso + 2 arms + 2 legs, no extra limb/gear clutter.
- **Derive rule:** each humanoid trooper = THIS base + that role's loadout swap + its ONE role accent (palette below). Silhouette
  edits stay IN-family (proportionally the same soldier, different gear). Derive ONE unit at a time, show Brick, get a
  thumbs-up BEFORE the next. Do NOT regenerate off separate one-off shape refs per caste. (ARMOR Pal `t` + the aliens are NOT on
  this derive path — separate non-humanoid chassis. The "same soldier, different gear" rule applies to the rebel HUMANOID units only.)
- **Status of derive (reconciled 2026-09-09 vs the on-disk derive sets):** each humanoid role below has a LANDED derive — its full
  `_full.png` + `_30px.png` compose set lives in `art_probe/base_model/derived_<slot>/` (and the paired `art_probe/contact_v2/human_<slot>_*`
  canonical sheet), all deriving off the one canonical teal human base with that role's single accent:
  - `g` Rebel Militia (RED melee trim; VISOR+SWORD variant) — **LOCKED by Brick 2026-09-09 ✓** ("that was good"); derived (derived_g)
  - `s` Striker/Breach-Cell (DEEP-NAVY #2A4EFF) — derived on disk (derived_s)
  - `r` AA-Gunner (sky-blue #4FC3FF) — derived on disk (derived_r)
  - `b` Scattershock (ORANGE #F97A1E pack) — derived on disk (derived_b)
  - `w` Combat-Med (white cross + green heal) — derived on disk (derived_w)
  - `u` Comms-Officer (MAGENTA #FF3BE8) — derived on disk (derived_u)
  OUT OF THE HUMAN-BODY derive chain — do NOT read as pending humanoid derives: **ARMOR Pal `t` is a MECH/walker (Paladin-chassis) =
  its OWN non-humanoid chassis, NOT "human base + armor" — tracked as its own separate OPEN build (SCRUM R6)**; and `node` = Scavenger
  worker stays amber-gold-bodied (different class, frozen, intact). [Aliens remain FROZEN — next line.]
- **ALIEN half is FROZEN** (Brick 2026-09-09 "Aliens look good") — do NOT re-derive/regenerate the 8 aliens.

### Unit / sprite-shape direction reference
- **LOCKED: PERFECT SPRITE SHAPE** `ds-sprite-shape-perfect---393fffe0-10f6-43ab-ab49-c3906bd6d44d.png` (Brick
  2026-09-08 20:00 ✓, from an inbound concept mockup he labeled "perfect sprite shape"). Canonical unit-shape language
  (human rounded-tech w/ visor helmets + iconic per-role helmets/weapons; alien jagged-organic spikes) AND the source of
  Brick's note that human/allied units need **more color differentiation** (currently monochrome teal — add per-role
  secondary accents; see PERFECT SPRITE SHAPE section).

### Unit sprite art (per-faction caste sets)
- Rebels (Human): `rebels_node/g/t/s/r/b/w/u-*.jpg` (worker/melee/ranged/etc caste refs)
- Aliens (Alien): `aliens_node/g/t/s/r/b/w/u-*.jpg` (same caste set, alien styling)

### Structure / core art
- `ally_core`, `ally_barrier` (blue/teal) · `enemy_core`, `enemy_barrier`, `enemy_core2` (red/ember)

### Battlefield backdrop tier guide (3-class — the "rich-not-scattered, rich-not-muted" lesson)
- v1 VIVID/SCATTERED (negative: too many uncohesive colors): `ds-battlefield-bg---16d787bd-...jpg`
- v2 DIM/MUTED (negative: grey-wash, too dark): `ds-battlefield-bg-calm---7bd2edcd-...jpg`
- v3 RICH+COHESIVE (KEEPER: one cool teal/indigo family + single amber accent): `ds-battlefield-bg-cohesive---4fe51577-...jpg`
- Older field comps: `bf-reference-1` `bf-ref-clean-v2` `bf-ref-war-torn-v2`

### ✅ DEDICATED GUI REFERENCE BOARDS — COMPLETE (all per-screen boards locked 2026-09-08)
Reward/upgrade + deck/relic + menu/start + end/victory had no standalone board; the whole per-screen GUI set was generated,
SHOWN to Brick, and each LOCKED. Every screen now has its own reference + rules section in this bible:
- SHOP/unit-card -> LOCKED GOOD UI (19:28/20:15) + dedicated palette/layout section
- MAP/route-select -> LOCKED FTL (20:40) + anti-clutter rule
- REWARD/upgrade -> LOCKED (21:01, 'good enough', shop-skeleton clone)
- DECK/relic -> LOCKED (20:55)
- MENU/start -> LOCKED (21:01)
- END/victory+defeat -> LOCKED (21:01)
- BATTLEFIELD field -> LOCKED LIVE-FRAME proportions v2 (21:12, 'PERFECT!')
Human-role-color-diff: LOCKED. Battlefield style: LOCKED (above). All guide gaps closed.
