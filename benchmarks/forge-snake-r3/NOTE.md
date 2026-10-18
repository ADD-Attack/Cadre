# Forge Snake Round 3 — Decision 26 bake-off

Order `op-forge-snake-r3-20261018` · Forge / studio-3d · continuing session.
Branch `forge-snake-r3-20261018`.

## Provenance and corrected panel baseline

Built directly from producer-verified R2 GLB on `snake-r2-sol-20261018` at
`52c96999907cb6a34ae41116092d97b9b4141024`. **Not rebuilt from scratch.**
R2 nodes, placements, primary plates, sockets, module, pistons and tail are the
starting geometry. No Hunyuan generation and no other entrant's branch,
workspace or deliverables were used. Forge's own R1 file supplies staging only;
its asset objects are deleted before R2 import.

Producer correction applied: resolved R2 medians are **MATCH 5.0 / QUALITY 4.5**,
not the superseded 5.5 / 5.0. No panel pass or acceptance claim is made here.

## Changes vs R2, mapped to the six consensus gaps

1. **Directional wear on dark gunmetal.** Removed the old broad, brown noise
   corrosion field rather than merely darkening it. Re-authored the albedo and
   roughness/metallic channels in part-local coordinates: 14 selected head runoff
   anchors, 6 module anchors, 5 tail anchors; narrow downward rust/grime streaks;
   finite drag scratches; broken, sharp-edge-confined abrasion and bright edge
   exposure. Recess tint remains neutral. Original ray-baked AO is retained in
   ORM-R and is not baked into the exported albedo. Normal maps remain inherited
   micro-detail. New albedo/ORM atlases are 1536²; inherited normal-map resolutions
   remain unchanged. Weathering repeats on the one shared module, as required.
2. **Longer, lower skull and thinner crest.** Edited the actual R2 fitted skull,
   plates, apertures and hardware: local length ×1.13, cheek width ×0.94 and skull
   height ×0.82, with corresponding socket placement. Crest blades are narrowed
   axially, roughly half-thickness, reduced vertically and raked back; feet and
   fasteners remain fitted. Outer plate UVs are retained. Exactly 1,000 triangles
   were reclaimed from deeply concealed skull-liner faces to fund body hardware;
   visible outer armor and smooth optical tessellation are preserved.
3. **Small recessed teal core.** The luminous inner optical assembly is 66% of
   the old radius and retreats another 0.035 local units. The inherited outer
   aperture stays fitted to the plates. Socket/rim/glass are darkened; the core and
   fine optical ticks are explicitly teal, not amber. Smooth original optical
   roundness was restored after rejecting a faceted budget trial.
4. **Modeled module layering and hardware.** Edited the existing shells to add
   shoulder relief; raised and notched the four inherited lap tiles. Added a
   separate concave interlocking crown shell with real sidewalls, four physical
   cooling crosswires and one seated captive screw. Retained all R2 modeled
   cooling slats and twin piston assemblies. Additions cost **86 triangles per
   shared module**, not normal-map or albedo-printed substitutes.
5. **Recessed hairline seams.** Joint emitter axial width is 0.010 vs 0.034;
   outer radius is 0.520 vs 0.528. Four shorter 30-degree arcs replace the old
   60-degree arcs, reducing visible coverage and emitter count to 24 triangles.
   Authored emission strength is 1.7; exported peak emissive RGB radiance is
   0.714 vs R2's 2.94. The dark housings are retained. Embedded tail
   emitters are also thinned. All 29 joint housing/emitter node pairs remain.
6. **Plated, finned tail.** Preserved the R2 plated taper, gently broadened its
   distal plates and added three swept guard fins plus six seated fasteners
   (**108 triangles**). Fin faces are dark gunmetal with steel sidewalls. The tip
   remains a stylized plated point, not an exact miniature-head reconstruction.

## No-regress audit (binary GLB, not just Blender statistics)

| Part | Verified R2 | R3 | Contract |
| --- | ---: | ---: | ---: |
| Head including both optics | 13,152 | 12,152 | 10,000–18,000 |
| Shared segment | 1,336 | 1,422 | — |
| Joint: housing + emitter | 192 | 168 | — |
| Segment + joint | 1,528 | 1,590 | ≤1,600 |
| Tail alone | 2,561 | 2,669 | — |
| Tail + joint | 2,753 | 2,837 | ≤3,000 |
| Full assembly, instanced | 58,689 | **59,509** | 30,000–60,000 |

28 rigid segment nodes reference **one** mesh. 29 housing nodes + 29 emitter
nodes; 90 mesh nodes total. No merged static assembly. All primitives have UV0,
normals and **tangents**. Five opaque materials use packed ORM (AO and
metallic/roughness resolve to the same image). Principled-only metal/roughness
materials; no skins, no Draco; standard glTF +Y up export. Only optional glTF
extension: `KHR_materials_emissive_strength`.

Independent hierarchy/transform comparison finds all 90 input nodes preserved,
parents unchanged, maximum transform-component delta 8.35e-7 (tolerance 1e-5).
See `glb-validation.json`, `rig-comparison.json`, and `counts-and-log.json`.

GLB: 18,121,464 bytes; SHA-256
`c34f3b69ecc48278263e7ea691b5011c65bb07837b7721fc29f39248a5ded34a`.

## Judged captures and staging

`captures/r3-full-body.png` and `captures/r3-head-closeup.png` are the judged
images. Paired `captures/baseline-r2-*` images show the untouched R2 GLB in the
**identical** rig and frames. Original R2 camera positions, rotations and ortho
scales are fixed; the camera is not re-fitted to flatter the edited asset.

Blender **4.5.14**, **Cycles CPU**, 1920×1080, **256 maximum samples**, adaptive
noise threshold 0.01, OpenImageDenoise on. Plain reference-matched light-grey
backdrop, unchanged shaped neutral key/fill/rim, real ORM-R AO multiply in render
materials, soft shadow-catcher contact shadow, tight, subtle compositor fog glow (threshold 0.65, size 6, mix -0.75),
applied identically to R2 baseline and R3 so even the dimmed seams get bloom. Camera backdrop uses the owner's #C1C1BF target. Actual top-right reference
sample median is RGB 194/195/192; see `reference-background-sample.json`.
Workbench was not used. Godot Compatibility images are import evidence only.

## Actual-eye checkpoints and corrections

The reference and both R2 judged images were opened and viewed in-session
**before building**. Own full-body/head previews were opened and viewed during
iteration, then the production captures were checked before delivery.

- **a:** lower/longer skull, small recessed optics and restrained seams improved
  the silhouette, but the finish read too clean and body layering too faint.
  Strengthened finite drag scratches and edge-confined directional abrasion;
  raised/notched existing lap tiles and added physical crown/cooling hardware.
- **d:** inspected close-up exposed large shading facets after trial optical
  decimation. Rejected that trial, restored smooth optics and moved the budget
  reduction into the concealed liner. Also reduced the still-oversized crest.
- Geometry check caught repeated scaling of shared tail-emitter vertices; fixed
  it to operate once per unique vertex before the delivered build.
- Binary export audit caught duplicate imported AO/MR texture nodes pointing at
  different images after replacement. Fixed every node to share the same new
  packed ORM image; final independent packing audit passes.
- The **f** head checkpoint caught comb-like scuff bands; lowered their frequency
  and made abrasion sparse in **g**, without restoring brown mottling.
- The detail check also caught overly bright, slab-like crown hardware; in **h**,
  darkened the faces and added a physical bevel, funded by two optional screws.
- Final artifact audit also caught the old zero-byte failed screenshot being
  scanned as an input by Godot. Removed it and repeated the fresh import/check/
  capture pipeline; the run script now removes its generated screenshot before
  import.
- Final **h** full-body/head plus module/tail detail previews and judged captures
  are the final visual self-check evidence. Historical previews are labeled;
  they are not judged captures and are not alternate deliveries.

## Host recovery, without changing the required tools

The initial Git fetch failed on a stale configured CA path; the same authorized
branch was fetched with the host CA bundle. OPTIX failed under the 8GB GPU's
existing memory load; production uses CPU **in the same required Windows Blender
executable**, with Cycles production settings unchanged. A concurrent processing
attempt hit host RAM pressure; the texture working set was reduced and new albedo/ORM
atlases were reduced to 1536² while preserving the original normal maps.

C: then filled completely, causing a checkpoint save and initial Godot PNG write
to fail. Only this order's checkout/output was moved to this workspace's Linux
volume and accessed through its WSL UNC share by the same Windows applications.
No other workload or files were stopped, changed or deleted. Final runtime and
capture outcome is recorded below and in `godot/`.

## Godot 4.7.2 outcome

**PASS** — fresh Windows Godot 4.7.2 import and loaded-scene checks: 59,509
triangles, 90 mesh instances, 28 segments independently posable on one shared
mesh, 29 housings + 29 emitters, zero missing tangent surfaces, and all three
opaque atlas materials retaining albedo/normal/AO/roughness/metallic textures.
Native 1280×720 rest-pose capture saved successfully (error 0) and was viewed.

The first recovered capture exposed stale shader-cache header errors after C:
filled. Disabled shader caching **only in this evidence project's settings**;
final import/check/capture logs contain no errors. No global cache was deleted.

Final validation result is recorded in `godot/check.log`, `godot/import.log`,
`godot/capture.log`, the native `godot/godot-import-pose.png`, and the summary in
`counts-and-log.json`. The required host executable is
`C:\Users\Moore\Godot\Godot_v4.7.2-stable_win64_console.exe`.

## Remaining limits

This is still a regularized interpretation of the reference: module weathering
repeats, the skull's panel grammar is simpler, cooling crosswires are coarser than
fine diamond mesh, and the tail remains pointed. No claim of panel acceptance,
new gameplay animation, or in-game performance is implied.

Source/reproduction instructions are in `source/README.md`. The canonical
artifact is `snake-sectional-r3.glb`; the working packed blend is local/ignored.
