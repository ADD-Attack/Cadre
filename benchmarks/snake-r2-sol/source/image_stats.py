"""R1-compatible image statistics; backdrop-difference mask, includes silhouette shadow.
Not a perfect semantic asset mask. Report definition rather than imply strict segmentation.
"""
from PIL import Image
import numpy as np,json,sys
rows=[]
for p in sys.argv[1:]:
 a=np.asarray(Image.open(p).convert('RGB'),dtype=float);bg=a[5:40,5:40].reshape(-1,3).mean(0);mask=np.abs(a-bg).sum(-1)>40;rgb=a[mask];v=rgb.mean(-1)
 rows.append({'path':p,'background_rgb':bg.tolist(),'foreground_percent':float(mask.mean()*100),'luminance_mean_rgb_p10_p25_p50_p75_p90':np.percentile(v,[10,25,50,75,90]).tolist(),'teal_percent':float(((rgb[:,1]-rgb[:,0])>60).mean()*100),'mask':'sum(abs(pixel-bg)) > 40; same family as R1 stats, includes contact shadow'})
print(json.dumps(rows,indent=2))
