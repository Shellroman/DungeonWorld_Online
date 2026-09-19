from pathlib import Path
import json, re, zipfile

ROOT=Path(__file__).resolve().parents[1]
JS=(ROOT/'static/app.js').read_text(encoding='utf-8')
CSS=(ROOT/'static/styles.css').read_text(encoding='utf-8')
LAUNCH=(ROOT/'launcher/main.go').read_text(encoding='utf-8')
SERVER=(ROOT/'app.py').read_text(encoding='utf-8')
UI=json.loads((ROOT/'static/i18n_ui_en.json').read_text(encoding='utf-8'))
CONTENT=json.loads((ROOT/'static/i18n_content_en.json').read_text(encoding='utf-8'))
checks=[]

def ok(name, cond, detail=''):
    if not cond:
        raise AssertionError(f'{name}: {detail}')
    checks.append(name)

ok('version_400',(ROOT/'VERSION').read_text(encoding='utf-8').strip()=='1.0.0')
ok('app_version','VERSION = "1.0.0"' in SERVER)
ok('schema_20','SCHEMA_VERSION = 20' in SERVER)
ok('revision_400','DEFAULT_DATA_REVISION = "1.0.0"' in SERVER)
ok('launcher_name','DungeonWorld_Online_v1.0.0.exe' in (ROOT/'build_windows_launcher.bat').read_text(encoding='utf-8'))

# The info control must not depend on the platform-specific circled-i glyph.
ok('no_circled_i_literal','ⓘ' not in JS)
ok('info_ascii_glyph','class="info-tip-glyph" aria-hidden="true">i</span>' in JS)
ok('info_css_circle','.info-tip-glyph' in CSS and 'border-radius:50%' in CSS)
ok('data_tip_localized',"['placeholder','title','aria-label','data-tip']" in JS)
ok('help_label_en',UI['exact'].get('도움말')=='Help',repr(UI['exact'].get('도움말')))
for text in [
    '장갑은 받는 피해를 줄이는 수치입니다. 기본 장갑은 참고값이고 현재 장갑은 직접 수정할 수 있습니다.',
    '예비는 행동에서 얻어 그 행동이 정한 용도로 소비합니다. 이 칸은 세션 중 현재 예비를 빠르게 기록하는 공용 트래커입니다.',
]:
    ok('tooltip_'+str(abs(hash(text))), bool(UI['exact'].get(text)), repr(UI['exact'].get(text)))

# Known dynamic English leaks are rendered as complete language-specific phrases.
ok('summary_load_complete',"translateUiText('하중')" in JS)
ok('launcher_code_complete',"' · Code <b>'" in LAUNCH)
ok('race_order_complete',"Use this race for <b>" in JS)
ok('multiclass_complete',"Treat as Lv." in JS and 'when choosing a move from another class' in JS)
ok('class_access_complete','data-track-prepared' in JS and 'classAccessSpellGroups' in JS and 'spellcastingProfile' in JS)
ok('inventory_hint_complete','Type</b> is for organization' in JS)

# Previously missing example/attribute translations.
for ko,en in {
    '판정, 성공 결과, 선택지 등 필요한 내용을 자유롭게 적으세요.':'Describe the trigger, results, choices, and any other rules this move needs.',
    '예: 어둠 속에서 누군가가 당신을 지켜보고 있습니다.':'Example: Someone is watching you from the darkness.',
    '플레이 기록 추가':'Play log entry added.',
    '추가 취소':'Remove Added Spell',
    '파일 추가':'Add File',
    '조건':'Requirement',
    '전용 종족 설명':'Race Feature',
}.items():
    ok('translation_'+ko,UI['exact'].get(ko)==en,repr(UI['exact'].get(ko)))

# Preserve familiar English Dungeon World move names and casing.
for ko,en in {
    '접근전':'Hack and Slash',
    '험난한 여정':'Undertake a Perilous Journey',
    '세션 종료':'End of Session',
}.items():
    ok('core_name_'+ko,CONTENT.get('map',{}).get(ko)==en,repr(CONTENT.get('map',{}).get(ko)))
ok('content_complete',len(CONTENT.get('map',{}))>=1179 and not CONTENT.get('unmapped'))

# Generated packs must be reproducible for v4 and the English core must be Korean-free.
for rel in ['dwpack/DungeonWorld_1E_Core.dwpack','dwpack/DungeonWorld_1E_Core_EN.dwpack','dwpack/UnlimitedDungeons_DistantShore_Expansions.dwpack','dwpack/UnlimitedDungeons_DistantShore_Expansions_EN.dwpack']:
    with zipfile.ZipFile(ROOT/rel) as z:
        man=json.loads(z.read('manifest.json'))
        ok('pack_version_'+Path(rel).name,man.get('created_with')=='1.0.0',repr(man.get('created_with')))
with zipfile.ZipFile(ROOT/'dwpack/DungeonWorld_1E_Core_EN.dwpack') as z:
    for name in z.namelist():
        if name.endswith('.json'):
            text=z.read(name).decode('utf-8')
            ok('core_en_no_hangul_'+name,not re.search('[가-힣]',text),name)

print(f'Public v1.0.0 final audit: {len(checks)}/{len(checks)} PASS')
