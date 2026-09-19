from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
js=(ROOT/'static/app.js').read_text(encoding='utf-8')
css=(ROOT/'static/styles.css').read_text(encoding='utf-8')
i18n=json.loads((ROOT/'static/i18n_ui_en.json').read_text(encoding='utf-8'))
checks=[]
def ok(name, cond):
    checks.append((name,bool(cond)))
    if not cond: raise AssertionError(name)

ok('settings save button is in header actions', 'settings-head-actions"><button id="settingsSaveUi"' in js)
ok('settings save button no longer lives in lower color section', 'id="settingsSaveUi" class="btn dark"' not in js)
ok('sound global button toggles drawer closed', "if($('#soundDrawer'))closeSoundDrawer();else openSoundPanel()" in js)
ok('settings global button toggles drawer closed', "if($('#gmSettingsDrawer'))closeGMSettings();else openGMSettings()" in js)
ok('sound add has stable inline wrapper', 'data-sound-add-wrap="bgm"' in js and 'data-sound-add-wrap="sfx"' in js)
ok('sound add toggle does not rerender drawer', "APP.soundAddOpen[kind]=open" in js and "renderSoundDrawer()}));attachGmVolumeSlider" not in js)
ok('sound add form responsive layout exists', '.sound-add{' in css and '@media(max-width:720px)' in css)
ok('new release banner translated', i18n.get('exact',{}).get('v1.0.0 · 비공식 팬메이드 도구')=='v1.0.0 · Unofficial fan-made tool')
ok('sound upload aria labels translated', i18n.get('terms',{}).get('BGM 오디오 파일')=='BGM audio file' and i18n.get('terms',{}).get('효과음 오디오 파일')=='SFX audio file')
print(f'Public v1.0.0 UI patch: {len(checks)}/{len(checks)} PASS')
