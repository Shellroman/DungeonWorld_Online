import json, os, pathlib, sys
root=pathlib.Path(__file__).resolve().parents[1]
db=root/'tests'/'dwarf_stone_migration.db'; db.unlink(missing_ok=True)
os.environ['DW_DB']=str(db); os.environ['DW_PORT']='8141'; sys.path.insert(0,str(root))
import app
app.init_db()
# Build a tiny schema-11-style campaign with the known legacy interpretation.
with app.db() as con:
    now=app.now_iso()
    cur=con.execute("INSERT INTO rooms(code,campaign_name,gm_name,gm_token_hash,rules_json,password_hash,settings_json,created_at,updated_at,default_data_initialized,default_data_revision) VALUES(?,?,?,?,?,?,?,?,?,1,'1.0.0')",('STONE1','x','GM',app.hash_token('g'),'{}','','{}',now,now))
    rid=int(cur.lastrowid)
    cleric={'hp':8,'damage':'D6','load':10,'races':[],'alignments':[],'bonds':[],'start':[],'a25':[],'a610':[],'gear':''}
    con.execute("INSERT INTO class_defs(room_id,name,data_json,sort_order) VALUES(?,?,?,1)",(rid,'사제',app.jdump(cleric)))
    spell={'name':'목석의 말','level':5,'desc':'기존 원본'}
    cur=con.execute("INSERT INTO spell_defs(room_id,class_name,name,level,data_json) VALUES(?,?,?,?,?)",(rid,'사제','목석의 말','5',app.jdump(spell)))
    sid=int(cur.lastrowid)
    race={'name':'드워프','description':'','per_class':{'사제':'드워프 사제는 돌에 매우 친숙합니다. 돌에 대해서만 쓸 수 있는 목석의 말이 암송주문으로서 추가됩니다.'},'enabled_classes':['사제'],'spell_effects':{'사제':[{'kind':'level_reduce','spell_id':sid,'amount':5}]}}
    con.execute("INSERT INTO race_defs(room_id,name,data_json,sort_order) VALUES(?,?,?,1)",(rid,'드워프',app.jdump(race)))
    app._set_schema_version(con,11)
app.init_db()
with app.db() as con:
    assert app._schema_version(con)==app.SCHEMA_VERSION
    sp=con.execute("SELECT id,level,data_json FROM spell_defs WHERE room_id=? AND class_name='__undefined__' AND name='목석의 말 · 돌'",(rid,)).fetchone(); assert sp
    assert sp['level']=='암송'
    data=json.loads(sp['data_json']); assert data['desc']==app.DWARF_STONE_SPEECH_DESC
    race=json.loads(con.execute("SELECT data_json FROM race_defs WHERE room_id=? AND name='드워프'",(rid,)).fetchone()['data_json'])
    rows=race['spell_effects']['사제']
    assert any(x['kind']=='grant_unclassified' and int(x['spell_id'])==int(sp['id']) for x in rows)
    assert not any(x['kind']=='level_reduce' and int(x.get('spell_id',0))==sid for x in rows)
print('dwarf stone speech migration ok')
db.unlink(missing_ok=True)
