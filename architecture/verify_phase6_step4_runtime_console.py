#!/usr/bin/env python3
"""Strict Phase-6 Step-4 primary-runtime + two-page control-room evidence gate."""
from pathlib import Path
import json, re, unicodedata
ROOT=Path(__file__).resolve().parent.parent

def req(c,m):
    if not c: raise AssertionError(m)

def read(path): return Path(path).read_text(encoding='utf-8')
def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def concept_fold(value):
    normalized=unicodedata.normalize('NFKC',str(value or ''))
    visible=''.join(ch for ch in normalized if unicodedata.category(ch)!='Cf')
    compact=re.sub(r'\s+',' ',visible).strip()
    return re.sub(r'[.!?]+$','',compact).strip().casefold()

def main():
    manifest=load(ROOT/'architecture'/'phase6_step4_runtime_console_manifest.json')
    req(manifest.get('phase')==6 and manifest.get('step')==4,'wrong manifest')
    req(manifest.get('status') in {'IMPLEMENTATION_IN_PROGRESS','PASS'},'invalid status')
    req(manifest.get('engine_count')==44 and manifest.get('new_engine_count')==0,'engine #45 forbidden')
    req(manifest['hidden_control_room']['page_count']==2 and manifest['hidden_control_room']['pages']==['Current Status','Training Center'],'two-page contract changed')
    req(manifest['authentication']['salted_scrypt_verifier'] is True and manifest['authentication']['hard_coded_password'] is False,'auth contract weakened')
    core=read(ROOT/'⚡'/'⚡');preload=read(ROOT/'⚡'/'🔌');auth=read(ROOT/'⚡'/'🔐');admin=read(ROOT/'⚡'/'🛡️');ui=read(ROOT/'⚡'/'🎛️');css=read(ROOT/'⚡'/'🕶️');runtime=read(ROOT/'↔️'/'⚡')
    req("path.join(ROOT, '↔️', '⚡')" in core,'Electron does not route to Step-4 facade')
    req('ADMIN.install(win)' in core and 'ADMIN.recordTranslation' in core,'admin runtime not integrated')
    req("'🔐'" in preload and "'🤖:snapshot'" in preload,'admin preload bridge missing')
    req('scryptSync' in auth and 'timingSafeEqual' in auth and 'randomBytes(24)' in auth,'slow salted verifier missing')
    req('SESSION_TTL_MS' in auth and 'rate-limited' in auth and 'sessions.clear()' in auth,'session/rate/rotation controls missing')
    req('5' in ui and '3000' in ui and "📊 Current Status" in ui and "🏋️ Training Center" in ui,'hidden gesture/two pages missing')
    req("setAttribute('aria-hidden', 'true')" in ui and 'setAttribute(\'title\'' not in ui and 'tabindex' not in ui.lower(),'hidden entry clue introduced')
    req('cursor:inherit!important' in css and '#el-admin-entry:hover' in css,'zero-clue CSS missing')
    req('forgey_primary_released' in runtime and 'provider_calls": 0' in runtime and 'SelectedGeneration' in runtime,'Forgey-first evidence missing')
    req('deterministic-authority-conflict' in runtime and 'deterministic-roundtrip-failed' in runtime,'neural validation boundary missing')

    # Historical Step-4 boundary: a Step-5 publisher is forbidden unless a valid,
    # later Step-5 authority manifest is present. This keeps Step 4 strict while
    # allowing the explicitly authorized next phase to exist after Step 4 merged.
    step5_manifest_path=ROOT/'architecture'/'phase6_step5_release_manifest.json'
    publisher_path=ROOT/'scripts'/'publish-phase6-release.ps1'
    step5_state='ABSENT'
    if step5_manifest_path.exists():
        step5=load(step5_manifest_path)
        req(step5.get('phase')==6 and step5.get('step')==5,'invalid later Step5 manifest')
        req(step5.get('status') in {'IMPLEMENTATION_IN_PROGRESS','PASS'},'invalid later Step5 status')
        req(step5.get('base_main_sha')=='e0ed1b2ac91ae1f9a716abfc0e93904469b91422','Step5 does not descend from merged Step4')
        req(publisher_path.exists(),'authorized Step5 manifest exists without publisher')
        step5_state=str(step5.get('status'))
    else:
        req(not publisher_path.exists(),'Step5 publisher leaked into Step4 without Step5 authority')

    evidence_dir=ROOT/'data'/'phase6-step4'
    for name in ('primary-forward.json','primary-reverse.json','status.json','auth-proof.json','console-proof.json'):
        req((evidence_dir/name).is_file(),f'missing Step4 evidence {name}')
    f=load(evidence_dir/'primary-forward.json');r=load(evidence_dir/'primary-reverse.json');s=load(evidence_dir/'status.json');a=load(evidence_dir/'auth-proof.json');c=load(evidence_dir/'console-proof.json')
    req(f.get('winner')=='🚲' and f.get('metrics',{}).get('forgey_primary_released') is True and int(f.get('metrics',{}).get('provider_calls',-1))==0,'forward primary proof failed')
    req(concept_fold(r.get('winner',''))==concept_fold('bicycle') and float(r.get('metrics',{}).get('roundtrip',0) or 0)==1.0 and r.get('metrics',{}).get('forgey_primary_released') is True and int(r.get('metrics',{}).get('provider_calls',-1))==0,'reverse primary concept/round-trip proof failed')
    req(f['metrics'].get('forgey_generation')=='G2' and r['metrics'].get('forgey_generation')=='G2','selected G2 not used')
    req(s.get('registry',{}).get('hashes_verified') is True and s.get('registry',{}).get('selected_generation')=='G2','status registry proof failed')
    req(int(s.get('model',{}).get('trainable_parameters') or 0)==1788672,'runtime parameter count not derived')
    req(int(s.get('model',{}).get('model_file_bytes') or 0)>0 and int(s.get('model',{}).get('tokenizer_file_bytes') or 0)>0,'actual model/tokenizer sizes missing')
    req(a.get('scrypt') is True and a.get('plaintext_absent') is True and a.get('rate_limit') is True and a.get('rotation') is True,'auth proof failed')
    req(c.get('page_count')==2 and c.get('pages')==['📊 Current Status','🏋️ Training Center'] and c.get('hidden_entry_no_title') is True and c.get('hidden_entry_no_tabindex') is True,'console proof failed')
    print(f'PHASE6_STEP4_OK primary=G2 provider=0 reverse_concept=bicycle reverse_roundtrip=1 pages=2 auth=scrypt status=REAL params=1788672 step5={step5_state}')
if __name__=='__main__':main()
