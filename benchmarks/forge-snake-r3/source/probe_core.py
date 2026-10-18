import bpy,numpy as np
from pathlib import Path
R=Path(r'\\wsl.localhost\OpenClawGateway\home\openclaw\.openclaw\workspace-studio-3d\tickets\forge-r3')
bpy.ops.wm.open_mainfile(filepath=str(R/'benchmarks/forge-snake-r3/snake-sectional-r3.blend'))
h=bpy.data.objects['Head'];xs=np.array([-2.03,-1.94,-1.70,-1.38,-1.03,-.65,-.30,.04]);ys=np.array([.12,.27,.36,.45,.54,.585,.56,.46]);zt=np.array([-.16,.015,.14,.285,.42,.47,.455,.36]);zb=np.array([-.29,-.40,-.455,-.47,-.465,-.445,-.415,-.36])
def radial(v):
 x,y,z=v.co;x/=1.13;y/=.94;z/=.82;w=np.interp(x,xs,ys);top=np.interp(x,xs,zt);bot=np.interp(x,xs,zb);zc=(top+bot)/2;rz=(top-bot)/2
 return (abs(y)/w)**(2/.78)+(abs(z-zc)/rz)**(2/.78)
r=[radial(v) for v in h.data.vertices]
for threshold in [.70,.75,.80,.84,.88,.90]:print('CORE_FACES',threshold,sum(all(r[i]<threshold for i in p.vertices) for p in h.data.polygons),flush=True)
