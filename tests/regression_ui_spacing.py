from pathlib import Path

root=Path(__file__).resolve().parents[1]
css=(root/'static'/'styles.css').read_text(encoding='utf-8')
js=(root/'static'/'app.js').read_text(encoding='utf-8')

checks=[]
def ok(name, cond):
    if not cond:
        raise AssertionError(name)
    checks.append(name)

ok('global spacing tokens', '--ui-space-3:14px' in css and 'global visibility / breathing-room pass' in css)
ok('settings header actions visibly separated', 'gap:14px!important' in css and '.settings-head [data-close-settings]' in css)
ok('settings save remains beside close control', 'settings-head-actions"><button id="settingsSaveUi"' in js)
ok('independent action groups get row and column gaps', '.compact-action-row,' in css and 'column-gap:var(--ui-space-2)' in css)
ok('modal body padding increased', '.modal-body{padding:16px}' in css)
ok('sound rows have breathing room', '.sound-item{padding:10px;gap:var(--ui-space-2)}' in css)
ok('effect editor spacing upgraded', '.move-effect-editor-row{padding:13px;gap:13px}' in css)
ok('race effect spacing upgraded', '.race-effect-config-grid{gap:12px}' in css)
ok('inventory remains text first with larger row spacing', '.inventory-text-line{gap:8px 10px}' in css)
ok('mobile spacing remains explicit', '@media(max-width:720px)' in css and '--ui-space-3:12px' in css)
print(f'UI visibility spacing regression: {len(checks)}/{len(checks)} PASS')
