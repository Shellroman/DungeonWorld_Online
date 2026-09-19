from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "static" / "app.js"
APP = APP_PATH.read_text(encoding="utf-8")
UI = json.loads((ROOT / "static" / "i18n_ui_en.json").read_text(encoding="utf-8"))
CONTENT = json.loads((ROOT / "static" / "i18n_content_en.json").read_text(encoding="utf-8"))
EXTRA = json.loads((ROOT / "tools" / "i18n_ui_extra_en.json").read_text(encoding="utf-8"))

fails: list[str] = []
passed = 0

def ok(name: str, cond: bool, detail: object = "") -> None:
    global passed
    if cond:
        passed += 1
    else:
        fails.append(f"{name}: {detail}")

# This release is a bug-fix pass inside the public v1.0.0 line. Never bump it here.
ok("version_stays_1_0_0", (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "1.0.0")
ok("schema_stays_20", bool(re.search(r"^SCHEMA_VERSION\s*=\s*20\s*$", (ROOT / "app.py").read_text(encoding="utf-8"), re.M)))

# Dynamic pattern captures must be translated as built-in content while preserving
# unknown/user-authored proper names. Replacement strings generated in JSON encode
# line breaks as \\n, so the runtime must decode them before displaying native dialogs.
ok("capture_translator_exists", "function _translateUiCapture" in APP)
ok("pattern_helper_exists", "function _applyUiPattern" in APP)
ok("pattern_capture_recursion", "m.slice(1).map(_translateUiCapture)" in APP)
ok("pattern_newline_decode", "String(repl).replace(/\\\\n/g,'\\n')" in APP or "String(repl).replace(/\\\\n/g,\"\\n\")" in APP)

# Later title / placeholder changes used to bypass the MutationObserver.
ok("observer_watches_attributes", "attributes:true" in APP)
for attr in ("placeholder", "title", "aria-label", "data-tip"):
    ok(f"observer_attr_{attr}", attr in APP)
ok("observer_localizes_attr_mutation", "m.type==='characterData'||m.type==='attributes'" in APP)

# Native dialogs and API error details must all use the same translator.
ok("dialog_translator_unified", "function translateDialogText(v=''){const raw=String(v??'');return APP.language==='en'?translateUiText(raw):raw}" in APP)
ok("api_error_translated", "new Error(APP.language==='en'?translateUiText(detail):detail)" in APP)

# Exact code paths that leaked Korean in the final pre-release screenshot/audit.
checks = {
    "onboarding_class_title": "contentValue(q.cls,classIsBuiltin(q.cls))",
    "onboarding_spell_title": "contentValue(q.cls,classIsBuiltin(q.cls))",
    "onboarding_confirm_names": "const cls=contentValue(q.cls,classIsBuiltin(q.cls)),race=contentValue(q.race,raceIsBuiltin(q.race))",
    "delete_class_display": "confirmUi(`${contentValue(APP.gmClassName,classIsBuiltin(APP.gmClassName))} 직업을 삭제할까요?`)",
    "delete_race_display": "confirmUi(`${contentValue(APP.gmRaceName,raceIsBuiltin(APP.gmRaceName))} 종족을 삭제할까요?`)",
    "monster_missing_tags_display": "missing.map(displayMonsterTag).join(', ')",
    "opposite_race_display": "contentValue(other,raceBuiltin)",
    "levelup_suffix_translate": "translateUiText('레벨업 가능')",
    "spell_validity_translate": "setCustomValidity(result.ok?'':translateUiText(result.message))",
    "folder_dynamic_title_translate": "b.title=translateUiText(closed?'펼치기':'접기')",
}
for name, needle in checks.items():
    ok(name, needle in APP, needle)

# Final contrast status and validation strings must have English entries.
expected_exact = {
    "가독성 낮음": "Low readability",
    "양호": "Good",
    "레벨업 가능": "Level up available",
    "최대": "Maximum",
    "펼치기": "Expand",
    "접기": "Collapse",
    "레벨 / 분류를 입력하세요.": "Enter a level / category.",
    "숫자 주문 레벨은 1~10의 정수만 사용할 수 있습니다.": "Numeric spell levels must be integers from 1 to 10.",
    "문자 분류는 0레벨 주문으로 취급됩니다.": "Text categories are treated as level-0 spells.",
    "폴더 생성": "Create Folder",
    "몬스터 생성": "Create Monster",
}
for ko, en in expected_exact.items():
    ok(f"exact_{ko}", UI.get("exact", {}).get(ko) == en, UI.get("exact", {}).get(ko))
ok("extra_low_readability", EXTRA.get("가독성 낮음") == "Low readability")
ok("extra_good", EXTRA.get("양호") == "Good")

# Run the actual JavaScript translation functions in Node when available. This catches
# the exact mixed-language failure class that static catalog-count tests missed.
node = shutil.which("node")
if node:
    start = APP.index("function _hasCustomContentCollision")
    end = APP.index("function canonicalizeBuiltIn", start)
    funcs = APP[start:end]
    samples = [
        ["직업 · 마법사", "Class · Wizard"],
        ["주문 · 마법사", "Spells · Wizard"],
        ["마법사 · 인간\n이 선택으로 캐릭터를 시작할까요?\n이후 직업/종족 변경은 GM에게 요청해야 합니다.", "Start the character as Wizard · Human?\nAsk the GM for later class or race changes."],
        ["마법사 직업을 삭제할까요?", "Delete the Wizard class?"],
        ["인간 종족을 삭제할까요?", "Delete the Human race?"],
        ["'사람들' 폴더를 삭제할까요?\n안의 몬스터는 삭제되지 않고 '미분류'로 이동합니다.", "Delete the 'Folk of the Realm' folder?\nIts monsters will not be deleted; they will move to Unclassified."],
        ["캠페인 태그 목록에 없어 제외됨: Magical, Divine", "Not in the campaign tag list and omitted: Magical, Divine"],
        ["주문 방어 행동을 선택하려면 먼저 주문 시전 행동을 배워야 합니다.", "To choose Spell Defense, learn Cast A Spell first."],
        # A user-created class whose name collides with a built-in spell must stay authored.
        ["암흑 직업을 삭제할까요?", "Delete the 암흑 class?"],
        ["내마법사 직업을 삭제할까요?", "Delete the 내마법사 class?"],
    ]
    script = f"""
const UI={json.dumps(UI, ensure_ascii=False)};
const CONTENT={json.dumps(CONTENT, ensure_ascii=False)};
const APP={{language:'en',i18nContentEn:CONTENT.map||{{}},i18nUiExact:UI.exact||{{}},i18nUiTerms:Object.entries(UI.terms||{{}}).sort((a,b)=>b[0].length-a[0].length),i18nUiPatterns:(UI.patterns||[]).map(([a,b])=>[new RegExp(a),b]),i18nUiCache:new Map(),state:{{
  classes:{{'마법사':{{_builtin:true}},'암흑':{{_builtin:false}}}},
  races:{{'인간':{{_builtin:true}}}},
  core_moves:[{{name:'주문 방어',_builtin:true}},{{name:'주문 시전',_builtin:true}}],
  spells:{{'사제':[{{name:'암흑',_builtin:true}}]}},
  monsters:[],monster_folders:[{{name:'사람들',builtin:true}}],expansions:[]
}}}};
function displayContent(v=''){{const raw=String(v??'');return APP.language==='en'?(APP.i18nContentEn[raw]??raw):raw;}}
function classIsBuiltin(name=''){{return !!APP.state?.classes?.[name]?._builtin;}}
function raceIsBuiltin(name=''){{return !!APP.state?.races?.[name]?._builtin;}}
function spellIsBuiltin(sp){{return !!sp?._builtin;}}
function coreMoveIsBuiltin(move){{return !!move?._builtin;}}
function monsterIsBuiltin(monster){{return !!monster?.data?.builtin;}}
function monsterFolderIsBuiltin(folder){{return !!folder?.builtin;}}
{funcs}
const samples={json.dumps(samples, ensure_ascii=False)};
for (const [input,expected] of samples) {{
  const got=translateUiText(input);
  if (got!==expected) {{ console.error(JSON.stringify({{input,expected,got}})); process.exit(7); }}
}}
"""
    with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as tf:
        tf.write(script)
        script_path = Path(tf.name)
    try:
        proc = subprocess.run([node, str(script_path)], cwd=ROOT, text=True, capture_output=True)
    finally:
        script_path.unlink(missing_ok=True)
    ok("node_dynamic_translation_samples", proc.returncode == 0, (proc.stderr or proc.stdout).strip())
else:
    # Node is optional for source-only environments; build_release.py performs the same
    # syntax check whenever Node is installed.
    ok("node_dynamic_translation_samples_skipped", True)

if fails:
    print(f"FAIL {len(fails)} / PASS {passed}")
    for item in fails:
        print(" -", item)
    sys.exit(1)
print(f"PASS {passed}")
