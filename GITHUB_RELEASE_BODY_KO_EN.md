# GitHub Release용 설명문 — v1.0.0

아래 내용을 GitHub **Releases → v1.0.0** 본문에 그대로 붙여 넣을 수 있습니다.

---

# Dungeon World Online v1.0.0

Dungeon World 1st Edition을 위한 비공식 온라인 플레이 보조 도구의 첫 공개 배포판입니다.

## 주요 기능

- Windows x64 호스트 런처 + 브라우저 플레이어 UI
- English / 한국어 (신규 설치 기본 언어: English)
- 캠페인당 플레이어 2–8명, 기본 4명 (GM 제외)
- 캐릭터 시트, 행동, 주문, 인벤토리, 레벨업, 종족/직업 규칙
- GM용 NPC/몬스터/로그/설정/참가자 관리
- DWPack import/export 및 선택형 확장직업 팩
- 파일 기반 BGM/SFX
- LAN 검색, 초대코드, 재접속
- 원격 플레이는 Tailscale / ZeroTier / Radmin VPN 같은 가상 LAN 사용 권장
- English 모드 동적 문장/툴팁/대화상자의 한국어 누수 최종 수정
- 하중(STR 수정치), 동전 무게, 피해 최솟값, 몬스터 고굴림/주사위 프리셋 계산 수정
- 마법사/사제 이름 하드코딩을 제거한 데이터 기반 주문 운용 프로필 및 타직업 주문 체계 상속
- 몬스터 도감 공개 English 번역 보완 + `전부 공개 / Reveal All`
- 기본 몬스터 154개 수록 (이계의 존재 14개 포함)
- 고급행동/다중직업/확장직업 행동의 공용 누적 포인트 시스템
- 능력치 성장 포인트·최소/최대, 확장직업 상한, 몬스터 이동 등 UI와 서버 규칙 최종 무결성 수정
- BGM `끝나면 다음 곡` / `재생목록 반복` 동작 분리
- 규칙 저장의 `r is not defined` 오류 수정 + BUILD_ID 기반 English 번역 캐시 무효화 + 154개 기본 몬스터 English 데이터 재검증
- 사용자 제작 데이터와 기본 콘텐츠 번역 출처를 분리해, 같은 문자열을 써도 커스텀 직업/주문/몬스터/확장직업 이름과 설명이 임의 번역되지 않도록 수정
- 타직업 주문 준비의 `available is not defined` 오류 수정 및 확장직업 상태 `히든 / Hidden` 정리

## 다운로드

일반 사용자는 **`DungeonWorld_Online_v1.0.0_Release.zip`**을 권장합니다. 압축을 푼 뒤 `DungeonWorld_Online_v1.0.0.exe`를 실행하세요.

EXE 단독 파일도 같은 Release Assets에서 제공할 수 있습니다.

## 라이선스 / 출처

프로그램의 독자적인 소프트웨어 코드는 MIT License로 공개합니다. Dungeon World 원문, 한국어 공개판, SRD 5.1 상위 자료, Unlimited Dungeons / Distant Shore 등 제3자 자료는 각 원 라이선스를 따릅니다. 자세한 내용은 `THIRD_PARTY_NOTICES.md`를 확인하세요.

본 프로젝트는 비공식 팬메이드 도구이며 원작자/출판사의 공식 제품이 아닙니다.

## AI 사용 안내

생성형 AI를 코딩·디버깅·테스트·번역/편집·문서화의 보조 도구로 사용했습니다. 최종 선택, 수정, 통합 및 검수는 ShellRoman이 수행했습니다. 상세 내용은 `AI_USE_NOTICE.md`를 확인하세요.

## Build

- Version: `1.0.0`
- Schema: `20`
- BUILD_ID: `bbf02338d0f83dc9`

---

## English

Dungeon World Online v1.0.0 is the first public release of an unofficial online play companion for Dungeon World 1st Edition.

### Highlights

- Windows x64 host launcher with browser-based player UI
- English / Korean; English is the default on a fresh install
- 2–8 player seats per campaign, default 4, GM excluded
- Character sheets, moves, spells, inventory, advancement, race/class rules
- GM tools for NPCs, monsters, logs, settings, and player management
- DWPack import/export and optional expansion-class packs
- File-backed BGM and SFX
- LAN discovery, invite codes, and reconnect support
- For remote play, a virtual LAN such as Tailscale, ZeroTier, or Radmin VPN is recommended
- Final fix pass for Korean leakage in dynamic English UI, tooltips, and dialogs
- Rules fixes for Load (STR modifier), coin weight, damage floor, monster best-of damage, and dice preset state
- Data-driven spellcasting profiles with cross-class/nested spellcasting inheritance instead of class-name runtime rules
- Complete English Bestiary Reveal labels plus a one-click `Reveal All` GM action
- 154 bundled monsters, including 14 Planar Powers
- One cumulative point pool shared by advanced, multiclass, and expansion-class moves
- Final server/UI integrity fixes for ability growth/bounds, expansion limits, monster movement, and related rule enforcement
- Correctly distinct `play next` and `repeat playlist` BGM modes
- Fixed the Rules `r is not defined` save error, build-versioned English translation catalogs, and re-audited English data for all 154 bundled monsters
- Separated bundled-content translation from user-authored data so custom classes, spells, monsters, and expansions are never translated merely because their text matches a core term
- Fixed the cross-class spell-preparation `available is not defined` error and standardized the expansion status label as `히든 / Hidden`

### Download

For most users, download **`DungeonWorld_Online_v1.0.0_Release.zip`**, extract it, and run `DungeonWorld_Online_v1.0.0.exe`.

### License / attribution

Original project software code is released under the MIT License. Dungeon World-derived and other third-party material remains under its applicable source license. See `THIRD_PARTY_NOTICES.md`.

This is an unofficial fan-made project and is not affiliated with or endorsed by the original authors or publishers.

### AI use

Generative AI was used as an assistive tool for coding, debugging, testing, translation/editing, and documentation. Final selection, modification, integration, and review were performed by ShellRoman. See `AI_USE_NOTICE.md`.
