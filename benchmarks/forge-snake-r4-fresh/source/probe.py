import bpy,json,bmesh
from pathlib import Path
R=Path(r'\\wsl.localhost\OpenClawGateway\home\openclaw\.openclaw\workspace-studio-3d\tickets\forge-r4-fresh')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(R/'benchmarks/forge-snake-r3/snake-sectional-r3.glb'))
for o in bpy.data.objects:
 if o.type=='MESH' and (o.name in ['Head','Segment_00','Tail','Joint_00_GlowBars','Joint_00_Housing'] or 'socket' in o.name):
  print('OBJ',o.name,'parent',o.parent.name if o.parent else None,'matrix',list(map(list,o.matrix_world)),'bounds',[(min(v.co[i] for v in o.data.vertices),max(v.co[i] for v in o.data.vertices)) for i in range(3)],'mats',[m.name for m in o.data.materials],flush=True)
  bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table();seen=set();cs=[]
  for v in bm.verts:
   if v.index in seen:continue
   st=[v];seen.add(v.index);vs=[]
   while st:
    q=st.pop();vs.append(q)
    for e in q.link_edges:
     w=e.other_vert(q)
     if w.index not in seen:seen.add(w.index);st.append(w)
   cs.append({'v':len(vs),'min':[round(min(q.co[i] for q in vs),4) for i in range(3)],'max':[round(max(q.co[i] for q in vs),4) for i in range(3)]})
  print('COMPONENTS',o.name,len(cs),json.dumps(cs[:160]),flush=True);bm.free()
print('IMAGES',[(im.name,tuple(im.size),im.colorspace_settings.name) for im in bpy.data.images],flush=True)
pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='OPTIX';pref.refresh_devices();print('DEVICES',[(d.name,d.type) for d in pref.devices],flush=True)
