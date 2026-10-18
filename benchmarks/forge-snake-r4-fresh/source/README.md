# Reproduce Arm B

Start at R3 commit `7a3a2c7c3af1f4d7803ad31753231d5f728043b0`.
`build_r4.py` imports only `benchmarks/forge-snake-r3/snake-sectional-r3.glb`.
It edits that asset and reconstructs staging from R3's tracked render-settings
JSON. It does not open a prior working blend or another Round 4 asset.

Host paths in the scripts point to this order's isolated Linux-volume worktree,
exposed to Windows Blender/Godot through the WSL UNC path. The host's C: is nearly
full; no unrelated workloads or files are changed. Cycles CPU avoids GPU memory
contention. Required executables are Windows Blender 4.5.14 and Godot 4.7.2.

From the worktree root:

1. `bash benchmarks/forge-snake-r4-fresh/source/run-build.sh` exports the GLB,
   texture atlases, counts and working blend.
2. `bash benchmarks/forge-snake-r4-fresh/source/run-render.sh preview g 0`
3. `bash benchmarks/forge-snake-r4-fresh/source/run-render.sh final g 0`
4. `bash benchmarks/forge-snake-r4-fresh/source/run-render.sh final baseline 1`
5. `python3 benchmarks/forge-snake-r4-fresh/source/validate_glb.py benchmarks/forge-snake-r4-fresh/snake-sectional-r4-fresh.glb`
6. `python3 benchmarks/forge-snake-r4-fresh/source/compare_rig.py benchmarks/forge-snake-r3/snake-sectional-r3.glb benchmarks/forge-snake-r4-fresh/snake-sectional-r4-fresh.glb`
7. `bash benchmarks/forge-snake-r4-fresh/source/run-godot.sh`
8. Run `source/finalize.py` with a Python containing Pillow/NumPy to assert paired
   production settings, dimensions and glare sockets, sample corners and write
   the consolidated counts/evidence manifest.

Canonical asset materials use packed ORM. Review AO multiplication is added only
after export. The rendering script opens the local working blend and uses the
same stage for R3 baseline and R4 candidate. Historical preview b is intentionally
retained as evidence of the eye correction. Build a failed the budget assert;
build b reclaimed superseded struts; build c exposed floating crest bolts in its
checkpoint; build d seats them
against the actual fin surfaces. Its module detail preview then exposed armor/
cassette overlap. Builds e/f diagnose cassette geometry; build g lifts the complete
cassettes and adds recessed dark backings, and is the delivered build.
Run `render_details.py` in Blender for the labeled 48-sample module/tail previews.
