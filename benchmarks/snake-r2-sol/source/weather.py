"""Geometry-aware PBR weathering. AO is ray-baked, never claimed procedural AO.
Color is clean paint/oxidation/wear only; AO remains separate in ORM-R.
"""
def hash2(x,y,s=0):return np.mod(np.sin(x*127.1+y*311.7+s*73.19)*43758.5453,1)
def noise(x,y,f=1,s=0):
 x=x*f;y=y*f;ix=np.floor(x);iy=np.floor(y);a=x-ix;b=y-iy;a=a*a*(3-2*a);b=b*b*(3-2*b)
 return (hash2(ix,iy,s)*(1-a)+hash2(ix+1,iy,s)*a)*(1-b)+(hash2(ix,iy+1,s)*(1-a)+hash2(ix+1,iy+1,s)*a)*b

def weather(o,kind,size,anchors,extra=()):
 print('WEATHER_START',kind,size,flush=True);select(o);tri(o);old=list(o.data.materials)
 # One UV0 atlas for every opaque surface; no stacked trim UVs.
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.0015);bpy.ops.object.mode_set(mode='OBJECT')
 aoim=bpy.data.images.new(kind+' actual baked AO',size,size,alpha=False);aoim.colorspace_settings.name='Non-Color';temp=[]
 for m in set(old):
  if not m:continue
  n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=aoim;m.node_tree.nodes.active=n;temp.append((m,n))
 saved={ob:ob.hide_render for ob in bpy.data.objects};keep={o,*extra}
 for ob in bpy.data.objects:ob.hide_render=ob not in keep
 sc.cycles.samples=96;sc.world.light_settings.distance=.22;sc.render.bake.use_selected_to_active=False;sc.render.bake.target='IMAGE_TEXTURES';select(o);bpy.ops.object.bake(type='AO',margin=8)
 for ob,v in saved.items():ob.hide_render=v
 for m,n in temp:m.node_tree.nodes.remove(n)
 ao=np.array(aoim.pixels[:],np.float32).reshape(size,size,4)[...,0].copy();bpy.data.images.remove(aoim)
 # Signed dihedral edge distances; connected component identity gives uniform paint per plate.
 bm=bmesh.new();bm.from_mesh(o.data);bm.faces.ensure_lookup_table();bm.verts.ensure_lookup_table();bm.normal_update();ef={};comps={};seen=set();cid=0
 for v in bm.verts:
  if v.index in seen:continue
  todo=[v];seen.add(v.index)
  while todo:
   q=todo.pop()
   for f in q.link_faces:comps[f.index]=cid
   for e in q.link_edges:
    w=e.other_vert(q)
    if w.index not in seen:seen.add(w.index);todo.append(w)
  cid+=1
 for f in bm.faces:
  vs=list(f.verts);fl=[]
  for k in range(3):
   a,b=vs[(k+1)%3],vs[(k+2)%3];e=next(e for e in a.link_edges if e.other_vert(a)==b)

   if len(e.link_faces)==2 and all(q.smooth for q in e.link_faces):fl.append(0);continue
   ang=e.calc_face_angle_signed(0) if e.is_manifold else 1.0;fl.append(1 if ang>.30 else (-1 if ang<-.30 else 0))
  ef[f.index]=fl
 bm.free()
 pos=np.zeros((size,size,3),np.float32);dcv=np.full((size,size),9.,np.float32);dcc=dcv.copy();identity=np.zeros((size,size),np.float32);typ=np.zeros((size,size),np.int8);mask=np.zeros((size,size),bool)
 uv=o.data.uv_layers.active.data
 for pl in o.data.polygons:
  mi=pl.material_index
  if old[mi] not in MATS:continue # inline emitters remain separate materials
  loops=list(pl.loop_indices);ps=np.array([o.data.vertices[o.data.loops[i].vertex_index].co[:] for i in loops]);tex=np.array([uv[i].uv[:] for i in loops])*size-.5
  lo=np.maximum(0,np.floor(tex.min(0)).astype(int));hi=np.minimum(size-1,np.ceil(tex.max(0)).astype(int))
  if np.any(hi<lo):continue
  yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1];v0=tex[1]-tex[0];v1=tex[2]-tex[0];den=v0[0]*v1[1]-v1[0]*v0[1]
  if abs(den)<1e-10:continue
  dx=xx-tex[0,0];dy=yy-tex[0,1];b=(dx*v1[1]-v1[0]*dy)/den;c=(v0[0]*dy-dx*v0[1])/den;a=1-b-c;ins=(a>=-.005)&(b>=-.005)&(c>=-.005);sl=(slice(lo[1],hi[1]+1),slice(lo[0],hi[0]+1));pos[sl][ins]=(a[...,None]*ps[0]+b[...,None]*ps[1]+c[...,None]*ps[2])[ins]
  area=np.linalg.norm(np.cross(ps[1]-ps[0],ps[2]-ps[0]))
  for k,bar in enumerate((a,b,c)):
   if not ef[pl.index][k]:continue
   length=np.linalg.norm(ps[(k+2)%3]-ps[(k+1)%3]);dist=np.maximum(bar,0)*area/max(length,1e-9);tgt=dcv if ef[pl.index][k]>0 else dcc;tgt[sl][ins]=np.minimum(tgt[sl][ins],dist[ins])
  identity[sl][ins]=hash2(comps[pl.index],0,17);typ[sl][ins]=MATS.index(old[mi]);mask[sl]|=ins
 x,y,z=pos.transpose(2,0,1);n0=noise(x+y*.43,z-y*.17,6,1);n1=noise(x-y*.21,z+y*.46,26,2);n2=noise(x+y*.31,z,100,3);n3=noise(x,z+y*.12,360,4)
 cavity=np.clip((1-ao)*1.7,0,1);crease=np.exp(-dcc/.024)
 # Readable corrosion fields, concentrated around recesses and broken creases.
 rust=np.clip((n0*.55+n1*.45-.43)*3.2,0,1)*np.clip(cavity*.9+crease*.65+.10,0,1)
 run=np.zeros_like(x)
 for i,(bx,by,bz) in enumerate(anchors):
  # downward runoff in authored section space; no UV-axis stripes.
  length=.10+(i%5)*.033;dz=bz-z;drift=.035*np.sin(dz*13+i);width=.008+.018*np.clip(dz/length,0,1)
  m=np.exp(-((x-bx-drift)/width)**2)*np.exp(-((y-by)/.13)**2)*np.clip(1-dz/length,0,1)*(dz>=-.008)
  run=np.maximum(run,m)
 # seam bleeding and drips extend away from sharp edges, not arbitrary color patches.
 runoff=np.exp(-dcv/.036)*np.clip(noise(x+y*.7,z*.15,39,9)-.35,0,1)*.8
 rust=np.clip(rust*.90+run*.88+runoff*.40,0,.94)
 grime=np.clip(cavity*.48+crease*.35+np.clip(.48-n1,0,1)*.34,0,.88)
 # Chipped edges with narrow bright metal exposed; multiscale breakup avoids stitched edges.
 wear=np.exp(-dcv/.0065)*np.clip((n1*.7+n2*.3-.28)*2.5,0,1)
 # Short directional scuffs; no regular dotted scratch array.
 streak=noise(x*1.8+y*.25,z*.18,110,7)
 scratch=np.clip((streak-.76)*11,0,1)*np.clip((n1-.46)*4,0,1)
 scratch*=.25+.75*np.exp(-dcv/.035)
 value=.066+identity*.067+n0*.019+n2*.009
 col=np.ones((size,size,4),np.float32);col[...,:3]=value[...,None]*np.array([1.04,1,.95])
 # Dark inserts and steel remain in the armor's value family.
 col[typ==1,:3]=np.stack([.115+n0*.055,.12+n0*.055,.12+n0*.055],-1)[typ==1]
 col[typ==2,:3]=np.stack([.012+n0*.012,.014+n0*.012,.015+n0*.012],-1)[typ==2]
 rust[typ==2]*=.38;wear[typ==2]*=.24;scratch[typ==2]*=.25
 col[...,:3]*=1-grime[...,None]*np.array([.66,.71,.75])
 rc=np.stack([.16+n1*.12,.047+n1*.045,.015+n1*.024],-1)
 col[...,:3]=col[...,:3]*(1-rust[...,None])+rc*rust[...,None]
 exposed=np.clip(wear*.76+scratch*.42,0,.9);scuff=np.stack([.32+n0*.12,.33+n0*.12,.325+n0*.12],-1)
 col[...,:3]=col[...,:3]*(1-exposed[...,None])+scuff*exposed[...,None]
 # sparse dark pitting at submillimeter scale. Normal map is micro-detail only.
 pits=np.clip((n3-.78)*6,0,1);height=-pits*.00015-scratch*.00003;gy,gx=np.gradient(height)
 safe=mask.copy()
 for sh,ax in [(1,0),(-1,0),(1,1),(-1,1)]:safe&=np.roll(mask,sh,axis=ax)
 nm=np.ones_like(col);ns=np.stack([-gx*size*.18,-gy*size*.18,np.ones_like(x)],-1);ns/=np.maximum(np.linalg.norm(ns,axis=-1,keepdims=True),1e-6);ns[~safe]=(0,0,1);nm[...,:3]=ns*.5+.5
 orm=np.ones_like(col);orm[...,0]=np.clip(ao,0,1);orm[...,1]=np.clip(.33+n0*.13+grime*.21+rust*.26-exposed*.15,.18,.92);orm[...,2]=np.clip(.52-rust*.50-grime*.16+exposed*.22,0,.8);orm[typ==2,1]=.7;orm[typ==2,2]=.20
 LOG.setdefault('weathering',{})[kind]={'ao_mean':float(ao[mask].mean()),'rust_coverage_gt_025':float((rust[mask]>.25).mean()),'grime_coverage_gt_04':float((grime[mask]>.4).mean()),'wear_coverage_gt_025':float((wear[mask]>.25).mean()),'runoff_sources':len(anchors),'basecolor_mean':float(col[...,:3][mask].mean())}
 for _ in range(9):
  grown=mask.copy()
  for sh,ax in [(1,0),(-1,0),(1,1),(-1,1)]:
   src=np.roll(mask,sh,axis=ax);fill=(~grown)&src
   for arr in (col,orm,nm):arr[fill]=np.roll(arr,sh,axis=ax)[fill]
   grown|=fill
  mask=grown
 (OUT/'textures').mkdir(exist_ok=True)
 def image(suffix,arr,linear=False):
  im=bpy.data.images.new('R2 '+kind+' '+suffix,size,size,alpha=False);im.colorspace_settings.name='Non-Color' if linear else 'sRGB';im.pixels.foreach_set(np.clip(arr,0,1).ravel());im.filepath_raw=str(OUT/'textures'/('r2-'+kind+'-'+suffix+'.png'));im.file_format='PNG';im.save();im.pack();return im
 ims=[image('albedo',col),image('normal',nm,True),image('ORM',orm,True)]
 m=bpy.data.materials.new('R2 baked '+kind);m.use_nodes=True;nt=m.node_tree;bs=nt.nodes['Principled BSDF'];nodes=[]
 for im in ims:t=nt.nodes.new('ShaderNodeTexImage');t.image=im;nodes.append(t)
 nt.links.new(nodes[0].outputs['Color'],bs.inputs['Base Color']);nn=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(nodes[1].outputs['Color'],nn.inputs['Color']);nt.links.new(nn.outputs[0],bs.inputs['Normal']);sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(nodes[2].outputs['Color'],sep.inputs[0]);nt.links.new(sep.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sep.outputs['Blue'],bs.inputs['Metallic']);group=nt.nodes.new('ShaderNodeGroup');group.node_tree=bpy.data.node_groups['glTF Material Output'];nt.links.new(sep.outputs['Red'],group.inputs['Occlusion'])
 for i,oldm in enumerate(old):
  if oldm in MATS:o.data.materials[i]=m
 print('WEATHER_READY',kind,LOG['weathering'][kind],flush=True)
