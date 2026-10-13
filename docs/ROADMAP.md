# Muse Relay — steal list (from browser-use, UFO², OmniParser)
_Written 2026-10-13. This is the MuseRelay2 spec if it's ever built; the alternative is assembling these instead (see chat 2026-10-13)._

## From browser-use
- Element-index interaction for web surfaces: act on numbered DOM elements, not pixels.
- Domain allowlists: hard rail on which sites the agent may touch.
- Parallel/headless runs: multiple tasks at once, no desktop held hostage.
- Custom-tools registry: bolt our own functions onto the agent cleanly.
- Benchmark discipline: measure task success rate, don't vibe.

## From UFO²
- UIA fusion: Windows UI Automation control tree first (exact rects/names, free, instant), vision only for what UIA can't see.
- GUI+API hybrid: prefer native app APIs / Office COM over clicking when an API exists.
- Speculative multi-action planning: predict 3–5 steps per LLM call, validate cheaply, re-plan only on failure (their claim: ~51.5% fewer LLM calls).
- Picture-in-Picture virtual desktop: agent works in a nested desktop, user keeps theirs (maturity flagged — README says "coming soon").
- Host/App agent split: one coordinator, per-app specialists (same shape as Cadre).

## From OmniParser / OmniTool
- Screen parsing for blind surfaces: labeled element boxes for games, canvas, custom-drawn UI where neither DOM nor UIA exists.
- Interactability prediction: parser flags which elements are actually clickable.
- Set-of-marks contract: numbered overlay on the screenshot as the shared language between parser and LLM.
- Trajectory recording: log screenshots + actions per session so failed runs can be replayed and debugged.

## The alternative to building MuseRelay2
Adopt UFO² as the desktop engine, point its custom OpenAI-compatible endpoint at the muse-brain-gateway (model `brain/muse-brain`) so Christopher's Muse context stays the brain, add browser-use CLI for pure-web tasks, and keep Muse Relay v1 as the simple fallback. Pros/cons delivered in chat 2026-10-13.
