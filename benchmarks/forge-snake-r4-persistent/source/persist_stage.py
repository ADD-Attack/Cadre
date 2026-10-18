"""Preserve verified R4 review stage locally; never changes exported GLB."""
import bpy,json
from pathlib import Path
R=Path(r'\\wsl.localhost\OpenClawGateway\home\openclaw\.openclaw\workspace-studio-3d\tickets\forge-r3');O=R/'benchmarks/forge-snake-r4-persistent';B=R/'benchmarks/forge-snake-r3'
bpy.ops.wm.open_mainfile(filepath=str(O/'snake-sectional-r4.blend'));s=bpy.context.scene
f=json.loads((B/'counts-and-log.json').read_text())['judged_render']['camera_frames']['full'];s.camera.location=f['location'];s.camera.rotation_euler=f['rotation'];s.camera.data.ortho_scale=f['ortho_scale']
for o in bpy.data.objects:
 if o.type=='MESH':o.hide_render=False
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=256;s.cycles.use_adaptive_sampling=True;s.cycles.adaptive_threshold=.01;s.cycles.use_denoising=True;s.cycles.denoiser='OPENIMAGEDENOISE';s.render.resolution_x=1920;s.render.resolution_y=1080;s.render.resolution_percentage=100;s.render.threads_mode='FIXED';s.render.threads=12
n=next(n for n in s.node_tree.nodes if n.type=='GLARE');n.inputs['Threshold'].default_value=.4;n.inputs['Strength'].default_value=.25;n.inputs['Size'].default_value=.125
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'snake-sectional-r4.blend'))
import numpy as np
materials={m for o in bpy.data.objects if o.type=='MESH' and 'staging' not in o.name.lower() for m in o.data.materials if m}
shader_audit={}
for m in materials:
 shaders=[n.type for n in m.node_tree.nodes if n.type.startswith('BSDF_') or n.type=='EMISSION']
 assert shaders==['BSDF_PRINCIPLED'],(m.name,shaders)
 normals=[float(n.inputs['Strength'].default_value) for n in m.node_tree.nodes if n.type=='NORMAL_MAP']
 if m.name.startswith('R4 directional silver'):assert normals and all(abs(v-.35)<1e-5 for v in normals)
 shader_audit[m.name]={'surface_shaders':shaders,'micro_normal_strengths':normals}
(O/'material-audit.json').write_text(json.dumps(shader_audit,indent=2))
samples={}
for name in ['r4-full-body.png','r4-head-closeup.png','baseline-r3-full-body.png','baseline-r3-head-closeup.png']:
 im=bpy.data.images.load(str(O/'captures'/name));im.colorspace_settings.name='Non-Color';w,h=im.size;a=np.empty(w*h*4,np.float32);im.pixels.foreach_get(a);a=a.reshape(h,w,4);samples[name]=(np.median(a[h-20:h,w-20:w,:3].reshape(-1,3),axis=0)*255).tolist();bpy.data.images.remove(im)
report={'sample':'clear top-right 20x20 encoded RGB median','owner_world_input':'#C1C1BF','rendered_background_rgb255':samples,'paired_max_channel_difference':max(abs(samples['r4-'+v+'.png'][i]-samples['baseline-r3-'+v+'.png'][i]) for v in ['full-body','head-closeup'] for i in range(3))}
(O/'background-validation.json').write_text(json.dumps(report,indent=2));assert report['paired_max_channel_difference']<=2,report
assert all(abs(c-194)<=7 for rgb in samples.values() for c in rgb),report
print('R4_FINAL_STAGE_PERSISTED',json.dumps(report),flush=True)
