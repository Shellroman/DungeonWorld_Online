from pathlib import Path
import json, re, zipfile
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'app.py').read_text(encoding='utf-8')
JS=(ROOT/'static/app.js').read_text(encoding='utf-8')
GO=(ROOT/'launcher/main.go').read_text(encoding='utf-8')
BUILD=(ROOT/'build_release.py').read_text(encoding='utf-8')
GOMOD=(ROOT/'launcher/go.mod').read_text(encoding='utf-8')
CSS=(ROOT/'static/styles.css').read_text(encoding='utf-8')
README=(ROOT/'README_KO.md').read_text(encoding='utf-8')
LIC=(ROOT/'LICENSE').read_text(encoding='utf-8')
NOTICES=(ROOT/'THIRD_PARTY_NOTICES.md').read_text(encoding='utf-8')
AI=(ROOT/'AI_USE_NOTICE.md').read_text(encoding='utf-8')
UI=json.loads((ROOT/'static/i18n_ui_en.json').read_text(encoding='utf-8'))
checks=[]
def ok(name,cond,detail=''):
    if not cond: raise AssertionError(f'{name}: {detail}')
    checks.append(name)

ok('version',(ROOT/'VERSION').read_text(encoding='utf-8').strip()=='1.0.0')
ok('app_version','VERSION = "1.0.0"' in APP)
ok('schema20','SCHEMA_VERSION = 20' in APP)
ok('data_revision','DEFAULT_DATA_REVISION = "1.0.0"' in APP)
ok('web_display','display_version = f"v{app_version}"' in APP)
ok('launcher_display','return "v" + v' in GO)
ok('build_display','DISPLAY_VERSION = f"v{APP_VERSION}"' in BUILD)
ok('public_exe_name','DungeonWorld_Online_v{APP_VERSION}.exe' in BUILD)
ok('public_banner','v1.0.0 · 비공식 팬메이드 도구' in JS)
ok('public_banner_en',UI.get('exact',{}).get('v1.0.0 · 비공식 팬메이드 도구')=='v1.0.0 · Unofficial fan-made tool')
ok('public_go_module','module dungeonworldonline/launcher' in GOMOD)
ok('public_config_dir','filepath.Join(base, "DungeonWorldOnline")' in GO)
ok('legacy_config_migration','filepath.Join(base, "DungeonWorldBeta")' in GO and 'os.Rename(legacy, current)' in GO)
ok('public_source_db','_PUBLIC_DB = BASE_DIR / "dungeonworld.db"' in APP)
ok('summary_button_class','summary-view-btn' in JS and 'summary-view-btn' in CSS and 'experimental-summary-btn' not in JS+CSS)
for bad in ('La'+'st v4.0.0','LA'+'ST v4.0.0','DungeonWorld_'+'Last_v4.0.0'):
    ok('no_old_brand_'+bad,bad not in APP+JS+GO+BUILD+README,bad)
ok('mit_root','MIT License' in LIC and 'Copyright (c) 2026 ShellRoman' in LIC)
for needle in ('Sage LaTorra','Adam Koebel','김성일','도서출판 초여명','SRD 5.1','Wizards of the Coast LLC','CC BY 4.0','Unlimited Dungeons','04(공포)','hu924','Jacob Randolph'):
    ok('notice_'+needle,needle in NOTICES,needle)
ok('ai_disclosure','Generative AI' in AI and 'ShellRoman' in AI and 'does not include an integration' in AI)
ok('payload_legal_files',all(x in BUILD for x in ['"LICENSE"','"THIRD_PARTY_NOTICES.md"','"AI_USE_NOTICE.md"','"LICENSE_ATTRIBUTION_KO.md"']))
with zipfile.ZipFile(ROOT/'dwpack/DungeonWorld_1E_Core.dwpack') as z:
    man=json.loads(z.read('manifest.json'))
    ok('core_translation_credit',man.get('translation_credit')=='김성일 / 도서출판 초여명',repr(man.get('translation_credit')))
    ok('core_created_with',man.get('created_with')=='1.0.0',repr(man.get('created_with')))
with zipfile.ZipFile(ROOT/'dwpack/DungeonWorld_1E_Core_EN.dwpack') as z:
    man=json.loads(z.read('manifest.json'))
    ok('english_core_author_credit',man.get('attribution')=='Dungeon World by Sage LaTorra and Adam Koebel',repr(man.get('attribution')))
    ok('english_core_no_translation_field','translation_credit' not in man,repr(man.get('translation_credit')))
    for name in z.namelist():
        if name.endswith('.json'):
            ok('english_core_no_hangul_'+name,not re.search('[가-힣]',z.read(name).decode('utf-8')),name)
# Public build must remain file-audio-only.
text='\n'.join([APP,JS,GO])
for bad in ('you'+'tube.com','you'+'tu.be','You'+'Tube'):
    ok('no_external_video_'+bad,bad.lower() not in text.lower(),bad)
print(f'Public v1.0.0 release audit: {len(checks)}/{len(checks)} PASS')
