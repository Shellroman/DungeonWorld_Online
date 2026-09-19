import os, sys, pathlib
root=pathlib.Path(__file__).resolve().parents[1]
db=root/'tests'/'advanced_requirements.db'; db.unlink(missing_ok=True)
os.environ['DW_DB']=str(db); os.environ['DW_PORT']='8137'; sys.path.insert(0,str(root))
from fastapi.testclient import TestClient
import app
app.require_local_request=lambda request: None

with TestClient(app.app, client=('127.0.0.1',50000)) as c:
    cr=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'REQ','password':''}); assert cr.status_code==200,cr.text
    room=cr.json()['room_code']; gh={'Authorization':'Bearer '+cr.json()['gm_token']}
    ji=c.get(f'/api/rooms/{room}/join-info').json(); wizard=next(x for x in ji['classes'] if x['name']=='마법사'); race=wizard['races'][0]
    p=c.post(f'/api/rooms/{room}/join',json={'display_name':'P','password':''}).json(); ph={'Authorization':'Bearer '+p['player_token']}
    x=c.post(f'/api/rooms/{room}/characters/{p["character_id"]}/onboarding',headers=ph,json={'class_name':'마법사','race_name':race}); assert x.status_code==200,x.text
    x=c.patch(f'/api/rooms/{room}/characters/{p["character_id"]}',headers=gh,json={'patch':{'level':6}}); assert x.status_code==200,x.text

    state=c.get(f'/api/rooms/{room}/state',headers=ph).json(); cls=state['classes']['마법사']
    move=next(m for m in cls['a610'] if m['name']=='대가')
    assert move['has_requirement'] is True and move['requires_move']=='천재'
    assert move['desc'].startswith('필요: 천재.')

    # Cannot take a dependent move before its prerequisite.
    x=c.patch(f'/api/rooms/{room}/characters/{p["character_id"]}',headers=ph,json={'patch':{'advanced_moves':['대가']}})
    assert x.status_code==400 and '천재' in x.text, x.text

    # Once the prerequisite is owned, the dependent move is legal.
    x=c.patch(f'/api/rooms/{room}/characters/{p["character_id"]}',headers=ph,json={'patch':{'advanced_moves':['천재','대가']}})
    assert x.status_code==200,x.text

    # Removing the prerequisite while retaining the dependent move is blocked.
    x=c.patch(f'/api/rooms/{room}/characters/{p["character_id"]}',headers=ph,json={'patch':{'advanced_moves':['대가']}})
    assert x.status_code==400 and '천재' in x.text, x.text

    # Explicitly disabling a condition wins over legacy text inference; description stays untouched.
    current=c.get(f'/api/rooms/{room}/state',headers=gh).json()['classes']['마법사']
    edited=dict(current)
    edited['races']=[]
    for m in edited['a610']:
        if m['name']=='대가':
            old_desc=m['desc']; m['has_requirement']=False; m['requires_move']=''
    x=c.put(f'/api/rooms/{room}/classes',headers=gh,json={'name':'마법사','old_name':'마법사','data':edited}); assert x.status_code==200,x.text
    after=c.get(f'/api/rooms/{room}/state',headers=gh).json()['classes']['마법사']
    move=next(m for m in after['a610'] if m['name']=='대가')
    assert move['has_requirement'] is False and move['requires_move']=='' and move['desc']==old_desc

print('advanced move requirement tests ok')
