import os, sys, json, tempfile, pathlib, re
root=pathlib.Path(__file__).resolve().parents[1]
tmp=root/'tests'/'smoke_data'; tmp.mkdir(parents=True,exist_ok=True)
db=tmp/'test.db'
if db.exists(): db.unlink()
os.environ['DW_DB']=str(db)
os.environ['DW_PORT']='8127'
sys.path.insert(0,str(root))
from fastapi.testclient import TestClient
import app
results=[]
def ok(name, cond, detail=''):
    results.append((name,bool(cond),detail))
    if not cond: print('FAIL',name,detail)

with TestClient(app.app, client=("127.0.0.1", 50000)) as c:
    r=c.get('/api/ping'); ok('ping',r.status_code==200 and r.json().get('version')=='1.0.0',r.text)
    r=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'테스트','password':'1234'}); ok('create_room',r.status_code==200,r.text); room=r.json()['room_code']; gm=r.json()['gm_token']
    hdr={'Authorization':'Bearer '+gm}
    r=c.get(f'/api/rooms/{room}/join-info'); j=r.json(); ok('join_info',r.status_code==200 and any(x['name']=='마법사' for x in j['classes']),r.text[:300])
    wizard=next(x for x in j['classes'] if x['name']=='마법사'); race=wizard['races'][0]
    r=c.post(f'/api/rooms/{room}/join',json={'display_name':'P1','password':'1234'}); ok('join_player',r.status_code==200,r.text); p=r.json(); ph={'Authorization':'Bearer '+p['player_token']}; cid=p['character_id']
    pending=c.get(f'/api/rooms/{room}/state',headers=ph).json(); ok('join_starts_unassigned',pending['character']['state']['onboarding_complete'] is False and pending['party'][0]['class_name']=='무직' and pending['party'][0]['race_name']=='없음',json.dumps(pending['party'][0],ensure_ascii=False))
    r=c.post(f'/api/rooms/{room}/characters/{cid}/onboarding',headers=ph,json={'class_name':'마법사','race_name':race}); ok('finish_onboarding',r.status_code==200,r.text)
    r=c.get(f'/api/rooms/{room}/state',headers=hdr); sj=r.json(); ok('gm_state_monsters_154',len(sj.get('monsters',[]))==154,str(len(sj.get('monsters',[]))))
    human=sj.get('races',{}).get('인간',{}); human_access=next((x for x in human.get('spell_effects',{}).get('마법사',[]) if x.get('kind')=='cross_class_access'),{}); ok('human_spell_effect',human_access.get('source_class')=='사제' and 'spell_access' not in human,json.dumps(human,ensure_ascii=False)[:300])
    # initial stats must obey campaign bounds after assignment as well.
    patch={'stats':{'str':16,'dex':15,'con':13,'int':12,'wis':9,'cha':8}}
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':patch}); ok('initial_stats',r.status_code==200,r.text)
    r=c.get(f'/api/rooms/{room}/state',headers=ph); st=r.json()['character']['state']; hp0=st['hp_current']; con0=st['stats']['con']
    stats=dict(st['stats']); stats['con']=25
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'stats':stats}}); ok('stat_bounds_after_init',r.status_code==400,r.text)
    # GM can edit within the same authoritative range; CON still adjusts current/max HP consistently.
    stats=dict(st['stats']); stats['con']=14
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=hdr,json={'patch':{'stats':stats}}); ok('gm_stat_edit_in_bounds',r.status_code==200,r.text)
    r=c.get(f'/api/rooms/{room}/state',headers=ph); st2=r.json()['character']['state']; ok('con_hp_delta',st2['hp_current']==min(r.json()['party'][0]['hp_max'],hp0+(14-con0)),f"{hp0}->{st2['hp_current']} con {con0}->14 max {r.json()['party'][0]['hp_max']}")
    # XP server value
    ok('xp_required_server',r.json()['party'][0]['xp_required']==8,str(r.json()['party'][0]['xp_required']))
    # session ticket one-time
    r=c.post(f'/api/rooms/{room}/session-ticket',headers=ph); ok('session_ticket_create',r.status_code==200,r.text); t=r.json()['ticket']
    a=c.get('/session/'+t,follow_redirects=False); b=c.get('/session/'+t,follow_redirects=False); ok('session_ticket_one_time',a.status_code==200 and b.status_code==410,f'{a.status_code},{b.status_code}')
    # race rename updates character if GM first changes player race to target human
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=hdr,json={'patch':{'race_name':'인간'}}); ok('gm_change_race',r.status_code==200,r.text)
    human=sj['races']['인간']
    r=c.put(f'/api/rooms/{room}/races',headers=hdr,json={'name':'사람','old_name':'인간','data':human}); ok('race_rename',r.status_code==200,r.text)
    r=c.get(f'/api/rooms/{room}/state',headers=ph); ok('race_rename_char_ref',r.json()['character']['state']['race_name']=='사람',r.json()['character']['state']['race_name'])
    r=c.delete(f'/api/rooms/{room}/races/사람',headers=hdr); ok('race_delete_in_use_blocked',r.status_code==400,str(r.status_code)+r.text)
    # catalog security: appear first monster no reveal, player response should not include hidden source data
    gmstate=c.get(f'/api/rooms/{room}/state',headers=hdr).json(); mid=gmstate['monsters'][0]['id']; original=gmstate['monsters'][0]
    r=c.post(f'/api/rooms/{room}/monsters/{mid}/appear',headers=hdr); ok('monster_appear',r.status_code==200,r.text)
    ps=c.get(f'/api/rooms/{room}/state',headers=ph).json(); cat=ps['monster_catalog'][0]; hidden = cat['name']=='???' and cat['hp']=='???' and cat['damage'] is None and cat['tags'] is None and original['data'].get('description','') not in json.dumps(ps,ensure_ascii=False)
    ok('catalog_hidden_data_not_leaked',hidden,json.dumps(cat,ensure_ascii=False)[:500])
    # Optional expansion examples are no longer startup/default data. A GM-created expansion still persists across init_db.
    gs=c.get(f'/api/rooms/{room}/state',headers=hdr).json(); ok('new_campaign_expansions_empty',gs.get('expansions')==[],str(gs.get('expansions')))
    r=c.post(f'/api/rooms/{room}/expansions',headers=hdr,json={'name':'커스텀 확장','gm_condition':'CUSTOM','public_intro':'테스트','data':{}}); ok('custom_expansion_create',r.status_code==200,r.text); eid=r.json().get('id') if r.status_code==200 else -1
    app.init_db()
    gs2=c.get(f'/api/rooms/{room}/state',headers=hdr).json(); e2=next((x for x in gs2['expansions'] if x['id']==eid),None); ok('custom_expansion_survives_restart_init',bool(e2 and e2['gm_condition']=='CUSTOM'),str(e2))
    ok('startup_does_not_inject_optional_examples',len(gs2.get('expansions',[]))==1,str(len(gs2.get('expansions',[]))))

print('\nSUMMARY')
for n,c,d in results: print(('PASS' if c else 'FAIL'),n,d if (not c) else '')
print('passed',sum(c for _,c,_ in results),'/',len(results))
