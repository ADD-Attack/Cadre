# Reproduction

The canonical input is only the verified delivery
`benchmarks/snake-r2-sol/snake-sectional-r2.glb` at
`52c96999907cb6a34ae41116092d97b9b4141024`.

`build_r3.py` edits that GLB directly. It uses Forge's own R1 packed blend only to
inherit the identical camera/light/world/shadow-catcher/compositor staging; every
R1 asset object is removed before R2 import. No asset regeneration, Hunyuan pass,
or other entrant input is used.

Paths identify this host. The checkout was moved from C: (full) to the Linux
workspace and accessed by the required Windows applications through WSL UNC.

1. `bash benchmarks/forge-snake-r3/source/run.sh build h`
2. Run `render.py` in Blender 4.5.14 with `R3_MODE=preview` / `R3_TAG=h`.
3. `bash benchmarks/forge-snake-r3/source/run-render.sh preview h 0` generates the
   final checkpoint pair. Run `render_details.py` for the explicitly labeled detail previews.
4. Run `render.py` with `R3_MODE=final`, `R3_BASELINE=0`, then again with
   `R3_BASELINE=1` for identically staged paired R2 captures. Defaults: CPU Cycles,
   256 samples, adaptive 0.01, OpenImageDenoise, 1920×1080. Tight fog glow is
   threshold 0.65 / size 6 / mix -0.75 for both paired assets.
5. `python3 benchmarks/forge-snake-r3/source/validate_glb.py benchmarks/forge-snake-r3/snake-sectional-r3.glb`
6. `python3 benchmarks/forge-snake-r3/source/compare_rig.py benchmarks/snake-r2-sol/snake-sectional-r2.glb benchmarks/forge-snake-r3/snake-sectional-r3.glb`
7. `bash benchmarks/forge-snake-r3/source/run-godot.sh` — Godot 4.7.2 import,
   loaded scene/material/tangent/independent-pose checks, native rest-pose capture.

The working packed `.blend` is local and ignored, not a delivery dependency.
Textures embedded in the GLB and their generated PNGs are provided. Judged renders
are `captures/r3-full-body.png` and `captures/r3-head-closeup.png`; baseline pairs
are explicitly named `baseline-r2-*`. Godot Compatibility evidence is not judged.
