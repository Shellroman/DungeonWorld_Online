from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
js = (ROOT/'static/app.js').read_text(encoding='utf-8')
css = (ROOT/'static/styles.css').read_text(encoding='utf-8')
i18n = (ROOT/'static/i18n_ui_en.json').read_text(encoding='utf-8')
checks = {
    'custom_bgm_file_picker': 'id="bgmAudioFile" class="hidden-file-input sound-file-input"' in js and 'class="sound-file-button" for="bgmAudioFile"' in js,
    'custom_sfx_file_picker': 'id="sfxAudioFile" class="hidden-file-input sound-file-input"' in js and 'class="sound-file-button" for="sfxAudioFile"' in js,
    'custom_file_name_updates': "input.files?.[0]?.name||'선택된 파일 없음'" in js,
    'native_file_button_not_styled': '::file-selector-button' not in css,
    'divider_stretches': 'align-items:stretch' in css and '.sound-grid>section+section{border-left:4px solid #111}' in css,
    'enable_effect_removed': 'data-race-effect-enabled' not in js and '이 효과 사용' not in js,
    'race_effects_saved_canonical': 'const item={kind};' in js and 'enabled:true,kind' not in js,
    'choose_file_en': '"파일 선택": "Choose File"' in i18n,
    'no_file_en': '"선택된 파일 없음": "No file selected"' in i18n,
}
failed=[k for k,v in checks.items() if not v]
for k,v in checks.items(): print(('PASS' if v else 'FAIL'), k)
print(f'Public sound/effect UI cleanup: {len(checks)-len(failed)}/{len(checks)} PASS')
if failed: raise SystemExit(1)
