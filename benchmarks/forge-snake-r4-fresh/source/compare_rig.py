import json,struct,sys
from pathlib import Path
def load(p):
 data=Path(p).read_bytes();n=struct.unpack_from('<I',data,12)[0];g=json.loads(data[20:20+n]);parents={g['nodes'][c].get('name'):n.get('name') for n in g['nodes'] for c in n.get('children',[])}
 return {n.get('name'):{'parent':parents.get(n.get('name')),'translation':n.get('translation',[0,0,0]),'rotation':n.get('rotation',[0,0,0,1]),'scale':n.get('scale',[1,1,1]),'matrix':n.get('matrix')} for n in g['nodes']}
a,b=map(load,sys.argv[1:3]);diffs=[];mx=0
for name,aa in a.items():
 if name not in b:diffs.append([name,'missing']);continue
 bb=b[name]
 if aa['parent']!=bb['parent']:diffs.append([name,'parent',aa['parent'],bb['parent']])
 for k in ['translation','rotation','scale']:
  d=max(abs(x-y) for x,y in zip(aa[k],bb[k]));mx=max(mx,d)
  if d>1e-5:diffs.append([name,k,d])
 if aa['matrix']!=bb['matrix']:diffs.append([name,'matrix'])
report={'input_nodes':len(a),'output_nodes':len(b),'max_component_delta':mx,'differences_over_1e_5':diffs,'passed':not diffs}
print(json.dumps(report,indent=2));assert not diffs
