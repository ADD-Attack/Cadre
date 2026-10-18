"""R4 surgical continuation: import canonical R3 GLB into retained staging only."""
import bpy,bmesh,math,os,json
import numpy as np
from mathutils import Vector,Matrix
from pathlib import Path
from math import sin,cos,pi
R=Path(r'\\wsl.localhost\OpenClawGateway\home\openclaw\.openclaw\workspace-studio-3d\tickets\forge-r3');B=R/'benchmarks/forge-snake-r3';O=R/'benchmarks/forge-snake-r4-persistent'
TAG=os.environ.get('R4_TAG','a')
bpy.ops.wm.open_mainfile(filepath=str(B/'snake-sectional-r3.blend'));sc=bpy.context.scene
for o in list(bpy.data.objects):
 if o.type=='MESH' and 'staging' not in o.name.lower():bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.outliner.orphans_purge(do_recursive=True)
for m in list(bpy.data.materials):
 if m.users==0:bpy.data.materials.remove(m)
bpy.ops.import_scene.gltf(filepath=str(B/'snake-sectional-r3.glb'))
assets=[o for o in bpy.data.objects if o.type=='MESH' and 'staging' not in o.name.lower()]
head=bpy.data.objects['Head'];tail=bpy.data.objects['Tail'];body=bpy.data.objects['Segment_00'];eyes=[o for o in head.children if o.type=='MESH'];jm=bpy.data.objects['Joint_00_Housing'];em=bpy.data.objects['Joint_00_GlowBars']
def select(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def count(o):o.data.calc_loop_triangles();return len(o.data.loop_triangles)
def tri(o):
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o.data.update()
def uv(o):
 select(o);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.008);bpy.ops.object.mode_set(mode='OBJECT')
def mat(name,col,rough=.35,metal=.8,emission=None):
 m=bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;bs=nt.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(*col,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
 if emission:bs.inputs['Emission Color'].default_value=(*emission[0],1);bs.inputs['Emission Strength'].default_value=emission[1]
 im=bpy.data.images.new(name+' packed ORM',4,4,alpha=False);im.colorspace_settings.name='Non-Color';im.pixels[:]=[1,rough,metal,1]*16;im.pack();tx=nt.nodes.new('ShaderNodeTexImage');tx.image=im;sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(tx.outputs['Color'],sep.inputs[0]);nt.links.new(sep.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sep.outputs['Blue'],bs.inputs['Metallic']);g=nt.nodes.new('ShaderNodeGroup');g.node_tree=bpy.data.node_groups.get('glTF Material Output');nt.links.new(sep.outputs['Red'],g.inputs['Occlusion']);return m
steel=mat('R4 satin silver edge steel',(.18,.20,.21),.3,.83);dark=mat('R4 graphite recess',(.016,.023,.027),.5,.45);plate=mat('R4 titanium plated fin',(.07,.08,.085),.36,.8)
iris=mat('R4 green iris recess',(.008,.06,.018),.28,.6,((.005,.5,.07),.4))
green=mat('R4 luminous green eye',(.008,.32,.10),.26,.25,((.015,1,.24),3.2));core=mat('R4 bright green optical core',(.06,.40,.12),.23,.2,((.15,1,.35),2.4));cyan=mat('R4 continuous cyan joint band',(.005,.22,.28),.3,.25,((.001,.70,1),2.1))
P={};LOG={}
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
 value=P.get('metal_value',.27)+noise(x+y*.3,z,2,4)*.012
 col=np.ones((size,size,4),np.float32);col[...,:3]=value[...,None]*np.array([.94,1.01,1.06]);col[...,:3]*=1-cavity[...,None]*.23
 col[carbon,:3]=np.array([.009,.013,.015])
 run=np.zeros_like(x);grime=np.zeros_like(x)
 for i,(bx,by,bz) in enumerate(anchors):
  length=.13+(i%4)*.047;dz=bz-z;drift=.009*np.sin(dz*9+i);w=.0055+.004*np.clip(dz/length,0,1)
  msk=np.exp(-((x-bx-drift)/w)**2)*np.exp(-((y-by)/.075)**2)*np.clip(1-dz/length,0,1)*(dz>=.003)
  run=np.maximum(run,msk)
  grime=np.maximum(grime,np.exp(-((x-bx-drift)/(.012+w))**2)*np.exp(-((y-by)/.085)**2)*np.clip(1-dz/(length*1.25),0,1)*(dz>=0))
 rust=run*.85 # no broad random corrosion, only anchored narrow drips
 rc=np.array([.07,.055,.04]);col[...,:3]=col[...,:3]*(1-rust[...,None])+rc*rust[...,None]
 col[...,:3]*=1-grime[...,None]*.30
 wear=np.exp(-edge/P.get('edge_width',.0050))*np.clip((n-.32)*2,0,1)
 # Deliberately placed finite scratch lines: fine, diagonal drag scars, clustered near seams.
 scratch=np.zeros_like(x)
 rng=np.random.default_rng({'head':31,'segment':41,'tail':51}[kind])
 for i in range(60 if kind=='head' else 28):
  ax=rng.uniform(float(x[mask].min()),float(x[mask].max()));ay=rng.choice([-1,1])*rng.uniform(.17,.5);az=rng.uniform(-.28,.32)
  length=rng.uniform(.018,.075);t=(x-ax);line=z-az-t*rng.uniform(-.7,.3)
  scf=np.exp(-(line/.0008)**2)*np.clip(1-np.abs(t)/length,0,1)*np.exp(-((y-ay)/.09)**2)
  scratch=np.maximum(scratch,scf)
 # Longer brushed scuffs are restricted to plate edges, never an all-over mottling field.
 brush=noise(x*1.8+y*.2,z*.6,24,13)
 abrasion=np.exp(-edge/.018)*np.clip((brush-.52)*3.4,0,1)*.45
 exposed=np.clip(wear*.67+scratch*.68+abrasion,0,.83);exposed[carbon]*=.2
 col[...,:3]=col[...,:3]*(1-exposed[...,None])+np.array([.52,.54,.55])*exposed[...,None]
 orm[...,1]=np.clip(.43+fine*.035+cavity*.14+grime*.10-exposed*.16,.22,.81);orm[...,2]=np.clip(.70-cavity*.10-rust*.48+exposed*.13,.12,.86);orm[carbon,1]=.67;orm[carbon,2]=.30
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
 m.name='R4 directional silver '+kind
 for n in nt.nodes:
  if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=.35
 LOG.setdefault('weathering',{})[kind]={'anchors':len(anchors),'rust_fraction_gt_025':float((rust[mask]>.25).mean()),'edge_exposure_gt_025':float((exposed[mask]>.25).mean()),'source_ao_mean':float(ao[mask].mean()),'direction':'local -Z runoff; finite diagonal scratches; sharp geometric edge wear','uniform_rust_noise':False}
 print('WEATHER_READY',kind,LOG['weathering'][kind],flush=True)

weather(head,'head',1536,[(-1.9,.30,.0),(-1.5,-.40,.2),(-1.1,.50,.2),(-.6,-.54,.25),(-.3,.52,.20)])
weather(body,'segment',1536,[(-.39,.45,.17),(.13,-.32,.35),(-.39,-.45,-.17),(.13,.32,-.35)])
weather(tail,'tail',1536,[(.24,.35,.21),(.64,-.32,.22),(1.18,.28,.18),(1.47,-.24,.14),(2.02,.22,.14)])

# Recolor the embedded R3 texture, keeping directional runoff/scratches and baked AO.
# Panel tone variations are assigned by connected physical panel, not an all-over noise field.
for ob,kind in [(head,'head'),(body,'segment'),(tail,'tail')]:
 m=ob.data.materials[0];nt=m.node_tree;bs=nt.nodes['Principled BSDF'];nodes=[n for n in nt.nodes if n.type=='TEX_IMAGE'];alb=next(n for n in nodes if 'albedo' in n.image.name);ort=next(n for n in nodes if 'ORM' in n.image.name)
 w,h=alb.image.size;a=np.empty(w*h*4,np.float32);alb.image.pixels.foreach_get(a);a=a.reshape(h,w,4);lum=a[...,:3].mean(-1);carbon=lum<.025
 # Neutral silver with preserved light scratches and dark finite drips.
 # Directional silver already rebuilt above; retain its actual scratch/runoff contrast.
 # A welded COPY classifies plates without touching delivered custom normals/UVs.
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000004);seen=set();panels=[]
 for v in bm.verts:
  if v in seen:continue
  todo=[v];seen.add(v);vs=[];fs=set()
  while todo:
   q=todo.pop();vs.append(q);fs.update(q.link_faces)
   for e in q.link_edges:
    z=e.other_vert(q)
    if z not in seen:seen.add(z);todo.append(z)
  lo=Vector(tuple(min(v.co[i] for v in vs) for i in range(3)));hi=Vector(tuple(max(v.co[i] for v in vs) for i in range(3)))
  if sum(len(f.verts)-2 for f in fs)>=34 and max(hi-lo)>.18:panels.append(((lo+hi)/2,lo,hi))
 bm.free();uvs=ob.data.uv_layers.active.data
 # Rasterize per-face panel tone into retained UV0. Stable spatial classification.
 for p in ob.data.polygons:
  if p.material_index!=0:continue
  pts=np.array([ob.data.vertices[ob.data.loops[i].vertex_index].co[:] for i in p.loop_indices]);c=pts.mean(0)
  candidates=[(np.linalg.norm(c-np.array(cc)),cc) for cc,lo,hi in panels if all(lo[i]-.0001<=c[i]<=hi[i]+.0001 for i in range(3))]
  if not candidates:continue
  cc=min(candidates,key=lambda v:v[0])[1];factor=.80+.38*((sin(cc.x*17+cc.y*23+cc.z*31)*43758.5453)%1)
  tex=np.array([uvs[i].uv[:] for i in p.loop_indices])*[w,h]-.5;lo=np.maximum(0,np.floor(tex.min(0)).astype(int));hi=np.minimum([w-1,h-1],np.ceil(tex.max(0)).astype(int))
  if np.any(hi<lo):continue
  yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1];u=tex[1]-tex[0];v=tex[2]-tex[0];den=u[0]*v[1]-v[0]*u[1]
  if abs(den)<1e-10:continue
  dx=xx-tex[0,0];dy=yy-tex[0,1];b=(dx*v[1]-v[0]*dy)/den;c2=(u[0]*dy-dx*u[1])/den;inside=(b>=0)&(c2>=0)&(b+c2<=1);sl=(slice(lo[1],hi[1]+1),slice(lo[0],hi[0]+1));a[sl][inside,:3]*=factor
 im=bpy.data.images.new('R4 silver '+kind+' albedo',w,h,alpha=False);im.colorspace_settings.name='sRGB';im.pixels.foreach_set(a.ravel());im.filepath_raw=str(O/'textures'/('r4-'+kind+'-albedo.png'));im.file_format='PNG';im.save();im.pack();alb.image=im
 # Smooth metallic steel, retain rougher scratches/grime instead of uniformly matte.
 old=ort.image;w,h=old.size;q=np.empty(w*h*4,np.float32);old.pixels.foreach_get(q);q=q.reshape(h,w,4);q[...,1]=np.clip(q[...,1]-.025,.23,.72);q[...,2]=np.clip(q[...,2]+.12,.35,.91)
 im=bpy.data.images.new('R4 '+kind+' packed ORM',w,h,alpha=False);im.colorspace_settings.name='Non-Color';im.pixels.foreach_set(q.ravel());im.filepath_raw=str(O/'textures'/('r4-'+kind+'-ORM.png'));im.file_format='PNG';im.save();im.pack()
 for n in nodes:
  if n.image==old:n.image=im
 m.name='R4 directional silver '+kind
 for n in nt.nodes:
  if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=.35
 print('R4_SILVER_READY',kind,flush=True)
# Head: shorten 21%, broaden 12%, widen frontal muzzle; keep its layered skull topology.
# Smooth deformation applies to fitted plates, vents and bolts together.
head.data.materials.append(plate)
for p in head.data.polygons:
 if all(head.data.vertices[i].co.z>.35 and -.90<head.data.vertices[i].co.x<-.24 for i in p.vertices):p.material_index=len(head.data.materials)-1
normalcopy=[Vector(n.vector) for n in head.data.corner_normals]
def skull(v):
 x,y,z=v;front=max(0,min(1,(-x-1.45)/.82));ys=1.12+front*.52;xx=x*.79
 if x < -1.85:xx=-1.85*.79+(x+1.85)*.36
 zz=z*1.05
 if z>.40:zz=.42+(z-.40)*.56;xx=min(xx,-.28)
 return Vector((xx,y*ys,zz))
for v in head.data.vertices:v.co=skull(v.co)
head.data.update();head.data.normals_split_custom_set([tuple(Vector((n.x/.79,n.y/1.12,n.z/1.05)).normalized()) for n in normalcopy])
# Full circular flush optics replace only meshes of the same two inherited nodes.
for eye in eyes:
 side=1 if sum(v.co.y for v in eye.data.vertices)>0 else -1;vs=[];fs=[];mis=[];N=96
 rings=[(.235,.565),(.230,.580),(.213,.586),(.205,.586),(.185,.589),(.175,.593),(.150,.595),(.095,.597)]
 for r,d in rings:
  for k in range(N):
   a=2*pi*k/N;vs.append((-.94*1.13*.79+r*cos(a),side*(d+.05),.065*.82*1.05+r*sin(a)))
 for j in range(len(rings)-1):
  for k in range(N):fs.append((j*N+k,j*N+(k+1)%N,(j+1)*N+(k+1)%N,(j+1)*N+k));mis.append([0,0,1,1,2,4,4][j])
 vs.append((-.94*1.13*.79,side*.647,.065*.82*1.05))
 for k in range(N):fs.append((7*N+k,7*N+(k+1)%N,len(vs)-1));mis.append(3)
 # Twenty-four physical radial iris ticks; seated, not texture-printed.
 for k in range(24):
  a=2*pi*k/24;u=Vector((cos(a),0,sin(a)));v=Vector((-sin(a),0,cos(a)));n=Vector((0,side,0));c=Vector((-.94*1.13*.79,side*.649,.065*.82*1.05))+u*.139;i=len(vs)
  for aa,bb,dd in [(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]:vs.append(tuple(c+u*aa*.011+v*bb*.0025+n*dd*.003))
  for f in [(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:fs.append(tuple(i+j for j in f));mis.append(2)
 me=bpy.data.meshes.new('R4 flush circular optical assembly');me.from_pydata(vs,[],fs)
 for m in [steel,dark,green,core,iris]:me.materials.append(m)
 for p,i in zip(me.polygons,mis):p.material_index=i;p.use_smooth=True
 eye.data=me;uv(eye);tri(eye)
# Joint emitters are continuous cylindrical ribbons; edge walls are seated inside housing.
# 36 sides preserve roundness for 72 triangles. Restore the original internal tube to close exposed gaps.
vs=[];fs=[];N=36
for x in [-.033,.033]:
 for k in range(N):a=2*pi*k/N;vs.append((x,.543*cos(a),.543*sin(a)))
for k in range(N):fs.append((k,(k+1)%N,N+(k+1)%N,N+k))
me=bpy.data.meshes.new('R4 36-sided full circumference cyan ribbon');me.from_pydata(vs,[],fs);me.materials.append(cyan)
for p in me.polygons:p.use_smooth=True
for o in assets:
 if 'GlowBars' in o.name:o.data=me
uv(em);tri(em)
jm.data.materials[0]=dark
# Housing remains its original 144-triangle dark rim. Remove R3's 86-triangle bolt-on X/crown.
bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index>0],context='FACES');bm.to_mesh(body.data);bm.free();body.data.update()
# Correct the inherited lap-plate/cassette intersection as whole welded components.
bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000004);seen=set();moves={}
for v in bm.verts:
 if v in seen:continue
 todo=[v];seen.add(v);vs2=[];fs2=set()
 while todo:
  q=todo.pop();vs2.append(q);fs2.update(q.link_faces)
  for e in q.link_edges:
   z=e.other_vert(q)
   if z not in seen:seen.add(z);todo.append(z)
 lo=min(v.co.x for v in vs2);hi=max(v.co.x for v in vs2);c=sum((v.co for v in vs2),Vector())/len(vs2);nt=sum(len(f.verts)-2 for f in fs2)
 if nt!=12 or lo<-.041 or hi>.321:continue
 for a in [pi*.75,pi*1.75]:
  n=Vector((0,cos(a),sin(a)));t=Vector((0,-sin(a),cos(a)))
  if .47<c.dot(n)<.55 and abs(c.dot(t))<.17:
   for q in vs2:moves[tuple(round(float(v),5) for v in q.co)]=n*.04
bm.free()
for v in body.data.vertices:
 d=moves.get(tuple(round(float(q),5) for q in v.co))
 if d is not None:v.co+=d
body.data.update()
# Expose the inherited telescoping piston sets rather than adding printed machinery.
rod_slot=len(body.data.materials);body.data.materials.append(steel);collar_slot=len(body.data.materials);body.data.materials.append(plate);material_moves={}
bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000004);seen=set();moves={}
for v in bm.verts:
 if v in seen:continue
 todo=[v];seen.add(v);vs2=[];fs2=set()
 while todo:
  q=todo.pop();vs2.append(q);fs2.update(q.link_faces)
  for e in q.link_edges:
   z=e.other_vert(q)
   if z not in seen:seen.add(z);todo.append(z)
 c=sum((v.co for v in vs2),Vector())/len(vs2);nt=sum(len(f.verts)-2 for f in fs2)
 if nt!=20 or not -.42<c.x<.075:continue
 a=math.atan2(c.z,c.y)%(2*pi)
 if min(abs(a-.38),abs(a-(pi+.38)))<.075:
  n=Vector((0,cos(a),sin(a)))
  for q in vs2:
   key=tuple(round(float(v),5) for v in q.co);moves[key]=n*.025;material_moves[key]=rod_slot if max(v.co.x for v in vs2)-min(v.co.x for v in vs2)>.20 else collar_slot
bm.free()
for p in body.data.polygons:
 keys=[tuple(round(float(q),5) for q in body.data.vertices[i].co) for i in p.vertices]
 if all(k in material_moves for k in keys):p.material_index=material_moves[keys[0]]
for v in body.data.vertices:
 d=moves.get(tuple(round(float(q),5) for q in v.co))
 if d is not None:v.co+=d
body.data.update()
# New lattice crossbars over delivered six-slat cassettes: 2 cassettes x3 bars x8 tris.
class Add:
 def __init__(self):self.v=[];self.f=[];self.mi=[]
 def face(self,f,mi=0):self.f.append(f);self.mi.append(mi)
 def box(self,c,axes,dims,mi=0):
  c=Vector(c);u,v,w=map(Vector,axes);du,dv,dw=[q/2 for q in dims];i=len(self.v)
  self.v.extend([tuple(c+u*a*du+v*b*dv+w*d*dw) for a,b,d in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]])
  for f in [(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6)]:self.face(tuple(i+j for j in f),mi)
 def bolt(self,c,n,r=.02,mi=0):
  c=Vector(c);n=Vector(n).normalized();u=n.orthogonal().normalized();v=n.cross(u);i=len(self.v)
  for d in (0,.012):
   for k in range(4):self.v.append(tuple(c+n*d+r*(cos(k*pi/2+pi/4)*u+sin(k*pi/2+pi/4)*v)))
  for k in range(4):j=(k+1)%4;self.face((i+k,i+j,i+4+j,i+4+k),mi)
  self.face((i+4,i+5,i+6,i+7),mi)
 def fin(self,outline,a,th=.025,mi=2):
  n=Vector((0,cos(a),sin(a)));t=Vector((0,-sin(a),cos(a)));i=len(self.v);N=len(outline)
  for sign in (-1,1):self.v.extend([tuple(Vector((x,0,0))+n*r+t*sign*th/2) for x,r in outline])
  self.face(tuple(i+k for k in range(N)),mi);self.face(tuple(i+N+k for k in reversed(range(N))),mi)
  for k in range(N):j=(k+1)%N;self.face((i+k,i+j,i+N+j,i+N+k),0)
 def join(self,base,name):
  saved=base.matrix_world.copy();base.matrix_world=Matrix.Identity(4);bpy.context.view_layer.update();me=bpy.data.meshes.new(name);me.from_pydata(self.v,[],self.f)
  for m in [steel,dark,plate,cyan]:me.materials.append(m)
  for p,i in zip(me.polygons,self.mi):p.material_index=i
  ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);uv(ob);tri(ob);nt=count(ob);select(base);ob.select_set(True);bpy.ops.object.join();base.matrix_world=saved;bpy.context.view_layer.update();return nt
# Short crest blades receive fitted inset plates and surface-seated rivets.
bm=bmesh.new();bm.from_mesh(head.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000004);seen=set();fins=[]
for v in bm.verts:
 if v in seen:continue
 todo=[v];seen.add(v);vs2=[];fs2=set()
 while todo:
  q=todo.pop();vs2.append(q);fs2.update(q.link_faces)
  for e in q.link_edges:
   z=e.other_vert(q)
   if z not in seen:seen.add(z);todo.append(z)
 if sum(len(f.verts)-2 for f in fs2)==20 and min(v.co.z for v in vs2)>.35 and max(v.co.z for v in vs2)>.48:
  pts=list(set((round(v.co.x,5),round(v.co.z,5)) for v in vs2));cx=sum(x for x,z in pts)/len(pts);cz=sum(z for x,z in pts)/len(pts);pts.sort(key=lambda v:math.atan2(v[1]-cz,v[0]-cx));cy=sum(v.co.y for v in vs2)/len(vs2);fins.append((pts,cx,cy,cz))
bm.free();add=Add()
for pts,cx,cy,cz in fins:
 i=len(add.v);add.fin([(cx+(x-cx)*.72,cz+(z-cz)*.72) for x,z in pts],pi/2,.05)
 for j in range(i,len(add.v)):a=list(add.v[j]);a[1]+=cy;add.v[j]=tuple(a)
if add.v:add.join(head,'R4 fitted crest inset plates')
add=Add()
for pts,cx,cy,cz in fins:
 for dx in [-.045,.045]:
  origin=Vector((cx+dx,cy-.10,cz));hit,p,n,index=head.ray_cast(origin,Vector((0,1,0)),distance=.2)
  if hit and abs(p.y-cy)<.04:add.bolt(p,n,.012)
if add.v:add.join(head,'R4 surface seated crest rivets')
# Budget: 72-triangle emitter +144 housing +1384 segment (including original internal tube) =1600 exact.
add=Add()
for a in [pi*.75,pi*1.75]:
 n=Vector((0,cos(a),sin(a)));u=Vector((1,0,0));v=n.cross(u).normalized()
 for x in [.055,.14,.225]:add.box(n*.567+Vector((x,0,0)),(v,u,n),(.215,.009,.010),0)
add.join(body,'R4 modeled cross-lattice grille')
for o in assets:
 if o.name.startswith('Segment_'):o.data=body.data
# Tail: remove distal pointed row, replace with blunt eight-sided finned terminal mechanics.
# Preserve near tail modules and hierarchy; the old tip's 320 tris fund the new terminal.
bm=bmesh.new();bm.from_mesh(tail.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if (all(v.co.x>=2.054 for v in f.verts) or any(v.co.x>2.50 for v in f.verts)) and f.material_index==0],context='FACES');bm.to_mesh(tail.data);bm.free()
# Thicken the inherited embedded emitter dashes before adding full external ribbons.
bm=bmesh.new();bm.from_mesh(tail.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index==1],context='FACES');bm.to_mesh(tail.data);bm.free()
add=Add()
for xc,rad in [(.905,.481),(1.68,.416)]:
 i=len(add.v);N=24
 for x in [xc-.031,xc+.031]:
  for k in range(N):a=2*pi*k/N;add.v.append((x,rad*cos(a),rad*sin(a)))
 for k in range(N):add.face((i+k,i+(k+1)%N,i+N+(k+1)%N,i+N+k),3)
# Mechanical end-cap: stepped, not conical.
i=len(add.v);N=8
for x,r in [(2.03,.275),(2.18,.245),(2.43,.18),(2.48,.16)]:
 for k in range(N):a=2*pi*k/N+pi/8;add.v.append((x,r*cos(a),r*sin(a)))
for j in range(3):
 for k in range(N):add.face((i+j*N+k,i+j*N+(k+1)%N,i+(j+1)*N+(k+1)%N,i+(j+1)*N+k),2 if j!=1 else 0)
add.face(tuple(i+3*N+k for k in range(N)),1)
for a in [pi/2,pi*7/6,pi*11/6]:
 add.fin([(2.05,.255),(2.13,.38),(2.34,.37),(2.44,.19)],a,.035)
 add.bolt((2.19,.38*cos(a),.38*sin(a)),(0,cos(a),sin(a)),.025)
# Raised top cooling slats seated over terminal plate.
for x in [2.08,2.14,2.20,2.26]:add.box((x,0,float(np.interp(x,[2.03,2.18,2.43],[.275,.245,.18]))*cos(pi/8)+.008),( (1,0,0),(0,1,0),(0,0,1)),(.018,.22,.024),1)
for side in [-1,1]:
 add.box((2.35,side*.225,.07),((1,0,0),(0,1,0),(0,0,1)),(.05,.12,.065),2)
 i=len(add.v);N=6
 for x,r in [(2.0,.026),(2.07,.045),(2.16,.045),(2.35,.022)]:
  for k in range(N):a=2*pi*k/N;add.v.append((x,side*.255+r*cos(a),.07+r*sin(a)))
 for j in range(3):
  for k in range(N):add.face((i+j*N+k,i+j*N+(k+1)%N,i+(j+1)*N+(k+1)%N,i+(j+1)*N+k),0 if j==2 else 2)
add.join(tail,'R4 finned blunt mechanical tail module')
# Existing R3 constant bolt-on materials also become visibly silver.
for m in bpy.data.materials:
 if m.name in ['R3 machined edge steel','R3 fitted hardware gunmetal']:
  bs=m.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(.12,.135,.14,1)
# All asset primitives keep UV0 and explicit tangents.
for ob in assets:
 if not ob.data.uv_layers:uv(ob)
counts={o.name:count(o) for o in assets};joint=count(jm)+count(em)
rep={'head':count(head)+sum(count(o) for o in eyes),'segment':count(body),'joint':joint,'segment_plus_joint':count(body)+joint,'tail':count(tail),'tail_plus_joint':count(tail)+joint,'assembly_triangles':sum(counts.values()),'mesh_nodes':len(assets),'segment_nodes':28,'housing_nodes':29,'emitter_nodes':29}
print('R4_COUNTS',json.dumps(rep),flush=True)
assert 10000<=rep['head']<=18000 and rep['segment_plus_joint']<=1600 and rep['tail_plus_joint']<=3000 and 30000<=rep['assembly_triangles']<=60000,rep
bpy.ops.object.select_all(action='DESELECT')
for ob in assets:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(O/'snake-sectional-r4.glb'),export_format='GLB',use_selection=True,export_yup=True,export_tangents=True,export_normals=True,export_texcoords=True,export_draco_mesh_compression_enable=False)
# Review-only actual ORM AO shading, after canonical packed export.
for ob in [head,body,tail]:
 m=ob.data.materials[0];nt=m.node_tree;bs=nt.nodes['Principled BSDF'];tx=bs.inputs['Base Color'].links[0].from_socket;orm=next(n for n in nt.nodes if n.type=='TEX_IMAGE' and 'ORM' in n.image.name);sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(orm.outputs['Color'],sep.inputs[0]);mul=nt.nodes.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;nt.links.new(tx,mul.inputs[1]);nt.links.new(sep.outputs['Red'],mul.inputs[2]);nt.links.new(mul.outputs[0],bs.inputs['Base Color'])
bpy.context.preferences.filepaths.save_version=0;bpy.ops.outliner.orphans_purge(do_recursive=True);bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'snake-sectional-r4.blend'))
(O/'counts-and-log.json').write_text(json.dumps({'order':'op-forge-snake-r4a-20261018','base_commit':'7a3a2c7c3af1f4d7803ad31753231d5f728043b0','counts_blender':rep,'objects':counts,'weathering':LOG.get('weathering',{}),'build_tag':TAG,'input':'canonical R3 GLB; retained blend for staging only','no_peek':'Only own R3 base, own workspace and reference used'},indent=2))
print('R4_BUILD_COMPLETE',flush=True)
