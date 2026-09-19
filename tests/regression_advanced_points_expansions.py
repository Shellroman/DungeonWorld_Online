import json, os, pathlib, sys
root=pathlib.Path(__file__).resolve().parents[1]
tmp=root/'tests'/'regression_advanced_points_data';tmp.mkdir(parents=True,exist_ok=True)
db=tmp/'test.db';db.unlink(missing_ok=True)
os.environ['DW_DB']=str(db);os.environ['DW_PORT']='8188';sys.path.insert(0,str(root))
from fastapi.testclient import TestClient
import app

results=[]
def ok(name,cond,detail=''):
    results.append((name,bool(cond),detail))
    if not cond: print('FAIL',name,detail)

# Pure accounting: one cumulative point for every level above 1; expansion moves share it.
rules={**app.DEFAULT_RULES,'level_max':15}
s={'level':1,'advanced_moves':[],'extension_state':{}}
ok('lv1_zero_points',app.advanced_move_point_cap(s,rules)==0,str(app.advanced_move_point_cap(s,rules)))
s['level']=6
ok('lv6_five_points',app.advanced_move_point_cap(s,rules)==5,str(app.advanced_move_point_cap(s,rules)))
s['advanced_moves']=['A','B']
s['extension_state']={'10':{'legend_owned':True,'class_moves_owned':['X','Y']}}
ok('shared_usage_counts_all_moves',app.advanced_move_point_usage(s)==5,str(app.advanced_move_point_usage(s)))
s['level']=14
ok('unused_points_carry_forward',app.advanced_move_point_cap(s,rules)==13,str(app.advanced_move_point_cap(s,rules)))

with TestClient(app.app,client=('127.0.0.1',50329)) as c:
    rr=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'포인트회귀','password':''})
    ok('room_create',rr.status_code==200,rr.text)
    room=rr.json()['room_code'];gm=rr.json()['gm_token'];gh={'Authorization':'Bearer '+gm}
    # Enable expansion classes.
    r=c.put(f'/api/rooms/{room}/settings',headers=gh,json={'settings':{'expansions_enabled':True}})
    ok('enable_expansions',r.status_code==200,r.text)
    ji=c.get(f'/api/rooms/{room}/join-info').json();wizard=next(x for x in ji['classes'] if x['name']=='마법사');race=wizard['races'][0]
    j=c.post(f'/api/rooms/{room}/join',json={'display_name':'P','password':''}).json();cid=j['character_id'];ph={'Authorization':'Bearer '+j['player_token']}
    r=c.post(f'/api/rooms/{room}/characters/{cid}/onboarding',headers=ph,json={'class_name':'마법사','race_name':race})
    ok('onboarding',r.status_code==200,r.text)

    # Create and accept an expansion path. Acceptance itself does not grant the legendary move.
    exp_data={'legend_move':{'name':'별의 문','desc':'전설행동'},'class_moves':[{'name':'별빛 걸음','desc':'직업 행동 1'},{'name':'밤의 눈','desc':'직업 행동 2'}]}
    er=c.post(f'/api/rooms/{room}/expansions',headers=gh,json={'name':'별의 길','gm_condition':'','public_intro':'','data':exp_data})
    ok('create_expansion',er.status_code==200,er.text);eid=er.json()['id']
    gr=c.post(f'/api/rooms/{room}/expansions/{eid}/grant',headers=gh,json={'character_id':cid,'visible_to_party':False,'message':''})
    ok('offer_expansion',gr.status_code==200,gr.text);gid=gr.json()['grant_id']
    ac=c.post(f'/api/rooms/{room}/grants/{gid}/respond',headers=ph,json={'accept':True})
    ok('accept_expansion',ac.status_code==200,ac.text)
    ps=c.get(f'/api/rooms/{room}/state',headers=ph).json()
    st=ps['character']['state']
    ok('accept_does_not_auto_grant_legend',not (st.get('extension_state') or {}).get(str(gid),{}).get('legend_owned',False),json.dumps(st.get('extension_state'),ensure_ascii=False))

    # Level 1 has no advanced-move point, so the legendary move cannot be bought.
    ext={str(gid):{'legend_owned':True,'class_moves_owned':[],'resource_current':0}}
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'extension_state':ext}})
    ok('lv1_legend_rejected_no_point',r.status_code==400,r.text)

    # Level 2 gives one point. Legendary Move costs that point.
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'level':2}})
    ok('level2',r.status_code==200,r.text)
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'extension_state':ext}})
    ok('legend_costs_one_point',r.status_code==200,r.text)
    ext2={str(gid):{'legend_owned':True,'class_moves_owned':['별빛 걸음'],'resource_current':0}}
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'extension_state':ext2}})
    ok('class_move_rejected_when_no_point',r.status_code==400,r.text)

    # At level 3, one more point is available and the expansion class move can be selected.
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'level':3}})
    ok('level3',r.status_code==200,r.text)
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'extension_state':ext2}})
    ok('expansion_class_move_costs_point',r.status_code==200,r.text)

    # A base advanced move competes for the same shared pool.
    gs=c.get(f'/api/rooms/{room}/state',headers=gh).json();w=gs['classes']['마법사'];a25=(w.get('a25') or [])[0]['name']
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'advanced_moves':[a25]}})
    ok('base_move_rejected_when_shared_pool_full',r.status_code==400,r.text)
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'level':4}})
    ok('level4',r.status_code==200,r.text)
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'advanced_moves':[a25]}})
    ok('base_move_uses_next_shared_point',r.status_code==200,r.text)

    # Lower-tier moves remain selectable later; the unlock level is a minimum, not an expiry window.
    # Remove the base move, then go to level 6 and add it again.
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'advanced_moves':[]}})
    ok('unselect_base_move',r.status_code==200,r.text)
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'level':6}})
    ok('level6',r.status_code==200,r.text)
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'advanced_moves':[a25]}})
    ok('a25_still_selectable_after_level5',r.status_code==200,r.text)

    # Class moves cannot remain owned if the legendary move is removed in a forged request.
    bad={str(gid):{'legend_owned':False,'class_moves_owned':['별빛 걸음'],'resource_current':0}}
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'extension_state':bad}})
    ok('class_move_requires_legend',r.status_code==400,r.text)

    # Campaign progression rules are authoritative and can extend beyond the original level 10.
    r=c.put(f'/api/rooms/{room}/rules',headers=gh,json={'rules':{'level_max':12,'xp_base':9}})
    ok('raise_max_level_and_xp_base',r.status_code==200,r.text)
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'level':11}})
    ok('level11_allowed_after_rule_raise',r.status_code==200,r.text)
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'level':13}})
    ok('above_max_level_rejected',r.status_code==400,r.text)
    ps=c.get(f'/api/rooms/{room}/state',headers=ph).json();summary=next(x for x in ps['party'] if x['character_id']==cid)
    ok('xp_formula_uses_configured_base',summary['xp_required']==20,str(summary['xp_required']))
    r=c.put(f'/api/rooms/{room}/rules',headers=gh,json={'rules':{'level_max':10}})
    ok('cannot_lower_max_below_existing_character',r.status_code==400,r.text)

    # 0 expansion limit means unlimited, matching the rules UI.
    r=c.put(f'/api/rooms/{room}/rules',headers=gh,json={'rules':{'max_expansions_per_character':0}})
    ok('expansion_limit_zero_saved',r.status_code==200,r.text)
    er2=c.post(f'/api/rooms/{room}/expansions',headers=gh,json={'name':'두번째 길','gm_condition':'','public_intro':'','data':exp_data})
    eid2=er2.json()['id']
    gr2=c.post(f'/api/rooms/{room}/expansions/{eid2}/grant',headers=gh,json={'character_id':cid,'visible_to_party':False,'message':''})
    ok('zero_expansion_limit_is_unlimited',gr2.status_code==200,gr2.text)

js=(root/'static'/'app.js').read_text(encoding='utf-8')
ok('monster_buttons_not_draggable','data-sort-kind="monsters"' not in js and 'data-folder-drop=' not in js)
ok('folders_still_draggable','data-sort-kind="folders"' in js and 'draggable="true"' in js)
ok('monster_move_drop_code_removed','/order/monsters' not in js and '/monsters/${dragged.id}/move' not in js)
ok('extension_ui_shares_points','extensionMovePointUsage' in js and 'Advanced-move points:' in js)
ok('rules_ui_max_99','id="ruleLevel" class="input" type="number" min="1" max="99"' in js)

print('\nSUMMARY')
for n,cnd,d in results: print(('PASS' if cnd else 'FAIL'),n,d if not cnd else '')
print('passed',sum(c for _,c,_ in results),'/',len(results))
if not all(c for _,c,_ in results): raise SystemExit(1)
