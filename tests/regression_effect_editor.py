from __future__ import annotations
import json, pathlib, re

ROOT=pathlib.Path(__file__).resolve().parents[1]
JS=(ROOT/'static/app.js').read_text(encoding='utf-8')
CSS=(ROOT/'static/styles.css').read_text(encoding='utf-8')
UI=json.loads((ROOT/'static/i18n_ui_en.json').read_text(encoding='utf-8'))
EXTRA=json.loads((ROOT/'tools/i18n_ui_extra_en.json').read_text(encoding='utf-8'))
checks=[]
def ok(name,cond,detail=''):
    checks.append((name,bool(cond),detail))
    if not cond: print('FAIL',name,detail)

# Internal identifiers remain data, not user-facing labels or placeholders.
ok('no_raw_builtin_group_in_ui','wizard.lowered_spells' not in JS and 'cleric.lowered_spells' not in JS)
ok('no_raw_group_label','중복 방지 그룹' not in JS)
ok('friendly_dedupe',all(x in JS for x in ['같은 주문 중복 선택 방지','data-me-dedupe','type="hidden" data-me-choice-group','moveEffectAutoChoiceGroup']))
ok('choice_group_preserved',"$('[data-me-choice-group]',r)?.value.trim()||moveEffectAutoChoiceGroup" in JS)

# Move-effect editor teaches intent and shows player-facing consequences.
for text in [
    '이 행동을 얻으면 무엇이 바뀌나요?',
    '플레이어에게는 이렇게 보입니다',
    '행동을 얻었을 때 캐릭터에 계속 남는 변화만 설정합니다.',
    '주사위를 굴린 뒤 10+ 또는 7–9에서 매번 고르는 선택지는 여기에 넣지 말고 행동 설명에 적으세요.',
    '주문 추가 습득','주문 요구 레벨 낮추기','주문을 0레벨로 만들기',
    '다른 직업의 행동 습득','다른 직업의 주문 체계 사용','다른 종족 특성 함께 사용',
]: ok('move_help_'+str(abs(hash(text))),text in JS,text)

# Player choice screen explains why the choice exists and uses action-specific buttons.
for text in ['행동에서 고를 것','추가로 배울 주문','레벨을 낮출 주문','이 주문 배우기','이 주문에 적용','이 행동 배우기']:
    ok('player_choice_'+str(abs(hash(text))),text in JS,text)
ok('player_instruction_function','function moveEffectChoiceInstruction' in JS)

# Race effects are readable cards rather than unlabeled compact/internal controls.
for text in [
    '이 종족 특성은 무엇을 하나요?','다른 직업 주문 추가 선택','현재 직업 주문 레벨 낮추기',
    '특수(미분류) 주문 자동 습득','어느 직업의 주문에서 고르나요?','몇 개를 추가로 고르나요?',
    '어떤 주문의 레벨을 낮추나요?','자동으로 줄 특수 주문','예외적인 자동 지급 기능입니다',
]: ok('race_help_'+str(abs(hash(text))),text in JS,text)
ok('race_effect_cards','race-effect-row-head' in JS and 'race-effect-config-grid' in JS and 'raceEffectPreviewText' in JS)

# Help manual contains concrete examples for both class moves and race spell features.
for text in ['행동 효과란?','행동 효과 예시','종족의 주문 관련 특성']:
    ok('manual_'+str(abs(hash(text))),text in JS,text)

# New static Korean UI/help text must have an English mapping. Dynamic player/race sentences
# are emitted directly in English by their helper functions.
required=[
 '종족의 주문 관련 특성','행동 효과란?','행동 효과 예시','행동에서 고를 것',
 '주문 추가 습득','주문 요구 레벨 낮추기','다른 직업의 행동 습득','주문을 0레벨로 만들기',
 '다른 직업의 주문 체계 사용','다른 종족 특성 함께 사용','같은 주문 중복 선택 방지',
 '플레이어에게는 이렇게 보입니다','이 종족 특성은 무엇을 하나요?','예외적인 자동 지급 기능입니다',
]
exact=UI.get('exact',{})
for ko in required:
    ok('en_'+str(abs(hash(ko))),bool(exact.get(ko)) and not re.search('[가-힣]',exact.get(ko,'')),repr(exact.get(ko)))

# Layout supports readable cards on desktop and narrow screens.
for needle in ['.effect-editor-guide{','.effect-result-preview{','.race-effect-row-head{','.race-effect-config-grid{','.effect-choice-instruction{']:
    ok('css_'+needle,needle in CSS,needle)

print('\nSUMMARY')
for n,p,d in checks: print(('PASS' if p else 'FAIL'),n,d if not p else '')
print('passed',sum(p for _,p,_ in checks),'/',len(checks))
if not all(p for _,p,_ in checks): raise SystemExit(1)
