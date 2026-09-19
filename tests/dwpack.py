import os,sys,pathlib,zipfile,io,json
root=pathlib.Path(__file__).resolve().parents[1]
tmp=root/'tests'/'dwpack_data'; tmp.mkdir(parents=True,exist_ok=True)
db=tmp/'test.db'
if db.exists(): db.unlink()
os.environ['DW_DB']=str(db); os.environ['DW_PORT']='8140'
sys.path.insert(0,str(root))
from fastapi.testclient import TestClient
import app
results=[]
def ok(name,cond,detail=''):
    results.append((name,bool(cond),detail))
    if not cond: print('FAIL',name,detail)

with TestClient(app.app,client=('127.0.0.1',50000)) as c:
    r=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'원본팩','password':''}); ok('create_source',r.status_code==200,r.text); room=r.json()['room_code']; gm=r.json()['gm_token']; h={'Authorization':'Bearer '+gm}
    # Add one custom class/spell/race relation so portable spell UID conversion is exercised.
    cls={'name':'팩직업','data':{'hp':7,'damage':'D6','load':9,'start':[],'a25':[],'a610':[],'multiclass_25':False,'multiclass_610':False}}
    ok('custom_class',c.put(f'/api/rooms/{room}/classes',headers=h,json=cls).status_code==200)
    sr=c.put(f'/api/rooms/{room}/spell',headers=h,json={'class_name':'팩직업','name':'팩주문','level':1,'desc':'팩 주문 설명'}); ok('custom_spell',sr.status_code==200,sr.text); sid=sr.json().get('id')
    # state route returns spell ids; use current spell id from state if endpoint body does not.
    st=c.get(f'/api/rooms/{room}/state',headers=h).json(); sid=next(x['id'] for x in st['spells']['팩직업'] if x['name']=='팩주문')
    race={'name':'팩종족','data':{'name':'팩종족','description':'','per_class':{'팩직업':'테스트'},'enabled_classes':['팩직업'],'spell_effects':{'팩직업':[{'kind':'level_reduce','spell_id':sid,'amount':1}]}}}
    ok('custom_race',c.put(f'/api/rooms/{room}/races',headers=h,json=race).status_code==200)
    ex=c.get(f'/api/rooms/{room}/dwpack/export?include_npcs=true&include_rules=true',headers=h); ok('export_status',ex.status_code==200,ex.text[:200] if ex.status_code!=200 else '')
    raw=ex.content; ok('export_zip',raw[:2]==b'PK',str(raw[:4]));
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=set(z.namelist()); ok('manifest_files','manifest.json' in names and 'data/classes.json' in names and 'data/races.json' in names and 'data/spells.json' in names,str(sorted(names)))
        races=json.loads(z.read('data/races.json')); pr=next(x for x in races if x['name']=='팩종족'); eff=pr['data']['spell_effects']['팩직업'][0]; ok('portable_spell_uid','spell_uid' in eff and 'spell_id' not in eff,json.dumps(eff,ensure_ascii=False))
    # New empty-ish campaign then import. Delete defaults first so import is easy to count.
    r2=c.post('/api/rooms',json={'gm_name':'GM2','campaign_name':'대상팩','password':''}); room2=r2.json()['room_code']; gm2=r2.json()['gm_token']; h2={'Authorization':'Bearer '+gm2}
    # preview from exported bytes
    pv=c.post(f'/api/rooms/{room2}/dwpack/preview',headers=h2,files={'file':('test.dwpack',raw,'application/octet-stream')}); ok('preview',pv.status_code==200,pv.text[:300]); pj=pv.json(); ok('preview_counts',pj['counts']['classes']>=1 and pj['counts']['monsters']>=1,str(pj.get('counts')))
    imp=c.post(f'/api/rooms/{room2}/dwpack/import',headers=h2,json={'preview_token':pj['preview_token'],'conflict_mode':'replace','apply_rules':True}); ok('import_replace',imp.status_code==200,imp.text[:500])
    st2=c.get(f'/api/rooms/{room2}/state',headers=h2).json(); ok('import_custom_class','팩직업' in st2['classes']); ok('import_custom_race','팩종족' in st2['races']);
    imported_spell=next(x for x in st2['spells']['팩직업'] if x['name']=='팩주문'); imported_race=st2['races']['팩종족']; ok('race_ref_rebound',imported_race['spell_effects']['팩직업'][0]['spell_id']==imported_spell['id'],json.dumps(imported_race['spell_effects'],ensure_ascii=False))
    # Re-preview same pack and duplicate conflicts.
    pv2=c.post(f'/api/rooms/{room2}/dwpack/preview',headers=h2,files={'file':('test.dwpack',raw,'application/octet-stream')}); ok('preview_conflict',pv2.status_code==200 and pv2.json()['conflict_count']>0,pv2.text[:200]);
    imp2=c.post(f'/api/rooms/{room2}/dwpack/import',headers=h2,json={'preview_token':pv2.json()['preview_token'],'conflict_mode':'duplicate','apply_rules':False}); ok('import_duplicate',imp2.status_code==200,imp2.text[:400]);
    st3=c.get(f'/api/rooms/{room2}/state',headers=h2).json(); ok('duplicate_class',any(n.startswith('팩직업 (가져옴)') for n in st3['classes']),str(list(st3['classes'])[-5:]))
    # Example pack and reference download must work.
    ref=c.get('/api/dwpack/reference'); ok('reference_download',ref.status_code==200 and ref.content[:2]==b'PK',str(ref.status_code))
    exraw=(root/'dwpack'/'reference'/'example'/'DungeonWorld_Example.dwpack').read_bytes(); pve=c.post(f'/api/rooms/{room2}/dwpack/preview',headers=h2,files={'file':('example.dwpack',exraw,'application/octet-stream')}); ok('example_pack_valid',pve.status_code==200,pve.text[:400])
    # Exact sync on a player-free campaign should reproduce the included content set.
    r3=c.post('/api/rooms',json={'gm_name':'GM3','campaign_name':'동기화대상','password':''}); room3=r3.json()['room_code']; h3={'Authorization':'Bearer '+r3.json()['gm_token']}
    pv3=c.post(f'/api/rooms/{room3}/dwpack/preview',headers=h3,files={'file':('example.dwpack',exraw,'application/octet-stream')}); ok('sync_preview',pv3.status_code==200,pv3.text[:300])
    im3=c.post(f'/api/rooms/{room3}/dwpack/import',headers=h3,json={'preview_token':pv3.json()['preview_token'],'conflict_mode':'sync','apply_rules':True}); ok('sync_import',im3.status_code==200,im3.text[:400])
    st4=c.get(f'/api/rooms/{room3}/state',headers=h3).json(); ok('sync_exact_counts',len(st4['classes'])==2 and sum(len(v) for v in st4['spells'].values())==2 and len(st4['races'])==1 and len(st4['expansions'])==1 and len(st4['monster_folders'])==1 and len(st4['monsters'])==1 and len(st4['npcs'])==1,(len(st4['classes']),sum(len(v) for v in st4['spells'].values()),len(st4['races']),len(st4['expansions']),len(st4['monster_folders']),len(st4['monsters']),len(st4['npcs'])))
    # Exact sync must be blocked once a player exists.
    j=c.post(f'/api/rooms/{room3}/join',json={'display_name':'P','password':''}); ok('sync_player_join',j.status_code==200,j.text)
    pv4=c.post(f'/api/rooms/{room3}/dwpack/preview',headers=h3,files={'file':('example.dwpack',exraw,'application/octet-stream')}); blocked=c.post(f'/api/rooms/{room3}/dwpack/import',headers=h3,json={'preview_token':pv4.json()['preview_token'],'conflict_mode':'sync','apply_rules':False}); ok('sync_block_live_campaign',blocked.status_code==400,blocked.text[:300])

print('\nSUMMARY')
for n,v,d in results: print(('PASS' if v else 'FAIL'),n,d if not v else '')
print('passed',sum(v for _,v,_ in results),'/',len(results))
if not all(v for _,v,_ in results): raise SystemExit(1)
