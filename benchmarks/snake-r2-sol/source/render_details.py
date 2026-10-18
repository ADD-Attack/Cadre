"""Low-sample detail previews from the packed FINAL blend; never judged images."""
import bpy,os
from pathlib import Path
from mathutils import Vector
root=Path(os.environ['R2_ROOT']);out=root/'out';bpy.ops.wm.open_mainfile(filepath=str(out/'snake-sectional-r2-final.blend'));sc=bpy.context.scene;cam=sc.camera
assets=[o for o in bpy.data.objects if o.type=='MESH' and 'staging' not in o.name.lower()]
sc.cycles.device='CPU';sc.cycles.samples=32;sc.cycles.use_adaptive_sampling=False;sc.render.resolution_x=1152;sc.render.resolution_y=648
p=out/'previews';p.mkdir(exist_ok=True)
def shot(name,vis,loc,target):
 for o in assets:o.hide_render=o not in vis
 cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update();inv=cam.matrix_world.inverted();pts=[inv@(o.matrix_world@v.co) for o in vis for v in o.data.vertices];lo=Vector((min(q.x for q in pts),min(q.y for q in pts),0));hi=Vector((max(q.x for q in pts),max(q.y for q in pts),0));cam.location+=cam.rotation_euler.to_quaternion()@((lo+hi)/2);cam.data.ortho_scale=max(hi.x-lo.x,(hi.y-lo.y)*16/9)*1.14;sc.render.filepath=str(p/name);bpy.ops.render.render(write_still=True)
ss=[bpy.data.objects['Segment_%02d'%i] for i in (9,10,11)];vis=ss+[c for s in ss for c in s.children]
shot('PREVIEW-final-module.png',vis,(-2,-7,4),(0,0,0))
tail=bpy.data.objects['Tail'];ss=[bpy.data.objects['Segment_%02d'%i] for i in (25,26,27)];vis=[tail]+list(tail.children)+ss+[c for s in ss for c in s.children]
shot('PREVIEW-final-tail.png',vis,(2,-9,5),(5,-1.5,.5))
print('FINAL_DETAIL_PREVIEWS_READY')
