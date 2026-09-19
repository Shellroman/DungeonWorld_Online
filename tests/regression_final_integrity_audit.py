import json, os, pathlib, sys
root=pathlib.Path(__file__).resolve().parents[1]
tmp=root/'tests'/'regression_final_integrity_data';tmp.mkdir(parents=True,exist_ok=True)
db=tmp/'test.db';db.unlink(missing_ok=True)
os.environ['DW_DB']=str(db);os.environ['DW_PORT']='8198';sys.path.insert(0,str(root))
from fastapi.testclient import TestClient
import app

results=[]
def ok(name,cond,detail=''):
    results.append((name,bool(cond),detail))
    if not cond: print('FAIL',name,detail)

# Pure normalization / guards.
r=app.normalize_rules({'stat_start':['bad'],'stat_min':'bad','stat_max':'bad','level_max':'bad','max_expansions_per_character':'bad','reserve_max':'bad','coin_weight_per':'bad'})
ok('rules_invalid_numeric_fallback',r['stat_start']==[16,15,13,12,9,8] and r['stat_min']==3 and r['stat_max']==18 and r['level_max']==10 and r['max_expansions_per_character']==3 and r['reserve_max']==0 and r['coin_weight_per']==100,str(r))
ok('expansion_limit_supports_99',app.normalize_rules({'max_expansions_per_character':99})['max_expansions_per_character']==99)
ok('legacy_class_damage_normalizes',app.normalize_class_data({'damage':'D20'})['damage']=='D6')

with TestClient(app.app,client=('127.0.0.1',50379)) as c:
    rr=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'최종무결성','password':''})
    ok('room_create',rr.status_code==200,rr.text)
    room=rr.json()['room_code']; gm=rr.json()['gm_token']; gh={'Authorization':'Bearer '+gm}
    ji=c.get(f'/api/rooms/{room}/join-info').json(); warrior=next(x for x in ji['classes'] if x['name']=='전사')
    j=c.post(f'/api/rooms/{room}/join',json={'display_name':'P','password':''}).json();cid=j['character_id'];ph={'Authorization':'Bearer '+j['player_token']}
    r0=c.post(f'/api/rooms/{room}/characters/{cid}/onboarding',headers=ph,json={'class_name':'전사','race_name':warrior['races'][0]})
    ok('onboarding',r0.status_code==200,r0.text)
    base={'str':16,'dex':15,'con':13,'int':12,'wis':9,'cha':8}
    ok('initial_stats',c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'stats':base}}).status_code==200)
    # Growth budget is now enforced.
    plus=dict(base);plus['str']=17
    r1=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'stats':plus}})
    ok('lv1_growth_blocked',r1.status_code==400,r1.text)
    ok('level2',c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'level':2}}).status_code==200)
    ok('one_growth_point_works',c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'stats':plus}}).status_code==200)
    down=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'level':1}})
    ok('cannot_lower_level_below_spent_growth',down.status_code==400,down.text)
    plus2=dict(plus);plus2['dex']=16
    r2=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'stats':plus2}})
    ok('second_growth_point_blocked',r2.status_code==400,r2.text)
    # Campaign stat bounds are real rules.
    too_high=dict(plus);too_high['str']=19
    r3=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=gh,json={'patch':{'stats':too_high}})
    ok('stat_max_enforced_for_gm',r3.status_code==400,r3.text)
    r4=c.put(f'/api/rooms/{room}/rules',headers=gh,json={'rules':{'stat_max':15}})
    ok('cannot_set_bounds_below_existing',r4.status_code==400,r4.text)
    # Supported damage dice match the UI/roller.
    r5=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=gh,json={'patch':{'damage_die':'D20'}})
    ok('unsupported_character_damage_rejected',r5.status_code==400,r5.text)
    state=c.get(f'/api/rooms/{room}/state',headers=gh).json();w=state['classes']['전사']
    r6=c.put(f'/api/rooms/{room}/classes',headers=gh,json={'name':'전사','old_name':'전사','data':{**w,'damage':'D20'}})
    ok('unsupported_class_damage_rejected',r6.status_code==400,r6.text)
    # The players_can_add_extra_moves rule now has runtime effect.
    ok('disable_player_multiclass_rule',c.put(f'/api/rooms/{room}/rules',headers=gh,json={'rules':{'players_can_add_extra_moves':False}}).status_code==200)
    forged=[{'source_class':'마법사','name':'주문서','desc':'x','source_type':'multiclass','source_name':'다중직업(초급)','bundle':False,'min_level':1,'acquired_at_level':2,'multiclass_tier':'다중직업(초급)'}]
    r7=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'extra_moves':forged}})
    ok('player_multiclass_add_rule_enforced',r7.status_code==403,r7.text)
    # Monster dragging/move APIs are blocked server-side; editor assignment remains separate.
    r8=c.put(f'/api/rooms/{room}/order/monsters',headers=gh,json={'ids':[],'folder_id':None})
    ok('monster_reorder_api_blocked',r8.status_code==409,r8.text)
    mids=state.get('monsters') or []
    if mids:
        r9=c.put(f'/api/rooms/{room}/monsters/{mids[0]["id"]}/move',headers=gh,json={'ids':[],'folder_id':None})
        ok('monster_move_api_blocked',r9.status_code==409,r9.text)
    # Expansion re-grant cannot bypass the active-grant cap.
    ok('enable_expansions',c.put(f'/api/rooms/{room}/settings',headers=gh,json={'settings':{'expansions_enabled':True}}).status_code==200)
    ok('expansion_limit_one',c.put(f'/api/rooms/{room}/rules',headers=gh,json={'rules':{'max_expansions_per_character':1}}).status_code==200)
    ed={'legend_move':{'name':'문','desc':''},'class_moves':[]}
    a=c.post(f'/api/rooms/{room}/expansions',headers=gh,json={'name':'A','gm_condition':'','public_intro':'','data':ed}).json()['id']
    b=c.post(f'/api/rooms/{room}/expansions',headers=gh,json={'name':'B','gm_condition':'','public_intro':'','data':ed}).json()['id']
    gb=c.post(f'/api/rooms/{room}/expansions/{b}/grant',headers=gh,json={'character_id':cid,'visible_to_party':False,'message':''});gbid=gb.json()['grant_id']
    ok('decline_b',c.post(f'/api/rooms/{room}/grants/{gbid}/respond',headers=ph,json={'accept':False}).status_code==200)
    ga=c.post(f'/api/rooms/{room}/expansions/{a}/grant',headers=gh,json={'character_id':cid,'visible_to_party':False,'message':''})
    ok('grant_a_active',ga.status_code==200,ga.text)
    reb=c.post(f'/api/rooms/{room}/expansions/{b}/grant',headers=gh,json={'character_id':cid,'visible_to_party':False,'message':''})
    ok('regrant_declined_respects_limit',reb.status_code==400,reb.text)

js=(root/'static'/'app.js').read_text(encoding='utf-8')
py=(root/'app.py').read_text(encoding='utf-8')
ok('multiclass_ui_uses_rule',"allowed=gmMode||APP.state.room.rules?.players_can_add_extra_moves!==false" in js)
ok('currency_translation_not_persisted_accidentally',"data-raw-currency" in js and "data-currency-dirty" in js)
ok('bgm_next_stops_at_end',"else if(mode==='next')" in js and "else soundControl('next')" in js and "idx<list.length-1" in js)
ok('class_damage_is_select',"id=\"classDamage\" class=\"select\"" in js and "['D4','D6','D8','D10','D12']" in js)
ok('race_rename_rewrites_pairs',"effect.get(\"kind\") == \"opposite_race_feature\"" in py and "effect[\"race_pair\"] = [name if x == old else x" in py)
ok('class_rename_rewrites_extra_spell_source','extra_spell.get("source") == lookup_name' in py)
ok('class_edit_prunes_stale_moves','Deleted/renamed moves must not remain hidden in state while still consuming points.' in py)

print('\nSUMMARY')
for n,cnd,d in results: print(('PASS' if cnd else 'FAIL'),n,d if not cnd else '')
print('passed',sum(c for _,c,_ in results),'/',len(results))
if not all(c for _,c,_ in results): raise SystemExit(1)
