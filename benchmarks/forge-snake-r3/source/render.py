"""Cycles renders from the saved R3 checkpoint, or paired untouched R2 baseline.
R3_MODE preview|final; R3_BASELINE=1; same camera/light/world rig for both assets.
"""
import bpy,json,os
import numpy as np
from pathlib import Path
R=Path(r'\\wsl.localhost\OpenClawGateway\home\openclaw\.openclaw\workspace-studio-3d\tickets\forge-r3');O=R/'benchmarks/forge-snake-r3';B=R/'benchmarks/snake-r2-sol'
MODE=os.environ.get('R3_MODE','preview');TAG=os.environ.get('R3_TAG','a');BASELINE=os.environ.get('R3_BASELINE','0')=='1'
bpy.ops.wm.open_mainfile(filepath=str(O/'snake-sectional-r3.blend'));sc=bpy.context.scene
bpy.ops.outliner.orphans_purge(do_recursive=True)
if BASELINE:
 for ob in list(bpy.data.objects):
  if ob.type=='MESH' and 'staging' not in ob.name.lower():bpy.data.objects.remove(ob,do_unlink=True)
 bpy.ops.outliner.orphans_purge(do_recursive=True)
 bpy.ops.import_scene.gltf(filepath=str(B/'snake-sectional-r2.glb'))
 for m in bpy.data.materials:
  if not m.name.startswith('R2 baked'):continue
  nt=m.node_tree;bs=nt.nodes['Principled BSDF'];tx=bs.inputs['Base Color'].links[0].from_socket;orm=next(n for n in nt.nodes if n.type=='TEX_IMAGE' and 'ORM' in n.image.name);sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(orm.outputs['Color'],sep.inputs[0]);mul=nt.nodes.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;nt.links.new(tx,mul.inputs[1]);nt.links.new(sep.outputs['Red'],mul.inputs[2]);nt.links.new(mul.outputs[0],bs.inputs['Base Color'])
# Sample clear reference background as encoded RGB, not an assumed grey.
reference=R.parent/'forge-snake-r1/pkg/forge-r1-pack/REFERENCE.png'
im=bpy.data.images.load(str(reference));im.colorspace_settings.name='Non-Color';rw,rh=im.size
arr=np.empty(rw*rh*4,np.float32);im.pixels.foreach_get(arr);arr=arr.reshape(rh,rw,4)
patch=arr[rh-180:rh,1400:1900,:3]
(O/'reference-background-sample.json').write_text(json.dumps({'reference':str(reference),'sample':'top-right 500x180 clear backdrop','median_rgb_encoded_0_to_1':np.median(patch.reshape(-1,3),axis=0).tolist(),'median_rgb_scaled_255':(np.median(patch.reshape(-1,3),axis=0)*255).tolist(),'owner_target':'#C1C1BF','staging':'inherited matched R1/R2 camera background'},indent=2))
bpy.data.images.remove(im);del arr,patch
assets=[o for o in bpy.data.objects if o.type=='MESH' and 'staging' not in o.name.lower()];head=bpy.data.objects['Head'];eyes=[o for o in head.children if o.type=='MESH'];cam=sc.camera
sc.render.engine='CYCLES';sc.cycles.device=os.environ.get('R3_DEVICE','CPU');sc.cycles.use_denoising=True;sc.cycles.denoiser='OPENIMAGEDENOISE';sc.cycles.samples=256 if MODE=='final' else 32;sc.cycles.use_adaptive_sampling=MODE=='final';sc.cycles.adaptive_threshold=.01
sc.cycles.max_bounces=6;sc.cycles.diffuse_bounces=2;sc.cycles.glossy_bounces=4;sc.cycles.sample_clamp_indirect=3
sc.render.resolution_x=1920 if MODE=='final' else 1152;sc.render.resolution_y=1080 if MODE=='final' else 648;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
# CPU avoids contending for the 8GB GPU's already-allocated memory. Same Blender executable/engine.
sc.render.threads_mode='FIXED';sc.render.threads=12
# Tight, subtle bloom also reaches the deliberately dimmed 0.714-peak joint emitters.
# Apply identically to the untouched R2 baseline and R3 after images.
glare=next(n for n in sc.node_tree.nodes if n.type=='GLARE');glare.inputs['Threshold'].default_value=.4;glare.inputs['Strength'].default_value=.25;glare.inputs['Size'].default_value=.125
frames=json.loads((B/'counts-and-log.json').read_text())['staging_frames_from_R1']
for label in ['full','head']:
 for ob in assets:ob.hide_render=label=='head' and ob not in [head]+eyes
 f=frames[label];cam.location=f['location'];cam.rotation_euler=f['rotation'];cam.data.ortho_scale=f['ortho_scale']
 prefix=('baseline-r2' if BASELINE else 'r3') if MODE=='final' else ('PREVIEW-'+('baseline-' if BASELINE else '')+TAG)
 dest='captures' if MODE=='final' else 'previews';name=prefix+('-full-body.png' if label=='full' else '-head-closeup.png');sc.render.filepath=str(O/dest/name)
 print('R3_RENDER_START',name,MODE,sc.cycles.device,sc.cycles.samples,flush=True);bpy.ops.render.render(write_still=True);print('R3_RENDER_DONE',name,flush=True)
if MODE=='final' and not BASELINE:
 log=json.loads((O/'counts-and-log.json').read_text());log['judged_render']={'application':bpy.app.version_string,'engine':sc.render.engine,'device':sc.cycles.device,'max_samples':sc.cycles.samples,'adaptive':sc.cycles.use_adaptive_sampling,'noise_threshold':sc.cycles.adaptive_threshold,'denoise':sc.cycles.use_denoising,'denoiser':sc.cycles.denoiser,'resolution':[sc.render.resolution_x,sc.render.resolution_y],'identical_frames_to_R2':True,'camera_frames':frames,'AO':'ORM R multiplied into Blender shader; packed separate in GLB','contact_shadow':'inherited shadow catcher','glow':{'type':'FOG_GLOW','threshold':glare.inputs['Threshold'].default_value,'strength':glare.inputs['Strength'].default_value,'size_normalized':glare.inputs['Size'].default_value},'backdrop':'reference-sampled #C1C1BF world; same baseline and after'};(O/'counts-and-log.json').write_text(json.dumps(log,indent=2))
if MODE=='final':
 settings={'frames':frames,'view_transform':sc.view_settings.view_transform,'look':sc.view_settings.look,'exposure':sc.view_settings.exposure,'gamma':sc.view_settings.gamma,'engine':sc.render.engine,'samples':sc.cycles.samples,'adaptive':sc.cycles.use_adaptive_sampling,'adaptive_threshold':sc.cycles.adaptive_threshold,'denoise':sc.cycles.use_denoising,'resolution':[sc.render.resolution_x,sc.render.resolution_y],'glare':{'type':glare.glare_type,'threshold':glare.inputs['Threshold'].default_value,'strength':glare.inputs['Strength'].default_value,'size_normalized':glare.inputs['Size'].default_value},'lights':[{'name':o.name,'location':list(o.location),'rotation':list(o.rotation_euler),'energy':o.data.energy,'size':o.data.size,'color':list(o.data.color)} for o in sorted(bpy.data.objects,key=lambda o:o.name) if o.type=='LIGHT'],'world_backgrounds':[{'color':list(n.inputs['Color'].default_value),'strength':n.inputs['Strength'].default_value} for n in sc.world.node_tree.nodes if n.type=='BACKGROUND']}
 (O/'captures'/('baseline-r2-render-settings.json' if BASELINE else 'r3-render-settings.json')).write_text(json.dumps(settings,indent=2))
print('R3_RENDER_COMPLETE',flush=True)
