"""Explicitly labeled 48-sample iteration-only detail views, not judged captures."""
import bpy,os
from pathlib import Path
from mathutils import Vector
R=Path(r'\\wsl.localhost\OpenClawGateway\home\openclaw\.openclaw\workspace-studio-3d\tickets\forge-r3');O=R/'benchmarks/forge-snake-r3'
bpy.ops.wm.open_mainfile(filepath=str(O/'snake-sectional-r3.blend'));sc=bpy.context.scene;cam=sc.camera
assets=[o for o in bpy.data.objects if o.type=='MESH' and 'staging' not in o.name.lower()]
sc.cycles.samples=48;sc.cycles.use_adaptive_sampling=False;sc.cycles.device='CPU';sc.render.resolution_x=1280;sc.render.resolution_y=720
pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='OPTIX';pref.refresh_devices()
for d in pref.devices:d.use=d.type=='OPTIX'
def shot(name,only,loc,target):
 for o in assets:o.hide_render=o not in only
 cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update();inv=cam.matrix_world.inverted();pts=[inv@(o.matrix_world@v.co) for o in only for v in o.data.vertices];lo=Vector((min(p.x for p in pts),min(p.y for p in pts),0));hi=Vector((max(p.x for p in pts),max(p.y for p in pts),0));cam.location+=cam.rotation_euler.to_quaternion()@((lo+hi)/2);cam.data.ortho_scale=max(hi.x-lo.x,(hi.y-lo.y)*1280/720)*1.15;sc.render.filepath=str(O/'previews'/name);bpy.ops.render.render(write_still=True)
ss=[bpy.data.objects['Segment_%02d'%i] for i in (9,10,11)];shot('PREVIEW-detail-module.png',ss+[c for s in ss for c in s.children],(-2,-7,4),(0,0,0))
tail=bpy.data.objects['Tail'];ss=[bpy.data.objects['Segment_%02d'%i] for i in (26,27)];shot('PREVIEW-detail-tail.png',[tail]+list(tail.children)+ss+[c for s in ss for c in s.children],(2,-9,5),(5,-1.5,.5))
print('R3_DETAIL_PREVIEWS_READY',flush=True)
