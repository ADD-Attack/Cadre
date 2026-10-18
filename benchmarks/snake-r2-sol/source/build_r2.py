"""Rescue R2. Run in Blender 4.5.14 from the shipped R1 packed blend.
All geometry edits start from R1 on every invocation. No R2 entrant inputs.
"""
import bpy,bmesh,math,os,json,random
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from math import sin,cos,pi
ROOT=Path(os.environ.get('R2_ROOT',r'C:\Users\Moore\snake-r2-sol'))
OUT=ROOT/'out';OUT.mkdir(exist_ok=True)
MODE=os.environ.get('R2_MODE','preview');TAG=os.environ.get('R2_TAG','a')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'r1-baseline.blend'))
sc=bpy.context.scene;head=bpy.data.objects['Head'];body=bpy.data.objects['Segment_00'];tail=bpy.data.objects['Tail']
segs=[bpy.data.objects['Segment_%02d'%i] for i in range(28)]
catcher=bpy.data.objects['Fix2 shadow catcher (staging)']
pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='OPTIX';pref.refresh_devices()
for d in pref.devices:d.use=d.type=='OPTIX'
sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.use_denoising=True
LOG={'order':'op-snake-r2-rescue-20261018','base':'forge-snake-r1-20261017 @ 32c661e','head_rebase':'Procedurally fitted skull and armor; no Hunyuan generation used.'}

def select(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o

def tri(o):
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o.data.validate(verbose=False,clean_customdata=False);o.data.update()

def count(o):o.data.calc_loop_triangles();return len(o.data.loop_triangles)

def mat(name,col,rough=.5,metal=.5,emit=None):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(*col,1);b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal
 if emit:b.inputs['Emission Color'].default_value=(*col,1);b.inputs['Emission Strength'].default_value=emit
 return m
armor=mat('R2 armor substrate',(.09,.085,.075));steel=mat('R2 exposed steel',(.025,.027,.027),.36,.58);dark=mat('R2 recessed graphite',(.008,.01,.011),.67,.28)
teal=mat('R2 lens teal',(.012,.45,.32),.24,.25,2.0)
glass=mat('R2 lens glass',(.012,.07,.055),.15,.35)
MATS=[armor,steel,dark]
# Freeze framing from the shipped R1 geometry before making any asset edits.
def baseline_frame(loc,target,vis):
 cam=sc.camera;cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update();inv=cam.matrix_world.inverted();pts=[inv@(o.matrix_world@v.co) for o in vis for v in o.data.vertices];xmin=min(p.x for p in pts);xmax=max(p.x for p in pts);ymin=min(p.y for p in pts);ymax=max(p.y for p in pts);loc=cam.location+cam.rotation_euler.to_quaternion()@Vector(((xmin+xmax)/2,(ymin+ymax)/2,0));scale=max(xmax-xmin,(ymax-ymin)*16/9)*1.12
 return (loc.copy(),cam.rotation_euler.copy(),scale)
R1_FRAMES={'full':baseline_frame((-7,-12,7),(.5,0,1.9),[o for o in bpy.data.objects if o.type=='MESH' and o is not catcher]),'head':baseline_frame((-4,-7,5.2),(-2.2,.25,4),[head]+[o for o in head.children if o.type=='MESH'])}
LOG['staging_frames_from_R1']={k:{'location':list(v[0]),'rotation':list(v[1]),'ortho_scale':v[2]} for k,v in R1_FRAMES.items()}
class Geo:
 def __init__(self):self.v=[];self.f=[];self.mi=[];self.bolts=[];self.smooth=[];self.normals={};self.solid=False
 def face(self,ids,mi=0,smooth=False):self.f.append(ids);self.mi.append(mi);self.smooth.append(smooth)
 def verts(self,pts):
  i=len(self.v);self.v.extend([tuple(p) for p in pts]);return list(range(i,len(self.v)))
 def obj(self,name,mats=MATS):
  me=bpy.data.meshes.new(name);me.from_pydata(self.v,[],self.f);me.update()
  for m in mats:me.materials.append(m)
  for p,mi,s in zip(me.polygons,self.mi,self.smooth):p.material_index=mi;p.use_smooth=s
  o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o)
  attr=me.attributes.new('R2_surface_normal','FLOAT_VECTOR','POINT')
  for i,n in self.normals.items():attr.data[i].vector=n
  tri(o);return o
 def patch(self,poly,mapper,mi=0,th=.018,bev=.012):
  # Parametric curved plate: inset top, chamfer and recessed skirt. Physical seams.
  uv=np.array(poly,float);c=uv.mean(0);dd=uv-c;length=np.linalg.norm(dd,axis=1);q=c+dd*np.maximum(0,(length-bev)/length)[:,None]
  outer=self.verts([mapper(*p,0) for p in uv]);inner=self.verts([mapper(*p,.008) for p in q]);bottom=self.verts([mapper(*p,-th) for p in uv]);center=self.verts([mapper(*c,.008)])[0];n=len(poly)
  for idx,p in list(zip(inner,q))+[(center,c)]:
   px,pa=p;dx=Vector(mapper(px+.0001,pa,.008))-Vector(mapper(px-.0001,pa,.008));da=Vector(mapper(px,pa+.0001,.008))-Vector(mapper(px,pa-.0001,.008));nn=da.cross(dx).normalized();self.normals[idx]=nn
  if self.solid:self.face(tuple(reversed(bottom)),mi)
  for k in range(n):
   j=(k+1)%n;self.face((center,inner[k],inner[j]),mi,True);self.face((inner[k],outer[k],outer[j],inner[j]),mi);self.face((outer[k],bottom[k],bottom[j],outer[j]),mi)
 def cylinder(self,center,axis,r,depth,n=8,mi=1,r2=None,caps=True):
  axis=Vector(axis).normalized();u=axis.orthogonal().normalized();v=axis.cross(u);c=Vector(center);r2=r if r2 is None else r2
  a=self.verts([c-axis*depth/2+r*(cos(k*2*pi/n)*u+sin(k*2*pi/n)*v) for k in range(n)])
  b=self.verts([c+axis*depth/2+r2*(cos(k*2*pi/n)*u+sin(k*2*pi/n)*v) for k in range(n)])
  for k in range(n):j=(k+1)%n;self.face((a[k],a[j],b[j],b[k]),mi)
  if caps:self.face(tuple(reversed(a)),mi);self.face(tuple(b),mi)
 def bolt(self,p,n,r=.025):
  p=Vector(p);n=Vector(n).normalized();self.cylinder(p+n*.004,n,r,.012,n=6,mi=1,r2=r*.86);self.bolts.append(tuple(p))
 def ring(self,c,axis,profile,n=48,mi=0):
  axis=Vector(axis).normalized();u=axis.orthogonal().normalized();v=axis.cross(u);c=Vector(c)
  rows=[self.verts([c+axis*d+r*(cos(k*2*pi/n)*u+sin(k*2*pi/n)*v) for k in range(n)]) for d,r in profile]
  for a,b in zip(rows,rows[1:]):
   for k in range(n):j=(k+1)%n;self.face((a[k],a[j],b[j],b[k]),mi,True)
 def box(self,c,axes,dims,mi=1):
  c=Vector(c);u,v,w=map(Vector,axes);du,dv,dw=[d/2 for d in dims];ids=self.verts([c+u*a*du+v*b*dv+w*d*dw for a,b,d in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]])
  for fs in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:self.face(tuple(ids[i] for i in fs),mi)
 def merge(self,ob,M=Matrix.Identity(4),mapmat=None):
  off=len(self.v);self.v.extend([tuple(M@v.co) for v in ob.data.vertices])
  for p in ob.data.polygons:self.face(tuple(off+i for i in p.vertices),mapmat[p.material_index] if mapmat else p.material_index,p.use_smooth)

def octpoly(x0,x1,a0,a1,cut=.035):return [(x0+cut,a0),(x1-cut,a0),(x1,a0+cut),(x1,a1-cut),(x1-cut,a1),(x0+cut,a1),(x0,a1-cut),(x0,a0+cut)]
# ------------------- layered module. Local X axis and existing node placements retained.
g=Geo()
def segmap(x,a,d=0):return (x,(.466+d)*cos(a),(.466+d)*sin(a))
g.ring((0,0,0),(1,0,0),[(-.535,.396),(.535,.396)],n=16,mi=2)
for row,(x0,x1) in enumerate([(-.475,.065),(.045,.468)]):
 for k in range(6):
  a=k*pi/3+(.045 if row else 0);poly=octpoly(x0,x1,a+.035,a+pi/3-.035,.045)
  g.patch(poly,segmap,0,th=.025,bev=.018)
  # Two seated fasteners on each shell, metallic rim + inset center.
  for xx,aa in [(x0+.085,a+.17)]:
   p=Vector(segmap(xx,aa,.012));g.bolt(p,(0,cos(aa),sin(aa)),.022)
# four protective lap tiles bridging staggered shell edges. Keep vents between them.
for k in (0,2,3,5):
 a=k*pi/3+.15
 g.patch(octpoly(-.18,.23,a,a+.48,.03),lambda x,a,d=0:segmap(x,a,d+.022),0,th=.018,bev=.012)
# two inset vent cassettes with modeled angled slats (no printed grille substitute)
for a in [pi*.75,pi*1.75]:
 n=Vector((0,cos(a),sin(a)));u=Vector((1,0,0));v=n.cross(u).normalized();c=n*.485+Vector((.14,0,0))
 g.box(c,(u,v,n),(.30,.24,.018),2)
 for du,dv,sz in [(-.168,0,(.022,.28,.025)),(.168,0,(.022,.28,.025)),(0,-.13,(.35,.022,.025)),(0,.13,(.35,.022,.025))]:g.box(c+u*du+v*dv+n*.012,(u,v,n),sz,0)
 for i in range(6):g.box(c+v*(-.095+i*.038)+n*.017,(u,v,n),(.285,.012,.022),1)
# twin exposed piston/shroud assemblies, not the old barrel surface
for a in [pi*.12,pi*1.12]:
 n=Vector((0,cos(a),sin(a)));c=n*.472
 g.cylinder(c+Vector((-.22,0,0)),(1,0,0),.037,.34,6,2)
 g.cylinder(c+Vector((-.16,0,0)),(1,0,0),.023,.34,6,1)
 for x in [-.36,.02]:g.cylinder(c+Vector((x,0,0)),(1,0,0),.048,.048,6,0)
module=g.obj('R2 layered segment');bolts_seg=g.bolts
body.data=module.data
bpy.data.objects.remove(module,do_unlink=True)
for o in segs:o.data=body.data
print('MODULE_TRIS',count(body),flush=True)
# Cost a real higher-detail option in memory only; never link/export it.
uncapped=Geo()
for a in [pi*.75,pi*1.75]:
 n=Vector((0,cos(a),sin(a)));u=Vector((1,0,0));v=n.cross(u).normalized();c=n*.520+Vector((.14,0,0))
 for sign in [-1,1]:
  for i in range(6):uncapped.cylinder(c+v*(-.09+i*.036),(u+v*sign*.55).normalized(),.0035,.30,6,1)
for row,(x0,x1) in enumerate([(-.475,.065),(.045,.468)]):
 for k in range(6):
  a=k*pi/3+pi/3-.15;uncapped.bolt(segmap(x1-.08,a,.012),(0,cos(a),sin(a)),.022)
extra_tris=sum(len(f)-2 for f in uncapped.f)
LOG['uncapped_detail_cost_study']={'additional_modeled_triangles':extra_tris,'module':count(body)+extra_tris,'module_plus_joint':count(body)+extra_tris+192,'detail':'24 six-sided crosswires plus 12 additional hex fasteners','status':'in-memory geometry cost study; not linked or exported'}

# ------------------- fitted head. Analytic shape (not another Hunyuan base).
for o in list(head.children):
 if o.type=='MESH':bpy.data.objects.remove(o,do_unlink=True)
xs=np.array([-2.03,-1.94,-1.70,-1.38,-1.03,-.65,-.30,.04]);ys=np.array([.12,.27,.36,.45,.54,.585,.56,.46]);zt=np.array([-.16,.015,.14,.285,.42,.47,.455,.36]);zb=np.array([-.29,-.40,-.455,-.47,-.465,-.445,-.415,-.36])
def hm(x,a,d=0):
 y=float(np.interp(x,xs,ys));top=float(np.interp(x,xs,zt));bot=float(np.interp(x,xs,zb));zc=(top+bot)/2;rz=(top-bot)/2
 # squared ellipse: broad plated cheeks and flattened crown, no lumpy interstitial surface
 ca=cos(a);sa=sin(a);power=.78
 return Vector((x,(y+d)*math.copysign(abs(ca)**power,ca),zc+(rz+d)*math.copysign(abs(sa)**power,sa)))
hg=Geo();hg.solid=True
# Smooth core, deliberately recessed. Density preserves the required head allocation.
rows=[]
for x in np.linspace(-2.03,.04,25):rows.append(hg.verts([hm(x,k*2*pi/48,-.080) for k in range(48)]))
for a,b in zip(rows,rows[1:]):
 for k in range(48):j=(k+1)%48;hg.face((a[k],a[j],b[j],b[k]),2,True)
hg.face(tuple(reversed(rows[0])),2);hg.face(tuple(rows[-1]),2)
# Crown and lower jaw panels, irregular lengths, each conformal rather than slabs.
for k in range(8):
 a0=k*pi/4+.012;a1=(k+1)*pi/4-.012
 if k in (0,3,4,7):cuts=[-2.025,-1.65,-1.20,-.72,-.28,.035]
 else:cuts=[-2.025,-1.78,-1.40,-.97,-.49,.035]
 for j,(x0,x1) in enumerate(zip(cuts,cuts[1:])):
  # perimeter doubled along axial edges follows the skull slope
  poly=octpoly(x0+.008,x1-.008,a0,a1,.025)
  expanded=[]
  for u,v in zip(poly,poly[1:]+poly[:1]):
   expanded.append(u)
   if abs(u[0]-v[0])>.20:expanded.append(((u[0]+v[0])/2,(u[1]+v[1])/2))
  hg.patch(expanded,hm,0,th=.020,bev=.010)
  for xx,aa in [(x0+.07,a0+.10),(x1-.07,a1-.10)]:
   if xx< -1.9:continue
   p=hm(xx,aa,.012);n=Vector((0,cos(aa),sin(aa)));hg.bolt(p,n,.017 if xx< -1.4 else .021)
# Three reference-like swept crest fins with modeled raised border strips.
for y,scale in [(-.30,.86),(0,1),(.30,.90)]:
 outline=[(-.78,.44),(-.66,.64),(-.35,.74*scale+.03),(-.22,.77*scale+.03),(-.37,.62),(-.30,.48)]
 a=hg.verts([(x,y-.015,z) for x,z in outline]);b=hg.verts([(x,y+.015,z) for x,z in outline]);hg.face(tuple(a),0);hg.face(tuple(reversed(b)),0)
 for i in range(len(a)):j=(i+1)%len(a);hg.face((a[i],b[i],b[j],a[j]),1)
 hg.box((-.51,y,.462),((1,0,0),(0,1,0),(0,0,1)),(.50,.065,.045),0)
 for x in [-.70,-.35]:hg.bolt((x,y,.49),(0,0,1),.025)
newhead=hg.obj('R2 fitted head');head.data=newhead.data;bpy.data.objects.remove(newhead,do_unlink=True);bolts_head=hg.bolts
# Boolean apertures cut through both fitted plates and core. No black decal nostrils.
def cutter(name,c,axis,r,depth,scale=None):
 q=Geo();q.cylinder(c,axis,r,depth,32,0);o=q.obj(name)
 if scale:
  for v in o.data.vertices:v.co=Vector(c)+Vector(tuple((v.co[i]-c[i])*scale[i] for i in range(3)))
 return o
# Cut the core and each closed plate independently. A Boolean on the entire
# overlapping assembly incorrectly treats bolt/plate overlaps as holes.
select(head);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.separate(type='LOOSE');bpy.ops.object.mode_set(mode='OBJECT')
headparts=[o for o in bpy.context.selected_objects if o.type=='MESH']
for side in [-1,1]:
 axis=Vector((0,side,0))
 for name,c,r,depth,scale in [('socket',Vector((-.94,side*.47,.065)),.202,.62,None),('nostril',Vector((-1.70,side*.327,-.040)),.073,.42,(1.65,1,.64))]:
  cut=cutter(name+' cutter',c,axis,r,depth,scale);cut.matrix_world=head.matrix_world.copy();bpy.context.view_layer.update()
  cb=[(min(v.co[a] for v in cut.data.vertices),max(v.co[a] for v in cut.data.vertices)) for a in range(3)]
  for part in list(headparts):
   if not part.data.vertices:continue
   pb=[(min(v.co[a] for v in part.data.vertices),max(v.co[a] for v in part.data.vertices)) for a in range(3)]
   if any(pb[a][1]<cb[a][0] or pb[a][0]>cb[a][1] for a in range(3)):continue
   select(part);mod=part.modifiers.new('machined '+name,'BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name)
   if not part.data.vertices:
    assert part is not head;headparts.remove(part);bpy.data.objects.remove(part,do_unlink=True)
  bpy.data.objects.remove(cut,do_unlink=True)
select(head)
for part in headparts:part.select_set(True)
bpy.ops.object.join();tri(head)
eyes=[]
for side in [-1,1]:
 c=Vector((-.94,side*.47,.065));axis=Vector((0,side,0))
 # Socket was cut into each independent solid above.
 eg=Geo();eg.ring(c,axis,[(.068,.214),(.077,.198),(.073,.184),(-.048,.122),(-.068,.114)],64,2)
 eg.ring(c,axis,[(.078,.204),(.083,.199),(.081,.191)],64,1)
 # Inner thin emitter ring is small and behind dark funnel lip.
 eg.ring(c,axis,[(-.040,.111),(-.034,.110),(-.034,.104),(-.042,.104)],64,3)
 eg.ring(c,axis,[(-.052,.103),(-.060,.075),(-.064,.021),(-.065,.001)],64,4)
 eg.cylinder(c+axis*(-.060),axis,.022,.007,24,3)
 # fine concentric optical tick marks and screws provide lens identity.
 for k in range(16):
  a=k*2*pi/16;rr=.097;p=c+axis*(-.046)+Vector((cos(a)*rr,0,sin(a)*rr));eg.cylinder(p,axis,.0035,.006,4,3)
 for k in range(4):
  a=k*pi/2+pi/4;p=c+axis*.079+Vector((cos(a)*.202,0,sin(a)*.202));eg.cylinder(p,axis,.008,.008,6,2)
 eye=eg.obj('R2 socket lens '+str(side),MATS+[teal,glass]);eye.parent=head;eye.matrix_parent_inverse=Matrix.Identity(4);eyes.append(eye)
 # Visible nostril: elongated socket bevel and deep black floor, cut into muzzle side.
 nc=Vector((-1.70,side*.327,-.040))
 ng=Geo();ng.ring(nc,axis,[(.043,.077),(.048,.070),(.032,.061),(-.08,.055)],32,1)
 for v in ng.v:pass
 ng.v=[tuple(nc+Vector(((p[0]-nc.x)*1.65,p[1]-nc.y,(p[2]-nc.z)*.64))) for p in ng.v]
 ng.cylinder(nc-axis*.075,axis,.060,.01,32,2)
 no=ng.obj('R2 nostril');saved=head.matrix_world.copy();head.matrix_world=Matrix.Identity(4);bpy.context.view_layer.update();select(head);no.select_set(True);bpy.ops.object.join();head.matrix_world=saved;bpy.context.view_layer.update()
# cheek cooling vents, tightly fitted and smaller than R1's large slab box
cg=Geo()
for s in [-1,1]:
 n=Vector((0,s,0));u=Vector((1,0,0));v=Vector((0,0,1));c=Vector((-.30,s*.565,-.125))
 cg.box(c,(u,v,n),(.25,.18,.025),2)
 for i in range(6):cg.box(c+Vector((-.105+i*.042,s*.019,0)),(u,v,n),(.012,.16,.026),1)
 for dx,dz,ds in [(0,-.10,(.30,.025,.025)),(0,.10,(.30,.025,.025)),(-.15,0,(.025,.21,.025)),(.15,0,(.025,.21,.025))]:cg.box(c+Vector((dx,s*.02,dz)),(u,v,n),ds,0)
co=cg.obj('R2 cheek vents');saved=head.matrix_world.copy();head.matrix_world=Matrix.Identity(4);bpy.context.view_layer.update();select(head);co.select_set(True);bpy.ops.object.join();head.matrix_world=saved;bpy.context.view_layer.update();tri(head)
if count(head)>9500:
 select(head);dec=head.modifiers.new('head retopology budget','DECIMATE');dec.ratio=9500/count(head);dec.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=dec.name);tri(head)
print('HEAD_TRIS',count(head)+sum(count(o) for o in eyes),flush=True)
# ------------------- tail: new module sections + individually plated taper.
tg=Geo()
for xx,sx,sy,ratio in [(.46,.78,.92,.68),(1.28,.67,.78,.44)]:
 tmp=bpy.data.objects.new('tail module budget copy',body.data.copy());bpy.context.collection.objects.link(tmp);select(tmp);dec=tmp.modifiers.new('tail budget','DECIMATE');dec.ratio=ratio;bpy.ops.object.modifier_apply(modifier=dec.name);tg.merge(tmp,Matrix.Translation((xx,0,0))@Matrix.Diagonal((sx,sy,sy,1)));bpy.data.objects.remove(tmp,do_unlink=True)
# preserve inline R1 recessed joints, mapped to own dark+emitter slots
jm=bpy.data.objects['Joint_00_Housing'];em=bpy.data.objects['Joint_00_GlowBars']
for x,s in [(.905,.88),(1.68,.76)]:
 M=Matrix.Translation((x,0,0))@Matrix.Diagonal((1,s,s,1));tg.merge(jm,M,{0:2});tg.merge(em,M,{0:3})
def tm(x,a,d=0):
 r=float(np.interp(x,[1.70,1.92,2.25,2.63],[.36,.33,.21,.015]));return (x,(r+d)*cos(a),(r+d)*sin(a))
for row,(x0,x1) in enumerate([(1.71,2.07),(2.055,2.61)]):
 for k in range(8):tg.patch(octpoly(x0,x1,k*pi/4+.025,(k+1)*pi/4-.025,.025),tm,0,.020,.010)
for a in [pi/2,pi*7/6,pi*11/6]:
 n=Vector((0,cos(a),sin(a)));t=Vector((0,-sin(a),cos(a)));ol=[(1.98,.29),(2.22,.26),(2.40,.43),(2.32,.44),(2.10,.34)]
 ids=tg.verts([Vector((x,0,0))+n*r-t*.010 for x,r in ol]);js=tg.verts([Vector((x,0,0))+n*r+t*.010 for x,r in ol]);tg.face(tuple(ids),0);tg.face(tuple(reversed(js)),0)
 for k in range(5):j=(k+1)%5;tg.face((ids[k],js[k],js[j],ids[j]),1)
tob=tg.obj('R2 plated tail',MATS+[em.data.materials[0]]);tail.data=tob.data;bpy.data.objects.remove(tob,do_unlink=True)
# head min and tail cap check before expensive atlas stage
print('GEOMETRY',count(head),count(body),count(tail),flush=True)
LOG['geometry_before_atlas']={'head':count(head)+sum(count(o) for o in eyes),'segment':count(body),'tail':count(tail)}
# Analytic normals on curved plate tops avoid fan-topology shading dents.
for ob in (head,body,tail):
 attr=ob.data.attributes.get('R2_surface_normal')
 if attr:
  ob.data.calc_loop_triangles();norms=[]
  for p in ob.data.polygons:
   for li in p.loop_indices:
    n=Vector(attr.data[ob.data.loops[li].vertex_index].vector)
    norms.append(tuple(n) if p.use_smooth and n.length>.5 else (0,0,0))
  ob.data.normals_split_custom_set(norms)
pre_head=count(head)+sum(count(o) for o in eyes)
pre_total=pre_head+28*count(body)+29*(count(jm)+count(em))+count(tail)
print('PRE_BAKE_BUDGET',pre_head,pre_total,flush=True)
assert 10000<=pre_head<=18000 and pre_total<=60000
# ---- atlas functions loaded from separate owned script
exec(compile((ROOT/'weather.py').read_text(),str(ROOT/'weather.py'),'exec'))
if MODE!='geometry':
 weather(head,'head',2048 if MODE=='preview' else 3072,bolts_head,eyes)
 weather(body,'segment',1536,bolts_seg)
 weather(tail,'tail',2048,[],())
# Eye opaque material slots use small constant materials; UVs still needed for tangents.
assets=[o for o in bpy.data.objects if o.type=='MESH' and o is not catcher]
for o in assets:
 tri(o)
 if not o.data.uv_layers:
  select(o);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.008);bpy.ops.object.mode_set(mode='OBJECT')
counts={o.name:count(o) for o in assets};joint=count(jm)+count(em)
rep={'head':count(head)+sum(count(o) for o in eyes),'segment':count(body),'joint':joint,'segment_plus_joint':count(body)+joint,'tail_plus_joint':count(tail)+joint,'total':sum(counts.values()),'segment_nodes':len(segs),'segment_meshes':len({o.data for o in segs})}
LOG['counts']=rep;LOG['objects']=counts
print('R2_COUNTS',json.dumps(rep),flush=True)
assert 10000<=rep['head']<=18000 and rep['segment_plus_joint']<=1600 and rep['tail_plus_joint']<=3000 and 30000<=rep['total']<=60000,rep
assert rep['segment_meshes']==1
bpy.ops.object.select_all(action='DESELECT')
for o in assets:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'snake-sectional-r2.glb'),export_format='GLB',use_selection=True,export_apply=False,export_yup=True,export_texcoords=True,export_normals=True,export_tangents=True,export_draco_mesh_compression_enable=False,export_materials='EXPORT')
# Render-only AO multiply AFTER exporting canonical PBR textures.
for m in bpy.data.materials:
 if not m.name.startswith('R2 baked'):continue
 nt=m.node_tree;bs=nt.nodes['Principled BSDF'];tx=bs.inputs['Base Color'].links[0].from_node;sep=next(n for n in nt.nodes if n.type=='SEPARATE_COLOR');mx=nt.nodes.new('ShaderNodeMixRGB');mx.blend_type='MULTIPLY';mx.inputs[0].default_value=1;nt.links.new(tx.outputs['Color'],mx.inputs[1]);nt.links.new(sep.outputs['Red'],mx.inputs[2]);nt.links.new(mx.outputs[0],bs.inputs['Base Color'])
cam=sc.camera
# Same view directions, centering and 1.12 framing margin as shipped R1.
def shot(path,loc,target,only=None):
 cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update();vis=assets if only is None else only;saved={o:o.hide_render for o in assets}
 for o in assets:o.hide_render=o not in vis
 inv=cam.matrix_world.inverted();pts=[inv@(o.matrix_world@v.co) for o in vis for v in o.data.vertices];xmin=min(p.x for p in pts);xmax=max(p.x for p in pts);ymin=min(p.y for p in pts);ymax=max(p.y for p in pts);cam.location+=cam.rotation_euler.to_quaternion()@Vector(((xmin+xmax)/2,(ymin+ymax)/2,0));cam.data.ortho_scale=max(xmax-xmin,(ymax-ymin)*sc.render.resolution_x/sc.render.resolution_y)*1.12;
 if only is None or (only and only[0] is head):
  frame=R1_FRAMES['full' if only is None else 'head'];cam.location=frame[0];cam.rotation_euler=frame[1];cam.data.ortho_scale=frame[2]
 sc.render.filepath=str(path);bpy.ops.render.render(write_still=True)
 for o,hv in saved.items():o.hide_render=hv
sc.render.image_settings.file_format='PNG';sc.render.resolution_percentage=100
if MODE!='final':
 sc.cycles.samples=32;sc.cycles.use_adaptive_sampling=False;sc.render.resolution_x=1152;sc.render.resolution_y=648;p=OUT/'previews';p.mkdir(exist_ok=True)

 if MODE!='geometry':shot(p/f'PREVIEW-{TAG}-full-body.png',(-7,-12,7),(.5,0,1.9))
 shot(p/f'PREVIEW-{TAG}-head.png',(-4,-7,5.2),(-2.2,.25,4),[head]+eyes)
 if MODE!='geometry':shot(p/f'PREVIEW-{TAG}-module.png',(-2,-7,4),(0,0,0),segs[9:12]+[c for s in segs[9:12] for c in s.children])
else:
 sc.cycles.samples=384;sc.cycles.use_adaptive_sampling=True;sc.cycles.adaptive_threshold=.01;sc.cycles.sample_clamp_indirect=3;sc.cycles.max_bounces=6;sc.cycles.diffuse_bounces=2;sc.cycles.glossy_bounces=6;sc.cycles.transmission_bounces=2;sc.cycles.transparent_max_bounces=6
 sc.render.resolution_x=1920;sc.render.resolution_y=1080;p=OUT/'captures';p.mkdir(exist_ok=True)
 shot(p/'r2-full-body.png',(-7,-12,7),(.5,0,1.9));shot(p/'r2-head-closeup.png',(-4,-7,5.2),(-2.2,.25,4),[head]+eyes)
bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('snake-sectional-r2-'+MODE+'.blend')))
(OUT/f'log-{TAG}.json').write_text(json.dumps(LOG,indent=2));print('R2_FINISHED',MODE,TAG,flush=True)
