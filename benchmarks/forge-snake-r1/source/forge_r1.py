"""FORGE R1 finish + modeled-detail pass on the FIX2 snake (op-forge-snake-r1-20261017).

Opens the FIX2 .blend (already staged: #C1C1BF camera backdrop mix, shaped
key/fill/rim, shadow catcher, compositor fog glow), applies the R1 asset
changes, exports, and renders with the FIX2 staging unchanged.

FORGE_MODE=preview -> 854x480, 32 samples, labeled iteration previews.
FORGE_MODE=final   -> exports + Cycles production finals (1920x1080, adaptive, 384 max, denoise).
Tunables come from env so self-check iterations don't edit code paths.
"""
import bpy, bmesh, math, os, json, random
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from math import pi, sin, cos
from pathlib import Path

O = Path(os.environ['FORGE_OUTPUT']); O.mkdir(parents=True, exist_ok=True)
MODE = os.environ.get('FORGE_MODE', 'preview')
PREVIEW = MODE != 'final'
TAG = os.environ.get('FORGE_TAG', 'it1')
P = json.loads(os.environ.get('FORGE_PARAMS', '{}'))
def prm(k, d): return P.get(k, d)

bpy.ops.wm.open_mainfile(filepath=os.environ['FORGE_BASE'])
sc = bpy.context.scene
head = bpy.data.objects['Head']; body = bpy.data.objects['Segment_00']; tail = bpy.data.objects['Tail']
eyes = [o for o in head.children if o.type == 'MESH']
lens_baseline = {o.name: ([tuple(v.co) for v in o.data.vertices], [tuple(r) for r in o.matrix_basis]) for o in eyes}
catcher = bpy.data.objects['Fix2 shadow catcher (staging)']
segs = [bpy.data.objects['Segment_%02d' % i] for i in range(28)]

def select(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
def triangulate(o):
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.triangulate(bm, faces=list(bm.faces)); bm.to_mesh(o.data); bm.free(); o.data.update()
def tris(o):
    o.data.calc_loop_triangles(); return len(o.data.loop_triangles)
def link_mesh(name, bm, material):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    me.materials.append(material); return o
def join_local(base, additions):
    saved = base.matrix_world.copy(); base.matrix_world = Matrix.Identity(4); bpy.context.view_layer.update()
    select(base)
    for o in additions: o.select_set(True)
    bpy.ops.object.join(); base.matrix_world = saved; bpy.context.view_layer.update()

pref = bpy.context.preferences.addons['cycles'].preferences
pref.compute_device_type = 'OPTIX'; pref.refresh_devices()
for d in pref.devices: d.use = d.type == 'OPTIX'
sc.render.engine = 'CYCLES'; sc.cycles.device = 'GPU'
steel = bpy.data.materials['Fix machined edges']; carbon = bpy.data.materials['Fix recessed carbon']
log = {}

# ============================================================ 1. HEAD: elongated skull, raked fins
A = head.data.vertices
SN0, SN1 = -1.00, -1.12          # blend zone just ahead of the lens socket (lens at x=-0.94)
SNOUT = prm('snout', 1.75)       # forward stretch of the muzzle
nf = ns = nc = 0
FIN_PLANES = (-0.39, 0.0, 0.39)
for v in A:
    x, y, z = v.co
    # --- muzzle: stretch forward, narrow and lower toward the tip
    if x < SN0:
        w = min(1.0, (SN0 - x) / (SN0 - SN1))          # 0..1 smooth onset
        w = w * w * (3 - 2 * w)
        d = SN0 - x
        nx = SN0 - d * (1 + (SNOUT - 1) * w)
        tt = min(1.0, d / 0.54)                        # 0 at onset .. 1 at old tip
        v.co.x = nx
        v.co.y = y * (1 - prm('snout_narrow', 0.16) * tt * w)
        if z > -0.2: v.co.z = z - prm('snout_drop', 0.10) * tt * w * (z + 0.2)
        ns += 1
    # --- behind the eye: slim the boxy cheek cladding
    elif x > -0.80 and abs(y) > 0.50:
        k = min(1.0, (abs(y) - 0.50) / 0.26)
        v.co.y = y * (1 - prm('cheek', 0.12) * k)
        nc += 1
head.data.update()
bm = bmesh.new(); bm.from_mesh(head.data); bm.verts.ensure_lookup_table()
seen = set(); doomed = []
for v in bm.verts:
    if v.index in seen: continue
    st = [v]; comp = []; seen.add(v.index)
    while st:
        w = st.pop(); comp.append(w)
        for e in w.link_edges:
            q = e.other_vert(w)
            if q.index not in seen: seen.add(q.index); st.append(q)
    zs = [c.co.z for c in comp]; xs = [c.co.x for c in comp]
    if len(comp) == 28 and max(zs) > 0.9: doomed += comp                       # FIX2 slab fins
    elif len(comp) == 8 and min(zs) > 0.41 and min(xs) > -0.7 and max(xs) < 0: doomed += comp   # their feet
assert len(doomed) == 3 * 36, len(doomed)
bmesh.ops.delete(bm, geom=doomed, context='VERTS')
armor_idx = next(i for i, m in enumerate(head.data.materials) if 'Gunmetal' in m.name)
trim_idx = next(i for i, m in enumerate(head.data.materials) if m.name == 'Fix machined edges')
FIN = [(-0.60, .43), (-0.42, .52), (-0.14, .67), (0.05, .80), (-0.02, .665), (-0.10, .50), (-0.17, .43)]
def prism(outline, yc, th, mi):
    top = [bm.verts.new((x, yc - th / 2, z)) for x, z in outline]
    bot = [bm.verts.new((x, yc + th / 2, z)) for x, z in outline]
    fs = [bm.faces.new(top), bm.faces.new(list(reversed(bot)))]
    n = len(outline)
    for i in range(n): fs.append(bm.faces.new((top[(i + 1) % n], top[i], bot[i], bot[(i + 1) % n])))
    for f in fs: f.material_index = mi
    return fs
newf = []
for yc, sc_, dx in ((-0.39, prm('fin_side', .82), -0.06), (0.0, 1.0, 0.0), (0.39, prm('fin_side', .82), -0.06)):
    ol = [(-0.38 + (x + 0.38) * 1.0 + dx, 0.43 + (z - 0.43) * sc_ * prm('fin_h', 1.0)) for x, z in FIN]
    newf += prism(ol, yc, prm('fin_t', .024), armor_idx)
    foot = [(-0.64 + dx, .405), (-0.62 + dx, .45), (-0.13 + dx, .45), (-0.11 + dx, .405)]
    newf += prism(foot, yc, .07, trim_idx)
bmesh.ops.recalc_face_normals(bm, faces=newf)
bmesh.ops.triangulate(bm, faces=newf)
bm.to_mesh(head.data); bm.free(); head.data.update()
nf = len(doomed)
log['head_edit'] = dict(fin_verts=nf, snout_verts=ns, cheek_verts=nc)
print('HEAD_EDIT', log['head_edit'], flush=True)

# ============================================================ 2. JOINTS: thin recessed arc seams
glow0 = bpy.data.objects['Joint_00_GlowBars']; jointmat = glow0.data.materials[0]
# Emitter follows the housing's 12-gon (vertices every 30 deg) so every arc sits evenly in the
# groove: 4 arcs x 60 deg, 30 deg gaps; outer band + both side walls, no end caps (48 tris).
W = prm('ring_w', 0.034) / 2; R0, R1 = prm('r0', .514), prm('r1', .528)
vs, fs = [], []
for arc in range(4):
    base = arc * 90
    for step in range(2):
        a0 = math.radians(base + step * 30); a1 = math.radians(base + step * 30 + 30)
        off = len(vs)
        for x in (-W, W):
            for r in (R0, R1):
                for a in (a0, a1): vs.append((x, r * cos(a), r * sin(a)))
        fs += [(off+0, off+1, off+3, off+2), (off+4, off+6, off+7, off+5), (off+2, off+3, off+7, off+6)]
me = bpy.data.meshes.new('R1 arc emitter'); me.from_pydata(vs, [], fs); me.update(); me.materials.append(jointmat)
bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces)); bmesh.ops.triangulate(bm, faces=list(bm.faces)); bm.to_mesh(me); bm.free()
for o in bpy.data.objects:
    if o.type == 'MESH' and 'GlowBars' in o.name: o.data = me
bs = jointmat.node_tree.nodes['Principled BSDF']
bs.inputs['Emission Color'].default_value = tuple(prm('ring_col', [0.02, 0.70, 0.48])) + (1,)
bs.inputs['Emission Strength'].default_value = prm('ring_em', 4.2)
bs.inputs['Base Color'].default_value = (.004, .12, .09, 1)
hb = bpy.data.objects['Joint_00_Housing'].data.materials[0].node_tree.nodes['Principled BSDF']
hb.inputs['Base Color'].default_value = (.004, .005, .006, 1); hb.inputs['Roughness'].default_value = .55

# ============================================================ 3. SEGMENT MODULE: modeled pistons + bolt heads
old = body.data
body.data = old.copy()
bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
def surf(x, ang):
    d = Vector((0, cos(ang), sin(ang)))
    hit = bvh.ray_cast(Vector((x, 0, 0)) + d * 1.2, -d, 2.0)
    return hit[0], hit[1]
adds = []
def frame(n):
    n = n.normalized(); t = Vector((1, 0, 0)); b = n.cross(t).normalized(); t = b.cross(n)
    return Matrix((t, b, n)).transposed()
for side in (+1, -1):                       # side piston knuckle at each joint end
    ang = math.radians(-18 if side > 0 else 198)
    co, nrm = surf(-0.30, ang)
    if co is None: continue
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=6, radius1=.052, radius2=.052, depth=.30)
    bmesh.ops.rotate(bm, verts=bm.verts, matrix=Matrix.Rotation(pi / 2, 3, 'Y'))
    bmesh.ops.translate(bm, verts=bm.verts, vec=co + nrm * 0.03)
    adds.append(link_mesh('R1 piston', bm, steel))
BOLTS = [(-0.33, 62), (0.31, 78), (-0.04, 102), (0.36, 122), (-0.31, -146)]
nb = 0
for x, deg in BOLTS:
    co, nrm = surf(x, math.radians(deg))
    if co is None: continue
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=4, radius1=.034, radius2=.026, depth=.03)
    bot = [f for f in bm.faces if f.normal.z < -0.9]; bmesh.ops.delete(bm, geom=bot, context='FACES_ONLY')
    bmesh.ops.rotate(bm, verts=bm.verts, matrix=Matrix.Rotation(pi / 4, 3, 'Z'))
    bmesh.ops.transform(bm, verts=bm.verts, matrix=Matrix.Translation(co + nrm * 0.006) @ frame(nrm).to_4x4())
    adds.append(link_mesh('R1 bolt head', bm, steel)); nb += 1
join_local(body, adds); triangulate(body)
log['module'] = dict(pistons=2, bolts=nb)

# ============================================================ 4. MATERIALS: dark weathered gunmetal atlases
def _hash(a, b, seed): return np.mod(np.sin(a * 127.1 + b * 311.7 + seed * 74.7) * 43758.5453, 1.0)

def bake_ao(o, size, extra=()):
    """Real ambient occlusion baked by Cycles into the section's UV layout."""
    im = bpy.data.images.new(o.name + '_r1_aobake', size, size, alpha=False); im.colorspace_settings.name = 'Non-Color'
    temp = []
    for m in {s.material for s in o.material_slots if s.material}:
        n = m.node_tree.nodes.new('ShaderNodeTexImage'); n.image = im; m.node_tree.nodes.active = n; temp.append((m, n))
    keep = {o, *extra}
    saved = {ob: ob.hide_render for ob in bpy.data.objects}
    for ob in bpy.data.objects: ob.hide_render = ob not in keep
    sc.world.light_settings.distance = prm('ao_dist', .22)
    sc.cycles.samples = 128
    sc.render.bake.use_selected_to_active = False; sc.render.bake.target = 'IMAGE_TEXTURES'
    select(o); bpy.ops.object.bake(type='AO', margin=8)
    for ob, hv in saved.items(): ob.hide_render = hv
    for m, n in temp: m.node_tree.nodes.remove(n)
    a = np.array(im.pixels[:], np.float32).reshape(size, size, 4)[..., 0].copy()
    bpy.data.images.remove(im)
    return a

def edge_flags(o):
    """Per triangle: for the edge opposite each corner, +1 sharp convex (or open plate rim), -1 sharp concave, 0 smooth."""
    bm = bmesh.new(); bm.from_mesh(o.data); bm.faces.ensure_lookup_table(); bm.normal_update()
    out = {}
    for f in bm.faces:
        vs = [v for v in f.verts]; fl = []
        for k in range(3):
            a, b = vs[(k + 1) % 3], vs[(k + 2) % 3]
            e = next((e for e in a.link_edges if e.other_vert(a) is b), None)
            if e is None or e.is_boundary or not e.is_manifold: fl.append(1); continue
            ang = e.calc_face_angle_signed(0.0)
            fl.append(1 if ang > prm('sharp', .45) else (-1 if ang < -prm('sharp', .45) else 0))
        out[f.index] = fl
    bm.free(); return out

def atlas(o, kind, size, extra=()):
    print('ATLAS_START', kind, flush=True)
    select(o); triangulate(o)
    oldm = list(o.data.materials)
    armor = {i for i, m in enumerate(oldm) if m and 'Gunmetal' in m.name}
    assert armor, kind
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.2, island_margin=.002); bpy.ops.object.mode_set(mode='OBJECT')
    ao = bake_ao(o, size, extra)
    ef = edge_flags(o)
    uv = o.data.uv_layers.active.data
    pos = np.zeros((size, size, 3), np.float32); dcv = np.full((size, size), 9., np.float32); dcc = np.full((size, size), 9., np.float32)
    hf = np.zeros((size, size), np.float32); mask = np.zeros((size, size), bool)
    for pl in o.data.polygons:
        if pl.material_index not in armor: continue
        loops = list(pl.loop_indices); vi = [o.data.loops[i].vertex_index for i in loops]
        ps = np.array([o.data.vertices[i].co[:] for i in vi]); fl = ef[pl.index]
        tex = np.array([uv[i].uv[:] for i in loops]) * size - .5
        lo = np.maximum(0, np.floor(tex.min(0)).astype(int)); hi = np.minimum(size - 1, np.ceil(tex.max(0)).astype(int))
        if np.any(hi < lo): continue
        yy, xx = np.mgrid[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]; v0 = tex[1] - tex[0]; v1 = tex[2] - tex[0]
        den = v0[0] * v1[1] - v1[0] * v0[1]
        if abs(den) < 1e-10: continue
        dx = xx - tex[0, 0]; dy = yy - tex[0, 1]
        b = (dx * v1[1] - v1[0] * dy) / den; c = (v0[0] * dy - dx * v0[1]) / den; a = 1 - b - c
        ins = (a >= -.015) & (b >= -.015) & (c >= -.015)
        sl = (slice(lo[1], hi[1] + 1), slice(lo[0], hi[0] + 1))
        pos[sl][ins] = (a[..., None] * ps[0] + b[..., None] * ps[1] + c[..., None] * ps[2])[ins]
        area2 = np.linalg.norm(np.cross(ps[1] - ps[0], ps[2] - ps[0]))
        bar = (a, b, c)
        for k in range(3):
            if fl[k] == 0: continue
            L = np.linalg.norm(ps[(k + 2) % 3] - ps[(k + 1) % 3]); hk = area2 / max(L, 1e-9)
            dk = np.maximum(bar[k], 0) * hk
            tgt = dcv if fl[k] > 0 else dcc
            tgt[sl][ins] = np.minimum(tgt[sl][ins], dk[ins])
        nq = np.round(np.array(pl.normal[:]) * 3)                 # plate identity ~ facet orientation + coarse position
        cq = np.round(np.array(pl.center[:]) * 2.5)
        hf[sl][ins] = float(_hash(nq[0] * 7 + nq[1] * 3 + nq[2] + cq[0] * 13, cq[1] * 5 + cq[2] * 11, 9.0))
        mask[sl] |= ins
    x, y, z = pos.transpose(2, 0, 1)
    macro = (np.sin(x * 21 + y * 17 + z * 12) * np.sin(z * 27 - y * 8) + 1) * .5
    fine = np.mod(np.sin(x * 1721.1 + y * 2371.3 + z * 1937.7) * 7819.2, 1)
    occl = np.clip(ao, 0, 1)
    cav = np.clip(1 - occl, 0, 1)                                        # crevice amount
    # --- dark gunmetal value field, per-plate variation (sRGB)
    value = prm('val_base', .078) + prm('val_var', .07) * hf + .03 * macro + .015 * fine
    # --- edge wear on convex edges, broken by noise
    brk = np.sin(x * 13 + y * 9 + z * 7) + .5 * np.sin(x * 37 - z * 29 + y * 23) + .25 * np.sin(x * 97 + z * 71)
    wear = np.clip(1 - dcv / prm('wear_w', .016), 0, 1) ** 1.5 * np.clip((brk + .9) / .8, 0, 1)
    value = value + wear * prm('wear', .22)
    # --- micro (normal map only carries these): pitting + two scratch sets
    height = np.zeros((size, size), np.float32)
    pit = np.sin(x * 733.7 + np.sin(z * 619.3) * 2.7) * np.sin(z * 691.3 + y * 547.9); pm = pit > .9
    height = np.where(pm, height - (pit - .9) * .004, height); value = np.where(pm, value * .7, value)
    sc1 = (np.abs(np.sin((x + z * .16 + y * .3) * 370)) > .9991) & (np.sin(z * 47 + x * 11) > .25) & (macro > .35)
    sc2 = (np.abs(np.sin((x * .83 - z * .31 + y * .5) * 880.)) > .9988) & (fine > .45)
    value = value + (sc1 * 1.0 + sc2 * .7) * prm('scratch', .20)
    height = np.where(sc1 | sc2, height - .00015, height)
    # --- grime pooling in crevices (AO-driven) + warm rust bleed
    g1 = np.sin(x * 9.1 + z * 5.3) * np.sin(y * 7.7 - x * 3.1) + .6 * np.sin(z * 13.7 + y * 4.4)
    crease = np.clip(1 - dcc / .03, 0, 1)
    grime = np.clip(cav * prm('grime_ao', 1.7) + crease * .5 + np.clip(g1, 0, 1) * .15, 0, 1) * prm('grime', .85)
    rust = np.clip(cav * 1.8 - .15, 0, 1) * np.clip(np.sin(x * 31 + z * 17 + y * 7) * .5 + .7, 0, 1) * prm('rust', .7)
    rust = rust * (1 - wear)
    col = np.ones((size, size, 4), np.float32)
    col[..., 0] = value * 1.03; col[..., 1] = value; col[..., 2] = value * .955
    col[..., :3] *= (1 - grime[..., None] * np.array([.50, .55, .60], np.float32))
    rc = np.array([.26, .15, .08], np.float32)
    col[..., :3] = col[..., :3] * (1 - rust[..., None]) + rc * rust[..., None]
    col[..., :3] = np.clip(col[..., :3], 0, 1)
    orm = np.ones_like(col)
    orm[..., 0] = occl
    rough = .36 + .12 * (1 - hf) + .08 * macro + grime * .3 + rust * .3
    rough = rough - wear * .14
    orm[..., 1] = np.clip(rough, .15, .9)
    orm[..., 2] = np.clip(prm('metal', .50) - rust * .6 - grime * .2 + wear * .15, 0, 1)
    gy, gx = np.gradient(height); safe = mask.copy()
    for sh, ax in [(1, 0), (-1, 0), (1, 1), (-1, 1)]: safe &= np.roll(mask, sh, axis=ax)
    st = size / 10.0
    ns_ = np.stack([-gx * st, -gy * st, np.ones_like(gx)], -1); ns_ /= np.maximum(np.linalg.norm(ns_, axis=-1, keepdims=True), 1e-6); ns_[~safe] = (0, 0, 1)
    nm = np.ones_like(col); nm[..., :3] = ns_ * .5 + .5
    for _ in range(7):
        grown = mask.copy()
        for sh, ax in [(1, 0), (-1, 0), (1, 1), (-1, 1)]:
            src = np.roll(mask, sh, axis=ax); fill = (~grown) & src
            for arr in (col, orm, nm): arr[fill] = np.roll(arr, sh, axis=ax)[fill]
            grown |= fill
        mask = grown
    (O / 'textures').mkdir(exist_ok=True)
    def image(suffix, arr, linear=False):
        name = kind + '_r1_' + suffix
        if bpy.data.images.get(name): bpy.data.images.remove(bpy.data.images[name])
        im = bpy.data.images.new(name, width=size, height=size, alpha=False)
        im.colorspace_settings.name = 'Non-Color' if linear else 'sRGB'
        im.pixels.foreach_set(arr.ravel()); im.filepath_raw = str(O / 'textures' / (name + '.png')); im.file_format = 'PNG'; im.save(); im.pack(); return im
    ims = [image('basecolor', col), image('normal', nm, True), image('ORM', orm, True)]
    m = bpy.data.materials.new(kind + '_Gunmetal_r1'); m.use_nodes = True; nd = m.node_tree.nodes; lk = m.node_tree.links
    bsdf = nd['Principled BSDF']; ts = []
    for im in ims: t = nd.new('ShaderNodeTexImage'); t.image = im; ts.append(t)
    lk.new(ts[0].outputs['Color'], bsdf.inputs['Base Color'])
    n = nd.new('ShaderNodeNormalMap'); lk.new(ts[1].outputs['Color'], n.inputs['Color']); lk.new(n.outputs['Normal'], bsdf.inputs['Normal'])
    sep = nd.new('ShaderNodeSeparateColor'); lk.new(ts[2].outputs['Color'], sep.inputs['Color'])
    lk.new(sep.outputs['Green'], bsdf.inputs['Roughness']); lk.new(sep.outputs['Blue'], bsdf.inputs['Metallic'])
    g = nd.new('ShaderNodeGroup'); g.node_tree = bpy.data.node_groups['glTF Material Output']; lk.new(sep.outputs['Red'], g.inputs['Occlusion'])
    for i in armor: o.data.materials[i] = m
    mv = float(np.mean(col[..., :3][mask])); log.setdefault('atlas_mean_albedo_srgb', {})[kind] = round(mv, 3)
    log.setdefault('ao_mean', {})[kind] = round(float(occl[mask].mean()), 3)
    print('ATLAS_READY', kind, 'mean_albedo', round(mv, 3), 'ao_mean', round(float(occl[mask].mean()), 3), flush=True)
    return m

atlas(head, 'head', 2048 if PREVIEW else 3072, extra=eyes)
atlas(body, 'segment2', 1024)
# ============================================================ 4b. TAIL: modeled sections + missile tip (replaces organic Hunyuan tail)
uvname = body.data.uv_layers.active.name
def tmp_obj(name, data, M):
    ob = bpy.data.objects.new(name, data); bpy.context.collection.objects.link(ob); ob.matrix_world = M; return ob
def ensure_uv(ob):
    if not ob.data.uv_layers:
        select(ob); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(island_margin=.02); bpy.ops.object.mode_set(mode='OBJECT')
    ob.data.uv_layers.active.name = uvname
    while len(ob.data.uv_layers) > 1: ob.data.uv_layers.remove(ob.data.uv_layers[-1])
T = Matrix.Translation; D = lambda a, b, c: Matrix.Diagonal((a, b, c, 1))
pieces = []
pA = tmp_obj('R1 tail section A', body.data.copy(), T((0.46, 0, 0)) @ D(.80, .92, .92))
pB = tmp_obj('R1 tail section B', body.data.copy(), T((1.30, 0, -0.01)) @ Matrix.Rotation(math.radians(-4), 4, 'Y') @ D(.68, .80, .80))
select(pB); m = pB.modifiers.new('budget', 'DECIMATE'); m.ratio = prm('tailB_ratio', .40); bpy.ops.object.modifier_apply(modifier=m.name)
pieces += [pA, pB]
hous = bpy.data.objects['Joint_00_Housing'].data; emit = bpy.data.objects['Joint_00_GlowBars'].data
for x, s_ in ((0.905, .88), (1.68, .76)):
    pieces.append(tmp_obj('R1 tail housing', hous.copy(), T((x, 0, 0)) @ D(1, s_, s_)))
    pieces.append(tmp_obj('R1 tail emitter', emit.copy(), T((x, 0, 0)) @ D(1, s_, s_)))
# missile cone: 8 sides, rings (x, r)
bm = bmesh.new(); prof = [(1.70, .375), (1.98, .345), (2.08, .30), (2.40, .17), (2.66, .0)]; N = 8; rings = []
for x, r in prof:
    if r == 0: rings.append([bm.verts.new((x, 0, 0))]); continue
    rings.append([bm.verts.new((x, r * cos(2 * pi * k / N + pi / 8), r * sin(2 * pi * k / N + pi / 8))) for k in range(N)])
cf = [bm.faces.new(list(reversed(rings[0])))]
for i in range(len(rings) - 1):
    A_, B_ = rings[i], rings[i + 1]
    for k in range(N):
        if len(B_) == 1: cf.append(bm.faces.new((A_[k], A_[(k + 1) % N], B_[0])))
        else: cf.append(bm.faces.new((A_[k], A_[(k + 1) % N], B_[(k + 1) % N], B_[k])))
bmesh.ops.recalc_face_normals(bm, faces=cf); bmesh.ops.triangulate(bm, faces=cf)
pieces.append(link_mesh('R1 tail cone', bm, steel))
# three small swept fins (dorsal + two lower-lateral), outline in (x, radial)
FINO = [(1.99, .30), (2.24, .30), (2.42, .52), (2.33, .52), (2.13, .37)]
for ang in (90, 210, 330):
    bm = bmesh.new(); a = math.radians(ang); rd = Vector((0, cos(a), sin(a))); tg = Vector((0, -sin(a), cos(a)))
    top = [bm.verts.new(Vector((x, 0, 0)) + rd * r + tg * .011) for x, r in FINO]
    bot = [bm.verts.new(Vector((x, 0, 0)) + rd * r - tg * .011) for x, r in FINO]
    fs = [bm.faces.new(top), bm.faces.new(list(reversed(bot)))]
    for i in range(len(FINO)): fs.append(bm.faces.new((top[(i + 1) % 5], top[i], bot[i], bot[(i + 1) % 5])))
    bmesh.ops.recalc_face_normals(bm, faces=fs); bmesh.ops.triangulate(bm, faces=fs)
    pieces.append(link_mesh('R1 tail fin', bm, bpy.data.materials['Worn machined rims']))
for ob in pieces: ensure_uv(ob)
old_tail = tail.data
tail.data = bpy.data.meshes.new('R1 modeled tail'); tail.data.uv_layers.new(name=uvname)
join_local(tail, pieces); triangulate(tail)
log['tail'] = dict(rebuilt='2 modeled sections (module copy + decimated module copy), 2 inline seam joints, 8-sided missile cone, 3 swept fins', tris=tris(tail))
print('TAIL_REBUILT', tris(tail), flush=True)
# machined/carbon trim darker so modeled parts sit in the same value family
for mname, colr, rgh, mtl in (('Fix machined edges', (.07, .07, .072), .42, .45), ('Worn machined rims', (.09, .09, .092), .40, .45),
                         ('Fix recessed carbon', (.012, .013, .015), .6, .5), ('Recessed graphite housings', (.02, .021, .024), .5, .5)):
    m = bpy.data.materials.get(mname)
    if m and m.use_nodes:
        b = m.node_tree.nodes.get('Principled BSDF')
        if b and not b.inputs['Base Color'].links: b.inputs['Base Color'].default_value = (*colr, 1); b.inputs['Roughness'].default_value = rgh; b.inputs['Metallic'].default_value = mtl

# ============================================================ 5. ASSEMBLY: re-share mesh, taper + roll variation
for o in segs: o.data = body.data
def taper(i):
    if i <= 3: return prm('neck_s', .93) + (1 - prm('neck_s', .93)) * i / 3
    if i <= prm('t0', 12): return 1.0
    t = (i - prm('t0', 12)) / (27 - prm('t0', 12)); return 1.0 - (1 - prm('s_end', .64)) * t
rng = random.Random(1017)
ROLLS = []
for i, o in enumerate(segs):
    kids = [c for c in o.children]
    kw = {c: c.matrix_world.translation.copy() for c in kids}
    roll = 0.0 if i == 0 else math.radians(rng.choice([-22, -14, -7, 0, 9, 16, 24, 180, 168, 192]))
    ROLLS.append(round(math.degrees(roll)))
    o.matrix_basis = o.matrix_basis @ Matrix.Rotation(roll, 4, 'X')
    s = taper(i); o.scale = (o.scale[0], s, s)
    bpy.context.view_layer.update()
    for c in kids:                       # keep joint centres on the chain after the roll
        c.location = (o.matrix_world.inverted() @ kw[c])
        c.location.y = c.location.y * 0 if False else c.location.y
    bpy.context.view_layer.update()
se = taper(27) * prm('tail_s', .97)
tail.scale = (1, se, se)
log['taper'] = [round(taper(i), 3) for i in range(28)] + [round(se, 3)]
log['rolls_deg'] = ROLLS

# ============================================================ 6. invariants + counts
assets = [o for o in bpy.data.objects if o.type == 'MESH' and o is not catcher]
for o in assets:
    if not o.data.uv_layers: ensure_uv(o)
    if o not in eyes: triangulate(o)
assert len([o for o in assets if o.name.startswith('Segment_')]) == 28
assert len({o.data for o in segs}) == 1
assert len([o for o in assets if 'Housing' in o.name]) == 29 and len([o for o in assets if 'GlowBars' in o.name]) == 29
assert lens_baseline == {o.name: ([tuple(v.co) for v in o.data.vertices], [tuple(r) for r in o.matrix_basis]) for o in eyes}, 'lens changed'
cnt = {o.name: tris(o) for o in assets}
rep = dict(total=sum(cnt.values()), head=sum(cnt[o.name] for o in [head] + eyes), segment=cnt['Segment_00'],
           joint=cnt['Joint_00_Housing'] + cnt['Joint_00_GlowBars'], tail=cnt['Tail'])
rep['segment_plus_joint'] = rep['segment'] + rep['joint']; rep['tail_plus_joint'] = rep['tail'] + rep['joint']
rep['segments'] = 28; rep['joints'] = 29
print('R1_COUNTS', rep, flush=True)
assert 10000 <= rep['head'] <= 18000 and rep['segment_plus_joint'] <= 1600 and rep['tail_plus_joint'] <= 3000 and 30000 <= rep['total'] <= 59900, rep
log['counts'] = rep; log['objects'] = cnt

if not PREVIEW:
    bpy.ops.object.select_all(action='DESELECT')
    for o in assets: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(O / 'snake-sectional-r1.glb'), export_format='GLB', use_selection=True,
        export_apply=False, export_yup=True, export_texcoords=True, export_normals=True, export_tangents=True,
        export_draco_mesh_compression_enable=False, export_materials='EXPORT')
    print('R1_EXPORTED', flush=True)

# ============================================================ 7. staging (FIX2 rig unchanged) + render
for m in bpy.data.materials:            # render-only AO multiply, inserted after export (FIX2 method)
    if not m.name.endswith('_Gunmetal_r1'): continue
    nt = m.node_tree; bsdf = nt.nodes['Principled BSDF']; tx = bsdf.inputs['Base Color'].links[0].from_node
    sep = next(n for n in nt.nodes if n.type == 'SEPARATE_COLOR')
    mx = nt.nodes.new('ShaderNodeMixRGB'); mx.blend_type = 'MULTIPLY'; mx.inputs['Fac'].default_value = 1.0
    nt.links.new(tx.outputs['Color'], mx.inputs['Color1']); nt.links.new(sep.outputs['Red'], mx.inputs['Color2']); nt.links.new(mx.outputs['Color'], bsdf.inputs['Base Color'])
cam = sc.camera
def shot(fp, loc, target, only=None):
    cam.location = loc; cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler(); bpy.context.view_layer.update()
    vis = assets if only is None else only
    saved = {o: o.hide_render for o in assets}
    for o in assets: o.hide_render = o not in vis
    inv = cam.matrix_world.inverted(); pts = [inv @ (o.matrix_world @ v.co) for o in vis for v in o.data.vertices]
    xmin = min(p.x for p in pts); xmax = max(p.x for p in pts); ymin = min(p.y for p in pts); ymax = max(p.y for p in pts)
    cam.location += cam.rotation_euler.to_quaternion() @ Vector(((xmin + xmax) / 2, (ymin + ymax) / 2, 0))
    w, hh = sc.render.resolution_x, sc.render.resolution_y
    cam.data.ortho_scale = max(xmax - xmin, (ymax - ymin) * w / hh) * 1.12
    sc.render.filepath = str(fp); bpy.ops.render.render(write_still=True)
    for o, hv in saved.items(): o.hide_render = hv
sc.render.engine = 'CYCLES'; sc.cycles.use_denoising = True; sc.render.image_settings.file_format = 'PNG'
if PREVIEW:
    sc.cycles.samples = 32; sc.cycles.use_adaptive_sampling = False
    sc.render.resolution_x, sc.render.resolution_y = 854, 480
    pv = O / 'previews'; pv.mkdir(exist_ok=True)
    shot(pv / ('PREVIEW-%s-full-body-480p.png' % TAG), (-7, -12, 7), (.5, 0, 1.9))
    shot(pv / ('PREVIEW-%s-head-closeup-480p.png' % TAG), (-4, -7, 5.2), (-2.2, .25, 4), only=[head] + eyes)
    tl = [tail] + [c for c in tail.children] + segs[24:] + [c for s_ in segs[24:] for c in s_.children]
    shot(pv / ('PREVIEW-%s-tail-480p.png' % TAG), (2, -9, 5), (5, -1.5, .5), only=tl)
    jl = segs[9:13] + [c for s_ in segs[9:13] for c in s_.children]
    shot(pv / ('PREVIEW-%s-joints-480p.png' % TAG), (-1, -9, 4), (0, -2.5, .5), only=jl)
else:
    sc.cycles.samples = 384; sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.01
    sc.cycles.sample_clamp_indirect = 3.0; sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 6
    sc.cycles.transmission_bounces = 2; sc.cycles.transparent_max_bounces = 6
    try: sc.cycles.use_light_tree = True
    except Exception: pass
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080; sc.render.resolution_percentage = 100
    bpy.ops.file.pack_all(); bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(O / 'snake-sectional-r1.blend'))
    (O / 'captures').mkdir(exist_ok=True)
    shot(O / 'captures/r1-full-body.png', (-7, -12, 7), (.5, 0, 1.9))
    shot(O / 'captures/r1-head-closeup.png', (-4, -7, 5.2), (-2.2, .25, 4), only=[head] + eyes)
(O / ('log-%s.json' % TAG)).write_text(json.dumps(log, indent=1))
print('R1_DONE', MODE, TAG, flush=True)
