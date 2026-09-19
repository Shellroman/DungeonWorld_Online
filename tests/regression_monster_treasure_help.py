#!/usr/bin/env python3
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'static/app.js').read_text(encoding='utf-8')
UI=json.loads((ROOT/'static/i18n_ui_en.json').read_text(encoding='utf-8'))
EXACT=UI.get('exact',{})
MONSTERS=json.loads((ROOT/'data/monster_seed.json').read_text(encoding='utf-8'))

checks=[]
def ok(name, cond):
    checks.append((name, bool(cond)))

counts=Counter(m.get('folder') for m in MONSTERS)
ok('core monster seed count is 154', len(MONSTERS)==154)
ok('planar folder count is 14', counts.get('이계의 존재')==14)
ok('help documents full Korean public-edition bestiary data', '총 154개 항목' in APP)
ok('help documents full planar count', '“이계의 존재” 폴더도 14개 기본 항목을 수록합니다.' in APP)
ok('help includes treasure adjustments', "['보물 굴림 조정'" in APP)
ok('help includes treasure results', "['보물 결과표'" in APP)
for n in range(1,19):
    ok(f'treasure result {n} present', f"'{n}. " in APP)
ok('monster editor includes roll-mode guide', '굴림 방식 안내' in APP and '고[2D8] + 2' in APP)
ok('help explains high roll', '가장 높은 하나만 쓰고' in APP)
ok('help explains low roll', '가장 낮은 하나만 쓴 뒤' in APP)
ok('help says monster damage does not auto-apply HP', '대상의 HP를 자동으로 깎지는 않습니다.' in APP)
ok('help says monster damage minimum is zero', '최종 피해가 0보다 작아지지 않도록 최소 0' in APP)
ok('load help names STR modifier', '직업의 기본 하중 + 근력 수정치(STR modifier)' in APP)

required_translations={
    '기본 몬스터 자료':'Core Monster Data',
    '보물':'Treasure',
    '보물 굴림 조정':'Treasure Roll Adjustments',
    '보물 결과표':'Treasure Results',
    '굴림 방식 안내':'Roll Mode Guide',
    '최대 하중은 직업의 기본 하중 + 근력 수정치(STR modifier)입니다.':'Maximum load is the class base load + the Strength modifier (STR modifier).',
}
for ko,en in required_translations.items():
    ok(f'English translation: {ko}', EXACT.get(ko)==en)
for n in range(1,19):
    candidates=[k for k in EXACT if k.startswith(f'{n}. ')]
    ok(f'English treasure result {n} mapped', any(EXACT.get(k) and not any('\uac00' <= ch <= '\ud7a3' for ch in EXACT[k]) for k in candidates))

failed=[name for name,cond in checks if not cond]
for name,cond in checks:
    print(('PASS' if cond else 'FAIL'), name)
print(f'\n{len(checks)-len(failed)}/{len(checks)} PASS')
if failed:
    raise SystemExit(1)
