"""Persist the verified final stage locally for Round 4 in this SAME session.
Does not re-export or change the canonical GLB. Working blend remains ignored.
"""
import bpy,json
from pathlib import Path
R=Path(r'\\wsl.localhost\OpenClawGateway\home\openclaw\.openclaw\workspace-studio-3d\tickets\forge-r3');O=R/'benchmarks/forge-snake-r3'
bpy.ops.wm.open_mainfile(filepath=str(O/'snake-sectional-r3.blend'));sc=bpy.context.scene
settings=json.loads((O/'captures/r3-render-settings.json').read_text());g=next(n for n in sc.node_tree.nodes if n.type=='GLARE')
for socket,key in [('Threshold','threshold'),('Strength','strength'),('Size','size_normalized')]:g.inputs[socket].default_value=settings['glare'][key]
sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=256;sc.cycles.use_adaptive_sampling=True;sc.cycles.adaptive_threshold=.01;sc.cycles.use_denoising=True;sc.cycles.denoiser='OPENIMAGEDENOISE';sc.render.resolution_x=1920;sc.render.resolution_y=1080
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.hide_render=False
f=settings['frames']['full'];sc.camera.location=f['location'];sc.camera.rotation_euler=f['rotation'];sc.camera.data.ortho_scale=f['ortho_scale']
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'snake-sectional-r3.blend'))
print('R3_LOCAL_STAGE_PERSISTED',flush=True)
