from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'static/app.js').read_text(encoding='utf-8')
CSS=(ROOT/'static/styles.css').read_text(encoding='utf-8')
UI=json.loads((ROOT/'static/i18n_ui_en.json').read_text(encoding='utf-8')).get('exact',{})

checks={
  'folder_title_is_toggle': 'class="monster-folder-title" data-monster-folder-toggle=' in APP,
  'caret_is_inside_title': 'class="monster-folder-caret"' in APP,
  'title_has_aria_expanded': 'aria-expanded="${closed?' in APP,
  'separate_collapse_button_removed': 'class="monster-folder-collapse" data-monster-folder-toggle=' not in APP,
  'per_folder_add_button_removed': 'data-new-monster=' not in APP,
  'top_create_folder_label': '<button id="newMonsterFolder" type="button">폴더 생성</button>' in APP,
  'top_create_monster_label': 'id="newMonsterLoose"' in APP and "'Create Monster':'몬스터 생성'" in APP,
  'top_actions_grouped': 'class="monster-side-actions"' in APP,
  'toggle_updates_aria': "b.setAttribute('aria-expanded',closed?'false':'true')" in APP,
  'toggle_updates_caret': "if(caret)caret.textContent=closed?'▸':'▾'" in APP,
  'folder_action_group': 'class="monster-folder-actions"' in APP,
  'icons_larger': 'font-size:18px!important' in CSS and 'width:34px!important' in CSS,
  'title_click_area_larger': '.monster-folder-title{display:flex!important' in CSS and 'min-height:36px!important' in CSS,
  'create_folder_english': UI.get('폴더 생성')=='Create Folder',
  'create_monster_english': UI.get('몬스터 생성')=='Create Monster',
}
fails=[k for k,v in checks.items() if not v]
if fails:
    raise SystemExit('FAIL: '+', '.join(fails))
print(f"PASS {len(checks)}/{len(checks)} monster folder UI cleanup")
