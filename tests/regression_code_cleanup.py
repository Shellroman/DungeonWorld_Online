from pathlib import Path
import json, re

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text(encoding='utf-8')
JS = (ROOT / 'static/app.js').read_text(encoding='utf-8')
HTML = (ROOT / 'static/index.html').read_text(encoding='utf-8')
GO = (ROOT / 'launcher/main.go').read_text(encoding='utf-8')
CSS = (ROOT / 'static/styles.css').read_text(encoding='utf-8')
BUILD = (ROOT / 'build_release.py').read_text(encoding='utf-8')
RACE_SCHEMA = json.loads((ROOT / 'dwpack/reference/schema/races.schema.json').read_text(encoding='utf-8'))

checks = {}
checks['single_mit_license'] = (ROOT / 'LICENSE').is_file() and not (ROOT / 'LICENSE_CODE_MIT.txt').exists()
checks['payload_uses_single_license'] = '"LICENSE"' in BUILD and 'LICENSE_CODE_MIT' not in BUILD
checks['noop_race_sync_removed'] = 'sync_class_races_from_race_defs' not in APP
checks['race_client_no_effect_enabled_flag'] = 'enabled:true,kind' not in JS and 'data-race-effect-enabled' not in JS
props = RACE_SCHEMA['items']['properties']['data']['properties']['spell_effects']['additionalProperties']['items']['properties']
checks['race_schema_no_effect_enabled_flag'] = 'enabled' not in props
checks['canonical_spell_access_not_emitted'] = 'd["spell_access"] = access' not in APP and 'spell_access:{}' not in JS

runtime = '\n'.join((APP, JS, HTML, GO))
css_classes = set(re.findall(r'\.([A-Za-z_][\w-]*)', CSS))
dead = sorted(c for c in css_classes if c not in runtime)
checks['no_unreferenced_runtime_css_classes'] = not dead

failed = []
for name, ok in checks.items():
    print(('PASS' if ok else 'FAIL'), name, ('' if ok else (', '.join(dead[:40]) if name == 'no_unreferenced_runtime_css_classes' else '')))
    if not ok:
        failed.append(name)
print(f'Code cleanup regression: {len(checks)-len(failed)}/{len(checks)} PASS')
if failed:
    raise SystemExit(1)
