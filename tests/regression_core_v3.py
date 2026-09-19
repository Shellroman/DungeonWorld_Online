import json, os, pathlib, sys
root=pathlib.Path(__file__).resolve().parents[1]
tmp=root/'tests'/'regression_core_v3_data';tmp.mkdir(parents=True,exist_ok=True)
db=tmp/'test.db'
if db.exists(): db.unlink()
os.environ['DW_DB']=str(db);os.environ['DW_PORT']='8162';sys.path.insert(0,str(root))
from fastapi.testclient import TestClient
import app

results=[]
def ok(name,cond,detail=''):
    results.append((name,bool(cond),detail))
    if not cond: print('FAIL',name,detail)

with TestClient(app.app,client=('127.0.0.1',50192)) as c:
    r=c.get('/')
    ok('current_web_label',r.status_code==200 and 'v1.0.0' in r.text)
    rr=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'실험3','password':''});room=rr.json()['room_code'];gm=rr.json()['gm_token'];gh={'Authorization':'Bearer '+gm}
    ji=c.get(f'/api/rooms/{room}/join-info').json();wizard=next(x for x in ji['classes'] if x['name']=='마법사');race=wizard['races'][0]
    j=c.post(f'/api/rooms/{room}/join',json={'display_name':'장비테스트','password':''}).json();cid=j['character_id'];ph={'Authorization':'Bearer '+j['player_token']}
    c.post(f'/api/rooms/{room}/characters/{cid}/onboarding',headers=ph,json={'class_name':'마법사','race_name':race})
    stats={'str':12,'dex':16,'con':13,'int':15,'wis':9,'cha':8}
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'stats':stats}})
    ok('inventory_initial_stats',r.status_code==200,r.text)
    inv=[
      {'name':'모험 장비','quantity':1,'weight':1,'uses_current':3,'uses_max':5,'tags':'5회분','note':'필요할 때 꺼낸다'},
      {'name':'단검','quantity':2,'weight':1,'uses_current':0,'uses_max':0,'tags':'무기, 한걸음','weapon_range':'근거리','damage':'+1 피해','note':''},
      {'name':'치유 물약','quantity':1,'weight':0,'tags':'','note':'긴급용'},
    ]
    r=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'inventory':inv,'currency':37}})
    ok('inventory_patch',r.status_code==200,r.text)
    ps=c.get(f'/api/rooms/{room}/state',headers=ph).json();st=ps['character']['state'];summary=ps['party'][0]
    ok('inventory_roundtrip',len(st.get('inventory',[]))==3 and st['inventory'][0]['uses_current']==3,str(st.get('inventory')))
    ok('inventory_weapon_details_roundtrip',st['inventory'][1].get('weapon_range')=='근거리' and st['inventory'][1].get('damage')=='+1 피해',str(st['inventory'][1]))
    ok('inventory_currency_shared',st.get('currency')==37,str(st.get('currency')))
    ok('inventory_weight_server',summary.get('load_current')==3.37,str(summary.get('load_current')))
    ok('inventory_load_max_server',summary.get('load_max')==(wizard.get('load',7)+0),str(summary.get('load_max')))
    # server normalization should cap uses and reject negative-ish values by normalization, not crash
    noisy=[{'name':'붕대','quantity':0,'weight':-2,'uses_current':9,'uses_max':3,'tags':'slow','note':''}]
    c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'inventory':noisy}})
    st2=c.get(f'/api/rooms/{room}/state',headers=ph).json()['character']['state']['inventory'][0]
    ok('inventory_normalized',st2['quantity']==1 and st2['weight']==0 and st2['uses_current']==3,str(st2))

js=(root/'static'/'app.js').read_text(encoding='utf-8')
css=(root/'static'/'styles.css').read_text(encoding='utf-8')
app_py=(root/'app.py').read_text(encoding='utf-8')
build=(root/'build_release.py').read_text(encoding='utf-8')
go=(root/'launcher'/'main.go').read_text(encoding='utf-8')

ok('schema20','SCHEMA_VERSION = 20' in app_py)
ok('inventory_ui','renderInventoryPage' in js and 'collectInventory' in js and 'inventoryCurrency' in js and '직업 시작 장비 안내' in js)
ok('inventory_text_style','.inventory-text-line{' in css and '.inventory-list{border-top:4px solid #111' in css and 'border:0!important' in css and 'inventory-add-text' in css)
ok('inventory_auto_weight','inventoryWeight(s)' in js and 'quantity)||1)*Math.max(0,Number(item?.weight)' in js)
ok('player_single_constrained','player-single-workspace' in js and '.player-single-workspace{max-width:1396px' in css)
ok('summary_kept','data-character-summary' in js and 'characterSummaryModal' in js)
ok('quickref_moved_into_help',"{title:'빠른 참조',quickref:true" in js and "['quickref','빠른 참조 · 실험']" not in js and 'renderGMQuickRef' not in js)
ok('help_source_groups','영문 원본' in js and '한국어판' in js and 'help-source-groups' in js and '.help-source-groups' in css)
ok('help_inventory_plain','인벤토리와 장비' in js and '물건 기록하기' in js and '사용 횟수와 탄약' in js and '프로그램이 대신 판정하지 않습니다' in js)
ok('monster_quick_builder','showMonsterBuilder' in js and 'monsterQuickBuild' in js and '현재 몬스터 편집기에 적용' in js and '대집단 · D6 / HP 3' in js)
ok('monster_catalog_status_dots','monsterCatalogState' in js and 'monster-catalog-dot seen' in js and 'monster-catalog-dot partial' in js and 'monster-catalog-dot full' in js and '.monster-catalog-dot.seen' in css)
ok('legacy_quickref_css_removed','.quickref-layout{' not in css)
ok('current_brand','v{app_version}' in app_py and 'DISPLAY_VERSION = f"v{APP_VERSION}"' in build and 'return "v" + v' in go)
ok('release_banner','v1.0.0 · 비공식 팬메이드 도구' in js and ('출시 전 '+'최종 확인판') not in js)
ok('starting_gear_autofill_removed',"gear+'\\n\\n[자유 메모]" not in js)

print('\nSUMMARY')
for n,c,d in results: print(('PASS' if c else 'FAIL'),n,d if not c else '')
print('passed',sum(c for _,c,_ in results),'/',len(results))
if not all(c for _,c,_ in results): raise SystemExit(1)
