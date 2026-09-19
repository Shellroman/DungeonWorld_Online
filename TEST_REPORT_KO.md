# Dungeon World Online v1.0.0 최종 테스트 보고서

최종 공개 배포용 소스 및 빌드 기준 검증 결과입니다.

- Version: **1.0.0**
- DB schema: **20**
- BUILD_ID: **bbf02338d0f83dc9**
- 기본 언어: **English** (기존 사용자의 저장된 언어 설정은 유지)
- 캠페인 플레이어 정원: **2~8명 / 기본 4명 / GM 제외**
- Windows target: **x64 GUI**
- 최종 주사위 UI: 다면체별 시각적 테두리 두께 보정 포함

## 회귀 테스트

`tests/*.py`의 전체 테스트 스크립트를 최종 소스에서 실행해 모두 PASS했습니다. 실행 시간 제한으로 한 번의 일괄 실행이 마지막 구간에서 중단된 경우에는 남은 스크립트를 별도로 실행해 PASS를 확인했으며, 최종 빌드 후에도 동일하게 재검증했습니다.

주요 결과:

- 전체 테스트 스크립트: **50/50 PASS**

- Public v1.0.0 release audit: **47/47 PASS**
- Public v1.0.0 final audit: **41/41 PASS**
- Release audit: **83/83 PASS**
- Campaign capacity/default language: **14/14 PASS**
- Code cleanup regression: **7/7 PASS**
- Sound/effect UI cleanup: **9/9 PASS**
- UI visibility spacing: **10/10 PASS**
- Move/effect editor: **53/53 PASS**
- Inventory refine: **75/75 PASS**
- Optional rules: **43/43 PASS**
- DWPack: **24/24 PASS**
- Smoke: **25/25 PASS**
- i18n exhaustive: **1315 PASS**
- English dynamic i18n regression: **38 PASS**
- Custom-content i18n collision regression: **9/9 PASS**
- Built-in/custom content provenance regression: **PASS**
- Rules / monster English hotfix: **3294/3294 PASS**
- Bestiary Reveal UI: **35/35 PASS**
- Spellcasting profiles / cross-class inheritance: **28/28 PASS**
- Rule calculations: **17/17 PASS**
- Final integrity audit: **31/31 PASS**
- Full bestiary seed: **1402/1402 PASS**
- English content build: **1795 mapped / 0 unmapped**
- English Core pack game-data Korean residue: **0**
- Build reproducibility: **PASS**
- `python -m py_compile app.py`: **PASS**
- `node --check static/app.js`: **PASS**
- Go `test` / `vet`: **PASS**
- encrypted payload ↔ source ↔ EXE embed verification: **PASS**

`BUILD_MANIFEST.json`에는 최종 payload와 EXE 해시가 기록되어 있습니다.
