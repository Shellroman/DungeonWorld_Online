from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]
js=(ROOT/'static/app.js').read_text(encoding='utf-8')
ui=json.loads((ROOT/'static/i18n_ui_en.json').read_text(encoding='utf-8'))
checks=[]
def ok(cond,name):
    if not cond: raise AssertionError(name)
    checks.append(name)

ok("const available=access.spells.filter" in js, "cross-class prepare variable is declared")
ok("next.add(name),available=" not in js, "no implicit available assignment")
ok("<span>히든</span>" in js and '<span class="hidden-tag">히든</span>' in js, "expansion hidden label stays 히든 in Korean")
ok(ui.get('exact',{}).get('히든')=='Hidden' or ui.get('terms',{}).get('히든')=='Hidden', "히든 translates to Hidden in English")
ok("data-i18n-value=\"raw\"" in js, "custom editor inputs opt out of content-value translation")
ok("recordEsc(resourceName,builtin)" in js and "no-i18n" in js, "custom expansion resource display preserves authored text")
ok("builtin=!!d.builtin" in js, "expansion localization uses provenance flag")
ok('"builtin": bool(data.get("builtin"))' in (ROOT/'app.py').read_text(encoding='utf-8'), "invite receives expansion provenance")
# The core dictionary may legitimately contain 암흑 -> Darkness for the cleric spell.
content=json.loads((ROOT/'static/i18n_content_en.json').read_text(encoding='utf-8')).get('map',{})
ok(content.get('암흑')=='Darkness', "core spell translation remains available")
print(f"custom-content i18n regression: {len(checks)}/{len(checks)} PASS")
