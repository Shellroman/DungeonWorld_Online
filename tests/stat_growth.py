import os,sys,pathlib
root=pathlib.Path(__file__).resolve().parents[1]; db=root/'tests/stat_growth.db'; db.unlink(missing_ok=True)
os.environ['DW_DB']=str(db);sys.path.insert(0,str(root))
from fastapi.testclient import TestClient
import app
with TestClient(app.app, client=("127.0.0.1", 50000)) as c:
    cr=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'S','password':''}).json(); room=cr['room_code']; gh={'Authorization':'Bearer '+cr['gm_token']}
    ji=c.get(f'/api/rooms/{room}/join-info').json(); cl=next(x for x in ji['classes'] if x['name']=='전사'); jp=c.post(f'/api/rooms/{room}/join',json={'display_name':'P','password':''}).json(); ph={'Authorization':'Bearer '+jp['player_token']}; cid=jp['character_id']; assert c.post(f'/api/rooms/{room}/characters/{cid}/onboarding',headers=ph,json={'class_name':'전사','race_name':cl['races'][0]}).status_code==200
    base={'str':16,'dex':15,'con':13,'int':12,'wis':9,'cha':8}
    assert c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'stats':base}}).status_code==200
    s=c.get(f'/api/rooms/{room}/state',headers=ph).json()['character']['state']; assert s['stat_growth_spent']==0,s
    # Level 1 has no growth point.
    n=dict(base);n['str']=17
    assert c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'stats':n}}).status_code==400
    # Level 2 grants one point, and it can be spent once.
    assert c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'level':2}}).status_code==200
    assert c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'stats':n}}).status_code==200
    s=c.get(f'/api/rooms/{room}/state',headers=ph).json()['character']['state']; assert s['stat_growth_spent']==1,s['stat_growth_spent']
    # No second point at level 2.
    n2=dict(n);n2['dex']=16
    assert c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'stats':n2}}).status_code==400
    # GM bonus points add to the same pool and cannot be negative.
    assert c.patch(f'/api/rooms/{room}/characters/{cid}',headers=gh,json={'patch':{'bonus_stat_points':1}}).status_code==200
    assert c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'stats':n2}}).status_code==200
    s=c.get(f'/api/rooms/{room}/state',headers=ph).json()['character']['state']; assert s['stat_growth_spent']==2,s['stat_growth_spent']
    assert c.patch(f'/api/rooms/{room}/characters/{cid}',headers=gh,json={'patch':{'bonus_stat_points':-5}}).status_code==200
    s=c.get(f'/api/rooms/{room}/state',headers=ph).json()['character']['state']; assert s['bonus_stat_points']==0,s['bonus_stat_points']
    # Campaign stat maximum is authoritative for GM and players.
    too_high=dict(n2);too_high['str']=19
    assert c.patch(f'/api/rooms/{room}/characters/{cid}',headers=gh,json={'patch':{'stats':too_high}}).status_code==400
print('stat growth ok')
