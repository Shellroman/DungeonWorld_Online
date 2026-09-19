import os, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
TMP=ROOT/'tests'/'campaign_capacity_default_language_data'; TMP.mkdir(parents=True,exist_ok=True)
DB=TMP/'test.db'; DB.unlink(missing_ok=True)
os.environ['DW_DB']=str(DB); os.environ['DW_PORT']='8291'
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
import app

checks=[]
def ok(name,cond,detail=''):
    checks.append((name,bool(cond),detail))
    if not cond: print('FAIL',name,detail)

js=(ROOT/'static/app.js').read_text(encoding='utf-8')
html=(ROOT/'static/index.html').read_text(encoding='utf-8')
go=(ROOT/'launcher/main.go').read_text(encoding='utf-8')

ok('schema20',app.SCHEMA_VERSION==20)
ok('app_default_english',"localStorage.getItem(LANGUAGE_KEY)==='ko'?'ko':'en'" in js)
ok('html_default_english','<html lang="en"' in html)
ok('launcher_default_english',"localStorage.getItem(LKEY)==='ko'?'ko':'en'" in go)
ok('launcher_capacity_select','id="campaignMaxPlayers"' in go and 'value="4" selected' in go)
ok('launcher_capacity_bounds',all(f'value="{n}"' in go for n in range(2,9)))

with TestClient(app.app,client=('127.0.0.1',50501)) as c:
    created=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'Cap','password':'','max_players':2})
    ok('create_2_capacity',created.status_code==200,created.text)
    data=created.json(); room=data['room_code']
    info=c.get(f'/api/rooms/{room}/join-info')
    ok('join_info_capacity',info.status_code==200 and info.json().get('max_players')==2 and info.json().get('player_count')==0,info.text)
    j1=c.post(f'/api/rooms/{room}/join',json={'display_name':'P1','password':''})
    j2=c.post(f'/api/rooms/{room}/join',json={'display_name':'P2','password':''})
    j3=c.post(f'/api/rooms/{room}/join',json={'display_name':'P3','password':''})
    ok('first_two_join',j1.status_code==200 and j2.status_code==200,(j1.text,j2.text))
    ok('third_join_blocked',j3.status_code==409,j3.text)
    info2=c.get(f'/api/rooms/{room}/join-info').json()
    ok('full_flag',info2.get('player_count')==2 and info2.get('max_players')==2 and info2.get('full') is True,str(info2))
    # Existing players can still reconnect/read state at capacity.
    p1=j1.json(); st=c.get(f'/api/rooms/{room}/state',headers={'Authorization':'Bearer '+p1['player_token']})
    ok('existing_player_not_blocked',st.status_code==200,st.text[:300])
    # Creation bounds are server-enforced.
    low=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'Low','password':'','max_players':1})
    high=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'High','password':'','max_players':9})
    ok('capacity_min_enforced',low.status_code==422,low.text)
    ok('capacity_max_enforced',high.status_code==422,high.text)

print('\nSUMMARY')
for n,p,d in checks: print(('PASS' if p else 'FAIL'),n,d if not p else '')
print('passed',sum(p for _,p,_ in checks),'/',len(checks))
DB.unlink(missing_ok=True)
if not all(p for _,p,_ in checks): raise SystemExit(1)
