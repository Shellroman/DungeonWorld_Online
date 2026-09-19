from pathlib import Path
import json

root=Path(__file__).resolve().parents[1]
js=(root/'static/app.js').read_text(encoding='utf-8')
i18n=json.loads((root/'static/i18n_ui_en.json').read_text(encoding='utf-8'))
extra=json.loads((root/'tools/i18n_ui_extra_en.json').read_text(encoding='utf-8'))
checks=[]
def ok(name,cond,detail=''):
    if not cond:
        raise AssertionError(f'{name}: {detail}')
    checks.append(name)

attach=js[js.index('function attachGMPlayers()'):js.index('function workspaceToolbar',js.index('function attachGMPlayers()'))]
render=js[js.index('function renderGMPlayers()'):js.index('function attachGMPlayers()',js.index('function renderGMPlayers()'))]
ok('gm_special_preview_has_local_pool', "const special=APP.state.spells?.__undefined__||[];" in attach)
ok('gm_special_available_pool', 'available=special.filter(' in render)
ok('gm_special_grant_disabled_when_none_available', "${available.length?'':'disabled'}" in render)
ok('gm_special_options_use_available', '${available.map(sp=>' in render)
# User-facing race spell effects now use explanatory names instead of the old terse label.
ok('cross_class_term_consistent', '다른 직업 주문 추가 선택' in js and '>다른 직업의 주문 습득</option>' not in js and '타직업 주문 획득</option>' not in js)
for key in [
    '다른 직업 주문 추가 선택',
    '종족 설명에 적힌 주문 관련 규칙을 실제 기능으로 연결합니다. 각 효과에서 ‘플레이어에게는 이렇게 보입니다’ 설명을 확인한 뒤 설정하세요.',
]:
    ok('en_exact_'+key[:10], bool(i18n.get('exact',{}).get(key)))
    ok('en_source_'+key[:10], bool(extra.get(key)))
print('PASS',len(checks),'/',len(checks))
