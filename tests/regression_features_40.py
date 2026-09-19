import json, os, pathlib, sys
root=pathlib.Path(__file__).resolve().parents[1]
db=root/'tests'/'regression_features_40.db'; db.unlink(missing_ok=True)
os.environ['DW_DB']=str(db); os.environ['DW_PORT']='8140'; sys.path.insert(0,str(root))
from fastapi.testclient import TestClient
import app
app.require_local_request=lambda request: None

with TestClient(app.app, client=("127.0.0.1",50000)) as c:
    cr=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'B40','password':''}); assert cr.status_code==200,cr.text
    room=cr.json()['room_code']; gh={'Authorization':'Bearer '+cr.json()['gm_token']}
    state=c.get(f'/api/rooms/{room}/state',headers=gh).json()
    assert state['room']['default_data_initialized'] is True
    assert state['room']['default_data_revision']=='1.0.0'

    # Known text-only racial rules are now explicit metadata, descriptions remain unchanged.
    elf=state['races']['엘프']; wiz_effects=elf.get('spell_effects',{}).get('마법사',[])
    detect=next(x for x in state['spells']['마법사'] if x['name']=='마법 탐지')
    assert any(x['kind']=='level_reduce' and x['spell_id']==detect['id'] and x['amount']==1 for x in wiz_effects)
    assert '마법 탐지가 간편주문이 됩니다.' in elf['per_class']['마법사']
    dwarf=state['races']['드워프']; cleric_effects=dwarf.get('spell_effects',{}).get('사제',[])
    stone_only=next(x for x in state['spells']['__undefined__'] if x['name']=='목석의 말 · 돌')
    assert stone_only['level']=='암송'
    assert stone_only['desc']=='돌을 만지며 이 주문을 걸면 그 안의 영들과 대화할 수 있습니다. 사제는 대상 물체에게 질문을 세 가지 할 수 있습니다. 돌은 이에 능력껏 대답할 것입니다.'
    assert any(x['kind']=='grant_unclassified' and x['spell_id']==stone_only['id'] for x in cleric_effects)
    assert not any(x['kind']=='level_reduce' for x in cleric_effects)
    assert '목석의 말이 암송주문으로서 추가됩니다.' in dwarf['per_class']['사제']

    # A GM-created unclassified spell can be wired into an arbitrary race/class auto-grant effect.
    x=c.put(f'/api/rooms/{room}/spell',headers=gh,json={'class_name':'__undefined__','name':'별의 축복','level':'축복','desc':'테스트용'}); assert x.status_code==200,x.text
    state=c.get(f'/api/rooms/{room}/state',headers=gh).json(); special=next(x for x in state['spells']['__undefined__'] if x['name']=='별의 축복')
    human=state['races']['인간']
    data=dict(human); effects=dict(data.get('spell_effects') or {}); rows=list(effects.get('전사') or [])
    rows.append({'kind':'grant_unclassified','spell_id':special['id']}); effects['전사']=rows; data['spell_effects']=effects
    x=c.put(f'/api/rooms/{room}/races',headers=gh,json={'name':'인간','old_name':'인간','data':data}); assert x.status_code==200,x.text
    state=c.get(f'/api/rooms/{room}/state',headers=gh).json(); assert any(x['spell_id']==special['id'] and x['kind']=='grant_unclassified' for x in state['races']['인간']['spell_effects']['전사'])

    # Deleting a spell also removes race-effect references to that definition.
    x=c.delete(f'/api/rooms/{room}/spell/{special["id"]}',headers=gh); assert x.status_code==200,x.text
    state=c.get(f'/api/rooms/{room}/state',headers=gh).json(); assert not any(x.get('spell_id')==special['id'] for rows in state['races']['인간'].get('spell_effects',{}).values() for x in rows)

    # Once a campaign exists, deleting every bundled definition is an intentional permanent state.
    with app.db() as con:
        rid=int(con.execute('SELECT id FROM rooms WHERE code=?',(room,)).fetchone()['id'])
        for table in ('monster_catalog','monster_defs','monster_folders','expansion_grants','expansion_defs','race_defs','spell_defs','core_moves','class_defs'):
            con.execute(f'DELETE FROM {table} WHERE room_id=?',(rid,))
    app.init_db()
    with app.db() as con:
        for table in ('monster_defs','monster_folders','expansion_defs','race_defs','spell_defs','core_moves','class_defs'):
            n=int(con.execute(f'SELECT COUNT(*) n FROM {table} WHERE room_id=?',(rid,)).fetchone()['n'])
            assert n==0,(table,n)

    # Explicit core/default import restores only Dungeon World core categories. Optional expansion examples are a separate DWPack.
    x=c.post(f'/api/rooms/{room}/default-data/import',headers=gh,json={'kinds':['core','classes','races','spells','expansions','monsters']}); assert x.status_code==200,x.text
    added=x.json()['added']; assert all(added[k]>0 for k in ('core','classes','races','spells','monsters')),added
    assert 'expansions' not in added,added
    restored=c.get(f'/api/rooms/{room}/state',headers=gh).json(); assert len(restored['monsters'])==154 and len(restored['expansions'])==0 and '전사' in restored['classes'] and '엘프' in restored['races']

    # Import never overwrites an existing same-name GM definition.
    with app.db() as con:
        row=con.execute("SELECT id,data_json FROM class_defs WHERE room_id=? AND name='전사'",(rid,)).fetchone(); data=json.loads(row['data_json']); data['hp']=123; con.execute('UPDATE class_defs SET data_json=? WHERE id=?',(json.dumps(data,ensure_ascii=False),row['id']))
    x=c.post(f'/api/rooms/{room}/default-data/import',headers=gh,json={'kinds':['classes']}); assert x.status_code==200,x.text
    with app.db() as con:
        data=json.loads(con.execute("SELECT data_json FROM class_defs WHERE room_id=? AND name='전사'",(rid,)).fetchone()['data_json']); assert data['hp']==123

print('feature regression 4.0 lineage ok')
