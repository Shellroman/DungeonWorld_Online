import os,sys,pathlib
root=pathlib.Path(__file__).resolve().parents[1]; td=root/'tests'; db=td/'edge_fixed.db'; db.unlink(missing_ok=True)
os.environ['DW_DB']=str(db);sys.path.insert(0,str(root))
from fastapi.testclient import TestClient
import app
app.require_local_request=lambda request: None
with TestClient(app.app, client=("127.0.0.1", 50000)) as c:
    cr=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'X','password':''}).json(); room=cr['room_code']; h={'Authorization':'Bearer '+cr['gm_token']}
    ji=c.get(f'/api/rooms/{room}/join-info').json(); warrior=next(x for x in ji['classes'] if x['name']=='전사'); race=warrior['races'][0]
    jp=c.post(f'/api/rooms/{room}/join',json={'display_name':'P','password':''}).json(); ph={'Authorization':'Bearer '+jp['player_token']}; cid=jp['character_id']; assert c.post(f'/api/rooms/{room}/characters/{cid}/onboarding',headers=ph,json={'class_name':'전사','race_name':race}).status_code==200
    # initialize CON 13
    c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'stats':{'str':16,'dex':15,'con':13,'int':12,'wis':9,'cha':8}}})
    before=c.get(f'/api/rooms/{room}/state',headers=ph).json(); hp0=before['character']['state']['hp_current']; max0=before['party'][0]['hp_max']
    gs=c.get(f'/api/rooms/{room}/state',headers=h).json(); cd=gs['classes']['전사']; oldhp=cd['hp']; cd2=dict(cd); cd2['hp']=oldhp+3
    r=c.put(f'/api/rooms/{room}/classes',headers=h,json={'name':'전사','data':cd2}); assert r.status_code==200,r.text
    after=c.get(f'/api/rooms/{room}/state',headers=ph).json(); hp1=after['character']['state']['hp_current']; max1=after['party'][0]['hp_max']; assert hp1==hp0+3 and max1==max0+3,(hp0,hp1,max0,max1)
    # Optional expansion pack is imported explicitly; startup must not re-inject renamed examples.
    raw=(root/'dwpack'/'UnlimitedDungeons_DistantShore_Expansions.dwpack').read_bytes()
    pv=c.post(f'/api/rooms/{room}/dwpack/preview',headers=h,files={'file':('optional.dwpack',raw,'application/octet-stream')}); assert pv.status_code==200,pv.text
    im=c.post(f'/api/rooms/{room}/dwpack/import',headers=h,json={'preview_token':pv.json()['preview_token'],'conflict_mode':'keep','apply_rules':False}); assert im.status_code==200,im.text
    gs=c.get(f'/api/rooms/{room}/state',headers=h).json(); e=gs['expansions'][0]; orig=e['name']; new=orig+' X'
    r=c.put(f'/api/rooms/{room}/expansions/{e["id"]}',headers=h,json={'name':new,'gm_condition':e['gm_condition'],'public_intro':e['public_intro'],'data':e['data']});assert r.status_code==200,r.text
    app.init_db(); gs2=c.get(f'/api/rooms/{room}/state',headers=h).json(); names=[x['name'] for x in gs2['expansions']]
    assert new in names and orig not in names and len(names)==11,(orig,new,len(names),names)
    # local GM resume must not invalidate original GM token
    rr=c.post(f'/api/local/campaigns/{room}/resume'); assert rr.status_code==200,rr.text; h2={'Authorization':'Bearer '+rr.json()['gm_token']}
    assert c.get(f'/api/rooms/{room}/state',headers=h2).status_code==200
    assert c.get(f'/api/rooms/{room}/state',headers=h).status_code==200
print('edge fixes ok')
