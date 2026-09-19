import os, sys, pathlib
root=pathlib.Path(__file__).resolve().parents[1]
db=root/'tests'/'resources.db'; db.unlink(missing_ok=True)
os.environ['DW_DB']=str(db); os.environ['DW_PORT']='8151'; sys.path.insert(0,str(root))
from fastapi.testclient import TestClient
import app
app.require_local_request=lambda request: None

with TestClient(app.app, client=("127.0.0.1",50000)) as c:
    cr=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'자원','password':''}); assert cr.status_code==200,cr.text
    room=cr.json()['room_code']; gh={'Authorization':'Bearer '+cr.json()['gm_token']}
    st=c.get(f'/api/rooms/{room}/state',headers=gh).json(); assert st['room']['rules']['reserve_max']==0
    # Expansion classes are an optional rule and default OFF for new campaigns.
    # This test explicitly enables them before exercising expansion resources.
    sx=c.put(f'/api/rooms/{room}/settings',headers=gh,json={'settings':{'expansions_enabled':True}}); assert sx.status_code==200,sx.text
    # global reserve: unlimited by default, then GM max clamps both future writes and existing values.
    j=c.post(f'/api/rooms/{room}/join',json={'display_name':'P','password':''}).json(); ph={'Authorization':'Bearer '+j['player_token']}; cid=j['character_id']
    ji=c.get(f'/api/rooms/{room}/join-info').json(); fighter=next(x for x in ji['classes'] if x['name']=='전사'); race=fighter['races'][0]
    assert c.post(f'/api/rooms/{room}/characters/{cid}/onboarding',headers=ph,json={'class_name':'전사','race_name':race}).status_code==200
    assert c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'reserve':17}}).status_code==200
    st=c.get(f'/api/rooms/{room}/state',headers=ph).json(); assert st['character']['state']['reserve']==17
    rules=dict(st['room']['rules']); rules['reserve_max']=6
    assert c.put(f'/api/rooms/{room}/rules',headers=gh,json={'rules':rules}).status_code==200
    st=c.get(f'/api/rooms/{room}/state',headers=ph).json(); assert st['character']['state']['reserve']==6 and st['room']['rules']['reserve_max']==6
    assert c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'reserve':99}}).status_code==200
    assert c.get(f'/api/rooms/{room}/state',headers=ph).json()['character']['state']['reserve']==6

    # expansion personal resource is independent per accepted grant.
    data={'legend_move':{'name':'문을 연 자','desc':'테스트'},'class_moves':[], 'resource':{'name':'별빛','max':5}, 'hidden':False,'sort_order':9999,'theme':{'page_background':'#f2f0e8','background':'#ffffff','text':'#181818','accent':'#181818'}}
    x=c.post(f'/api/rooms/{room}/expansions',headers=gh,json={'name':'별의 길','gm_condition':'','public_intro':'','data':data}); assert x.status_code==200,x.text
    eid=x.json()['id']
    g=c.post(f'/api/rooms/{room}/expansions/{eid}/grant',headers=gh,json={'character_id':cid,'visible_to_party':False,'message':''}); assert g.status_code==200,g.text
    gid=g.json()['grant_id']
    assert c.post(f'/api/rooms/{room}/grants/{gid}/respond',headers=ph,json={'accept':True}).status_code==200
    state=c.get(f'/api/rooms/{room}/state',headers=ph).json(); ext=next(x for x in state['party'] if x['character_id']==cid)['extensions'][0]
    assert ext['data']['resource']=={'name':'별빛','max':5}
    patch={'extension_state':{str(gid):{'legend_owned':False,'class_moves_owned':[],'resource_current':4}}}
    assert c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':patch}).status_code==200
    assert c.get(f'/api/rooms/{room}/state',headers=ph).json()['character']['state']['extension_state'][str(gid)]['resource_current']==4
    # player cannot exceed expansion max
    patch['extension_state'][str(gid)]['resource_current']=99
    assert c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':patch}).status_code==200
    assert c.get(f'/api/rooms/{room}/state',headers=ph).json()['character']['state']['extension_state'][str(gid)]['resource_current']==5
    # lowering the expansion max clamps accepted holders immediately
    data['resource']['max']=2
    x=c.put(f'/api/rooms/{room}/expansions/{eid}',headers=gh,json={'name':'별의 길','gm_condition':'','public_intro':'','data':data}); assert x.status_code==200,x.text
    assert c.get(f'/api/rooms/{room}/state',headers=ph).json()['character']['state']['extension_state'][str(gid)]['resource_current']==2

print('reserve and expansion resource tests ok')
