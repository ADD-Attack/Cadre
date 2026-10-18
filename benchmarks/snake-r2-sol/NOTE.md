# Snake R2 rescue — delivery for independent panel review

Order `op-snake-r2-rescue-20261018` · Chisel / studio-builder-2 · Sol medium.
Branch `snake-r2-sol-20261018`, based strictly on shipped R1 `32c661e`.
This is an implementation/evidence handoff, **not a panel pass or acceptance claim**.

Input pack: 52,335,140 bytes; SHA-256
`37d0b267806c04813c151449c9954bff531e32797458a617db7fd96ee8a1f2c6`.
No Forge R2 or other entrant's in-progress work was accessed.

## Changes versus R1, mapped to all five targets

1. **Weathering system, not a value-only pass.** Rebuilt the head, module and tail
   PBR atlases in stable part-local coordinates. Cycles ray-baked AO and signed
   geometric curvature drive recess grime and broken seam corrosion. Explicit
   bolt anchors seed downward rust runoff; exposed convex edges and short scuffs
   reveal brighter metal. Roughness and metallic change with dirt, oxidation and
   exposed steel. AO is separately packed in ORM-R, not multiplied into the
   exported albedo. Render-only AO multiplication is applied after GLB export.
   Smooth internal triangulation edges are excluded from the curvature-wear mask.
   Normal maps carry fine scratches and pitting only; plates, seams, fasteners,
   cooling slats and pistons are geometry.
2. **Head re-plate / re-base.** Replaced the lumpy reconstructed skull and slab
   overlays with an analytic tapered skull and fitted, chamfered plate shells.
   Each solid plate is cut independently for sockets and nostrils before joining;
   this avoids Boolean artifacts from overlapping hardware. The hidden core is
   recessed sufficiently to avoid poking through curved plates. A visible oval
   nostril has an actual machined opening and dark inner floor, not a printed slot.
   **Re-base disclosure:** this is a fresh procedural head, not a Hunyuan generation.
   No ComfyUI/texture stage was used. The assembly head pivot/placement is retained.
3. **Eye recess.** Replaced R1's large bright optical assembly with a smaller
   teal lens behind a deep dark funnel, a thin darkened metal rim, fine optical
   ticks and a small central emitter. Both sides are modeled. The outer socket
   lip is near-flush with the head plates; the luminous element is recessed.
4. **Layered segment module.** Rebuilt the smooth reconstructed barrel as a dark
   core plus twelve staggered shell plates, four secondary lap tiles, twelve
   seated hex fasteners, two modeled cooling cassettes and twin piston assemblies.
   All 28 rigid segment nodes still reference **one shared mesh**. R1's joint
   housing/emitter geometry, taper, axial rolls and placement are retained.
5. **Tail tip + trims.** Rebuilt the tail from budget-rebalanced copies of the
   new module, preserved inline recessed seam joints, and two rings of individual
   tapering tip plates plus swept fins. No bare pale cone remains. Opaque trim
   surfaces receive the same dark weathered atlas family; optical rims are also
   darkened.

## Budgets and export checks

| Part | R1 | R2 exported | Limit |
| --- | ---: | ---: | ---: |
| Head incl. optical assemblies | 12,861 | 13,152 | 10,000–18,000 |
| Shared segment | 1,392 | 1,336 | — |
| Joint | 192 | 192 | — |
| Segment + joint | 1,584 | 1,528 | ≤1,600 |
| Tail + joint | 2,634 | 2,753 | ≤3,000 |
| Assembly, instanced | 59,847 | 58,689 | 30,000–60,000 |

28 segment nodes → one mesh; 29 housings + 29 emitters; 90 mesh nodes overall.
GLB SHA-256: `7e38d91836a8cd4e02a5b84b8c26b49117b35a5253355a7f40f2135c71504424` (31,247,664 bytes).

The uncapped cost study adds 24 six-sided grille crosswires and 12 additional
hex fasteners: **720 extra modeled triangles per module**. That option costs
**2,056 module / 2,248 module+joint triangles** and adds 20,160 triangles across
28 instances (78,849 assembled triangles). It violates both module and assembly caps and is not exported.
The additions are constructed and counted in memory by the build script, not
presented as a tested alternate delivery.

Independent binary-glTF validation, preserved-rig comparison and Godot import
results are in `counts-and-log.json` and `godot/`. All required primitives have
UV0, normals and tangents; the three opaque atlases use the same image for AO
and metallic/roughness. No skins, Draco or merged-static-body substitute.

Godot 4.7.2 fresh import and runtime checks pass: all 28 sections independently
posable, no surfaces without tangents, and all three opaque materials retain
albedo/normal/AO/metallic/roughness textures. The inspected native rest-pose image
is `godot/godot-import-pose.png` (1280×720). Its llvmpipe capture log has one
unsupported V-Sync driver warning; no import or script error.

## Judged staging and value

`captures/r2-full-body.png` and `captures/r2-head-closeup.png` are the judged
captures. Blender **4.5.14 Cycles**, CPU (Linux), adaptive threshold 0.01,
384 maximum samples, denoising, 1920×1080. Same R1 neutral key/fill/rim rig,
plain light-grey camera backdrop, shadow-catcher contact shadow and compositor
fog glow. The cameras are pinned to **R1 geometry's original framing**, not
re-fitted to flatter the new asset. Crest height was kept within that framing.

Reference background was sampled: clear top-right/left/background regions have
median RGB approximately (194,195,192), consistent with the owner's approximate
#C1C1BF target. R1's inherited camera-background rig is unchanged for comparison.
Its rendered background is approximately (191,191,190); no dark-grey staging.

Full-body median mean-RGB luminance is **79** (R1 **90**, reference **79.7**).
R2 p25 / median / p75 = **55.3 / 79 / 122**; teal pixels **1.90%**.
Thus the dark value family is retained without darkening the staging.

The image statistic uses R1's backdrop-difference mask and mean RGB luminance;
it includes contact shadow and is not a perfect semantic object mask. Definition
and percentiles are recorded in `image-stats.json`.

## Self-checks, recovery and remaining gaps

- Initial preview caught blocked lenses, false diagonal wear, coarse pitting and
  skull poke-through. These were corrected before the final bake. Historical
  previews are explicitly labeled and are **not** judged images.
- Initial Windows GPU and CPU jobs failed under memory pressure. Only this
  order's failed process was stopped. The job was moved to Linux CPU Cycles;
  no competing workload or configuration was changed. A gateway restart was
  recovered without duplicating a running job.
- The geometric panel grammar remains more regular than the reference's
  intricately notched, interlocking shells. Module grille slats are simpler than
  the reference's fine diamond screens; the measured uncapped study above makes
  that trade-off explicit.
- The head/muzzle and jaw are a clean procedural interpretation, not an exact
  reconstruction of the reference. The crest retains a three-across arrangement.
- The plated tail still ends in a stylized point rather than the reference's
  rounded miniature-head-like tip.
- One shared textured module necessarily repeats its weathering. Axial rolls
  change the read, but there are no per-instance unique weathering textures.
- No claim is made about gameplay performance, animation on a new path, or
  hardware-GPU rendering. Godot captures are import/rest-pose evidence only.

## Reproduction / source

`source/build_r2.py` + `source/weather.py` start from the shipped R1 packed blend
on each run. See `source/run-build.sh`; `R2_MODE=geometry|preview|final` provides
clearly separated debugging, 32-sample previews and production renders.

Authorized input blend: `C:\Users\Moore\forge-r1\out\snake-sectional-r1.blend`.
Working Linux copy and packed final blend: workspace `snake-r2-work/` (not
committed). Canonical shipped asset is `snake-sectional-r2.glb`.

`godot/run.sh` creates a fresh temporary project with the delivered GLB, imports
it, checks materials/rig/tangents, and captures a native 1280×720 software-rendered
rest pose. Its `.godot` cache is not a delivery dependency.
