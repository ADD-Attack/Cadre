# Forge Snake Round 4 — Arm B / fresh session

Order `op-forge-snake-r4b-20261018`. Delivery branch `forge-snake-r4-fresh-20261018`.

## Provenance

Built by importing and editing the **producer-verified R3 binary GLB** at
`7a3a2c7c3af1f4d7803ad31753231d5f728043b0`,
`benchmarks/forge-snake-r3/snake-sectional-r3.glb`. Not a scratch rebuild.
An isolated worktree was created directly at that commit. No other entrant's
branch, workspace, asset or deliverable was fetched, opened or used. No session
history or other Round 4 arm context was used. No Hunyuan regeneration.

The actual reference was viewed from this seat's own copy:
`tickets/forge-snake-r1/pkg/forge-r1-pack/REFERENCE.png`.
The R3 captures were inspected as the baseline, **not** treated as the reference.
R3 published render settings provide the camera frames and studio specifications;
no untracked R3 working blend was used.

## Changes mapped to the five consensus gaps

1. **Weathered silver-grey steel.** Re-authored all three primary albedo/ORM
   atlases in geometry-local coordinates, retaining baked AO-R. Primary steel is
   substantially brighter, slightly cool-neutral silver with independent tones
   assigned to connected physical panels. Finite diagonal scratches and broken
   edge exposure reveal brighter steel. Grime/rust is confined to selected
   downward runoff anchors, not an even random brown field. Dark vent cavities
   and structural recesses stay dark. Inherited normal maps remain micro-detail;
   their strength is reduced to 0.38 to avoid overpowering the new finish.
2. **Thick continuous cyan joints.** Replaced the shared four-dash emitter mesh
   with a **360-degree, 48-sided sleeve**, axial width 0.064 (R3: 0.010), radius
   0.547 beyond the housing shoulder. Cyan authored emission strength is 4.8.
   All 29 housing/emitter pairs remain. Embedded tail emitter widths are also
   increased, operating once per unique vertex. Tight compositor fog glow is
   enabled for review captures, identically for baseline and candidate.
3. **Shorter, broader, blunt head.** Edited the inherited fitted skull, plates,
   apertures and hardware together: axial scale 0.80, cheek width 1.12, height
   1.16, additional front widening and a compressed blunt apex. Node transforms
   and attachment hierarchy are unchanged. No replacement primitive skull.
4. **Large bright green flush circular eyes.** Retained both smooth, detailed
   R3 optical meshes. Enlarged the circular luminous interior by 2.45, expanded
   its central core further, compressed socket depth and moved the optical face
   to the head side. The optical disc is physically circular in local X/Z; the
   surrounding lip is nearly circular after fitting to the shortened skull.
   Green replaces teal, with a bright core, radial ticks and steel bezel.
   The second checkpoint corrects the first preview's washed-out mint disc.
5. **Density, plated fins and mechanical tail.** The shared segment retains its
   original layered shells, fasteners and pistons. Coarse crossing struts are
   replaced with modeled fine diamond-wire vent inserts, not a grille normal
   map. Complete cassette frames/slats are raised 0.065 local units to clear
   inherited raised lap armor; a recessed dark backing lies behind the lattice. Only buried shell backs, concealed axial sleeve faces and superseded
   struts are removed to pay for emitters and lattice. The three crest fins are
   lowered, silver-plated in finish and receive seated fasteners. Added temple
   cooling hardware is joined into the existing Head mesh. The distal tail is
   shortened/broadened and gains two additional plate fins plus six raised
   cooling slats, remaining within the tail budget.

## Independent binary audit

| Constraint | R4 Arm B | Hard limit |
| --- | ---: | ---: |
| Full assembly, instanced triangles | **59,925** | 30,000–60,000 |
| Head, including both optics | **12,416** | 10,000–18,000 |
| Shared segment | 1,350 | — |
| Joint housing + emitter | 240 | — |
| Segment + joint | **1,590** | ≤1,600 |
| Tail alone | 2,749 | — |
| Tail + joint | **2,989** | ≤3,000 |
| Segment nodes / shared segment meshes | **28 / 1** | 28 / 1 |
| Housing / emitter nodes | **29 / 29** | 29 / 29 |
| Mesh nodes | **90** | 90 |

All primitives contain position, normal, UV0 and tangent attributes.
All **14 materials** have packed ORM; independently verified AO and MR texture
references resolve to the same embedded image source. No skins or Draco.
Only optional glTF extension is `KHR_materials_emissive_strength`.

`rig-comparison.json` compares every R3 node to the exported R4 node. All 90
names and parents remain, with no transform difference above 1e-5.
GLB: 18,876,648 bytes; SHA-256
`ed4c8874be4938e1146f5af46c9c93249e3fdc78cb989d1d2c853d858abbcf62`.
See `glb-validation.json` and `counts-and-log.json` for exact binary counts.

## Capture discipline and actual-eye checkpoints

The actual reference and R3 full/head views were viewed in-session before the
build. Own `PREVIEW-b-*` full/head renders were viewed during the build; the eye
was then changed from a pale mint disc to a greener optic with a larger center,
physical panel tone variation was added, inherited normal strength was reduced,
and crest fasteners added. `PREVIEW-c-*` is the second checkpoint; its head view caught floating crest fasteners.
   Build d seats those fasteners by raycasting against the actual fin surfaces,
   adds sparse etched scratch contrast and widens panel-tone variation.
   `PREVIEW-d-*` checked the seated fasteners. Its module-detail view then caught
   armor/cassette overlap hidden at full-body scale. The final g pass lifts
   complete cassette assemblies and adds recessed dark backing faces, so the
   lattice is not intersected by the raised lap armor. `PREVIEW-g-*` and
   `PREVIEW-g-detail-*` are the final checkpoints; d module detail is rejected
   historical evidence, not the delivered geometry. Previews are
32-sample Cycles at 1152×648 and are **not judged captures**.

Final review images are `captures/r4-fresh-full-body.png` and
`captures/r4-fresh-head-closeup.png`. Paired `baseline-r3-*` images import the
untouched R3 GLB into exactly the same stage. Camera transforms and ortho scales
are copied unchanged from the published R3 settings, never refitted for R4.

Blender 4.5.14, **Cycles CPU**, 1920×1080, 256 maximum samples, adaptive threshold
0.01, OpenImageDenoise; shaped neutral key/fill/rim, plain reference-matched
light-grey background, soft shadow catcher and real ORM-R multiplication in
Blender review shading. Canonical GLB is exported **before** that review-only AO
multiply. Glare uses active input sockets: Threshold 0.4, Strength 0.25,
normalized Size 0.125, FOG_GLOW. All four production images were opened and visually inspected in-session.
Production paired setting equality, expected active glare sockets, 1920×1080
dimensions, per-image hashes and sampled background corners all pass; results
are recorded in `captures/capture-verification.json`.

The top-right clear reference background was sampled, not inferred from R3:
median encoded RGB 194/195/192; the owner's staging target is #C1C1BF. The
reconstructed studio renders a clear corner about 196/196/195 after AgX/bloom,
matching the published R3 studio read. See `reference-background-sample.json`.

## Godot evidence

The first evidence-script rename accidentally changed the `Vector3` token; the
parse error was fixed before rerunning the fresh pipeline.

**PASS — Godot 4.7.2:** 59,925 triangles, 90 mesh instances, 28 independently
posable segments on one mesh, 29 housings + 29 emitters, zero missing tangent
surfaces, and retained albedo/normal/AO/roughness/metallic on all three primary
materials. Native 1280×720 capture saved successfully (error 0) and was viewed.

`godot/` contains the isolated Godot 4.7.2 evidence project, fresh import/check/
capture logs and native rest-pose screenshot. Compatibility capture is **import
and pose evidence only**, not a judged capture. The check traverses all mesh
instances, verifies tangents/textured channels/shared module counts, and rotates
all 28 segment nodes independently before discarding the test scene.

## Self-check limits

The inherited coil pose and module silhouette are intentionally retained to
preserve the R3 hierarchy and one-shared-mesh contract. It remains more regular
and less densely hand-panelled than the reference; shared-module texture wear
repeats. The mechanical tail is improved, not an exact miniature reproduction
of the reference tip. No blind-panel score, gate pass or acceptance is claimed.

## Reproduction

See `source/README.md`. Source scripts, texture atlases, previews and audit logs
are included. The packed working `.blend` is local/ignored; the canonical
review/import asset is `snake-sectional-r4-fresh.glb`.
