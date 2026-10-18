# Forge Snake — Round 4 Arm A / persistent session

Order: `op-forge-snake-r4a-20261018`. Corrected rerun deadline: **2026-10-18 07:15 CDT** (the producer's 05:38 amendment supersedes the verbatim old deadline).

## Provenance and continuity

Built by importing **`benchmarks/forge-snake-r3/snake-sectional-r3.glb`** from producer-verified commit `7a3a2c7c3af1f4d7803ad31753231d5f728043b0`, branch `forge-snake-r3-20261018`. The retained local R3 blend supplies **staging only**: all its asset meshes are deleted before canonical GLB import. No regeneration, Hunyuan, other entrant branch/workspace, or other Round 4 arm was used. Own `REFERENCE.png` and own R3 full/head captures were actually viewed in-session before editing. R3 panel: MATCH 4.5 / QUALITY 4.5, gate FAIL. R4 is not yet independently scored.

## Changes mapped to the five panel gaps

1. **Material/color.** Replaced charcoal finish with neutral weathered silver-grey steel; baked physical-panel tone variation into inherited UV0. Directional local -Z grime originates at chosen hardware sites, with finite fine diagonal scratches and true geometric edge exposure. No uniform brown noise/camouflage. Retained baked occlusion in ORM R; varied roughness/metalness. Reduced inherited normal-map strength to 0.35 so micro-detail does not read as deep, crumpled plate geometry. Constant fitted-hardware finishes were balanced separately from sRGB albedo textures.
2. **Glowing joints.** Replaced four 30-degree hairline dashes with a **36-sided, 360-degree cyan emitter ribbon**, 0.066 local units wide versus 0.010 in R3. The original 144-triangle dark housing remains; the emitter sits just outside its central surface, between dark edges. Every one of the 29 emitter nodes uses the shared full-ring mesh. The two embedded tail bands are also full circumference and wider. Bright cyan Principled emission, with identical tight compositor bloom for baseline and candidate captures.
3. **Head proportions.** Reworked the existing plated skull, vents and fasteners together: X shortened by 21%, with an additional compressed/blunted frontal muzzle; Y broadened by 12%, increasing toward the front; slight height restoration. Kept fitted layered skull topology and unchanged Head node transform/hierarchy. No replacement head base.
4. **Eye.** Replaced only the meshes on the same two inherited optic nodes: circular flush assemblies rather than deep oval funnels. Large bright green iris ring and core, darker green optical face, 24 physically modeled radial ticks per eye, concentric machined bezel. Moved the optic faces outward to sit at the broadened cheek surface; not a tiny light at the back of a socket. No extra mesh nodes.
5. **Segment detail, fins and tail.** Removed R3's X crosswires and redundant crown add-ons. Added three physical crossbars over each inherited six-slat cassette, forming modeled lattice; moved each entire frame/slat/backing assembly clear of the lap plate. Exposed the inherited modeled telescoping pistons and gave rods/collars clean contrasting machined finishes; removed distracting inherited albedo patches from those parts. Kept real shell layers and fasteners. Shortened and blunted the crest blades, fitted raised inset plates, and raycast-seated six crest rivets. Removed the tail's distal pointed armor row; built a blunt stepped eight-sided terminal with plated fins, seated bolts, raised cooling slats and twin telescoping pistons. Tail is still one rigid inherited node.

## Binary budgets and hierarchy

Independent standard-library GLB parse: `binary-validation.json`; binary-to-binary hierarchy comparison: `rig-comparison.json`.

| Part / invariant | Final | Contract |
|---|---:|---:|
| Head incl. both optical assemblies | 11,832 tris | 10,000–18,000 |
| Shared segment mesh | 1,384 tris | — |
| Joint housing + emitter | 144 + 72 = 216 tris | — |
| Segment + joint | 1,600 tris | ≤1,600 |
| Tail | 2,527 tris | — |
| Tail + joint | 2,743 tris | ≤3,000 |
| Full instanced assembly | 59,375 tris | 30,000–60,000 |
| Segment nodes / distinct segment meshes | 28 / 1 | exactly 28 / 1 |
| Joint housing/emitter pairs | 29 | exactly 29 |
| Mesh nodes | 90 | exactly 90 |

Every primitive has POSITION, NORMAL, TANGENT and UV0. Every exported material has packed occlusion/roughness/metalness with AO and MR resolving to the same embedded image. Principled-only export, +Y up, no skins, no Draco. Original names, parents and local transforms are preserved within numerical exporter tolerance; see exact measured delta in rig comparison.

## Eye-driven checkpoints / what changed after self-check

- Viewed the reference and R3 full/head captures before the build; then viewed full/head iterations A, B, C, D, E, F, G and final checkpoints during the pass.
- First budget check stopped export at **1,608** tris per segment+joint. An early pass temporarily reclaimed the 32-triangle internal segment tube. Once brightened, the gaps made that tube useful visually, so the final pass **restores the original tube** and balances the budget with a 36-sided/72-triangle emitter instead of the 48-sided/96-triangle prototype. Removed the obsolete 86-triangle R3 X/crown add-ons, not visible inherited shell/fastener detail. Final segment+joint is exactly 1,600 triangles.
- Preview A: silver was too uniformly bright; eye was a blank green disc. Rebuilt the weathering contrast and panel tones, added a darker iris face, concentric emission and physical ticks. Reduced emissive strength while retaining clearly bright full cyan rings.
- Close-up caught a bezel/head intersection: seated the circular optic assembly outward against the broadened cheek, removing the clipped lip.
- Isolated module preview exposed inherited lap-plate intrusion into cassette slats. Classified welded components on a COPY, then translated whole frame/slat/backing assemblies together; did not discard guessed slat faces. Increased lattice to three crossbars per cassette.
- Fins and tail initially read as bright flat slabs because constant linear colors were too bright beside sRGB textures. Balanced their finishes, fitted fin inset plates and surface-seated rivets, and added actual terminal piston geometry. A final seating check then placed each cooling slat directly on its actual stepped cap surface and added two piston end brackets; candidate production rendering was stopped and restarted for this correction.
- Reduced inherited normal-map amplitude for micro-detail; rechecked the final full/head/module/tail views before production capture.
- Historical failed/obsolete build logs are explicitly separated from final successful evidence. The unqualified shell alias `python` was unavailable; local helper scripts use installed `python3`. Required Windows Blender and Godot executables were used throughout.

## Capture discipline and engine evidence

Judged images: `captures/r4-full-body.png` and `captures/r4-head-closeup.png`. Paired untouched R3 baseline images and matching active-setting JSON records are included. **1920×1080 Cycles CPU, 256 maximum samples, adaptive 0.01, OpenImageDenoise**, shaped neutral key/fill/rim and soft contact shadow. Cameras, orthographic framing, lights, world, color management and compositor are identical between baseline and after. Reference background sampled in `reference-background-sample.json`; owner target #C1C1BF. No camera re-fit for the shorter head.

Packed ORM R is multiplied into Blender review albedo **after canonical GLB export**; standard glTF occlusion stays separate in the deliverable. Glare uses actual Blender 4.5 node sockets: Threshold 0.4 / Strength 0.25 / normalized Size 0.125, FOG_GLOW. Lower-sample `PREVIEW-*` images are iteration evidence only. Godot Compatibility screenshots are import/pose evidence only, never judged captures.

Required host executables: `C:\Users\Moore\Blender\blender-4.5.14-windows-x64\blender.exe` and `C:\Users\Moore\Godot\Godot_v4.7.2-stable_win64_console.exe`. Files stay on the continuing session's Linux volume, accessed through the same WSL UNC path used in R3. Cycles CPU avoids contending for the host's 8 GB GPU; no render-engine substitute.

Godot: fresh 4.7.2 editor import, automated rigid-segment pose/material/tangent audit, and native 1280×720 capture. Exact final outcome, process exits, binary hash and image manifest are recorded in `counts-and-log.json` and `godot/` logs.

## Remaining limits

The hard one-shared-mesh contract preserves repeated module geometry and the inherited R3 rest-pose hierarchy. Lattice, layered panels, bolts, piston sets, fins and terminal hardware are modeled, but this constrained rigid asset does not reproduce every fine woven-mesh or small fitting in the reference. No claim of a new panel score is made.

## Final binary / engine verification

- Final GLB SHA256: `8819c6ef236c1cb9496a52216533566ef23bbd600dd22f68219b8da80fb9e457`.
- Godot **4.7.2 PASS**: fresh editor import, rigid pose/material/tangent check, and native screenshot; process exits **0 / 0 / 0**. Imported 59,375 tris, 90 mesh nodes, 28 independently posable segments on one mesh, 29 housing/emitter pairs, no missing tangents or primary texture/AO resources.
- Maximum hierarchy/local-transform component delta from canonical R3: `4.917383193969727e-07`; no differences above 1e-5.
- Final canonical input SHA256: `c34f3b69ecc48278263e7ea691b5011c65bb07837b7721fc29f39248a5ded34a`.

Paired production staging/settings check: **PASS**. Clear top-right rendered backdrop medians: full-body RGB **195/195/194**, head RGB **195/195/195**, identical to each corresponding untouched R3 baseline (maximum paired channel difference **0**). Final capture/settings/hash manifest checks: **PASS**. The final full/head production images and module/tail/terminal checkpoints were actually viewed before delivery.
