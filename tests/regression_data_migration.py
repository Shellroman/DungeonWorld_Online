import json, os, pathlib, re, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
TMP=ROOT/'tests'/'regression_data_migration_data'; TMP.mkdir(parents=True,exist_ok=True)
DB=TMP/'test.db'; DB.unlink(missing_ok=True)
os.environ['DW_DB']=str(DB); os.environ['DW_PORT']='8199'
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
import app

checks=[]
def ok(name,cond,detail=''):
    checks.append((name,bool(cond),detail))
    if not cond: print('FAIL',name,detail)

js=(ROOT/'static/app.js').read_text(encoding='utf-8')
launcher=(ROOT/'launcher/main.go').read_text(encoding='utf-8')
py=(ROOT/'app.py').read_text(encoding='utf-8')
ui=json.loads((ROOT/'static/i18n_ui_en.json').read_text(encoding='utf-8'))
content=json.loads((ROOT/'static/i18n_content_en.json').read_text(encoding='utf-8'))
all_release_text='\n'.join(p.read_text(encoding='utf-8',errors='ignore') for p in [ROOT/'app.py',ROOT/'static/app.js',ROOT/'static/index.html',ROOT/'static/styles.css',ROOT/'launcher/main.go'])

ok('version_300', app.VERSION=='1.0.0' and (ROOT/'VERSION').read_text().strip()=='1.0.0')
ok('schema20', app.SCHEMA_VERSION==20)
video_needles=['you'+'tube','youtu'+'.be']; ok('named_video_service_removed', not any(x in all_release_text.lower() for x in video_needles))
ok('english_content_complete', not content.get('unmapped') and len(content.get('map',{}))>=1179, str((len(content.get('map',{})),len(content.get('unmapped',[])))))
exact=ui.get('exact',{})
for ko,en in {
    '파일 추가':'Add File',
    '조건':'Requirement',
    '전용 종족 설명':'Race Feature',
    '예: 폐허의 문을 열고 2층으로 진입':'Example: Opened the ruined gate and reached the second floor',
    '탄약':'Ammo',
    '행동 효과':'Move Effects',
    '효과 종류':'Effect Type',
}.items():
    ok('ui_'+ko, exact.get(ko)==en, repr(exact.get(ko)))
ok('memo_placeholder_translated', '예: 폐허의 문을 열고 2층으로 진입' in exact)
ok('race_label_dynamic_translation', "translateUiText('전용 종족 설명')" in js)
ok('multiclass_enable_dynamic_translation', "Enable ${translateUiText(multiclassLabel)}" in js)
ok('move_effect_editor_present', all(x in js for x in ['MOVE_EFFECT_KINDS','moveEffectEditor(','collectMoveEffects(','data-add-move-effect','선택 필요']))
ok('move_effect_server_kinds', all(x in py for x in ['spell_grant','spell_level_reduce','spell_zero','move_grant','class_access','opposite_race_feature']))
ok('inventory_ammo_type', '"탄약"' in py and "ammoItem=type==='탄약'" in js)
ok('new_inventory_blank', "name:''" in js and "name:'새 물건'" not in js)
ok('launcher_offline_resume_disabled', '[data-resume]:not(:disabled)' in launcher and '캠페인이 열려 있을 때만 재접속할 수 있습니다.' in launcher)
resume=launcher[launcher.find('func apiClientResume'):launcher.find('func apiClientResume')+5000]
ok('launcher_probe_before_ticket', resume.find('probeCampaign')!=-1 and resume.find('issueSessionURL')!=-1 and resume.find('probeCampaign') < resume.find('issueSessionURL'))
ref_readme=(ROOT/'dwpack/reference/README_KO.md').read_text(encoding='utf-8')
ref_schema=json.loads((ROOT/'dwpack/reference/schema/classes.schema.json').read_text(encoding='utf-8'))
ref_kinds=set(ref_schema['$defs']['moveEffect']['properties']['kind']['enum'])
ok('reference_move_effects_documented','직업 행동 효과 (`move_effects`)' in ref_readme)
ok('reference_move_effects_schema',ref_kinds=={'spell_grant','spell_level_reduce','spell_zero','move_grant','class_access','opposite_race_feature'},str(ref_kinds))

with TestClient(app.app,client=('127.0.0.1',50401)) as c:
    r1=c.post('/api/rooms',json={'gm_name':'GM1','campaign_name':'One','password':''}).json(); room1=r1['room_code']; gh1={'Authorization':'Bearer '+r1['gm_token']}
    j1=c.post(f'/api/rooms/{room1}/join',json={'display_name':'P1','password':''}); ok('join_active_campaign',j1.status_code==200,j1.text)
    p1=j1.json(); ph1={'Authorization':'Bearer '+p1['player_token']}
    r2=c.post('/api/rooms',json={'gm_name':'GM2','campaign_name':'Two','password':''}).json(); room2=r2['room_code']
    off=c.get(f'/api/rooms/{room1}/join-info'); ok('inactive_join_info_blocked',off.status_code==409,off.text)
    offj=c.post(f'/api/rooms/{room1}/join',json={'display_name':'Nope','password':''}); ok('inactive_new_join_blocked',offj.status_code==409,offj.text)
    state=c.get(f'/api/rooms/{room1}/state',headers=ph1); ok('inactive_existing_player_blocked',state.status_code==409,state.text)
    on=c.get(f'/api/rooms/{room2}/join-info'); ok('active_second_campaign_allowed',on.status_code==200,on.text)

# Schema 18 -> 19 must detach legacy weapon ammo into a dedicated Ammo item without losing its resource value.
with app.db() as con:
    room=con.execute('SELECT id FROM rooms ORDER BY id LIMIT 1').fetchone()
    char=con.execute('SELECT id,state_json FROM characters WHERE room_id=? ORDER BY id LIMIT 1',(room['id'],)).fetchone()
    st=json.loads(char['state_json'])
    st['inventory']=[{'name':'사냥활','item_type':'무기','quantity':1,'weight':1,'tags':'중거리, 장거리','ammo_current':2,'ammo_max':3}]
    con.execute('UPDATE characters SET state_json=? WHERE id=?',(app.jdump(st),char['id']))
    app._set_schema_version(con,18)
app.init_db()
with app.db() as con:
    ok('migration_schema20',app._schema_version(con)==20)
    char=con.execute('SELECT state_json FROM characters ORDER BY id LIMIT 1').fetchone(); st=json.loads(char['state_json']); inv=st.get('inventory',[])
    weapon=next((x for x in inv if x.get('item_type')=='무기'),{})
    ammo=next((x for x in inv if x.get('item_type')=='탄약'),{})
    ok('weapon_ammo_detached',weapon.get('ammo_current')==0 and weapon.get('ammo_max')==0,str(inv))
    ok('ammo_resource_preserved',ammo.get('ammo_current')==2 and ammo.get('ammo_max')==3,str(inv))

print('\nSUMMARY')
for n,p,d in checks: print(('PASS' if p else 'FAIL'),n,d if not p else '')
print('passed',sum(p for _,p,_ in checks),'/',len(checks))
DB.unlink(missing_ok=True)
if not all(p for _,p,_ in checks): raise SystemExit(1)
