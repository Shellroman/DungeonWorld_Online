import json, os, pathlib, sys
root=pathlib.Path(__file__).resolve().parents[1]
db=root/'tests'/'regression_names.db'; db.unlink(missing_ok=True)
os.environ['DW_DB']=str(db); os.environ['DW_PORT']='8142'; sys.path.insert(0,str(root))
import app
app.init_db()
with app.db() as con:
    now=app.now_iso()
    cur=con.execute("INSERT INTO rooms(code,campaign_name,gm_name,gm_token_hash,rules_json,password_hash,settings_json,created_at,updated_at,default_data_initialized,default_data_revision) VALUES(?,?,?,?,?,?,?,?,?,1,'1.0.0')",('N41001','x','GM',app.hash_token('g'),'{}','','{}',now,now))
    rid=int(cur.lastrowid)
    old={'name':'목석의 말(돌)','level':'암송','desc':app.DWARF_STONE_SPEECH_DESC}
    cur=con.execute("INSERT INTO spell_defs(room_id,class_name,name,level,data_json) VALUES(?,?,?,?,?)",(rid,'__undefined__','목석의 말(돌)','암송',app.jdump(old)))
    sid=int(cur.lastrowid)
    race={'name':'드워프','description':'','per_class':{'사제':'돌에 대해서만 쓸 수 있는 목석의 말이 암송주문으로서 추가됩니다.'},'enabled_classes':['사제'],'spell_effects':{'사제':[{'kind':'grant_unclassified','spell_id':sid}]}}
    con.execute("INSERT INTO race_defs(room_id,name,data_json,sort_order) VALUES(?,?,?,1)",(rid,'드워프',app.jdump(race)))
    app._set_schema_version(con,12)
app.init_db()
with app.db() as con:
    assert app._schema_version(con)==app.SCHEMA_VERSION
    sp=con.execute("SELECT id,name,level,data_json FROM spell_defs WHERE room_id=? AND class_name='__undefined__'",(rid,)).fetchone()
    assert sp['name']=='목석의 말 · 돌' and sp['level']=='암송'
    assert json.loads(sp['data_json'])['desc']==app.DWARF_STONE_SPEECH_DESC
    race=json.loads(con.execute("SELECT data_json FROM race_defs WHERE room_id=? AND name='드워프'",(rid,)).fetchone()['data_json'])
    assert any(int(x.get('spell_id',0))==int(sp['id']) for x in race['spell_effects']['사제'])
seed=app.seed_payload()
assert any(x.get('name')=='목석의 말 · 돌' for x in seed['spells']['__undefined__'])
assert not any(x.get('name')=='목석의 말(돌)' for x in seed['spells']['__undefined__'])
js=(root/'static'/'app.js').read_text(encoding='utf-8')
assert '<span>개인 자원</span><b>${esc(resourceName)}</b>' not in js
assert "recordEsc(resourceName,builtin)" in js and "extension-resource-box" in js
print('naming regression ok')
db.unlink(missing_ok=True)
