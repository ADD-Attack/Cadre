"""Independent delivery checks; fail closed on budgets, engine evidence, or staging mismatch."""
from pathlib import Path
import json,struct,hashlib,re,subprocess,sys
O=Path(__file__).resolve().parents[1];R=O.parents[1];B=R/'benchmarks/forge-snake-r3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(script,*args):
 r=subprocess.run([sys.executable,str(O/'source'/script),*map(str,args)],capture_output=True,text=True);assert r.returncode==0,r.stderr+r.stdout;return json.loads(r.stdout)
assert sha(B/'snake-sectional-r3.glb')=='c34f3b69ecc48278263e7ea691b5011c65bb07837b7721fc29f39248a5ded34a'
v=run('validate_glb.py',O/'snake-sectional-r4.glb');rig=run('compare_rig.py',B/'snake-sectional-r3.glb',O/'snake-sectional-r4.glb')
(O/'binary-validation.json').write_text(json.dumps(v,indent=2));(O/'rig-comparison.json').write_text(json.dumps(rig,indent=2))
a=json.loads((O/'captures/r4-render-settings.json').read_text());b=json.loads((O/'captures/baseline-r3-render-settings.json').read_text());assert a==b,'paired active staging differs'
assert a['samples']==256 and a['adaptive'] and abs(a['adaptive_threshold']-.01)<1e-6 and a['denoise'] and a['resolution']==[1920,1080] and a['engine']=='CYCLES'
assert a['glare']=={'type':'FOG_GLOW','threshold':a['glare']['threshold'],'strength':.25,'size_normalized':.125}
assert abs(a['glare']['threshold']-.4)<1e-6
assert a['frames']==json.loads((B/'counts-and-log.json').read_text())['judged_render']['camera_frames']
for name in ['render-r4.log','render-baseline-r3.log']:
 t=(O/'logs'/name).read_text();assert 'R4_RENDER_COMPLETE' in t and 'Traceback' not in t,name
assert 'R4_BUILD_COMPLETE' in (O/'logs/build-final.log').read_text()
manifest=[]
for p in sorted(O.rglob('*.png')):
 if '.godot' in p.parts or p.name.startswith('snake-sectional-r4_'):continue
 data=p.read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n' and len(data)>1000,p
 w,h=struct.unpack_from('>II',data,16)
 if p.parent.name=='captures':assert (w,h)==(1920,1080),(p,w,h)
 manifest.append({'path':p.relative_to(O).as_posix(),'bytes':len(data),'sha256':sha(p),'resolution':[w,h]})
for name in ['r4-full-body.png','r4-head-closeup.png','baseline-r3-full-body.png','baseline-r3-head-closeup.png']:assert (O/'captures'/name).exists()
assert (O/'previews/PREVIEW-g-full-body.png').exists() and (O/'previews/PREVIEW-g-head-closeup.png').exists()
assert (O/'previews/PREVIEW-detail-terminal.png').exists()
assert (O/'previews/PREVIEW-detail-module.png').exists() and (O/'previews/PREVIEW-detail-tail.png').exists()
logs={k:(O/'godot'/(k+'.log')).read_text() for k in ['import','check','capture']}
for k,t in logs.items():assert not re.search(r'ERROR:|SCRIPT ERROR|Parse Error|Failed to',t,re.I),(k,t)
assert 'v4.7.2.stable' in logs['import']
result=json.loads(re.search(r'R4_GODOT (\{.*\})',logs['check']).group(1));cap=json.loads(re.search(r'R4_NATIVE_CAPTURE (\{.*\})',logs['capture']).group(1))
assert result['loaded'] and result['mesh_instances']==90 and result['segment_nodes']==28 and result['segment_distinct_meshes']==1 and result['segments_posable']==28 and result['surfaces_without_tangents']==0 and result['triangles']==v['assembly_triangles']
assert result['housing_nodes']==29 and result['glow_nodes']==29 and not result.get('skeleton',False)
assert len(result['textured_materials'])==3 and all(all(d.values()) for d in result['textured_materials'].values())
assert cap['save_error']==0 and cap['viewport']==[1280,720]
assert sha(O/'godot/snake-sectional-r4.glb')==v['sha256']
assert (O/'godot/exit-codes.json').exists();exits=json.loads((O/'godot/exit-codes.json').read_text());assert all(x==0 for x in exits.values()),exits
bg=json.loads((O/'background-validation.json').read_text());assert bg['paired_max_channel_difference']<=2
log=json.loads((O/'counts-and-log.json').read_text());log.update({'base_glb_sha256':sha(B/'snake-sectional-r3.glb'),'binary_validation':v,'rig_comparison':rig,'staging_identical_to_baseline':True,'active_render_settings':a,'godot':{'version':'4.7.2.stable.official.ed1daf0bf','fresh_import':True,'exit_codes':exits,'result':result,'native_capture':cap,'imported_glb_sha256':v['sha256'],'outcome':'PASS'},'image_manifest':manifest,'visual_self_check':{'reference_and_R3_viewed_before_build':True,'checkpoints_viewed':['A full/head','B full/head','C full/head','D full/head','E full/head','F full/head','G full/head','final module, tail and terminal detail','final production full/head and paired R3 baseline'],'self_check_changes':'See NOTE.md: budget reclamation, directional silver contrast, structured eye, bezel seating, complete cassette lift, exposed pistons, plated/riveted fins, terminal mechanics, reduced micro-normal strength'},'final_build_log':'logs/build-final.log','final_checkpoint':'G: original internal segment tube restored; 36-sided continuous bands; clean rods and seated terminal hardware','final_glb_sha256':v['sha256'],'background_validation':bg,'principled_material_audit':json.loads((O/'material-audit.json').read_text())})
(O/'counts-and-log.json').write_text(json.dumps(log,indent=2))
print(json.dumps({'outcome':'PASS','counts':v,'rig_preserved':rig['passed'],'paired_staging_equal':a==b,'godot_pass':True,'image_files':len(manifest)},indent=2))
