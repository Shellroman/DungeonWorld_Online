from __future__ import annotations

import ast
import os
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
app_py = (root / 'app.py').read_text(encoding='utf-8')
js = (root / 'static' / 'app.js').read_text(encoding='utf-8')
build = (root / 'build_release.py').read_text(encoding='utf-8')
go = (root / 'launcher' / 'main.go').read_text(encoding='utf-8')
seed = (root / 'data' / 'seed_data.json').read_text(encoding='utf-8')
ref = (root / 'dwpack' / 'reference' / 'AI_BUILDER_PROMPT_KO.md').read_text(encoding='utf-8')
css = (root / 'static' / 'styles.css').read_text(encoding='utf-8')
results=[]
def ok(name, cond, detail=''):
    results.append((name,bool(cond),detail))
    if not cond: print('FAIL',name,detail)

ok('last_brand_app', 'v{app_version}' in app_py)
ok('last_brand_build', 'DISPLAY_VERSION = f"v{APP_VERSION}"' in build and 'DungeonWorld_Online_v{APP_VERSION}.exe' in build)
ok('last_brand_launcher', 'return "v" + v' in go)
ok('last_banner', 'v1.0.0 · 비공식 팬메이드 도구' in js and ('출시 전 '+'최종 확인판') not in js)
ok('state_member_join', 'member_disabled' in app_py and 'member_reconnect_code_hash' in app_py and 'SELECT disabled,reconnect_code_hash FROM members WHERE id=?' not in app_py)
ok('catalog_join', 'monster_data_json' in app_py and 'JOIN monster_defs m ON m.id=c.monster_id' in app_py)
ok('network_cache', 'NETWORK_ADDRESS_CACHE_TTL = 5.0' in app_py and 'def _scan_local_network_addresses' in app_py)
ok('refresh_coalesce', 'scheduleStateRefresh()' in js and 'refreshPromise' in js and 'refreshQueued' in js)
ok('i18n_cache', 'i18nUiCache: new Map()' in js and '_translateUiTextUncached' in js)
ok('ammo_term_seed', '발수' not in seed and '탄약' in seed)
ok('class_move_term_reference', '직업행동' not in ref and '직업 행동' in ref)
ok('wal_not_per_request', 'con.execute("PRAGMA journal_mode = WAL")' in app_py and app_py.index('con.execute("PRAGMA journal_mode = WAL")') > app_py.index('def init_db'))
ok('auth_indexes', all(x in app_py for x in ['idx_members_room_token','idx_members_room_reconnect','idx_gm_sessions_room_token','idx_expansion_grants_character_status']))
ok('file_audio_only_release', "filter(x=>x.source_type==='file')" in js and "source_type='file'" in app_py and 'legacy-sound' not in css)
ok('launcher_language_button_no_mutation_loop', "languageButton&&languageButton.textContent!==languageLabel" in go and "$('#language').textContent=LANG==='en'?'한국어':'English'" not in go)

# Static Python hygiene: no ordinary top-level function is left completely unreferenced.
mod=ast.parse(app_py)
loads={}
for n in ast.walk(mod):
    if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load): loads[n.id]=loads.get(n.id,0)+1
unused=[]
for n in mod.body:
    if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and not n.decorator_list and not n.name.startswith('__') and loads.get(n.name,0)==0:
        unused.append(n.name)
ok('no_unreferenced_top_level_python_helpers', not unused, ','.join(unused))

print('\nSUMMARY')
for n,p,d in results: print(('PASS' if p else 'FAIL'),n,d if not p else '')
print('passed',sum(p for _,p,_ in results),'/',len(results))
if not all(p for _,p,_ in results): raise SystemExit(1)
