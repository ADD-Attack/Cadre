import bpy, numpy as np, sys
for p in sys.argv[sys.argv.index('--')+1:]:
    im=bpy.data.images.load(p); w,h=im.size; a=np.array(im.pixels[:]).reshape(h,w,4)[...,:3]
    if im.colorspace_settings.name!='sRGB': pass
    a=a*255; bg=a[-40:-5,5:40].reshape(-1,3).mean(0)
    d=np.abs(a-bg).sum(-1); m=d>40; L=a.mean(-1)[m]; R,G,B=[a[...,i][m] for i in range(3)]
    print('STAT',p.split('\\')[-1],'bg',bg.round(1),'asset%',round(m.mean()*100,1),'L p10/25/50/75/90',np.percentile(L,[10,25,50,75,90]).round(0),'teal%',round(((G-R)>60).mean()*100,2), 'warm(R-B)',round(float((R-B).mean()),1))
