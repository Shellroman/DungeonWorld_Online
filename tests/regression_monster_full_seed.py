#!/usr/bin/env python3
from __future__ import annotations
import json,re,zipfile
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SEED=json.loads((ROOT/'data/monster_seed.json').read_text(encoding='utf-8'))
EXPECTED={
    '캄캄한 동굴':19,
    '부글거리는 늪지':20,
    '언데드 군단':18,
    '어두운 숲속':18,
    '이민족의 무리':19,
    '뒤틀린 실험체':15,
    '깊고도 깊은 곳':13,
    '이계의 존재':14,
    '사람들':18,
}
checks=[]
def ok(name,cond): checks.append((name,bool(cond)))

counts=Counter(x.get('folder') for x in SEED)
ok('154 bundled monster entries',len(SEED)==154)
ok('environment counts match full core corpus',dict(counts)==EXPECTED)
ok('unique builtin keys',len({x.get('key') for x in SEED})==len(SEED))
ok('unique Korean display names',len({x.get('name') for x in SEED})==len(SEED))
required={'안케그','고블린','바실리스크','리치','코카트리스','놀 두령','불레트','천사','타라스크','언령','가시 악마','종말의 용'}
ok('representative monsters from every expanded folder are present',required <= {x.get('name') for x in SEED})
planar={x.get('name') for x in SEED if x.get('folder')=='이계의 존재'}
ok('all planar core entries present', {'가시 악마','천사','사슬 악마','관념의 정령','유혹의 악마','지니','지옥개','임프','불가피','인면충','나이트메어','콰시트','타라스크','언령'}==planar)

new=[x for x in SEED if isinstance(x.get('en'),dict)]
ok('all 154 bundled entries include explicit English metadata',len(new)==154)
for x in new:
    en=x['en']
    ok(f"English name exists: {x['key']}",bool(en.get('name')))
    for field in ('name','attack_name','range','special','instinct','description'):
        v=en.get(field,'')
        ok(f"English {field} has no Hangul: {x['key']}",not re.search(r'[가-힣]',v or ''))
    for field in ('moves','tags'):
        vals=en.get(field,[]) or []
        ok(f"English {field} has no Hangul: {x['key']}",all(not re.search(r'[가-힣]',v or '') for v in vals))

# Canonical English names that were previously approximated in the starter subset.
content=json.loads((ROOT/'static/i18n_content_en.json').read_text(encoding='utf-8')).get('map',{})
for ko,en in {'거대 악어':'Crocodilian','생살벌레':'Rot Grub','해골룡':'Dragonbone','혼돈의 종자':'Chaos Spawn'}.items():
    ok(f'canonical English name: {ko}',content.get(ko)==en)

# Both bundled core packs must carry the same complete 154-entry corpus.
for fn,expect_english in [('DungeonWorld_1E_Core.dwpack',False),('DungeonWorld_1E_Core_EN.dwpack',True)]:
    with zipfile.ZipFile(ROOT/'dwpack'/fn) as z:
        manifest=json.loads(z.read('manifest.json'))
        monsters=json.loads(z.read('data/monsters.json'))
    ok(f'{fn}: manifest count 154',manifest.get('contents',{}).get('monsters')==154)
    ok(f'{fn}: monster payload count 154',len(monsters)==154)
    if expect_english:
        text=json.dumps(monsters,ensure_ascii=False)
        ok(f'{fn}: no Hangul remains in English monster payload',not re.search(r'[가-힣]',text))

for name,cond in checks:
    if not cond: print('FAIL',name)
failed=[n for n,c in checks if not c]
print(f"{len(checks)-len(failed)}/{len(checks)} PASS")
if failed: raise SystemExit(1)
