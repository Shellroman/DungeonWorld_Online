import json, os, pathlib, sys, zipfile
root=pathlib.Path(__file__).resolve().parents[1]
db=root/'tests'/'move_effects_structured.db'; db.unlink(missing_ok=True)
os.environ['DW_DB']=str(db); os.environ['DW_PORT']='8182'; sys.path.insert(0,str(root))
from fastapi.testclient import TestClient
import app
app.require_local_request=lambda request: None

seed=json.loads((root/'data/seed_data.json').read_text(encoding='utf-8'))
js=(root/'static/app.js').read_text(encoding='utf-8')
app_py=(root/'app.py').read_text(encoding='utf-8')

# All persistent move effects discussed for the built-in classes are structured.
expected={
 '마법사': {'천재','대가','증보'},
 '사제': {'선택 받은 자','기름으로 바른 자','응급처치','상급 응급처치'},
 '성기사': {'신의 은혜'},
 '사냥꾼': {'황무지의 신','하프엘프','특별한 재주'},
 '드루이드': {'사냥꾼의 형제','숲사람의 자매'},
}
for cname,names in expected.items():
    c=seed['classes'][cname]
    got={m['name'] for sec in ('start','a25','a610') for m in c.get(sec,[]) if m.get('move_effects')}
    assert names <= got, (cname,names-got)

assert 'SCHEMA_VERSION = 20' in app_py
assert "if(source==='__undefined__')continue" in js  # ordinary choice pool excludes special/unclassified spells
assert 'spellPreviewHtml' in js and 'movePreviewHtml' in js
assert "${esc('추가됨')}" in js and 'added_source' in js
assert 'validate_move_choices' in app_py and '__undefined__' in app_py

# Korean and English core packs must both carry the move-effect metadata.
def load_classes(path):
    with zipfile.ZipFile(path) as z:
        return json.loads(z.read('data/classes.json'))
ko=load_classes(root/'dwpack/DungeonWorld_1E_Core.dwpack')
en=load_classes(root/'dwpack/DungeonWorld_1E_Core_EN.dwpack')
assert any(m.get('move_effects') for c in ko for sec in ('start','a25','a610') for m in c['data'].get(sec,[]))
assert any(m.get('move_effects') for c in en for sec in ('start','a25','a610') for m in c['data'].get(sec,[]))

with TestClient(app.app, client=('127.0.0.1',50082)) as c:
    cr=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'MoveEffects','password':''}); assert cr.status_code==200,cr.text
    room=cr.json()['room_code']; gh={'Authorization':'Bearer '+cr.json()['gm_token']}
    join=c.post(f'/api/rooms/{room}/join',json={'display_name':'Tester','password':''}); assert join.status_code==200,join.text
    cid=join.json()['character_id']; ph={'Authorization':'Bearer '+join.json()['player_token']}
    ji=c.get(f'/api/rooms/{room}/join-info').json(); wiz=next(x for x in ji['classes'] if x['name']=='마법사')
    race='인간' if '인간' in wiz['races'] else wiz['races'][0]
    r=c.post(f'/api/rooms/{room}/characters/{cid}/onboarding',headers=ph,json={'class_name':'마법사','race_name':race}); assert r.status_code==200,r.text
    state=c.get(f'/api/rooms/{room}/state',headers=gh).json()
    unclassified=(state['spells'].get('__undefined__') or [])
    assert unclassified, 'special spell pool should exist for GM direct grants'
    special_id=unclassified[0]['id']
    cleric=state['spells']['사제']; classified=next(sp for sp in cleric if str(sp.get('level','')).isdigit())
    wizard_numeric=next(sp for sp in state['spells']['마법사'] if str(sp.get('level','')).isdigit())

    # Racial cross-class spell selection also cannot be used to smuggle a special/unclassified spell.
    bad_extra=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'extra_spells':[
        {'kind':'race','spell_id':special_id,'name':unclassified[0]['name'],'source':'__undefined__','level':unclassified[0]['level'],'desc':unclassified[0].get('desc','')}
    ]}})
    assert bad_extra.status_code==400,bad_extra.text
    if race=='인간':
        valid_extra=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=ph,json={'patch':{'extra_spells':[
            {'kind':'race','spell_id':classified['id'],'name':'forged name','source':'사제','level':'99','desc':'forged'}
        ]}})
        assert valid_extra.status_code==200,valid_extra.text
        stx=c.get(f'/api/rooms/{room}/state',headers=ph).json()['character']['state']; ex=next(x for x in stx['extra_spells'] if x.get('kind')=='race')
        assert ex['name']==classified['name'] and str(ex['level'])==str(classified['level']) and ex['desc']==classified.get('desc','')

    # Move-based ordinary acquisition may never select an unclassified spell, even if a client forges the request.
    bad=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=gh,json={'patch':{
        'level':6,'advanced_moves':['증보'],'move_choices':{'wizard.expanded_spellbook.spell':{'spell_id':special_id,'acquired_at_level':6}}
    }})
    assert bad.status_code==400,bad.text

    # A classified spell from another class is valid for Expanded Spellbook.
    good=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=gh,json={'patch':{
        'level':6,'advanced_moves':['증보'],'move_choices':{'wizard.expanded_spellbook.spell':{'spell_id':classified['id'],'acquired_at_level':6}}
    }})
    assert good.status_code==200,good.text
    saved=c.get(f'/api/rooms/{room}/state',headers=gh).json()
    char=next(x for x in saved['characters'] if x['character_id']==cid)['state']
    assert char['move_choices']['wizard.expanded_spellbook.spell']['spell_id']==classified['id']

    # Paired level-reduction moves cannot select the same spell.
    dup=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=gh,json={'patch':{
        'advanced_moves':['천재','대가'],'move_choices':{
            'wizard.prodigy.spell':{'spell_id':wizard_numeric['id'],'acquired_at_level':2},
            'wizard.master.spell':{'spell_id':wizard_numeric['id'],'acquired_at_level':6},
        }
    }})
    assert dup.status_code==400,dup.text

    # Fixed-source cross-class move grants cannot be spoofed to another class.
    # GM switches the test character to Druid and selects the structured move.
    state=c.get(f'/api/rooms/{room}/state',headers=gh).json(); druid=state['classes']['드루이드']; druid_race=druid['races'][0]['name']
    # First set the class/race and level without an explicit move choice.
    sw=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=gh,json={'patch':{'class_name':'드루이드','race_name':druid_race,'level':6,'advanced_moves':['사냥꾼의 형제']}}); assert sw.status_code==200,sw.text
    badsrc=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=gh,json={'patch':{'move_choices':{
        'druid.hunters_brother.move':{'source_class':'마법사','move_name':state['classes']['마법사']['start'][0]['name'],'acquired_at_level':6}
    }}})
    assert badsrc.status_code==400,badsrc.text
    ranger_move=state['classes']['사냥꾼']['start'][0]['name']
    goodsrc=c.patch(f'/api/rooms/{room}/characters/{cid}',headers=gh,json={'patch':{'move_choices':{
        'druid.hunters_brother.move':{'source_class':'사냥꾼','move_name':ranger_move,'acquired_at_level':6}
    }}})
    assert goodsrc.status_code==200,goodsrc.text

# Schema 16 -> current migration restores metadata for matching built-in moves and
# initializes the move-choice container without overwriting prose.
with app.db() as con:
    app._set_schema_version(con,16)
    for row in con.execute('SELECT id,data_json FROM class_defs'):
        raw=json.loads(row['data_json'])
        for sec in ('start','a25','a610'):
            for mv in raw.get(sec,[]): mv.pop('move_effects',None)
        con.execute('UPDATE class_defs SET data_json=? WHERE id=?',(app.jdump(raw),row['id']))
    row=con.execute('SELECT id,state_json FROM characters LIMIT 1').fetchone(); raw=json.loads(row['state_json']); raw.pop('move_choices',None)
    con.execute('UPDATE characters SET state_json=? WHERE id=?',(app.jdump(raw),row['id']))
app.init_db()
with app.db() as con:
    assert app._schema_version(con)==20
    wiz=con.execute("SELECT data_json FROM class_defs WHERE name='마법사' LIMIT 1").fetchone(); data=json.loads(wiz['data_json'])
    prodigy=next(m for m in data['a25'] if m['name']=='천재'); assert prodigy.get('move_effects')
    st=json.loads(con.execute('SELECT state_json FROM characters LIMIT 1').fetchone()['state_json']); assert isinstance(st.get('move_choices'),dict)

print('structured move effects ok')
db.unlink(missing_ok=True)
