# FORGE R1 — snake sectional assembly, finish + modeled-detail pass on FIX2

Order `op-forge-snake-r1-20261017` · seat studio-3d (Forge) · executor claude-cli/claude-opus-5-5.
Built from the FIX2 `.blend` in the pack (pack SHA-256 verified). The build script is `source/forge_r1.py`, and it is rerunnable:
`FORGE_MODE=preview|final`, base = FIX2 blend.

Deliverables in this folder:
- `snake-sectional-r1.glb` (SHA-256 `4def595e…7b81cc`)
- `captures/r1-full-body.png` and `captures/r1-head-closeup.png`: judged captures
- `previews/` contains the labeled 480p self-check previews
- `godot/` contains the import and scene-check evidence
- `counts-and-log.json`

## What changed versus FIX2, and why (mapped to the panel gaps)

1. **Finish: dark weathered gunmetal (gap 1).** All armor atlases were regenerated.
   - **Albedo** runs sRGB ~.08–.15 with per-plate variation. The mean is .139 for the head and .138 for the segment; FIX2 was .40–.70.
   - **AO** is real ambient occlusion, baked per section in Cycles into ORM R. It replaces procedural seam AO.
   - **Grime and rust** pool in the crevices, driven by the baked AO and by concave creases. A warm rust bleed sits in the cavities.
   - **Edge wear** sits only on true convex edges. It is computed per texel as the distance to sharp convex mesh edges, from dihedral angles, and broken up with low-frequency noise.
   - **Metallic** is lowered (~.5) so the plates stop mirroring the light backdrop as silver.
   - **Trim materials** (machined edges and rims, carbon, graphite) were darkened into the same value family.
2. **Printed detail removed; key detail modeled (gap 2).**
   - The procedural plate grid, the printed fasteners and the printed diamond-mesh vent decals are all gone from the atlases. Seams now come from the modeled plates only.
   - The shared segment module gained modeled detail: two side piston knuckles (6-sided) and five raycast-seated bolt heads.
   - Normal maps now carry only micro-detail: pitting and two scratch sets.
3. **Rings are thin recessed seams (gap 3).** The emitter was rebuilt to follow the housing's own 12-gon groove: 4 arcs of 60° with 30° gaps, seated in the groove floor (r .514–.528, width .034). It is 48 tris per joint (FIX2: 120). Emission was lowered and the housing lips darkened. The result reads as short teal arcs in dark recessed gaps.
4. **Crest fins (gap 4).** The three FIX2 slab islands and their feet were deleted. In their place are three modeled swept fins: a concave 7-point profile, 0.024 thick, a strong rearward rake and pointed tips, with the outer two at 0.82×. Each sits on a bolted machined foot.
5. **Head and tail/body (gap 5).**
   - **Head:** the muzzle ahead of the lens was stretched 1.75× with a smooth onset, narrowed and lowered toward the tip, and the boxy cheek cladding behind the eye was slimmed 12%. The lens is untouched: all lens child nodes were asserted identical to FIX2.
   - **Body taper:** segment cross-section scale goes 0.93 (neck) → 1.0 (coil) → 0.64 (last segment) as node scale on the shared mesh. Segment lengths are unchanged, so no gaps open.
   - **Variation:** each segment node is rolled about its axis (0/±7–24°/168–192°), so the grille, junction box, pistons and bolts land differently along the body. Joint centres are kept on the chain.
   - **Tail:** the organic Hunyuan tail was replaced by modeled mechanical sections: one full module copy (0.80 length) and one decimated module copy (0.68). They are joined by two inline seam joints (housing + arc emitter, tapering), and end in an 8-sided missile cone with three small swept fins.

## Tri counts (exported GLB, instanced; Godot-confirmed)

| Part | FIX2 | R1 | Limit |
| --- | ---: | ---: | ---: |
| Head (incl. unchanged lens, 3,104) | 12,945 | **12,861** | 10,000–18,000 |
| Shared segment | 1,302 | **1,392** | — |
| One joint (housing 144 + emitter 48) | 264 | **192** | — |
| Segment + joint | 1,566 | **1,584** | ≤1,600 |
| Tail + joint | 2,204 | **2,634** | ≤3,000 |
| **Assembly total** | 58,997 | **59,847** | 30,000–60,000 |

**Nodes:** 28 rigid `Segment_*` nodes on one shared mesh, 29 joints (28 segment joints + tail joint; 29 housing + 29 glow nodes). There are 104 mesh nodes in total.

**Format:** tangents on every primitive. ORM packed, with occlusion and metallic-roughness on the same image. Principled-only materials, no Draco, no skins, glTF +Y up. The only glTF extensions are the transmission and emissive_strength extensions FIX2 already used, for the lens cover and the emitters.

## Godot 4.7.2 (ed1daf0bf, this host)

- **Import:** fresh-cache headless `--import` exits 0 with no errors or warnings (`godot/import.log`).
- **Scene check** (`godot/check.gd`, output in `godot/check.log`), which exits clean with 0 errors:
  - loaded; 104 MeshInstance3D; **59,847 triangles**
  - 28 segment nodes → 1 distinct mesh
  - 29 housing / 29 glow nodes
  - 0 surfaces without tangents
  - no Skeleton3D
  - all 28 segment nodes independently posable (rotated each; transforms changed)
  - all 11 materials import as StandardMaterial3D

## Judged captures

The FIX2 staging rig was used unchanged:
- #C1C1BF camera backdrop via Light Path mix
- key 2400 / fill 450 / rim 2300, neutral
- shadow-catcher contact shadow
- ORM-R AO multiplied into the render materials after export
- compositor fog-glow on emissives
- same camera angles and auto-framing

Render settings: Cycles, adaptive sampling (threshold 0.01, max 384), OpenImageDenoise, indirect clamp 3.0, light tree, 1920×1080.

**Disclosed change:** the Cycles device is the host's RTX 3070 Ti (OptiX) instead of CPU. All look-affecting settings are identical.

Previews in `previews/` are 32-sample 480p iteration renders. They are labeled `PREVIEW-` and are not judged captures.

Asset luminance against the matched backdrop (0–255; measured with `stats.py` logic):

| | p25 | median | p75 | teal px |
| --- | ---: | ---: | ---: | ---: |
| REFERENCE | 35 | 80 | 142 | 2.2% |
| FIX2 | 93 | 141 | 169 | 6.4% |
| **R1** | 63 | **90** | 129 | **1.8%** |

## Mid-build self-checks — what they caught and what I changed

I kept the reference and my own renders in view during the build. Six preview iterations ran before the finals; all are in `previews/`.

- **it1:**
  - **Armor still silver.** At albedo sRGB ~.30 the render median was 112 against the reference's 80. The cause was the metallic surfaces mirroring the bright backdrop. Fix: lowered metallic to ~.5 and darkened albedo in steps (.25 → .15 → .115 → .095 → .078 base).
  - **Printed bricks.** The procedural plate-grid seams with rust lines read as a printed brick pattern across the head, which is exactly gap 2. Fix: removed all procedural seam grids and let the modeled plates carry seams.
  - **Crest still a block.** My vertex filter only moved 39 vertices. I found the fins were 28-vertex slab islands. Fix: deleted them and modeled new swept fins.
  - **Rings evenly dashed.** Fix: changed the arc count and gaps.
- **it2 (AO-bake build):**
  - **Bake rejected.** The Cycles bake was rejected because the scene had `bake.use_selected_to_active` on. Fix: disabled it for the bake.
  - **Carbon-fibre checker.** Edge wear covered whole plates in a diagonal checker, because on low-poly plates every vertex counts as "convex". Fix: replaced the per-vertex convexity with a per-texel distance to sharp convex edges.
  - **Tail still organic.** The tail close-up showed the crumpled, organic Hunyuan tail. Fix: rebuilt it from modeled sections with a missile tip.
- **it3–it4:**
  - **Rings only dots.** The joint close-up showed the rings only as dots. Cause: each arc had two angle samples, so it was a straight chord sunk inside the 12-gon housing, and only its ends poked out. Fix: rebuilt the emitter on the housing's 12-gon. This also cut it to 48 tris, which funded the modeled module detail.
  - **Stitched edge wear.** Edge wear read as dashed white stitching. Fix: made it thinner, softer and lower-frequency.
- **it5–it6:**
  - **Glow and colour cast.** Rings were slightly hot for "dim to moderate", so I lowered emission (5.5 → 4.2) and width (.044 → .034). The armor had a blue cast (R−B −4.9 against the reference's +1.2), so I warmed it slightly.
  - **Backdrop-white trims.** Trim and steel parts (tail cone, fins) mirrored the backdrop white. Fix: lowered trim metallic.
  - **Value gap traced.** The median was still ~90 against 80. I measured material area on the segment: 40% is already near-black graphite housing. The remaining brightness is key-lit armor tops under the pinned staging, so I stopped darkening the paint rather than turn the plates black.

## Known remaining gaps (my read against the reference)

- **Segment silhouette.** The segment module is still a fairly smooth cylinder compared with the reference's heavily layered shells with notched cutouts. The 1,600 segment+joint cap leaves little room; the next round should rebuild the module with layered shells rather than add parts.
- **Head base mesh.** Lumpy areas of the Hunyuan base mesh are visible between the head plates, mostly the lower muzzle and the cheek.
- **Fin layout.** The fins keep FIX2's side-by-side layout across the skull. They are not a staggered row.
- **Light trims.** Machined trim parts (pistons, grille rims, tail tip) still read a little lighter than the armor.
- **Asset value.** At a median of 90 against the reference's 80, the asset is somewhat lighter than the reference under the pinned staging.

## Host-side files (not committed)

The working `.blend` is on the host at `C:\Users\Moore\forge-r1\out\snake-sectional-r1.blend` (40 MB, packed), along with the textures and the iteration script snapshots.
