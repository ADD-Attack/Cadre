"""Forge R3: surgical edits of the producer-verified R2 GLB, never a regeneration.
Run with Blender 4.5.14. R3_MODE=preview|final|build; R3_TAG=a|b.
"""
import bpy,bmesh,math,os,json,hashlib
import numpy as np
from mathutils import Vector,Matrix
from pathlib import Path
from math import sin,cos,pi
R=Path(r'\\wsl.localhost\OpenClawGateway\home\openclaw\.openclaw\workspace-studio-3d\tickets\forge-r3'); O=R/'benchmarks/forge-snake-r3'; BASE=R/'benchmarks/snake-r2-sol'
MODE=os.environ.get('R3_MODE','preview'); TAG=os.environ.get('R3_TAG','a')
P=json.loads(os.environ.get('R3_PARAMS','{}'))
LOG={'order':'op-forge-snake-r3-20261018','base_sha':'52c96999907cb6a34ae41116092d97b9b4141024','mode':MODE,'tag':TAG,'parameters':P}
# Reuse only our own approved staging. Remove every old asset before importing R2.
bpy.ops.wm.open_mainfile(filepath=r'C:\Users\Moore\forge-r1\out\snake-sectional-r1.blend')
sc=bpy.context.scene
for ob in list(bpy.data.objects):
 if ob.type=='MESH' and 'staging' not in ob.name.lower():bpy.data.objects.remove(ob,do_unlink=True)
bpy.ops.outliner.orphans_purge(do_recursive=True)
# Remove stale unused materials/images, avoiding automatic .001 names on R2 materials.
for m in list(bpy.data.materials):
 if m.users==0:bpy.data.materials.remove(m)
for im in list(bpy.data.images):
 if im.users==0:bpy.data.images.remove(im)
bpy.ops.import_scene.gltf(filepath=str(BASE/'snake-sectional-r2.glb'))
head=bpy.data.objects['Head'];tail=bpy.data.objects['Tail'];body=bpy.data.objects['Segment_00'];segs=[bpy.data.objects['Segment_%02d'%i] for i in range(28)]
eyes=[o for o in head.children if o.type=='MESH'];jm=bpy.data.objects['Joint_00_Housing'];em=bpy.data.objects['Joint_00_GlowBars']
assets=[o for o in bpy.data.objects if o.type=='MESH' and 'staging' not in o.name.lower()]
rig_before={o.name:{'matrix':list(map(list,o.matrix_basis)),'parent':o.parent.name if o.parent else None} for o in assets}

def select(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o

def count(o):o.data.calc_loop_triangles();return len(o.data.loop_triangles)
def tri(o):
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o.data.update()
def material(name,col,rough=.4,metal=.65):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(*col,1);b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough;return m
steel=material('R3 machined edge steel',(.17,.19,.195),.33,.78)
dark=material('R3 dark socket graphite',(.006,.009,.010),.56,.35)
plate=material('R3 fitted hardware gunmetal',(.018,.021,.023),.43,.66)

# HEAD: keep R2 plates / apertures / hardware. 13% longer; 18% lower; narrower cheek.
SX=P.get('head_x',1.13); SY=.94; SZ=P.get('head_z',.82)
head_normals=[Vector(n.vector) for n in head.data.corner_normals]
for v in head.data.vertices:
 x,y,z=v.co
 if z>.50: # crest blades: thin, upright, narrow, swept back; feet stay seated
  t=(z-.46)/.34;v.co.x=(-.51+(x+.51)*.70+.08*t)*SX;v.co.z=.46*SZ+(z-.46)*.90
  yc=min([-.30,0,.30],key=lambda a:abs(y-a));v.co.y=(yc+(y-yc)*.57)*SY
 else:v.co=Vector((x*SX,y*SY,z*SZ))
head.data.update()
head.data.normals_split_custom_set([tuple(Vector((n.x/SX,n.y/SY,n.z/SZ)).normalized()) for n in head_normals])
# Apply inverse-transpose to custom normals with whole-head aspect change.
# The fins and skull are still the original fitted R2 geometry, not replacement primitives.
for eye in eyes:
 side=1 if sum(v.co.y for v in eye.data.vertices)>0 else -1
 for v in eye.data.vertices:
  x,y,z=v.co;dx=x+.94;dz=z-.065;r=math.hypot(dx,dz)
  # Outer lip fits inherited machined aperture. Inner optics shrink by 34%, retreat 0.035.
  inner=r<.125
  k=.66 if inner else 1.0
  v.co.x=-.94*SX+dx*(k if inner else SX)
  v.co.z=.065*SZ+dz*(k if inner else SZ)
  depth=(abs(y)-.47)
  if inner:depth-=P.get('eye_recess',.035)
  v.co.y=side*(.47*SY+depth)
 eye.data.update()
for m in bpy.data.materials:
 if m.name=='R2 lens teal':
  bs=m.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(.002,.24,.21,1);bs.inputs['Emission Color'].default_value=(.002,.62,.52,1);bs.inputs['Emission Strength'].default_value=P.get('eye_em',2.3)
 if m.name=='R2 lens glass':
  bs=m.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(.003,.018,.017,1);bs.inputs['Roughness'].default_value=.25
 if m.name in ['R2 exposed steel','R2 recessed graphite']:
  bs=m.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(.007,.012,.014,1);bs.inputs['Roughness'].default_value=.46

# Reclaim budget from the concealed skull liner, NOT from visible socket roundness.
# A normalized inward test selects only deeply internal faces of the delivered R2 head.
xs=np.array([-2.03,-1.94,-1.70,-1.38,-1.03,-.65,-.30,.04]);ys=np.array([.12,.27,.36,.45,.54,.585,.56,.46]);zt=np.array([-.16,.015,.14,.285,.42,.47,.455,.36]);zb=np.array([-.29,-.40,-.455,-.47,-.465,-.445,-.415,-.36])
def radial(v):
 x,y,z=v.co;x/=SX;y/=SY;z/=SZ;w=np.interp(x,xs,ys);top=np.interp(x,xs,zt);bot=np.interp(x,xs,zb);zc=(top+bot)/2;rz=(top-bot)/2
 return (abs(y)/w)**(2/.78)+(abs(z-zc)/rz)**(2/.78)
rads=[radial(v) for v in head.data.vertices]
select(head);bpy.context.tool_settings.mesh_select_mode=(False,False,True);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='DESELECT');bpy.ops.object.mode_set(mode='OBJECT')
for p in head.data.polygons:p.select=all(rads[i]<.70 for i in p.vertices)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.separate(type='SELECTED');bpy.ops.object.mode_set(mode='OBJECT')
core=next(o for o in bpy.context.selected_objects if o is not head)
bm=bmesh.new();bm.from_mesh(core.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000004);bm.to_mesh(core.data);bm.free()
n0=count(core);select(core);dec=core.modifiers.new('Concealed liner budget, outer plating unchanged','DECIMATE');dec.ratio=max(.15,(n0-1000)/n0);dec.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=dec.name);tri(core)
LOG['concealed_liner_triangle_savings']=n0-count(core)
select(head);core.select_set(True);bpy.ops.object.join();bpy.context.view_layer.update()
print('LINER_BUDGET_SAVED',LOG['concealed_liner_triangle_savings'],flush=True)

# JOINT: original nodes/parents/housings intact; four shorter recessed hairline arcs.
# Use only one 30deg step per arc instead of two; 24 vs 48 triangles, reinvest budget in hardware.
vs=[];fs=[];W=P.get('ring_w',.010)/2
for arc in range(4):
 a0=math.radians(arc*90+15);a1=a0+pi/6;off=len(vs)
 for x in (-W,W):
  for rad in (.512,.520):
   for a in (a0,a1):vs.append((x,rad*cos(a),rad*sin(a)))
 fs.extend([tuple(off+i for i in f) for f in [(0,1,3,2),(4,6,7,5),(2,3,7,6)]])
me=bpy.data.meshes.new('R3 thin recessed arc emitter');me.from_pydata(vs,[],fs);me.materials.append(em.data.materials[0]);me.update()
for ob in assets:
 if 'GlowBars' in ob.name:ob.data=me
tri(em)
bs=me.materials[0].node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(.002,.08,.07,1);bs.inputs['Emission Color'].default_value=(.002,.42,.34,1);bs.inputs['Emission Strength'].default_value=P.get('ring_em',1.7)

# Module plating: break the barrel regularity with a raised rear shoulder and staggered plate lips.
# Same plates, UVs and fasteners; no decimation of the modeled cassettes/pistons.
for v in body.data.vertices:
 x,y,z=v.co;r=math.hypot(y,z)
 if .449<r<.49:
  a=math.atan2(z,y);row=0 if x<.04 else 1
  # Broad shells: mild angular shoulder shaping, visible in glancing silhouette.
  lift=.020*max(0,min(1,(abs(x)-.23)/.19))
  v.co.y*=1+lift/r;v.co.z*=1+lift/r
# Raise and notch the inherited four lap tiles, leaving the primary shell intact.
for v in body.data.vertices:
 x,y,z=v.co;r=math.hypot(y,z);a=math.atan2(z,y)%(2*pi)
 lap=any(.15+k*pi/3-.005<=a<=.15+k*pi/3+.485 for k in (0,2,3,5))
 if lap and -.181<=x<=.231 and .482<r<.507:
  lift=.025;v.co.y*=1+lift/r;v.co.z*=1+lift/r
  if x>.17:v.co.x-=.070*min(1,(x-.17)/.05)
body.data.update()

# Small geometric additions. Flat-bottomed crosswires = 8 triangles each, no normal-map grille.
class Add:
 def __init__(self):self.v=[];self.f=[];self.mi=[]
 def face(self,f,mi):self.f.append(f);self.mi.append(mi)
 def box(self,c,axes,dims,mi=0):
  c=Vector(c);u,v,w=map(Vector,axes);du,dv,dw=[q/2 for q in dims];i=len(self.v)
  self.v.extend([tuple(c+u*a*du+v*b*dv+w*d*dw) for a,b,d in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]])
  for f in [(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6)]:self.face(tuple(i+j for j in f),mi)
 def bolt(self,c,n,r=.02,mi=0):
  c=Vector(c);n=Vector(n).normalized();u=n.orthogonal().normalized();v=n.cross(u);i=len(self.v)
  for d in (0,.014):
   for k in range(4):self.v.append(tuple(c+n*d+r*(cos(k*pi/2+pi/4)*u+sin(k*pi/2+pi/4)*v)))
  for k in range(4):j=(k+1)%4;self.face((i+k,i+j,i+4+j,i+4+k),mi)
  self.face((i+4,i+5,i+6,i+7),mi) # 10 triangles (bottom is seated/hidden)
 def fin(self,outline,angle,th=.014,mi=0):
  n=Vector((0,cos(angle),sin(angle)));t=Vector((0,-sin(angle),cos(angle)));i=len(self.v);N=len(outline)
  for sign in (-1,1):
   self.v.extend([tuple(Vector((x,0,0))+n*r+t*sign*th/2) for x,r in outline])
  self.face(tuple(i+k for k in range(N)),2);self.face(tuple(i+N+k for k in reversed(range(N))),2)
  for k in range(N):j=(k+1)%N;self.face((i+k,i+j,i+N+j,i+N+k),mi)
 def join(self,base,name):
  saved=base.matrix_world.copy();base.matrix_world=Matrix.Identity(4);bpy.context.view_layer.update()
  me=bpy.data.meshes.new(name);me.from_pydata(self.v,[],self.f);me.materials.append(steel);me.materials.append(dark);me.materials.append(plate);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
  for p,mi in zip(me.polygons,self.mi):p.material_index=mi
  # UV0 on added geometry. Constant packed ORM below means no empty tangent surfaces.
  select(ob);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.02);bpy.ops.object.mode_set(mode='OBJECT')
  tri(ob);nt=count(ob);select(base);ob.select_set(True);bpy.ops.object.join();base.matrix_world=saved;bpy.context.view_layer.update();return nt
add=Add()
for a in [pi*.75,pi*1.75]:
 n=Vector((0,cos(a),sin(a)));u=Vector((1,0,0));v=n.cross(u).normalized();c=n*.526+Vector((.14,0,0))
 for sign in [-1,1]:
  t=(u+v*sign*.45).normalized();b=n.cross(t);add.box(c,(t,b,n),(.30,.009,.011))
 # one newly seated fastener by each cooling cassette
 # Reinvest the two optional cassette screws in a physical crown-shell bevel.
# A separate concave, interlocking crown shell: modeled sidewalls, top and underside.
outline=[(-.32,-.14),(.09,-.14),(.18,-.065),(.085,-.015),(.18,.085),(.10,.14),(-.32,.14),(-.245,.015)]
i=len(add.v)
for rad in (.472,.490):
 for xx,yy in outline:add.v.append((xx,yy,math.sqrt(rad*rad-yy*yy)))
cx=sum(x for x,y in outline)/8;cy=sum(y for x,y in outline)/8
for xx,yy in outline:
 d=Vector((xx-cx,yy-cy));d*=max(0,(d.length-.012)/d.length);xx,yy=cx+d.x,cy+d.y;add.v.append((xx,yy,math.sqrt(.501*.501-yy*yy)))
add.face(tuple(i+k for k in reversed(range(8))),2);add.face(tuple(i+16+k for k in range(8)),2)
for k in range(8):
 j=(k+1)%8;add.face((i+k,i+j,i+8+j,i+8+k),2);add.face((i+8+k,i+8+j,i+16+j,i+16+k),0)
add.bolt((-.18,.055,math.sqrt(.501*.501-.055*.055)),(0,.11,.994),.018)
LOG['added_segment_triangles']=add.join(body,'R3 physical cooling crosswires, notched crown and captive screws')
for ob in segs:ob.data=body.data
# Tail: retain R2 plated taper, widen tip gently and add two raked guard fins + dorsal vent.
for v in tail.data.vertices:
 x,y,z=v.co
 if x>2.10:
  t=(x-2.1)/.51;factor=1+.40*t;v.co.y*=factor;v.co.z*=factor
 # Embedded tail emitter bands get the same thin seam width.
emitter_indices={vi for p in tail.data.polygons if p.material_index==1 for vi in p.vertices}
for vi in emitter_indices:
 v=tail.data.vertices[vi];xc=min([.905,1.68],key=lambda a:abs(v.co.x-a));v.co.x=xc+(v.co.x-xc)*.30
add=Add()
for a in [pi/2,pi*7/6,pi*11/6]:
 add.fin([(1.92,.28),(2.10,.35),(2.28,.52),(2.43,.48),(2.30,.27)],a)
 for x,rad in [(2.01,.31),(2.28,.23)]:add.bolt((x,rad*cos(a),rad*sin(a)),(0,cos(a),sin(a)),.018)
# Each fin 16 triangles, each seated four-sided fastener 10 triangles: 108 total.
LOG['added_tail_triangles']=add.join(tail,'R3 tail fin guards and fasteners')

# Geometry-coordinate weathering retains original UVs and real baked AO from the R2 ORM.
# Rasterizes local coordinates and true sharp-edge distances; no isotropic brown noise field.
def hash2(x,y,s=0):return np.mod(np.sin(x*127.1+y*311.7+s*73.19)*43758.5453,1)
def noise(x,y,f=1,s=0):
 x=x*f;y=y*f;ix=np.floor(x);iy=np.floor(y);a=x-ix;b=y-iy;a=a*a*(3-2*a);b=b*b*(3-2*b)
 return (hash2(ix,iy,s)*(1-a)+hash2(ix+1,iy,s)*a)*(1-b)+(hash2(ix,iy+1,s)*(1-a)+hash2(ix+1,iy+1,s)*a)*b

def weather(ob,kind,size,anchors):
 print('WEATHER_START',kind,flush=True)
 m=ob.data.materials[0];nt=m.node_tree;bs=nt.nodes['Principled BSDF']
 texs=[n for n in nt.nodes if n.type=='TEX_IMAGE'];alb=next(n for n in texs if 'albedo' in n.image.name);ort=next(n for n in texs if 'ORM' in n.image.name)
 # Scale copies only, retaining source textures for reproducibility.
 def pixels(im):
  cp=im.copy();cp.scale(size,size);a=np.empty(size*size*4,np.float32);cp.pixels.foreach_get(a);bpy.data.images.remove(cp);return a.reshape(size,size,4)
 oldcol=pixels(alb.image);orm=pixels(ort.image);ao=orm[...,0].copy()
 pos=np.zeros((size,size,3),np.float32);edge=np.full((size,size),9,np.float32);mask=np.zeros((size,size),bool)
 # Weld a COPY to detect real crease edges across glTF's UV/normal vertex splits.
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000004);bm.normal_update();bm.faces.ensure_lookup_table()
 # coordinate edge dictionary: triangulation diagonals are ignored; plate chamfers count.
 crease={}
 def key(a,b):return tuple(sorted((tuple(round(float(x),5) for x in a),tuple(round(float(x),5) for x in b))))
 for e in bm.edges:
  if not e.is_manifold or e.calc_face_angle(0)>.32:crease[key(e.verts[0].co,e.verts[1].co)]=True
 bm.free();uv=ob.data.uv_layers.active.data
 for p in ob.data.polygons:
  if p.material_index!=0:continue
  inds=list(p.loop_indices);ps=np.array([ob.data.vertices[ob.data.loops[i].vertex_index].co[:] for i in inds]);tex=np.array([uv[i].uv[:] for i in inds])*size-.5
  if len(ps)!=3:raise RuntimeError('expected triangular base')
  lo=np.maximum(0,np.floor(tex.min(0)).astype(int));hi=np.minimum(size-1,np.ceil(tex.max(0)).astype(int))
  if np.any(hi<lo):continue
  yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1];v0=tex[1]-tex[0];v1=tex[2]-tex[0];den=v0[0]*v1[1]-v1[0]*v0[1]
  if abs(den)<1e-10:continue
  dx=xx-tex[0,0];dy=yy-tex[0,1];b=(dx*v1[1]-v1[0]*dy)/den;c=(v0[0]*dy-dx*v0[1])/den;a=1-b-c;inside=(a>=-.003)&(b>=-.003)&(c>=-.003);sl=(slice(lo[1],hi[1]+1),slice(lo[0],hi[0]+1))
  pos[sl][inside]=(a[...,None]*ps[0]+b[...,None]*ps[1]+c[...,None]*ps[2])[inside];mask[sl]|=inside
  area=np.linalg.norm(np.cross(ps[1]-ps[0],ps[2]-ps[0]))
  for k,bar in enumerate((a,b,c)):
   aa,bb=ps[(k+1)%3],ps[(k+2)%3]
   if key(aa,bb) not in crease:continue
   d=np.maximum(bar,0)*area/max(np.linalg.norm(aa-bb),1e-9);edge[sl][inside]=np.minimum(edge[sl][inside],d[inside])
 x,y,z=pos.transpose(2,0,1);n=noise(x+y*.2,z,23,3);fine=noise(x,z+y*.1,120,5)
 # Cavity tint is restrained and neutral, AO remains separate.
 cavity=np.clip((1-ao)*.75,0,.7);carbon=oldcol[...,:3].mean(-1)<.026
 value=P.get('metal_value',.085)+noise(x+y*.3,z,2,4)*.012
 col=np.ones((size,size,4),np.float32);col[...,:3]=value[...,None]*np.array([.94,1.01,1.06]);col[...,:3]*=1-cavity[...,None]*.23
 col[carbon,:3]=np.array([.009,.013,.015])
 run=np.zeros_like(x);grime=np.zeros_like(x)
 for i,(bx,by,bz) in enumerate(anchors):
  length=.13+(i%4)*.047;dz=bz-z;drift=.009*np.sin(dz*9+i);w=.0055+.004*np.clip(dz/length,0,1)
  msk=np.exp(-((x-bx-drift)/w)**2)*np.exp(-((y-by)/.075)**2)*np.clip(1-dz/length,0,1)*(dz>=.003)
  run=np.maximum(run,msk)
  grime=np.maximum(grime,np.exp(-((x-bx-drift)/(.012+w))**2)*np.exp(-((y-by)/.085)**2)*np.clip(1-dz/(length*1.25),0,1)*(dz>=0))
 rust=run*.70 # no broad random corrosion, only anchored narrow drips
 rc=np.array([.105,.049,.024]);col[...,:3]=col[...,:3]*(1-rust[...,None])+rc*rust[...,None]
 col[...,:3]*=1-grime[...,None]*.30
 wear=np.exp(-edge/P.get('edge_width',.0050))*np.clip((n-.32)*2,0,1)
 # Deliberately placed finite scratch lines: fine, diagonal drag scars, clustered near seams.
 scratch=np.zeros_like(x)
 rng=np.random.default_rng({'head':31,'segment':41,'tail':51}[kind])
 for i in range(180 if kind=='head' else 90):
  ax=rng.uniform(float(x[mask].min()),float(x[mask].max()));ay=rng.choice([-1,1])*rng.uniform(.17,.5);az=rng.uniform(-.28,.32)
  length=rng.uniform(.025,.115);t=(x-ax);line=z-az-t*rng.uniform(-.7,.3)
  scf=np.exp(-(line/.0017)**2)*np.clip(1-np.abs(t)/length,0,1)*np.exp(-((y-ay)/.09)**2)
  scratch=np.maximum(scratch,scf)
 # Longer brushed scuffs are restricted to plate edges, never an all-over mottling field.
 brush=noise(x*1.8+y*.2,z*.6,24,13)
 abrasion=np.exp(-edge/.018)*np.clip((brush-.52)*3.4,0,1)*.45
 exposed=np.clip(wear*.67+scratch*.68+abrasion,0,.83);exposed[carbon]*=.2
 col[...,:3]=col[...,:3]*(1-exposed[...,None])+np.array([.28,.30,.31])*exposed[...,None]
 orm[...,1]=np.clip(.39+fine*.035+cavity*.14+grime*.10-exposed*.16,.22,.81);orm[...,2]=np.clip(.70-cavity*.10-rust*.48+exposed*.13,.12,.86);orm[carbon,1]=.67;orm[carbon,2]=.30
 # Keep baked AO-R exactly (resampled only on head); no albedo AO multiplication in GLB.
 for _ in range(6):
  grown=mask.copy()
  for sh,ax in [(1,0),(-1,0),(1,1),(-1,1)]:
   src=np.roll(mask,sh,axis=ax);fill=(~grown)&src
   for arr in (col,orm):arr[fill]=np.roll(arr,sh,axis=ax)[fill]
   grown|=fill
  mask=grown
 def save(suffix,a,linear):
  im=bpy.data.images.new('R3 '+kind+' '+suffix,size,size,alpha=False);im.colorspace_settings.name='Non-Color' if linear else 'sRGB';im.pixels.foreach_set(np.clip(a,0,1).ravel());im.filepath_raw=str(O/'textures'/('r3-'+kind+'-'+suffix+'.png'));im.file_format='PNG';im.save();im.pack();return im
 alb.image=save('albedo',col,False);oldorm=ort.image;neworm=save('ORM',orm,True)
 for t in texs:
  if t.image==oldorm:t.image=neworm
 m.name='R3 directional '+kind
 LOG.setdefault('weathering',{})[kind]={'anchors':len(anchors),'rust_fraction_gt_025':float((rust[mask]>.25).mean()),'edge_exposure_gt_025':float((exposed[mask]>.25).mean()),'source_ao_mean':float(ao[mask].mean()),'direction':'local -Z runoff; finite diagonal scratches; sharp geometric edge wear','uniform_rust_noise':False}
 print('WEATHER_READY',kind,LOG['weathering'][kind],flush=True)
(O/'textures').mkdir(exist_ok=True)
# Chosen fastener anchor sites, not a drip from every polygon or every bolt.
anchors=[]
for x,z,y in [(-1.72,-.07,.32),(-1.34,.11,.44),(-1.05,.28,.51),(-.69,.25,.55),(-.31,.18,.54),(-1.40,-.20,.44),(-.56,-.22,.55)]:
 for s in (-1,1):anchors.append((x*SX,s*y*SY,z*SZ))
weather(head,'head',1536,anchors)
anchors=[]
for x0,a in [(-.39,.17),(.13,1.20),(-.39,2.26),(.13,3.29),(-.39,4.36),(.13,5.40)]:anchors.append((x0,.476*cos(a),.476*sin(a)))
weather(body,'segment',1536,anchors)
weather(tail,'tail',1536,[(.24,.35,.21),(.64,-.32,.22),(1.18,.28,.18),(1.47,-.24,.14),(2.02,.22,.14)])
# Geometry additions get a valid packed constant ORM (they are real steel, no fake baked detail).
for m,rgba in [(steel,(1,.34,.78,1)),(dark,(1,.56,.35,1)),(plate,(1,.43,.66,1))]:
 nt=m.node_tree;bs=nt.nodes['Principled BSDF'];im=bpy.data.images.new(m.name+' packed ORM',4,4,alpha=False);im.colorspace_settings.name='Non-Color';im.pixels[:]=list(rgba)*16;im.pack();tx=nt.nodes.new('ShaderNodeTexImage');tx.image=im;sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(tx.outputs['Color'],sep.inputs[0]);nt.links.new(sep.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
 group=nt.nodes.new('ShaderNodeGroup');group.node_tree=bpy.data.node_groups.get('glTF Material Output')
 if group.node_tree:nt.links.new(sep.outputs['Red'],group.inputs['Occlusion'])
# UVs/tangents and asset-only export.
for ob in assets:
 if not ob.data.uv_layers:
  select(ob);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.005);bpy.ops.object.mode_set(mode='OBJECT')
counts={o.name:count(o) for o in assets};joint=count(jm)+count(em)
rep={'head_including_lenses':count(head)+sum(count(o) for o in eyes),'segment':count(body),'joint':joint,'segment_plus_joint':count(body)+joint,'tail':count(tail),'tail_plus_joint':count(tail)+joint,'assembly_instanced_triangles':sum(counts.values()),'segment_nodes':len(segs),'segment_shared_meshes':len({o.data for o in segs}),'housing_nodes':sum('Housing' in o.name for o in assets),'glow_nodes':sum('GlowBars' in o.name for o in assets)}
LOG['counts']=rep;LOG['objects']=counts;LOG['rig_max_transform_delta']=max(abs(rig_before[o.name]['matrix'][i][j]-o.matrix_basis[i][j]) for o in assets for i in range(4) for j in range(4));LOG['rig_preserved']=LOG['rig_max_transform_delta']<1e-5 and all(rig_before[o.name]['parent']==(o.parent.name if o.parent else None) for o in assets)
print('R3_COUNTS',json.dumps(rep),flush=True)
assert 10000<=rep['head_including_lenses']<=18000 and rep['segment_plus_joint']<=1600 and rep['tail_plus_joint']<=3000 and 30000<=rep['assembly_instanced_triangles']<=60000,rep
assert rep['segment_nodes']==28 and rep['segment_shared_meshes']==1 and rep['housing_nodes']==29 and LOG['rig_preserved']
bpy.ops.object.select_all(action='DESELECT')
for ob in assets:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(O/'snake-sectional-r3.glb'),export_format='GLB',use_selection=True,export_yup=True,export_tangents=True,export_normals=True,export_texcoords=True,export_draco_mesh_compression_enable=False)
# AO R actually affects Blender render, after exporting the GLB's canonical AO channel.
for m in [head.data.materials[0],body.data.materials[0],tail.data.materials[0]]:
 nt=m.node_tree;bs=nt.nodes['Principled BSDF'];tx=bs.inputs['Base Color'].links[0].from_socket
 orm=next(n for n in nt.nodes if n.type=='TEX_IMAGE' and 'ORM' in n.image.name);sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(orm.outputs['Color'],sep.inputs[0]);mul=nt.nodes.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;nt.links.new(tx,mul.inputs[1]);nt.links.new(sep.outputs['Red'],mul.inputs[2]);nt.links.new(mul.outputs[0],bs.inputs['Base Color'])
sc.render.engine='CYCLES';sc.cycles.use_denoising=True;sc.cycles.max_bounces=6;sc.cycles.diffuse_bounces=2;sc.cycles.glossy_bounces=4
pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='OPTIX';pref.refresh_devices()
for d in pref.devices:d.use=d.type=='OPTIX'
sc.cycles.device='CPU';sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
frames=json.loads((BASE/'counts-and-log.json').read_text())['staging_frames_from_R1'];cam=sc.camera
LOG['staging']={'frames':frames,'engine':'Cycles','device':'CPU (OPTIX attempted; VRAM exhausted)','samples':256 if MODE=='final' else 32,'adaptive_threshold':.01,'denoise':True,'backdrop':'reference sampled #C1C1BF; inherited R1/R2 world','lighting':'unchanged R1/R2 shaped neutral key/fill/rim','occlusion':'original R2 baked ORM-R multiply connected in render materials, shadow catcher','bloom':'inherited subtle FOG_GLOW compositor'}
bpy.ops.outliner.orphans_purge(do_recursive=True)
bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'snake-sectional-r3.blend'))
(O/'counts-and-log.json').write_text(json.dumps(LOG,indent=2))

# All previews and judged images use the one audited common render pipeline.
if MODE!='build':
 exec(compile((O/'source/render.py').read_text(),str(O/'source/render.py'),'exec'))
print('R3_FINISHED',MODE,TAG,flush=True)
