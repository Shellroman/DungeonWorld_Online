from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]
JS=(ROOT/'static/app.js').read_text(encoding='utf-8')
CSS=(ROOT/'static/styles.css').read_text(encoding='utf-8')
UI=json.loads((ROOT/'static/i18n_ui_en.json').read_text(encoding='utf-8'))
CONTENT=json.loads((ROOT/'static/i18n_content_en.json').read_text(encoding='utf-8'))['map']
checks=[]
def ok(n,c,d=''):
 checks.append((n,bool(c),d))
 if not c: print('FAIL',n,d)
ok('inventory_range_dropdown','inventory-range-select' in JS and '<select class="inventory-detail-value inventory-text-select inventory-range-select"' in JS)
ok('no_inventory_range_datalist','inventoryRangeOptions' not in JS)
ok('bard_bonds_translate_linewise',"(c.bonds||[]).map(x=>builtin?displayMultilineContent(x):String(x??'')).join('\\n')" in JS and 'function displayMultilineContent' in JS)
ok('starting_gear_translate_whole',"displayMultilineContent(c.gear||'')" in JS)
ok('large_editor_labels',all(UI['exact'].get(k) for k in ['크게 편집','긴 설명 편집','내용 적용','닫기']))
ok('coin_default_translation',CONTENT.get('닢')=='Coin')
ok('monster_tags_translate',all(CONTENT.get(k) for k in ['마법적','신성','조직적','대집단','소집단','외톨이','반걸음','한걸음','중거리','장거리']))
ok('monster_tag_rule_fields_localized','value="${attr(displayMonsterTag(raw))}"' in JS or 'displayMonsterTag(raw)' in JS)
ok('monster_tag_summary_explicit','selectedTags.map(displayMonsterTag).join' in JS and 'names.map(displayMonsterTag).join' in JS)
ok('file_audio_only_ui',"sounds=(APP.state?.sounds||[]).filter(x=>x.source_type==='file')" in JS and 'legacy-sound' not in JS)
ok('ui_wrap_rules',all(k in CSS for k in ['.gm-tabs button{display:inline-flex','.editor-row .row-head{flex-wrap:wrap}','overflow-wrap:anywhere']))
ok('shellroman','ShellRoman' in JS and 'ShellRoman' in (ROOT/'README_EN.md').read_text(encoding='utf-8'))
passed=sum(c for _,c,_ in checks)
print('PASS',passed,'/',len(checks))
if passed!=len(checks): raise SystemExit(1)
