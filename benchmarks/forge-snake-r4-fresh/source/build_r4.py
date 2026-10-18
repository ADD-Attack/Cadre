import bpy,bmesh,math,os,json,hashlib
import numpy as np
from mathutils import Vector,Matrix
from pathlib import Path
from math import sin,cos,pi
R=Path(r'\\wsl.localhost\OpenClawGateway\home\openclaw\.openclaw\workspace-studio-3d\tickets\forge-r4-fresh');O=R/'benchmarks/forge-snake-r4-fresh';BASE=R/'benchmarks/forge-snake-r3'
P={};LOG={'order':'op-forge-snake-r4b-20261018','base_sha':'7a3a2c7c3af1f4d7803ad31753231d5f728043b0','source_glb':'benchmarks/forge-snake-r3/snake-sectional-r3.glb','no_peek':True}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(BASE/'snake-sectional-r3.glb'))
sc=bpy.context.scene
head=bpy.data.objects['Head'];tail=bpy.data.objects['Tail'];body=bpy.data.objects['Segment_00'];segs=[bpy.data.objects['Segment_%02d'%i] for i in range(28)];eyes=[o for o in head.children if o.type=='MESH'];jm=bpy.data.objects['Joint_00_Housing'];em=bpy.data.objects['Joint_00_GlowBars'];assets=[o for o in bpy.data.objects if o.type=='MESH']
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


# Bright hardware is differentiated from shadowed structural liner.
steel.name='R4 edge steel';plate.name='R4 layered steel';dark.name='R4 graphite'
for m,col,rough,metal in [(steel,(.45,.48,.50),.27,.90),(plate,(.25,.28,.30),.34,.86),(dark,(.015,.019,.020),.58,.32)]:
 bs=m.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(*col,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
# R3 whole skull is shortened 20%, broadened 12%, restored height 16%; front is blunt.
SX=.80;SY=1.12;SZ=1.16
oldnorm=[Vector(n.vector) for n in head.data.corner_normals]
for v in head.data.vertices:
 x,y,z=v.co
 front=max(0,min(1,(-x-1.35)/.85))
 # Widen nose and flatten the pointed axial apex while retaining all fitted plates.
 v.co.x=x*SX+.08*front
 v.co.y=y*SY*(1+.28*front)
 v.co.z=z*SZ
 if z>.40:
  v.co.z=.40*SZ+(z-.40)*.53
  v.co.x-=.055*max(0,(z-.40)/.28)
head.data.update();head.data.normals_split_custom_set([tuple(Vector((n.x/SX,n.y/SY,n.z/SZ)).normalized()) for n in oldnorm])
# Existing optical meshes retain tessellation. Large luminous core sits flush in circular lip.
for eye in eyes:
 side=1 if sum(v.co.y for v in eye.data.vertices)>0 else -1
 for v in eye.data.vertices:
  x,y,z=v.co;dx=x+1.0622;dz=z-.0533;r=math.hypot(dx,dz)
  inner=r<.13
  core_scale=1.7 if r<.025 else 1.0
  v.co.x=-1.0622*SX+dx*(2.45*core_scale if inner else SX)
  v.co.z=.0533*SZ+dz*(2.45*core_scale if inner else SZ)
  v.co.y=side*(.625+(abs(y)-(.36 if inner else .52))*.11)
 eye.data.update()
for m in bpy.data.materials:
 bs=m.node_tree.nodes.get('Principled BSDF') if m.use_nodes else None
 if not bs:continue
 if m.name=='R2 lens teal':
  bs.inputs['Base Color'].default_value=(.005,.50,.13,1);bs.inputs['Emission Color'].default_value=(.002,1,.12,1);bs.inputs['Emission Strength'].default_value=3.5
 if m.name=='R2 lens glass':
  bs.inputs['Base Color'].default_value=(.002,.065,.015,1);bs.inputs['Metallic'].default_value=.25;bs.inputs['Roughness'].default_value=.22;bs.inputs['Emission Color'].default_value=(.002,.40,.07,1);bs.inputs['Emission Strength'].default_value=1.8
 if m.name=='R2 exposed steel':bs.inputs['Base Color'].default_value=(.38,.43,.44,1)
# Continuous 360-degree cyan joint sleeve; 48 sides, visible beyond dark shoulder housing.
vs=[];fs=[];N=48
for x in (-.032,.032):
 for i in range(N):a=2*pi*i/N;vs.append((x,.547*cos(a),.547*sin(a)))
for i in range(N):j=(i+1)%N;fs.append((i,j,N+j,N+i))
me=bpy.data.meshes.new('R4 full circumference cyan band');me.from_pydata(vs,[],fs);me.materials.append(em.data.materials[0]);me.update()
for ob in assets:
 if 'GlowBars' in ob.name:ob.data=me
tri(em)
for p in me.polygons:p.use_smooth=True
bs=me.materials[0].node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(.002,.50,.42,1);bs.inputs['Emission Color'].default_value=(.003,.95,.78,1);bs.inputs['Emission Strength'].default_value=4.8
# Reclaim only buried shell backs, the concealed axial sleeve and the old X crosswires.
# Work on original split-vertex faces, so UV/normal seams remain intact.
# Raised R3 lap plates cross the old cassette depth. Lift complete cassette boxes,
# preserving their rigid shapes, before fitting the new wire insert and dark backing.
weld=bmesh.new();weld.from_mesh(body.data);bmesh.ops.remove_doubles(weld,verts=list(weld.verts),dist=.000005);seen=set();lift_map={}
for vv in weld.verts:
 if vv in seen:continue
 stack=[vv];seen.add(vv);component=[]
 while stack:
  q=stack.pop();component.append(q)
  for e in q.link_edges:
   w=e.other_vert(q)
   if w not in seen:seen.add(w);stack.append(w)
 c=sum((v.co for v in component),Vector())/len(component);xs=[v.co.x for v in component];angle=math.atan2(c.z,c.y)%(2*pi)
 if len(component)==8 and min(xs)>-.041 and max(xs)<.322 and any(abs(angle-a)<.38 for a in [pi*.75,pi*1.75]):
  cassette_angle=min([pi*.75,pi*1.75],key=lambda a:abs(angle-a))
  delta=Vector((0,cos(cassette_angle),sin(cassette_angle)))*.065
  for v in component:lift_map[tuple(round(float(a),5) for a in v.co)]=delta
weld.free()
for v in body.data.vertices:
 k=tuple(round(float(a),5) for a in v.co)
 if k in lift_map:v.co+=lift_map[k]
body.data.update()
bm=bmesh.new();bm.from_mesh(body.data);bm.normal_update();remove=[]
# Remove complete superseded cassette backing inserts, not a subset of their split faces.
weld=bm.copy();bmesh.ops.remove_doubles(weld,verts=list(weld.verts),dist=.000005);seen=set();obsolete=set()
for vv in weld.verts:
 if vv in seen:continue
 stack=[vv];seen.add(vv);component=[]
 while stack:
  q=stack.pop();component.append(q)
  for e in q.link_edges:
   w=e.other_vert(q)
   if w not in seen:seen.add(w);stack.append(w)
 xs=[v.co.x for v in component]
 if len(component)==8 and abs(min(xs)+.01)<.0001 and abs(max(xs)-.29)<.0001:
  obsolete.update(tuple(round(float(a),5) for a in v.co) for v in component)
weld.free()
for f in bm.faces:
 if all(tuple(round(float(a),5) for a in v.co) in obsolete for v in f.verts):remove.append(f)
for f in bm.faces:
 c=f.calc_center_median();rad=Vector((0,c.y,c.z));r=rad.length
 if r>0:rad.normalize()
 if (f.material_index==0 and r<.405 and abs(f.normal.x)<.5) or (f.material_index==0 and .415<r<.48 and f.normal.dot(rad)<-.55) or (f.material_index==1 and c.x>-.01 and abs(c.y)>.30 and abs(c.z)>.30):remove.append(f)
remove=list(set(remove))
print('SEGMENT_BURIED_FACE_REMOVALS',len(remove),flush=True);LOG['segment_removed_faces']=len(remove)
bmesh.ops.delete(bm,geom=remove,context='FACES');bm.to_mesh(body.data);bm.free();body.data.update()
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

# Diamond-wire inserts are actual mesh ribbons at depth inside the inherited cassette frames.
add=Add()
for angle in [pi*.75,pi*1.75]:
 n=Vector((0,cos(angle),sin(angle)));u=Vector((1,0,0));v=n.cross(u);center=n*.572+u*.14
 # A physical recessed backing occludes the raised armor behind the fine grille.
 i=len(add.v);bc=n*.548+u*.14
 add.v.extend([tuple(bc+u*x+v*y) for x,y in [(-.15,-.115),(.15,-.115),(.15,.115),(-.15,.115)]]);add.face((i,i+1,i+2,i+3),1)
 for slope in [-1,1]:
  for k in range(-3,4):
   # Clip diagonal lines to the rectangular vent aperture.
   pts=[];b=k*.035
   for xx in [-.13,.13]:
    yy=slope*xx*.72+b
    if abs(yy)<=.105:pts.append((xx,yy))
   for yy in [-.105,.105]:
    xx=(yy-b)/(slope*.72)
    if abs(xx)<.13:pts.append((xx,yy))
   if len(pts)<2:continue
   a,bp=pts[0],pts[1];p0=center+u*a[0]+v*a[1];p1=center+u*bp[0]+v*bp[1];width=n.cross((p1-p0).normalized())*.0025;i=len(add.v)
   add.v.extend([tuple(p0-width),tuple(p1-width),tuple(p1+width),tuple(p0+width)]);add.face((i,i+1,i+2,i+3),0)
LOG['new_segment_detail_triangles']=add.join(body,'R4 modeled diamond vent wires')
for ob in segs:ob.data=body.data
# Tail distal module broadening, shorter plated tip and extra cooling fins/slats.
for v in tail.data.vertices:
 x,y,z=v.co
 if x>1.8:
  t=min(1,(x-1.8)/.8);v.co.x=1.8+(x-1.8)*.82;v.co.y*=1+.48*t;v.co.z*=1+.30*t
# Existing embedded tail bands enlarged once per unique vertex.
ix={vi for p in tail.data.polygons if p.material_index==1 for vi in p.vertices}
for vi in ix:
 v=tail.data.vertices[vi];xc=min([.905,1.68],key=lambda a:abs(v.co.x-a));v.co.x=xc+(v.co.x-xc)*7
add=Add()
for angle in [pi*.12,pi*.88]:
 add.fin([(1.73,.28),(1.85,.40),(2.11,.57),(2.26,.53),(2.11,.27)],angle,th=.025)
for k in range(6):
 add.box((1.88+k*.045,0,.265),((1,0,0),(0,1,0),(0,0,1)),(.018,.29,.025),0)
LOG['tail_added_triangles']=add.join(tail,'R4 tail finned cooling module')
# Fitted head temple hardware: additional framing and mesh-like vent slots, retains one Head node.
add=Add()
for side in [-1,1]:
 for k in range(7):
  add.box((-.36+k*.04,side*.573,-.10),((1,0,0),(0,0,1),(0,side,0)),(.016,.22,.028),0)
 for z in [-.23,.06]:add.box((-.23,side*.575,z),((1,0,0),(0,0,1),(0,side,0)),(.34,.035,.045),2)
# Seated captive fasteners identify the lowered crest as plated mechanical fins.
from mathutils.bvhtree import BVHTree
bpy.context.view_layer.update();bvh=BVHTree.FromObject(head,bpy.context.evaluated_depsgraph_get())
for y in [-.3158,0,.3158]:
 for side in [-1,1]:
  for x in [-.50,-.35]:
   hit,normal,face,distance=bvh.ray_cast(Vector((x,y+side*.06,.505)),Vector((0,-side,0)),.12)
   if hit is not None and abs(hit.y-y)<.025:add.bolt(hit+Vector((0,side*.001,0)),(0,side,0),.015)

LOG['head_added_triangles']=add.join(head,'R4 temple cooling hardware')
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
 tones=np.ones((size,size),np.float32);component_tones={}
 pos=np.zeros((size,size,3),np.float32);edge=np.full((size,size),9,np.float32);mask=np.zeros((size,size),bool)
 # Weld a COPY to detect real crease edges across glTF's UV/normal vertex splits.
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000004);bm.normal_update();bm.faces.ensure_lookup_table()
 # coordinate edge dictionary: triangulation diagonals are ignored; plate chamfers count.
 crease={}
 def key(a,b):return tuple(sorted((tuple(round(float(x),5) for x in a),tuple(round(float(x),5) for x in b))))
 for e in bm.edges:
  if not e.is_manifold or e.calc_face_angle(0)>.32:crease[key(e.verts[0].co,e.verts[1].co)]=True
 # Assign restrained independent tones to physical connected panels, never random per triangle.
 seen=set()
 for vv in bm.verts:
  if vv in seen:continue
  stack=[vv];seen.add(vv);component=[]
  while stack:
   q=stack.pop();component.append(q)
   for e in q.link_edges:
    w=e.other_vert(q)
    if w not in seen:seen.add(w);stack.append(w)
  c=sum((v.co for v in component),Vector())/len(component)
  tone=.62+.68*float(hash2(c.x,c.y+c.z,17))
  for v in component:component_tones[tuple(round(float(a),5) for a in v.co)]=tone
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
  tones[sl][inside]=component_tones.get(tuple(round(float(q),5) for q in ps[0]),1.0)
  pos[sl][inside]=(a[...,None]*ps[0]+b[...,None]*ps[1]+c[...,None]*ps[2])[inside];mask[sl]|=inside
  area=np.linalg.norm(np.cross(ps[1]-ps[0],ps[2]-ps[0]))
  for k,bar in enumerate((a,b,c)):
   aa,bb=ps[(k+1)%3],ps[(k+2)%3]
   if key(aa,bb) not in crease:continue
   d=np.maximum(bar,0)*area/max(np.linalg.norm(aa-bb),1e-9);edge[sl][inside]=np.minimum(edge[sl][inside],d[inside])
 x,y,z=pos.transpose(2,0,1);n=noise(x+y*.2,z,23,3);fine=noise(x,z+y*.1,120,5)
 # Cavity tint is restrained and neutral, AO remains separate.
 cavity=np.clip((1-ao)*.75,0,.7);carbon=oldcol[...,:3].mean(-1)<.026
 value=P.get('metal_value',.38)+noise(x+y*.3,z,2,4)*.045
 col=np.ones((size,size,4),np.float32);col[...,:3]=(value*tones)[...,None]*np.array([.96,1.00,1.025]);col[...,:3]*=1-cavity[...,None]*.23
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
 scratch=np.zeros_like(x);etch=np.zeros_like(x)
 rng=np.random.default_rng({'head':31,'segment':41,'tail':51}[kind])
 for i in range(180 if kind=='head' else 90):
  ax=rng.uniform(float(x[mask].min()),float(x[mask].max()));ay=rng.choice([-1,1])*rng.uniform(.17,.5);az=rng.uniform(-.28,.32)
  length=rng.uniform(.025,.115);t=(x-ax);line=z-az-t*rng.uniform(-.7,.3)
  scf=np.exp(-(line/.0017)**2)*np.clip(1-np.abs(t)/length,0,1)*np.exp(-((y-ay)/.09)**2)
  scratch=np.maximum(scratch,scf)
  if i%3==0:etch=np.maximum(etch,scf)
 # Longer brushed scuffs are restricted to plate edges, never an all-over mottling field.
 brush=noise(x*1.8+y*.2,z*.6,24,13)
 abrasion=np.exp(-edge/.018)*np.clip((brush-.52)*3.4,0,1)*.45
 exposed=np.clip(wear*.67+scratch*.68+abrasion,0,.83);exposed[carbon]*=.2
 col[...,:3]=col[...,:3]*(1-exposed[...,None])+np.array([.62,.65,.67])*exposed[...,None]
 col[...,:3]*=1-etch[...,None]*.48
 orm[...,1]=np.clip(.30+fine*.055+cavity*.16+grime*.16-exposed*.10,.22,.81);orm[...,2]=np.clip(.84-cavity*.10-rust*.48+exposed*.10,.12,.94);orm[carbon,1]=.67;orm[carbon,2]=.30
 # Keep baked AO-R exactly (resampled only on head); no albedo AO multiplication in GLB.
 for _ in range(6):
  grown=mask.copy()
  for sh,ax in [(1,0),(-1,0),(1,1),(-1,1)]:
   src=np.roll(mask,sh,axis=ax);fill=(~grown)&src
   for arr in (col,orm):arr[fill]=np.roll(arr,sh,axis=ax)[fill]
   grown|=fill
  mask=grown
 def save(suffix,a,linear):
  im=bpy.data.images.new('R4 '+kind+' '+suffix,size,size,alpha=False);im.colorspace_settings.name='Non-Color' if linear else 'sRGB';im.pixels.foreach_set(np.clip(a,0,1).ravel());im.filepath_raw=str(O/'textures'/('r4-'+kind+'-'+suffix+'.png'));im.file_format='PNG';im.save();im.pack();return im
 alb.image=save('albedo',col,False);oldorm=ort.image;neworm=save('ORM',orm,True)
 for t in texs:
  if t.image==oldorm:t.image=neworm
 m.name='R4 silver '+kind
 LOG.setdefault('weathering',{})[kind]={'anchors':len(anchors),'rust_fraction_gt_025':float((rust[mask]>.25).mean()),'edge_exposure_gt_025':float((exposed[mask]>.25).mean()),'source_ao_mean':float(ao[mask].mean()),'direction':'local -Z runoff; finite diagonal scratches; sharp geometric edge wear','uniform_rust_noise':False}
 print('WEATHER_READY',kind,LOG['weathering'][kind],flush=True)

# Re-author atlases from the R3 geometry and preserve original baked AO-R.
(O/'textures').mkdir(exist_ok=True)
weather(head,'head',1536,[(-1.38,.46,.1),(-1.05,-.55,.2),(-.55,.61,.23),(-.23,-.59,.1)])
weather(body,'segment',1536,[(-.39,.48,.08),(.13,-.34,.35),(-.39,-.48,-.08),(.13,.34,-.35)])
weather(tail,'tail',1536,[(.24,.35,.21),(.64,-.32,.22),(1.18,.28,.18),(1.47,-.24,.14),(2.02,.22,.14)])
# Raise inherited hardware panel tones without changing the graphite cavities.
for name,col in [('R3 machined edge steel',(.46,.49,.51)),('R3 fitted hardware gunmetal',(.27,.30,.32))]:
 m=bpy.data.materials.get(name)
 if m:m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*col,1)
for m in bpy.data.materials:
 if m.use_nodes:
  for n in m.node_tree.nodes:
   if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=.38
# Packed ORM on every opaque material, including optics/housings and modeled additions.
for m in bpy.data.materials:
 if not m.use_nodes:continue
 nt=m.node_tree;bs=nt.nodes.get('Principled BSDF')
 if not bs:continue
 if any(n.type=='TEX_IMAGE' and n.image and 'ORM' in n.image.name for n in nt.nodes):continue
 rough=bs.inputs['Roughness'].default_value;metal=bs.inputs['Metallic'].default_value
 im=bpy.data.images.new(m.name+' packed ORM',4,4,alpha=False);im.colorspace_settings.name='Non-Color';im.pixels[:]=[1,rough,metal,1]*16;im.pack();tx=nt.nodes.new('ShaderNodeTexImage');tx.image=im;sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(tx.outputs['Color'],sep.inputs[0]);nt.links.new(sep.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
 group=nt.nodes.new('ShaderNodeGroup');group.node_tree=bpy.data.node_groups.get('glTF Material Output')
 if group.node_tree:nt.links.new(sep.outputs['Red'],group.inputs['Occlusion'])
for ob in assets:
 if not ob.data.uv_layers:
  select(ob);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.005);bpy.ops.object.mode_set(mode='OBJECT')
counts={o.name:count(o) for o in assets};joint=count(jm)+count(em)
rep={'head_including_lenses':count(head)+sum(count(o) for o in eyes),'segment':count(body),'joint':joint,'segment_plus_joint':count(body)+joint,'tail':count(tail),'tail_plus_joint':count(tail)+joint,'assembly_instanced_triangles':sum(counts.values()),'segment_nodes':len(segs),'segment_shared_meshes':len({o.data for o in segs}),'housing_nodes':sum('Housing' in o.name for o in assets),'glow_nodes':sum('GlowBars' in o.name for o in assets)}
LOG['counts']=rep;LOG['objects']=counts
print('R4_COUNTS',json.dumps(rep),flush=True)
assert 10000<=rep['head_including_lenses']<=18000 and rep['segment_plus_joint']<=1600 and rep['tail_plus_joint']<=3000 and 30000<=rep['assembly_instanced_triangles']<=60000,rep
bpy.ops.object.select_all(action='DESELECT')
for ob in assets:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(O/'snake-sectional-r4-fresh.glb'),export_format='GLB',use_selection=True,export_yup=True,export_tangents=True,export_normals=True,export_texcoords=True,export_draco_mesh_compression_enable=False)
(O/'counts-and-log.json').write_text(json.dumps(LOG,indent=2))
# Canonical export first; review-only AO multiply second.
for m in bpy.data.materials:
 if not m.use_nodes:continue
 nt=m.node_tree;bs=nt.nodes.get('Principled BSDF');orm=next((n for n in nt.nodes if n.type=='TEX_IMAGE' and n.image and 'ORM' in n.image.name),None)
 if not bs or not orm:continue
 sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(orm.outputs['Color'],sep.inputs[0]);mul=nt.nodes.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1
 if bs.inputs['Base Color'].is_linked:nt.links.new(bs.inputs['Base Color'].links[0].from_socket,mul.inputs[1])
 else:mul.inputs[1].default_value=bs.inputs['Base Color'].default_value
 nt.links.new(sep.outputs['Red'],mul.inputs[2]);nt.links.new(mul.outputs[0],bs.inputs['Base Color'])
# Reconstruct exact R3 published stage, no untracked blend dependency.
settings=json.loads((BASE/'captures/r3-render-settings.json').read_text())
for spec in settings['lights']:
 dat=bpy.data.lights.new(spec['name'],'AREA');dat.energy=spec['energy'];dat.shape='DISK';dat.size=spec['size'];dat.color=spec['color'];ob=bpy.data.objects.new(spec['name'],dat);sc.collection.objects.link(ob);ob.location=spec['location'];ob.rotation_euler=spec['rotation']
world=bpy.data.worlds.new('Reference-matched neutral studio');world.use_nodes=True;sc.world=world;nt=world.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputWorld');mix=nt.nodes.new('ShaderNodeMixShader');lp=nt.nodes.new('ShaderNodeLightPath');nt.links.new(lp.outputs['Is Camera Ray'],mix.inputs[0])
for i,spec in enumerate(settings['world_backgrounds']):
 b=nt.nodes.new('ShaderNodeBackground');b.inputs['Color'].default_value=spec['color'];b.inputs['Strength'].default_value=spec['strength'];nt.links.new(b.outputs[0],mix.inputs[i+1])
nt.links.new(mix.outputs[0],out.inputs[0])
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.015));ground=bpy.context.object;ground.name='staging shadow catcher';ground.is_shadow_catcher=True
camdat=bpy.data.cameras.new('Matched R3 camera');camdat.type='ORTHO';cam=bpy.data.objects.new('Matched R3 camera',camdat);sc.collection.objects.link(cam);sc.camera=cam
sc.view_settings.view_transform=settings['view_transform'];sc.view_settings.look=settings['look'];sc.view_settings.exposure=settings['exposure'];sc.view_settings.gamma=settings['gamma']
sc.use_nodes=True;nt=sc.node_tree;nt.nodes.clear();rl=nt.nodes.new('CompositorNodeRLayers');gl=nt.nodes.new('CompositorNodeGlare');gl.glare_type='FOG_GLOW';gl.inputs['Threshold'].default_value=.4;gl.inputs['Strength'].default_value=.25;gl.inputs['Size'].default_value=.125;out=nt.nodes.new('CompositorNodeComposite');nt.links.new(rl.outputs['Image'],gl.inputs['Image']);nt.links.new(gl.outputs['Image'],out.inputs['Image'])
sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=256;sc.cycles.use_adaptive_sampling=True;sc.cycles.adaptive_threshold=.01;sc.cycles.use_denoising=True;sc.cycles.denoiser='OPENIMAGEDENOISE';sc.cycles.max_bounces=6;sc.cycles.diffuse_bounces=2;sc.cycles.glossy_bounces=4;sc.cycles.sample_clamp_indirect=3;sc.render.resolution_x=1920;sc.render.resolution_y=1080;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.threads_mode='FIXED';sc.render.threads=12
bpy.ops.outliner.orphans_purge(do_recursive=True);bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'snake-sectional-r4-fresh.blend'))
print('R4_BUILD_COMPLETE',flush=True)
