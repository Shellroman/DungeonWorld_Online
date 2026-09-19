import json, os, pathlib, sys, zipfile
root=pathlib.Path(__file__).resolve().parents[1]
tmp=root/'tests'/'regression_inventory_refine_data';tmp.mkdir(parents=True,exist_ok=True)
db=tmp/'test.db';db.unlink(missing_ok=True)
os.environ['DW_DB']=str(db);os.environ['DW_PORT']='8171';sys.path.insert(0,str(root))
from fastapi.testclient import TestClient
import app

results=[]
def ok(name,cond,detail=''):
    results.append((name,bool(cond),detail))
    if not cond: print('FAIL',name,detail)

with TestClient(app.app,client=('127.0.0.1',50311)) as c:
    rr=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'인벤토리정리','password':''}).json();room=rr['room_code'];gh={'Authorization':'Bearer '+rr['gm_token']}
    j=c.post(f'/api/rooms/{room}/join',json={'display_name':'P','password':''}).json();ph={'Authorization':'Bearer '+j['player_token']};cid=j['character_id']
    ji=c.get(f'/api/rooms/{room}/join-info').json();fighter=next(x for x in ji['classes'] if x['name']=='전사');race=fighter['races'][0]
    c.post(f'/api/rooms/{room}/characters/{cid}/onboarding',headers=ph,json={'class_name':'전사','race_name':race})
    inv=[
      {'name':'레이피어','quantity':1,'weight':1,'tags':'한걸음, 정밀','damage':'+1 피해'},
      {'name':'방패','quantity':1,'weight':2,'tags':'장갑 +1'},
      {'name':'사슬 갑옷','quantity':1,'weight':1,'tags':'장갑 1, 착용'},
      {'name':'사냥활','quantity':1,'weight':1,'tags':'중거리, 장거리, 발수 3'},
      {'name':'붕대','quantity':1,'weight':0,'uses_current':2,'uses_max':3,'tags':'느림'},
      {'name':'왕실 인장','item_type':'중요한 물건','quantity':1,'weight':0,'tags':'왕가의 문장'},
      {'name':'정체불명의 병','item_type':'독','quantity':1,'weight':0,'tags':'위험, 접촉'},
    ]
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'inventory':inv}})
    ok('patch_inventory',r.status_code==200,r.text)
    st=c.get(f'/api/rooms/{room}/state',headers=ph).json()['character']['state']['inventory']
    types=[x.get('item_type') for x in st]
    ok('legacy_weapon_inferred',types[0]=='무기',str(types))
    ok('legacy_armor_inferred',types[1]=='갑옷',str(types))
    ok('legacy_base_armor_inferred',types[2]=='갑옷' and st[2]['armor_value']==1,str(st[2]))
    ok('current_weapon_ammo_detached',types[3]=='무기' and st[3]['ammo_current']==0 and st[3]['ammo_max']==0,str(st[3]))
    ok('dungeon_gear_inferred_before_consumable',types[4]=='던전 장비',str(types))
    ok('explicit_important_preserved',types[5]=='중요한 물건',str(types))
    ok('explicit_poison_preserved',types[6]=='독',str(types))
    ok('legacy_weapon_damage_becomes_modifier',st[0]['damage_bonus']==1 and st[0]['damage']=='+1 피해',str(st[0]))
    ok('legacy_shield_becomes_bonus_armor',st[1]['armor_value']==0 and st[1]['armor_bonus']==1,str(st[1]))
    ok('tags_remain_free_text',st[0]['tags']=='한걸음, 정밀' and st[6]['tags']=='위험, 접촉',str(st))

js=(root/'static/app.js').read_text(encoding='utf-8')
css=(root/'static/styles.css').read_text(encoding='utf-8')
seed=json.loads((root/'data/seed_data.json').read_text(encoding='utf-8'))
py=(root/'app.py').read_text(encoding='utf-8')

for label in ['일반 장비','무기','갑옷','던전 장비','소모품','독','탄약','마법 물품','중요한 물건']:
    ok('inventory_type_'+label,label in js,label)
ok('item_type_persisted','item_type:String(val(\'item_type\')).trim()' in js and '"item_type": item_type' in py)
ok('weapon_type_drives_detail',"weapon=type==='무기'" in js)
ok('weapon_uses_damage_modifier','data-inv="damage_bonus"' in js and '피해 수정치' in js and '피해 주사위는 무기마다 따로 정하는 것이 아니라' in js)
ok('armor_split_fields','data-inv=\"armor_value\"' in js and 'data-inv=\"armor_bonus\"' in js and 'inventoryArmorInfo' in js)
ok('uses_and_ammo_separate','data-inv=\"uses_current\"' in js and 'data-inv=\"ammo_current\"' in js and '추상 자원' in js)
ok('dungeon_and_consumable_drive_uses',"usesItem=type==='소모품'||type==='던전 장비'||um>0" in js)
ok('tags_are_manual','placeholder="예: 정밀, 관통 1, 느림"' in js)
ok('currency_compact_right','.inventory-currency{display:flex' in css and 'margin:10px 0 0 auto' in css and 'text-align:center!important' in css)
ok('inventory_fonts_slightly_larger','.inventory-primary-line{font-size:15px}' in css and '.inventory-key{font-size:12px' in css and '.inventory-tags-text' in css and 'font-size:15px' in css)

for name,cdata in seed['classes'].items():
    gear=cdata.get('gear','')
    ok('gear_title_'+name,gear.startswith(f'[시작 장비 안내 — {name}]'),gear[:80])
    ok('gear_load_line_'+name,'최대 하중:' in gear and '근력(STR)' in gear,gear[:160])
    ok('gear_no_joined_sections_'+name,'근력기본:' not in gear and '닢근' not in gear and '레이피어장거리' not in gear and '다발추가' not in gear and '성표방어구' not in gear and '옷무기' not in gear and '노래책복장' not in gear,gear)
    ok('gear_has_spacing_'+name,'\n\n' in gear,gear)

user_visible=js+'\n'+json.dumps(seed,ensure_ascii=False)
for old in ['보정치','능력수정치','한계 하중','던전 식량','치유 물약','약초와 찜질약','비늘 갑옷']:
    ok('term_removed_'+old,old not in user_visible,old)
ok('modifier_term_unified','수정치' in js and '능력치 수정치' in user_visible)
ok('move_term_unified_seed','액션' not in json.dumps(seed,ensure_ascii=False) and '행동' in json.dumps(seed,ensure_ascii=False))
ok('gm_term_unified_seed','마스터' not in json.dumps(seed,ensure_ascii=False) and 'GM' in json.dumps(seed,ensure_ascii=False))
ok('hidden_label_korean','HIDDEN ·' not in js and '>HIDDEN<' not in js and "'히든 · '" in js)
ok('range_terms_korean_english','반걸음(hand)' in js and '한걸음(close)' in js and '몇걸음(reach)' in js)

with zipfile.ZipFile(root/'dwpack'/'DungeonWorld_1E_Core.dwpack') as z:
    classes=json.loads(z.read('data/classes.json'))
    fighter_pack=next(x for x in classes if x['name']=='전사')['data']['gear']
    ok('core_pack_starting_gear_synced','[시작 장비 안내 — 전사]' in fighter_pack and '최대 하중:' in fighter_pack,fighter_pack[:200])
    alltxt='\n'.join(z.read(n).decode('utf-8','ignore') for n in z.namelist() if n.endswith('.json'))
    ok('core_pack_terms_synced','보정치' not in alltxt and '마스터' not in alltxt and '액션' not in alltxt)

print('\nSUMMARY')
for n,p,d in results: print(('PASS' if p else 'FAIL'),n,d if not p else '')
print('passed',sum(p for _,p,_ in results),'/',len(results))
if not all(p for _,p,_ in results): raise SystemExit(1)
