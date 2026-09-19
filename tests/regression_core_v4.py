import io, json, os, pathlib, re, sys, threading, time, zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

root = pathlib.Path(__file__).resolve().parents[1]
tmp = root / 'tests' / 'regression_core_v4_data'
tmp.mkdir(parents=True, exist_ok=True)
db = tmp / 'test.db'
if db.exists(): db.unlink()
os.environ['DW_DB'] = str(db)
os.environ['DW_PORT'] = '8174'
sys.path.insert(0, str(root))
from fastapi.testclient import TestClient
import app

results=[]
def ok(name, cond, detail=''):
    results.append((name, bool(cond), detail))
    if not cond: print('FAIL', name, detail)

# Branding, schema and language catalog basics.
app_py=(root/'app.py').read_text(encoding='utf-8')
js=(root/'static/app.js').read_text(encoding='utf-8')
css=(root/'static/styles.css').read_text(encoding='utf-8')
go=(root/'launcher/main.go').read_text(encoding='utf-8')
build=(root/'build_release.py').read_text(encoding='utf-8')
ui_builder=(root/'tools/build_i18n_ui_en.py').read_text(encoding='utf-8')
content=json.loads((root/'static/i18n_content_en.json').read_text(encoding='utf-8'))
ui=json.loads((root/'static/i18n_ui_en.json').read_text(encoding='utf-8'))

ok('schema20', 'SCHEMA_VERSION = 20' in app_py)
ok('regression_brand', 'v{app_version}' in app_py and 'DISPLAY_VERSION = f"v{APP_VERSION}"' in build and 'return "v" + v' in go)
ok('regression_banner', 'v1.0.0 · 비공식 팬메이드 도구' in js and ('출시 전 '+'최종 확인판') not in js)
ok('language_loading_overlay', 'showLanguageLoading' in js and '.language-loading{' in css)
ok('language_launcher_propagation', "x.searchParams.set('lang',LANG)" in go and "searchParams.set('lang',next)" in js)
ok('content_translation_complete', not content.get('unmapped'), str(content.get('unmapped')))
ok('translation_catalog_nontrivial', len(content.get('map',{})) >= 1100 and len(ui.get('exact',{})) >= 1200 and '마법사' not in ui.get('exact',{}) and '암흑' not in ui.get('exact',{}), f"content={len(content.get('map',{}))} ui={len(ui.get('exact',{}))}")

# Regexes shipped to JS must be valid JS-style patterns/replacements, not escaped literal \\d / \\1.
patterns=ui.get('patterns',[])
sample=dict(patterns)
ok('ui_regex_player_count', any(re.compile(p).match('플레이어 3명') and r=='$1 players' for p,r in patterns), str(patterns[:3]))
ok('ui_regex_no_python_backrefs', all('\\\\1' not in r and not re.search(r'\\\\\\\\d', p) for p,r in patterns), str(patterns[:3]))

# The remaining simple, directly-displayed quoted Korean strings must be translatable.
terms=ui.get('terms',{})
exact=ui.get('exact',{})
content_map=content.get('map',{})
compiled=[re.compile(p) for p,_ in patterns]
def ui_covered(raw):
    core=raw.strip().replace('\\n','\n')
    if core in exact or core in content_map: return True
    if any(p.search(core) for p in compiled): return True
    if len(core)<=120:
        out=core
        for a,b in sorted(terms.items(), key=lambda kv:-len(kv[0])): out=out.replace(a,b)
        return out!=core and not re.search(r'[가-힣]',out)
    return False
quoted=re.compile(r"(?s)(?:'([^'\\]*(?:\\.[^'\\]*)*)'|\"([^\"\\]*(?:\\.[^\"\\]*)*)\")")
uncovered=[]
for m in quoted.finditer(js):
    raw=next(g for g in m.groups() if g is not None)
    # This lightweight scanner intentionally covers only ordinary quoted UI
    # literals. Template-literal selector fragments can look like one giant quoted
    # string to this regex; exhaustive i18n coverage is tested separately.
    if re.search(r'[가-힣]',raw) and '<' not in raw and '${' not in raw and 'data-' not in raw and '\n' not in raw and len(raw)<300 and not ui_covered(raw):
        if raw not in uncovered: uncovered.append(raw)
ok('simple_ui_strings_covered', not uncovered, repr(uncovered[:15]))

# No dead stubs from earlier iterations remain.
for dead in ('function coreRow(', 'function attachCoreRows(', 'function attachSpellRows(', 'function spellEditorRow(', 'function inventoryTagSet(', 'function loadNetworkInfo('):
    ok('dead_removed_'+re.sub(r'\W+','_',dead).strip('_'), dead not in js)
for dead in ('def insert_expansions(', 'def ensure_builtin_expansions(', 'def sync_builtin_expansions(', 'def find_move(', 'def _safe_pack_name(', 'def builtin_expansion_key('):
    ok('dead_py_removed_'+re.sub(r'\W+','_',dead).strip('_'), dead not in app_py)

# Payload definition must include bilingual runtime assets and packs.
for rel in ('static/i18n_content_en.json','static/i18n_ui_en.json','dwpack/DungeonWorld_1E_Core_EN.dwpack','dwpack/UnlimitedDungeons_DistantShore_Expansions_EN.dwpack','LICENSE'):
    ok('payload_has_'+rel.replace('/','_'), f'"{rel}"' in build)

# Compare KO/EN pack structure: all non-string values and dictionary keys must be identical.
def load_pack(path):
    with zipfile.ZipFile(path) as z:
        return {n:json.loads(z.read(n)) for n in z.namelist() if n.startswith('data/') and n.endswith('.json')}
def same_mechanics(a,b,path=''):
    if type(a) is not type(b): return False, f'type {path}: {type(a).__name__}!={type(b).__name__}'
    if isinstance(a,dict):
        if set(a)!=set(b): return False, f'keys {path}: {set(a)^set(b)}'
        for k in a:
            yes,why=same_mechanics(a[k],b[k],path+'/'+str(k))
            if not yes:return yes,why
        return True,''
    if isinstance(a,list):
        if len(a)!=len(b):return False,f'length {path}: {len(a)}!={len(b)}'
        for i,(x,y) in enumerate(zip(a,b)):
            yes,why=same_mechanics(x,y,path+f'[{i}]')
            if not yes:return yes,why
        return True,''
    if isinstance(a,str): return True,''
    return (a==b, '' if a==b else f'value {path}: {a!r}!={b!r}')
# English packs translate display/reference names consistently, including dictionary
# keys such as race per-class mappings. Normalize translated keys back before comparing.
reverse={v:k for k,v in {**ui.get('exact',{}), **content_map}.items()}
def canonical_keys(x):
    if isinstance(x,dict): return {reverse.get(k,k):canonical_keys(v) for k,v in x.items()}
    if isinstance(x,list): return [canonical_keys(v) for v in x]
    return x
for stem in ('DungeonWorld_1E_Core','UnlimitedDungeons_DistantShore_Expansions'):
    ko=load_pack(root/'dwpack'/f'{stem}.dwpack'); en=canonical_keys(load_pack(root/'dwpack'/f'{stem}_EN.dwpack'))
    yes,why=same_mechanics(ko,en)
    ok('pack_mechanics_'+stem, yes, why)

# No Korean game text remains in English packs, except credited proper names in expansion manifest (not data/*).
for stem in ('DungeonWorld_1E_Core_EN','UnlimitedDungeons_DistantShore_Expansions_EN'):
    with zipfile.ZipFile(root/'dwpack'/f'{stem}.dwpack') as z:
        hang=[]
        for n in z.namelist():
            if not n.startswith('data/'): continue
            text=z.read(n).decode('utf-8')
            if re.search(r'[가-힣]',text): hang.append(n)
        ok('english_pack_no_hangul_'+stem, not hang, str(hang))

# Test that a language query survives the one-time launcher ticket redirect.
with TestClient(app.app, client=('127.0.0.1', 50174)) as c:
    rootpage=c.get('/')
    ok('root_brand_http', rootpage.status_code==200 and 'v1.0.0' in rootpage.text)
    rr=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'V4','password':''})
    room=rr.json()['room_code']; gm=rr.json()['gm_token']; hdr={'Authorization':'Bearer '+gm}
    t=c.post(f'/api/rooms/{room}/session-ticket',headers=hdr).json()['ticket']
    landing=c.get(f'/session/{t}?lang=en',follow_redirects=False)
    ok('session_ticket_preserves_language', landing.status_code==200 and "&lang=" in landing.text and '"en"' in landing.text, landing.text[:500])

    # The GM stop route must bridge to the launcher so its watchdog marks the exit intentional.
    hits=[]
    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            hits.append(self.path)
            self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(b'{"ok":true}')
        def log_message(self,*args): pass
    srv=ThreadingHTTPServer(('127.0.0.1',0),H)
    th=threading.Thread(target=srv.serve_forever,daemon=True);th.start()
    old=os.environ.get('DW_LAUNCHER_BASE')
    os.environ['DW_LAUNCHER_BASE']=f'http://127.0.0.1:{srv.server_address[1]}'
    try:
        r=c.post(f'/api/rooms/{room}/server-stop',headers=hdr)
        deadline=time.time()+2
        while time.time()<deadline and '/api/stop' not in hits: time.sleep(.05)
        ok('gm_stop_returns_ok', r.status_code==200 and r.json().get('ok') is True, r.text)
        ok('gm_stop_calls_launcher', '/api/stop' in hits, str(hits))
    finally:
        if old is None: os.environ.pop('DW_LAUNCHER_BASE',None)
        else: os.environ['DW_LAUNCHER_BASE']=old
        srv.shutdown();srv.server_close()

# Invite display no longer advertises a same-PC portable code; ordinary LAN is deduplicated by kind.
ok('same_pc_invite_omitted_launcher', 'No loopback invite is shown' in go and '같은 PC' not in go)
ok('ordinary_lan_dedup_server', 'if group in seen_kind:' in app_py and 'group = "로컬 LAN" if kind == "로컬 LAN" else kind' in app_py)
ok('launcher_english_dynamic_ui', "'비밀번호는 초대코드에 포함되지 않습니다. 친구의 환경에 맞는 코드를 복사하세요.':'The password is not included in the invite code." in go and "LANG==='en'?'RESET':'초기화'" in go)
ok('launcher_english_status_patterns', 'Python 3.11 or newer was not found.' in go and 'Host connection was lost. Recovering automatically.' in go and 'Server version mismatch.' in go)

print('\nSUMMARY')
for n,c,d in results: print(('PASS' if c else 'FAIL'), n, d if not c else '')
print('passed',sum(c for _,c,_ in results),'/',len(results))
if not all(c for _,c,_ in results): raise SystemExit(1)
