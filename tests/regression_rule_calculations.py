import json, os, pathlib, sys
root=pathlib.Path(__file__).resolve().parents[1]
tmp=root/'tests'/'regression_rule_calculations_data';tmp.mkdir(parents=True,exist_ok=True)
db=tmp/'test.db';db.unlink(missing_ok=True)
os.environ['DW_DB']=str(db);os.environ['DW_PORT']='8179';sys.path.insert(0,str(root))
from fastapi.testclient import TestClient
import app

results=[]
def ok(name,cond,detail=''):
    results.append((name,bool(cond),detail))
    if not cond: print('FAIL',name,detail)

# Pure rule helpers: Load uses the configured modifier table, not raw Strength.
ok('stat_mod_12_zero', app.stat_modifier(12, app.DEFAULT_RULES)==0, str(app.stat_modifier(12, app.DEFAULT_RULES)))
ok('stat_mod_16_plus_two', app.stat_modifier(16, app.DEFAULT_RULES)==2, str(app.stat_modifier(16, app.DEFAULT_RULES)))
custom={**app.DEFAULT_RULES,'stat_mod_ranges':[{'max':10,'mod':-1},{'max':20,'mod':4},{'max':99,'mod':7}]}
ok('stat_mod_custom_rules', app.stat_modifier(16, custom)==4, str(app.stat_modifier(16, custom)))

state={'inventory':[{'name':'A','quantity':2,'weight':1.5}],'currency':250}
ok('weight_items_and_coins', app.inventory_weight(state, app.DEFAULT_RULES)==5.5, str(app.inventory_weight(state, app.DEFAULT_RULES)))
no_coins={**app.DEFAULT_RULES,'coin_weight_enabled':False}
ok('weight_coin_rule_off', app.inventory_weight(state, no_coins)==3.0, str(app.inventory_weight(state, no_coins)))

with TestClient(app.app,client=('127.0.0.1',50319)) as c:
    rr=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'계산회귀','password':''});
    ok('room_create',rr.status_code==200,rr.text)
    room=rr.json()['room_code'];gm=rr.json()['gm_token'];gh={'Authorization':'Bearer '+gm}
    ji=c.get(f'/api/rooms/{room}/join-info').json();wizard=next(x for x in ji['classes'] if x['name']=='마법사');race=wizard['races'][0]
    j=c.post(f'/api/rooms/{room}/join',json={'display_name':'P','password':''}).json();cid=j['character_id'];ph={'Authorization':'Bearer '+j['player_token']}
    c.post(f'/api/rooms/{room}/characters/{cid}/onboarding',headers=ph,json={'class_name':'마법사','race_name':race})
    stats={'str':16,'dex':15,'con':13,'int':12,'wis':9,'cha':8}
    c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'stats':stats,'inventory':[{'name':'짐','quantity':1,'weight':2}],'currency':200}})
    ps=c.get(f'/api/rooms/{room}/state',headers=ph).json();summary=next(x for x in ps['party'] if x['character_id']==cid)
    ok('wizard_str16_load_is_base_plus_2', summary['load_max']==int(wizard.get('load',7))+2, str(summary))
    ok('server_summary_includes_coin_weight', summary['load_current']==4.0, str(summary['load_current']))

    # Damage rolls have a floor of 0, but ordinary checks are not clamped.
    prep=c.post(f'/api/rooms/{room}/dice/prepare',headers=ph,json={'dice':{'d2':1},'modifier':-99,'minimum_total':0,'context':'피해'})
    ok('damage_floor_prepare',prep.status_code==200 and prep.json()['preparation'].get('minimum_total')==0,prep.text)
    roll=c.post(f'/api/rooms/{room}/dice/roll',headers=ph).json()['roll']
    ok('damage_floor_zero',roll['total']==0,json.dumps(roll,ensure_ascii=False))
    c.post(f'/api/rooms/{room}/dice/prepare',headers=ph,json={'dice':{'d2':1},'modifier':-99,'context':'일반 판정'})
    roll2=c.post(f'/api/rooms/{room}/dice/roll',headers=ph).json()['roll']
    ok('ordinary_roll_can_be_negative',roll2['total']<0,json.dumps(roll2,ensure_ascii=False))

    # High mode must actually have multiple dice to choose from.
    c.post(f'/api/rooms/{room}/dice/prepare',headers=ph,json={'dice':{'d8':2},'modifier':0,'roll_mode':'high','minimum_total':0})
    high=c.post(f'/api/rooms/{room}/dice/roll',headers=ph).json()['roll']
    vals=[x['value'] for x in high['results']]
    ok('high_roll_two_dice',len(vals)==2 and high['dice_total']==max(vals),json.dumps(high,ensure_ascii=False))

js=(root/'static'/'app.js').read_text(encoding='utf-8')
ok('client_load_uses_modifier','(Number(classData(s).load)||0)+statMod(s?.stats?.str)' in js and '(Number(c.load)||0)+statMod(stats.str)' in js)
ok('monster_offense_rolls_twice',"k==='offense'){mode='high';count=2}" in js)
ok('magic_armor_auto_tag',"if(defense===4||magic)tags.push('마법적')" in js)
ok('damage_prepares_floor_zero','minimum_total:0' in js)
ok('dice_presets_reset_state',"prep.roll_mode='normal';prep.minimum_total=null;prep.context='';$('#diceModifier').value=0" in js)

print('\nSUMMARY')
for n,c,d in results: print(('PASS' if c else 'FAIL'),n,d if not c else '')
print('passed',sum(c for _,c,_ in results),'/',len(results))
if not all(c for _,c,_ in results): raise SystemExit(1)
