import os, sys, pathlib, json, base64
root=pathlib.Path(__file__).resolve().parents[1]
db=root/'tests'/'regression_features_21.db'; db.unlink(missing_ok=True)
os.environ['DW_DB']=str(db); os.environ['DW_PORT']='8131'; sys.path.insert(0,str(root))
from fastapi.testclient import TestClient
import app
app.require_local_request=lambda request: None

with TestClient(app.app, client=("127.0.0.1",50000)) as c:
    cr=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'B21','password':''}); assert cr.status_code==200,cr.text
    room=cr.json()['room_code']; gh={'Authorization':'Bearer '+cr.json()['gm_token']}
    ji=c.get(f'/api/rooms/{room}/join-info').json(); wc=next(x for x in ji['classes'] if x['name']=='전사'); race=wc['races'][0]
    p1=c.post(f'/api/rooms/{room}/join',json={'display_name':'P1','password':''}).json()
    p2=c.post(f'/api/rooms/{room}/join',json={'display_name':'P2','password':''}).json()
    h1={'Authorization':'Bearer '+p1['player_token']}; h2={'Authorization':'Bearer '+p2['player_token']}
    p1state=c.get(f'/api/rooms/{room}/state',headers=h1).json(); assert p1state['character']['state']['onboarding_complete'] is False and p1state['party'][0]['status_text']=='자신의 운명을 결정하는 중'
    assert c.post(f'/api/rooms/{room}/characters/{p1["character_id"]}/onboarding',headers=h1,json={'class_name':'전사','race_name':race}).status_code==200
    assert c.post(f'/api/rooms/{room}/characters/{p2["character_id"]}/onboarding',headers=h2,json={'class_name':'전사','race_name':race}).status_code==200
    assert c.get(f'/api/rooms/{room}/state',headers=h1).status_code==200

    # reconnect code: one-time, rotates token, restores same character.
    rr=c.post(f'/api/rooms/{room}/members/{p1["member_id"]}/reconnect-code',headers=gh); assert rr.status_code==200,rr.text
    reconnect=rr.json()['reconnect_code']; assert reconnect.startswith(room+'-')
    restored=c.post(f'/api/rooms/{room}/reconnect',json={'reconnect_code':reconnect}); assert restored.status_code==200,restored.text
    rj=restored.json(); assert rj['character_id']==p1['character_id'] and rj['display_name']=='P1'
    assert c.post(f'/api/rooms/{room}/reconnect',json={'reconnect_code':reconnect}).status_code==403
    assert c.get(f'/api/rooms/{room}/state',headers=h1).status_code==401
    h1n={'Authorization':'Bearer '+rj['player_token']}; assert c.get(f'/api/rooms/{room}/state',headers=h1n).status_code==200

    # Disable / enable access.
    x=c.put(f'/api/rooms/{room}/members/{p1["member_id"]}/enabled',headers=gh,json={'enabled':False}); assert x.status_code==200
    assert c.get(f'/api/rooms/{room}/state',headers=h1n).status_code==403
    x=c.put(f'/api/rooms/{room}/members/{p1["member_id"]}/enabled',headers=gh,json={'enabled':True}); assert x.status_code==200
    assert c.get(f'/api/rooms/{room}/state',headers=h1n).status_code==200

    # Swap character ownership and keep both characters valid.
    x=c.put(f'/api/rooms/{room}/members/{p1["member_id"]}/character',headers=gh,json={'character_id':p2['character_id']}); assert x.status_code==200,x.text
    assert x.json()['swapped'] is True
    s1=c.get(f'/api/rooms/{room}/state',headers=h1n).json(); s2=c.get(f'/api/rooms/{room}/state',headers=h2).json()
    assert s1['character']['character_id']==p2['character_id']; assert s2['character']['character_id']==p1['character_id']

    # Undefined special spell can be defined, granted and revoked.
    x=c.put(f'/api/rooms/{room}/spell',headers=gh,json={'class_name':'__undefined__','name':'목석의 말','level':'암송','desc':'특수 주문'}); assert x.status_code==200,x.text
    gs=c.get(f'/api/rooms/{room}/state',headers=gh).json(); sp=next(x for x in gs['spells']['__undefined__'] if x['name']=='목석의 말')
    x=c.post(f'/api/rooms/{room}/characters/{p2["character_id"]}/special-spells',headers=gh,json={'spell_id':sp['id']}); assert x.status_code==200,x.text
    ps=c.get(f'/api/rooms/{room}/state',headers=h1n).json(); grants=[x for x in ps['character']['state']['extra_spells'] if x.get('kind')=='gm']; assert grants and grants[0]['name']=='목석의 말' and str(grants[0]['level'])=='암송'
    x=c.delete(f'/api/rooms/{room}/characters/{p2["character_id"]}/special-spells/{sp["id"]}',headers=gh); assert x.status_code==200,x.text
    ps=c.get(f'/api/rooms/{room}/state',headers=h1n).json(); assert not [x for x in ps['character']['state']['extra_spells'] if x.get('kind')=='gm']

    # Invite code payload matches launcher DW2 schema and 2.1 version/build.
    x=c.get(f'/api/rooms/{room}/invite-codes',headers=gh); assert x.status_code==200,x.text
    inv=x.json()['invites'][0]['invite_code']; assert inv.startswith('DW2-')
    raw=inv[4:]; raw += '='*((4-len(raw)%4)%4); payload=json.loads(base64.urlsafe_b64decode(raw).decode())
    assert payload['f']==2 and payload['r']==room and payload['v']=='1.0.0' and payload['b']==app.BUILD_ID

    # Sound pause/resume preserve position and return state immediately.
    with app.db() as con:
        rid=con.execute('SELECT id FROM rooms WHERE code=?',(room,)).fetchone()['id']
        cur=con.execute("INSERT INTO sound_defs(room_id,name,kind,source_type,source,sort_order,created_at) VALUES(?,?,?,?,?,?,?)",(rid,'T','bgm','file','/api/sounds/test.mp3',1,'2026-09-10T00:00:00'))
        sid=cur.lastrowid
    x=c.post(f'/api/rooms/{room}/sounds/play',headers=gh,json={'sound_id':sid,'position':0,'volume':0.8}); assert x.status_code==200 and x.json()['state']['status']=='playing'
    x=c.post(f'/api/rooms/{room}/sounds/pause',headers=gh,json={'sound_id':sid,'position':42.5,'volume':0.8}); assert x.status_code==200 and x.json()['state']['status']=='paused' and abs(x.json()['state']['position']-42.5)<0.01
    x=c.post(f'/api/rooms/{room}/sounds/control',headers=gh,json={'action':'resume','position':0}); assert x.status_code==200 and x.json()['state']['status']=='playing' and abs(x.json()['state']['position']-42.5)<0.01

    # Participant delete cascades character.
    x=c.delete(f'/api/rooms/{room}/members/{p2["member_id"]}',headers=gh); assert x.status_code==200,x.text
    with app.db() as con:
        assert con.execute('SELECT 1 FROM members WHERE id=?',(p2['member_id'],)).fetchone() is None
        # p2 owned p1's character after swap, so that character is deleted.
        assert con.execute('SELECT 1 FROM characters WHERE id=?',(p1['character_id'],)).fetchone() is None

print('feature regression 2.1 lineage ok')
