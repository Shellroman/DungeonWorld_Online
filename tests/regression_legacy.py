import io, json, os, pathlib, sys
from urllib.error import HTTPError

root = pathlib.Path(__file__).resolve().parents[1]
tmp = root / 'tests' / 'regression_legacy_data'
tmp.mkdir(parents=True, exist_ok=True)
db = tmp / 'test.db'
if db.exists(): db.unlink()
os.environ['DW_DB'] = str(db)
os.environ['DW_PORT'] = '8147'
sys.path.insert(0, str(root))
from fastapi.testclient import TestClient
import app

results=[]
def ok(name, cond, detail=''):
    results.append((name, bool(cond), detail))
    if not cond: print('FAIL', name, detail)

class FakeResponse:
    status = 200
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, n=-1): return json.dumps(self.payload, ensure_ascii=False).encode('utf-8')

with TestClient(app.app, client=('127.0.0.1', 50147)) as c:
    r1=c.post('/api/rooms',json={'gm_name':'GM1','campaign_name':'첫 캠페인','password':''});
    room1=r1.json()['room_code']; gm1=r1.json()['gm_token']
    r2=c.post('/api/rooms',json={'gm_name':'GM2','campaign_name':'둘째 캠페인','password':''});
    room2=r2.json()['room_code']; gm2=r2.json()['gm_token']
    ok('create_two_rooms', r1.status_code==200 and r2.status_code==200)
    x=c.get('/api/local/active-campaign').json()
    ok('newly_created_room_is_active', x.get('active') and x.get('room_code')==room2, str(x))
    c.delete('/api/local/active-campaign')
    x=c.get('/api/active-campaign').json()
    ok('server_can_be_ready_without_active_campaign', x.get('active') is False and x.get('room_code')=='', str(x))
    r=c.post(f'/api/local/active-campaign/{room1}')
    x=r.json()
    ok('select_exactly_one_active_campaign', r.status_code==200 and x.get('room_code')==room1 and x.get('campaign_name')=='첫 캠페인', str(x))
    # Local campaign list still stores both; online/discovery must use active-campaign instead of this list.
    xs=c.get('/api/local/campaigns').json()['campaigns']
    ok('stored_campaigns_remain_independent', len(xs)==2, str(xs))

    # Release builds expose file-backed audio only.
    ok('file_audio_only_server', "source_type='file'" in pathlib.Path(app.__file__).read_text(encoding='utf-8'))
    hdr={'Authorization':'Bearer '+gm1}
    r=c.post(f'/api/rooms/{room1}/sounds/stop',headers=hdr)
    ok('sound_stop_returns_cleared_state', r.status_code==200 and r.json().get('state',{}).get('sound_id') is None and r.json().get('state',{}).get('status')=='stopped', r.text)

js=(root/'static'/'app.js').read_text(encoding='utf-8')
css=(root/'static'/'styles.css').read_text(encoding='utf-8')
go=(root/'launcher'/'main.go').read_text(encoding='utf-8')
build=(root/'build_release.py').read_text(encoding='utf-8')

ok('release_brand_web', 'v{app_version}' in (root/'app.py').read_text(encoding='utf-8') and '${VERSION_LABEL} EXE' in js)
ok('release_brand_build', 'DISPLAY_VERSION = f"v{APP_VERSION}"' in build)
ok('launcher_active_campaign_probe', '/api/active-campaign' in go and '이 캠페인은 열려 있지 않습니다' in go)
ok('launcher_discovery_active_only', '/api/local/active-campaign' in go and 'localActiveCampaign' in go)
ok('launcher_dedupe_by_instance', 'identity := strings.TrimSpace(resp.Instance)' in go and 'key := identity + "|" + strings.ToUpper(c.Code)' in go)
ok('launcher_auto_scroll_invite_join', 'scrollIntoView({behavior:\'smooth\',block:\'center\'})' in go and "reveal($('#inviteArea'))" in go and "reveal($('#joinStep'))" in go)
ok('catalog_three_columns', '.catalog-grid{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))!important' in css)
ok('d6_independent_fill_border', '.rolling-die.d6, .rolling-die.revealed.d6{' in css and 'background:var(--die-fill,#fff)!important;' in css and 'box-shadow:inset 0 0 0 6px var(--die-border,#111)!important;' in css and 'color:var(--die-text,#111)!important;' in css and '.die-result' not in css)
ok('sound_clear_button', 'id="stopBgm"' in js and "$('#stopBgm')?.addEventListener('click',()=>soundControl('stop'))" in js)
ok('sound_seek_loading_fallback', "Math.max(14400,Math.ceil(pos)+300)" in js and "'불러오는 중'" in js)
ok('sound_old_track_stopped_before_change', "if(['stop','next','prev'].includes(action)){APP.soundSeeking=false;stopSoundEngines()" in js and "APP.forceBgmStartId=Number(id);APP.soundSeeking=false;stopSoundEngines()" in js)
ok('old_track_seek_bug_removed', 'APP.forceBgmStartId=Number(id);APP.soundSeeking=false;seekBgmEngine(0)' not in js)
ok('sound_drawer_scroll_shell', 'sound-drawer-scroll' in js and '.sound-drawer-scroll{min-height:0;overflow:auto' in css)
ok('file_audio_only_runtime', "filter(x=>x.source_type==='file')" in js and 'legacy-sound' not in js)

print('\nSUMMARY')
for n,c,d in results: print(('PASS' if c else 'FAIL'), n, d if not c else '')
print('passed', sum(c for _,c,_ in results), '/', len(results))
if not all(c for _,c,_ in results): raise SystemExit(1)
