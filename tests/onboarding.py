import os, sys, pathlib
root=pathlib.Path(__file__).resolve().parents[1]
db=root/'tests'/'onboarding.db'; db.unlink(missing_ok=True)
os.environ['DW_DB']=str(db); os.environ['DW_PORT']='8138'; sys.path.insert(0,str(root))
from fastapi.testclient import TestClient
import app
app.require_local_request=lambda request: None

with TestClient(app.app, client=("127.0.0.1",50000)) as c:
    cr=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'운명','password':'pw'}); assert cr.status_code==200,cr.text
    room=cr.json()['room_code']; gh={'Authorization':'Bearer '+cr.json()['gm_token']}
    ji=c.get(f'/api/rooms/{room}/join-info').json(); wizard=next(x for x in ji['classes'] if x['name']=='마법사'); race=wizard['races'][0]
    # Old class/race fields are accepted for compatibility but intentionally ignored.
    jp=c.post(f'/api/rooms/{room}/join',json={'display_name':'결정중','password':'pw','class_name':'마법사','race_name':race}); assert jp.status_code==200,jp.text
    j=jp.json(); ph={'Authorization':'Bearer '+j['player_token']}; cid=j['character_id']
    st=c.get(f'/api/rooms/{room}/state',headers=ph).json(); assert st['character']['state']['class_name']=='' and st['character']['state']['race_name']=='' and st['character']['state']['onboarding_complete'] is False
    own=next(x for x in st['party'] if x['character_id']==cid); assert own['class_name']=='무직' and own['race_name']=='없음' and own['status_text']=='자신의 운명을 결정하는 중'
    # Another player also sees only the pending public identity.
    p2=c.post(f'/api/rooms/{room}/join',json={'display_name':'관전자','password':'pw'}).json(); h2={'Authorization':'Bearer '+p2['player_token']}
    other=c.get(f'/api/rooms/{room}/state',headers=h2).json(); seen=next(x for x in other['party'] if x['character_id']==cid); assert seen['class_name']=='무직' and seen['race_name']=='없음'
    # Emergency reconnect before choosing a fate must still return to onboarding.
    rc=c.post(f'/api/rooms/{room}/members/{j["member_id"]}/reconnect-code',headers=gh).json()['reconnect_code']
    rr=c.post(f'/api/rooms/{room}/reconnect',json={'reconnect_code':rc}); assert rr.status_code==200,rr.text
    ph2={'Authorization':'Bearer '+rr.json()['player_token']}; rest=c.get(f'/api/rooms/{room}/state',headers=ph2).json(); assert rest['character']['state']['onboarding_complete'] is False
    # Invalid choices are refused, valid choice finalizes exactly once.
    bad=c.post(f'/api/rooms/{room}/characters/{cid}/onboarding',headers=ph2,json={'class_name':'마법사','race_name':'없는 종족'}); assert bad.status_code==400,bad.text
    done=c.post(f'/api/rooms/{room}/characters/{cid}/onboarding',headers=ph2,json={'class_name':'마법사','race_name':race}); assert done.status_code==200,done.text
    st=c.get(f'/api/rooms/{room}/state',headers=ph2).json(); assert st['character']['state']['onboarding_complete'] is True and st['character']['state']['class_name']=='마법사' and st['character']['state']['race_name']==race
    again=c.post(f'/api/rooms/{room}/characters/{cid}/onboarding',headers=ph2,json={'class_name':'마법사','race_name':race}); assert again.status_code==409,again.text
print('first-join onboarding ok')
