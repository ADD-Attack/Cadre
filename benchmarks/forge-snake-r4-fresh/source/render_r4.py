import bpy,os,json
from pathlib import Path
R=Path(r'\\wsl.localhost\OpenClawGateway\home\openclaw\.openclaw\workspace-studio-3d\tickets\forge-r4-fresh');O=R/'benchmarks/forge-snake-r4-fresh';B=R/'benchmarks/forge-snake-r3'
mode=os.environ.get('R4_MODE','preview');tag=os.environ.get('R4_TAG','a');baseline=os.environ.get('R4_BASELINE','0')=='1'
bpy.ops.wm.open_mainfile(filepath=str(O/'snake-sectional-r4-fresh.blend'));sc=bpy.context.scene
if baseline:
 for ob in list(bpy.data.objects):
  if ob.type=='MESH' and not ob.name.startswith('staging'):bpy.data.objects.remove(ob,do_unlink=True)
 bpy.ops.outliner.orphans_purge(do_recursive=True)
 bpy.ops.import_scene.gltf(filepath=str(B/'snake-sectional-r3.glb'))
 for m in bpy.data.materials:
  if not m.use_nodes:continue
  nt=m.node_tree;bs=nt.nodes.get('Principled BSDF');orm=next((n for n in nt.nodes if n.type=='TEX_IMAGE' and n.image and 'ORM' in n.image.name),None)
  if not bs or not orm:continue
  sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(orm.outputs['Color'],sep.inputs[0]);mul=nt.nodes.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1
  if bs.inputs['Base Color'].is_linked:nt.links.new(bs.inputs['Base Color'].links[0].from_socket,mul.inputs[1])
  else:mul.inputs[1].default_value=bs.inputs['Base Color'].default_value
  nt.links.new(sep.outputs['Red'],mul.inputs[2]);nt.links.new(mul.outputs[0],bs.inputs['Base Color'])
assets=[o for o in bpy.data.objects if o.type=='MESH' and not o.name.startswith('staging')];head=bpy.data.objects['Head'];eyes=[o for o in head.children if o.type=='MESH'];cam=sc.camera
frames=json.loads((B/'captures/r3-render-settings.json').read_text())['frames']
sc.cycles.samples=256 if mode=='final' else 32;sc.cycles.use_adaptive_sampling=mode=='final';sc.render.resolution_x=1920 if mode=='final' else 1152;sc.render.resolution_y=1080 if mode=='final' else 648
for label in ['full','head']:
 for ob in assets:ob.hide_render=label=='head' and ob not in [head]+eyes
 f=frames[label];cam.location=f['location'];cam.rotation_euler=f['rotation'];cam.data.ortho_scale=f['ortho_scale']
 prefix=('baseline-r3' if baseline else 'r4-fresh') if mode=='final' else 'PREVIEW-'+('baseline-' if baseline else '')+tag
 name=prefix+('-full-body.png' if label=='full' else '-head-closeup.png');sc.render.filepath=str(O/('captures' if mode=='final' else 'previews')/name)
 print('R4_RENDER_START',name,flush=True);bpy.ops.render.render(write_still=True);print('R4_RENDER_DONE',name,flush=True)
gl=next(n for n in sc.node_tree.nodes if n.type=='GLARE')
settings={'frames':frames,'view_transform':sc.view_settings.view_transform,'look':sc.view_settings.look,'exposure':sc.view_settings.exposure,'gamma':sc.view_settings.gamma,'engine':sc.render.engine,'device':sc.cycles.device,'samples':sc.cycles.samples,'adaptive':sc.cycles.use_adaptive_sampling,'adaptive_threshold':sc.cycles.adaptive_threshold,'denoise':sc.cycles.use_denoising,'resolution':[sc.render.resolution_x,sc.render.resolution_y],'glare':{'type':gl.glare_type,'threshold':gl.inputs['Threshold'].default_value,'strength':gl.inputs['Strength'].default_value,'size_normalized':gl.inputs['Size'].default_value},'lights':[{'name':o.name,'location':list(o.location),'rotation':list(o.rotation_euler),'energy':o.data.energy,'size':o.data.size,'color':list(o.data.color)} for o in sorted(bpy.data.objects,key=lambda o:o.name) if o.type=='LIGHT'],'world_backgrounds':[{'color':list(n.inputs['Color'].default_value),'strength':n.inputs['Strength'].default_value} for n in sc.world.node_tree.nodes if n.type=='BACKGROUND']}
if mode=='final':(O/'captures'/('baseline-r3-render-settings.json' if baseline else 'r4-fresh-render-settings.json')).write_text(json.dumps(settings,indent=2))
print('R4_RENDER_COMPLETE',flush=True)
