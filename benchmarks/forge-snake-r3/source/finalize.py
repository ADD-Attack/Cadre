"""Assemble the delivered evidence manifest; fail on missing final artifacts."""
import json,re,struct,hashlib
from pathlib import Path
O=Path(__file__).resolve().parents[1]
log=json.loads((O/'counts-and-log.json').read_text())
validation=json.loads((O/'glb-validation.json').read_text());rig=json.loads((O/'rig-comparison.json').read_text())
def event(file,prefix):
 s=(O/file).read_text();lines=[line.split(prefix,1)[1] for line in s.splitlines() if prefix in line];assert lines,(file,prefix);return json.loads(lines[-1])
godot=event('godot/check.log','R3_GODOT ');capture=event('godot/capture.log','R3_NATIVE_CAPTURE ')
assert godot['triangles']==validation['assembly_triangles']==59509
assert godot['segment_nodes']==godot['segments_posable']==28 and godot['segment_distinct_meshes']==1
assert godot['housing_nodes']==godot['glow_nodes']==29 and godot['surfaces_without_tangents']==0
assert capture['save_error']==0 and capture['viewport']==[1280,720]
for n in ['import','check','capture']:
 s=(O/'godot'/f'{n}.log').read_text();assert 'ERROR:' not in s and 'SCRIPT ERROR:' not in s,(n,s)
 assert 'v4.7.2.stable' in s
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(O/'snake-sectional-r3.glb')==validation['sha256']==sha(O/'godot/snake-sectional-r3.glb')
artifacts={}
for name in ['captures/r3-full-body.png','captures/r3-head-closeup.png','captures/baseline-r2-full-body.png','captures/baseline-r2-head-closeup.png','godot/godot-import-pose.png','previews/PREVIEW-h-full-body.png','previews/PREVIEW-h-head-closeup.png','previews/PREVIEW-detail-module.png','previews/PREVIEW-detail-tail.png']:
 p=O/name;d=p.read_bytes();assert d[:8]==b'\x89PNG\r\n\x1a\n';w,h=struct.unpack('>II',d[16:24]);expected=(1920,1080) if name.startswith('captures/') else ((1152,648) if 'PREVIEW-h-' in name else (1280,720));assert (w,h)==expected,(name,w,h)
 artifacts[name]={'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest(),'width':w,'height':h}
settings=json.loads((O/'captures/r3-render-settings.json').read_text());baseline_settings=json.loads((O/'captures/baseline-r2-render-settings.json').read_text());assert settings==baseline_settings,'Baseline/after staging mismatch'
render=log['judged_render'];assert render['engine']=='CYCLES' and render['max_samples']==256 and render['adaptive'] and render['denoise'] and render['resolution']==[1920,1080]
log.update({'resolved_R2_panel_medians':{'MATCH':5.0,'QUALITY':4.5},'binary_glb_validation':validation,'rig_comparison':rig,'godot':{'version':'4.7.2.stable.official.ed1daf0bf','required_executable':r'C:\Users\Moore\Godot\Godot_v4.7.2-stable_win64_console.exe','import_exit_code':0,'check_exit_code':0,'capture_exit_code':0,'result':godot,'native_capture':capture,'final_logs_without_errors':True},'export':{'format':'GLB','gltf_yup':True,'tangents':True,'packed_ORM':True,'materials':'Principled-only metal/roughness','Draco':False,'skins':False},'self_checks':[{'checkpoint':'a','caught':'too-clean finish, insufficient layering','changed':'finite scratches, edge abrasion, physical notched crown and crosswires'},{'checkpoint':'d','caught':'faceted optical socket after decimation','changed':'restored original optical tessellation; reclaimed 1000 concealed liner tris'},{'checkpoint':'f','caught':'regular comb-like abrasion bands','changed':'lower-frequency sparse broken edge scuffs; finite scratches retained'},{'checkpoint':'h','caught':'bright slab-like crown additions','changed':'darkened gunmetal faces and modeled bevel; traded two optional screws'}],'artifacts':artifacts,'delivery_folder':'benchmarks/forge-snake-r3/','branch':'forge-snake-r3-20261018'})
(O/'counts-and-log.json').write_text(json.dumps(log,indent=2)+'\n')
print(json.dumps({'status':'ALL_ARTIFACT_CHECKS_PASS','counts':log['counts'],'GLB_SHA256':validation['sha256'],'production_images':4,'Godot':'4.7.2 PASS'},indent=2))
