from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / 'static' / 'app.js').read_text(encoding='utf-8')
APP_PY = (ROOT / 'app.py').read_text(encoding='utf-8')
UI = json.loads((ROOT / 'static' / 'i18n_ui_en.json').read_text(encoding='utf-8')).get('exact', {})

fails: list[str] = []
passed = 0

def ok(name: str, cond: bool, detail: object = '') -> None:
    global passed
    if cond:
        passed += 1
    else:
        fails.append(f'{name}: {detail}')

ok('version_stays_1_0_0', (ROOT / 'VERSION').read_text(encoding='utf-8').strip() == '1.0.0')
ok('schema_stays_20', bool(re.search(r'^SCHEMA_VERSION\s*=\s*20\s*$', APP_PY, re.M)))

expected = {
    '이름 공개': 'Reveal Name',
    'HP 공개': 'Reveal HP',
    '장갑 공개': 'Reveal Armor',
    '공격명 공개': 'Reveal Attack',
    '피해 공개': 'Reveal Damage',
    '거리 공개': 'Reveal Range',
    '태그 전체 공개': 'Reveal All Tags',
    '본능 공개': 'Reveal Instinct',
    '특기 공개': 'Reveal Special Qualities',
    '몬스터 행동 공개': 'Reveal Monster Moves',
    '설명 공개': 'Reveal Description',
    '전부 공개': 'Reveal All',
    '모든 도감 정보를 플레이어에게 공개할까요?': 'Reveal all bestiary information to players?',
    '모든 도감 정보를 공개했습니다.': 'All bestiary information revealed.',
}
for ko, en in expected.items():
    ok(f'i18n_{ko}', UI.get(ko) == en, UI.get(ko))

ok('full_label_constants_exist', "const MONSTER_CATALOG_REVEAL_FIELDS=[['name','이름 공개']" in APP_JS)
ok('no_fragment_public_suffix', '${l} 공개' not in APP_JS)
ok('reveal_all_button_exists', 'id="revealAllCatalog"' in APP_JS and '>전부 공개</button>' in APP_JS)
ok('reveal_all_handler_exists', 'async function revealAllCatalog()' in APP_JS)
ok('reveal_all_builds_every_field_true', 'Object.fromEntries(MONSTER_CATALOG_REVEAL_FIELDS.map(([key])=>[key,true]))' in APP_JS)
ok('reveal_all_requires_confirmation', "confirmUi('모든 도감 정보를 플레이어에게 공개할까요?')" in APP_JS)
ok('reveal_all_listener_attached', "$('#revealAllCatalog')?.addEventListener('click',revealAllCatalog)" in APP_JS)

field_keys = ['name','hp','armor','attack','damage','range','tags','instinct','special','moves','description']
for key in field_keys:
    ok(f'field_{key}_present', bool(re.search(rf"\['{re.escape(key)}','", APP_JS)))

endpoint_match = re.search(r'async def monster_catalog_update\([\s\S]*?return \{"ok": True\}', APP_PY)
endpoint_text = endpoint_match.group(0) if endpoint_match else ''
allowed_match = re.search(r'allowed\s*=\s*\{([^}]+)\}', endpoint_text)
allowed = set(re.findall(r'"([a-z]+)"', allowed_match.group(1))) if allowed_match else set()
ok('backend_accepts_all_reveal_fields', set(field_keys) <= allowed, sorted(allowed))

if fails:
    print(f'FAIL {len(fails)} / PASS {passed}')
    for item in fails:
        print(' -', item)
    sys.exit(1)
print(f'PASS {passed}')
