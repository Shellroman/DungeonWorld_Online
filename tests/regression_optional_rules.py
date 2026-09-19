import io
import json
import os
import pathlib
import sys
import zipfile

root = pathlib.Path(__file__).resolve().parents[1]
tmp = root / 'tests' / 'regression_optional_rules_data'
tmp.mkdir(parents=True, exist_ok=True)
db = tmp / 'test.db'
db.unlink(missing_ok=True)
os.environ['DW_DB'] = str(db)
os.environ['DW_PORT'] = '8167'
sys.path.insert(0, str(root))

from fastapi.testclient import TestClient
import app

results = []
def ok(name, cond, detail=''):
    results.append((name, bool(cond), detail))
    if not cond:
        print('FAIL', name, detail)

room = ''
with TestClient(app.app, client=('127.0.0.1', 50207)) as c:
    created = c.post('/api/rooms', json={'gm_name': 'GM', 'campaign_name': '선택규칙', 'password': ''})
    ok('create_room', created.status_code == 200, created.text)
    room = created.json()['room_code']
    gh = {'Authorization': 'Bearer ' + created.json()['gm_token']}

    gs = c.get(f'/api/rooms/{room}/state', headers=gh).json()
    ok('new_campaign_expansions_default_off', gs['room']['settings'].get('expansions_enabled') is False, str(gs['room']['settings']))
    ok('new_campaign_has_no_bundled_expansion_examples', len(gs.get('expansions', [])) == 0, str(len(gs.get('expansions', []))))

    joined = c.post(f'/api/rooms/{room}/join', json={'display_name': 'P', 'password': ''})
    ok('join_player', joined.status_code == 200, joined.text)
    ph = {'Authorization': 'Bearer ' + joined.json()['player_token']}
    cid = joined.json()['character_id']
    ji = c.get(f'/api/rooms/{room}/join-info').json()
    fighter = next(x for x in ji['classes'] if x['name'] == '전사')
    race = fighter['races'][0]
    onboard = c.post(f'/api/rooms/{room}/characters/{cid}/onboarding', headers=ph, json={'class_name': '전사', 'race_name': race})
    ok('onboard_player', onboard.status_code == 200, onboard.text)

    # The 11 reference jobs are a separate opt-in DWPack, not default campaign data.
    optional_path = root / 'dwpack' / 'UnlimitedDungeons_DistantShore_Expansions.dwpack'
    optional_raw = optional_path.read_bytes()
    preview0 = c.post(f'/api/rooms/{room}/dwpack/preview', headers=gh, files={'file': ('optional.dwpack', optional_raw, 'application/octet-stream')})
    ok('optional_pack_preview_before_use', preview0.status_code == 200, preview0.text[:500])
    imported = c.post(f'/api/rooms/{room}/dwpack/import', headers=gh, json={'preview_token': preview0.json().get('preview_token',''), 'conflict_mode': 'keep', 'apply_rules': False}) if preview0.status_code == 200 else None
    ok('optional_pack_import', imported is not None and imported.status_code == 200, imported.text if imported is not None else '')
    gs = c.get(f'/api/rooms/{room}/state', headers=gh).json()
    ok('optional_examples_available_after_import', len(gs.get('expansions', [])) == 11, str(len(gs.get('expansions', []))))
    eid = gs['expansions'][0]['id']
    blocked = c.post(f'/api/rooms/{room}/expansions/{eid}/grant', headers=gh, json={'character_id': cid, 'visible_to_party': False, 'message': ''})
    ok('grant_blocked_while_off', blocked.status_code == 409, blocked.text)

    enabled = c.put(f'/api/rooms/{room}/settings', headers=gh, json={'settings': {'expansions_enabled': True}})
    ok('enable_expansions', enabled.status_code == 200 and enabled.json()['settings']['expansions_enabled'] is True, enabled.text)
    grant = c.post(f'/api/rooms/{room}/expansions/{eid}/grant', headers=gh, json={'character_id': cid, 'visible_to_party': False, 'message': '테스트'})
    ok('grant_when_enabled', grant.status_code == 200, grant.text)
    gid = grant.json()['grant_id'] if grant.status_code == 200 else -1
    accepted = c.post(f'/api/rooms/{room}/grants/{gid}/respond', headers=ph, json={'accept': True})
    ok('accept_when_enabled', accepted.status_code == 200, accepted.text)
    ps = c.get(f'/api/rooms/{room}/state', headers=ph).json()
    mine = next(x for x in ps['party'] if x['character_id'] == cid)
    ok('extension_visible_when_enabled', any(x['grant_id'] == gid for x in mine.get('extensions', [])), str(mine.get('extensions', [])))

    disabled = c.put(f'/api/rooms/{room}/settings', headers=gh, json={'settings': {'expansions_enabled': False}})
    ok('disable_expansions', disabled.status_code == 200 and disabled.json()['settings']['expansions_enabled'] is False, disabled.text)
    ps_off = c.get(f'/api/rooms/{room}/state', headers=ph).json()
    mine_off = next(x for x in ps_off['party'] if x['character_id'] == cid)
    ok('extension_hidden_while_off', mine_off.get('extensions') == [], str(mine_off.get('extensions')))
    ok('invite_hidden_while_off', ps_off.get('expansion_invites') == [], str(ps_off.get('expansion_invites')))
    patch = c.patch(f'/api/rooms/{room}/characters/{cid}', headers=ph, json={'patch': {'extension_state': {str(gid): {'legend_owned': True, 'class_moves_owned': [], 'resource_current': 0}}}})
    ok('extension_state_blocked_while_off', patch.status_code == 409, patch.text)

    c.put(f'/api/rooms/{room}/settings', headers=gh, json={'settings': {'expansions_enabled': True}})
    ps_on = c.get(f'/api/rooms/{room}/state', headers=ph).json()
    mine_on = next(x for x in ps_on['party'] if x['character_id'] == cid)
    ok('accepted_data_preserved_after_reenable', any(x['grant_id'] == gid for x in mine_on.get('extensions', [])), str(mine_on.get('extensions', [])))

    # Dice response exposes the raw dice subtotal separately from the modifier.
    prep = c.post(f'/api/rooms/{room}/dice/prepare', headers=ph, json={'dice': {'d6': 2}, 'modifier': 3, 'context': '표시 테스트'})
    ok('dice_prepare', prep.status_code == 200, prep.text)
    rolled = c.post(f'/api/rooms/{room}/dice/roll', headers=ph)
    ok('dice_roll', rolled.status_code == 200, rolled.text)
    if rolled.status_code == 200:
        roll = rolled.json()['roll']
        raw_sum = sum(int(x['value']) for x in roll['results'])
        ok('dice_total_exposed', roll.get('dice_total') == raw_sum, json.dumps(roll, ensure_ascii=False))
        ok('dice_formula_consistent', roll.get('total') == roll.get('dice_total') + 3, json.dumps(roll, ensure_ascii=False))

    # Core Dungeon World material and the optional Unlimited Dungeons expansion examples
    # must remain separate packs with their own license metadata.
    core_path = root / 'dwpack' / 'DungeonWorld_1E_Core.dwpack'
    optional_path = root / 'dwpack' / 'UnlimitedDungeons_DistantShore_Expansions.dwpack'
    with zipfile.ZipFile(core_path) as z:
        names = set(z.namelist())
        manifest = json.loads(z.read('manifest.json'))
        ok('core_pack_has_no_expansions_file', 'data/expansions.json' not in names, str(sorted(names)))
        ok('core_pack_expansion_count_zero', manifest['contents'].get('expansions') == 0, str(manifest.get('contents')))
        ok('core_pack_cc_by3', str(manifest.get('license', '')).startswith('CC BY 3.0'), str(manifest.get('license')))
    optional_raw = optional_path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(optional_raw)) as z:
        manifest = json.loads(z.read('manifest.json'))
        exps = json.loads(z.read('data/expansions.json'))
        ok('optional_pack_expansions_only', set(z.namelist()) == {'manifest.json', 'data/expansions.json'}, str(z.namelist()))
        ok('optional_pack_has_11_examples', len(exps) == 11 and manifest['contents'].get('expansions') == 11, str(manifest.get('contents')))
        ok('optional_pack_cc_by_sa4', 'BY-SA 4.0' in str(manifest.get('license', '')), str(manifest.get('license')))
        ok('optional_pack_source_uses_home', manifest.get('source_url') == 'https://sites.google.com/view/unlimiteddungeonskr/', str(manifest.get('source_url')))
        ok('optional_pack_keeps_english_reference', str(manifest.get('english_reference', '')).startswith('https://drive.google.com/'), str(manifest.get('english_reference')))
        ok('optional_pack_items_use_home', all((x.get('data') or {}).get('source_url') == 'https://sites.google.com/view/unlimiteddungeonskr/' for x in exps), 'item source_url mismatch')
    preview = c.post(f'/api/rooms/{room}/dwpack/preview', headers=gh, files={'file': ('optional.dwpack', optional_raw, 'application/octet-stream')})
    ok('optional_pack_preview_valid', preview.status_code == 200, preview.text[:500])
    if preview.status_code == 200:
        ok('optional_pack_preview_count', preview.json()['counts'].get('expansions') == 11, str(preview.json().get('counts')))

# Simulate opening a pre-schema-14 campaign whose settings JSON predates
# the new optional-rule flag. Migration must preserve the old behaviour by turning it ON.
with app.db() as con:
    row = con.execute('SELECT id,settings_json FROM rooms WHERE code=?', (room,)).fetchone()
    settings = json.loads(row['settings_json'])
    settings.pop('expansions_enabled', None)
    con.execute('UPDATE rooms SET settings_json=? WHERE id=?', (json.dumps(settings, ensure_ascii=False), row['id']))
    con.execute("INSERT INTO app_meta(key,value) VALUES('schema_version','14') ON CONFLICT(key) DO UPDATE SET value='14'")
app.init_db()
with app.db() as con:
    row = con.execute('SELECT settings_json FROM rooms WHERE code=?', (room,)).fetchone()
    migrated = json.loads(row['settings_json'])
    schema = con.execute("SELECT value FROM app_meta WHERE key='schema_version'").fetchone()['value']
    ok('schema14_to_current', schema == str(app.SCHEMA_VERSION), str(schema))
    ok('legacy_campaign_expansions_migrate_on', migrated.get('expansions_enabled') is True, str(migrated))

js = (root / 'static' / 'app.js').read_text(encoding='utf-8')
ok('dice_formula_ui', '주사위 결과' in js and '수정치' in js and 'diceBaseTotal' in js)
ok('settings_ui_toggle', 'settingsExpansionsEnabled' in js and '확장직업 사용' in js)
ok('help_marks_optional_source', "{title:'확장직업'" in js and 'Unlimited Dungeons' in js and 'CC BY-SA 4.0' in js)
ok('player_single_centered_multi_wide', "const layout=getWorkspace(b,false),wide=layout.mode==='multi'" in js and "const layout=getWorkspace(b,true),wide=layout.mode==='multi'" in js)
ok('help_korean_source_collapsed', "['던전월드 한국어 공개판','ko_home']" in js and "['플레이 하는 법','ko_play']" not in js)
ok('help_expansion_sources_separate', "['확장직업 자료',[" in js and "['영어 자료 · 커뮤니티 보관본','ud_en_reference']" in js)
py = (root / 'app.py').read_text(encoding='utf-8')
ok('source_aliases_resolve_to_home', py.count('https://sites.google.com/view/dwtemporary/%ED%99%88?authuser=0') >= 10 and '"ud_expansions": "https://sites.google.com/view/unlimiteddungeonskr/"' in py)
ok('optional_pack_not_core_default_import', 'data-default-import="expansions"' not in js and "['core','classes','races','spells','monsters']" in js)

print('\nSUMMARY')
for name, passed, detail in results:
    print(('PASS' if passed else 'FAIL'), name, detail if not passed else '')
print('passed', sum(p for _, p, _ in results), '/', len(results))
if not all(p for _, p, _ in results):
    raise SystemExit(1)

ok('optional_pack_not_core_default_import', 'data-default-import=\"expansions\"' not in js and "['core','classes','races','spells','monsters']" in js)
