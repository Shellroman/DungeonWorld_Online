from __future__ import annotations
import json, os, pathlib, sys
root=pathlib.Path(__file__).resolve().parents[1]
db=root/'tests'/'regression_content_provenance.db'; db.unlink(missing_ok=True)
os.environ['DW_DB']=str(db); os.environ['DW_PORT']='8159'; sys.path.insert(0,str(root))
import app
app.init_db()
seed=app.seed_payload()
with app.db() as con:
    now=app.now_iso()
    cur=con.execute("INSERT INTO rooms(code,campaign_name,gm_name,gm_token_hash,rules_json,password_hash,settings_json,created_at,updated_at,default_data_initialized,default_data_revision) VALUES(?,?,?,?,?,?,?,?,?,1,'1.0.0')",('PRV001','x','GM',app.hash_token('g'),'{}','','{}',now,now))
    rid=int(cur.lastrowid)
    # One exact bundled class and one custom class whose name collides with a bundled spell.
    wiz=app.normalize_class_data(seed['classes']['마법사'])
    con.execute("INSERT INTO class_defs(room_id,name,data_json,sort_order) VALUES(?,?,?,1)",(rid,'마법사',app.jdump(wiz)))
    custom=app.normalize_class_data({'hp':6,'damage':'D6','load':8,'gear':'암흑','start':[{'name':'암흑','desc':'사용자 작성'}]})
    con.execute("INSERT INTO class_defs(room_id,name,data_json,sort_order) VALUES(?,?,?,2)",(rid,'암흑',app.jdump(custom)))
    # One exact core move and one custom core move that collides by text.
    core=seed['core'][0]
    con.execute("INSERT INTO core_moves(room_id,name,data_json) VALUES(?,?,?)",(rid,core['name'],app.jdump(core)))
    con.execute("INSERT INTO core_moves(room_id,name,data_json) VALUES(?,?,?)",(rid,'암흑',app.jdump({'name':'암흑','desc':'사용자 작성'})))
    # Exact spell + custom spell with a catalog-colliding name.
    sp=seed['spells']['마법사'][0]
    con.execute("INSERT INTO spell_defs(room_id,class_name,name,level,data_json) VALUES(?,?,?,?,?)",(rid,'마법사',sp['name'],str(sp['level']),app.jdump(sp)))
    con.execute("INSERT INTO spell_defs(room_id,class_name,name,level,data_json) VALUES(?,?,?,?,?)",(rid,'암흑','암흑','1',app.jdump({'name':'암흑','level':'1','desc':'사용자 작성'})))
    classes=app.class_map(con,rid); cores=app.core_move_list(con,rid); spells=app.spell_map(con,rid)
    assert classes['마법사']['_builtin'] is True
    assert classes['암흑']['_builtin'] is False
    assert next(x for x in cores if x['name']==core['name'])['_builtin'] is True
    assert next(x for x in cores if x['name']=='암흑')['_builtin'] is False
    assert next(x for x in spells['마법사'] if x['name']==sp['name'])['_builtin'] is True
    assert next(x for x in spells['암흑'] if x['name']=='암흑')['_builtin'] is False
js=(root/'static'/'app.js').read_text(encoding='utf-8')
assert "APP.i18nUiExact[core] ?? APP.i18nContentEn[core]" not in js
assert "APP.i18nUiExact[mid] ?? APP.i18nContentEn[mid]" not in js
assert "requestOptions.body=JSON.stringify(canonicalizeBuiltIn(JSON.parse(requestOptions.body)))" not in js
assert "el.value=APP.i18nContentEn[x]" not in js
assert 'restoreDisplayedBuiltIn' in js
assert 'recordEsc(resourceName,builtin)' in js
assert 'recordEsc(selected.name,builtin)' in js
assert 'recordEsc(sp.name,builtin)' in js
assert 'recordEsc(m.name,coreMoveIsBuiltin(m))' in js
assert "available=access.spells.filter" not in js or "const available=access.spells.filter" in js

# The UI catalog must stay separate from the core-content catalog. Otherwise a GM-authored
# value such as a custom resource/class named '암흑' is silently translated to 'Darkness'.
ui=json.loads((root/'static'/'i18n_ui_en.json').read_text(encoding='utf-8'))['exact']
builder=(root/'tools'/'build_i18n_ui_en.py').read_text(encoding='utf-8')
assert "for k,v in CONTENT.items()" not in builder
for text in ('암흑','마법사','인간','마법적','신성'):
    assert text not in ui, (text,ui.get(text))
assert ui.get('히든')=='Hidden'
assert 'function _hasCustomContentCollision' in js
assert 'data-raw-tag=' in js and 'data-tag-dirty=' in js
assert 'names.map(displayMonsterTag).join' in js
assert 'class="textarea no-i18n"' in js and 'rawEsc(target.value)' in js
print('content provenance regression: PASS')
db.unlink(missing_ok=True)
