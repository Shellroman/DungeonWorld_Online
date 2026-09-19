# Dungeon World Online `.dwpack` 공식 참고 자료

`.dwpack`은 Dungeon World Online의 **게임 콘텐츠와 GM 정의 데이터만** 옮기는 ZIP 기반 데이터팩 형식입니다.

플레이어 계정, 캐릭터 현재 상태, 인증 토큰, 세션, 로그, 개인 주사위 설정, 다중창 배치, 개인 음량 등은 포함하지 않습니다.

## 가장 빠른 사용법

1. `example/DungeonWorld_Example.dwpack`을 열어 실제 폴더/JSON 구조를 확인합니다.
2. `schema/`의 JSON Schema를 형식 검증 기준으로 사용합니다.
3. AI로 팩을 만들 때 `AI_BUILDER_PROMPT_KO.md`를 시스템/작업 프롬프트로 함께 제공합니다.
4. 완성된 파일은 ZIP으로 묶되 확장자를 `.dwpack`으로 사용합니다.
5. Dungeon World Online의 `설정 → 데이터팩`에서 먼저 미리보기한 뒤 적용합니다.

## `.dwpack` 내부 구조

```text
manifest.json
data/
  rules.json
  core_moves.json
  classes.json
  spells.json
  races.json
  expansions.json
  monster_folders.json
  monsters.json
  npcs.json
```

부분 데이터팩도 허용합니다. 사용하지 않는 `data/*.json` 파일은 생략할 수 있습니다.

## 충돌 처리

가져오기 시 캠페인에 같은 이름의 데이터가 있으면 다음 중 하나를 선택합니다.

- **기존 데이터 유지**: 이미 있는 항목은 건너뜁니다.
- **가져온 데이터로 교체**: 같은 이름의 정의를 데이터팩 내용으로 갱신합니다.
- **별도 항목으로 추가**: 충돌 항목에 `(가져옴)` 이름을 붙여 별도 항목으로 추가합니다.

규칙은 별도 `캠페인 규칙도 적용` 체크를 켰을 때만 교체됩니다.

## UID

각 항목의 `uid`는 데이터팩 안의 휴대 가능한 참조 식별자입니다. SQLite의 숫자 ID를 복사하지 마십시오.

특히 종족의 `level_reduce`, `grant_unclassified` 주문 효과는 `spell_uid`로 데이터팩 안의 주문을 참조합니다. 가져오기 시 프로그램이 실제 DB ID로 변환합니다.


## 직업 행동 효과 (`move_effects`)

직업의 `start`, `a25`, `a610` 행동에는 선택적으로 `move_effects` 배열을 넣을 수 있습니다. 설명문은 사람이 읽는 규칙 원문으로 그대로 보존하고, 캐릭터 시트에 **지속적으로 반영할 선택/획득 효과만** 구조화합니다. 판정할 때마다 고르는 일회성 선택은 `move_effects`로 만들지 마십시오.

지원 종류:

- `spell_grant`: 분류된 주문 하나 추가. 기본은 현재 직업, `source_class`로 특정 직업, `all_classes: true`로 모든 분류 직업을 대상으로 합니다. `count`, `choice_group`, `exclude_unclassified`를 사용할 수 있습니다.
- `spell_level_reduce`: 현재 직업의 숫자 레벨 주문 하나를 골라 `amount`만큼 레벨을 낮춥니다. 보통 `target_class: "self"`, `exclude_unclassified: true`를 사용합니다.
- `spell_zero`: `spell_name`으로 지정한 현재 직업 주문을 이 행동을 보유하는 동안 0레벨로 취급합니다.
- `move_grant`: `source_class`의 행동 하나를 추가로 선택합니다. `source_class: "*"`이면 모든 타직업에서 출처 직업도 함께 고릅니다.
- `class_access`: `source_class`의 주문 체계를 별도 타직업 영역으로 획득합니다. `grant_moves`에는 함께 자동 획득할 행동 이름을 넣을 수 있습니다.
- `opposite_race_feature`: `race_pair`의 두 종족 중 현재 종족과 반대쪽의 해당 직업 종족 특성을 추가합니다.

`id`는 한 행동 안에서 안정적으로 유지되는 식별자를 권장합니다. 미분류(`__undefined__`) 주문은 일반 `spell_grant`/`spell_level_reduce` 선택 대상으로 넣지 마십시오. 프로그램도 일반 플레이어 선택에서 이를 차단합니다.

## 주문 레벨

- 숫자 `1`~`10`: 해당 레벨 주문
- 문자열(예: `간편`, `암송`): 계산상 0레벨, 화면에는 문자열 그대로 표시

## 보안/개인정보 제외

`.dwpack`에 다음을 넣지 마십시오.

- player/member/character
- 현재 HP/XP/예비/확장직업 보유 상태
- GM/Player token, Host Secret, 비밀번호, 재접속 코드
- 세션/로그/도감 공개 상태
- 주사위 개인 커스텀, 다중창 배치, 개인 볼륨
- IP/LAN/초대코드 정보

## 프로그램 동작

가져온 `.dwpack` 원본 파일 자체는 캠페인 데이터로 보관하지 않습니다. 서버는 내용을 검사하고 현재 캠페인 DB에 복사한 뒤, 업로드 파일은 운반 수단으로만 취급합니다.

## 직업 주문 운용 규칙 (`spellcasting`)

주문직업은 `마법사`, `사제` 같은 직업 이름으로 판별하지 않습니다. 직업 `data.spellcasting`에 실제 운용 규칙을 조합해 저장합니다. 따라서 새 주문직업도 프로그램 코드를 수정하지 않고 만들 수 있습니다.

주요 필드:

- `enabled`: 이 직업의 기본 주문 체계 사용 여부
- `known_mode`: `selected`(선택 습득), `all`(직업 주문 전체를 앎), `manual`(수동)
- `known_label`: 주문서/받은 주문/습득 등 화면에 표시할 이름
- `prepare_mode`: `known`(아는 주문에서 준비), `all`(직업 주문 전체에서 준비), `none`(준비 없음), `manual`
- `prepare_label`: 준비 상태의 표시 이름
- `limit_mode`: `level_sum`, `count`, `none`
- `limit_offset`: `level_sum`일 때 `유효 주문직업 레벨 + 보정값`
- `limit_count`: `count`일 때 고정 준비 개수
- `zero_level_label`: 간편/암송처럼 숫자가 아닌 0레벨 분류 이름
- `zero_auto_known`, `zero_auto_prepared`, `zero_limit_exempt`: 0레벨 주문의 자동 습득/자동 준비/한도 제외 여부
- `starting_choice_level`, `starting_choice_count`: 시작 시 선택할 주문 레벨과 개수. 0이면 시작 선택 없음
- `learn_per_level`: 레벨 상승마다 추가로 습득할 수 있는 주문 수

`class_access` 행동 효과는 `source_class`에 지정한 직업의 `spellcasting` 규칙을 그대로 상속합니다. 예를 들어 어떤 행동이 사제 주문 체계를 얻도록 되어 있다면, 그 행동을 가진 캐릭터의 원래 직업 이름과 관계없이 사제 쪽 설정(전체 주문을 앎, 준비 한도 등)을 별도 주문 트랙으로 사용합니다. 이 효과가 다중직업으로 얻은 행동에 들어 있어도 같은 원칙으로 처리됩니다.
