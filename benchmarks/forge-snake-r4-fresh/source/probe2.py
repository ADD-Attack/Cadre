import bpy,json,bmesh
from pathlib import Path
R=Path(r'\\wsl.localhost\OpenClawGateway\home\openclaw\.openclaw\workspace-studio-3d\tickets\forge-r4-fresh')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(R/'benchmarks/forge-snake-r3/snake-sectional-r3.glb'))

for name in ['R2 socket lens -1','Segment_00']:
 o=bpy.data.objects[name]
 print('PART',name,'mats',[m.name for m in o.data.materials])
 for mi,m in enumerate(o.data.materials):
  vs={v for p in o.data.polygons if p.material_index==mi for v in p.vertices}
  print('MAT',mi,m.name,'faces',sum(p.material_index==mi for p in o.data.polygons),'bounds',[(min(o.data.vertices[v].co[i] for v in vs),max(o.data.vertices[v].co[i] for v in vs)) for i in range(3)] if vs else [])
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000005);seen=set();cs=[]
 for v in bm.verts:
  if v in seen:continue
  st=[v];seen.add(v);vs=[]
  while st:
   q=st.pop();vs.append(q)
   for e in q.link_edges:
    w=e.other_vert(q)
    if w not in seen:seen.add(w);st.append(w)
  fs={f for v in vs for f in v.link_faces}
  cs.append({'v':len(vs),'f':len(fs),'mat':list({f.material_index for f in fs}),'min':[round(min(q.co[i] for q in vs),4) for i in range(3)],'max':[round(max(q.co[i] for q in vs),4) for i in range(3)]})
 print('WELDED',name,json.dumps(cs));bm.free()
