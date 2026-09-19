import os, sys, pathlib
root=pathlib.Path(__file__).resolve().parents[1]
db=root/'tests'/'regression_runtime_bugfix.db'; db.unlink(missing_ok=True)
os.environ['DW_DB']=str(db); os.environ['DW_PORT']='8191'; sys.path.insert(0,str(root))
from fastapi.testclient import TestClient
import app

js=(root/'static'/'app.js').read_text(encoding='utf-8')
results=[]
def ok(name, cond, detail=''):
    results.append((name,bool(cond),detail))
    if not cond: print('FAIL',name,detail)

# Inventory add must create a client-side draft first. Saving an entirely empty
# row immediately makes the server normalizer drop it and the row appears not to add.
ok('inventory_draft_row',"row.dataset.inventoryDraft='1'" in js and 'data-inventory-draft' in js)
ok('inventory_add_not_immediate_save',"$('#addInventoryItem')?.addEventListener('click',()=>{clearTimeout(timer);" in js and "list.insertAdjacentHTML('beforeend',inventoryItemRow(blank,index))" in js)
ok('inventory_draft_focus',"$('[data-inv=\"name\"]',row)?.focus()" in js)

# Zero is a valid class load and must not render back as the default 8.
ok('class_zero_load_visible','Number.isFinite(Number(c.load))?Number(c.load):8' in js)

# XP base 0 is explicitly allowed by the rules UI and must stay 0 end-to-end.
ok('xp_base_zero_normalize',app.normalize_rules({'xp_base':0})['xp_base']==0,str(app.normalize_rules({'xp_base':0})))
ok('xp_base_zero_required',app.xp_required(1,{'xp_base':0})==1,str(app.xp_required(1,{'xp_base':0})))
ok('xp_client_zero_fallback','Number.isFinite(rawBase)?rawBase:7' in js)

# GM sound volume 0 is a real value (mute), not a missing/default value.
ok('sound_client_zero_helper','function soundSliderVolume' in js and "Number.isFinite(raw)?raw:fallback" in js)

with TestClient(app.app, client=('127.0.0.1',50200)) as c:
    cr=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'BugAudit','password':''})
    ok('create_room',cr.status_code==200,cr.text)
    room=cr.json()['room_code']; hdr={'Authorization':'Bearer '+cr.json()['gm_token']}
    r=c.put(f'/api/rooms/{room}/rules',headers=hdr,json={'rules':{'xp_base':0}})
    st=c.get(f'/api/rooms/{room}/state',headers=hdr).json()
    ok('xp_base_zero_api',r.status_code==200 and st['room']['rules']['xp_base']==0,str(st['room']['rules']))
    r=c.put(f'/api/rooms/{room}/classes',headers=hdr,json={'name':'ZeroLoad','data':{'hp':6,'damage':'D6','load':0,'alignments':[],'bonds':[],'start':[],'a25':[],'a610':[],'gear':''}})
    st=c.get(f'/api/rooms/{room}/state',headers=hdr).json()
    ok('class_zero_load_api',r.status_code==200 and st['classes']['ZeroLoad']['load']==0,str(st['classes'].get('ZeroLoad')))
    with app.db() as con:
        rid=con.execute('SELECT id FROM rooms WHERE code=?',(room,)).fetchone()['id']
        bgm=con.execute("INSERT INTO sound_defs(room_id,name,kind,source_type,source,sort_order,created_at) VALUES(?,?,?,?,?,?,?)",(rid,'B','bgm','file','/media/test-b.mp3',1,app.now_iso())).lastrowid
        sfx=con.execute("INSERT INTO sound_defs(room_id,name,kind,source_type,source,sort_order,created_at) VALUES(?,?,?,?,?,?,?)",(rid,'S','sfx','file','/media/test-s.wav',1,app.now_iso())).lastrowid
    r=c.post(f'/api/rooms/{room}/sounds/volume',headers=hdr,json={'kind':'bgm','volume':0})
    ok('bgm_zero_set',r.status_code==200 and r.json()['bgm_volume']==0,r.text)
    r=c.post(f'/api/rooms/{room}/sounds/volume',headers=hdr,json={'kind':'sfx','volume':0})
    ok('sfx_zero_set',r.status_code==200 and r.json()['sfx_volume']==0,r.text)
    r=c.post(f'/api/rooms/{room}/sounds/play',headers=hdr,json={'sound_id':bgm,'position':0,'volume':0})
    state=r.json().get('state',{})
    ok('bgm_play_zero_kept',r.status_code==200 and state.get('bgm_volume')==0 and state.get('sfx_volume')==0,r.text)
    r=c.post(f'/api/rooms/{room}/sounds/stop',headers=hdr)
    state=r.json().get('state',{})
    ok('sound_stop_zero_kept',r.status_code==200 and state.get('bgm_volume')==0 and state.get('sfx_volume')==0,r.text)
    r=c.post(f'/api/rooms/{room}/sounds/play',headers=hdr,json={'sound_id':sfx,'position':0,'volume':0})
    st=c.get(f'/api/rooms/{room}/state',headers=hdr).json()['sound_state']
    ok('sfx_play_keeps_bgm_zero',r.status_code==200 and st.get('bgm_volume')==0 and st.get('sfx_volume')==0,str(st))

print('\nSUMMARY')
for n,c,d in results: print(('PASS' if c else 'FAIL'),n,d if not c else '')
print('passed',sum(c for _,c,_ in results),'/',len(results))
if not all(c for _,c,_ in results): raise SystemExit(1)
