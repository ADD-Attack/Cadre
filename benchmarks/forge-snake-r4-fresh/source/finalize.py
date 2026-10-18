"""Independent final evidence checks. Requires Pillow and NumPy, not Blender."""
import json,hashlib,struct,subprocess,sys
from pathlib import Path
from PIL import Image
import numpy as np
O=Path(__file__).resolve().parents[1];R=O.parents[1];B=R/'benchmarks/forge-snake-r3'
asset=O/'snake-sectional-r4-fresh.glb'
validation=json.loads(subprocess.check_output([sys.executable,str(O/'source/validate_glb.py'),str(asset)]))
rig=json.loads(subprocess.check_output([sys.executable,str(O/'source/compare_rig.py'),str(B/'snake-sectional-r3.glb'),str(asset)]))
(O/'glb-validation.json').write_text(json.dumps(validation,indent=2));(O/'rig-comparison.json').write_text(json.dumps(rig,indent=2))
a=json.loads((O/'captures/baseline-r3-render-settings.json').read_text());b=json.loads((O/'captures/r4-fresh-render-settings.json').read_text())
assert a==b,'Baseline/candidate staging mismatch'
assert a['engine']=='CYCLES' and a['device']=='CPU' and a['samples']==256 and a['adaptive'] and a['denoise'] and a['resolution']==[1920,1080]
assert a['frames']==json.loads((B/'captures/r3-render-settings.json').read_text())['frames']
assert a['glare']['type']=='FOG_GLOW'
for k,v in [('threshold',.4),('strength',.25),('size_normalized',.125)]:assert abs(a['glare'][k]-v)<1e-6
images=[]
for prefix in ['baseline-r3','r4-fresh']:
 for suffix in ['full-body','head-closeup']:
  p=O/'captures'/(prefix+'-'+suffix+'.png');im=Image.open(p);assert im.size==(1920,1080);arr=np.asarray(im.convert('RGB'));corner=np.median(arr[:32,-32:].reshape(-1,3),axis=0).tolist()
  assert max(abs(x-y) for x,y in zip(corner,[196,196,195]))<=4,corner
  images.append({'file':str(p.relative_to(O)),'dimensions':list(im.size),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'clear_top_right_rgb_median':corner})
assert images[0]['sha256']!=images[2]['sha256'] and images[1]['sha256']!=images[3]['sha256']
check=(O/'godot/check.log').read_text();capture=(O/'godot/capture.log').read_text();imp=(O/'godot/import.log').read_text()
assert hashlib.sha256((O/'godot/snake-sectional-r4-fresh.glb').read_bytes()).hexdigest()==validation['sha256'],'Godot imported a different GLB'
assert 'Godot Engine v4.7.2' in check
assert not any('ERROR:' in s for s in [check,capture,imp]),'Godot error in final logs'
godot=json.loads(next(line.split('R4_GODOT ',1)[1] for line in check.splitlines() if 'R4_GODOT ' in line))
assert godot['loaded'] and godot['mesh_instances']==90 and godot['triangles']==validation['assembly_triangles'] and godot['segment_nodes']==28 and godot['segment_distinct_meshes']==1 and godot['housing_nodes']==29 and godot['glow_nodes']==29 and godot['surfaces_without_tangents']==0 and godot['segments_posable']==28
assert len(godot['textured_materials'])==3
for fields in godot['textured_materials'].values():assert all(fields.values())
native=json.loads(next(line.split('R4_NATIVE_CAPTURE ',1)[1] for line in capture.splitlines() if 'R4_NATIVE_CAPTURE ' in line));assert native['save_error']==0
im=Image.open(O/'godot/godot-import-pose.png');assert im.size==(1280,720)
report={'paired_staging_equal':True,'camera_frames_identical_to_published_R3':True,'production_settings_verified':True,'active_glare_inputs_verified':True,'reference_background_sample':json.loads((O/'reference-background-sample.json').read_text()),'images':images,'Godot_4_7_2':{'passed':True,'check':godot,'native_capture':native}}
(O/'captures/capture-verification.json').write_text(json.dumps(report,indent=2))
log=json.loads((O/'counts-and-log.json').read_text());log['base_glb_sha256']=hashlib.sha256((B/'snake-sectional-r3.glb').read_bytes()).hexdigest();log['delivered_build']='g';log['binary_validation']=validation;log['hierarchy_validation']=rig;log['judged_render']=a;log['capture_verification']=report
log['self_checks']={'actual_reference_viewed_in_session':True,'R3_full_and_head_viewed_before_build':True,'own_checkpoint_full_and_head_viewed_during_build':True,'production_full_and_head_viewed_in_session':True,'Godot_native_capture_viewed_in_session':True,'module_and_tail_detail_previews_viewed_in_session':True,'no_other_entrant_used':True,'iteration_corrections':['a budget gate rejected overrun before export','b coarse superseded struts reclaimed','c stronger panel tones, green optical face, larger core and reduced normal strength','d checkpoint caught floating crest bolts; raycast seating replaces guessed placement; added sparse etched scratches','g module detail exposed armor/cassette overlap; lifted complete cassette assemblies and added recessed dark backings; repeated capture and import checks','Godot evidence filename substitution fixed; fresh pipeline rerun']}
(O/'counts-and-log.json').write_text(json.dumps(log,indent=2))
# Windows applications write CRLF logs/JSON. Normalize text evidence for clean repo diffs.
for p in O.rglob('*'):
 if '.godot' in p.parts or not p.is_file():continue
 if p.suffix in ['.json','.log','.md','.py','.sh','.gd','.uid','.godot']:
  p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
print(json.dumps({'passed':True,'sha256':validation['sha256'],'counts':validation,'staging_equal':True,'godot':True},indent=2))
