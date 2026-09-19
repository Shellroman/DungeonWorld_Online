import os, sys, pathlib, json
root=pathlib.Path(__file__).resolve().parents[1]
tmp=root/'tests'/'regression_convenience_data'; tmp.mkdir(parents=True,exist_ok=True)
db=tmp/'test.db'
if db.exists(): db.unlink()
os.environ['DW_DB']=str(db)
os.environ['DW_PORT']='8139'
sys.path.insert(0,str(root))
from fastapi.testclient import TestClient
import app

results=[]
def ok(name, cond, detail=''):
    results.append((name,bool(cond),detail))
    if not cond: print('FAIL',name,detail)

with TestClient(app.app, client=("127.0.0.1", 50100)) as c:
    r=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'편의성','password':''})
    room=r.json()['room_code']; gm=r.json()['gm_token']; hdr={'Authorization':'Bearer '+gm}
    state=c.get(f'/api/rooms/{room}/state',headers=hdr).json()
    cls=next(iter(state['classes']))

    def save(name, level):
        return c.put(f'/api/rooms/{room}/spell',headers=hdr,json={'class_name':cls,'name':name,'level':level,'desc':'test'})

    for level in (1,10,'1','10'):
        r=save('숫자'+str(level),level); ok('numeric_'+str(level),r.status_code==200,r.text)
    for level in ('암송','간편','축복'):
        r=save('문자'+level,level); ok('text_'+level,r.status_code==200,r.text)
    for level in (0,11,-1,'0','11','1.5'):
        r=save('거부'+str(level),level); ok('reject_'+str(level),r.status_code==400,r.text)

    st=c.get(f'/api/rooms/{room}/state',headers=hdr).json()
    rows=st['spells'][cls]
    byname={x['name']:x for x in rows}
    ok('canonical_numeric',byname.get('숫자1',{}).get('level')=='1',json.dumps(byname.get('숫자1'),ensure_ascii=False))
    ok('text_preserved',byname.get('문자암송',{}).get('level')=='암송',json.dumps(byname.get('문자암송'),ensure_ascii=False))

js=(root/'static'/'app.js').read_text(encoding='utf-8')
css=(root/'static'/'styles.css').read_text(encoding='utf-8')
ok('workspace_updates_all_z', 'normalizeWorkspaceZ(layout);syncWindowZ();saveWorkspace' in js)
ok('workspace_touch_listener', "el.addEventListener('pointerdown',()=>bring(w,el),{capture:true})" in js)
ok('extension_owner_label', 'rawEsc(ownerName)' in js and '본인 + GM 전용' not in js)
ok('extension_condition_label', 'GM 전용 해금 조건' not in js)
ok('spell_text_level_zero', 'spellEffectiveLevel(level)' in js and '숫자 1~10 = 해당 레벨 · 문자는 0레벨 분류' in js)
ok('compact_alignment', '.rules-compact-grid{align-items:start!important}' in css and '.exp-resource-editor{align-items:start!important}' in css)

print('\nSUMMARY')
for n,c,d in results: print(('PASS' if c else 'FAIL'),n,d if not c else '')
print('passed',sum(c for _,c,_ in results),'/',len(results))
if not all(c for _,c,_ in results): raise SystemExit(1)
