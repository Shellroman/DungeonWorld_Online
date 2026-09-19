from pathlib import Path
import json, zipfile
root=Path(__file__).resolve().parents[1]
js=(root/'static/app.js').read_text(encoding='utf-8')
license_doc=(root/'LICENSE_ATTRIBUTION_KO.md').read_text(encoding='utf-8')
mit=(root/'LICENSE').read_text(encoding='utf-8')
seed=json.loads((root/'data/seed_data.json').read_text(encoding='utf-8'))

results=[]
def ok(name,cond,detail=''):
    results.append((name,bool(cond),detail))
    if not cond: print('FAIL',name,detail)

start=js.index('const HELP_TOPICS = [')
end=js.index('\n\nfunction migrateBrowserStorage',start)
help_text=js[start:end]
for term in ['Experi'+'mental','W'+'IP','schema','DB','웹 입력','서버 전송 범위','이 버전은']:
    ok('help_no_dev_'+term,term not in help_text,term)
ok('help_plain_inventory','인벤토리와 장비' in help_text and '물건 기록하기' in help_text)
ok('help_plain_data','팩 가져오기·내보내기·백업' in help_text and '팩(.dwpack)' in help_text)
ok('help_license_simple','라이선스와 출처' in help_text and '비공식 팬메이드 도구' in help_text)
ok('summary_no_experiment_label','요약 보기 · 실험' not in js)
ok('inventory_no_experiment_label','인벤토리 <small>· 실험' not in js)
ok('settings_no_revision_jargon','템플릿 revision' not in js)
ok('settings_plain_reset','캠페인 데이터는 삭제되지 않습니다.' in js and '캠페인 DB는 삭제되지 않습니다.' not in js)
ok('mit_file','MIT License' in mit and 'Permission is hereby granted' in mit)
ok('license_code_mit','프로그램 코드' in license_doc and 'MIT License' in license_doc)
ok('license_original_content_ccby','프로젝트가 직접 만든 설명 자료' in license_doc and 'CC BY 3.0' in license_doc)
ok('license_dw_ccby','## Dungeon World' in license_doc and 'CC BY 3.0' in license_doc)
ok('license_ud_bysa','## Unlimited Dungeons / Distant Shore Pack' in license_doc and 'CC BY-SA 4.0' in license_doc)

for exp in seed.get('expansions',[]):
    d=exp.get('data',{}) if isinstance(exp,dict) else {}
    note=str(d.get('source_note',''))
    if note:
        ok('seed_expansion_note_plain_'+str(exp.get('name','')), '온라인 도구에 맞게' not in note and '바탕으로 정리한 자료' in note, note)

with zipfile.ZipFile(root/'dwpack'/'UnlimitedDungeons_DistantShore_Expansions.dwpack') as z:
    rows=json.loads(z.read('data/expansions.json'))
    ok('pack_notes_plain',all('온라인 도구에 맞게' not in str(x.get('data',{}).get('source_note','')) for x in rows))

print('\nSUMMARY')
for n,p,d in results: print(('PASS' if p else 'FAIL'),n,d if not p else '')
print('passed',sum(p for _,p,_ in results),'/',len(results))
if not all(p for _,p,_ in results): raise SystemExit(1)
