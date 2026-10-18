"""Compare preserved rigid placement values with the shipped R1 glTF."""
import json,struct,sys
from pathlib import Path
def load(p):
 b=Path(p).read_bytes();n=struct.unpack_from('<I',b,12)[0];return json.loads(b[20:20+n])
a,b=map(load,sys.argv[1:3]);da={n.get('name'):n for n in a['nodes']};db={n.get('name'):n for n in b['nodes']};tested=[];err=[]
for name,old in da.items():
 if not(name.startswith('Segment_') or 'Housing' in name or 'GlowBars' in name or name=='Tail' or name=='Head'):continue
 new=db.get(name);assert new,name
 for key in ('matrix','translation','rotation','scale'):
  if old.get(key)!=new.get(key):err.append({'node':name,'field':key,'r1':old.get(key),'r2':new.get(key)})
 tested.append(name)
assert not err,err
print(json.dumps({'preserved_rigid_node_transforms':len(tested),'comparison':'exact JSON TRS/matrix equality against shipped R1','changed':err},indent=2))
