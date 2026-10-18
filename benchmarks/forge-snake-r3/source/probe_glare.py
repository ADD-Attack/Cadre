import bpy
from pathlib import Path
r=Path(r'\\wsl.localhost\OpenClawGateway\home\openclaw\.openclaw\workspace-studio-3d\tickets\forge-r3')
bpy.ops.wm.open_mainfile(filepath=str(r/'benchmarks/forge-snake-r3/snake-sectional-r3.blend'));g=next(n for n in bpy.context.scene.node_tree.nodes if n.type=='GLARE')
print('GLARE_INITIAL',g.glare_type,g.threshold,g.mix,g.size,[(x.name,str(x.default_value) if hasattr(x,'default_value') else '') for x in g.inputs],flush=True)
g.threshold=.65;g.mix=-.75;g.size=6
print('GLARE_LEGACY_SET',g.threshold,g.mix,g.size,[(x.name,str(x.default_value) if hasattr(x,'default_value') else '') for x in g.inputs],flush=True)

print('GLARE_OUTPUTS',[(x.name,x.identifier) for x in g.outputs],flush=True)
bpy.context.scene.view_layers[0].use_pass_emit=True
print('RENDER_OUTPUTS',[(x.name,x.enabled) for n in bpy.context.scene.node_tree.nodes if n.type=='R_LAYERS' for x in n.outputs],flush=True)
im=bpy.data.images.load(str(r/'benchmarks/forge-snake-r3/captures/r3-full-body.png'));im.colorspace_settings.name='Non-Color';w,h=im.size
print('RENDER_BACKGROUND_RGB',[round(im.pixels[((h-20)*w+(w-20))*4+k]*255,2) for k in range(3)],flush=True)
