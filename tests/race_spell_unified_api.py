import os, pathlib, sys
root=pathlib.Path(__file__).resolve().parents[1]
db=root/'tests'/'race_spell_unified_api.db'; db.unlink(missing_ok=True)
os.environ['DW_DB']=str(db); os.environ['DW_PORT']='8142'; sys.path.insert(0,str(root))
from fastapi.testclient import TestClient
import app
app.require_local_request=lambda request: None
with TestClient(app.app, client=('127.0.0.1',50000)) as c:
    cr=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'UNI','password':''}); assert cr.status_code==200,cr.text
    room=cr.json()['room_code']; h={'Authorization':'Bearer '+cr.json()['gm_token']}
    state=c.get(f'/api/rooms/{room}/state',headers=h).json()
    human=state['races']['인간']
    rows=human['spell_effects']['마법사']
    cross=next(x for x in rows if x['kind']=='cross_class_access')
    assert cross['source_class']=='사제' and cross['count']==1
    # Current state exposes only the canonical spell_effects representation.
    assert 'spell_access' not in human
    assert next(x for x in human['spell_effects']['마법사'] if x['kind']=='cross_class_access')['source_class']=='사제'
    data=dict(human)
    rows=[x for x in data['spell_effects']['마법사'] if x['kind']!='cross_class_access']
    rows.insert(0,{'enabled':True,'kind':'cross_class_access','source_class':'사제','count':2})
    data['spell_effects']['마법사']=rows
    r=c.put(f'/api/rooms/{room}/races',headers=h,json={'name':'인간','old_name':'인간','data':data}); assert r.status_code==200,r.text
    state=c.get(f'/api/rooms/{room}/state',headers=h).json(); human=state['races']['인간']
    cross=next(x for x in human['spell_effects']['마법사'] if x['kind']=='cross_class_access')
    assert cross['count']==2 and 'enabled' not in cross and 'spell_access' not in human
    # Older development data is still accepted, but disabled legacy rows disappear
    # instead of leaking an obsolete toggle back into current state.
    legacy=app.normalize_race_data({'per_class':{},'spell_access':{'마법사':{'enabled':True,'source_class':'사제','count':1}},'spell_effects':{'사제':[{'enabled':False,'kind':'cross_class_access','source_class':'마법사','count':1}]}})
    assert 'spell_access' not in legacy and legacy['spell_effects']['마법사'][0]['source_class']=='사제' and legacy['spell_effects']['사제']==[]
    assert all('enabled' not in e for rows in legacy['spell_effects'].values() for e in rows)
print('unified race spell API ok')
db.unlink(missing_ok=True)
