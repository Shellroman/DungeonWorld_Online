import json, os, pathlib, sqlite3, sys
root=pathlib.Path(__file__).resolve().parents[1]
tmp=root/'tests'/'inventory_migration_data';tmp.mkdir(parents=True,exist_ok=True)
db=tmp/'test.db';db.unlink(missing_ok=True)
os.environ['DW_DB']=str(db);sys.path.insert(0,str(root))
from fastapi.testclient import TestClient
import app
with TestClient(app.app,client=('127.0.0.1',50193)) as c:
    cr=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'M','password':''}).json();room=cr['room_code'];gm=cr['gm_token'];gh={'Authorization':'Bearer '+gm}
    ji=c.get(f'/api/rooms/{room}/join-info').json();cl=next(x for x in ji['classes'] if x['name']=='전사');race=cl['races'][0]
    j=c.post(f'/api/rooms/{room}/join',json={'display_name':'P','password':''}).json();cid=j['character_id'];ph={'Authorization':'Bearer '+j['player_token']}
    c.post(f'/api/rooms/{room}/characters/{cid}/onboarding',headers=ph,json={'class_name':'전사','race_name':race})
    state=c.get(f'/api/rooms/{room}/state',headers=ph).json()['character']['state']
    with sqlite3.connect(db) as con:
        gear=json.loads(con.execute('select data_json from class_defs where room_id=(select id from rooms where code=?) and name=?',(room,'전사')).fetchone()[0])['gear']
        state['memo']=gear+'\n\n[자유 메모]\n내가 적은 메모\n둘째 줄'
        state.pop('inventory',None)
        con.execute('update characters set state_json=? where id=?',(json.dumps(state,ensure_ascii=False),cid))
        con.execute("update app_meta set value='13' where key='schema_version'")
        con.commit()
    app.init_db()
    with sqlite3.connect(db) as con:
        raw=json.loads(con.execute('select state_json from characters where id=?',(cid,)).fetchone()[0]);schema=con.execute("select value from app_meta where key='schema_version'").fetchone()[0]
    assert schema==str(app.SCHEMA_VERSION),schema
    assert raw.get('inventory')==[],raw.get('inventory')
    assert raw.get('memo')=='내가 적은 메모\n둘째 줄',repr(raw.get('memo'))
print('inventory migration 13 -> 14 ok')
