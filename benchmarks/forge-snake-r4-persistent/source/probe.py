import bpy,bmesh,json
from pathlib import Path
R=Path(r'\\wsl.localhost\OpenClawGateway\home\openclaw\.openclaw\workspace-studio-3d\tickets\forge-r3')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(R/'benchmarks/forge-snake-r3/snake-sectional-r3.glb'))
for name in ['Segment_00','Joint_00_Housing','Joint_00_GlowBars','Head','Tail','R2 socket lens -1']:
 ob=bpy.data.objects[name];print('OBJECT',name,[(i,m.name) for i,m in enumerate(ob.data.materials)],flush=True)
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000004);bm.verts.ensure_lookup_table();seen=set();cs=[]
 for v in bm.verts:
  if v in seen:continue
  todo=[v];vs=[];fs=set();seen.add(v)
  while todo:
   a=todo.pop();vs.append(a);fs.update(a.link_faces)
   for e in a.link_edges:
    q=e.other_vert(a)
    if q not in seen:seen.add(q);todo.append(q)
  cs.append({'tris':sum(len(f.verts)-2 for f in fs),'mi':list(set(f.material_index for f in fs)),'lo':[round(min(a.co[i] for a in vs),4) for i in range(3)],'hi':[round(max(a.co[i] for a in vs),4) for i in range(3)]})
 print('COMPONENTS',name,json.dumps(cs),flush=True);bm.free()
