"""Validate delivered binary glTF, independently of Blender's mesh counts."""
import json,struct,hashlib,sys
from pathlib import Path
p=Path(sys.argv[1]);data=p.read_bytes();magic,version,length=struct.unpack_from('<4sII',data);assert (magic,version,length)==(b'glTF',2,len(data));n,kind=struct.unpack_from('<II',data,12);g=json.loads(data[20:20+n]);acc=g['accessors'];meshes=g['meshes'];nodes=g['nodes']
def tris(mi):return sum(acc[q['indices']]['count']//3 for q in meshes[mi]['primitives'])
mesh_nodes=[n for n in nodes if 'mesh'in n];seg=[n for n in mesh_nodes if n.get('name','').startswith('Segment_')];hous=[n for n in mesh_nodes if 'Housing'in n.get('name','')];glow=[n for n in mesh_nodes if 'GlowBars'in n.get('name','')]
missing=[]
for i,m in enumerate(meshes):
 for j,q in enumerate(m['primitives']):
  for a in ['POSITION','NORMAL','TANGENT','TEXCOORD_0']:
   if a not in q['attributes']:missing.append([i,j,a])
orm=[]
for m in g.get('materials',[]):
 if 'occlusionTexture'in m:
  ao=m['occlusionTexture']['index'];mr=m['pbrMetallicRoughness']['metallicRoughnessTexture']['index'];assert g['textures'][ao]['source']==g['textures'][mr]['source'];orm.append(m['name'])
byname={n.get('name',''):tris(n['mesh']) for n in mesh_nodes};joint=byname['Joint_00_Housing']+byname['Joint_00_GlowBars'];head=sum(t for n,t in byname.items() if n=='Head' or n.startswith('R2 socket lens'))
rep={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'head':head,'segment':byname['Segment_00'],'joint':joint,'segment_plus_joint':byname['Segment_00']+joint,'tail_plus_joint':byname['Tail']+joint,'assembly_triangles':sum(tris(n['mesh']) for n in mesh_nodes),'segment_nodes':len(seg),'segment_distinct_mesh_indices':sorted(set(n['mesh'] for n in seg)),'housing_nodes':len(hous),'glow_nodes':len(glow),'mesh_nodes':len(mesh_nodes),'missing_attributes':missing,'packed_orm_materials':orm,'skins':len(g.get('skins',[])),'extensions':g.get('extensionsUsed',[])}
assert not missing and len(seg)==28 and len(set(n['mesh'] for n in seg))==1 and len(hous)==29 and len(glow)==29 and not g.get('skins')
assert 10000<=head<=18000 and rep['segment_plus_joint']<=1600 and rep['tail_plus_joint']<=3000 and 30000<=rep['assembly_triangles']<=60000,rep
assert len(orm)==len(g.get('materials',[])),orm
assert len(mesh_nodes)==90
assert {n['name'].rsplit('_',1)[0] for n in hous}=={n['name'].rsplit('_',1)[0] for n in glow}
assert all(m.get('alphaMode','OPAQUE')=='OPAQUE' for m in g['materials'])
assert 'KHR_draco_mesh_compression' not in rep['extensions']
print(json.dumps(rep,indent=2))
