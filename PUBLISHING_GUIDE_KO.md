# Dungeon World Online v1.0.0 공개 배포 가이드

## 권장 역할 분담

- **GitHub**: 공식 소스, 라이선스, 버전 기록, 이슈, Release Assets
- **itch.io**: 일반 사용자용 소개/스크린샷/다운로드 페이지

## GitHub 저장소

저장소 이름 권장: `DungeonWorld-Online`

Source ZIP의 내용을 풀어 저장소 루트에 올립니다. 루트에는 `README.md`, `LICENSE`, `THIRD_PARTY_NOTICES.md`, `AI_USE_NOTICE.md`를 유지하세요.

### GitHub Release

### 이미 올라간 v1.0.0 Release의 파일 교체

이번 빌드도 버전과 태그는 **v1.0.0 그대로**입니다. 기존 Release를 새로 만들지 말고, 기존 `v1.0.0` Release에서 이전 EXE/Release ZIP/SHA256 파일을 삭제한 뒤 이 패키지의 새 파일을 같은 이름으로 다시 업로드하세요. Release 본문도 `GITHUB_RELEASE_BODY_KO_EN.md`의 최신 내용으로 교체하고, BUILD_ID가 `bbf02338d0f83dc9`인지 확인합니다.

GitHub 저장소의 소스 자체도 이전 공개 소스라면 `DungeonWorld_Online_v1.0.0_Source.zip` 내용으로 갱신한 뒤 커밋/푸시하세요. 태그가 이미 이전 커밋을 가리키고 있다면 태그를 강제로 옮길지 여부는 저장소 운영 방식에 따라 결정하되, 이미 공개된 태그 변경이 부담스럽다면 Release Assets와 기본 브랜치 소스만 최신화하고 Release 본문에 최종 빌드 식별자를 명확히 적는 방법이 안전합니다.

- Tag: `v1.0.0`
- Title: `Dungeon World Online v1.0.0`
- Pre-release: 끔
- Latest release: 켬

첨부 권장:

1. `DungeonWorld_Online_v1.0.0.exe`
2. `DungeonWorld_Online_v1.0.0_Release.zip`
3. `DungeonWorld_Online_v1.0.0_SHA256SUMS.txt`

Release 본문은 `GITHUB_RELEASE_BODY_KO_EN.md`를 복사해 사용하세요.

## itch.io

- Kind: Downloadable
- Platform: Windows
- 메인 다운로드: `DungeonWorld_Online_v1.0.0_Release.zip`
- 첫 공개판 가격: Free 권장
- 설명문: `ITCHIO_PAGE_TEXT_KO_EN.md` 사용
- 소스 링크: GitHub 저장소
- AI 사용 공개 항목은 `AI_USE_NOTICE.md`와 일치하게 설정

## 공개 전 마지막 확인

- Release ZIP을 새 폴더에 풀어 EXE가 존재하는지 확인
- GitHub/itch.io에서 다운로드한 파일의 SHA-256이 `DungeonWorld_Online_v1.0.0_SHA256SUMS.txt`와 일치하는지 확인
- itch.io는 Draft 상태에서 페이지/다운로드/외부 링크를 확인한 뒤 Public으로 전환
- 새 제3자 이미지·음원·폰트·팩을 추가할 경우 공개 전에 별도로 라이선스를 확인

최종 BUILD_ID: `bbf02338d0f83dc9`
