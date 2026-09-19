'use strict';

const VERSION_LABEL = document.documentElement.dataset.displayVersion || 'v1.0.0';
const BUILD_ID_LABEL = document.documentElement.dataset.buildId || '';
const STATIC_CACHE_KEY = `${document.documentElement.dataset.appVersion || VERSION_LABEL}-${BUILD_ID_LABEL || 'dev'}`;
const STORAGE_SCHEMA = '8';
const STORAGE_VERSION_KEY = 'dw_storage_schema';
const SESSION_KEY = 'dw_session_v2';
const WORKSPACE_PREFIX = 'dw_workspace_';
const SOUND_ENABLED_KEY = 'dw_sound_enabled';
const SOUND_PREFS_KEY = 'dw_sound_prefs_v2';
const DICE_STYLE_KEY = 'dw_dice_style_v2';
const LANGUAGE_KEY = 'dw_language_v1';
const HELP_TOPICS = [
  {title:'빠른 참조',quickref:true,intro:'세션 중 자주 확인하는 내용을 한곳에 모았습니다. 먼저 이야기 속에서 무엇이 일어나는지 확인하고, 필요한 순간에 규칙을 참고하세요.'},
  {title:'처음 시작하기',intro:'처음이라면 여기부터 읽어보세요. Dungeon World는 이야기를 나누다가 어떤 행동의 조건이 맞아떨어질 때 주사위를 굴리는 게임입니다. 이 프로그램은 캐릭터와 캠페인 정보를 함께 정리해 주는 도구입니다.',sections:[
    ['플레이어로 참가하기',['캠페인을 찾거나 초대코드를 입력한 뒤 이름과 비밀번호로 참가합니다. 처음 참가하면 직업과 종족을 고르는 화면이 열립니다.','바로 정하지 않아도 괜찮습니다. 나갔다가 다시 들어오면 이어서 선택할 수 있습니다.']],
    ['GM으로 시작하기',['캠페인을 만든 뒤 같은 네트워크의 플레이어에게 방을 알려주거나 초대코드를 전달합니다.','직업, 종족, 주문, 몬스터 같은 자료는 캠페인마다 따로 저장됩니다.']],
    ['게임을 진행하는 순서',['먼저 캐릭터가 무엇을 하는지 이야기합니다. 그 설명이 어떤 행동의 발동 조건에 맞으면 주사위를 굴리고, 해당 행동의 결과를 적용합니다.','숫자와 체크칸은 현재 상태를 기록하기 위한 도구입니다. 규칙만으로 분명하지 않은 상황은 이야기의 맥락을 확인한 뒤 GM과 플레이어가 함께 판단하세요.']]
  ]},
  {title:'기본 판정',intro:'Dungeon World에서는 행동 이름을 먼저 고르기보다, 캐릭터가 실제로 무엇을 하는지 이야기하는 것이 먼저입니다. 그 설명이 행동의 조건에 맞으면 판정을 합니다.',sections:[
    ['2D6 판정',['보통 2D6을 굴리고 관련 능력치 수정치를 더합니다. 10+는 대체로 온전한 성공, 7–9는 성공하지만 대가나 선택이 따르는 결과입니다. 6-에서는 GM이 상황을 움직이며 이야기에 새로운 문제나 기회를 더할 수 있습니다.','정확한 결과는 각 행동의 설명을 함께 확인하세요. 같은 7–9라도 행동마다 결과가 다릅니다.']],
    ['피해와 장갑',['피해를 받으면 보통 피해에서 적용되는 장갑만큼 뺀 뒤 HP를 줄입니다. 관통이나 장갑 무시처럼 이 계산을 바꾸는 태그도 있습니다.','특별한 상황에서 장갑이 어떻게 적용되는지는 이야기와 해당 규칙을 함께 보고 판단하세요.']],
    ['예비',['어떤 행동은 예비(hold)를 줍니다. 얻은 예비는 그 행동이 정한 선택지에 쓰는 자원입니다.','캐릭터의 예비 칸은 세션 중 현재 수치를 빠르게 적어두는 공용 기록칸입니다.']]
  ]},
  {title:'캐릭터와 성장',intro:'캐릭터 화면에서는 현재 상태를 기록하고, 요약 보기에서는 세션 중 자주 확인하는 정보만 한눈에 볼 수 있습니다.',sections:[
    ['능력치',['처음에는 캠페인에서 정한 시작 능력치를 배분합니다. 기본값은 16, 15, 13, 12, 9, 8입니다.','게임 중 보상, 부상, 저주, 특별한 효과 등으로 능력치가 달라졌다면 그에 맞게 수정할 수 있습니다.']],
    ['HP와 레벨',['최대 HP는 직업 기본 HP와 체력(CON)을 더해 정합니다. 체력이 오르거나 내리면 최대 HP도 함께 달라집니다.','기본적으로 다음 레벨에 필요한 XP는 현재 레벨 + 7입니다. 캠페인 규칙에 따라 달라질 수 있습니다.']],
    ['요약 보기',['요약 보기에서는 HP, 장갑, 피해, 능력치, 하중, 재화, 가치관, 종족 특성, 인연, 주요 행동을 빠르게 확인할 수 있습니다.','내용을 고칠 때는 각 캐릭터 항목이나 인벤토리, 행동, 주문 화면을 이용하세요.']],
    ['자유 메모',['메모에는 장소의 단서, 물건의 사연, 약속, 세션 중 떠오른 생각처럼 정해진 칸에 넣기 어려운 내용을 자유롭게 적을 수 있습니다.']]
  ]},
  {title:'인벤토리와 장비',intro:'장비는 이름, 종류, 수량, 무게와 태그를 중심으로 기록합니다. 종류는 목록을 정리하기 위한 분류이고, 실제 효과는 태그와 필요한 수치, 설명을 함께 보고 판단합니다.',sections:[
    ['물건 기록하기',['종류는 일반 장비, 무기, 갑옷, 던전 장비, 소모품, 독, 마법 물품, 중요한 물건 등에서 고를 수 있습니다.','태그는 자유롭게 적습니다. 정밀, 관통, 느림, 파괴적처럼 상황에 따라 해석해야 하는 태그는 프로그램이 대신 판정하지 않습니다.']],
    ['하중',['현재 하중은 각 물건의 수량과 무게를 바탕으로 자동 계산됩니다. 최대 하중은 직업의 기본 하중 + 근력 수정치(STR modifier)입니다.','현재 하중이 최대 하중을 넘었을 때의 불이익은 원작의 하중 규칙을 참고하세요.']],
    ['무기',['무기는 거리와 피해 수정치를 기록할 수 있습니다. 피해 주사위는 무기마다 따로 정하는 것이 아니라 캐릭터의 직업 피해 주사위를 사용합니다.','거리에는 반걸음(hand), 한걸음(close), 몇걸음(reach), 중거리(near), 장거리(far)처럼 필요한 범위를 적을 수 있습니다.']],
    ['갑옷',['갑옷은 기본 장갑과 추가 장갑을 나누어 기록합니다. 여러 기본 갑옷이 있다면 가장 높은 기본 장갑 하나를 기준으로 하고, 방패처럼 추가 장갑인 값은 더해서 장비 기준 장갑을 보여줍니다.','장비 기준 장갑은 참고용이며 캐릭터의 현재 장갑을 자동으로 바꾸지는 않습니다.']],
    ['사용 횟수와 탄약',['붕대나 모험 장비처럼 여러 번 쓰는 물건은 사용 횟수를 현재/최대로 기록할 수 있습니다.','탄약은 원작의 추상적인 자원이므로 무기와 분리된 탄약 물건으로 기록하고 현재/최대 값을 관리합니다.']],
    ['재화',['인벤토리 아래의 재화와 캐릭터 화면의 재화는 같은 값입니다. 어느 쪽에서 바꾸어도 함께 반영됩니다.']]
  ]},
  {title:'직업과 종족',intro:'직업은 캐릭터의 기본 HP, 피해, 하중과 주요 행동을 정하고, 종족은 그 직업에서 특별한 출발점을 더해 줍니다.',sections:[
    ['직업',['직업마다 기본 HP, 피해 주사위, 기본 하중, 가치관, 인연 예시, 시작 장비 안내, 시작 행동과 고급 행동이 있습니다.','GM은 캠페인 분위기에 맞게 직업을 새로 만들거나 기존 직업을 바꿀 수 있습니다.']],
    ['종족',['같은 종족이라도 직업에 따라 다른 특징을 가질 수 있습니다. 종족 설명과 주문 관련 특성은 캠페인에 맞게 정할 수 있습니다.']],
    ['종족의 주문 관련 특성',['종족 설명에 “다른 직업의 주문 하나를 고른다”, “특정 주문의 레벨을 낮춘다”, “특수 주문을 자동으로 안다” 같은 내용이 있다면 종족 편집 화면의 주문 관련 특성에서 실제 기능으로 연결할 수 있습니다.','다른 직업 주문 선택은 플레이어가 직접 고르는 선택입니다. 주문 레벨 감소는 현재 직업의 지정 주문을 자동으로 낮춥니다. 미분류 주문 자동 습득은 플레이어가 고르는 기능이 아니라 종족 특성으로 정해진 특수 주문을 자동 지급하는 예외 기능입니다.']],
    ['처음 선택한 뒤',['처음 직업과 종족을 고른 뒤의 큰 변경은 GM과 상의해서 진행하는 것이 좋습니다. 직업을 바꾸면 행동과 주문 구성이 크게 달라질 수 있습니다.']]
  ]},
  {title:'행동과 고급 행동',intro:'행동 설명에는 언제 그 행동이 발동하는지와 주사위 결과가 무엇을 뜻하는지가 함께 적혀 있습니다. 캐릭터가 행동을 가지고 있다고 해서 언제나 자동으로 발동하는 것은 아닙니다.',sections:[
    ['핵심 행동과 시작 행동',['핵심 행동은 누구나 참고할 수 있고, 시작 행동은 해당 직업이 처음부터 가진 능력입니다. 현재 상황이 행동의 조건에 맞는지 설명을 확인하세요.']],
    ['고급 행동',['레벨 2부터 레벨이 오를 때마다 고급행동 포인트를 1점씩 누적해서 얻습니다. 쓰지 않은 포인트는 다음 레벨에도 그대로 남습니다.','직업 고급 행동, 다중직업 선택, 확장직업의 전설행동과 직업 행동은 같은 포인트를 사용합니다. 레벨 2/6 해금 조건은 최소 레벨이며, 그 레벨을 지나도 선택 기회가 사라지지 않습니다.']],
    ['행동 효과란?',['행동 설명에 “주문 하나를 더 배운다”, “주문 레벨을 낮춘다”, “다른 직업 행동을 하나 얻는다”처럼 캐릭터 시트에 계속 남는 변화가 있다면 GM은 행동 효과로 그 기능을 연결할 수 있습니다.','반대로 판정할 때마다 “10+이면 둘을 고른다”처럼 그 순간에만 고르는 결과는 행동 효과가 아닙니다. 그런 내용은 행동 설명에 그대로 적습니다.']],
    ['행동 효과 예시',['증보처럼 주문 하나를 더 배우는 행동은 “주문 추가 습득”을 사용합니다. 플레이어가 행동을 얻은 뒤 조건에 맞는 주문 하나를 고릅니다.','천재처럼 주문 하나를 낮은 레벨로 취급하는 행동은 “주문 요구 레벨 낮추기”를 사용합니다. 새 주문을 얻는 것이 아니라 선택한 주문의 요구 레벨이 내려갑니다.','사냥꾼의 형제처럼 다른 직업 행동을 하나 얻는 행동은 “다른 직업의 행동 습득”을 사용합니다. 신의 은혜처럼 다른 직업의 주문 체계를 쓰게 되는 행동은 “다른 직업의 주문 체계 사용”을 사용합니다.']],
    ['필요와 대체',['어떤 행동을 먼저 배워야 한다면 “필요 · 행동명”으로 표시됩니다. 기존 행동을 대신하는 행동은 “대체 · 행동명”으로 표시됩니다.','표시는 선택을 돕기 위한 안내이며, 세부 해석은 행동 설명과 GM 판단을 함께 따르세요.']]
  ]},
  {title:'주문',intro:'주문은 직업별 목록과 특별한 경우에 쓰는 별도 목록으로 나뉩니다.',sections:[
    ['주문 레벨',['숫자는 주문 레벨을 뜻합니다. 간편이나 암송처럼 숫자가 아닌 분류는 그 이름을 그대로 보여줍니다.']],
    ['마법사와 사제',['마법사는 주문서와 준비한 주문을 따로 관리합니다. 사제는 암송 주문과 일반 주문을 구분해 관리할 수 있습니다.']],
    ['특별한 주문',['종족 특전, 축복, 저주, 물건이나 사건의 효과처럼 일반 직업 주문 목록에 넣기 어려운 주문도 따로 기록할 수 있습니다.']]
  ]},
  {title:'다중직업',intro:'다중직업은 성장 과정에서 다른 직업의 행동을 배우는 선택입니다. 어떤 행동을 가져올 수 있는지는 현재 직업과 레벨, 해당 행동의 조건에 따라 달라집니다.',sections:[
    ['다른 직업의 행동 배우기',['다중직업 행동을 얻으면 조건에 맞는 다른 직업의 행동을 선택할 수 있습니다. 어떤 행동을 배울 수 있는지는 현재 직업과 성장 단계에 따라 달라질 수 있습니다.']],
    ['함께 필요한 행동',['주문서, 주문 준비, 주문 시전처럼 서로 함께 있어야 자연스럽게 작동하는 행동은 묶어서 다룰 수 있습니다. 모든 시작 행동이 무조건 한 묶음이 되는 것은 아닙니다.']]
  ]},
  {title:'확장직업',intro:'확장직업은 Dungeon World 1판의 기본 규칙이 아니라, Unlimited Dungeons의 머나먼 해안(Distant Shore Pack)에서 소개된 아이디어를 참고한 선택 규칙입니다. 사용 여부는 GM이 캠페인마다 정할 수 있습니다.',sections:[
    ['사용하기',['새 캠페인에서는 확장직업이 기본적으로 꺼져 있습니다. 사용하려면 설정에서 켠 뒤, 필요하면 별도로 제공되는 확장직업 예시 팩을 가져오세요.','기능을 끄더라도 이미 만든 확장직업이나 캐릭터가 가진 정보는 지워지지 않습니다.']],
    ['전설행동',['전설행동은 확장직업을 열고 그 뒤의 직업 행동으로 이어지는 대표 행동을 가리키기 위해 이 프로그램에서 사용하는 이름입니다.','다른 게임에서 사용하는 Legendary Action 규칙과는 관계가 없습니다. 영어 화면에서는 Legendary Move로 표시합니다.']],
    ['제안과 획득',['GM이 플레이어에게 확장직업을 제안하고 플레이어가 받아들이면 해당 캐릭터에게 확장직업 항목이 생깁니다.']],
    ['개인 자원',['확장직업마다 별도의 자원이 필요하다면 이름과 최대치를 정해 사용할 수 있습니다.']],
    ['출처',['확장직업 예시는 Unlimited Dungeons / Distant Shore Pack 자료와 한국어 번역을 참고했습니다. 자세한 출처와 이용 조건은 “라이선스와 출처”에서 확인할 수 있습니다.']]
  ]},
  {title:'몬스터와 도감',intro:'GM이 가진 몬스터 정보와 플레이어에게 공개되는 도감 정보는 따로 관리됩니다.',sections:[
    ['몬스터 관리',['몬스터를 지역이나 종류별 폴더로 나누고, HP, 장갑, 공격, 피해, 거리, 태그, 본능, 특기, 행동과 설명을 기록할 수 있습니다.']],
    ['기본 몬스터 자료',['기본 몬스터 자료에는 던전월드 한국어 공개판의 괴물 환경 목록을 기본 데이터로 수록합니다. 현재 사람들을 포함해 총 154개 항목이며, GM은 자유롭게 추가·수정하거나 .dwpack으로 가져올 수 있습니다.','“이계의 존재” 폴더도 14개 기본 항목을 수록합니다. 캠페인에서 기본 몬스터를 수정해도 이후 실행에서 강제로 덮어쓰지 않습니다.']],
    ['도감 공개',['몬스터를 출현시키면 플레이어 도감에 이름이 생깁니다. 아직 공개하지 않은 정보는 ???로 보이며, GM이 원하는 항목만 골라 공개할 수 있습니다.','GM 몬스터 목록의 점은 빨강이 출현만, 주황이 일부 공개, 초록이 전체 공개 상태를 뜻합니다.']],
    ['몬스터 피해 굴림',['피해 굴리기 버튼은 저장된 몬스터 피해식을 공용 주사위 준비창으로 보냅니다. 굴림 결과를 보여줄 뿐 대상의 HP를 자동으로 깎지는 않습니다.','일반은 지정한 주사위를 모두 더한 뒤 수정치를 적용합니다. 고(높은 값)는 지정한 개수의 주사위를 굴려 가장 높은 하나만 쓰고, 저(낮은 값)는 가장 낮은 하나만 쓴 뒤 수정치를 적용합니다.','예: 고[2D8] + 2는 D8 두 개를 굴려 높은 값 하나에 +2를 더합니다. 저[2D8]는 두 값 중 낮은 하나를 씁니다. 주사위 개수가 1개면 고/저는 일반과 같은 결과를 냅니다.','몬스터 피해 굴림은 최종 피해가 0보다 작아지지 않도록 최소 0을 적용합니다.']],
    ['보물',['괴물들도 모험가나 마찬가지로 유용하고 값나가는 것들을 모으곤 합니다. 주인공들이 괴물의 소지품을 뒤질 때는 몸에 지니고 있건 근처에 숨겨 놓았건 그 내용을 사실대로 묘사하십시오.','괴물의 재산은 무작위로 정할 수도 있습니다. 괴물의 피해 주사위를 굴리고 괴물의 특징에 따라 조정한 뒤 보물 결과표에서 결과를 찾습니다.']],
    ['보물 굴림 조정',['• 보물지기: 주사위를 두 번 굴리고 높은 쪽을 택합니다.','• 여행하는 중: 식량을 최소한 하나 더하십시오. 괴물과 입맛이 같은 사람이면 누구나 먹을 수 있습니다.','• 마법적: 특이한 물건 하나. 마법 물품일 수도 있습니다.','• 신성: 어느 신의 징표.','• 이계: 다른 세계에서 온 물건.','• 다른 괴물들의 지배자: 주사위 결과에 +1D4.','• 나이가 많고 특별한 존재: 주사위 결과에 +1D4.']],
    ['보물 결과표',['1. 돈 약간. 2D8 닢 정도.','2. 현 상황에 유용한 물건 하나.','3. 돈 조금. 4D10 닢 정도.','4. 작지만 값비싼 물건 하나(보석, 미술품 등). 가치는 2D10×10 닢, 무게 0.','5. 사소한 마법 물품.','6. 중요한 정보(단서, 지도 등).','7. 돈 주머니. 1D4×100 닢 정도. 100닢에 무게 1.','8. 아주 비싸고 작은 물건 하나(보석, 미술품 등). 가치는 2D6×100 닢, 무게 0.','9. 돈과 기타 소형 귀중품이 든 상자. 가치는 3D6×100 닢, 무게 1.','10. 마법 물품 또는 마법적 효과.','11. 돈 주머니 여럿. 도합 2D4×100 닢.','12. 지위나 직책의 상징(왕관, 깃발 등). 가치는 3D4×100 닢.','13. 대형 미술품. 가치는 4D4×100 닢, 무게 1.','14. 적어도 5D4×100 닢에 상당하는 독특한 물건.','15. 새로운 주문을 하나 배우는 데 필요한 정보 일체. 그리고 한 번 더 굴립니다.','16. 비밀문이나 통로, 또는 그런 곳에 관한 정보. 그리고 한 번 더 굴립니다.','17. 주인공들 중 한 명에 관계된 것. 그리고 한 번 더 굴립니다.','18. 보물더미. 돈 1D10×1000 닢, 그리고 각각 2D6×100의 가치를 가진 보석 1D10×10개.']]
  ]},
  {title:'몬스터 만들기',intro:'“몬스터 빠른 제작”은 몇 가지 질문에 답하면서 기본 수치와 태그의 출발점을 잡는 도구입니다. 마지막에는 이름, 본능, 행동과 설명을 직접 다듬어 몬스터를 완성하세요.',sections:[
    ['무리 규모',['대집단, 소집단, 외톨이 중 어떤 식으로 싸우는지 고르면 기본 피해와 HP의 출발점이 정해집니다.']],
    ['크기와 방어',['크기와 방어 방식을 고르면 HP, 피해, 거리와 장갑이 조정됩니다.']],
    ['특징',['지능적, 조직적, 이계의 존재, 인공물, 끔찍함 같은 특징을 골라 몬스터의 성격을 더할 수 있습니다.']],
    ['마무리',['숫자만으로 몬스터가 완성되는 것은 아닙니다. 무엇을 원하고, 어떤 행동으로 그것을 이루려 하는지 본능과 몬스터 행동에 적어주세요.']]
  ]},
  {title:'NPC',intro:'NPC에는 이름, 외형, 설명, 관계와 GM 메모를 기록할 수 있습니다.',sections:[
    ['정리하기',['중요한 인물은 즐겨찾기에 두고 원하는 순서로 정렬할 수 있습니다. 관계와 현재 상황은 게임이 진행될 때마다 자유롭게 고쳐 쓰세요.']]
  ]},
  {title:'주사위',intro:'한 번 굴린 주사위 결과는 참가자들에게 같은 값으로 보입니다.',sections:[
    ['준비와 굴림',['D2, D4, D6, D8, D10, D12의 개수와 수정치를 정해 굴릴 수 있습니다. GM은 필요에 따라 굴림을 공개하지 않을 수도 있습니다.','결과는 “주사위 결과 + 수정치 = 최종값”으로 표시됩니다.']],
    ['주사위 모양',['내 주사위의 내부색, 테두리색, 숫자색을 정할 수 있습니다. 다른 사람이 굴린 주사위는 그 사람이 고른 색으로 보입니다.']]
  ]},
  {title:'사운드',intro:'BGM은 방 전체에서 함께 듣고, 효과음은 여러 개를 겹쳐 사용할 수 있습니다.',sections:[
    ['BGM',['BGM은 오디오 파일을 업로드해 사용합니다. 방에 참가한 사람들은 같은 곡을 듣고 각자 개인 음량을 조절할 수 있습니다.','현재 재생 영역의 × 버튼은 음악을 완전히 멈추고 현재 곡을 비웁니다.']],
    ['재생 위치와 음량',['재생 막대를 움직여 원하는 위치로 이동할 수 있습니다. GM이 정한 기본 음량과 각 플레이어가 듣는 개인 음량은 따로 조절할 수 있습니다.']]
  ]},
  {title:'다중창',intro:'PC에서는 캐릭터의 여러 항목을 동시에 띄워 둘 수 있습니다.',sections:[
    ['창 조작',['창을 클릭하면 그 창이 앞으로 올라옵니다. 필요한 창만 켜고 끄거나, 위치와 크기를 바꾸고, 준비된 배치를 사용할 수 있습니다.']],
    ['배치 고정',['배치를 고정하면 창의 위치와 크기만 잠깁니다. 창 안의 캐릭터 정보는 평소처럼 수정할 수 있습니다.']]
  ]},
  {title:'플레이어 관리',intro:'접속이 꼬이거나 캐릭터 연결을 바로잡아야 할 때 GM이 사용하는 기능입니다.',sections:[
    ['추방과 접속 차단',['추방은 현재 접속만 끊습니다. 접속 차단은 다시 들어오는 것을 막습니다. 재접속 코드는 같은 캐릭터로 돌아오기 위한 일회용 코드입니다.']],
    ['캐릭터 연결과 삭제',['잘못 참가한 플레이어를 기존 캐릭터에 다시 연결할 수 있습니다. 캐릭터를 영구 삭제하면 되돌리기 어려우므로 먼저 백업하는 것을 권장합니다.']]
  ]},
  {title:'GM 안내',intro:'GM은 세계를 묘사하고 플레이어의 선택에 반응합니다. 프로그램은 정보를 정리해 주지만, 상황을 판단하고 이야기를 움직이는 일은 GM과 플레이어가 함께 합니다.',sections:[
    ['세션 진행',['플레이어가 무엇을 하는지 먼저 듣고, 행동의 조건이 맞을 때 판정을 요청하세요. 결과가 나오면 준비해 둔 정답에 맞추기보다 그 결과에서 이어지는 상황을 보여주세요.']],
    ['정보 공개',['몬스터 도감이나 숨겨진 확장직업처럼 아직 알려지지 않은 정보는 필요한 순간에만 공개하세요.']],
    ['캠페인에 맞게 바꾸기',['직업, 종족, 주문, 확장직업, NPC, 몬스터와 규칙은 캠페인에 맞게 자유롭게 바꿀 수 있습니다.']]
  ]},
  {title:'접속과 캠페인',intro:'호스트가 캠페인을 열어 두면 플레이어는 같은 네트워크에서 찾거나 초대코드로 참가할 수 있습니다.',sections:[
    ['LAN과 초대코드',['같은 네트워크에서는 캠페인 찾기를 사용할 수 있습니다. 다른 네트워크나 VPN 환경에서는 초대코드를 이용하는 것이 편합니다.','호스트가 현재 열어 둔 캠페인 하나만 검색 목록에 나타납니다.']],
    ['연결이 끊겼을 때',['잠시 연결이 끊겨도 다시 접속할 수 있습니다. 호스트 쪽 프로그램은 예기치 않은 종료가 생기면 제한된 횟수 안에서 다시 실행을 시도합니다.']]
  ]},
  {title:'팩 가져오기·내보내기·백업',intro:'기본 자료는 새 캠페인을 만들 때 한 번 복사됩니다. 이후에는 그 캠페인에서 고친 내용이 그대로 유지됩니다.',sections:[
    ['기본 자료',['기본 직업, 종족, 주문이나 몬스터를 지웠다고 해서 다시 시작할 때 자동으로 되살아나지는 않습니다. 필요할 때만 규칙 화면의 “누락 기본 데이터 가져오기”를 사용하세요.','확장직업 예시는 기본 자료와 따로 제공됩니다.']],
    ['팩(.dwpack)',['직업, 종족, 주문, 행동, 확장직업, 몬스터와 일부 규칙을 다른 캠페인으로 옮길 수 있습니다.','플레이어의 현재 캐릭터 상태, 비밀번호, 접속 정보나 개인 화면 설정은 팩에 들어가지 않습니다.']],
    ['백업',['캠페인을 크게 고치거나 삭제하기 전에는 호스트의 데이터 폴더 전체를 따로 복사해 두는 것이 가장 안전합니다. 팩은 콘텐츠를 옮기는 용도이며 전체 캠페인 백업을 대신하지 않습니다.']]
  ]},
  {title:'라이선스와 출처',intro:'Dungeon World Online은 Dungeon World를 함께 즐기기 위한 비공식 팬메이드 도구입니다. 원작자, 번역자, 퍼블리셔 또는 Wizards of the Coast가 제작·승인·보증한 공식 제품이 아닙니다.',sections:[
    ['Dungeon World 원작',['Dungeon World 게임 텍스트는 Sage LaTorra와 Adam Koebel의 저작물이며, 공개된 게임 텍스트를 CC BY 3.0 조건에 따라 사용합니다. 프로그램에 맞게 순서와 형식을 구조화하거나 편집한 부분이 있습니다.']],
    ['한국어 공개판',['한국어 규칙 문구는 김성일 / 도서출판 초여명의 Dungeon World 한국어 공개판을 참고했습니다. 해당 공개판은 저자와 번역자를 표시하는 조건으로 CC BY 3.0 이용을 안내합니다.']],
    ['SRD 5.1 상위 고지',['Dungeon World 공식 라이선스는 Wizards of the Coast LLC의 System Reference Document 5.1 자료를 포함한다고 밝히며, SRD 5.1은 CC BY 4.0으로 제공됩니다. 자세한 내용은 아래 공식 링크를 확인하세요.']],
    ['확장직업 자료',['선택형 확장직업 예시는 Unlimited Dungeons / Distant Shore Pack 계열의 팬 창작 자료를 참고합니다. 한국어 번역은 04(공포), hu924로 표시되어 있으며, 번들된 변형 자료는 CC BY-SA 4.0 조건과 출처 표시를 따릅니다.']],
    ['프로그램 코드',['Dungeon World Online의 독자적인 프로그램 코드와 UI·네트워크·데이터 처리 기능은 ShellRoman이 정리·제작했으며 MIT License로 공개합니다. 제3자 게임 텍스트와 번역 자료에는 해당 MIT License가 적용되지 않습니다.']],
    ['AI 사용 안내',['개발 과정에서 생성형 AI를 코드 작성·검토, 디버깅, 테스트, 번역·문장 다듬기와 문서 작성의 보조 도구로 사용했습니다. 최종 기능 선택, 통합과 검수는 제작자가 수행했습니다. 배포 프로그램 자체에는 외부 AI 서비스 연동 기능이 없습니다.']]
  ]},
  {title:'원작 정보',intro:'더 자세한 원문이나 번역 자료를 확인하고 싶을 때 사용할 수 있는 대표 링크입니다.',link_groups:[
    ['영문 원본',[
      ['Dungeon World 공식 홈페이지','en_home'],
      ['원작 소개 · 라이선스 안내','en_about'],
      ['공식 다운로드','en_downloads'],
      ['Dungeon World 원문 소스','en_source']
    ]],
    ['한국어판',[
      ['던전월드 한국어 공개판','ko_home']
    ]],
    ['확장직업 자료',[
      ['Unlimited Dungeons 한국어 번역','ud_home'],
      ['영어 자료 · 커뮤니티 보관본','ud_en_reference'],
      ['Creative Commons BY-SA 4.0','cc_by_sa_4']
    ]],
    ['Dungeon World · 상위 라이선스',[
      ['Dungeon World 공식 LICENSE','dw_license'],
      ['Creative Commons Attribution 3.0','cc_by'],
      ['System Reference Document 5.1','srd_51'],
      ['Creative Commons Attribution 4.0','cc_by_4']
    ]]
  ]}
];

function migrateBrowserStorage(){
  if(localStorage.getItem(STORAGE_VERSION_KEY)===STORAGE_SCHEMA)return;
  const sound=localStorage.getItem(SOUND_PREFS_KEY)||localStorage.getItem('dw_v151_sound_prefs')||localStorage.getItem('dw_v15_sound_prefs')||localStorage.getItem('dw_sound_prefs');
  const enabled=localStorage.getItem(SOUND_ENABLED_KEY)||localStorage.getItem('dw_v151_sound_enabled')||localStorage.getItem('dw_v15_sound_enabled')||localStorage.getItem('dw_sound_enabled');
  const dice=localStorage.getItem(DICE_STYLE_KEY)||localStorage.getItem('dw_v151_dice_style');
  const language=localStorage.getItem(LANGUAGE_KEY);
  const keep=[];
  for(let i=0;i<localStorage.length;i++){
    const k=localStorage.key(i);
    if(!k)continue;
    if(/workspace_/.test(k)&&k.startsWith('dw_'))keep.push([k,localStorage.getItem(k)]);
    else if(k.startsWith(DICE_STYLE_KEY+':'))keep.push([k,localStorage.getItem(k)]);
  }
  for(let i=localStorage.length-1;i>=0;i--){const k=localStorage.key(i);if(k&&k.startsWith('dw_'))localStorage.removeItem(k);}
  for(let i=sessionStorage.length-1;i>=0;i--){const k=sessionStorage.key(i);if(k&&k.startsWith('dw_')&&k!==SESSION_KEY)sessionStorage.removeItem(k);}
  if(sound)localStorage.setItem(SOUND_PREFS_KEY,sound);if(enabled)localStorage.setItem(SOUND_ENABLED_KEY,enabled);if(dice)localStorage.setItem(DICE_STYLE_KEY,dice);if(language)localStorage.setItem(LANGUAGE_KEY,language);
  for(const [k,v] of keep){if(!v)continue;const suffix=k.slice(k.indexOf('workspace_')+'workspace_'.length);localStorage.setItem(WORKSPACE_PREFIX+suffix,v);}
  localStorage.setItem(STORAGE_VERSION_KEY,STORAGE_SCHEMA);
}
migrateBrowserStorage();

const APP = {
  creds: null,
  state: null,
  ws: null,
  connected: false,
  playerTab: 'character',
  gmTab: 'players',
  gmSelectedChar: null,
  gmClassName: null,
  gmSpellClass: null,
  gmExpansionId: null,
  gmRaceName: null,
  gmNpcId: null,
  gmMonsterId: null,
  gmMonsterFolderId: null,
  ignoreRefreshUntil: 0,
  refreshPromise: null,
  refreshQueued: false,
  refreshTimer: null,
  saveTimer: null,
  workspaceLayouts: {},
  workspaceResizeHandler: null,
  gmLogMode: 'play',
  gmLogFilter: 'all',
  helpTopic: 0,
  expansionSort: 'manual',
  dicePreps: {},
  diceOpenKey: null,
  lastRollStamp: '',
  soundEnabled: localStorage.getItem(SOUND_ENABLED_KEY) === '1',
  soundSeeking: false,
  forceBgmStartId: null,
  onboardingClass: null,
  onboardingRace: null,
  language: (localStorage.getItem(LANGUAGE_KEY)==='ko'?'ko':'en'),
  i18nContentEn: {},
  i18nContentKo: {},
  i18nUiExact: {},
  i18nUiTerms: [],
  i18nUiPatterns: [],
  i18nUiCache: new Map(),
  i18nObserver: null,
};

const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
const appEl = () => $('#app');
const expansionsEnabled = () => APP.state?.room?.settings?.expansions_enabled === true;
const STAT_META = {
  str:['근력','STR','육체적인 힘. 접근전, 힘으로 버티거나 밀어붙이는 위험 돌파 등에 주로 사용합니다.'],
  dex:['민첩성','DEX','반사신경과 손재주. 사격, 회피, 균형, 은밀한 움직임 등에 주로 사용합니다.'],
  con:['체력','CON','생명력과 지구력. 최대 HP와 연결되고 독, 피로, 육체적 고통을 견딜 때 중요합니다.'],
  int:['지능','INT','지식과 논리. 지식 더듬기와 마법사의 여러 행동에 중요합니다.'],
  wis:['지혜','WIS','직감과 관찰력. 상황 파악과 여러 신앙·자연 관련 행동에 중요합니다.'],
  cha:['매력','CHA','설득력과 존재감. 협상과 대인 관계, 여러 사회적 행동에 사용합니다.'],
};

function htmlEscape(v=''){ return String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function displayContent(v=''){
  const raw=String(v ?? '');
  if(APP.language==='en'){
    const direct=APP.i18nContentEn[raw];if(direct!==undefined)return direct;
    const imported=raw.match(/^(.*) \(가져옴\)( \d+)?$/);if(imported){const base=APP.i18nContentEn[imported[1]]??imported[1];return `${base} (Imported)${imported[2]||''}`}
    return raw;
  }
  return APP.i18nContentKo[raw] ?? raw;
}
function displayMultilineContent(v=''){const raw=String(v??'');if(APP.language!=='en'||!raw)return raw;const whole=displayContent(raw);if(whole!==raw)return whole;return raw.split('\n').map(line=>displayContent(line)).join('\n')}
function esc(v=''){ const raw=String(v??'');return htmlEscape(APP.language==='en'?translateUiText(raw):raw); }
function rawEsc(v=''){ return htmlEscape(String(v ?? '')); }
function recordEsc(v,builtin=true){ return builtin?htmlEscape(displayContent(v)):rawEsc(v); }
function recordNoI18n(builtin=true){ return builtin?'':' no-i18n'; }
function contentValue(v,builtin=true){ return builtin?displayContent(v):String(v ?? ''); }
function canonicalIfBuiltin(v,builtin=true){ return builtin?canonicalizeBuiltIn(v):v; }
function restoreDisplayedBuiltIn(edited,original){
  if(APP.language!=='en')return edited;
  if(typeof edited==='string')return typeof original==='string'&&edited===displayContent(original)?original:edited;
  if(Array.isArray(edited))return edited.map((v,i)=>restoreDisplayedBuiltIn(v,Array.isArray(original)?original[i]:undefined));
  if(edited&&typeof edited==='object'){const out={};for(const [k,v] of Object.entries(edited))out[k]=restoreDisplayedBuiltIn(v,original&&typeof original==='object'?original[k]:undefined);return out}
  return edited;
}
function classIsBuiltin(name=''){ return !!APP.state?.classes?.[name]?._builtin; }
function raceIsBuiltin(name=''){ return !!APP.state?.races?.[name]?._builtin; }
function spellIsBuiltin(sp){ if(!sp)return false;if(sp._builtin!==undefined)return !!sp._builtin;const id=Number(sp.id||sp.spell_id)||0;if(id){for(const list of Object.values(APP.state?.spells||{})){const hit=(list||[]).find(x=>Number(x.id)===id);if(hit)return !!hit._builtin}}return false; }
function coreMoveIsBuiltin(move){ return !!move?._builtin; }
function monsterIsBuiltin(monster){ return !!monster?.data?.builtin; }
function monsterFolderIsBuiltin(folder){ return !!folder?.builtin; }
const CORE_MONSTER_TAGS=new Set(['마법적','신성','음흉함','부정형','조직적','지능적','보물지기','은밀','끔찍함','조심스러움','인공물','이계','대집단','소집단','외톨이','매우 작음','작음','큼','거대','괴력','파괴적','장갑 무시','반걸음','한걸음','몇걸음','중거리','장거리']);
const CORE_MONSTER_RANGES=new Set(['반걸음','한걸음','몇걸음','중거리','장거리']);
function displayMonsterTag(v=''){const raw=String(v??'');return APP.language==='en'&&CORE_MONSTER_TAGS.has(raw)?displayContent(raw):raw;}
function displayMonsterRange(v=''){const raw=String(v??'');if(APP.language!=='en'||!raw)return raw;return raw.split(/(\s*,\s*)/).map((part,i)=>i%2?part:(CORE_MONSTER_RANGES.has(part.trim())?displayContent(part.trim()):part)).join('');}
function currencyDisplayName(v=''){const raw=String(v||'닢');return APP.language==='en'&&raw==='닢'?'Coin':raw;}
// Attribute values are deliberately kept canonical. Select values and data-* identifiers
// are used by rule logic and must not change when the display language changes.
function attr(v=''){ return htmlEscape(v).replace(/`/g,'&#96;'); }
function clone(v){ return JSON.parse(JSON.stringify(v)); }
function currentLocale(){return APP.language==='en'?'en-US':'ko-KR'}
function _hasCustomContentCollision(raw=''){
  const name=String(raw??'').trim();if(!name||!APP.state)return false;
  if(Object.prototype.hasOwnProperty.call(APP.state.classes||{},name)&&!classIsBuiltin(name))return true;
  if(Object.prototype.hasOwnProperty.call(APP.state.races||{},name)&&!raceIsBuiltin(name))return true;
  if((APP.state.core_moves||[]).some(x=>x?.name===name&&!coreMoveIsBuiltin(x)))return true;
  for(const list of Object.values(APP.state.spells||{})){if((list||[]).some(x=>x?.name===name&&!spellIsBuiltin(x)))return true}
  if((APP.state.monsters||[]).some(x=>x?.name===name&&!monsterIsBuiltin(x)))return true;
  if((APP.state.monster_folders||[]).some(x=>x?.name===name&&!monsterFolderIsBuiltin(x)))return true;
  if((APP.state.expansions||[]).some(x=>x?.name===name&&!x?.data?.builtin))return true;
  return false;
}
function _builtinContentCapture(v=''){
  const raw=String(v??'').trim();if(!raw||!APP.state||_hasCustomContentCollision(raw))return null;
  if(classIsBuiltin(raw)||raceIsBuiltin(raw))return displayContent(raw);
  const core=(APP.state.core_moves||[]).find(x=>x?.name===raw&&coreMoveIsBuiltin(x));if(core)return displayContent(raw);
  for(const list of Object.values(APP.state.spells||{})){const sp=(list||[]).find(x=>x?.name===raw&&spellIsBuiltin(x));if(sp)return displayContent(raw)}
  const monster=(APP.state.monsters||[]).find(x=>x?.name===raw&&monsterIsBuiltin(x));if(monster)return displayContent(raw);
  const folder=(APP.state.monster_folders||[]).find(x=>x?.name===raw&&monsterFolderIsBuiltin(x));if(folder)return displayContent(raw);
  const expansion=(APP.state.expansions||[]).find(x=>x?.name===raw&&x?.data?.builtin);if(expansion)return displayContent(raw);
  return null;
}
function _translateUiCapture(v=''){
  const raw=String(v??''),left=raw.match(/^\s*/)?.[0]||'',right=raw.match(/\s*$/)?.[0]||'',core=raw.slice(left.length,raw.length-right.length);
  if(!core)return raw;
  const exact=APP.i18nUiExact[core];if(exact!==undefined)return left+exact+right;
  const builtin=_builtinContentCapture(core);if(builtin!==null&&builtin!==core)return left+builtin+right;
  // Dynamic patterns often capture a comma/center-dot separated list. UI words are
  // translated from the UI catalog; bundled rule names are translated only when the
  // current campaign state marks that exact record as built-in. User-authored values
  // are therefore preserved even when their text collides with a core Korean term.
  const parts=core.split(/(\s*(?:·|,|\/|→)\s*)/);let changed=false;
  for(let i=0;i<parts.length;i+=2){const part=parts[i],l=part.match(/^\s*/)?.[0]||'',r=part.match(/\s*$/)?.[0]||'',mid=part.slice(l.length,part.length-r.length),x=APP.i18nUiExact[mid]??_builtinContentCapture(mid);if(x!==undefined&&x!==null&&x!==mid){parts[i]=l+x+r;changed=true}}
  return changed?left+parts.join('')+right:raw;
}
function _applyUiPattern(core,re,repl){
  const m=core.match(re);if(!m)return null;const caps=m.slice(1).map(_translateUiCapture),template=String(repl).replace(/\\n/g,'\n');
  return template.replace(/\$(\d+)/g,(_,n)=>caps[Number(n)-1]??'');
}
function _translateUiTextUncached(raw){
  if(APP.language!=='en'||!/[가-힣]/.test(raw))return raw;
  const left=raw.match(/^\s*/)?.[0]||'',right=raw.match(/\s*$/)?.[0]||'',core=raw.slice(left.length,raw.length-right.length);
  if(!core)return raw;
  const exact=APP.i18nUiExact[core];if(exact!==undefined)return left+exact+right;
  let out=core;
  for(const [re,repl] of APP.i18nUiPatterns){const x=_applyUiPattern(core,re,repl);if(x!==null){out=x;break}}
  // Fragment replacement is limited to short interface-like strings. Partial English
  // is preserved when the remaining Hangul is a user-authored proper name.
  if(out.length<=160){for(const [ko,en] of APP.i18nUiTerms){if(out.includes(ko))out=out.split(ko).join(en)}
    const bits=out.split(/(\s*(?:·|,|\/|→)\s*)/);for(let i=0;i<bits.length;i+=2)bits[i]=_translateUiCapture(bits[i]);out=bits.join('')}
  return out!==core?left+out+right:raw;
}
function translateUiText(v=''){
  const raw=String(v ?? '');if(APP.language!=='en'||!/[가-힣]/.test(raw))return raw;
  const cached=APP.i18nUiCache.get(raw);if(cached!==undefined)return cached;
  const out=_translateUiTextUncached(raw);
  // Dynamic UI has many repeated labels. Keep a small bounded cache so the MutationObserver
  // does not re-run every pattern/term replacement for the same text after each render.
  if(APP.i18nUiCache.size>=2048)APP.i18nUiCache.clear();APP.i18nUiCache.set(raw,out);return out;
}
function canonicalizeBuiltIn(v){
  if(APP.language!=='en')return v;
  if(typeof v==='string')return APP.i18nContentKo[v] ?? v;
  if(Array.isArray(v))return v.map(canonicalizeBuiltIn);
  if(v&&typeof v==='object'){const out={};for(const [k,x] of Object.entries(v))out[k]=canonicalizeBuiltIn(x);return out}
  return v;
}
function localizeDomNode(node){
  if(APP.language!=='en'||!node)return;
  if(node.nodeType===Node.TEXT_NODE){const parent=node.parentElement;if(!parent||parent.closest('script,style,textarea,[contenteditable="true"],code,.no-i18n'))return;const x=translateUiText(node.nodeValue||'');if(x!==node.nodeValue)node.nodeValue=x;return}
  if(node.nodeType!==Node.ELEMENT_NODE)return;
  const el=node;if(el.closest?.('.no-i18n'))return;
  for(const name of ['placeholder','title','aria-label','data-tip']){const x=el.getAttribute?.(name);if(x&&/[가-힣]/.test(x)){const y=translateUiText(x);if(y!==x)el.setAttribute(name,y)}}
  for(const child of [...el.childNodes])localizeDomNode(child);
}
function localizeDocument(){document.documentElement.lang=APP.language==='en'?'en':'ko';if(APP.language==='en')localizeDomNode(document.body)}
function startI18nObserver(){
  APP.i18nObserver?.disconnect?.();if(APP.language!=='en')return;
  APP.i18nObserver=new MutationObserver(ms=>{for(const m of ms){for(const n of m.addedNodes||[])localizeDomNode(n);if(m.type==='characterData'||m.type==='attributes')localizeDomNode(m.target)}});
  APP.i18nObserver.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['placeholder','title','aria-label','data-tip']});localizeDocument();
}
function showLanguageLoading(target){
  document.querySelector('#languageLoading')?.remove();const en=target==='en';document.body.insertAdjacentHTML('beforeend',`<div id="languageLoading" class="language-loading" role="status"><div><span class="language-spinner"></span><b>${en?'Switching language…':'언어를 변경하는 중…'}</b><p>${en?'Loading the interface and core rules.':'화면과 기본 규칙 자료를 불러오고 있습니다.'}</p></div></div>`);
}
function setLanguage(lang){
  const next=lang==='en'?'en':'ko';if(next===APP.language)return;showLanguageLoading(next);localStorage.setItem(LANGUAGE_KEY,next);setTimeout(()=>{const u=new URL(location.href);u.searchParams.set('lang',next);location.replace(u.toString())},120);
}
function languageButton(){return `<button data-language-switch class="btn small" type="button" title="Language / 언어">${APP.language==='en'?'한국어':'English'}</button>`}
function toast(msg,ms=2300){ const t=$('#toast'); if(!t)return; t.textContent=translateUiText(msg);t.classList.add('on');clearTimeout(t._timer);t._timer=setTimeout(()=>t.classList.remove('on'),ms); }
function confirmUi(msg){return window.confirm(translateUiText(msg));}
function promptUi(msg,value=''){return window.prompt(translateUiText(msg),value);}
function fmtTime(iso){ try{return new Date(iso).toLocaleString(currentLocale(),{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'});}catch{return iso||''} }
function statMod(n){n=Number(n)||0;const ranges=APP.state?.room?.rules?.stat_mod_ranges||[{max:3,mod:-3},{max:5,mod:-2},{max:8,mod:-1},{max:12,mod:0},{max:15,mod:1},{max:17,mod:2},{max:99,mod:3}];for(const r of ranges){if(n<=Number(r.max))return Number(r.mod)||0}return Number(ranges.at(-1)?.mod)||0;}
function modText(n){ const m=statMod(n);return (m>=0?'+':'')+m; }
function classData(s){ return APP.state.classes[s.class_name]||{}; }
function hpMax(s){ const c=classData(s);return Math.max(1,(Number(c.hp)||1)+(Number(s.stats?.con)||0)); }
function xpRequiredFor(s,bundle=null){const server=Number(bundle?.summary?.xp_required);if(Number.isFinite(server)&&server>0)return server;const rawBase=Number(APP.state?.room?.rules?.xp_base),base=Math.max(0,Number.isFinite(rawBase)?rawBase:7);return Math.max(1,(Number(s?.level)||1)+base);}
function currentSummary(id){ return APP.state.party.find(p=>p.character_id===id); }
function damageText(s){ const die=String(s.damage_die||classData(s).damage||'D6').toUpperCase(),b=Number(s.damage_bonus)||0;return b?`${die} ${b>0?'+':'-'} ${Math.abs(b)}`:die; }
function formatWeight(n){const v=Math.max(0,Number(n)||0);return Number.isInteger(v)?String(v):String(Math.round(v*100)/100);}
function inventoryWeight(s){const itemWeight=(Array.isArray(s?.inventory)?s.inventory:[]).reduce((sum,item)=>sum+Math.max(1,Number(item?.quantity)||1)*Math.max(0,Number(item?.weight)||0),0),rules=APP.state?.room?.rules||{};if(rules.coin_weight_enabled===true){const per=Math.max(1,Number(rules.coin_weight_per)||100),coins=Math.max(0,Number(s?.currency)||0);return itemWeight+(coins/per)}return itemWeight;}
function inventoryLoadInfo(s){const max=Math.max(0,(Number(classData(s).load)||0)+statMod(s?.stats?.str)),current=inventoryWeight(s);if(current<=max)return {current,max,state:'ok',short:'정상 하중',detail:'최대 하중 이하입니다.'};if(current<=max+2)return {current,max,state:'warn',short:'초과 하중 · 행동 시 -1',detail:'최대 하중보다 1~2 높습니다. 짐을 진 채 행동할 때 원작의 하중(Encumbrance) 규칙에 따라 -1을 적용합니다.'};return {current,max,state:'bad',short:'과적 · 하중 정리 필요',detail:'최대 하중+2를 넘었습니다. 원작의 하중(Encumbrance) 규칙에 따라 최소 1무게를 버리고 -1로 굴리거나 자동 실패를 선택하는 상황입니다.'};}
function infoTip(text){ const tip=translateUiText(text),label=translateUiText('도움말');return `<button class="info-tip" type="button" aria-label="${attr(label)}" data-tip="${attr(tip)}"><span class="info-tip-glyph" aria-hidden="true">i</span></button>`; }
function rgb(hex){ const h=String(hex||'').replace('#','');if(!/^[0-9a-f]{6}$/i.test(h))return [255,255,255];return [0,2,4].map(i=>parseInt(h.slice(i,i+2),16)); }
function luminance(hex){ return rgb(hex).map(x=>{x/=255;return x<=.03928?x/12.92:Math.pow((x+.055)/1.055,2.4)}).reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0); }
function contrastRatio(a,b){ const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05); }

function rememberCreds(creds){APP.creds={...creds};sessionStorage.setItem(SESSION_KEY,JSON.stringify(APP.creds));}
function clearCurrent(){APP.creds=null;APP.state=null;sessionStorage.removeItem(SESSION_KEY);if(APP.ws){try{APP.ws.close()}catch{}}APP.ws=null;APP.connected=false;}
function clearBrowserGameData(){clearCurrent();for(let i=localStorage.length-1;i>=0;i--){const k=localStorage.key(i);if(k&&k.startsWith('dw_'))localStorage.removeItem(k);}for(let i=sessionStorage.length-1;i>=0;i--){const k=sessionStorage.key(i);if(k&&k.startsWith('dw_'))sessionStorage.removeItem(k);}APP.soundEnabled=false;try{stopSoundEngines()}catch{}}
function loadCreds(){try{const raw=sessionStorage.getItem(SESSION_KEY);APP.creds=raw?JSON.parse(raw):null;}catch{APP.creds=null}}
async function api(path,options={},timeoutMs=7000){
  const headers={'Content-Type':'application/json',...(options.headers||{})};if(APP.creds?.token)headers.Authorization=`Bearer ${APP.creds.token}`;
  const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),timeoutMs);
  try{
    const requestOptions={...options,headers,signal:ctrl.signal};
    const res=await fetch(path,requestOptions);let data=null;try{data=await res.json()}catch{}
    if(!res.ok){const detail=data?.detail||`HTTP ${res.status}`,err=new Error(APP.language==='en'?translateUiText(detail):detail);err.status=res.status;throw err;}return data;
  }catch(e){
    if(e?.name==='AbortError'){const err=new Error('서버 응답 시간이 초과되었습니다. 서버가 실행 중인지 확인하고 다시 시도해주세요.');err.status=0;throw err;}
    if(e instanceof TypeError){const err=new Error('서버에 연결할 수 없습니다. 주소와 서버 실행 상태를 확인해주세요.');err.status=0;throw err;}
    throw e;
  }finally{clearTimeout(timer)}
}
async function apiForm(path,formData,timeoutMs=30000){
  const headers={};if(APP.creds?.token)headers.Authorization=`Bearer ${APP.creds.token}`;
  const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),timeoutMs);
  try{const res=await fetch(path,{method:'POST',headers,body:formData,signal:ctrl.signal});let data=null;try{data=await res.json()}catch{}if(!res.ok){const detail=data?.detail||`HTTP ${res.status}`,err=new Error(APP.language==='en'?translateUiText(detail):detail);err.status=res.status;throw err}return data}
  catch(e){if(e?.name==='AbortError')throw new Error('업로드 시간이 초과되었습니다.');throw e}finally{clearTimeout(timer)}
}

async function refreshState(force=false){
  if(!APP.creds)return renderLauncherRequired();if(!force&&Date.now()<APP.ignoreRefreshUntil)return;
  // Explicit refreshes supersede a pending WebSocket debounce. Multiple refresh messages
  // are coalesced so a burst of edits does not download/render the full campaign repeatedly.
  if(APP.refreshTimer){clearTimeout(APP.refreshTimer);APP.refreshTimer=null}
  if(APP.refreshPromise){APP.refreshQueued=true;return APP.refreshPromise}
  const task=(async()=>{
    try{APP.state=await api(`/api/rooms/${encodeURIComponent(APP.creds.room)}/state`,{},6000);render();connectWS();}
    catch(e){
      const msg=String(e.message||'');
      if(e.status===404||msg.includes('캠페인을 찾을 수 없습니다')){clearCurrent();renderLauncherRequired('캠페인이 삭제되었거나 더 이상 존재하지 않습니다. EXE 런처에서 다시 접속해주세요.');toast('캠페인을 찾을 수 없어 저장된 재접속 정보를 정리했습니다.',4300);}
      else if(e.status===401||msg.includes('인증')){clearCurrent();renderLauncherRequired('접속 인증이 만료되었습니다. EXE 런처에서 다시 접속해주세요.');toast('접속 인증이 만료되었습니다.',3500);}
      else{toast(msg,3500);showGlobalError(msg)}
    }
  })();
  APP.refreshPromise=task;
  try{return await task}
  finally{
    APP.refreshPromise=null;
    if(APP.refreshQueued&&APP.creds){APP.refreshQueued=false;APP.refreshTimer=setTimeout(()=>{APP.refreshTimer=null;refreshState(true)},60)}
  }
}
function scheduleStateRefresh(){
  if(Date.now()<APP.ignoreRefreshUntil)return;clearTimeout(APP.refreshTimer);APP.refreshTimer=setTimeout(()=>{APP.refreshTimer=null;refreshState(true)},60);
}
function showGlobalError(msg){let x=$('#globalError');if(!x){document.body.insertAdjacentHTML('beforeend','<div id="globalError" class="global-error" role="alert"></div>');x=$('#globalError')}x.textContent=translateUiText(msg||'오류가 발생했습니다.');x.classList.add('on');clearTimeout(x._t);x._t=setTimeout(()=>x.classList.remove('on'),6500)}

function connectWS(){
  if(!APP.creds||(APP.ws&&(APP.ws.readyState===0||APP.ws.readyState===1)))return;
  const proto=location.protocol==='https:'?'wss':'ws',ws=new WebSocket(`${proto}://${location.host}/ws/${encodeURIComponent(APP.creds.room)}?token=${encodeURIComponent(APP.creds.token)}`);APP.ws=ws;
  ws.onopen=()=>{APP.connected=true;updateConnectionBadge();ws.send('ping')};
  ws.onclose=()=>{APP.connected=false;updateConnectionBadge();setTimeout(connectWS,1800)};ws.onerror=()=>{APP.connected=false;updateConnectionBadge()};
  ws.onmessage=ev=>{try{const m=JSON.parse(ev.data);if(m.type==='kicked'){clearCurrent();renderLauncherRequired('GM이 현재 접속을 종료했습니다. 다시 참가하려면 EXE 런처를 사용해주세요.');toast('GM이 접속을 종료했습니다.',3500);return}if(m.type==='deleted'){clearCurrent();renderLauncherRequired('GM이 캠페인을 삭제했습니다.');toast('캠페인이 삭제되어 재접속 정보를 정리했습니다.',3500);return}if(m.type==='server_stopping'){APP.connected=false;updateConnectionBadge();toast('호스트 서버가 종료됩니다.',3000);return}if(m.type.startsWith('dice_')){handleDiceEvent(m);return}if(m.type==='sound_bgm'){applyBgmState(m.state);updateSoundDrawerState(m.state);return}if(m.type==='sound_sfx'){playSfxEvent(m);return}if(m.type==='sound_mixer'){if(APP.state?.sound_state){APP.state.sound_state.bgm_volume=Number(m.bgm_volume);APP.state.sound_state.sfx_volume=Number(m.sfx_volume);APP.state.sound_state.volume=Number(m.bgm_volume)}const bg=$('#gmBgmVolume'),fx=$('#gmSfxVolume');if(bg&&!bg.matches(':active'))bg.value=String(m.bgm_volume);if(fx&&!fx.matches(':active'))fx.value=String(m.sfx_volume);applyBgmState(APP.state?.sound_state);return}if(m.type==='refresh')scheduleStateRefresh()}catch(e){console.error(e)}};
}
function updateConnectionBadge(){const d=$('#connDot');if(d)d.classList.toggle('on',APP.connected);const t=$('#connText');if(t)t.textContent=APP.connected?'실시간 연결':'재연결 중';}

function renderLauncherRequired(message=''){
  document.body.classList.remove('workspace-multi-active');
  appEl().innerHTML=`<div class="auth-wrap"><div class="hero"><div class="hero-head"><div class="hero-title-row"><h1>DUNGEON WORLD ONLINE <span class="alpha">${VERSION_LABEL}</span></h1>${languageButton()}</div><p>접속과 캠페인 선택은 Windows EXE 런처에서 관리합니다.</p></div><div class="hero-body single-mode"><section class="auth-card">${message?`<div class="notice bad">${esc(message)}</div>`:''}<h2>EXE 런처에서 게임을 열어주세요</h2><p>브라우저에는 영구 접속 토큰을 저장하지 않습니다. 런처가 안전한 일회성 티켓으로 이 화면을 엽니다.</p></section></div></div></div>`;
}
function renderAuth(opts={}){renderLauncherRequired(opts.error||'');}

async function loadHostCampaigns(){
  const root=$('#hostCampaigns');if(!root)return;root.innerHTML='<div class="notice">이 PC의 캠페인 목록을 불러오는 중…</div>';
  try{const x=await api('/api/local/campaigns',{},6000);root.innerHTML=x.campaigns?.length?`<h3>이 PC의 캠페인</h3><div class="recent-grid">${x.campaigns.map(c=>`<article class="recent-card"><div><b>${rawEsc(c.campaign_name)}</b><div class="small muted">GM ${rawEsc(c.gm_name)} · 플레이어 ${Number(c.player_count)||0}명 · <span class="roomcode small">${esc(c.code)}</span></div><div class="small muted">최근 저장 ${fmtTime(c.updated_at)}</div></div><div class="inline-actions"><button class="btn dark" data-local-resume="${attr(c.code)}" type="button">이어하기</button><button class="btn danger" data-local-delete="${attr(c.code)}" data-local-name="${attr(c.campaign_name)}" type="button">삭제</button></div></article>`).join('')}</div>`:'<div class="notice">저장된 캠페인이 없습니다. 아래에서 새 캠페인을 만들 수 있습니다.</div>';
    $$('[data-local-resume]',root).forEach(b=>b.addEventListener('click',()=>resumeLocalCampaign(b.dataset.localResume,b)));
    $$('[data-local-delete]',root).forEach(b=>b.addEventListener('click',()=>deleteLocalCampaign(b.dataset.localDelete,b.dataset.localName,b)));
  }catch(e){root.innerHTML=`<div class="notice bad">캠페인 목록을 불러오지 못했습니다.<br>${esc(e.message||'')}</div><button id="retryHostCampaigns" class="btn" type="button">다시 시도</button>`;$('#retryHostCampaigns')?.addEventListener('click',loadHostCampaigns);showGlobalError(e.message)}
}
async function deleteLocalCampaign(code,name,btn){if(!confirmUi(`'${name}' 캠페인을 영구 삭제할까요?\n캐릭터·로그·확장직업 데이터도 함께 삭제됩니다.`))return;if(btn)btn.disabled=true;try{await api(`/api/local/campaigns/${encodeURIComponent(code)}`,{method:'DELETE'},8000);await loadHostCampaigns();toast('캠페인을 삭제했습니다.')}catch(e){if(btn)btn.disabled=false;toast(e.message,3500);showGlobalError(e.message)}}
async function resumeLocalCampaign(code,btn){if(btn){btn.disabled=true;btn.textContent='연결 중…'}try{const r=await api(`/api/local/campaigns/${encodeURIComponent(code)}/resume`,{method:'POST'},8000);rememberCreds({room:r.room_code,token:r.gm_token,role:'gm'},{campaign_name:r.campaign_name});location.replace(`/?mode=play&room=${encodeURIComponent(r.room_code)}`)}catch(e){if(btn){btn.disabled=false;btn.textContent='이어하기'}toast(e.message,3500);showGlobalError(e.message)}}

function shell(inner,roleLabel,wide=false){
  const sess=APP.state.room.active_session,isGM=APP.state.me.role==='gm';
  return `<div class="app ${wide?'wide-app':''}"><header class="topbar"><div><span class="brand">${rawEsc(APP.state.room.campaign_name)}</span><span class="alpha">${VERSION_LABEL}</span></div><div class="topmeta"><span>방 <b class="roomcode">${esc(APP.state.room.code)}</b></span>${sess?`<span class="session-badge">세션 #${sess.session_no}</span>`:''}<span>${roleLabel}</span><span><i id="connDot" class="status-dot ${APP.connected?'on':''}"></i><span id="connText">${APP.connected?'실시간 연결':'재연결 중'}</span></span><button data-global-dice class="btn small dark" type="button">주사위 굴리기</button><button data-global-sound class="btn small" type="button">사운드</button>${isGM?'<button data-global-settings class="btn small" type="button">설정</button>':''}${languageButton()}<button data-top-action="${isGM?'server-stop':'client-leave'}" class="btn small ${isGM?'danger':''}" type="button">${isGM?'서버 종료':'접속 종료'}</button></div></header><div class="release-banner">v1.0.0 · 비공식 팬메이드 도구</div><main class="shell ${wide?'workspace-shell':''}">${inner}</main></div>`;
}
function render(){
  if(!APP.state)return renderAuth();
  if(!expansionsEnabled())document.querySelector('#expInviteModal')?.remove();
  if(APP.state.me.role==='gm')renderGM();
  else if(!APP.state.character?.state?.onboarding_complete)renderPlayerOnboarding();
  else {renderPlayer();setTimeout(maybeShowExpansionInvite,0)}
  updateConnectionBadge();syncLiveState();
}
async function handleTopAction(btn){
  if(btn.dataset.topAction==='client-leave'){clearCurrent();renderLauncherRequired('접속을 종료했습니다. 다시 들어오려면 EXE 런처의 최근 캠페인에서 접속하세요.');return;}
  if(btn.dataset.topAction!=='server-stop'||APP.state?.me?.role!=='gm')return;
  if(!confirmUi('호스트 서버를 종료하시겠습니까?\n접속 중인 플레이어의 연결도 종료됩니다. 캠페인 데이터는 삭제되지 않습니다.'))return;
  btn.disabled=true;btn.textContent='종료 중…';let success=false,err=null;
  try{await api(`/api/rooms/${encodeURIComponent(APP.creds.room)}/server-stop`,{method:'POST'},3200);success=true}catch(e){err=e;await new Promise(r=>setTimeout(r,700));try{await api('/api/ping',{},900)}catch{success=true}}
  if(success){clearCurrent();appEl().innerHTML=`<div class="auth-wrap"><div class="hero"><div class="hero-head"><h1>서버 종료 완료</h1><p>캠페인 데이터는 저장되어 있습니다. EXE 런처에서 다시 호스트를 시작하면 이어갈 수 있습니다.</p></div></div></div>`;return}
  btn.disabled=false;btn.textContent='서버 종료';toast(err?.message||'서버 종료 요청에 실패했습니다.',4000);showGlobalError(err?.message||'서버 종료 요청에 실패했습니다.')
}

function partyStrip(selectedCharId=null){
  return `<div class="party">${APP.state.party.map(p=>{const deciding=!p.onboarding_complete,pct=deciding?0:Math.max(0,Math.min(100,p.hp_current/(p.hp_max||1)*100));return `<div class="party-card ${p.character_id===selectedCharId?'me':''} ${deciding?'fate-pending':''}" data-party="${p.character_id}" tabindex="0"><div class="name">${rawEsc(p.character_name||p.display_name)}</div><div class="small">${p.class_name?recordEsc(p.class_name,classIsBuiltin(p.class_name)):esc('무직')} · ${p.race_name?recordEsc(p.race_name,raceIsBuiltin(p.race_name)):esc('없음')}${deciding?'':` · Lv.${p.level}`}</div>${deciding?'':`<div class="small">HP <b>${p.hp_current}/${p.hp_max}</b> · 장갑 ${p.armor} · ${esc(p.damage)}</div><div class="hpbar"><i style="width:${pct}%"></i></div>${(p.extensions||[]).map(x=>{const th=x.data?.theme||{};return `<span class="pill" style="border-color:${attr(th.accent||'#181818')}">${recordEsc(x.name,!!x.data?.builtin)}</span>`}).join('')}`}</div>`}).join('')}</div>`;
}

function attachPartyModal(){ $$('[data-party]').forEach(el=>{const open=()=>showPartyModal(Number(el.dataset.party));el.addEventListener('click',open);el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open()}})}); }
function showPartyModal(id){
  const p=currentSummary(id);if(!p)return;const deciding=!p.onboarding_complete,ex=(p.extensions||[]).map(x=>{const b=!!x.data?.builtin;return `<div class="notice${b?'':' no-i18n'}"><b>${recordEsc(x.name,b)}</b><br>${recordEsc(x.public_intro||'',b)}</div>`}).join('');
  const body=deciding?`<div class="fate-status-detail"><div class="fate-mark">?</div><h2>자신의 운명을 결정하는 중</h2><p>${rawEsc(p.character_name||p.display_name)}님은 아직 직업과 종족을 선택하지 않았습니다.</p><div class="metrics"><div class="metric">직업<div class="big">무직</div></div><div class="metric">종족<div class="big">없음</div></div></div></div>`:`<div class="metrics"><div class="metric">직업<div class="big">${recordEsc(p.class_name,classIsBuiltin(p.class_name))}</div></div><div class="metric">레벨<div class="big">${p.level}</div></div><div class="metric">HP<div class="big">${p.hp_current}/${p.hp_max}</div></div><div class="metric">장갑<div class="big">${p.armor}</div></div><div class="metric">피해<div class="big">${esc(p.damage)}</div></div><div class="metric">XP<div class="big">${p.xp}</div></div></div>${ex?`<h3>공개된 확장직업</h3>${ex}`:''}`;
  document.body.insertAdjacentHTML('beforeend',`<div class="modal" id="partyModal"><div class="modal-card"><div class="modal-head"><b>${rawEsc(p.character_name||p.display_name)}</b><button class="btn small" data-close type="button">${esc(translateUiText('닫기'))}</button></div><div class="modal-body">${body}</div></div></div>`);
  $('#partyModal [data-close]').addEventListener('click',()=>$('#partyModal').remove());$('#partyModal').addEventListener('click',e=>{if(e.target.id==='partyModal')e.currentTarget.remove()});
}


function onboardingChoices(){
  const names=Object.keys(APP.state.classes||{});if(!names.length)return {names,cls:'',race:'',races:[]};
  if(!APP.onboardingClass||!APP.state.classes[APP.onboardingClass])APP.onboardingClass=names[0];
  const c=APP.state.classes[APP.onboardingClass]||{},races=(c.races||[]).filter(x=>x?.name);
  if(!APP.onboardingRace||!races.some(x=>x.name===APP.onboardingRace))APP.onboardingRace=races[0]?.name||'';
  return {names,cls:APP.onboardingClass,race:APP.onboardingRace,races};
}
function onboardingMoveList(title,list=[],builtin=true){return `<section class="onboarding-read-section"><h3>${esc(title)}</h3>${list.length?list.map(m=>`<article class="onboarding-read-card${builtin?'':' no-i18n'}"><b>${recordEsc(m.name||'',builtin)}</b><div>${recordEsc(m.desc||'설명 없음',builtin)}</div></article>`).join(''):'<div class="small muted">등록된 내용이 없습니다.</div>'}</section>`}
function renderOnboardingClassView(className){
  const c=APP.state.classes[className]||{},builtin=classIsBuiltin(className),races=c.races||[],aligns=c.alignments||[];
  return `<div class="onboarding-summary-grid"><div><span>기본 HP</span><b>${Number(c.hp)||0}</b></div><div><span>기본 피해</span><b>${rawEsc(c.damage||'—')}</b></div><div><span>기본 하중</span><b>${Number(c.load)||0}</b></div></div><section class="onboarding-read-section"><h3>사용 가능한 종족</h3><div class="readonly-race-grid">${races.map(r=>{const rb=r._builtin!==undefined?!!r._builtin:raceIsBuiltin(r.name);return `<article class="readonly-race-card${rb?'':' no-i18n'}"><div class="readonly-race-name">${recordEsc(r.name,rb)}</div><div class="readonly-race-desc">${recordEsc(r.desc||'설명 없음',rb)}</div></article>`}).join('')||'<div class="notice">사용 가능한 종족이 없습니다.</div>'}</div></section><section class="onboarding-read-section"><h3>가치관</h3>${aligns.map(a=>`<article class="onboarding-read-card${builtin?'':' no-i18n'}"><b>${recordEsc(a.name,builtin)}</b><div>${recordEsc(a.desc||'',builtin)}</div></article>`).join('')||'<div class="small muted">등록된 가치관이 없습니다.</div>'}</section><section class="onboarding-read-section"><h3>인연 예시</h3>${(c.bonds||[]).map(x=>`<div class="onboarding-line${builtin?'':' no-i18n'}">${recordEsc(x,builtin)}</div>`).join('')||'<div class="small muted">등록된 인연이 없습니다.</div>'}</section>${onboardingMoveList('직업 시작 행동',c.start||[],builtin)}${onboardingMoveList('고급 행동 2–5',c.a25||[],builtin)}${onboardingMoveList('고급 행동 6–10',c.a610||[],builtin)}`;
}
function renderOnboardingSpellView(className,raceName=''){
  const ctx=raceSpellContext({class_name:className,race_name:raceName}),spells=[...ctx.all],special=[...ctx.special];
  if(!spells.length&&!special.length)return '<div class="fate-empty"><b>이 직업에는 주문이 정의되어 있지 않습니다.</b><span>직업 설명을 살펴본 뒤 다른 직업도 비교해보세요.</span></div>';
  const levelOrder=x=>spellEffectiveLevel(x.level);spells.sort((a,b)=>levelOrder(a)-levelOrder(b)||String(a.name).localeCompare(String(b.name),'ko'));
  const raceBuiltin=raceIsBuiltin(raceName);
  const cards=spells.map(sp=>{const sb=spellIsBuiltin(sp);return `<article class="onboarding-spell-card${sb?'':' no-i18n'}"><div class="onboarding-spell-title"><b>${recordEsc(sp.name,sb)}</b><span>${recordEsc(spellLevelLabel(sp.level),sb)}</span></div><div>${recordEsc(sp.desc||'설명 없음',sb)}</div>${sp.race_modified?`<div class="small muted">${recordEsc(raceName,raceBuiltin)} 특성 · ${recordEsc(spellLevelLabel(sp.original_level),sb)} → ${recordEsc(spellLevelLabel(sp.level),sb)}</div>`:''}</article>`});
  const extra=special.map(sp=>{const sb=spellIsBuiltin(sp);return `<article class="onboarding-spell-card${sb?'':' no-i18n'}"><div class="onboarding-spell-title"><b>${recordEsc(sp.name,sb)}</b><span>${recordEsc(spellLevelLabel(sp.level),sb)}</span></div><div>${recordEsc(sp.desc||'설명 없음',sb)}</div><div class="small muted">${recordEsc(raceName,raceBuiltin)} 특성으로 자동 습득</div></article>`});
  return `<div class="onboarding-spell-list">${cards.join('')}${extra.join('')}</div>`;
}
function selectedOnboardingRaceDesc(cls,race){const c=APP.state.classes?.[cls]||{},item=(c.races||[]).find(x=>x.name===race);return item?.desc||''}
function selectedOnboardingRaceItem(cls,race){const c=APP.state.classes?.[cls]||{};return (c.races||[]).find(x=>x.name===race)||null}
function renderPlayerOnboarding(){
  document.body.classList.remove('workspace-multi-active');const q=onboardingChoices(),me=APP.state.character?.state?.profile?.name||APP.state.me.name,clsBuiltin=classIsBuiltin(q.cls),raceItem=selectedOnboardingRaceItem(q.cls,q.race),raceBuiltin=raceItem?((raceItem._builtin!==undefined)?!!raceItem._builtin:raceIsBuiltin(raceItem.name)):raceIsBuiltin(q.race);
  appEl().innerHTML=shell(`<div class="fate-intro"><b>${rawEsc(me)}</b><span>아직 직업과 종족이 정해지지 않았습니다. 자료를 살펴보고 자신의 운명을 선택하세요.</span></div><div class="fate-workspace"><section class="fate-window fate-choice-window"><div class="fate-window-head"><b>운명 선택</b><span>선택용</span></div><div class="fate-window-body"><label class="field"><span>직업</span><select id="fateClass" class="select">${q.names.map(n=>`<option value="${attr(n)}" ${n===q.cls?'selected':''}>${recordEsc(n,classIsBuiltin(n))}</option>`).join('')}</select></label><label class="field"><span>종족</span><select id="fateRace" class="select">${q.races.map(r=>{const b=r._builtin!==undefined?!!r._builtin:raceIsBuiltin(r.name);return `<option value="${attr(r.name)}" ${r.name===q.race?'selected':''}>${recordEsc(r.name,b)}</option>`}).join('')}</select></label><div id="fateRaceDesc" class="notice fate-race-desc${raceBuiltin?'':' no-i18n'}">${raceItem?recordEsc(raceItem.desc||'설명 없음',raceBuiltin):esc('선택한 종족의 설명이 여기에 표시됩니다.')}</div><div class="notice warn">적용한 뒤에는 일반 플레이 화면으로 넘어갑니다. 이후 직업/종족 변경은 GM에게 요청하세요.</div><button id="finishFate" class="btn dark large full" type="button" ${q.cls&&q.race?'':'disabled'}>이 운명을 선택한다</button></div></section><section class="fate-window fate-class-window"><div class="fate-window-head"><b id="fateClassTitle">직업 · ${q.cls?recordEsc(q.cls,clsBuiltin):esc('없음')}</b><span>보기 전용</span></div><div id="fateClassView" class="fate-window-body scroll-body">${renderOnboardingClassView(q.cls)}</div></section><section class="fate-window fate-spell-window"><div class="fate-window-head"><b id="fateSpellTitle">주문 · ${q.cls?recordEsc(q.cls,clsBuiltin):esc('없음')}</b><span>보기 전용</span></div><div id="fateSpellView" class="fate-window-body scroll-body">${renderOnboardingSpellView(q.cls,q.race)}</div></section></div>`,`PLAYER · ${rawEsc(APP.state.me.name)}`);
  attachPlayerOnboarding();
}
function attachPlayerOnboarding(){
  const update=()=>{const q=onboardingChoices(),race=$('#fateRace'),item=selectedOnboardingRaceItem(q.cls,q.race),rb=item?((item._builtin!==undefined)?!!item._builtin:raceIsBuiltin(item.name)):raceIsBuiltin(q.race);if(race){race.innerHTML=q.races.map(r=>{const b=r._builtin!==undefined?!!r._builtin:raceIsBuiltin(r.name);return `<option value="${attr(r.name)}" ${r.name===q.race?'selected':''}>${recordEsc(r.name,b)}</option>`}).join('');race.disabled=!q.races.length}const d=$('#fateRaceDesc');if(d){d.textContent=item?contentValue(item.desc||'설명 없음',rb):translateUiText('선택한 종족의 설명이 여기에 표시됩니다.');d.classList.toggle('no-i18n',!rb&&!!item)}const ct=$('#fateClassTitle');if(ct)ct.textContent=`${APP.language==='en'?'Class':'직업'} · ${q.cls?contentValue(q.cls,classIsBuiltin(q.cls)):(APP.language==='en'?'None':'없음')}`;const cv=$('#fateClassView');if(cv)cv.innerHTML=renderOnboardingClassView(q.cls);const st=$('#fateSpellTitle');if(st)st.textContent=`${APP.language==='en'?'Spells':'주문'} · ${q.cls?contentValue(q.cls,classIsBuiltin(q.cls)):(APP.language==='en'?'None':'없음')}`;const sv=$('#fateSpellView');if(sv)sv.innerHTML=renderOnboardingSpellView(q.cls,q.race);const done=$('#finishFate');if(done)done.disabled=!(q.cls&&q.race)};
  $('#fateClass')?.addEventListener('change',e=>{APP.onboardingClass=e.target.value;APP.onboardingRace=null;update()});$('#fateRace')?.addEventListener('change',e=>{APP.onboardingRace=e.target.value;update()});
  $('#finishFate')?.addEventListener('click',async e=>{const q=onboardingChoices();if(!q.cls||!q.race)return toast('직업과 종족을 선택하세요.');const cls=contentValue(q.cls,classIsBuiltin(q.cls)),race=contentValue(q.race,raceIsBuiltin(q.race));if(!confirmUi(`${cls} · ${race}\n이 선택으로 캐릭터를 시작할까요?\n이후 직업/종족 변경은 GM에게 요청해야 합니다.`))return;e.currentTarget.disabled=true;e.currentTarget.textContent='운명을 정하는 중…';try{await api(`/api/rooms/${encodeURIComponent(APP.creds.room)}/characters/${APP.state.character.character_id}/onboarding`,{method:'POST',body:JSON.stringify({class_name:q.cls,race_name:q.race})},8000);APP.onboardingClass=null;APP.onboardingRace=null;await refreshState(true);toast('운명을 선택했습니다. 캐릭터 시트를 시작합니다.')}catch(err){e.currentTarget.disabled=false;e.currentTarget.textContent='이 운명을 선택한다';toast(err.message,4000)}});
}

function myCharacterBundle(){ return {id:APP.state.character.character_id,state:APP.state.character.state,summary:currentSummary(APP.state.character.character_id)}; }
function gmCharacterBundle(id){ const r=APP.state.characters.find(c=>c.character_id===id);return r?{id:r.character_id,state:r.state,summary:currentSummary(r.character_id)}:null; }
function playerTabsFor(bundle){
  const tabs=[{id:'character',label:'캐릭터'},{id:'inventory',label:'인벤토리'},{id:'advanced',label:'고급/추가 행동'}],s=bundle.state,race=APP.state.races?.[s.race_name]||{},raceEffects=(race.spell_effects?.[s.class_name]||[]).some(Boolean);
  const hasAddedSpellAccess=(s.extra_spells||[]).length>0||activeMoveEffects(s).some(x=>['class_access','spell_grant','spell_level_reduce','spell_zero'].includes(x.effect?.kind)),primarySpellAccess=spellcastingProfile(s.class_name).enabled&&(APP.state.spells[s.class_name]||[]).length>0;
  if(primarySpellAccess||raceEffects||hasAddedSpellAccess)tabs.push({id:'spells',label:'주문'});
  if(APP.state.me?.role==='player')tabs.push({id:'catalog',label:'도감'});
  tabs.push({id:'memo',label:'메모'});
  (bundle.summary?.extensions||[]).forEach(x=>tabs.push({id:`ext:${x.grant_id}`,label:x.name,builtin:!!x.data?.builtin,theme:x.data?.theme||{}}));return tabs;
}
function tabButton(t){const th=t.theme||{},style=t.id.startsWith('ext:')?`style="--tab-bg:${attr(th.background||'#fff')};--tab-text:${attr(th.text||'#181818')};--tab-accent:${attr(th.accent||'#181818')}"`:'';return `<button type="button" ${style} data-ptab="${attr(t.id)}" class="${APP.playerTab===t.id?'active':''} ${t.id.startsWith('ext:')?'ext-tab':''}">${t.id.startsWith('ext:')?recordEsc(t.label,!!t.builtin):esc(t.label)}</button>`;}
function desktopWorkspace(){return window.matchMedia('(min-width: 901px)').matches;}
function renderPlayer(){
  const b=myCharacterBundle(),tabs=playerTabsFor(b);if(!tabs.some(t=>t.id===APP.playerTab))APP.playerTab='character';
  if(desktopWorkspace()){
    const layout=getWorkspace(b,false),wide=layout.mode==='multi';
    appEl().innerHTML=shell(`${partyStrip(b.id)}${renderWorkspace(b,false)}`,`PLAYER · ${rawEsc(APP.state.me.name)}`,wide);
    attachPartyModal();attachWorkspace(b,false);attachPlayerPage(b,false);return;
  }
  appEl().innerHTML=shell(`${partyStrip(b.id)}<div class="nav">${tabs.map(tabButton).join('')}</div><div id="playerBoard">${renderPlayerPage(b,false)}</div>`,`PLAYER · ${rawEsc(APP.state.me.name)}`);
  attachPartyModal();$$('[data-ptab]').forEach(x=>x.addEventListener('click',()=>{APP.playerTab=x.dataset.ptab;renderPlayer()}));attachPlayerPage(b,false);
}
function renderPlayerPageById(bundle,gmMode,t){if(t==='character')return renderCharacterPage(bundle,gmMode);if(t==='inventory')return renderInventoryPage(bundle,gmMode);if(t==='advanced')return renderAdvancedPage(bundle,gmMode);if(t==='spells')return renderSpellPage(bundle,gmMode);if(t==='catalog')return renderMonsterCatalog();if(t==='memo')return renderMemoPage(bundle);if(t.startsWith('ext:'))return renderExtensionPage(bundle,Number(t.split(':')[1]),gmMode);return '';}

function renderPlayerPage(bundle,gmMode){return renderPlayerPageById(bundle,gmMode,APP.playerTab);}
function workspaceKey(bundle,gmMode){return `${WORKSPACE_PREFIX}${APP.creds.room}_${bundle.id}_${gmMode?'gm':'player'}`;}
function defaultWorkspace(tabs,preset='default'){
  const W=Math.max(620,window.innerWidth-28),H=Math.max(420,window.innerHeight-170),windows={};
  tabs.forEach((t,i)=>windows[t.id]={open:false,x:24+i*24,y:20+i*22,w:Math.min(760,W-60),h:Math.min(720,H-40),z:i+1,max:false});
  const has=id=>windows[id];
  if(preset==='combat'){if(has('character'))Object.assign(windows.character,{open:true,x:14,y:14,w:Math.round(W*.52),h:H-28,z:2});if(has('advanced'))Object.assign(windows.advanced,{open:true,x:Math.round(W*.53),y:14,w:Math.round(W*.46)-16,h:H-28,z:3})}
  else if(preset==='explore'){if(has('character'))Object.assign(windows.character,{open:true,x:14,y:14,w:Math.round(W*.58),h:H-28,z:2});if(has('memo'))Object.assign(windows.memo,{open:true,x:Math.round(W*.59),y:14,w:Math.round(W*.40)-16,h:H-28,z:3})}
  else {if(has('character'))Object.assign(windows.character,{open:true,x:14,y:14,w:Math.round(W*.56),h:H-28,z:2});if(has('advanced'))Object.assign(windows.advanced,{open:true,x:Math.round(W*.57),y:14,w:Math.round(W*.42)-16,h:H-28,z:3})}
  return {mode:'single',active:'character',locked:false,windows};
}
function getWorkspace(bundle,gmMode){
  const key=workspaceKey(bundle,gmMode),tabs=playerTabsFor(bundle),ids=new Set(tabs.map(t=>t.id));
  // Keep one live object per workspace. Re-reading localStorage during a click/drag used to
  // replace the object being edited, which made '기본 화면' and '배치 고정' appear broken.
  let x=APP.workspaceLayouts[key]||null;
  if(!x){try{x=JSON.parse(localStorage.getItem(key)||'null')}catch{x=null}}
  if(!x||!x.windows)x=defaultWorkspace(tabs);
  const def=defaultWorkspace(tabs);
  for(const t of tabs){
    if(!x.windows[t.id])x.windows[t.id]=def.windows[t.id];
    const w=x.windows[t.id],d=def.windows[t.id];
    for(const k of ['x','y','w','h','z'])if(!Number.isFinite(Number(w[k])))w[k]=d[k];
    w.w=Math.max(360,Number(w.w)||d.w);w.h=Math.max(260,Number(w.h)||d.h);w.x=Math.max(0,Number(w.x)||0);w.y=Math.max(0,Number(w.y)||0);w.open=!!w.open;w.max=!!w.max;
  }
  Object.keys(x.windows).forEach(id=>{if(!ids.has(id))delete x.windows[id]});
  x.mode=x.mode==='multi'?'multi':'single';x.active=ids.has(x.active)?x.active:(ids.has('character')?'character':tabs[0]?.id||'');x.locked=!!x.locked;delete x.snap;
  if(x.mode==='multi'&&!Object.values(x.windows).some(w=>w?.open)){
    const id=ids.has(x.active)?x.active:(ids.has('character')?'character':tabs[0]?.id);if(id&&x.windows[id])x.windows[id].open=true;
  }
  APP.workspaceLayouts[key]=x;return x
}
function saveWorkspace(bundle,gmMode){const key=workspaceKey(bundle,gmMode),x=APP.workspaceLayouts[key];if(x)localStorage.setItem(key,JSON.stringify(x))}
function rerenderCharacterContext(gmMode){if(gmMode)renderGM();else renderPlayer()}

function captureWorkspaceGeometry(bundle,gmMode,layout=null){layout=layout||getWorkspace(bundle,gmMode);const canvas=$('.workspace-canvas');if(!canvas)return layout;const cr=canvas.getBoundingClientRect();$$('.dw-window',canvas).forEach(el=>{const id=el.dataset.windowId,w=layout.windows[id],r=el.getBoundingClientRect();if(!w)return;w.x=Math.max(0,Math.round(r.left-cr.left));w.y=Math.max(0,Math.round(r.top-cr.top));w.w=Math.max(360,Math.round(r.width));w.h=Math.max(260,Math.round(r.height))});return layout}
function normalizeWorkspaceZ(layout){const ordered=Object.values(layout.windows||{}).filter(w=>w&&w.open).sort((a,b)=>(Number(a.z)||0)-(Number(b.z)||0));ordered.forEach((w,i)=>{w.z=10+i})}

function statGrowthInfo(s,rules){
  const keys=Object.keys(STAT_META),vals=keys.map(k=>Number(s.stats?.[k])||0),base=(rules.stat_start||[16,15,13,12,9,8]).map(Number),assigned=vals.every(v=>v>0),baseTotal=base.reduce((a,b)=>a+b,0),total=vals.reduce((a,b)=>a+b,0);
  const remaining=[...base];for(const v of vals){const i=remaining.indexOf(v);if(i>=0)remaining.splice(i,1)}
  const tracked=s.stat_growth_spent===null||s.stat_growth_spent===undefined?null:Number(s.stat_growth_spent),used=assigned?(Number.isFinite(tracked)?Math.max(0,tracked):Math.max(0,total-baseTotal)):0,totalPts=Math.max(0,(Number(s.level)||1)-1)+(Number(s.bonus_stat_points)||0),remain=totalPts-used;
  const bs=[...base].sort((a,b)=>a-b),vs=[...vals].sort((a,b)=>a-b),growthShape=assigned&&vs.every((v,i)=>v>=bs[i]);
  return {assigned,used,totalPts,remain,growthShape,baseTotal,remaining};
}
function stepper(value,attrs='',small=false){return `<div class="stepper ${small?'small-stepper':''}"><button type="button" data-step="-1" ${attrs}>−</button><input ${attrs} value="${Number(value)||0}" inputmode="numeric"><button type="button" data-step="1" ${attrs}>＋</button></div>`;}
function renderCharacterPage(bundle,gmMode){
  const s=bundle.state,c=classData(s),classBuiltin=classIsBuiltin(s.class_name),rules=APP.state.room.rules,races=c.races||[],aligns=c.alignments||[],selectedRace=races.find(r=>r.name===s.race_name)||{},raceBuiltin=selectedRace._builtin!==undefined?!!selectedRace._builtin:raceIsBuiltin(s.race_name),stats=s.stats||{},max=hpMax(s),maxLoad=(Number(c.load)||0)+statMod(stats.str),currentLoad=inventoryWeight(s),loadInfo=inventoryLoadInfo(s),g=statGrowthInfo(s,rules),xpNeed=xpRequiredFor(s,bundle),currencyName=currencyDisplayName(rules.currency_name||'닢'),reserve=Number(s.reserve)||0,reserveMax=Math.max(0,Number(rules.reserve_max)||0);
  const hp=Number(s.hp_current)||0,xp=Number(s.xp)||0,hpPct=Math.max(0,Math.min(100,hp/Math.max(1,max)*100)),xpMax=Number(s.level)>=Number(rules.level_max)?Math.max(1,xp):xpNeed,xpPct=Math.max(0,Math.min(100,xp/Math.max(1,xpMax)*100));
  let statMsg;if(!g.assigned)statMsg=`<div class="notice stat-assignment"><b>초기 능력치 배분</b><span>사용할 값: ${(rules.stat_start||[]).join(' · ')}</span><span>남은 값: <b>${g.remaining.length?g.remaining.join(' · '):'없음'}</b></span></div>`;else if(!g.growthShape)statMsg=`<div class="notice bad">기본 능력치 배분을 확인하세요: ${(rules.stat_start||[]).join(', ')}</div>`;else if(g.remain<0)statMsg=`<div class="notice bad">현재 능력치 합계가 성장 포인트를 ${Math.abs(g.remain)}점 초과합니다.</div>`;else statMsg=`<div class="notice good">능력치 성장 · 사용 ${g.used} / 총 ${g.totalPts} · <b>남음 ${g.remain}</b></div>`;
  const statCards=Object.entries(STAT_META).map(([k,[name,abbr,desc]])=>{const v=Number(stats[k])||0,lo=Number(rules.stat_min??3),hi=Number(rules.stat_max??18),canGrow=!g.assigned||gmMode||(g.remain>0&&v<hi),minusDisabled=g.assigned&&v<=lo?'disabled':'',plusDisabled=canGrow?'':'disabled',statTip=APP.language==='en'?`${translateUiText(desc)} Current score: ${v}; modifier: ${modText(v)}. Campaign range: ${lo}–${hi}.`:`${desc} 현재 점수 ${v}, 수정치 ${modText(v)} · 캠페인 범위 ${lo}~${hi}`;return `<article class="summary-stat"><div class="summary-stat-top"><span>${esc(name)}</span>${infoTip(statTip)}</div><div class="summary-stat-controls"><button type="button" data-stat-step="${k}" data-delta="-1" ${minusDisabled}>−</button><input data-stat="${k}" inputmode="numeric" min="${lo}" max="${hi}" value="${v}"><button type="button" data-stat-step="${k}" data-delta="1" ${plusDisabled}>＋</button></div><b class="summary-mod ${statMod(v)<0?'neg':''}">${modText(v)}</b><small>${abbr}</small></article>`}).join('');
  const dice=['D4','D6','D8','D10','D12'];const curDie=String(s.damage_die||c.damage||'D6').toUpperCase();if(!dice.includes(curDie))dice.push(curDie);
  const bondRows=(s.bonds||[]).map((b,i)=>`<textarea class="textarea bond-textarea player-bond-free" rows="2" data-bond="${i}" placeholder="인연 내용을 자유롭게 적으세요.">${rawEsc(typeof b==='string'?b:(b?.desc||b?.text||''))}</textarea>`).join('');
  return `<div class="character-page">
    <section class="character-summary-card">
      <div class="character-hero-row"><div class="character-identity"><input class="hero-name-input" data-prof="name" ${gmMode?'':'disabled'} value="${attr(s.profile?.name||'')}" placeholder="캐릭터 이름"><div class="identity-line"><select id="charClass" class="hero-select" ${gmMode?'':'disabled'}>${Object.keys(APP.state.classes).map(n=>`<option ${n===s.class_name?'selected':''}>${recordEsc(n,classIsBuiltin(n))}</option>`).join('')}</select><span>·</span><select id="charRace" class="hero-select" ${gmMode?'':'disabled'}>${races.map(r=>{const b=r._builtin!==undefined?!!r._builtin:raceIsBuiltin(r.name);return `<option ${r.name===s.race_name?'selected':''}>${recordEsc(r.name,b)}</option>`}).join('')}</select><span>·</span><b>${s.alignment_name?recordEsc(s.alignment_name,classBuiltin):esc('가치관')}</b></div><input class="hero-sub-input" data-prof="personality" value="${attr(s.profile?.personality||'')}" placeholder="성격 / 외모 / 인상"></div><div class="character-hero-actions"><button class="btn small summary-view-btn" data-character-summary type="button">요약 보기</button><label class="level-chip"><span>레벨</span><input data-num="level" type="number" min="1" max="${rules.level_max}" value="${Number(s.level)||1}"></label></div></div>
      <div class="summary-stats">${statCards}</div>
      <div class="summary-vitals">
        <div class="vital-block"><div class="vital-head"><b>HP</b><span data-vital-label="hp_current">${hp} / ${max}</span></div><div class="vital-slider-wrap"><div class="vital-bar"><i data-vital-fill="hp_current" style="width:${hpPct}%"></i></div><input class="vital-range" data-vital-range="hp_current" type="range" min="0" max="${max}" step="1" value="${hp}"></div></div>
        <div class="vital-block"><div class="vital-head"><b>XP</b><span data-vital-label="xp">${xp} / ${Number(s.level)>=Number(rules.level_max)?'MAX':xpNeed}${Number(s.level)<Number(rules.level_max)&&xp>=xpNeed?` · ${translateUiText('레벨업 가능')}`:''}</span></div><div class="vital-slider-wrap"><div class="vital-bar xp"><i data-vital-fill="xp" style="width:${xpPct}%"></i></div><input class="vital-range" data-vital-range="xp" type="range" min="0" max="${Math.max(1,xpMax)}" step="1" value="${Math.min(xp,Math.max(1,xpMax))}"></div></div>
      </div>
      <div class="summary-combat">
        <article class="summary-metric"><span>장갑 ${infoTip('장갑은 받는 피해를 줄이는 수치입니다. 기본 장갑은 참고값이고 현재 장갑은 직접 수정할 수 있습니다.')}</span><div class="metric-inline">${stepper(s.armor,'data-num="armor"',true)}</div><small>기본 장갑 <input class="mini-input" data-num="armor_base" type="number" min="0" value="${Number(s.armor_base)||0}"></small></article>
        <article class="summary-metric"><span>피해 ${infoTip(`직업 기본 피해는 ${c.damage||'없음'}입니다.`)}</span><select class="hero-damage" id="damageDie">${dice.map(d=>`<option ${d===curDie?'selected':''}>${d}</option>`).join('')}</select><div class="damage-mini"><span>추가</span>${stepper(s.damage_bonus,'data-damage-bonus="1"',true)}</div><small>현재 ${esc(damageText(s))}</small></article>
        <article class="summary-metric"><span>하중</span><b>${formatWeight(currentLoad)} / ${formatWeight(maxLoad)}</b><small>${esc(loadInfo.short)}</small></article>
        <article class="summary-metric reserve-metric"><span>예비 ${infoTip('예비는 행동에서 얻어 그 행동이 정한 용도로 소비합니다. 이 칸은 세션 중 현재 예비를 빠르게 기록하는 공용 트래커입니다.')}</span><input class="reserve-input metric-value-input" data-num="reserve" type="number" min="0" ${reserveMax>0?`max="${reserveMax}"`:''} value="${reserve}" aria-label="예비"><small>${reserveMax>0?`최대 ${reserveMax}`:'최대 제한 없음'}</small></article>
        <article class="summary-metric currency-metric"><span class="no-i18n">${rawEsc(currencyName)}</span><input class="currency-input metric-value-input" data-num="currency" type="number" min="0" value="${Number(s.currency)||0}" aria-label="${attr(currencyName)}"><small>캠페인 재화</small></article>
      </div>
      <div class="growth-strip"><div><span>레벨 성장</span><b>${g.used} / ${g.totalPts}</b></div><div><span>남은 포인트</span><b class="${g.remain<0?'danger-text':''}">${g.remain}</b></div>${gmMode?`<label><span>GM 추가 포인트</span><input class="input mini-input" data-num="bonus_stat_points" type="number" value="${Number(s.bonus_stat_points)||0}"></label>`:''}</div>${statMsg}
    </section>
    <div class="grid two character-detail-grid">
      <div class="grid"><section class="panel"><div class="head">인물 정보</div><div class="body"><div class="profile-grid compact-profile"><label class="field"><span>성별</span><input class="input" data-prof="gender" value="${attr(s.profile?.gender||'')}"></label><label class="field"><span>나이</span><input class="input" data-prof="age" value="${attr(s.profile?.age||'')}"></label><label class="field" style="grid-column:span 2"><span>키 / 몸무게</span><input class="input" data-prof="body" value="${attr(s.profile?.body||'')}"></label></div></div></section><section class="panel"><div class="head">종족 특성</div><div class="body"><div class="notice${raceBuiltin?'':' no-i18n'}">${recordEsc(selectedRace.desc||'',raceBuiltin)}</div></div></section><section class="panel"><div class="head">가치관</div><div class="body">${aligns.map(a=>`<label class="choice${classBuiltin?'':' no-i18n'}"><input type="radio" name="alignment" value="${attr(a.name)}" ${a.name===s.alignment_name?'checked':''}><span><b>${recordEsc(a.name,classBuiltin)}</b><div class="small">${recordEsc(a.desc,classBuiltin)}</div></span></label>`).join('')}</div></section><section class="panel"><div class="head">인연</div><div class="body bond-list">${bondRows}</div></section></div>
      <div class="grid"><details class="panel move-section" open><summary class="head section-summary">직업 행동 <span class="small">${recordEsc(s.class_name,classIsBuiltin(s.class_name))} 시작 행동 전체</span></summary><div class="body moves">${(c.start||[]).map(m=>moveDetail(m,classIsBuiltin(s.class_name))).join('')}</div></details><details class="panel move-section" open><summary class="head section-summary">핵심 행동 <span class="small">모든 캐릭터가 보유</span></summary><div class="body moves">${(APP.state.core_moves||[]).map(m=>moveDetail(m,coreMoveIsBuiltin(m))).join('')}</div></details></div>
    </div>${gmMode?'<div class="notice warn">GM 편집 모드: 일반 플레이어의 제한을 넘겨 저장할 수 있습니다.</div>':''}
  </div>`;
}
function moveRelationBadges(m,builtin=true){const out=[];if(m?.has_requirement&&String(m.requires_move||'').trim())out.push(`<span class="pill requirement-pill">필요 · ${recordEsc(String(m.requires_move).trim(),builtin)}</span>`);const text=String(m?.desc||''),hit=text.match(/(?:^|\n)\s*(?:대체|Replaces)\s*[:：]\s*([^\n]+)/i);if(hit?.[1])out.push(`<span class="pill replace-pill">대체 · ${recordEsc(hit[1].trim(),builtin)}</span>`);return out.join('')}
function moveDetail(m,builtin=true){const badges=moveRelationBadges(m,builtin);return `<details class="move-details${builtin?'':' no-i18n'}"><summary><span>${recordEsc(m.name,builtin)}</span>${badges?`<span class="move-summary-badges">${badges}</span>`:''}</summary><div class="move-desc">${recordEsc(m.desc||'',builtin)}</div></details>`;}

function multiclassChoices(source,level){
  const c=APP.state.classes[source]||{},effective=Math.max(1,(Number(level)||1)-1),out=[],bundled=new Set();
  for(const bundle of (c.multiclass_bundles||[])){
    const names=(bundle.moves||[]).filter(Boolean),moves=names.map(n=>(c.start||[]).find(m=>m.name===n)).filter(Boolean);
    if(moves.length){
      moves.forEach(m=>bundled.add(m.name));
      out.push({
        name:bundle.name||`${source} 시작 행동 묶음`,
        bundle:true,
        min_level:1,
        desc:moves.map(m=>`${m.name}\n${m.desc||''}`).join('\n\n'),
        bundle_moves:moves.map(m=>m.name),
        rule_note:'서로 의존하는 시작 행동을 하나의 선택으로 취급'
      });
    }
  }
  if(effective>=1)(c.start||[]).filter(m=>!bundled.has(m.name)).forEach(m=>out.push({...m,bundle:false,min_level:1}));
  if(effective>=2)(c.a25||[]).forEach(m=>out.push({...m,bundle:false,min_level:2}));
  if(effective>=6)(c.a610||[]).forEach(m=>out.push({...m,bundle:false,min_level:6}));
  return out;
}


function moveEffectKey(move,effect,index=0){return String(effect?.id||`${move?.name||'move'}:${effect?.kind||'effect'}:${index}`)}
function extraMoveDefinitions(state){
  const out=[];
  for(const item of (state.extra_moves||[])){
    const source=String(item?.source_class||''),c=APP.state.classes?.[source];if(!c)continue;
    if(item?.bundle){
      const bundle=(c.multiclass_bundles||[]).find(b=>String(b?.name||'')===String(item.name||''));
      for(const name of (bundle?.moves||[])){const move=(c.start||[]).find(m=>m.name===name);if(move)out.push({move,source_class:source,origin:item})}
      continue;
    }
    const move=[...(c.start||[]),...(c.a25||[]),...(c.a610||[])].find(m=>m.name===item.name);if(move)out.push({move,source_class:source,origin:item});
  }
  return out;
}
function activeMoveEffects(state){
  const c=classData(state),owned=new Set(state.advanced_moves||[]),out=[],seen=new Set();
  const add=(move,sourceClass=state.class_name,origin=null)=>{if(!move)return;const identity=`${sourceClass}::${move.name}`;if(seen.has(identity))return;seen.add(identity);(move.move_effects||[]).forEach((effect,index)=>out.push({move,effect,index,key:moveEffectKey(move,effect,index),source_class:sourceClass,origin}))};
  for(const move of (c.start||[]))add(move,state.class_name,null);
  for(const move of [...(c.a25||[]),...(c.a610||[])])if(owned.has(move.name))add(move,state.class_name,null);
  for(const row of extraMoveDefinitions(state))add(row.move,row.source_class,row.origin);
  return out;
}
function moveChoice(state,key){return (state.move_choices||{})[key]||{}}
function classifiedSpellPool(){
  const out=[];for(const [source,list] of Object.entries(APP.state.spells||{})){if(source==='__undefined__')continue;for(const sp of (list||[]))out.push({...sp,source_class:source})}return out;
}
function spellById(id){const sid=Number(id)||0;if(!sid)return null;return classifiedSpellPool().find(sp=>Number(sp.id)===sid)||null}
function moveEffectSpellOptions(state,row){
  const e=row.effect||{},choice=moveChoice(state,row.key),currentId=Number(choice.spell_id)||0;let list=[];
  if(e.kind==='spell_level_reduce')list=(APP.state.spells?.[state.class_name]||[]).filter(sp=>spellEffectiveLevel(sp.level)>0).map(sp=>({...sp,source_class:state.class_name}));
  else if(e.kind==='spell_grant'){
    const source=String(e.source_class||'');
    if(e.all_classes||source==='*')list=classifiedSpellPool();
    else {const cls=source||state.class_name;list=(APP.state.spells?.[cls]||[]).map(sp=>({...sp,source_class:cls}));}
  }
  if(e.choice_group){const used=new Set(activeMoveEffects(state).filter(x=>x.key!==row.key&&x.effect?.choice_group===e.choice_group).map(x=>Number(moveChoice(state,x.key).spell_id)||0).filter(Boolean));list=list.filter(sp=>Number(sp.id)===currentId||!used.has(Number(sp.id)))}
  return list;
}
function classMoveChoicesAt(source,level){
  const c=APP.state.classes[source]||{},effective=Math.max(1,Number(level)||1),out=[],bundled=new Set();
  for(const bundle of (c.multiclass_bundles||[])){const names=(bundle.moves||[]).filter(Boolean),moves=names.map(n=>(c.start||[]).find(m=>m.name===n)).filter(Boolean);if(!moves.length)continue;moves.forEach(m=>bundled.add(m.name));out.push({name:bundle.name||`${source} 시작 행동 묶음`,bundle:true,min_level:1,desc:moves.map(m=>`${m.name}\n${m.desc||''}`).join('\n\n'),bundle_moves:moves.map(m=>m.name)})}
  (c.start||[]).filter(m=>!bundled.has(m.name)).forEach(m=>out.push({...m,bundle:false,min_level:1}));
  if(effective>=2)(c.a25||[]).forEach(m=>out.push({...m,bundle:false,min_level:2}));
  if(effective>=6)(c.a610||[]).forEach(m=>out.push({...m,bundle:false,min_level:6}));
  return out;
}
function spellPreviewHtml(sp){if(!sp)return `<div class="choice-preview empty">${esc('선택하면 주문 설명이 여기에 표시됩니다.')}</div>`;const b=spellIsBuiltin(sp);return `<article class="choice-preview ${b?'':'no-i18n'}"><div class="row-head"><b>${recordEsc(sp.name,b)}</b><span class="pill">${sp.source_class?recordEsc(sp.source_class,classIsBuiltin(sp.source_class)):''}</span><span class="pill">${recordEsc(spellLevelLabel(sp.level),b)}</span></div><div class="move-desc">${recordEsc(sp.desc||'설명 없음',b)}</div></article>`}
function movePreviewHtml(move,source=''){if(!move)return `<div class="choice-preview empty">${esc('선택하면 행동 설명이 여기에 표시됩니다.')}</div>`;const b=classIsBuiltin(source);return `<article class="choice-preview${b?'':' no-i18n'}"><div class="row-head"><b>${recordEsc(move.name,b)}</b>${source?`<span class="pill">${recordEsc(source,b)}</span>`:''}</div><div class="move-desc">${recordEsc(move.desc||'설명 없음',b)}</div></article>`}
function moveEffectChoiceInstruction(row,state){
  const e=row.effect||{},moveName=contentValue(row.move?.name||'',classIsBuiltin(state.class_name));
  if(APP.language==='en'){
    if(e.kind==='spell_level_reduce')return `${moveName}: choose one ${contentValue(state.class_name,classIsBuiltin(state.class_name))} spell. Its required level will be lowered by ${Math.max(1,Number(e.amount)||1)}.`;
    if(e.kind==='spell_grant'){const source=e.all_classes||e.source_class==='*'?'a classified class':contentValue(e.source_class||state.class_name,classIsBuiltin(e.source_class||state.class_name));return `${moveName}: choose one additional spell from ${source}. Unclassified spells are not available here.`}
    if(e.kind==='move_grant'){const source=e.source_class&&e.source_class!=='*'?contentValue(e.source_class,classIsBuiltin(e.source_class)):'another class';return `${moveName}: choose one move from ${source}. Read the preview before saving your choice.`}
    return '';
  }
  if(e.kind==='spell_level_reduce')return `${moveName}: ${contentValue(state.class_name,classIsBuiltin(state.class_name))} 주문 하나를 고르세요. 선택한 주문의 요구 레벨이 ${Math.max(1,Number(e.amount)||1)}단계 낮아집니다.`;
  if(e.kind==='spell_grant'){const cls=e.source_class||state.class_name,source=e.all_classes||e.source_class==='*'?'분류된 모든 직업':contentValue(cls,classIsBuiltin(cls));return `${moveName}: ${source} 주문 중 하나를 추가로 배우세요. 미분류 주문은 여기에서 선택할 수 없습니다.`}
  if(e.kind==='move_grant'){const source=e.source_class&&e.source_class!=='*'?contentValue(e.source_class,classIsBuiltin(e.source_class)):'다른 직업';return `${moveName}: ${source}의 행동 하나를 고르세요. 저장하기 전에 아래 설명을 확인할 수 있습니다.`}
  return '';
}
function renderMoveEffectChoices(bundle){
  const s=bundle.state,ownerBuiltin=classIsBuiltin(s.class_name),rows=activeMoveEffects(s).filter(r=>['spell_level_reduce','spell_grant','move_grant'].includes(r.effect?.kind));if(!rows.length)return '';
  const pending=rows.filter(row=>{const c=moveChoice(s,row.key);return row.effect?.kind==='move_grant'?!String(c.move_name||'').trim():!Number(c.spell_id)}).length;
  return `<section class="panel move-effect-choice-panel ${pending?'needs-choice':''}"><div class="head"><span>행동에서 고를 것</span>${pending?`<span class="pill pending-choice-pill">선택 필요 ${pending}</span>`:''}</div><div class="body"><div class="notice move-choice-guide">행동을 얻으면서 함께 정해야 하는 영구 선택입니다. 무엇을 고르는지와 결과를 읽은 뒤 저장하세요. 판정 때마다 고르는 선택지는 이곳에 나오지 않습니다.</div><div class="grid">${rows.map(row=>{const e=row.effect,choice=moveChoice(s,row.key),instruction=moveEffectChoiceInstruction(row,s),rowName=recordEsc(row.move.name,ownerBuiltin);if(e.kind==='spell_level_reduce'||e.kind==='spell_grant'){const opts=moveEffectSpellOptions(s,row),selected=Number(choice.spell_id)||0,sp=opts.find(x=>Number(x.id)===selected)||spellById(selected),label=e.kind==='spell_grant'?'추가로 배울 주문':'레벨을 낮출 주문',button=e.kind==='spell_grant'?'이 주문 배우기':'이 주문에 적용';return `<div class="move-effect-choice${ownerBuiltin?'':' no-i18n'}" data-effect-block="${attr(row.key)}"><div class="row-head"><b>${rowName}</b><span class="pill">${esc(e.kind==='spell_grant'?'주문 추가 습득':'주문 요구 레벨 낮추기')}</span></div><div class="effect-choice-instruction">${htmlEscape(instruction)}</div><label class="field compact-field"><span>${esc(label)}</span><select class="select" data-effect-spell="${attr(row.key)}"><option value="">${esc('주문 선택…')}</option>${opts.map(x=>{const b=spellIsBuiltin(x);return `<option value="${Number(x.id)||0}" ${Number(x.id)===selected?'selected':''}>${recordEsc(x.name,b)} · ${recordEsc(x.source_class,classIsBuiltin(x.source_class))} · ${recordEsc(spellLevelLabel(x.level),b)}</option>`}).join('')}</select></label><button class="btn small effect-choice-save" data-save-move-effect="${attr(row.key)}" type="button">${esc(button)}</button><div data-effect-preview="${attr(row.key)}">${spellPreviewHtml(sp)}</div></div>`}
    const fixed=String(e.source_class||''),source=String(choice.source_class||((fixed&&fixed!=='*')?fixed:Object.keys(APP.state.classes||{}).find(x=>x!==s.class_name)||'')),sources=fixed&&fixed!=='*'?[fixed]:Object.keys(APP.state.classes||{}).filter(x=>x!==s.class_name),opts=classMoveChoicesAt(source,Number(s.level)||1),selected=String(choice.move_name||''),mv=opts.find(x=>x.name===selected),srcBuiltin=classIsBuiltin(source);return `<div class="move-effect-choice${ownerBuiltin?'':' no-i18n'}" data-effect-block="${attr(row.key)}"><div class="row-head"><b>${rowName}</b><span class="pill">${esc('다른 직업의 행동 습득')}</span></div><div class="effect-choice-instruction">${htmlEscape(instruction)}</div><div class="move-effect-source-grid">${sources.length>1?`<label class="field compact-field"><span>${esc('행동을 가져올 직업')}</span><select class="select" data-effect-source="${attr(row.key)}">${sources.map(x=>`<option value="${attr(x)}" ${x===source?'selected':''}>${recordEsc(x,classIsBuiltin(x))}</option>`).join('')}</select></label>`:''}<label class="field compact-field"><span>${esc('배울 행동')}</span><select class="select" data-effect-move="${attr(row.key)}"><option value="">${esc('행동 선택…')}</option>${opts.map(x=>`<option value="${attr(x.name)}" ${x.name===selected?'selected':''}>${recordEsc(x.name,srcBuiltin)}</option>`).join('')}</select></label><button class="btn small" data-save-move-effect="${attr(row.key)}" type="button">${esc('이 행동 배우기')}</button></div><div data-effect-preview="${attr(row.key)}">${movePreviewHtml(mv,source)}</div>${e.restriction_note?`<div class="small muted effect-condition-note${ownerBuiltin?'':' no-i18n'}"><b>${esc('사용 조건')}</b> · ${recordEsc(e.restriction_note,ownerBuiltin)}</div>`:''}</div>`}).join('')}</div></div></section>`;
}
function renderMoveEffectGrants(bundle){
  const s=bundle.state,cards=[],ownerBuiltin=classIsBuiltin(s.class_name);
  for(const row of activeMoveEffects(s)){const e=row.effect||{},choice=moveChoice(s,row.key);
    if(e.kind==='class_access'){const source=String(e.source_class||''),src=APP.state.classes[source]||{},srcBuiltin=classIsBuiltin(source),acquired=Math.max(1,Number(choice.acquired_at_level)||Number(s.level)||1);for(const name of (e.grant_moves||[])){const mv=(src.start||[]).find(x=>x.name===name)||(src.a25||[]).find(x=>x.name===name)||(src.a610||[]).find(x=>x.name===name);if(mv)cards.push({name:mv.name,desc:mv.desc,source_class:source,source_name:row.move.name,builtin:srcBuiltin,sourceMoveBuiltin:ownerBuiltin,noteKind:'class_access',acquired})}}
    if(e.kind==='move_grant'&&choice.move_name){const source=String(choice.source_class||e.source_class||''),srcBuiltin=classIsBuiltin(source),mv=classMoveChoicesAt(source,Number(s.level)||1).find(x=>x.name===choice.move_name);if(mv)cards.push({name:mv.name,desc:mv.desc,source_class:source,source_name:row.move.name,builtin:srcBuiltin,sourceMoveBuiltin:ownerBuiltin,noteKind:'move_grant',restriction:e.restriction_note||''})}
    if(e.kind==='opposite_race_feature'){const pair=e.race_pair||[],other=pair.find(x=>x!==s.race_name),rd=APP.state.races?.[other],desc=rd?.per_class?.[s.class_name]||'',raceBuiltin=raceIsBuiltin(other);if(other&&desc)cards.push({name:`${contentValue(other,raceBuiltin)} ${APP.language==='en'?'Race Move':'종족 행동'}`,desc,source_class:other,source_name:row.move.name,builtin:raceBuiltin,sourceMoveBuiltin:ownerBuiltin,noteKind:'race'})}
  }
  if(!cards.length)return '';
  const note=x=>{const source=recordEsc(x.source_class,x.builtin),move=recordEsc(x.source_name,x.sourceMoveBuiltin);if(x.noteKind==='class_access')return `${esc('추가됨')} · ${esc('타직업 획득')} · ${source} · ${move} · ${esc('획득 레벨')} ${x.acquired}`;if(x.noteKind==='race')return `${esc('추가됨')} · ${move} · ${source}`;return `${esc('추가됨')} · ${move} · ${source}`};
  return `<section class="panel added-grants-panel"><div class="head">${esc('추가로 얻은 행동 / 특성')}</div><div class="body advanced-grid">${cards.map(x=>`<article class="adv-card added-grant-card${x.builtin?'':' no-i18n'}"><div class="adv-head"><div class="adv-name">${recordEsc(x.name,x.builtin)}</div><span class="pill added-pill">${note(x)}</span></div><details class="move-details" open><summary>${esc('설명')}</summary><div class="move-desc">${recordEsc(x.desc||'설명 없음',x.builtin)}</div></details>${x.restriction?`<div class="small muted${x.sourceMoveBuiltin?'':' no-i18n'}">${recordEsc(x.restriction,x.sourceMoveBuiltin)}</div>`:''}</article>`).join('')}</div></section>`;
}

function monsterDamageText(d){
  d=d||{};const die=String(d.die||'D6').toUpperCase(),count=Math.max(1,Number(d.count)||1),mod=Number(d.modifier)||0,base=`${count>1?count:''}${die}`,mode=d.mode==='high'?(APP.language==='en'?'High[':'고['):d.mode==='low'?(APP.language==='en'?'Low[':'저['):'';return `${mode}${base}${mode?']':''}${mod?` ${mod>0?'+':'-'} ${Math.abs(mod)}`:''}`;
}
function renderMonsterCatalog(){
  const list=APP.state.monster_catalog||[];
  return `<section class="panel catalog-panel"><div class="head"><span>몬스터 도감</span><span class="small">GM이 출현시킨 정보만 기록됩니다.</span></div><div class="body"><div class="catalog-grid">${list.map(m=>{const b=!!m.builtin,show=v=>recordEsc(v??'???',b);return `<article class="catalog-card ${b?'':'no-i18n'}"><div class="catalog-title">${show(m.name)}</div><div class="catalog-stats"><span>HP <b>${esc(m.hp??'???')}</b></span><span>장갑 <b>${esc(m.armor??'???')}</b></span><span>피해 <b>${m.damage?esc(monsterDamageText(m.damage)):'???'}</b></span></div><dl><dt>공격</dt><dd>${show(m.attack)}</dd><dt>거리</dt><dd>${show(m.range)}</dd><dt>태그</dt><dd>${m.tags?m.tags.map(x=>`<span class="pill">${htmlEscape(displayMonsterTag(x))}</span>`).join(' '):'???'}</dd><dt>본능</dt><dd>${show(m.instinct)}</dd><dt>특기</dt><dd>${show(m.special)}</dd><dt>행동</dt><dd>${m.moves?m.moves.map(x=>`• ${show(x)}`).join('<br>'):'???'}</dd><dt>설명</dt><dd class="prewrap">${show(m.description)}</dd></dl></article>`}).join('')||'<div class="notice">아직 도감에 출현한 몬스터가 없습니다.</div>'}</div></div></section>`;
}

const INVENTORY_ITEM_TYPES=['일반 장비','무기','탄약','갑옷','던전 장비','소모품','독','마법 물품','중요한 물건'];
const INVENTORY_RANGES=['반걸음(hand)','한걸음(close)','몇걸음(reach)','중거리(near)','장거리(far)'];
function inventoryItemType(item={}){
  const explicit=String(item.item_type||'').trim();if(INVENTORY_ITEM_TYPES.includes(explicit))return explicit;
  const name=String(item.name||''),tags=String(item.tags||''),hay=`${name} ${tags}`;
  if(['갑옷','방패','장갑 ','장갑+','장갑 +'].some(x=>hay.includes(x)))return '갑옷';
  if(['탄약','화살 다발','화살 한 다발','화살 묶음','쇠뇌살','볼트 묶음'].some(x=>hay.includes(x)))return '탄약';
  if(['독','타기트 기름','박혈초','황금근','뱀눈물'].some(x=>hay.includes(x)))return '독';
  if(hay.includes('마법'))return '마법 물품';
  if(tags.includes('무기')||['활','쇠뇌','단검','단도','비수','소검','장검','검','도끼','전투망치','철퇴','창','지팡이','레이피어','할버드','곤봉','몽둥이','고유병기'].some(x=>name.includes(x)))return '무기';
  if(['모험 장비','붕대','연고와 약초','책 자루','던전용 식량','고급 도시락','드워프 건빵','엘프 빵','하플링 담뱃잎','해독제','치료약'].some(x=>name.includes(x)))return '던전 장비';
  if(Number(item.uses_max)>0||tags.includes('소모품')||tags.includes('회분'))return '소모품';
  return '일반 장비';
}
function inventoryLegacyDamageBonus(item={}){
  if(item.damage_bonus!==undefined&&item.damage_bonus!==null&&String(item.damage_bonus)!=='')return Math.max(-99,Math.min(99,Number(item.damage_bonus)||0));
  const m=String(item.damage||'').match(/([+-])\s*(\d+)/);return m?(m[1]==='+'?1:-1)*Number(m[2]):0;
}
function inventoryArmorInfo(items=[]){
  let base=0,bonus=0;
  for(const item of items){if(inventoryItemType(item)!=='갑옷')continue;base=Math.max(base,Math.max(0,Number(item.armor_value)||0));bonus+=Math.max(0,Number(item.armor_bonus)||0)}
  return {base,bonus,total:base+bonus};
}
function inventoryItemRow(item={},i=0){
  const q=Math.max(1,Number(item.quantity)||1),w=Math.max(0,Number(item.weight)||0),um=Math.max(0,Number(item.uses_max)||0),uc=Math.max(0,Math.min(um||9999,Number(item.uses_current)||0)),am=Math.max(0,Number(item.ammo_max)||0),ac=Math.max(0,Math.min(am||9999,Number(item.ammo_current)||0)),type=inventoryItemType(item),weapon=type==='무기',ammoItem=type==='탄약',armorItem=type==='갑옷',usesItem=type==='소모품'||type==='던전 장비'||um>0,range=String(item.weapon_range||''),damageBonus=inventoryLegacyDamageBonus(item),armorValue=Math.max(0,Number(item.armor_value)||0),armorBonus=Math.max(0,Number(item.armor_bonus)||0),tags=String(item.tags||'');
  return `<article class="inventory-item inventory-text-item" data-inventory-row="${i}">
    <div class="inventory-text-line inventory-primary-line"><input class="inventory-name inventory-text-input" data-inv="name" value="${attr(item.name||'')}" placeholder="물건 이름"><span class="inventory-sep">·</span><span class="inventory-key">종류</span><select class="inventory-text-select inventory-type-select" data-inv="item_type">${INVENTORY_ITEM_TYPES.map(x=>`<option value="${attr(x)}" ${x===type?'selected':''}>${esc(x)}</option>`).join('')}</select><span class="inventory-sep">·</span><span class="inventory-key">수량</span><input class="inventory-text-number" data-inv="quantity" type="number" min="1" max="9999" value="${q}"><span class="inventory-sep">·</span><span class="inventory-key">무게</span><input class="inventory-text-number" data-inv="weight" type="number" min="0" max="9999" step="0.1" value="${w}"><span class="inventory-sep">·</span><span class="inventory-key">태그</span><input class="inventory-tags-text inventory-text-input" data-inv="tags" value="${attr(tags)}" placeholder="예: 정밀, 관통 1, 느림"><button class="inventory-remove inventory-text-remove" data-inventory-remove="${i}" type="button" title="물건 삭제">×</button></div>
    ${weapon?`<div class="inventory-text-line inventory-detail-line"><span class="inventory-detail-kind">무기</span><span class="inventory-sep">·</span><span class="inventory-key">거리</span><select class="inventory-detail-value inventory-text-select inventory-range-select" data-inv="weapon_range"><option value="">거리 선택…</option>${INVENTORY_RANGES.map(x=>`<option value="${attr(x)}" ${range===x?'selected':''}>${esc(x)}</option>`).join('')}</select><span class="inventory-sep">·</span><span class="inventory-key">피해 수정치</span><input class="inventory-text-number signed" data-inv="damage_bonus" type="number" min="-99" max="99" value="${damageBonus}" title="직업의 피해 주사위에 더해 기록할 무기 자체의 피해 수정치"><small class="inventory-rule-note">탄약은 무기와 분리해 ‘탄약’ 종류의 물건으로 기록합니다.</small></div>`:''}
    ${armorItem?`<div class="inventory-text-line inventory-detail-line"><span class="inventory-detail-kind">갑옷</span><span class="inventory-sep">·</span><span class="inventory-key">장갑</span><input class="inventory-text-number" data-inv="armor_value" type="number" min="0" max="99" value="${armorValue}"><span class="inventory-sep">·</span><span class="inventory-key">추가 장갑</span><input class="inventory-text-number" data-inv="armor_bonus" type="number" min="0" max="99" value="${armorBonus}" title="방패처럼 가장 높은 기본 장갑에 더해지는 값"></div>`:''}
    ${usesItem?`<div class="inventory-text-line inventory-detail-line"><span class="inventory-detail-kind">사용 횟수</span><span class="inventory-sep">·</span><span class="inventory-uses inventory-text-uses"><input data-inv="uses_current" type="number" min="0" max="9999" value="${uc}" aria-label="남은 사용 횟수"><i>/</i><input data-inv="uses_max" type="number" min="0" max="9999" value="${um}" aria-label="최대 사용 횟수"></span></div>`:`<input data-inv="uses_current" type="hidden" value="${uc}"><input data-inv="uses_max" type="hidden" value="${um}">`}
    ${ammoItem?`<div class="inventory-text-line inventory-detail-line"><span class="inventory-detail-kind">탄약</span><span class="inventory-sep">·</span><span class="inventory-uses inventory-text-uses"><input data-inv="ammo_current" type="number" min="0" max="9999" value="${ac}" aria-label="현재 탄약"><i>/</i><input data-inv="ammo_max" type="number" min="0" max="9999" value="${am}" aria-label="최대 탄약"></span><small class="inventory-rule-note">Dungeon World의 탄약은 정확한 화살 개수가 아니라 추상 자원입니다.</small></div>`:`<input data-inv="ammo_current" type="hidden" value="${ac}"><input data-inv="ammo_max" type="hidden" value="${am}">`}
    ${weapon?'':`<input data-inv="weapon_range" type="hidden" value="${attr(range)}"><input data-inv="damage_bonus" type="hidden" value="${damageBonus}">`}
    ${armorItem?'':`<input data-inv="armor_value" type="hidden" value="${armorValue}"><input data-inv="armor_bonus" type="hidden" value="${armorBonus}">`}
    <textarea class="inventory-note inventory-text-note" data-inv="note" rows="1" placeholder="필요한 설명이나 사연을 적으세요">${rawEsc(item.note||'')}</textarea>
    ${(q>1||w>0)?`<div class="inventory-line-total">${q>1?`${q}개 × `:''}${formatWeight(w)}무게${q>1?` = ${formatWeight(q*w)}무게`:''}</div>`:''}
  </article>`;
}
function renderInventoryPage(bundle,gmMode){
  const s=bundle.state,c=classData(s),items=Array.isArray(s.inventory)?s.inventory:[],load=inventoryLoadInfo(s),armor=inventoryArmorInfo(items),currency=currencyDisplayName(APP.state.room.rules?.currency_name||'닢');
  return `<section class="panel inventory-panel"><div class="head"><span>인벤토리</span><div class="inventory-load-head ${load.state}"><b>하중 ${formatWeight(load.current)} / ${formatWeight(load.max)}</b><small>${esc(load.short)}</small></div></div><div class="body"><div class="inventory-load-note ${load.state}">${esc(load.detail)}</div>${String(c.gear||'').trim()?`<details class="starting-gear-reference"><summary>직업 시작 장비 안내</summary><div class="${classIsBuiltin(s.class_name)?'':'no-i18n'}">${classIsBuiltin(s.class_name)?htmlEscape(displayMultilineContent(c.gear)):rawEsc(c.gear)}</div></details>`:''}${APP.language==='en'?'<div class="inventory-format-hint"><b>Type</b> is for organization; record the item’s actual qualities under <b>Tags</b>. Only clearly numeric values—load, uses, ammo, armor, and damage modifiers—are tracked in dedicated fields. Track ammo as a separate Ammo item rather than on the weapon itself. Descriptive tags such as precise, piercing, or slow are not resolved automatically.</div>':'<div class="inventory-format-hint"><b>종류</b>는 정리용이고 실제 성질은 <b>태그</b>에 자유롭게 적습니다. 숫자로 분명한 무게·사용 횟수·탄약·장갑·피해 수정치만 구조화합니다. 탄약은 무기에 붙이지 않고 별도 탄약 물건으로 기록하며, 정밀·관통·느림 같은 서술 태그는 자동 판정하지 않습니다.</div>'}${armor.total?`<div class="inventory-armor-summary"><b>장비 기준 장갑</b><span>${armor.base}${armor.bonus?` + ${armor.bonus}`:''} = <strong>${armor.total}</strong></span><small>가장 높은 기본 장갑 + 추가 장갑. 캐릭터 현재 장갑을 자동으로 덮어쓰지는 않습니다.</small></div>`:''}<div id="inventoryList" class="inventory-list">${items.map(inventoryItemRow).join('')||'<div class="inventory-empty">아직 기록한 장비가 없습니다. 필요한 물건을 한 줄씩 추가하세요.</div>'}</div><button id="addInventoryItem" class="inventory-add-text" type="button">＋ 물건 한 줄 추가</button><div class="inventory-currency" title="캐릭터 기본 화면과 같은 재화 값입니다."><b>${esc(currency)}</b><input id="inventoryCurrency" class="currency-input" type="number" min="0" value="${Number(s.currency)||0}" aria-label="${attr(currency)}"></div></div></section>`;
}
function collectInventoryRow(row){const val=k=>$(`[data-inv="${k}"]`,row)?.value??'';let max=Math.max(0,Number(val('uses_max'))||0),cur=Math.max(0,Number(val('uses_current'))||0),ammoMax=Math.max(0,Number(val('ammo_max'))||0),ammoCur=Math.max(0,Number(val('ammo_current'))||0);if(max>0)cur=Math.min(cur,max);if(ammoMax>0)ammoCur=Math.min(ammoCur,ammoMax);const damageBonus=Math.max(-99,Math.min(99,Number(val('damage_bonus'))||0));return {name:String(val('name')).trim(),item_type:String(val('item_type')).trim(),quantity:Math.max(1,Math.min(9999,Number(val('quantity'))||1)),weight:Math.max(0,Math.min(9999,Number(val('weight'))||0)),uses_current:cur,uses_max:max,ammo_current:ammoCur,ammo_max:ammoMax,tags:String(val('tags')).trim(),weapon_range:String(val('weapon_range')).trim(),damage_bonus:damageBonus,damage:damageBonus?`${damageBonus>0?'+':''}${damageBonus} 피해`:'',armor_value:Math.max(0,Math.min(99,Number(val('armor_value'))||0)),armor_bonus:Math.max(0,Math.min(99,Number(val('armor_bonus'))||0)),note:String(val('note'))};}
function collectInventory(){return $$('[data-inventory-row]').map(collectInventoryRow);}
function inventoryRowHasPersistableContent(item={}){return !!(String(item.name||'').trim()||String(item.tags||'').trim()||String(item.note||'').trim()||String(item.weapon_range||'').trim()||Number(item.weight)>0||Number(item.uses_max)>0||Number(item.ammo_max)>0||Number(item.damage_bonus)!==0||Number(item.armor_value)>0||Number(item.armor_bonus)>0);}
function attachInventory(bundle,gmMode){
  const s=bundle.state,save=(patch,rerender=false)=>patchCharacter(bundle.id,patch,gmMode,rerender);let timer=null;
  const persist=(rerender=false)=>{clearTimeout(timer);timer=setTimeout(()=>{const inventory=collectInventory();s.inventory=inventory;save({inventory},rerender)},rerender?0:350)};
  const restoreEmptyHint=()=>{const list=$('#inventoryList');if(list&&!$('[data-inventory-row]',list))list.innerHTML='<div class="inventory-empty">아직 기록한 장비가 없습니다. 필요한 물건을 한 줄씩 추가하세요.</div>'};
  const replaceDraftRow=(row,item)=>{const index=Number(row.dataset.inventoryRow)||0,rowTop=row.getBoundingClientRect().top;row.outerHTML=inventoryItemRow(item,index);const next=$(`[data-inventory-row="${index}"]`,$('#inventoryList'));if(next){next.dataset.inventoryDraft='1';bindRow(next);window.scrollBy(0,next.getBoundingClientRect().top-rowTop)}return next};
  const bindRow=row=>{
    $('[data-inventory-remove]',row)?.addEventListener('click',()=>{clearTimeout(timer);if(row.dataset.inventoryDraft==='1'){row.remove();restoreEmptyHint();return}const inventory=collectInventory();inventory.splice(Number(row.dataset.inventoryRow),1);s.inventory=inventory;save({inventory},true)});
    $$('input,textarea',row).forEach(i=>{i.addEventListener('input',()=>{if(row.dataset.inventoryDraft==='1'&&!inventoryRowHasPersistableContent(collectInventoryRow(row)))return;persist(false)});i.addEventListener('change',()=>{if(row.dataset.inventoryDraft==='1'&&!inventoryRowHasPersistableContent(collectInventoryRow(row)))return;persist(true)})});
    $$('select',row).forEach(i=>i.addEventListener('change',()=>{if(row.dataset.inventoryDraft==='1'){const item=collectInventoryRow(row);if(i.dataset.inv==='item_type'){const next=replaceDraftRow(row,item);if(!inventoryRowHasPersistableContent(item)){next?.querySelector('[data-inv="item_type"]')?.focus();return}}if(!inventoryRowHasPersistableContent(item))return}persist(true)}));
  };
  $('#addInventoryItem')?.addEventListener('click',()=>{clearTimeout(timer);const list=$('#inventoryList');if(!list)return;const existingDraft=$('[data-inventory-draft="1"]',list);if(existingDraft){$('[data-inv="name"]',existingDraft)?.focus();existingDraft.scrollIntoView({block:'nearest'});return}$('.inventory-empty',list)?.remove();const index=$$('[data-inventory-row]',list).length,blank={name:'',item_type:'일반 장비',quantity:1,weight:0,uses_current:0,uses_max:0,ammo_current:0,ammo_max:0,tags:'',weapon_range:'',damage_bonus:0,damage:'',armor_value:0,armor_bonus:0,note:''};list.insertAdjacentHTML('beforeend',inventoryItemRow(blank,index));const row=$(`[data-inventory-row="${index}"]`,list);if(row){row.dataset.inventoryDraft='1';bindRow(row);$('[data-inv="name"]',row)?.focus();row.scrollIntoView({block:'nearest'})}});
  $$('[data-inventory-row]').forEach(bindRow);
  $('#inventoryCurrency')?.addEventListener('change',e=>{const v=Math.max(0,Number(e.target.value)||0);e.target.value=v;s.currency=v;save({currency:v},true)});
}

function renderMemoPage(bundle){return `<section class="panel"><div class="head">자유 메모 <span class="small">장비는 인벤토리에서 관리합니다.</span></div><div class="body"><textarea id="memoArea" class="textarea memo" placeholder="단서, 약속, 아이템의 사연, 세션 메모처럼 자유 형식으로 기록하세요.">${rawEsc(bundle.state.memo||'')}</textarea></div></section>`;}

function advancedMovePointCap(state){const level=Math.max(1,Number(state?.level)||1),levelMax=Math.max(1,Number(APP.state?.room?.rules?.level_max)||10);return Math.max(0,Math.min(level,levelMax)-1)}
function extensionMovePointUsage(state){let total=0;for(const raw of Object.values(state?.extension_state||{})){const st=raw||{};if(st.legend_owned)total+=1;total+=new Set((st.class_moves_owned||[]).filter(Boolean)).size}return total}
function advancedMovePointUsage(state){return new Set((state?.advanced_moves||[]).filter(Boolean)).size+extensionMovePointUsage(state)}
function advancedMovePointInfo(state){const cap=advancedMovePointCap(state),used=advancedMovePointUsage(state);return {cap,used,left:Math.max(0,cap-used),over:Math.max(0,used-cap)}}

function expansionMoveDetails(move,builtin=true){
  return `<details class="move-details"><summary>설명</summary><div class="move-desc${recordNoI18n(builtin)}">${recordEsc(move?.desc||'설명 없음',builtin)}</div></details>`;
}

function renderExtensionPage(bundle,grantId,gmMode){
  const ext=(bundle.summary?.extensions||[]).find(x=>x.grant_id===grantId);if(!ext)return '<div class="notice bad">확장직업 정보를 찾을 수 없습니다.</div>';
  const d=ext.data||{},builtin=!!d.builtin,st=(bundle.state.extension_state||{})[String(grantId)]||{},legend=d.legend_move||{},legendOwned=!!st.legend_owned,owned=new Set(st.class_moves_owned||[]),th=d.theme||{},isHidden=!!d.hidden,resource=d.resource||{},resourceName=String(resource.name||'').trim(),resourceMax=Math.max(0,Number(resource.max)||0),resourceCurrent=Math.max(0,Number(st.resource_current)||0),ownerName=String(bundle.summary?.character_name||bundle.state?.profile?.name||bundle.summary?.display_name||APP.state?.me?.name||'플레이어').trim()||'플레이어',points=advancedMovePointInfo(bundle.state),canSpend=points.left>0;
  const classCards=(d.class_moves||[]).map(m=>{const has=owned.has(m.name),disabled=!gmMode&&(!legendOwned||(!has&&!canSpend));return `<div class="adv-card"><div class="adv-head"><div class="adv-name${recordNoI18n(builtin)}">${recordEsc(m.name,builtin)}</div><span class="pill">직업 행동</span><label class="move-check"><input type="checkbox" data-ext-classmove="${grantId}" value="${attr(m.name)}" ${has?'checked':''} ${disabled?'disabled':''}> ${has?'보유':'선택'}</label></div>${expansionMoveDetails(m,builtin)}${!has&&!gmMode&&legendOwned&&!canSpend?`<div class="small muted">${APP.language==='en'?'No advanced-move points remain.':'남은 고급행동 포인트가 없습니다.'}</div>`:''}</div>`}).join('');
  const pointText=APP.language==='en'?`Advanced-move points: ${points.used}/${points.cap} used · ${points.left} remaining. Accepting an expansion class costs no point; its Legendary Move and each Class Move cost 1 point. Unspent points carry forward.`:`고급행동 포인트 ${points.used}/${points.cap} 사용 · ${points.left} 남음. 확장직업을 받아들이는 것 자체는 포인트를 쓰지 않으며, 전설행동과 각 직업 행동은 1점씩 사용합니다. 남은 포인트는 이후 레벨에도 계속 이월됩니다.`;
  const legendDisabled=!gmMode&&!legendOwned&&!canSpend;
  return `<section class="panel extension-panel ${isHidden?'hidden-expansion':''}" style="--ext-page-bg:${attr(th.page_background||'#f2f0e8')};--ext-bg:${attr(th.background||'#fff')};--ext-text:${attr(th.text||'#181818')};--ext-accent:${attr(th.accent||'#181818')}"><div class="head"><span class="extension-title${recordNoI18n(builtin)}">${isHidden?'◆ ':''}${recordEsc(ext.name,builtin)}</span><span>${isHidden?'히든 · ':''}${ext.visible_to_party?'파티 공개':`<span class="no-i18n">${rawEsc(ownerName)}</span> 전용`}</span></div><div class="body"><div class="notice ext-intro${recordNoI18n(builtin)}">${recordEsc(ext.public_intro||'',builtin)}</div>${d.source_note?`<div class="notice small${recordNoI18n(builtin)}">${recordEsc(d.source_note,builtin)}</div>`:''}<div class="notice advanced-point-notice">${pointText}</div>${resourceName?`<div class="extension-resource-box"><div><b class="${builtin?'':'no-i18n'}">${recordEsc(resourceName,builtin)}</b></div><input data-ext-resource="${grantId}" type="number" min="0" ${resourceMax>0?`max="${resourceMax}"`:''} value="${Math.min(resourceCurrent,resourceMax>0?resourceMax:resourceCurrent)}"><small>${resourceMax>0?`/ ${resourceMax}`:'상한 없음'}</small></div>`:''}
    <h3 class="ext-heading">전설행동</h3><div class="legend-card"><div class="adv-head"><div class="adv-name${recordNoI18n(builtin)}">${recordEsc(legend.name||'전설행동 미등록',builtin)}</div><span class="pill">전설행동 · 1점</span><label class="move-check"><input type="checkbox" data-ext-legend="${grantId}" ${legendOwned?'checked':''} ${legendDisabled?'disabled':''}> ${legendOwned?'보유':'선택'}</label></div>${expansionMoveDetails(legend,builtin)}${!legendOwned&&!gmMode&&!canSpend?`<div class="small muted">${APP.language==='en'?'Gain another level or unselect another advanced move to free a point.':'레벨을 더 올리거나 다른 고급 행동 선택을 취소해 포인트를 확보해야 합니다.'}</div>`:''}</div>
    <h3 class="ext-heading">직업 행동</h3><div class="advanced-grid">${classCards||'<div class="notice">표시할 직업 행동이 없습니다.</div>'}</div>${!legendOwned&&!gmMode?'<div class="notice warn">먼저 전설행동을 고급행동 포인트로 선택해야 직업 행동을 선택할 수 있습니다.</div>':''}
    ${gmMode?'<div class="notice warn">GM은 필요하면 행동을 강제로 지급하거나 회수할 수 있습니다. 강제로 지급한 행동도 고급행동 포인트 사용량에는 포함됩니다.</div>':''}</div></section>`;
}

function characterSummaryModal(bundle){
  const s=bundle.state,c=classData(s),classBuiltin=classIsBuiltin(s.class_name),rules=APP.state.room.rules||{},stats=s.stats||{},loadInfo=inventoryLoadInfo(s),races=c.races||[],race=(races.find(x=>x.name===s.race_name)||{}),raceBuiltin=race._builtin!==undefined?!!race._builtin:raceIsBuiltin(s.race_name),owned=new Set(s.advanced_moves||[]),currency=currencyDisplayName(rules.currency_name||'닢');
  const statBoxes=Object.entries(STAT_META).map(([k,[name,abbr]])=>`<div class="playbook-stat"><span>${esc(name)}</span><b>${Number(stats[k])||0}</b><em>${esc(abbr)} ${modText(Number(stats[k])||0)}</em></div>`).join('');
  const starting=(c.start||[]).map(m=>`<li${classBuiltin?'':' class="no-i18n"'}><b>${recordEsc(m.name,classBuiltin)}</b>${moveRelationBadges(m,classBuiltin)}</li>`).join('')||'<li class="muted">없음</li>';
  const advanced=[...(c.a25||[]),...(c.a610||[])].filter(m=>owned.has(m.name)).map(m=>`<li${classBuiltin?'':' class="no-i18n"'}><b>${recordEsc(m.name,classBuiltin)}</b>${moveRelationBadges(m,classBuiltin)}</li>`).join('')||'<li class="muted">아직 선택한 고급 행동 없음</li>';
  const bonds=(s.bonds||[]).filter(x=>String(typeof x==='string'?x:(x?.desc||x?.text||'')).trim()).map(x=>`<li class="no-i18n">${rawEsc(String(typeof x==='string'?x:(x?.desc||x?.text||'')))}</li>`).join('')||'<li class="muted">기록된 인연 없음</li>';
  const spells=(s.prepared_spells||[]).slice(0,10).map(x=>{const sp=Object.values(APP.state.spells||{}).flat().find(y=>y.name===x);return `<span class="pill${sp&&!spellIsBuiltin(sp)?' no-i18n':''}">${sp?recordEsc(x,spellIsBuiltin(sp)):rawEsc(x)}</span>`}).join('')||'<span class="muted">준비 주문 없음</span>';
  document.body.insertAdjacentHTML('beforeend',`<div class="modal playbook-summary-modal" id="characterSummaryModal"><div class="modal-card playbook-summary-card"><div class="modal-head"><div><b>${rawEsc(s.profile?.name||bundle.summary?.character_name||'캐릭터')}</b><span class="small">요약 보기 · 자주 쓰는 정보를 한눈에 확인합니다</span></div><button class="btn small" data-close-summary type="button">닫기</button></div><div class="modal-body"><section class="playbook-summary-top"><div class="playbook-title"><span>${s.class_name?recordEsc(s.class_name,classIsBuiltin(s.class_name)):esc('무직')} · ${s.race_name?recordEsc(s.race_name,raceIsBuiltin(s.race_name)):esc('종족 없음')} · ${htmlEscape(translateUiText('하중'))} ${formatWeight(loadInfo.current)}/${formatWeight(loadInfo.max)}</span><b>LV.${Number(s.level)||1}</b><b>XP ${Number(s.xp)||0}</b></div><div class="playbook-vitals"><div><span>HP</span><b>${Number(s.hp_current)||0}/${hpMax(s)}</b></div><div><span>장갑</span><b>${Number(s.armor)||0}</b></div><div><span>피해</span><b>${esc(damageText(s))}</b></div><div><span>예비</span><b>${Number(s.reserve)||0}</b></div><div><span class="no-i18n">${rawEsc(currency)}</span><b>${Number(s.currency)||0}</b></div></div></section><section class="playbook-stat-grid">${statBoxes}</section><div class="playbook-summary-columns"><section><h3>가치관</h3><div class="summary-note"><b>${s.alignment_name?recordEsc(s.alignment_name,classBuiltin):esc('미정')}</b></div><h3>종족 특성</h3><div class="summary-note${raceBuiltin?'':' no-i18n'}">${race.desc?recordEsc(race.desc,raceBuiltin):esc('등록된 설명 없음')}</div><h3>인연</h3><ul>${bonds}</ul></section><section><h3>시작 행동</h3><ul class="playbook-move-list">${starting}</ul><h3>선택한 고급 행동</h3><ul class="playbook-move-list">${advanced}</ul><h3>준비 주문</h3><div class="summary-spell-pills">${spells}</div></section></div></div></div></div>`);
  const modal=$('#characterSummaryModal');$('[data-close-summary]',modal)?.addEventListener('click',()=>modal.remove());modal?.addEventListener('click',e=>{if(e.target===modal)modal.remove()});
}

function attachPlayerPage(bundle,gmMode){
  const s=bundle.state,cid=bundle.id,save=(patch,rerender=false)=>patchCharacter(cid,patch,gmMode,rerender);
  $('[data-character-summary]')?.addEventListener('click',()=>characterSummaryModal(bundle));
  attachInventory(bundle,gmMode);
  $$('[data-prof]').forEach(i=>i.addEventListener('change',()=>{if(i.dataset.prof==='name'&&!gmMode)return;const p={...(s.profile||{})};p[i.dataset.prof]=i.value;s.profile=p;save({profile:p})}));
  if(gmMode) $('#charClass')?.addEventListener('change',async e=>{const name=e.target.value,c=APP.state.classes[name]||{},r=c.races?.[0]?.name||'',a=c.alignments?.[0]?.name||'';const patch={class_name:name,race_name:r,alignment_name:a,bonds:(c.bonds||[]).map(x=>String(x)),advanced_moves:[],extra_moves:[],move_choices:{},spellbook:[],prepared_spells:[],extra_spells:[],starting_spells_complete:false,spell_tracks:{},damage_die:String(c.damage||'D6'),damage_bonus:0};Object.assign(s,patch);await save(patch,true)});
  if(gmMode) $('#charRace')?.addEventListener('change',e=>{s.race_name=e.target.value;save({race_name:s.race_name},true)});
  const setStat=(k,next)=>{const rules=APP.state.room.rules||{},lo=Number(rules.stat_min??3),hi=Number(rules.stat_max??18),assigned=!!s.stats_initialized,gNow=statGrowthInfo(s,rules),old=Number(s.stats?.[k])||0;if(assigned){next=Math.max(lo,Math.min(hi,Number(next)||0));if(!gmMode&&next>old&&gNow.remain<=0){toast(APP.language==='en'?'No ability growth points remain.':'남은 능력치 성장 포인트가 없습니다.');return}}const delta=k==='con'?next-old:0,stats={...(s.stats||{}),[k]:next},patch={stats};if(delta){const newMax=Math.max(1,(Number(classData(s).hp)||1)+(Number(stats.con)||0));patch.hp_current=Math.max(0,Math.min(newMax,(Number(s.hp_current)||0)+delta));s.hp_current=patch.hp_current}s.stats=stats;save(patch,true)};
  $$('[data-stat]').forEach(i=>i.addEventListener('change',()=>setStat(i.dataset.stat,Number(i.value)||0)));
  $$('[data-stat-step]').forEach(b=>b.addEventListener('click',()=>{const k=b.dataset.statStep,delta=Number(b.dataset.delta),rules=APP.state.room.rules,cur=Number(s.stats?.[k])||0,gNow=statGrowthInfo(s,rules);let next=cur;if(!gNow.assigned){if(delta>0&&cur===0&&gNow.remaining.length)next=Number(gNow.remaining[0]);else if(delta<0&&cur>0)next=0;else return}else{next=cur+delta}setStat(k,next)}));
  $$('[data-vital-range]').forEach(i=>{const key=i.dataset.vitalRange,max=Number(i.max)||1;i.addEventListener('input',()=>{const v=Number(i.value)||0,$fill=$(`[data-vital-fill="${key}"]`),$lab=$(`[data-vital-label="${key}"]`);if($fill)$fill.style.width=`${Math.max(0,Math.min(100,v/Math.max(1,max)*100))}%`;if($lab)$lab.textContent=key==='hp_current'?`${v} / ${hpMax(s)}`:`${v} / ${(Number(s.level)>=Number(APP.state.room.rules.level_max))?(APP.language==='en'?'MAX':'최대'):xpRequiredFor(s,bundle)}${Number(s.level)<Number(APP.state.room.rules.level_max)&&v>=(xpRequiredFor(s,bundle))?` · ${translateUiText('레벨업 가능')}`:''}`});i.addEventListener('change',()=>{const v=Number(i.value)||0;s[key]=v;save({[key]:v})})});
  $$('[data-num]').forEach(i=>i.addEventListener('change',()=>{let v=Number(i.value)||0;if(i.dataset.num==='level')v=Math.max(1,Math.min(Number(APP.state.room.rules.level_max)||10,v));else v=Math.max(0,v);if(i.dataset.num==='reserve'){const m=Math.max(0,Number(APP.state.room.rules.reserve_max)||0);if(m>0)v=Math.min(v,m);i.value=v}s[i.dataset.num]=v;save({[i.dataset.num]:v},true)}));
  $$('[data-step][data-num], [data-step][data-damage-bonus]').forEach(b=>b.addEventListener('click',()=>{const input=b.parentElement.querySelector('input'),delta=Number(b.dataset.step);let v=(Number(input.value)||0)+delta;if(input.dataset.num)v=Math.max(0,v);input.value=v;input.dispatchEvent(new Event('change',{bubbles:true}))}));
  $('#damageDie')?.addEventListener('change',e=>{s.damage_die=e.target.value;save({damage_die:s.damage_die},true)});
  $('input[data-damage-bonus]')?.addEventListener('change',e=>{s.damage_bonus=Number(e.target.value)||0;save({damage_bonus:s.damage_bonus},true)});
  $$('input[name="alignment"]').forEach(i=>i.addEventListener('change',()=>{s.alignment_name=i.value;save({alignment_name:i.value})}));
  $$('[data-bond]').forEach(i=>{autoGrowBond(i);i.addEventListener('input',()=>autoGrowBond(i));i.addEventListener('change',()=>{const b=[...(s.bonds||[])];b[Number(i.dataset.bond)]=i.value;s.bonds=b;save({bonds:b})})});
  $$('[data-adv]').forEach(i=>i.addEventListener('change',async()=>{const set=new Set(s.advanced_moves||[]),choices={...(s.move_choices||{})},tracks={...(s.spell_tracks||{})},c=classData(s),def=[...(c.a25||[]),...(c.a610||[])].find(m=>m.name===i.dataset.adv);if(i.checked){set.add(i.dataset.adv);(def?.move_effects||[]).forEach((e,idx)=>{const key=moveEffectKey(def,e,idx);choices[key]={...(choices[key]||{}),acquired_at_level:Number(choices[key]?.acquired_at_level)||Math.max(1,Number(s.level)||1)}})}else{set.delete(i.dataset.adv);(def?.move_effects||[]).forEach((e,idx)=>{const key=moveEffectKey(def,e,idx);delete choices[key];delete tracks[key]})}s.advanced_moves=[...set];s.move_choices=choices;s.spell_tracks=tracks;try{await save({advanced_moves:s.advanced_moves,move_choices:choices,spell_tracks:tracks},true)}catch{i.checked=!i.checked}}));
  attachExtraMoves(bundle,gmMode);
  $$('[data-spellbook]').forEach(i=>i.addEventListener('change',()=>{
    const profile=spellcastingProfile(s.class_name),name=i.dataset.spellbook,set=new Set(s.spellbook||[]),prep=new Set(s.prepared_spells||[]),base=moveSpellContext(s,raceSpellContext(s).all),spell=base.find(x=>x.name===name),was=set.has(name);
    if(i.checked){
      if(!gmMode&&profile.known_mode==='selected'){
        const level=spellEffectiveLevel(spell?.level),startLevel=Math.max(0,Number(profile.starting_choice_level)||0),startNeed=Math.max(0,Number(profile.starting_choice_count)||0),startPending=startLevel>0&&startNeed>0&&!s.starting_spells_complete;
        if(startPending&&level!==startLevel){i.checked=was;return toast(`${startLevel}레벨 시작 주문을 먼저 확정하세요.`)}
        const cap=spellKnownCap(profile,Number(s.level)||1),next=new Set(set);next.add(name),learnable=base.filter(x=>spellEffectiveLevel(x.level)>0&&spellEffectiveLevel(x.level)<=Number(s.level||1)),used=learnable.filter(x=>next.has(x.name)).length;
        if(Number.isFinite(cap)&&used>cap){i.checked=was;return toast(`${profile.known_label||'습득'} 가능한 주문 수는 현재 ${cap}개입니다.`)}
      }
      set.add(name);
    }else{set.delete(name);prep.delete(name)}
    s.spellbook=[...set];s.prepared_spells=[...prep];save({spellbook:s.spellbook,prepared_spells:s.prepared_spells},true)
  }));
  $$('[data-prepared]').forEach(i=>i.addEventListener('change',()=>{
    const profile=spellcastingProfile(s.class_name),name=i.dataset.prepared,set=new Set(s.prepared_spells||[]),was=set.has(name),pool=primarySpellPool(s),spell=pool.find(x=>x.name===name),known=new Set(s.spellbook||[]),zero=spellEffectiveLevel(spell?.level)===0,autoKnown=profile.known_mode==='all'||(zero&&profile.zero_auto_known)||!!spell?.auto_book||!!spell?.race_auto||!!spell?.kind;
    if(i.checked){
      if(!gmMode&&profile.prepare_mode==='known'&&!autoKnown&&!known.has(name)){i.checked=was;return toast(`${profile.known_label||'습득'}한 주문만 ${profile.prepare_label||'준비'}할 수 있습니다.`)}
      const next=new Set(set);next.add(name),limit=spellPrepLimit(profile,Number(s.level)||1),usage=spellPrepUsage(profile,[...next],pool);
      if(!gmMode&&Number.isFinite(limit)&&usage>limit){i.checked=was;return toast(profile.limit_mode==='count'?`${profile.prepare_label||'준비'} 가능한 주문은 ${limit}개입니다.`:`${profile.prepare_label||'준비'} 주문 레벨 합은 ${limit}을 넘을 수 없습니다.`)}
      set.add(name);
    }else set.delete(name);
    s.prepared_spells=[...set];save({prepared_spells:s.prepared_spells},true)
  }));
  $('#finishStartingSpells')?.addEventListener('click',()=>{const profile=spellcastingProfile(s.class_name),level=Math.max(0,Number(profile.starting_choice_level)||0),need=Math.max(0,Number(profile.starting_choice_count)||0),choices=moveSpellContext(s,raceSpellContext(s).all).filter(x=>spellEffectiveLevel(x.level)===level),count=choices.filter(x=>(s.spellbook||[]).includes(x.name)).length;if(count!==need)return toast(`${level}레벨 시작 주문을 정확히 ${need}개 선택하세요.`);s.starting_spells_complete=true;save({starting_spells_complete:true},true)});
  $$('[data-track-known]').forEach(i=>i.addEventListener('change',()=>{
    const key=i.dataset.trackKnown,name=i.dataset.trackSpell,access=classAccessSpellGroups(s).find(x=>x.key===key);if(!access)return;
    const profile=access.profile,track=spellTrackState(s,key),known=new Set(track.known),prepared=new Set(track.prepared),was=known.has(name),spell=access.spells.find(x=>x.name===name);
    if(i.checked){
      if(!gmMode&&profile.known_mode==='selected'){
        const level=spellEffectiveLevel(spell?.level),startLevel=Math.max(0,Number(profile.starting_choice_level)||0),startNeed=Math.max(0,Number(profile.starting_choice_count)||0),startPending=startLevel>0&&startNeed>0&&!track.starting_complete;
        if(startPending&&level!==startLevel){i.checked=was;return toast(`${access.source_class}: ${startLevel}레벨 시작 주문을 먼저 확정하세요.`)}
        const next=new Set(known);next.add(name),cap=spellKnownCap(profile,access.effective_level),learnable=access.spells.filter(x=>{const n=spellEffectiveLevel(x.level);return n>0&&n<=access.effective_level}),used=learnable.filter(x=>next.has(x.name)).length;
        if(Number.isFinite(cap)&&used>cap){i.checked=was;return toast(`${access.source_class}: ${profile.known_label||'습득'} 가능한 주문 수는 ${cap}개입니다.`)}
      }
      known.add(name);
    }else{known.delete(name);prepared.delete(name)}
    track.known=[...known];track.prepared=[...prepared];updateSpellTrack(s,key,track);save({spell_tracks:s.spell_tracks},true)
  }));
  $$('[data-track-prepared]').forEach(i=>i.addEventListener('change',()=>{
    const key=i.dataset.trackPrepared,name=i.dataset.trackSpell,access=classAccessSpellGroups(s).find(x=>x.key===key);if(!access)return;
    const profile=access.profile,track=spellTrackState(s,key),known=new Set(track.known),prepared=new Set(track.prepared),was=prepared.has(name),spell=access.spells.find(x=>x.name===name),zero=spellEffectiveLevel(spell?.level)===0,autoKnown=profile.known_mode==='all'||(zero&&profile.zero_auto_known);
    if(i.checked){
      if(!gmMode&&profile.prepare_mode==='known'&&!autoKnown&&!known.has(name)){i.checked=was;return toast(`${access.source_class}: ${profile.known_label||'습득'}한 주문만 ${profile.prepare_label||'준비'}할 수 있습니다.`)}
      const next=new Set(prepared);next.add(name);const available=access.spells.filter(x=>{const n=spellEffectiveLevel(x.level);return n===0||n<=access.effective_level}),limit=spellPrepLimit(profile,access.effective_level),usage=spellPrepUsage(profile,[...next],available);
      if(!gmMode&&Number.isFinite(limit)&&usage>limit){i.checked=was;return toast(profile.limit_mode==='count'?`${access.source_class}: ${profile.prepare_label||'준비'} 가능한 주문은 ${limit}개입니다.`:`${access.source_class}: ${profile.prepare_label||'준비'} 주문 레벨 합은 ${limit}을 넘을 수 없습니다.`)}
      prepared.add(name);
    }else prepared.delete(name);
    track.prepared=[...prepared];updateSpellTrack(s,key,track);save({spell_tracks:s.spell_tracks},true)
  }));
  $$('[data-finish-track-start]').forEach(b=>b.addEventListener('click',()=>{const key=b.dataset.finishTrackStart,access=classAccessSpellGroups(s).find(x=>x.key===key);if(!access)return;const profile=access.profile,track=spellTrackState(s,key),level=Math.max(0,Number(profile.starting_choice_level)||0),need=Math.max(0,Number(profile.starting_choice_count)||0),choices=access.spells.filter(x=>spellEffectiveLevel(x.level)===level),count=choices.filter(x=>track.known.includes(x.name)).length;if(count!==need)return toast(`${access.source_class}: ${level}레벨 시작 주문을 정확히 ${need}개 선택하세요.`);track.starting_complete=true;updateSpellTrack(s,key,track);save({spell_tracks:s.spell_tracks},true)}));
  $('#extraSpellSelect')?.addEventListener('change',e=>{const raceRule=APP.state.races?.[s.race_name]||{},access=raceCrossClassAccess(raceRule,s.class_name),source=access.enabled?String(access.source_class||''):'',sp=(APP.state.spells?.[source]||[]).find(x=>x.name===e.target.value),box=$('#extraSpellPreview');if(box)box.innerHTML=spellPreviewHtml(sp?{...sp,source_class:source}:null)});
  $('#addExtraSpell')?.addEventListener('click',()=>{const sel=$('#extraSpellSelect'),raceRule=APP.state.races?.[s.race_name]||{},access=raceCrossClassAccess(raceRule,s.class_name),source=access.enabled?String(access.source_class||''):'';const limit=Math.max(1,Number(access.count)||1),arr=[...(s.extra_spells||[])];if(!sel?.value||!source||arr.filter(x=>x.kind!=='gm').length>=limit)return;const sp=(APP.state.spells?.[source]||[]).find(x=>x.name===sel.value);if(!sp)return;arr.push({kind:'race',spell_id:Number(sp.id)||0,name:sp.name,source,level:sp.level,desc:sp.desc||'',source_name:s.race_name,note:''});s.extra_spells=arr;save({extra_spells:arr},true)});
  $$('[data-extra-del]').forEach(b=>b.addEventListener('click',()=>{const arr=[...(s.extra_spells||[])];arr.splice(Number(b.dataset.extraDel),1);s.extra_spells=arr;save({extra_spells:arr},true)}));
  $('#memoArea')?.addEventListener('input',e=>{autoGrow(e.target);clearTimeout(APP.saveTimer);APP.saveTimer=setTimeout(()=>{s.memo=e.target.value;save({memo:s.memo})},550)});if($('#memoArea'))autoGrow($('#memoArea'));
  attachExtension(bundle,gmMode);
}

function attachExtension(bundle,gmMode){
  const s=bundle.state;
  $$('[data-ext-resource]').forEach(i=>i.addEventListener('change',()=>{const gid=Number(i.dataset.extResource),ext=(bundle.summary?.extensions||[]).find(x=>Number(x.grant_id)===gid),max=Math.max(0,Number(ext?.data?.resource?.max)||0),cur=clone((s.extension_state||{})[String(gid)]||{});let v=Math.max(0,Number(i.value)||0);if(max>0)v=Math.min(v,max);i.value=v;cur.resource_current=v;updateExtState(bundle,gid,cur,gmMode,true)}));
  $$('[data-ext-legend]').forEach(i=>i.addEventListener('change',()=>{const gid=Number(i.dataset.extLegend),cur=clone((s.extension_state||{})[String(gid)]||{});cur.legend_owned=i.checked;if(!i.checked&&!gmMode)cur.class_moves_owned=[];updateExtState(bundle,gid,cur,gmMode,true)}));
  $$('[data-ext-classmove]').forEach(i=>i.addEventListener('change',()=>{const gid=Number(i.dataset.extClassmove),cur=clone((s.extension_state||{})[String(gid)]||{}),set=new Set(cur.class_moves_owned||[]);if(i.checked)set.add(i.value);else set.delete(i.value);cur.class_moves_owned=[...set];updateExtState(bundle,gid,cur,gmMode,true)}));
}

function autoGrow(el){const max=Number(el.dataset.maxGrow)||260,min=Number(el.dataset.minGrow)||96;el.style.height='auto';const h=Math.max(min,Math.min(max,el.scrollHeight+4));el.style.height=h+'px';el.style.overflowY=el.scrollHeight>max?'auto':'hidden';}
function autoGrowBond(el){el.style.height='auto';el.style.height=Math.max(44,Math.min(150,el.scrollHeight+4))+'px';el.style.overflowY=el.scrollHeight>150?'auto':'hidden';}
function updateExtState(bundle,gid,partial,gmMode,replace=false){const s=bundle.state,all=clone(s.extension_state||{}),cur=clone(all[String(gid)]||{});all[String(gid)]=replace?partial:{...cur,...partial};s.extension_state=all;patchCharacter(bundle.id,{extension_state:all},gmMode,true);}
async function patchCharacter(charId,patch,gmMode=false,rerender=false){
  APP.ignoreRefreshUntil=Date.now()+900;
  try{await api(`/api/rooms/${encodeURIComponent(APP.creds.room)}/characters/${charId}`,{method:'PATCH',body:JSON.stringify({patch})});if(rerender)await refreshState(true);return true}catch(e){toast(e.message,3500);await refreshState(true);throw e}
}

function maybeShowExpansionInvite(){if(APP.state?.me?.role!=='player'||!expansionsEnabled()||document.querySelector('#expInviteModal'))return;const inv=(APP.state.expansion_invites||[])[0];if(!inv)return;const th=inv.theme||{},builtin=!!inv.builtin;document.body.insertAdjacentHTML('beforeend',`<div class="modal" id="expInviteModal"><div class="modal-card expansion-invite ${inv.hidden?'hidden-invite':''}" style="--invite-bg:${attr(th.background||'#fff')};--invite-text:${attr(th.text||'#181818')};--invite-accent:${attr(th.accent||'#181818')}"><div class="modal-head"><b><span class="${builtin?'':'no-i18n'}">${recordEsc(inv.name,builtin)}</span>의 길이 열렸습니다</b></div><div class="modal-body"><div class="invite-emblem">확장직업 제안</div>${inv.message?`<div class="invite-message no-i18n">${rawEsc(inv.message)}</div>`:''}${inv.public_intro?`<p class="${builtin?'':'no-i18n'}">${recordEsc(inv.public_intro,builtin)}</p>`:`<p>이 확장직업을 습득하시겠습니까?</p>`}<div class="inline-actions"><button class="btn dark large" data-invite-answer="yes" type="button">받아들인다</button><button class="btn large" data-invite-answer="no" type="button">거절한다</button></div></div></div></div>`);$$('[data-invite-answer]').forEach(b=>b.addEventListener('click',async()=>{try{await api(`/api/rooms/${APP.creds.room}/grants/${inv.grant_id}/respond`,{method:'POST',body:JSON.stringify({accept:b.dataset.inviteAnswer==='yes'})});$('#expInviteModal')?.remove();await refreshState(true);toast(b.dataset.inviteAnswer==='yes'?`${inv.name} 확장직업을 받아들였습니다.`:'확장직업 제안을 거절했습니다.')}catch(e){toast(e.message,3500)}}))}

// ---------------- GM ----------------
function renderGM(){
  if(APP.gmSelectedChar){
    const b=gmCharacterBundle(APP.gmSelectedChar);if(!b){APP.gmSelectedChar=null;return renderGM()}
    if(!b.state.onboarding_complete){appEl().innerHTML=shell(`<div class="inline-actions gm-workspace-back"><button id="gmBack" class="btn dark" type="button">← GM 보드로</button><b>${rawEsc(b.summary?.character_name||b.summary?.display_name||'플레이어')}</b></div>${partyStrip(b.id)}<section class="panel fate-gm-status"><div class="head">캐릭터 준비 상태</div><div class="body fate-status-detail"><div class="fate-mark">?</div><h2>자신의 운명을 결정하는 중</h2><p>이 플레이어는 아직 첫 직업과 종족을 선택하지 않았습니다.</p><div class="metrics"><div class="metric">직업<div class="big">무직</div></div><div class="metric">종족<div class="big">없음</div></div></div></div></section>`,`GM · ${rawEsc(APP.state.me.name)}`);$('#gmBack')?.addEventListener('click',()=>{APP.gmSelectedChar=null;renderGM()});attachPartyModal();return}
    const tabs=playerTabsFor(b);if(!tabs.some(t=>t.id===APP.playerTab))APP.playerTab='character';
    if(desktopWorkspace()){const layout=getWorkspace(b,true),wide=layout.mode==='multi';appEl().innerHTML=shell(`<div class="inline-actions gm-workspace-back"><button id="gmBack" class="btn dark" type="button">← GM 보드로</button><b>${rawEsc(b.summary?.character_name||b.summary?.display_name||'캐릭터')} 시트 편집</b></div>${partyStrip(b.id)}${renderWorkspace(b,true)}`,`GM · ${rawEsc(APP.state.me.name)}`,wide);$('#gmBack').addEventListener('click',()=>{APP.gmSelectedChar=null;APP.playerTab='character';renderGM()});attachPartyModal();attachWorkspace(b,true);attachPlayerPage(b,true);return}
    appEl().innerHTML=shell(`<div class="inline-actions"><button id="gmBack" class="btn dark" type="button">← GM 보드로</button><b>${rawEsc(b.summary?.character_name||'캐릭터')} 시트 편집</b></div>${partyStrip(b.id)}<div class="nav">${tabs.map(tabButton).join('')}</div>${renderPlayerPage(b,true)}`,`GM · ${rawEsc(APP.state.me.name)}`);$('#gmBack').addEventListener('click',()=>{APP.gmSelectedChar=null;APP.playerTab='character';renderGM()});$$('[data-ptab]').forEach(x=>x.addEventListener('click',()=>{APP.playerTab=x.dataset.ptab;renderGM()}));attachPartyModal();attachPlayerPage(b,true);return;
  }
  if(APP.gmTab==='expansions'&&!expansionsEnabled())APP.gmTab='players';
  const tabs=[['players','플레이어','Players'],['classes','직업','Classes'],['races','종족','Races'],['core','핵심 행동','Basic Moves'],['spells','주문','Spells'],...(expansionsEnabled()?[['expansions','확장직업','Expansion Classes']]:[]),['npcs','NPC','NPCs'],['monsters','몬스터','Monsters'],['rules','규칙','Rules'],['logs','플레이 기록','Play Log']];
  appEl().innerHTML=shell(`${partyStrip()}<div class="gm-tabs"><div class="gm-tabs-main">${tabs.map(([id,ko,en])=>`<button type="button" data-gtab="${id}" class="${APP.gmTab===id?'active':''}">${APP.language==='en'?en:ko}</button>`).join('')}</div><button type="button" data-gtab="help" class="gm-help-tab ${APP.gmTab==='help'?'active':''}">${APP.language==='en'?'Help':'도움말'}</button></div><div id="gmContent">${renderGMTab()}</div>`,`GM · ${rawEsc(APP.state.me.name)}`);
  attachPartyModal();$$('[data-gtab]').forEach(b=>b.addEventListener('click',()=>{APP.gmTab=b.dataset.gtab;renderGM()}));attachGMTab();attachSmartTextareas();
}
function renderGMTab(){if(APP.gmTab==='players')return renderGMPlayers();if(APP.gmTab==='classes')return renderGMClasses();if(APP.gmTab==='races')return renderGMRaces();if(APP.gmTab==='core')return renderGMCore();if(APP.gmTab==='spells')return renderGMSpells();if(APP.gmTab==='expansions')return renderGMExpansions();if(APP.gmTab==='npcs')return renderGMNPCs();if(APP.gmTab==='monsters')return renderGMMonsters();if(APP.gmTab==='rules')return renderGMRules();if(APP.gmTab==='help')return renderGMHelp();return renderGMLogs();}
function attachGMTab(){if(APP.gmTab==='players')attachGMPlayers();else if(APP.gmTab==='classes')attachGMClasses();else if(APP.gmTab==='races')attachGMRaces();else if(APP.gmTab==='core')attachGMCore();else if(APP.gmTab==='spells')attachGMSpells();else if(APP.gmTab==='expansions')attachGMExpansions();else if(APP.gmTab==='npcs')attachGMNPCs();else if(APP.gmTab==='monsters')attachGMMonsters();else if(APP.gmTab==='rules')attachGMRules();else if(APP.gmTab==='help')attachGMHelp();else attachGMLogs();if(['classes','races','expansions','npcs','monsters'].includes(APP.gmTab))attachSortableLists();}
function visibleHelpTopics(){
  return HELP_TOPICS.map((topic,index)=>({topic,index})).filter(({topic})=>expansionsEnabled()||topic.title!=='확장직업');
}
function helpSectionsForDisplay(t){
  let sections=[...(t.sections||[])];
  if(!expansionsEnabled()){
    sections=sections.filter(([title])=>title!=='확장직업 자료').map(([title,lines])=>[title,(lines||[]).filter(line=>!String(line).includes('확장직업'))]).filter(([,lines])=>lines.length);
  }
  if(APP.language==='en'&&t.title==='라이선스와 출처')sections=sections.filter(([title])=>title!=='한국어 공개판');
  return sections;
}
function helpLinkGroupsForDisplay(t){
  let groups=(t.link_groups||[]).map(([group,links])=>[group,[...(links||[])]]);
  if(!expansionsEnabled())groups=groups.filter(([group])=>group!=='확장직업 자료');
  if(APP.language==='en'){
    groups=groups.filter(([group])=>group!=='한국어판');
    groups=groups.map(([group,links])=>[group,group==='확장직업 자료'?links.filter(([,key])=>key!=='ud_home'):links]);
  }
  return groups;
}
function renderHelpTopicBody(t,urls){
  if(t.quickref){const core=APP.state.core_moves||[];return `<div class="help-intro">${esc(t.intro||'')}</div><div class="quickref-principles"><article><h3>GM의 목표</h3><p>환상적인 세계를 묘사한다.</p><p>캐릭터들의 삶을 모험으로 채운다.</p><p>무슨 일이 일어날지 플레이하며 알아낸다.</p></article><article><h3>운영 원칙</h3><p>캐릭터에게 말한다.</p><p>질문하고 답을 사용한다.</p><p>캐릭터의 팬이 된다.</p><p>허구에서 시작해 허구로 돌아간다.</p><p>화면 밖에서도 무엇이 일어나는지 생각한다.</p></article><article><h3>자주 쓰는 GM 행동</h3><p>불길한 진실을 드러낸다.</p><p>다가오는 위협의 징조를 보인다.</p><p>자원을 소모시킨다.</p><p>분리하거나 곤경에 빠뜨린다.</p><p>대가가 있는 기회를 제시한다.</p><p>요구조건이나 결과를 말하고 묻는다.</p></article></div><h3 class="help-inline-title">현재 캠페인 핵심 행동</h3><div class="quickref-moves">${core.map(m=>moveDetail(m,coreMoveIsBuiltin(m))).join('')||'<div class="notice">등록된 핵심 행동이 없습니다.</div>'}</div>`}
  if(t.link_groups){const groups=helpLinkGroupsForDisplay(t);return `<div class="help-intro">${esc(t.intro||'')}</div><div class="help-source-groups">${groups.map(([group,links])=>`<section class="help-source-group"><h3>${esc(group)}</h3><div class="help-source-grid">${(links||[]).map(([label,key])=>{const u=urls[key]||'';return u?`<a class="help-source-card" href="${attr(u)}" target="_blank" rel="noopener"><b>${esc(label)}</b><span>원문 열기 ↗</span></a>`:''}).join('')}</div></section>`).join('')}</div>`}
  const sections=helpSectionsForDisplay(t);return `<div class="help-intro">${esc(t.intro||'')}</div><div class="help-sections">${sections.map(([title,lines])=>`<section class="help-section"><h3>${esc(title)}</h3>${(lines||[]).map(x=>`<p>${esc(x)}</p>`).join('')}</section>`).join('')}</div>`;
}

function renderGMHelp(){const visible=visibleHelpTopics(),selected=visible.find(x=>x.index===Number(APP.helpTopic))||visible[0],i=selected?.index??0,t=selected?.topic||HELP_TOPICS[0],urls=APP.state.room.source_urls||{};APP.helpTopic=i;return `<div class="help-layout"><aside class="help-index">${visible.map(({topic,index})=>`<button data-help-topic="${index}" class="${index===i?'active':''}" type="button">${esc(topic.title)}</button>`).join('')}</aside><section class="panel help-panel"><div class="head">${esc(t.title)}</div><div class="body help-manual">${renderHelpTopicBody(t,urls)}</div></section></div>`}
function attachGMHelp(){$$('[data-help-topic]').forEach(b=>b.addEventListener('click',()=>{APP.helpTopic=Number(b.dataset.helpTopic)||0;renderGM()}))}


function renderGMClasses(){const names=Object.keys(APP.state.classes);if(APP.gmClassName&&APP.gmClassName!=='__new__'&&!names.includes(APP.gmClassName))APP.gmClassName=null;const isNew=APP.gmClassName==='__new__',name=isNew?'':(APP.gmClassName||names[0]),c=name?APP.state.classes[name]:blankClass(),builtin=!!c?._builtin;if(!isNew)APP.gmClassName=name;return `<div class="split"><aside class="side-list sortable-list"><button id="newClass" type="button">＋ 새 직업</button>${names.map(n=>{const b=classIsBuiltin(n);return `<button draggable="true" data-sort-kind="classes" data-sort-name="${attr(n)}" data-class="${attr(n)}" class="${n===name?'active':''}${b?'':' no-i18n'}" type="button">${recordEsc(n,b)}</button>`}).join('')}</aside><section class="panel gm-editor"><div class="head sticky-edit-head"><span class="${builtin?'':'no-i18n'}">${name?recordEsc(name,builtin):'새 직업'}</span><div class="inline-actions"><button id="saveClass" class="btn small" type="button">저장</button>${name?'<button id="deleteClass" class="btn small danger" type="button">삭제</button>':''}</div></div><div class="body"><div class="grid three"><label class="field"><span>직업 이름</span><input id="className" class="input" ${builtin?'':'data-i18n-value="raw"'} value="${attr(contentValue(name||'',builtin))}"></label><label class="field"><span>기본 HP</span><input id="classHp" class="input" type="number" value="${Number(c.hp)||6}"></label><label class="field"><span>기본 피해</span><select id="classDamage" class="select">${['D4','D6','D8','D10','D12'].map(d=>`<option value="${d}" ${String(c.damage||'D6').toUpperCase()===d?'selected':''}>${d}</option>`).join('')}</select></label><label class="field"><span>기본 하중</span><input id="classLoad" class="input" type="number" value="${Number.isFinite(Number(c.load))?Number(c.load):8}"></label></div>${structuredClassEditor(c,name,builtin)}</div></section></div>`;}
function editorPair(kind,i,name='',desc='',builtin=false){return `<div class="editor-row${builtin?'':' no-i18n'}" data-erow="${kind}"><div class="row-head"><input class="input" data-ename value="${attr(contentValue(name,builtin))}" placeholder="이름"><button class="btn small danger" data-rowdel type="button">삭제</button></div><textarea class="textarea smart-textarea" data-max-grow="240" data-edesc rows="4" placeholder="설명">${recordEsc(desc||'',builtin)}</textarea></div>`;}
function moveEffectNewId(){return `movefx.${Date.now().toString(36)}.${Math.random().toString(36).slice(2,8)}`}
const MOVE_EFFECT_KINDS=[
  ['spell_grant','주문 추가 습득'],['spell_level_reduce','주문 요구 레벨 낮추기'],['spell_zero','주문을 0레벨로 만들기'],
  ['move_grant','다른 직업의 행동 습득'],['class_access','다른 직업의 주문 체계 사용'],['opposite_race_feature','다른 종족 특성 함께 사용']
];
function moveEffectClassOptions(selected='',className='',allowAny=false,allowSelf=false){
  const names=Object.keys(APP.state.classes||{}),opts=[];if(allowSelf)opts.push(`<option value="" ${selected===''?'selected':''}>현재 직업</option>`);if(allowAny)opts.push(`<option value="*" ${selected==='*'?'selected':''}>${allowSelf?'모든 분류 직업':'모든 타직업'}</option>`);for(const n of names){if(n===className)continue;opts.push(`<option value="${attr(n)}" ${selected===n?'selected':''}>${recordEsc(n,classIsBuiltin(n))}</option>`)}return opts.join('');
}
function moveEffectGrantMoveChoices(source,selected=[]){const set=new Set(selected||[]),c=APP.state.classes?.[source]||{},moves=[...(c.start||[]),...(c.a25||[]),...(c.a610||[])],builtin=classIsBuiltin(source);return moves.length?moves.map(m=>`<label class="choice compact-choice${builtin?'':' no-i18n'}"><input type="checkbox" data-me-grant-move value="${attr(m.name)}" ${set.has(m.name)?'checked':''}><span>${recordEsc(m.name,builtin)}</span></label>`).join(''):'<div class="small muted">출처 직업을 고르면 함께 자동으로 줄 행동을 선택할 수 있습니다.</div>'}
function moveEffectAutoChoiceGroup(className,kind){return `auto.move_effect.${String(kind||'effect')}`}
function moveEffectDedupeControl(e={},kind='spell_grant'){
  const on=!!String(e.choice_group||'').trim(),help=kind==='spell_level_reduce'?'같은 직업의 다른 “주문 요구 레벨 낮추기” 효과에서 이미 고른 주문을 다시 고르지 못하게 합니다.':'같은 직업의 다른 “주문 추가 습득” 효과에서 이미 고른 주문을 다시 고르지 못하게 합니다.';
  return `<div class="effect-friendly-option"><label class="choice settings-choice"><input type="checkbox" data-me-dedupe ${on?'checked':''}><span><b>같은 주문 중복 선택 방지</b><small>${esc(help)}</small></span></label><input type="hidden" data-me-choice-group value="${attr(e.choice_group||'')}"></div>`;
}
function moveEffectConfigHtml(kind,e={},className=''){
  if(kind==='spell_level_reduce')return `<div class="move-effect-config-grid"><label class="field compact-field"><span>몇 단계 낮추나요?</span><select class="select" data-me-amount>${[1,2,3].map(n=>`<option value="${n}" ${Math.max(1,Number(e.amount)||1)===n?'selected':''}>${APP.language==='en'?`${n} level${n===1?'':'s'}`:`${n}단계`}</option>`).join('')}</select></label>${moveEffectDedupeControl(e,kind)}<div class="effect-result-preview"><b>플레이어에게는 이렇게 보입니다</b><span>이 행동을 얻은 뒤 현재 직업의 숫자 레벨 주문 하나를 고릅니다. 선택한 주문의 요구 레벨이 지정한 단계만큼 낮아지며, 미분류 주문은 선택할 수 없습니다.</span></div></div>`;
  if(kind==='spell_grant'){const source=e.all_classes?'*':String(e.source_class||'');return `<div class="move-effect-config-grid"><label class="field compact-field"><span>어디의 주문을 배우나요?</span><select class="select" data-me-source>${moveEffectClassOptions(source,className,true,true)}</select></label>${moveEffectDedupeControl(e,kind)}<div class="effect-result-preview"><b>플레이어에게는 이렇게 보입니다</b><span>이 행동을 얻은 뒤 조건에 맞는 분류된 주문 하나를 추가로 고릅니다. “모든 분류 직업”을 고르면 현재 직업을 포함한 모든 일반 직업 주문에서 선택합니다. 미분류 주문은 나오지 않습니다.</span></div></div>`}
  if(kind==='spell_zero'){const spells=APP.state.spells?.[className]||[],name=String(e.spell_name||'');return `<div class="move-effect-config-grid single"><label class="field"><span>어떤 주문을 0레벨로 만드나요?</span><select class="select" data-me-spell-name><option value="">주문 선택…</option>${spells.map(sp=>`<option value="${attr(sp.name)}" ${name===sp.name?'selected':''}>${recordEsc(sp.name,spellIsBuiltin(sp))} · ${recordEsc(spellLevelLabel(sp.level),spellIsBuiltin(sp))}</option>`).join('')}${name&&!spells.some(sp=>sp.name===name)?`<option value="${attr(name)}" selected>${rawEsc(name)} · 현재 목록에 없음</option>`:''}</select></label><div class="effect-result-preview"><b>플레이어에게는 이렇게 보입니다</b><span>추가 선택창은 뜨지 않습니다. 이 행동을 가지고 있는 동안 지정한 주문을 현재 직업의 0레벨 주문으로 취급합니다.</span></div></div>`}
  if(kind==='move_grant'){const source=String(e.source_class||'*');return `<div class="move-effect-config-grid"><label class="field"><span>어느 직업에서 행동을 가져오나요?</span><select class="select" data-me-source>${moveEffectClassOptions(source,className,true,false)}</select></label><label class="field"><span>추가 사용 조건 · 선택</span><input class="input" data-me-restriction value="${attr(e.restriction_note||'')}" placeholder="예: 동물 친구와 함께 행동할 때만"></label><div class="effect-result-preview"><b>플레이어에게는 이렇게 보입니다</b><span>이 행동을 얻은 뒤 다른 직업의 행동 하나를 선택합니다. “모든 타직업”이면 먼저 출처 직업을 고른 다음 행동을 고릅니다.</span></div></div>`}
  if(kind==='class_access'){const source=String(e.source_class||Object.keys(APP.state.classes||{}).find(x=>x!==className)||'');return `<div class="move-effect-config-grid"><label class="field"><span>어느 직업의 주문 체계를 사용하나요?</span><select class="select" data-me-source><option value="">출처 직업 선택…</option>${moveEffectClassOptions(source,className,false,false)}</select></label><div class="field"><span>함께 자동으로 얻는 행동 · 선택</span><div class="move-effect-grant-moves" data-me-grant-moves>${moveEffectGrantMoveChoices(source,e.grant_moves||[])}</div></div><div class="effect-result-preview"><b>플레이어에게는 이렇게 보입니다</b><span>주문 하나만 배우는 기능이 아닙니다. 지정한 다른 직업의 주문 목록과 성장에 따른 주문 사용 영역이 별도로 열립니다. 체크한 행동은 그 체계를 쓰는 데 필요한 행동으로 함께 지급할 수 있습니다.</span></div></div>`}
  if(kind==='opposite_race_feature'){const races=Object.keys(APP.state.races||{}),pair=Array.isArray(e.race_pair)?e.race_pair:[],a=pair[0]||races[0]||'',b=pair[1]||races.find(x=>x!==a)||'';const opts=x=>races.map(r=>`<option value="${attr(r)}" ${x===r?'selected':''}>${recordEsc(r,raceIsBuiltin(r))}</option>`).join('');return `<div class="move-effect-config-grid two"><label class="field"><span>첫 번째 종족</span><select class="select" data-me-race-a>${opts(a)}</select></label><label class="field"><span>두 번째 종족</span><select class="select" data-me-race-b>${opts(b)}</select></label><div class="effect-result-preview span2"><b>플레이어에게는 이렇게 보입니다</b><span>캐릭터가 두 종족 중 하나라면 다른 쪽 종족의 현재 직업 전용 특성도 함께 얻습니다. 예: 인간/엘프 중 하나인 사냥꾼이 다른 쪽 사냥꾼 종족 특성을 추가로 얻는 경우입니다.</span></div></div>`}
  return '';
}
function moveEffectEditorRow(e={},className=''){
  const kind=MOVE_EFFECT_KINDS.some(x=>x[0]===e.kind)?e.kind:'spell_grant',id=String(e.id||moveEffectNewId());
  return `<article class="move-effect-editor-row" data-move-effect-row data-effect-id="${attr(id)}"><div class="move-effect-editor-head"><label class="field compact-field"><span>이 행동을 얻으면 무엇이 바뀌나요?</span><select class="select" data-me-kind>${MOVE_EFFECT_KINDS.map(([k,l])=>`<option value="${k}" ${k===kind?'selected':''}>${esc(l)}</option>`).join('')}</select></label><button class="btn small danger" data-me-delete type="button">효과 삭제</button></div><div data-me-config>${moveEffectConfigHtml(kind,e,className)}</div></article>`;
}
function moveEffectEditor(m={},className=''){
  const rows=Array.isArray(m.move_effects)?m.move_effects:[];return `<div class="move-effects-editor"><div class="move-effects-editor-title"><b>행동 효과</b><button class="btn small" data-add-move-effect type="button">＋ 효과 추가</button></div><div class="effect-editor-guide"><b>언제 사용하나요?</b><span>행동을 얻었을 때 캐릭터에 계속 남는 변화만 설정합니다. 예: 주문을 하나 더 배우기, 주문 레벨 낮추기, 다른 직업 행동 얻기.</span><span>주사위를 굴린 뒤 10+ 또는 7–9에서 매번 고르는 선택지는 여기에 넣지 말고 행동 설명에 적으세요.</span><small>도움말 → 행동과 고급 행동에서 실제 예시를 볼 수 있습니다.</small></div><div data-move-effect-list>${rows.map(e=>moveEffectEditorRow(e,className)).join('')||'<div class="small muted move-effect-empty">설정된 행동 효과가 없습니다.</div>'}</div></div>`;
}
function basicMoveEditorPair(kind,i,m={},className='',builtin=false){return `<div class="editor-row${builtin?'':' no-i18n'}" data-erow="${kind}"><div class="row-head"><input class="input" data-ename value="${attr(contentValue(m.name||'',builtin))}" placeholder="행동 이름"><button class="btn small danger" data-rowdel type="button">삭제</button></div><textarea class="textarea smart-textarea" data-max-grow="240" data-edesc rows="4" placeholder="설명">${recordEsc(m.desc||'',builtin)}</textarea>${moveEffectEditor(m,className)}</div>`;}
function advancedMoveEditorPair(kind,i,m={},allAdvanced=[],className='',builtin=false){
  const name=String(m.name||''),desc=String(m.desc||''),has=!!m.has_requirement,requires=String(m.requires_move||''),opts=allAdvanced.filter(x=>String(x?.name||'').trim()&&String(x.name)!==name),missing=requires&&!opts.some(x=>String(x.name)===requires);
  return `<div class="editor-row advanced-rule-editor${builtin?'':' no-i18n'}" data-erow="${kind}"><div class="row-head"><input class="input" data-ename value="${attr(contentValue(name,builtin))}" placeholder="행동 이름"><button class="btn small danger" data-rowdel type="button">삭제</button></div><div class="advanced-requirement-row"><label class="choice compact-choice"><input type="checkbox" data-move-requirement ${has?'checked':''}><span>선행 조건 사용</span></label><label class="field compact-field advanced-requirement-detail" data-move-requirement-detail ${has?'':'hidden'}><span>먼저 배워야 하는 고급 행동</span><select class="select" data-move-requires><option value="">선행 행동 선택…</option>${missing?`<option value="${attr(requires)}" selected>${recordEsc(requires,builtin)} · 현재 목록에 없음</option>`:''}${opts.map(x=>`<option value="${attr(x.name)}" ${requires===String(x.name)?'selected':''}>${recordEsc(x.name,builtin)}</option>`).join('')}</select></label></div><textarea class="textarea smart-textarea" data-max-grow="240" data-edesc rows="4" placeholder="설명">${recordEsc(desc,builtin)}</textarea>${moveEffectEditor(m,className)}</div>`;
}
function moveEditor(kind,list,allAdvanced=[],className='',builtin=false){const advanced=kind==='a25'||kind==='a610';return `<div class="editor-list" data-move-editor="${kind}">${list.map((m,i)=>advanced?advancedMoveEditorPair(kind,i,m,allAdvanced,className,builtin):basicMoveEditorPair(kind,i,m,className,builtin)).join('')}</div><button class="btn small" data-addmove="${kind}" type="button">＋ 행동 추가</button>`;}
function currentAdvancedMoveNames(){return $$('[data-move-editor="a25"] [data-ename],[data-move-editor="a610"] [data-ename]').map(x=>x.value.trim()).filter(Boolean).map(name=>({name}))}
function currentClassEditorName(){return $('#className')?.value.trim()||((APP.gmClassName&&APP.gmClassName!=='__new__')?APP.gmClassName:'')}
function collectMoveEffects(moveRow){
  const className=currentClassEditorName();
  return $$('[data-move-effect-row]',moveRow).map(r=>{const kind=$('[data-me-kind]',r)?.value||'',id=r.dataset.effectId||moveEffectNewId(),e={id,kind};if(kind==='spell_level_reduce'){e.target_class='self';e.amount=Math.max(1,Number($('[data-me-amount]',r)?.value)||1);e.exclude_unclassified=true;if($('[data-me-dedupe]',r)?.checked)e.choice_group=$('[data-me-choice-group]',r)?.value.trim()||moveEffectAutoChoiceGroup(className,kind)}else if(kind==='spell_grant'){const src=$('[data-me-source]',r)?.value||'';e.count=1;e.exclude_unclassified=true;if(src==='*')e.all_classes=true;else if(src)e.source_class=src;if($('[data-me-dedupe]',r)?.checked)e.choice_group=$('[data-me-choice-group]',r)?.value.trim()||moveEffectAutoChoiceGroup(className,kind)}else if(kind==='spell_zero'){e.target_class='self';e.spell_name=$('[data-me-spell-name]',r)?.value||''}else if(kind==='move_grant'){e.source_class=$('[data-me-source]',r)?.value||'*';e.count=1;const note=$('[data-me-restriction]',r)?.value.trim();if(note)e.restriction_note=note}else if(kind==='class_access'){e.source_class=$('[data-me-source]',r)?.value||'';e.grant_moves=$$('[data-me-grant-move]:checked',r).map(x=>x.value)}else if(kind==='opposite_race_feature'){e.race_pair=[$('[data-me-race-a]',r)?.value||'',$('[data-me-race-b]',r)?.value||''].filter(Boolean)}return e}).filter(e=>e.kind);
}
function invalidMoveEffect(data){
  for(const move of [...(data.start||[]),...(data.a25||[]),...(data.a610||[])])for(const e of (move.move_effects||[])){
    if(e.kind==='spell_zero'&&!String(e.spell_name||'').trim())return `${move.name}: 0레벨로 바꿀 주문을 선택하세요.`;
    if(e.kind==='class_access'&&!String(e.source_class||'').trim())return `${move.name}: 획득할 직업 체계를 선택하세요.`;
    if(e.kind==='move_grant'&&!String(e.source_class||'').trim())return `${move.name}: 행동 출처 직업을 선택하세요.`;
    if(e.kind==='opposite_race_feature'&&(!Array.isArray(e.race_pair)||e.race_pair.length!==2||e.race_pair[0]===e.race_pair[1]))return `${move.name}: 서로 다른 두 종족을 선택하세요.`;
  }
  return '';
}
function attachMoveRequirementControls(root=document){$$('[data-move-requirement]',root).forEach(i=>{if(i.dataset.on)return;i.dataset.on='1';const sync=()=>{const row=i.closest('.editor-row'),detail=$('[data-move-requirement-detail]',row),sel=$('[data-move-requires]',row);if(detail)detail.hidden=!i.checked;if(sel)sel.disabled=!i.checked};i.addEventListener('change',sync);sync()})}
function attachMoveEffectEditors(root=document){
  $$('[data-add-move-effect]',root).forEach(b=>{if(b.dataset.on)return;b.dataset.on='1';b.addEventListener('click',()=>{const moveRow=b.closest('.editor-row'),list=$('[data-move-effect-list]',moveRow),empty=$('.move-effect-empty',list);empty?.remove();list?.insertAdjacentHTML('beforeend',moveEffectEditorRow({kind:'spell_grant'},currentClassEditorName()));attachMoveEffectEditors(moveRow)})});
  $$('[data-move-effect-row]',root).forEach(row=>{const del=$('[data-me-delete]',row),kind=$('[data-me-kind]',row);if(del&&!del.dataset.on){del.dataset.on='1';del.addEventListener('click',()=>{const list=row.parentElement;row.remove();if(list&&!$('[data-move-effect-row]',list))list.innerHTML='<div class="small muted move-effect-empty">설정된 행동 효과가 없습니다.</div>'})}if(kind&&!kind.dataset.on){kind.dataset.on='1';kind.addEventListener('change',()=>{const box=$('[data-me-config]',row);if(box)box.innerHTML=moveEffectConfigHtml(kind.value,{id:row.dataset.effectId,kind:kind.value},currentClassEditorName());attachMoveEffectEditors(row)})}const source=$('[data-me-source]',row);if(source&&!source.dataset.grantOn&&kind?.value==='class_access'){source.dataset.grantOn='1';source.addEventListener('change',()=>{const box=$('[data-me-grant-moves]',row);if(box)box.innerHTML=moveEffectGrantMoveChoices(source.value,[])})}})
}
function attachGMClasses(){
  $$('[data-class]').forEach(b=>b.addEventListener('click',()=>{APP.gmClassName=b.dataset.class;renderGM()}));$('#newClass')?.addEventListener('click',()=>{APP.gmClassName='__new__';renderGM()});
  $$('[data-addrow]').forEach(b=>b.addEventListener('click',()=>{const root=$('#alignEditor');root?.insertAdjacentHTML('beforeend',editorPair('align',0));attachRowDeletes(root||document)}));
  $$('[data-addmove]').forEach(b=>b.addEventListener('click',()=>{const kind=b.dataset.addmove,root=$(`[data-move-editor="${kind}"]`),advanced=kind==='a25'||kind==='a610',className=currentClassEditorName();root.insertAdjacentHTML('beforeend',advanced?advancedMoveEditorPair(kind,0,{},currentAdvancedMoveNames(),className):basicMoveEditorPair(kind,0,{},className));attachRowDeletes(root);attachMoveRequirementControls(root);attachMoveEffectEditors(root)}));attachRowDeletes(document);attachMoveRequirementControls(document);attachMoveEffectEditors(document);$$('[data-spellcasting-preset]').forEach(b=>b.addEventListener('click',()=>applySpellcastingPreset(b.dataset.spellcastingPreset)));
  $('#saveClass')?.addEventListener('click',saveClass);$('#deleteClass')?.addEventListener('click',deleteClass);
}
function attachRowDeletes(root){$$('[data-rowdel]',root).forEach(b=>{if(b.dataset.on)return;b.dataset.on='1';b.addEventListener('click',()=>b.closest('.editor-row').remove())});}
function collectRows(selector){return $$(selector).map(r=>{const item={name:$('[data-ename]',r)?.value.trim()||'',desc:$('[data-edesc]',r)?.value||'',move_effects:collectMoveEffects(r)},toggle=$('[data-move-requirement]',r);if(toggle){item.has_requirement=!!toggle.checked;item.requires_move=toggle.checked?($('[data-move-requires]',r)?.value||''):''}return item}).filter(x=>x.name);}
async function deleteClass(){if(!APP.gmClassName||!confirmUi(`${contentValue(APP.gmClassName,classIsBuiltin(APP.gmClassName))} 직업을 삭제할까요?`))return;try{await api(`/api/rooms/${APP.creds.room}/classes/${encodeURIComponent(APP.gmClassName)}`,{method:'DELETE'});APP.gmClassName=null;await refreshState(true)}catch(e){toast(e.message,3500)}}

function blankRace(){return {name:'',description:'',per_class:{},enabled_classes:[],spell_effects:{}}}
function raceEffectSpellOptions(className,kind,selected=0){
  const list=kind==='grant_unclassified'?(APP.state.spells?.__undefined__||[]):(APP.state.spells?.[className]||[]);
  return `<option value="">주문 선택…</option>`+list.map(sp=>`<option value="${Number(sp.id)||0}" ${Number(selected)===Number(sp.id)?'selected':''}>${recordEsc(sp.name,spellIsBuiltin(sp))} · ${recordEsc(spellLevelLabel(sp.level),spellIsBuiltin(sp))}</option>`).join('');
}
function raceEffectSourceOptions(className,selected=''){
  return `<option value="">출처 직업 선택…</option>`+Object.keys(APP.state.classes||{}).filter(x=>x!==className).map(x=>`<option value="${attr(x)}" ${String(selected)===x?'selected':''}>${recordEsc(x,classIsBuiltin(x))}</option>`).join('');
}
const RACE_EFFECT_KINDS=[
  ['cross_class_access','다른 직업 주문 추가 선택'],
  ['level_reduce','현재 직업 주문 레벨 낮추기'],
  ['grant_unclassified','특수(미분류) 주문 자동 습득']
];
function raceEffectPreviewText(className,kind){
  const cls=contentValue(className||'',classIsBuiltin(className));
  if(APP.language==='en'){
    if(kind==='cross_class_access')return `When this race is used with ${cls}, the player chooses the configured number of normal spells from the selected other class. Unclassified spells are never offered here.`;
    if(kind==='level_reduce')return `The player does not make an extra choice. With this race and ${cls}, the configured spell from the current class automatically has its required level lowered.`;
    return 'This is an exceptional automatic grant. Unclassified spells cannot be learned through normal spell choices; the configured special spell is granted automatically by this race feature.';
  }
  if(kind==='cross_class_access')return `이 종족으로 ${cls}를 플레이할 때 지정한 다른 직업의 일반 주문 중 정한 개수만큼 직접 고를 수 있습니다. 미분류 주문은 후보에 나오지 않습니다.`;
  if(kind==='level_reduce')return `플레이어가 따로 고르지 않습니다. 이 종족과 ${cls} 조합을 선택하면 지정한 현재 직업 주문의 레벨이 자동으로 낮아집니다.`;
  return '미분류 주문은 일반 주문 선택으로는 얻을 수 없습니다. 여기에서 지정한 주문은 플레이어가 고르는 것이 아니라 이 종족 특성으로 자동 습득합니다.';
}
function raceEffectConfigHtml(className,kind,e={}){
  const sid=Number(e.spell_id)||0,source=String(e.source_class||''),count=Math.max(1,Number(e.count)||1),preview=htmlEscape(raceEffectPreviewText(className,kind));
  if(kind==='cross_class_access')return `<div class="race-effect-config-grid"><label class="field compact-field"><span>어느 직업의 주문에서 고르나요?</span><select class="select" data-race-effect-source>${raceEffectSourceOptions(className,source)}</select></label><label class="field compact-field"><span>몇 개를 추가로 고르나요?</span><select class="select" data-race-effect-count>${[1,2,3,4,5].map(n=>`<option value="${n}" ${count===n?'selected':''}>${APP.language==='en'?`${n} spell${n===1?'':'s'}`:`${n}개`}</option>`).join('')}</select></label><div class="effect-result-preview"><b>플레이어에게는 이렇게 보입니다</b><span>${preview}</span></div></div>`;
  if(kind==='level_reduce')return `<div class="race-effect-config-grid"><label class="field"><span>어떤 주문의 레벨을 낮추나요?</span><select class="select" data-race-effect-spell>${raceEffectSpellOptions(className,kind,sid)}</select></label><label class="field compact-field"><span>몇 단계 낮추나요?</span><select class="select" data-race-effect-amount>${[1,2,3].map(n=>`<option value="${n}" ${Math.max(1,Number(e.amount)||1)===n?'selected':''}>${APP.language==='en'?`${n} level${n===1?'':'s'}`:`${n}단계`}</option>`).join('')}</select></label><div class="effect-result-preview"><b>플레이어에게는 이렇게 보입니다</b><span>${preview}</span></div></div>`;
  return `<div class="race-effect-config-grid single"><label class="field"><span>자동으로 줄 특수 주문</span><select class="select" data-race-effect-spell>${raceEffectSpellOptions(className,'grant_unclassified',sid)}</select></label><div class="effect-result-preview warn"><b>예외적인 자동 지급 기능입니다</b><span>${preview}</span></div></div>`;
}
function raceSpellEffectRow(className,e={}){
  const allowed=new Set(RACE_EFFECT_KINDS.map(x=>x[0])),kind=allowed.has(e.kind)?e.kind:'level_reduce';
  return `<article class="race-spell-effect-row" data-race-effect-row data-race-effect-class="${attr(className)}"><div class="race-effect-row-head"><label class="field compact-field race-effect-kind-field"><span>이 종족 특성은 무엇을 하나요?</span><select class="select" data-race-effect-kind>${RACE_EFFECT_KINDS.map(([k,l])=>`<option value="${k}" ${kind===k?'selected':''}>${esc(l)}</option>`).join('')}</select></label><button class="btn small danger" data-race-effect-del type="button">효과 삭제</button></div><div data-race-effect-config>${raceEffectConfigHtml(className,kind,e)}</div></article>`;
}
function renderGMRaces(){
  const names=Object.keys(APP.state.races||{}),isNew=APP.gmRaceName==='__new__',name=isNew?'':(APP.gmRaceName||names[0]||''),r=name?(APP.state.races[name]||blankRace()):blankRace();if(!isNew)APP.gmRaceName=name;
  const classes=Object.keys(APP.state.classes),enabled=new Set(r.enabled_classes||Object.entries(r.per_class||{}).filter(([,v])=>String(v||'').trim()).map(([k])=>k)),effects=r.spell_effects||{};
  const cards=classes.map(c=>{const rows=(effects[c]||[]).map(e=>raceSpellEffectRow(c,e)).join(''),useLabel=APP.language==='en'?`Use this race for <b>${recordEsc(c,classIsBuiltin(c))}</b>`:`<b>${recordEsc(c,classIsBuiltin(c))}</b>에서 이 종족 사용`,descLabel=APP.language==='en'?`${recordEsc(c,classIsBuiltin(c))} Race Feature`:`${recordEsc(c,classIsBuiltin(c))} ${htmlEscape(translateUiText('전용 종족 설명'))}`;return `<article class="race-class-rule"><label class="choice race-enabled"><input type="checkbox" data-race-enabled="${attr(c)}" ${enabled.has(c)?'checked':''}><span>${useLabel}</span></label><label class="field"><span>${descLabel}</span><textarea class="textarea smart-textarea" data-max-grow="180" data-race-class="${attr(c)}" placeholder="이 직업에서 보일 종족 행동/설명">${recordEsc((r.per_class||{})[c]||'',!!r._builtin)}</textarea></label><div class="race-spell-effects"><div class="race-effect-head"><b>주문 관련 특성</b><button class="btn small" data-add-race-effect="${attr(c)}" type="button">＋ 효과 추가</button></div><div class="small muted">종족 설명에 적힌 주문 관련 규칙을 실제 기능으로 연결합니다. 각 효과에서 ‘플레이어에게는 이렇게 보입니다’ 설명을 확인한 뒤 설정하세요.</div><div data-race-effect-list="${attr(c)}">${rows||'<div class="small muted race-effect-empty">설정된 주문 효과가 없습니다.</div>'}</div></div></article>`}).join('');
  return `<div class="split"><aside class="side-list sortable-list"><button id="newRace" type="button">＋ 새 종족</button>${names.map(n=>{const b=raceIsBuiltin(n);return `<button draggable="true" data-sort-kind="races" data-sort-name="${attr(n)}" data-race="${attr(n)}" class="${n===name?'active':''}${b?'':' no-i18n'}" type="button">${recordEsc(n,b)}</button>`}).join('')}</aside><section class="panel gm-editor"><div class="head sticky-edit-head"><span class="${r?._builtin?'':'no-i18n'}">${name?recordEsc(name,!!r?._builtin):'새 종족'}</span><div class="inline-actions"><button id="saveRace" class="btn small" type="button">저장</button>${name?'<button id="deleteRace" class="btn small danger" type="button">삭제</button>':''}</div></div><div class="body"><label class="field"><span>종족 이름</span><input id="raceName" class="input" value="${attr(contentValue(name,!!r?._builtin))}"></label><label class="field"><span>공통 설명</span><textarea id="raceDesc" class="textarea smart-textarea" data-max-grow="220">${recordEsc(r.description||'',!!r?._builtin)}</textarea></label><h3>직업별 사용 설정 / 설명</h3><div class="notice race-effect-guide"><b>종족 설명과 실제 기능은 따로 관리합니다.</b><br>위 설명은 플레이어가 읽는 규칙 문장이고, 아래 ‘주문 관련 특성’은 그 문장을 시스템 기능으로 연결하는 곳입니다. 예: 다른 직업 주문 고르기, 특정 주문 레벨 낮추기, 특수 주문 자동 지급.</div><div class="editor-list race-class-list">${cards||'<div class="notice">먼저 직업을 하나 만들어주세요.</div>'}</div></div></section></div>`;
}
function refreshRaceEffectRow(row,keep=true){
  const c=row.dataset.raceEffectClass||'',kind=$('[data-race-effect-kind]',row)?.value||'level_reduce',old={kind};
  if(keep){old.spell_id=Number($('[data-race-effect-spell]',row)?.value)||0;old.source_class=$('[data-race-effect-source]',row)?.value||'';old.amount=Math.max(1,Number($('[data-race-effect-amount]',row)?.value)||1);old.count=Math.max(1,Number($('[data-race-effect-count]',row)?.value)||1)}
  const box=$('[data-race-effect-config]',row);if(box)box.innerHTML=raceEffectConfigHtml(c,kind,old);
}
function attachRaceEffectRows(){
  $$('[data-add-race-effect]').forEach(b=>{if(b.dataset.on)return;b.dataset.on='1';b.addEventListener('click',()=>{const c=b.dataset.addRaceEffect,list=$(`[data-race-effect-list="${CSS.escape(c)}"]`);if(!list)return;$('.race-effect-empty',list)?.remove();list.insertAdjacentHTML('beforeend',raceSpellEffectRow(c,{}));attachRaceEffectRows()})});
  $$('[data-race-effect-kind]').forEach(x=>{if(x.dataset.on)return;x.dataset.on='1';x.addEventListener('change',()=>{refreshRaceEffectRow(x.closest('[data-race-effect-row]'),false);attachRaceEffectRows()})});
  $$('[data-race-effect-del]').forEach(b=>{if(b.dataset.on)return;b.dataset.on='1';b.addEventListener('click',()=>{const row=b.closest('[data-race-effect-row]'),list=row?.parentElement;row?.remove();if(list&&!$('[data-race-effect-row]',list))list.innerHTML='<div class="small muted race-effect-empty">설정된 주문 효과가 없습니다.</div>'})});
}
function attachGMRaces(){
  $$('[data-race]').forEach(b=>b.addEventListener('click',()=>{APP.gmRaceName=b.dataset.race;renderGM()}));$('#newRace')?.addEventListener('click',()=>{APP.gmRaceName='__new__';renderGM()});
  attachRaceEffectRows();
  $('#saveRace')?.addEventListener('click',async()=>{const name=$('#raceName').value.trim();if(!name)return toast('종족 이름을 입력하세요.');const per={},enabled=[],spell_effects={};$$('[data-race-class]').forEach(t=>{per[t.dataset.raceClass]=t.value||''});$$('[data-race-enabled]').forEach(x=>{if(x.checked)enabled.push(x.dataset.raceEnabled)});$$('[data-race-effect-row]').forEach(row=>{const c=row.dataset.raceEffectClass||'',kind=$('[data-race-effect-kind]',row)?.value||'level_reduce';if(!c)return;const item={kind};if(kind==='cross_class_access'){const src=$('[data-race-effect-source]',row)?.value||'',count=Math.max(1,Number($('[data-race-effect-count]',row)?.value)||1);if(!src)return;item.source_class=src;item.count=count}else{const spell_id=Number($('[data-race-effect-spell]',row)?.value)||0;if(!spell_id)return;item.spell_id=spell_id;if(kind==='level_reduce')item.amount=Math.max(1,Number($('[data-race-effect-amount]',row)?.value)||1)}(spell_effects[c]||(spell_effects[c]=[])).push(item)});const original=APP.gmRaceName&&APP.gmRaceName!=='__new__'?(APP.state.races?.[APP.gmRaceName]||null):null,edited={name,description:$('#raceDesc').value,per_class:per,enabled_classes:enabled,spell_effects},clean=original?restoreDisplayedBuiltIn(edited,{name:APP.gmRaceName,...original}):edited;try{await api(`/api/rooms/${APP.creds.room}/races`,{method:'PUT',body:JSON.stringify({name:clean.name,old_name:APP.gmRaceName==='__new__'?null:APP.gmRaceName,data:clean})});APP.gmRaceName=name;await refreshState(true);toast('종족 저장')}catch(e){toast(e.message,3500)}});
  $('#deleteRace')?.addEventListener('click',async()=>{if(!APP.gmRaceName||!confirmUi(`${contentValue(APP.gmRaceName,raceIsBuiltin(APP.gmRaceName))} 종족을 삭제할까요?`))return;try{await api(`/api/rooms/${APP.creds.room}/races/${encodeURIComponent(APP.gmRaceName)}`,{method:'DELETE'});APP.gmRaceName=null;await refreshState(true)}catch(e){toast(e.message,3500)}});attachSmartTextareas();
}

function renderGMCore(){
  const list=APP.state.core_moves||[];
  if(APP.gmCoreName==='__new__'){}
  else if(!APP.gmCoreName||!list.some(m=>m.name===APP.gmCoreName))APP.gmCoreName=list[0]?.name||'__new__';
  const isNew=APP.gmCoreName==='__new__',m=isNew?{name:'',desc:''}:(list.find(x=>x.name===APP.gmCoreName)||{name:'',desc:''});
  return `<div class="split classified-editor"><aside class="side-list classified-side"><button id="newCoreMove" type="button">＋ 새 핵심 행동</button>${list.map(x=>`<button data-core-select="${attr(x.name)}" class="${!isNew&&x.name===APP.gmCoreName?'active':''}${coreMoveIsBuiltin(x)?'':' no-i18n'}" type="button">${recordEsc(x.name,coreMoveIsBuiltin(x))}</button>`).join('')}</aside><section class="panel gm-editor"><div class="head sticky-edit-head"><span>${isNew?'새 핵심 행동':recordEsc(m.name,coreMoveIsBuiltin(m))}</span><div class="inline-actions"><button id="saveCoreMove" class="btn small" type="button">저장</button>${isNew?'':'<button id="deleteCoreMove" class="btn small danger" type="button">삭제</button>'}</div></div><div class="body"><label class="field"><span>행동 이름</span><input id="coreMoveName" class="input" value="${attr(contentValue(m.name,coreMoveIsBuiltin(m)))}"></label><label class="field"><span>행동 설명</span><textarea id="coreMoveDesc" class="textarea smart-textarea" data-max-grow="420">${recordEsc(m.desc||'',coreMoveIsBuiltin(m))}</textarea></label></div></section></div>`;
}
function attachGMCore(){
  $$('[data-core-select]').forEach(b=>b.addEventListener('click',()=>{APP.gmCoreName=b.dataset.coreSelect;renderGM()}));
  $('#newCoreMove')?.addEventListener('click',()=>{APP.gmCoreName='__new__';renderGM()});
  $('#saveCoreMove')?.addEventListener('click',async()=>{let name=$('#coreMoveName')?.value.trim(),desc=$('#coreMoveDesc')?.value||'';if(!name)return toast('행동 이름을 입력하세요.');const original=(APP.state.core_moves||[]).find(x=>x.name===APP.gmCoreName);if(original?._builtin){const clean=restoreDisplayedBuiltIn({name,desc},{name:original.name,desc:original.desc});name=clean.name;desc=clean.desc}try{await api(`/api/rooms/${APP.creds.room}/core-move`,{method:'PUT',body:JSON.stringify({name,desc,old_name:APP.gmCoreName==='__new__'?null:APP.gmCoreName})});APP.gmCoreName=name;await refreshState(true);toast('핵심 행동 저장')}catch(e){toast(e.message,3500)}});
  $('#deleteCoreMove')?.addEventListener('click',async()=>{const name=APP.gmCoreName;if(!name||name==='__new__'||!confirmUi(`${contentValue(name,coreMoveIsBuiltin((APP.state.core_moves||[]).find(x=>x.name===name)))}을 삭제할까요?`))return;try{await api(`/api/rooms/${APP.creds.room}/core-move/${encodeURIComponent(name)}`,{method:'DELETE'});APP.gmCoreName=null;await refreshState(true)}catch(e){toast(e.message,3500)}});
}

function attachGMSpells(){
  $('#spellClass')?.addEventListener('change',e=>{APP.gmSpellClass=e.target.value;APP.gmSpellId=null;renderGM()});
  $$('[data-spell-select]').forEach(b=>b.addEventListener('click',()=>{APP.gmSpellId=Number(b.dataset.spellSelect);renderGM()}));
  $('#addSpell')?.addEventListener('click',()=>{APP.gmSpellId='__new__';renderGM()});
  const levelInput=$('#spellLevel'),validateLevel=()=>{if(!levelInput)return {ok:true,value:''};const result=validateSpellLevelValue(levelInput.value);levelInput.setCustomValidity(result.ok?'':translateUiText(result.message));levelInput.title=translateUiText(result.ok?(result.effective===0?'문자 분류는 0레벨 주문으로 취급됩니다.':`레벨 ${result.effective} 주문`):result.message);return result};
  levelInput?.addEventListener('input',validateLevel);levelInput?.addEventListener('blur',validateLevel);validateLevel();
  $('#saveSpell')?.addEventListener('click',async()=>{const name=$('#spellName')?.value.trim(),checked=validateLevel(),desc=$('#spellDesc')?.value||'';if(!name)return toast('주문 이름을 입력하세요.');if(!checked.ok){levelInput?.reportValidity();return toast(checked.message)}let level=checked.value,current=(APP.state.spells[APP.gmSpellClass]||[]).find(x=>Number(x.id)===Number(APP.gmSpellId));let clean={name,level,desc};if(current?._builtin)clean=restoreDisplayedBuiltIn(clean,{name:current.name,level:String(current.level??''),desc:current.desc||''});const payload={id:APP.gmSpellId==='__new__'||!current?null:Number(current.id),class_name:APP.gmSpellClass,name:clean.name,level:clean.level,desc:clean.desc};try{await api(`/api/rooms/${APP.creds.room}/spell`,{method:'PUT',body:JSON.stringify(payload)});APP.gmSpellId=null;await refreshState(true);const hit=(APP.state.spells[APP.gmSpellClass]||[]).find(x=>x.name===name);APP.gmSpellId=hit?.id||null;renderGM();toast('주문 저장')}catch(e){toast(e.message,3500)}});
  $('#deleteSpell')?.addEventListener('click',async()=>{const id=Number(APP.gmSpellId)||0;if(!id||!confirmUi('이 주문을 삭제할까요?'))return;try{await api(`/api/rooms/${APP.creds.room}/spell/${id}`,{method:'DELETE'});APP.gmSpellId=null;await refreshState(true)}catch(e){toast(e.message,3500)}});
}

function blankExpansion(){return {name:'',gm_condition:'',public_intro:'',data:{legend_move:{name:'',desc:''},class_moves:[],resource:{name:'',max:0},theme:{page_background:'#f2f0e8',background:'#ffffff',text:'#181818',accent:'#181818'},hidden:false,sort_order:9999}};}
function renderGMExpansions(){
  let list=[...(APP.state.expansions||[])];if(APP.expansionSort==='name')list.sort((a,b)=>a.name.localeCompare(b.name,'ko'));else if(APP.expansionSort==='created')list.sort((a,b)=>String(a.created_at).localeCompare(String(b.created_at)));else list.sort((a,b)=>(Number(a.data?.sort_order)||9999)-(Number(b.data?.sort_order)||9999)||a.name.localeCompare(b.name,'ko'));
  if(APP.gmExpansionId&&!list.some(x=>x.id===APP.gmExpansionId))APP.gmExpansionId=null;const e=list.find(x=>x.id===APP.gmExpansionId)||null;
  return `<div class="split"><aside class="side-list expansion-side sortable-list"><button id="newExpansion" type="button">＋ 새 확장직업</button><label class="field compact-field"><span>정렬</span><select id="expSort" class="select"><option value="manual" ${APP.expansionSort==='manual'?'selected':''}>수동 정렬</option><option value="name" ${APP.expansionSort==='name'?'selected':''}>이름순</option><option value="created" ${APP.expansionSort==='created'?'selected':''}>생성순</option></select></label>${list.map((x,i)=>{const t=x.data?.theme||{},hid=!!x.data?.hidden;return `<div draggable="${APP.expansionSort==='manual'?'true':'false'}" data-sort-kind="expansions" data-sort-id="${x.id}" class="exp-list-row ${hid?'is-hidden':''}"><button data-exp="${x.id}" class="${x.id===APP.gmExpansionId?'active':''}" type="button"><i class="theme-dot" style="background:${attr(t.accent||'#181818')}"></i>${hid?'<span class="hidden-tag">히든</span>':''}<span class="${x.data?.builtin?'':'no-i18n'}">${recordEsc(x.name,!!x.data?.builtin)}</span></button>${APP.expansionSort==='manual'?``:''}</div>`}).join('')}</aside><section class="panel gm-editor"><div class="head sticky-edit-head"><span class="${e&&!e.data?.builtin?'no-i18n':''}">${e?recordEsc(e.name,!!e.data?.builtin):'새 확장직업'}</span><div class="inline-actions"><button id="saveExpansion" class="btn small" type="button">저장</button>${e?'<button id="deleteExpansion" class="btn small danger" type="button">삭제</button>':''}</div></div><div class="body">${expansionEditor(e||blankExpansion())}</div></section></div>`;
}
function expansionMoveText(m={}){const parts=[];if(m.trigger)parts.push(`발동: ${m.trigger}`);if(m.roll)parts.push(`판정: ${m.roll}`);if(m.success)parts.push(`성공: ${m.success}`);if(m.result_12)parts.push(`12+: ${m.result_12}`);if(m.result_10)parts.push(`10+: ${m.result_10}`);if(m.result_7)parts.push(`7–9: ${m.result_7}`);if(m.result_6)parts.push(`6-: ${m.result_6}`);if((m.choices||[]).length)parts.push(`선택지:
${m.choices.map(x=>`• ${x}`).join('\n')}`);if(m.desc)parts.push(m.desc);if(m.notes)parts.push(m.notes);return parts.filter(Boolean).join('\n\n')}
function expMoveEditorRow(kind,m={},builtin=false){return `<div class="editor-row exp-move-editor" data-exp-move-kind="${attr(kind)}"><div class="row-head"><input class="input" ${builtin?'':'data-i18n-value="raw"'} data-x-name value="${attr(m.name||'')}" placeholder="행동 이름"><button class="btn small danger" data-rowdel type="button">삭제</button></div><label class="field"><span>행동 설명</span><textarea class="textarea smart-textarea" data-min-grow="110" data-max-grow="260" data-x-desc placeholder="판정, 성공 결과, 선택지 등 필요한 내용을 자유롭게 적으세요.">${builtin?htmlEscape(displayMultilineContent(expansionMoveText(m))):rawEsc(expansionMoveText(m))}</textarea></label></div>`}
function collectExpMove(row){return {name:$('[data-x-name]',row)?.value.trim()||'',desc:$('[data-x-desc]',row)?.value||''}}

function expansionEditor(e){const d=e.data||blankExpansion().data,t=d.theme||{},builtin=!!d.builtin;return `<div class="expansion-title-line"><label class="field expansion-title-field"><span>확장직업 이름</span><input id="expName" class="input" ${builtin?'':'data-i18n-value="raw"'} value="${attr(e.name||'')}"></label><label class="hidden-toggle compact"><input id="expHidden" type="checkbox" ${d.hidden?'checked':''}><span>히든</span></label></div><label class="field" style="margin-top:9px"><span>해금 조건 · 플레이어에게는 숨김</span><textarea id="expCondition" class="textarea smart-textarea" data-max-grow="240">${recordEsc(e.gm_condition||'',builtin)}</textarea></label><label class="field" style="margin-top:9px"><span>플레이어 공개 소개</span><textarea id="expIntro" class="textarea smart-textarea" data-max-grow="240">${recordEsc(e.public_intro||'',builtin)}</textarea></label>
  <h3>개인 자원</h3><div class="exp-resource-editor"><label class="field"><span>자원 이름</span><input id="expResourceName" class="input" ${builtin?'':'data-i18n-value="raw"'} value="${attr(d.resource?.name||'')}" placeholder="비우면 개인 자원을 사용하지 않음"></label><label class="field"><span>최대치</span><input id="expResourceMax" class="input" type="number" min="0" max="9999" value="${Math.max(0,Number(d.resource?.max)||0)}"><small>0 = 상한 없음</small></label></div>
  <h3>테마</h3><div class="theme-editor"><label>페이지 배경색 <input id="themePageBg" type="color" value="${attr(t.page_background||'#f2f0e8')}"></label><label>창 배경색 <input id="themeBg" type="color" value="${attr(t.background||'#ffffff')}"></label><label>텍스트색 <input id="themeText" type="color" value="${attr(t.text||'#181818')}"></label><label>강조색 <input id="themeAccent" type="color" value="${attr(t.accent||'#181818')}"></label><div id="themePreview" class="theme-preview"><div class="theme-preview-card">확장직업 미리보기<br><b>전설행동 / 직업 행동</b></div></div><div id="contrastWarn" class="small"></div></div>
  <h3>전설행동</h3><div id="legendEditor">${expMoveEditorRow('legend',d.legend_move||{},builtin)}</div>
  <h3>직업 행동</h3><div id="expClassMoves" class="editor-list">${(d.class_moves||[]).map(m=>expMoveEditorRow('class',m,builtin)).join('')}</div><button id="addExpClassMove" class="btn small" type="button">＋ 직업 행동</button>
  
  ${e.id?`<h3>플레이어에게 해금 제안</h3><div class="grid two"><select id="grantChar" class="select"><option value="">캐릭터 선택…</option>${APP.state.party.map(p=>`<option value="${p.character_id}">${rawEsc(p.character_name||p.display_name)}</option>`).join('')}</select><label class="choice"><input id="grantVisible" type="checkbox"><span>수락 후 파티에게 공개</span></label></div><label class="field" style="margin-top:8px"><span>플레이어에게 보낼 메시지</span><textarea id="grantMessage" class="textarea smart-textarea" data-max-grow="220" placeholder="예: 어둠 속에서 누군가가 당신을 지켜보고 있습니다."></textarea></label><button id="grantBtn" class="btn dark" type="button">선택한 플레이어에게 제안</button><div class="grant-list">${(APP.state.grants||[]).filter(g=>g.expansion_id===e.id).map(g=>{const p=APP.state.party.find(x=>x.character_id===g.character_id);return `<div class="grant-row"><span>${rawEsc(p?.character_name||`#${g.character_id}`)} · ${g.status==='pending'?'제안 대기':g.status==='accepted'?'수락':'거절'}</span><button class="btn small danger" data-revoke="${g.id}" type="button">회수</button></div>`}).join('')}</div>`:''}`}

function attachGMExpansions(){
  $('#expSort')?.addEventListener('change',e=>{APP.expansionSort=e.target.value;renderGM()});
  $$('[data-exp]').forEach(b=>b.addEventListener('click',()=>{APP.gmExpansionId=Number(b.dataset.exp);renderGM()}));$('#newExpansion')?.addEventListener('click',()=>{APP.gmExpansionId=null;renderGM()});
  $('#addExpClassMove')?.addEventListener('click',()=>{const cur=(APP.state.expansions||[]).find(x=>x.id===APP.gmExpansionId),builtin=!!cur?.data?.builtin;$('#expClassMoves').insertAdjacentHTML('beforeend',expMoveEditorRow('class',{},builtin));attachRowDeletes($('#expClassMoves'));attachSmartTextareas()});attachRowDeletes(document);
  ['themePageBg','themeBg','themeText','themeAccent'].forEach(id=>$(`#${id}`)?.addEventListener('input',updateThemePreview));updateThemePreview();attachSmartTextareas();
  $('#saveExpansion')?.addEventListener('click',saveExpansion);$('#deleteExpansion')?.addEventListener('click',deleteExpansion);$('#grantBtn')?.addEventListener('click',grantExpansion);$$('[data-revoke]').forEach(b=>b.addEventListener('click',()=>revokeExpansion(Number(b.dataset.revoke))));
}
function updateThemePreview(){const page=$('#themePageBg')?.value||'#f2f0e8',bg=$('#themeBg')?.value||'#fff',tx=$('#themeText')?.value||'#181818',ac=$('#themeAccent')?.value||'#181818',p=$('#themePreview');if(p){p.style.background=page;p.style.color=tx;p.style.borderColor=ac;const card=$('.theme-preview-card',p);if(card){card.style.background=bg;card.style.color=tx;card.style.borderColor=ac}}const ratio=contrastRatio(bg,tx),w=$('#contrastWarn');if(w){w.textContent=APP.language==='en'?`Text Contrast ${ratio.toFixed(1)}:1 · ${ratio<4.5?'Low readability':'Good'}`:`텍스트 대비 ${ratio.toFixed(1)}:1 ${ratio<4.5?'· 가독성 낮음':'· 양호'}`;w.className=`small ${ratio<4.5?'danger-text':'muted'}`;}}
async function saveExpansion(){let name=$('#expName').value.trim();if(!name)return toast('확장직업 이름을 입력하세요.');const legendRow=$('#legendEditor .editor-row'),legend=collectExpMove(legendRow),existing=(APP.state.expansions||[]).find(x=>x.id===APP.gmExpansionId),cur=existing?.data||{};let payload={name,gm_condition:$('#expCondition').value,public_intro:$('#expIntro').value,data:{legend_move:legend,class_moves:$$('#expClassMoves .editor-row').map(collectExpMove).filter(x=>x.name),resource:{name:$('#expResourceName')?.value.trim()||'',max:Math.max(0,Number($('#expResourceMax')?.value)||0)},hidden:!!$('#expHidden')?.checked,sort_order:Number(cur.sort_order)||((APP.state.expansions||[]).reduce((m,x)=>Math.max(m,Number(x.data?.sort_order)||0),0)+1),theme:{page_background:$('#themePageBg').value,background:$('#themeBg').value,text:$('#themeText').value,accent:$('#themeAccent').value},source_url:cur.source_url||'',source_note:cur.source_note||'',builtin:!!cur.builtin}};if(existing?.data?.builtin)payload=restoreDisplayedBuiltIn(payload,{name:existing.name,gm_condition:existing.gm_condition,public_intro:existing.public_intro,data:existing.data});try{const url=APP.gmExpansionId?`/api/rooms/${APP.creds.room}/expansions/${APP.gmExpansionId}`:`/api/rooms/${APP.creds.room}/expansions`,r=await api(url,{method:APP.gmExpansionId?'PUT':'POST',body:JSON.stringify(payload)});if(!APP.gmExpansionId)APP.gmExpansionId=r.id;await refreshState(true);toast('확장직업 저장')}catch(e){toast(e.message,3500)}}
async function deleteExpansion(){if(!APP.gmExpansionId||!confirmUi('이 확장직업을 삭제할까요? 해금 기록도 함께 삭제됩니다.'))return;try{await api(`/api/rooms/${APP.creds.room}/expansions/${APP.gmExpansionId}`,{method:'DELETE'});APP.gmExpansionId=null;await refreshState(true)}catch(e){toast(e.message,3500)}}
async function grantExpansion(){const cid=Number($('#grantChar').value);if(!cid)return toast('캐릭터를 선택하세요.');try{await api(`/api/rooms/${APP.creds.room}/expansions/${APP.gmExpansionId}/grant`,{method:'POST',body:JSON.stringify({character_id:cid,visible_to_party:$('#grantVisible').checked,message:$('#grantMessage')?.value||''})});await refreshState(true);toast('플레이어에게 확장직업 제안을 보냈습니다.')}catch(e){toast(e.message,3500)}}
async function revokeExpansion(id){if(!confirmUi('이 확장직업을 회수할까요? 해당 확장직업의 보유 상태도 함께 정리됩니다.'))return;try{await api(`/api/rooms/${APP.creds.room}/grants/${id}`,{method:'DELETE'});await refreshState(true);toast('확장직업을 회수했습니다.')}catch(e){toast(e.message,3500)}}

function attachSmartTextareas(){ $$('.smart-textarea').forEach(t=>{autoGrow(t);if(t.dataset.smartAttached)return;t.dataset.smartAttached='1';t.addEventListener('input',()=>autoGrow(t));const wrap=t.parentElement;if(wrap&&!wrap.querySelector(':scope > .expand-text-btn')){const b=document.createElement('button');b.type='button';b.className='btn small expand-text-btn';b.textContent=translateUiText('크게 편집');b.addEventListener('click',()=>openTextEditor(t));wrap.appendChild(b)}})}
function openTextEditor(target){document.body.insertAdjacentHTML('beforeend',`<div class="modal" id="textEditorModal"><div class="modal-card text-editor-modal"><div class="modal-head"><b>${esc(translateUiText('긴 설명 편집'))}</b><button class="btn small" data-close type="button">${esc(translateUiText('닫기'))}</button></div><div class="modal-body"><textarea id="bigTextEditor" class="textarea no-i18n">${rawEsc(target.value)}</textarea><button id="applyBigText" class="btn dark large" type="button">${esc(translateUiText('내용 적용'))}</button></div></div></div>`);$('#applyBigText').onclick=()=>{target.value=$('#bigTextEditor').value;target.dispatchEvent(new Event('input',{bubbles:true}));$('#textEditorModal').remove()};$('#textEditorModal [data-close]').onclick=()=>$('#textEditorModal').remove()}

function blankNPC(){return {id:null,name:'',data:{appearance:'',description:'',bonds:[]}}}

function renderGMNPCs(){const raw=APP.state.npcs||[],list=[...raw].sort((a,b)=>(Number(!!b.data?.favorite)-Number(!!a.data?.favorite))||((a.sort_order||9999)-(b.sort_order||9999))||a.name.localeCompare(b.name));if(APP.gmNpcId&&!list.some(x=>x.id===APP.gmNpcId))APP.gmNpcId=null;const cur=list.find(x=>x.id===APP.gmNpcId)||blankNPC();const fav=list.filter(x=>x.data?.favorite),rest=list.filter(x=>!x.data?.favorite);const items=(arr)=>arr.map(n=>`<button draggable="true" data-sort-kind="npcs" data-sort-id="${n.id}" data-npc="${n.id}" class="${n.id===APP.gmNpcId?'active':''}" type="button">${n.data?.favorite?'★ ':''}${rawEsc(n.name)}</button>`).join('');return `<div class="split"><aside class="side-list sortable-list"><button id="newNpc" type="button">＋ 새 NPC</button>${fav.length?`<div class="side-section-label">★ 즐겨찾기</div>${items(fav)}<div class="side-section-label">전체 NPC</div>`:''}${items(rest)||(!fav.length?'<div class="side-empty">등록된 NPC가 없습니다.</div>':'')}</aside><section class="panel gm-editor"><div class="head sticky-edit-head"><span>${cur.id?rawEsc(cur.name):'새 NPC'}</span><div class="inline-actions"><button id="saveNpc" class="btn small" type="button">저장</button>${cur.id?'<button id="deleteNpc" class="btn small danger" type="button">삭제</button>':''}</div></div><div class="body"><div class="npc-title-row"><label class="field"><span>NPC 이름</span><input id="npcName" class="input" value="${attr(cur.name||'')}"></label><label class="favorite-toggle"><input id="npcFavorite" type="checkbox" ${cur.data?.favorite?'checked':''}> ★ 즐겨찾기</label></div><label class="field"><span>외형</span><textarea id="npcAppearance" class="textarea smart-textarea" data-max-grow="220">${rawEsc(cur.data?.appearance||'')}</textarea></label><label class="field"><span>설명</span><textarea id="npcDescription" class="textarea smart-textarea" data-max-grow="280">${rawEsc(cur.data?.description||'')}</textarea></label><h3>관계</h3><div id="npcBonds" class="editor-list">${(cur.data?.bonds||[]).map(npcBondRow).join('')}</div><button id="addNpcBond" class="btn small" type="button">＋ 관계 추가</button></div></section></div>`}
function attachGMNPCs(){$$('[data-npc]').forEach(b=>b.addEventListener('click',()=>{APP.gmNpcId=Number(b.dataset.npc);renderGM()}));$('#newNpc')?.addEventListener('click',()=>{APP.gmNpcId=null;renderGM()});$('#addNpcBond')?.addEventListener('click',()=>{$('#npcBonds').insertAdjacentHTML('beforeend',npcBondRow({}));attachNpcBondDeletes();attachSmartTextareas();attachNpcBigEditors()});attachNpcBondDeletes();attachNpcBigEditors();$('#saveNpc')?.addEventListener('click',saveNpc);$('#deleteNpc')?.addEventListener('click',deleteNpc)}
function attachNpcBigEditors(){$$('[data-big-edit-target="npc-bond"]').forEach(b=>{if(b.dataset.on)return;b.dataset.on='1';b.addEventListener('click',()=>{const ta=$('[data-npc-bond-desc]',b.closest('.npc-bond-row'));if(ta)openTextEditor(ta)})})}

function attachNpcBondDeletes(){$$('[data-npc-bond-del]').forEach(b=>{if(b.dataset.on)return;b.dataset.on='1';b.addEventListener('click',()=>b.closest('.npc-bond-row')?.remove())})}
async function saveNpc(){const name=$('#npcName')?.value.trim();if(!name)return toast('NPC 이름을 입력하세요.');const bonds=$$('.npc-bond-row').map(r=>({name:$('[data-npc-bond-name]',r)?.value||'',desc:$('[data-npc-bond-desc]',r)?.value||''})).filter(x=>x.name.trim()||x.desc.trim());try{const r=await api(`/api/rooms/${APP.creds.room}/npcs`,{method:'PUT',body:JSON.stringify({id:APP.gmNpcId||null,name,data:{appearance:$('#npcAppearance')?.value||'',description:$('#npcDescription')?.value||'',bonds,favorite:!!$('#npcFavorite')?.checked}})});APP.gmNpcId=r.id;await refreshState(true);toast('NPC를 저장했습니다.')}catch(e){toast(e.message,3500)}}

async function deleteNpc(){if(!APP.gmNpcId||!confirmUi('이 NPC를 삭제할까요?'))return;try{await api(`/api/rooms/${APP.creds.room}/npcs/${APP.gmNpcId}`,{method:'DELETE'});APP.gmNpcId=null;await refreshState(true);toast('NPC를 삭제했습니다.')}catch(e){toast(e.message,3500)}}

function blankMonster(folderId=null){return {id:null,folder_id:folderId,name:'',data:{attack:'',damage:{die:'D6',count:1,modifier:0,mode:'normal'},range:'',tags:[],instinct:'',special:'',moves:[],description:''}}}



async function createMonsterFolder(){const name=promptUi('새 지역 / 몬스터 폴더 이름');if(!name?.trim())return;try{await api(`/api/rooms/${APP.creds.room}/monster-folders`,{method:'POST',body:JSON.stringify({name:name.trim()})});await refreshState(true);toast('몬스터 폴더를 만들었습니다.')}catch(e){toast(e.message,3500)}}
async function renameMonsterFolder(id){const f=(APP.state.monster_folders||[]).find(x=>x.id===id);if(!f)return;const name=promptUi('폴더 이름 변경',f.name);if(!name?.trim()||name.trim()===f.name)return;try{await api(`/api/rooms/${APP.creds.room}/monster-folders/${id}`,{method:'PUT',body:JSON.stringify({name:name.trim()})});await refreshState(true)}catch(e){toast(e.message,3500)}}
async function deleteMonsterFolder(id){const f=(APP.state.monster_folders||[]).find(x=>x.id===id);if(!f||!confirmUi(`'${contentValue(f.name,monsterFolderIsBuiltin(f))}' 폴더를 삭제할까요?\n안의 몬스터는 삭제되지 않고 '미분류'로 이동합니다.`))return;try{await api(`/api/rooms/${APP.creds.room}/monster-folders/${id}`,{method:'DELETE'});if(APP.gmMonsterFolderId===id)APP.gmMonsterFolderId=null;await refreshState(true)}catch(e){toast(e.message,3500)}}
async function saveMonster(){let name=$('#monsterName')?.value.trim();if(!name)return toast('몬스터 이름을 입력하세요.');const folderRaw=$('#monsterFolder')?.value,folder_id=folderRaw?Number(folderRaw):null,tags=$$('[data-monster-tag]:checked').map(x=>x.value),damage={die:$('#monsterDamageDie')?.value||'D6',count:Number($('#monsterDamageCount')?.value)||1,modifier:Number($('#monsterDamageMod')?.value)||0,mode:$('#monsterDamageMode')?.value||'normal'},original=(APP.state.monsters||[]).find(x=>Number(x.id)===Number(APP.gmMonsterId));let data={hp:Number($('#monsterHp')?.value)||0,armor:Number($('#monsterArmor')?.value)||0,attack:$('#monsterAttack')?.value||'',damage,range:$('#monsterRange')?.value||'',tags,instinct:$('#monsterInstinct')?.value||'',special:$('#monsterSpecial')?.value||'',moves:($('#monsterMoves')?.value||'').split('\n').map(x=>x.trim()).filter(Boolean),description:$('#monsterDescription')?.value||''};if(monsterIsBuiltin(original)){const restored=restoreDisplayedBuiltIn({name,data},{name:original.name,data:original.data});name=restored.name;data=restored.data;const coreKeys=['hp','armor','attack','damage','range','tags','instinct','special','moves','description'],same=coreKeys.every(k=>JSON.stringify(data?.[k])===JSON.stringify(original.data?.[k]));if(same){for(const k of ['builtin','builtin_key','source_url','source_note'])if(original.data?.[k]!==undefined)data[k]=original.data[k]}}try{const r=await api(`/api/rooms/${APP.creds.room}/monsters`,{method:'PUT',body:JSON.stringify({id:APP.gmMonsterId||null,folder_id,name,data})});APP.gmMonsterId=r.id;APP.gmMonsterFolderId=folder_id;await refreshState(true);toast('몬스터를 저장했습니다.')}catch(e){toast(e.message,3500)}}
const MONSTER_CATALOG_REVEAL_FIELDS=[['name','이름 공개'],['hp','HP 공개'],['armor','장갑 공개'],['attack','공격명 공개'],['damage','피해 공개'],['range','거리 공개'],['tags','태그 전체 공개'],['instinct','본능 공개'],['special','특기 공개'],['moves','몬스터 행동 공개'],['description','설명 공개']];
async function monsterAppear(){if(!APP.gmMonsterId)return;try{await api(`/api/rooms/${APP.creds.room}/monsters/${APP.gmMonsterId}/appear`,{method:'POST'});await refreshState(true);toast('플레이어 도감에 출현시켰습니다.')}catch(e){toast(e.message,3500)}}
async function saveCatalogReveal(){if(!APP.gmMonsterId)return;const reveal={};$$('[data-catalog-reveal]').forEach(i=>reveal[i.dataset.catalogReveal]=i.checked);try{await api(`/api/rooms/${APP.creds.room}/monsters/${APP.gmMonsterId}/catalog`,{method:'PUT',body:JSON.stringify({reveal})});await refreshState(true);toast('도감 공개 정보를 저장했습니다.')}catch(e){toast(e.message,3500)}}
async function revealAllCatalog(){if(!APP.gmMonsterId||!confirmUi('모든 도감 정보를 플레이어에게 공개할까요?'))return;const reveal=Object.fromEntries(MONSTER_CATALOG_REVEAL_FIELDS.map(([key])=>[key,true]));try{await api(`/api/rooms/${APP.creds.room}/monsters/${APP.gmMonsterId}/catalog`,{method:'PUT',body:JSON.stringify({reveal})});await refreshState(true);toast('모든 도감 정보를 공개했습니다.')}catch(e){toast(e.message,3500)}}
async function removeCatalog(){if(!APP.gmMonsterId||!confirmUi('이 몬스터를 플레이어 도감에서 제거할까요?'))return;try{await api(`/api/rooms/${APP.creds.room}/monsters/${APP.gmMonsterId}/catalog`,{method:'DELETE'});await refreshState(true)}catch(e){toast(e.message,3500)}}
async function prepareMonsterDamage(){if(APP.state?.me?.role!=='gm'||!APP.gmMonsterId)return;const mon=(APP.state.monsters||[]).find(x=>x.id===APP.gmMonsterId);if(!mon)return;const d={die:$('#monsterDamageDie')?.value||mon.data?.damage?.die||'D6',count:Number($('#monsterDamageCount')?.value)||Number(mon.data?.damage?.count)||1,modifier:Number($('#monsterDamageMod')?.value)||0,mode:$('#monsterDamageMode')?.value||'normal'},dice={},key=String(d.die).toLowerCase();dice[key]=Math.max(1,d.count);try{const r=await api(`/api/rooms/${APP.creds.room}/dice/prepare`,{method:'POST',body:JSON.stringify({dice,modifier:d.modifier,style:diceStyle(),context:`${mon.name} · 피해 ${monsterDamageText(d)}`,roll_mode:d.mode||'normal',minimum_total:0})});APP.dicePreps[r.preparation.key]=r.preparation;openDiceDrawer(r.preparation.key)}catch(e){toast(e.message,3500)}}

async function deleteMonster(){if(!APP.gmMonsterId||!confirmUi('이 몬스터를 삭제할까요?'))return;try{await api(`/api/rooms/${APP.creds.room}/monsters/${APP.gmMonsterId}`,{method:'DELETE'});APP.gmMonsterId=null;await refreshState(true);toast('몬스터를 삭제했습니다.')}catch(e){toast(e.message,3500)}}

function copyText(text){if(navigator.clipboard?.writeText)return navigator.clipboard.writeText(text).then(()=>toast('클립보드에 복사했습니다.')).catch(()=>fallbackCopy(text));return fallbackCopy(text)}
function fallbackCopy(text){const t=document.createElement('textarea');t.value=text;document.body.appendChild(t);t.select();try{document.execCommand('copy');toast('클립보드에 복사했습니다.')}catch{toast('복사하지 못했습니다.',3000)}t.remove()}
function attachSortableLists(){
  let dragged=null,changedList=null;
  const keyOf=el=>el.dataset.sortName?`name:${el.dataset.sortName}`:`id:${el.dataset.sortId}`;
  $$('[draggable="true"][data-sort-kind]').forEach(el=>{
    el.addEventListener('dragstart',e=>{dragged={kind:el.dataset.sortKind,id:Number(el.dataset.sortId)||null,name:el.dataset.sortName||'',folder:el.dataset.folderId??null,el};changedList=el.closest('.sortable-list');el.classList.add('dragging');e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('text/plain',keyOf(el))});
    el.addEventListener('dragend',async()=>{el.classList.remove('dragging');if(changedList&&dragged){const kind=dragged.kind;if(kind==='expansions'){const ids=$$('[data-sort-kind="expansions"][data-sort-id]',changedList).map(x=>Number(x.dataset.sortId)).filter(Boolean);if(ids.length)try{await api(`/api/rooms/${APP.creds.room}/expansion-order`,{method:'PUT',body:JSON.stringify({ids})})}catch(e){toast(e.message,3000)}}else if(['classes','races'].includes(kind)){const names=$$(`[data-sort-kind="${kind}"][data-sort-name]`,changedList).map(x=>x.dataset.sortName);if(names.length)try{await api(`/api/rooms/${APP.creds.room}/order/${kind}`,{method:'PUT',body:JSON.stringify({names,ids:[]})})}catch(e){toast(e.message,3000)}}else if(kind==='npcs'){await persistSimpleOrder('npcs','[data-sort-kind="npcs"][data-sort-id]')}else if(kind==='folders'){await persistSimpleOrder('folders','[data-sort-kind="folders"][data-sort-id]')}}dragged=null;changedList=null});
  });
  $$('.sortable-list').forEach(list=>list.addEventListener('dragover',e=>{const target=e.target.closest?.('[draggable="true"][data-sort-kind]');if(!dragged||!target||target.dataset.sortKind!==dragged.kind)return;e.preventDefault();const src=dragged.el;if(!src||src===target||src.parentNode!==target.parentNode)return;const r=target.getBoundingClientRect();target.parentNode.insertBefore(src,e.clientY<r.top+r.height/2?target:target.nextSibling);changedList=list}));
}
async function persistSimpleOrder(kind,selector,folder_id=null){const ids=$$(selector).map(x=>Number(x.dataset.sortId)).filter(Boolean);if(!ids.length)return;try{await api(`/api/rooms/${APP.creds.room}/order/${kind}`,{method:'PUT',body:JSON.stringify({ids,names:[],folder_id})})}catch(e){toast(e.message,3000)}}
function closeGMSettings(){$('#gmSettingsDrawer')?.remove()}

function ruleModRow(item={max:99,mod:0}){return `<div class="rule-mod-row"><label><span>이 점수 이하</span><input class="input" data-rule-mod-max type="number" value="${Number(item.max)}"></label><label><span>수정치</span><input class="input" data-rule-mod-value type="number" value="${Number(item.mod)}"></label><button class="btn small danger" data-rule-mod-del type="button">삭제</button></div>`}
function ruleTagRow(tag=''){const raw=String(tag??'');return `<div class="rule-tag-row"><input class="input" data-rule-monster-tag data-raw-tag="${attr(raw)}" data-tag-dirty="0" value="${attr(displayMonsterTag(raw))}" placeholder="몬스터 태그"><button class="btn small danger" data-rule-tag-del type="button">삭제</button></div>`}
function renderGMRules(){const r=APP.state.room.rules,exp=expansionsEnabled();const expansionRules=exp?`<hr class="rule"><h3>확장직업 규칙</h3><div class="notice">확장직업을 사용하는 캠페인에서만 적용되는 규칙입니다.</div><div class="rules-compact-grid"><label class="field"><span>캐릭터당 확장직업 최대</span><input id="ruleExp" class="input" type="number" min="0" max="99" value="${Number(r.max_expansions_per_character)||0}"><small>0 = 상한 없음</small></label></div>${APP.language==='en'?'<div class="small muted"><b>Legendary Move</b> is this app’s name for the signature move that opens an expansion class. It is unrelated to the “Legendary Action” rules used in other games.</div>':'<div class="small muted"><b>전설행동</b>은 확장직업을 여는 대표 행동을 뜻하는 이 프로그램의 명칭입니다. 다른 게임의 Legendary Action 규칙과는 관계가 없습니다.</div>'}`:'';return `<section class="panel gm-editor"><div class="head sticky-edit-head"><span>규칙</span><button id="saveRules" class="btn small" type="button">규칙 저장</button></div><div class="body"><div class="notice">최대 레벨과 XP 기준값은 실제 캐릭터 진행에 적용됩니다. 최대 레벨을 올리면 그 레벨까지 고급행동 포인트도 계속 누적됩니다.</div><div class="rules-compact-grid"><label class="field"><span>초기 능력치 배분</span><input id="ruleStart" class="input" value="${attr((r.stat_start||[]).join(', '))}"></label><label class="field"><span>능력치 최소</span><input id="ruleMin" class="input" type="number" value="${r.stat_min}"></label><label class="field"><span>능력치 최대</span><input id="ruleMax" class="input" type="number" value="${r.stat_max}"></label><label class="field"><span>최대 레벨</span><input id="ruleLevel" class="input" type="number" min="1" max="99" value="${r.level_max}"><small>레벨 2부터 레벨당 고급행동 포인트 1점 · 미사용 포인트는 이월</small></label><label class="field"><span>재화 명칭</span><input id="ruleCurrency" class="input" data-raw-currency="${attr(r.currency_name||'닢')}" data-currency-dirty="0" value="${attr(APP.language==='en'&&String(r.currency_name||'닢')==='닢'?'Coin':(r.currency_name||'닢'))}"></label><label class="field"><span>레벨업 XP 기준값</span><input id="ruleXpBase" class="input" type="number" min="0" max="100" value="${Number(r.xp_base??7)}"><small>다음 레벨 필요 XP = 현재 레벨 + 이 값 · XP가 차도 레벨은 자동으로 오르지 않습니다</small></label><label class="field"><span>최대 예비</span><input id="ruleReserveMax" class="input" type="number" min="0" max="9999" value="${Math.max(0,Number(r.reserve_max)||0)}"><small>0 = 제한 없음</small></label></div>${expansionRules}<hr class="rule"><h3>선택 규칙 / 권한</h3><div class="rule-choice-grid"><label class="choice settings-choice"><input id="rulePlayersExtraMoves" type="checkbox" ${r.players_can_add_extra_moves!==false?'checked':''}><span><b>플레이어가 다중직업 행동 직접 선택</b><small>끄면 GM이 캐릭터를 관리할 때만 다중직업 행동을 추가할 수 있습니다.</small></span></label><label class="choice settings-choice"><input id="ruleCoinWeight" type="checkbox" ${r.coin_weight_enabled===true?'checked':''}><span><b>동전도 하중에 포함</b><small>Dungeon World 원작 기준: 기본 100닢 = 1무게. 숫자는 아래에서 바꿀 수 있습니다.</small></span></label><label class="field compact-field"><span>1무게가 되는 재화 수</span><input id="ruleCoinWeightPer" class="input" type="number" min="1" max="100000" value="${Math.max(1,Number(r.coin_weight_per)||100)}"></label></div><hr class="rule"><h3>능력치 수정치 규칙</h3><div id="ruleModRanges" class="rule-mod-list compact-rule-grid">${(r.stat_mod_ranges||[]).map(ruleModRow).join('')}</div><button id="addRuleMod" class="btn small" type="button">＋ 수정치 구간</button><hr class="rule"><h3>몬스터 기본 태그</h3><div class="notice">새 캠페인의 기본 태그를 출발점으로 제공합니다. 이 캠페인에서는 자유롭게 추가·수정·삭제할 수 있습니다.</div><div id="ruleMonsterTags" class="rule-tag-list compact-tag-grid">${(r.monster_tags||[]).map(ruleTagRow).join('')}</div><button id="addRuleTag" class="btn small" type="button">＋ 태그 추가</button><hr class="rule"><div class="default-data-box"><h3>기본 데이터 관리</h3>${APP.language==='en'?'<div class="notice warn">Core data is copied once when a new campaign is created. Deleted entries are not restored automatically. The buttons below restore <b>only core entries that are currently missing</b> and never overwrite GM data with the same name.</div>':'<div class="notice warn">기본 데이터는 새 캠페인을 만들 때 한 번 복사됩니다. 삭제한 항목은 자동으로 되살아나지 않습니다. 아래 버튼은 <b>현재 없는 기본 항목만</b> 다시 가져오며 같은 이름의 GM 데이터는 덮어쓰지 않습니다.</div>'}<div class="default-data-actions"><button class="btn small" data-default-import="core" type="button">핵심 행동 가져오기</button><button class="btn small" data-default-import="classes" type="button">직업 가져오기</button><button class="btn small" data-default-import="races" type="button">종족 가져오기</button><button class="btn small" data-default-import="spells" type="button">주문 가져오기</button><button class="btn small" data-default-import="monsters" type="button">몬스터 가져오기</button><button class="btn dark" data-default-import="all" type="button">전체 누락 기본 데이터 가져오기</button></div></div></div></section>`}

function attachGMRules(){const r=APP.state.room.rules;$('#ruleCurrency')?.addEventListener('input',e=>{e.currentTarget.dataset.currencyDirty='1'});const bindTagDirty=()=>$$('[data-rule-monster-tag]').forEach(i=>{if(i.dataset.dirtyBound)return;i.dataset.dirtyBound='1';i.addEventListener('input',()=>{i.dataset.tagDirty='1'})});$('#addRuleMod')?.addEventListener('click',()=>{$('#ruleModRanges').insertAdjacentHTML('beforeend',ruleModRow({max:99,mod:0}));attachRuleRowDeletes()});$('#addRuleTag')?.addEventListener('click',()=>{$('#ruleMonsterTags').insertAdjacentHTML('beforeend',ruleTagRow(''));attachRuleRowDeletes();bindTagDirty()});attachRuleRowDeletes();bindTagDirty();$$('[data-default-import]').forEach(b=>b.addEventListener('click',async()=>{const k=b.dataset.defaultImport,kinds=k==='all'?['core','classes','races','spells','monsters']:[k];if(!confirmUi(`${k==='all'?translateUiText('전체 누락 기본 데이터'):b.textContent.trim()}를 가져올까요?\n현재 GM 데이터는 덮어쓰지 않습니다.`))return;try{const x=await api(`/api/rooms/${APP.creds.room}/default-data/import`,{method:'POST',body:JSON.stringify({kinds})});await refreshState(true);const total=Object.values(x.added||{}).reduce((a,v)=>a+Number(v||0),0);toast(total?`기본 데이터 ${total}개를 추가했습니다.`:'추가할 누락 기본 데이터가 없습니다.')}catch(e){toast(e.message,3500)}}));$('#saveRules')?.addEventListener('click',async()=>{const start=$('#ruleStart').value.split(',').map(x=>Number(x.trim())).filter(Number.isFinite);if(start.length!==6)return toast('초기 능력치 6개를 입력하세요.');const stat_mod_ranges=$$('.rule-mod-row').map(r=>({max:Number($('[data-rule-mod-max]',r)?.value),mod:Number($('[data-rule-mod-value]',r)?.value)})).filter(x=>Number.isFinite(x.max)&&Number.isFinite(x.mod)).sort((a,b)=>a.max-b.max),monster_tags=$$('[data-rule-monster-tag]').map(i=>i.dataset.tagDirty==='1'?i.value.trim():(i.dataset.rawTag||i.value.trim())).filter(Boolean);const rules={stat_start:start,stat_min:Number($('#ruleMin').value),stat_max:Number($('#ruleMax').value),level_max:Math.max(1,Math.min(99,Number($('#ruleLevel').value)||10)),max_expansions_per_character:expansionsEnabled()?Math.max(0,Math.min(99,Number($('#ruleExp')?.value??r.max_expansions_per_character)||0)):Number(r.max_expansions_per_character),players_can_add_extra_moves:!!$('#rulePlayersExtraMoves')?.checked,currency_name:(()=>{const el=$('#ruleCurrency'),raw=el?.dataset.rawCurrency||r.currency_name||'닢';return el?.dataset.currencyDirty==='1'?(el.value.trim()||'닢'):raw})(),xp_base:Number($('#ruleXpBase')?.value??7),reserve_max:Math.max(0,Number($('#ruleReserveMax')?.value)||0),coin_weight_enabled:!!$('#ruleCoinWeight')?.checked,coin_weight_per:Math.max(1,Number($('#ruleCoinWeightPer')?.value)||100),stat_mod_ranges,monster_tags};try{await api(`/api/rooms/${APP.creds.room}/rules`,{method:'PUT',body:JSON.stringify({rules})});await refreshState(true);toast('규칙을 저장했습니다.')}catch(e){toast(e.message,3500)}})}
function attachRuleRowDeletes(){$$('[data-rule-mod-del]').forEach(b=>{if(b.dataset.on)return;b.dataset.on='1';b.addEventListener('click',()=>b.closest('.rule-mod-row')?.remove())});$$('[data-rule-tag-del]').forEach(b=>{if(b.dataset.on)return;b.dataset.on='1';b.addEventListener('click',()=>b.closest('.rule-tag-row')?.remove())})}

const LOG_ACTION_EN={
  'NPC 삭제':'NPC Deleted','NPC 수정':'NPC Updated','NPC 생성':'NPC Created','규칙 수정':'Rules Updated','기본 데이터 가져오기':'Core Data Imported',
  '몬스터 삭제':'Monster Deleted','몬스터 수정':'Monster Updated','몬스터 생성':'Monster Created','몬스터 출현':'Monster Encountered','몬스터 폴더 삭제':'Monster Folder Deleted','몬스터 폴더 생성':'Monster Folder Created','몬스터 폴더 수정':'Monster Folder Updated',
  '사운드 삭제':'Sound Deleted','사운드 추가':'Sound Added','설정 수정':'Settings Updated','세션 시작':'Session Started','세션 종료':'Session Ended','운명 선택':'Destiny Chosen','재접속 코드 발급':'Reconnect Code Issued',
  '종족 삭제':'Race Deleted','종족 저장':'Race Updated','주문 삭제':'Spell Deleted','주문 저장':'Spell Updated','주사위 굴림':'Dice Roll','직업 삭제':'Class Deleted','직업 이름 변경':'Class Renamed','직업 저장':'Class Updated','직업 추가':'Class Added',
  '참가자 삭제':'Player Deleted','캐릭터 수정':'Character Updated','캐릭터 재배치':'Character Reassigned','캠페인 생성':'Campaign Created','캠페인 이름 변경':'Campaign Renamed','캠페인 입장':'Campaign Joined',
  '특수 주문 지급':'Special Spell Granted','특수 주문 회수':'Special Spell Revoked','팩 가져오기':'Pack Imported','플레이 기록':'Play Log','핵심 행동 삭제':'Basic Move Deleted','핵심 행동 저장':'Basic Move Updated',
  '확장직업 삭제':'Expansion Class Deleted','확장직업 수정':'Expansion Class Updated','확장직업 제안':'Expansion Class Offered','확장직업 추가':'Expansion Class Added','확장직업 수락':'Expansion Class Accepted','확장직업 거절':'Expansion Class Declined','확장직업 회수':'Expansion Class Revoked'
};
function logActionName(action=''){const raw=String(action||'');return APP.language==='en'?(LOG_ACTION_EN[raw]||translateUiText(raw)):raw}

const LOG_FIELD_LABELS={
  stat_start:'초기 능력치 배분',stat_min:'능력치 최소',stat_max:'능력치 최대',level_max:'최대 레벨',max_expansions_per_character:'캐릭터당 확장직업 최대',players_can_add_extra_moves:'플레이어의 다중직업 행동 직접 선택',currency_name:'재화 명칭',xp_base:'레벨업 XP 기준값',reserve_max:'최대 예비',coin_weight_enabled:'동전 하중 적용',coin_weight_per:'1무게가 되는 재화 수',stat_mod_ranges:'능력치 수정치 규칙',monster_tags:'몬스터 기본 태그',
  gm_dice_public:'GM 주사위 공개',gm_color:'GM 대표색',player_colors:'플레이어 대표색',expansions_enabled:'확장직업 사용',
  hp_current:'HP',xp:'XP',armor:'장갑',armor_base:'기본 장갑',level:'레벨',currency:'재화',reserve:'예비',damage_die:'피해 주사위',damage_bonus:'추가 피해',bonds:'인연',advanced_moves:'고급 행동',extra_moves:'추가 행동',move_choices:'행동 선택 결과',spellbook:'주문서',prepared_spells:'준비 주문',extra_spells:'추가 주문',class_name:'직업',race_name:'종족',alignment_name:'가치관',profile:'인물 정보',inventory:'인벤토리',memo:'메모',stats:'능력치',
  name:'이름',desc:'설명',description:'설명',hp:'기본 HP',damage:'피해',load:'기본 하중',gear:'시작 장비 안내',alignments:'가치관',start:'시작 행동',a25:'고급 행동 2–5',a610:'고급 행동 6–10',multiclass_25:'다중직업 2–5',multiclass_610:'다중직업 6–10',races:'종족',move_effects:'행동 효과',has_requirement:'선행 행동 조건',requires_move:'필요 행동',
  appearance:'외형',favorite:'즐겨찾기',attack:'공격',range:'거리',tags:'태그',instinct:'본능',special:'특기 사항',moves:'행동',source_url:'출처 주소',kind:'종류',source_type:'출처 방식',count:'개수',modifier:'수정치',mode:'굴림 방식',enabled_classes:'사용 가능한 직업',spell_effects:'주문 관련 특성',per_class:'직업별 설명'
};
function readableFieldName(k){const v=LOG_FIELD_LABELS[k]||(k==='currency'?(APP.state?.room?.rules?.currency_name||'재화'):k);return translateUiText(v)}
function localizedLogScalar(v){if(typeof v==='boolean')return translateUiText(v?'사용':'사용 안 함');if(typeof v==='string'){const b=_builtinContentCapture(v);return b!==null?b:translateUiText(v)}return String(v)}
function readableValue(v,k=''){
  if(v===null||v===undefined)return '—';
  if(typeof v==='string'||typeof v==='number'||typeof v==='boolean')return localizedLogScalar(v);
  if(Array.isArray(v)){
    if(!v.length)return translateUiText('없음');
    if(k==='stat_mod_ranges')return v.map(x=>`≤ ${Number(x?.max)||0}: ${(Number(x?.mod)||0)>=0?'+':''}${Number(x?.mod)||0}`).join(' · ');
    if(v.every(x=>x===null||['string','number','boolean'].includes(typeof x)))return v.map(localizedLogScalar).join(', ');
    const names=v.map(x=>x&&typeof x==='object'?(x.name||x.label||''): '').filter(Boolean);if(names.length===v.length)return names.map(localizedLogScalar).join(', ');
    return APP.language==='en'?`${v.length} items`:`${v.length}개 항목`;
  }
  if(typeof v==='object'){
    if(k==='player_colors')return APP.language==='en'?`${Object.keys(v).length} player colors`:`플레이어 대표색 ${Object.keys(v).length}개`;
    if(k==='damage'&&v.die)return `${Number(v.count)||1}${String(v.die).toUpperCase()}${Number(v.modifier)?` ${(Number(v.modifier)>0?'+':'')}${Number(v.modifier)}`:''}${v.mode&&v.mode!=='normal'?` · ${translateUiText(v.mode==='high'?'고(높은 값)':'저(낮은 값)')}`:''}`;
    return APP.language==='en'?`${Object.keys(v).length} fields`:`${Object.keys(v).length}개 항목`;
  }
  return String(v);
}
function changedObjectLines(before={},after={},keys=null){
  const ordered=(Array.isArray(keys)&&keys.length)?keys:[...new Set([...Object.keys(before||{}),...Object.keys(after||{})])],out=[];
  for(const k of ordered){const a=before?.[k],b=after?.[k];if(JSON.stringify(a)===JSON.stringify(b))continue;const label=esc(readableFieldName(k));
    if(k==='stats'){const aa=a||{},bb=b||{};for(const sk of Object.keys(STAT_META)){if(Number(aa[sk]||0)!==Number(bb[sk]||0))out.push(`${esc(STAT_META[sk][0])} <span class="log-before">${esc(aa[sk]??0)}</span> → <b>${esc(bb[sk]??0)}</b>`)}continue}
    if(Array.isArray(a)||Array.isArray(b)){
      const ba=Array.isArray(a)?a:[],bb=Array.isArray(b)?b:[];
      if(ba.every(x=>x===null||['string','number','boolean'].includes(typeof x))&&bb.every(x=>x===null||['string','number','boolean'].includes(typeof x))){
        if(k==='stat_start'||k==='stat_mod_ranges'){out.push(`${label} <span class="log-before">${esc(readableValue(a,k))}</span> → <b>${esc(readableValue(b,k))}</b>`);continue}
        const oldVals=ba.map(localizedLogScalar),newVals=bb.map(localizedLogScalar),oldSet=new Set(oldVals),newSet=new Set(newVals),added=newVals.filter(x=>!oldSet.has(x)),removed=oldVals.filter(x=>!newSet.has(x));
        for(const x of added)out.push(`${label} · <b>${esc(x)} ${APP.language==='en'?'added':'추가'}</b>`);for(const x of removed)out.push(`${label} · <b>${esc(x)} ${APP.language==='en'?'removed':'제거'}</b>`);if(!added.length&&!removed.length)out.push(`${label} · <b>${translateUiText('변경됨')}</b>`);continue
      }
      const oldNames=ba.map(x=>x&&typeof x==='object'?(x.name||x.label||''):'').filter(Boolean).map(localizedLogScalar),newNames=bb.map(x=>x&&typeof x==='object'?(x.name||x.label||''):'').filter(Boolean).map(localizedLogScalar);
      if(oldNames.length===ba.length&&newNames.length===bb.length){const os=new Set(oldNames),ns=new Set(newNames),added=newNames.filter(x=>!os.has(x)),removed=oldNames.filter(x=>!ns.has(x));for(const x of added)out.push(`${label} · <b>${esc(x)} ${APP.language==='en'?'added':'추가'}</b>`);for(const x of removed)out.push(`${label} · <b>${esc(x)} ${APP.language==='en'?'removed':'제거'}</b>`);if(added.length||removed.length)continue}
      out.push(`${label} · <b>${translateUiText('변경됨')}</b>`);continue
    }
    if((a&&typeof a==='object')||(b&&typeof b==='object')){out.push(`${label} · <b>${translateUiText('변경됨')}</b>`);continue}
    out.push(`${label} <span class="log-before">${esc(readableValue(a,k))}</span> → <b>${esc(readableValue(b,k))}</b>`)
  }
  return out;
}

function readableLogDetail(l){
  const d=l.detail||{},action=logActionName(l.action||'');
  if(l.action==='주사위 굴림'){const rs=(d.results||[]).map(x=>x.value).join(', '),mod=Number(d.modifier)||0,base=diceBaseTotal(d);return APP.language==='en'?`Dice Roll · ${rs} · Dice Total ${base} + Modifier (${mod>=0?'+':''}${mod}) = <b>${Number(d.total)||0}</b>`:`주사위 굴림 · ${rs} · 주사위 결과 ${base} + 수정치 (${mod>=0?'+':''}${mod}) = <b>${Number(d.total)||0}</b>`}
  if(l.action==='캐릭터 수정'&&Array.isArray(d.changed_keys)){const out=changedObjectLines(d.before||{},d.after||{},d.changed_keys);return out.join(' / ')||translateUiText('캐릭터 정보를 수정했습니다.')}
  const before=d.before??d.old??d.previous,after=d.after??d.new??d.current;
  if(before!==undefined||after!==undefined){
    if(before&&typeof before==='object'&&!Array.isArray(before)&&after&&typeof after==='object'&&!Array.isArray(after)){const lines=changedObjectLines(before,after,d.changed_keys);if(lines.length)return `${esc(action)} · ${lines.join(' / ')}`}
    if(after===undefined&&(before&&typeof before==='object'))return esc(action);
    return `${esc(action)} · <span class="log-before">${esc(readableValue(before))}</span> → <b>${esc(readableValue(after))}</b>`;
  }
  if(Array.isArray(d.changed_keys)&&d.changed_keys.length)return `${esc(action)} · ${d.changed_keys.map(k=>esc(readableFieldName(k))).join(', ')}`;
  return esc(action);
}
function logTargetName(target){const raw=String(target||'');if(raw==='room_rules')return translateUiText('캠페인 규칙');if(raw==='room_settings')return translateUiText('시스템 설정');const m=raw.match(/^character:(\d+)$/);if(m){const p=(APP.state.party||[]).find(x=>Number(x.character_id)===Number(m[1]));return p?.character_name||p?.display_name||raw}const sp=raw.match(/^__undefined__:(.+)$/);if(sp){const item=(APP.state.spells?.__undefined__||[]).find(x=>x.name===sp[1]);return `${translateUiText('미분류')} · ${item?contentValue(sp[1],spellIsBuiltin(item)):sp[1]}`}return translateUiText(raw)}
function renderGMLogs(){
  const active=APP.state.room.active_session,sessions=APP.state.sessions||[],sessionMap=Object.fromEntries(sessions.map(s=>[s.id,s.session_no])),playActions=new Set(['플레이 기록','캠페인 생성','캠페인 입장','세션 시작','세션 종료','확장직업 제안','확장직업 수락','확장직업 거절','주사위 굴림']),mode=APP.gmLogMode||'play',filter=APP.gmLogFilter||'all';
  let logs=(APP.state.logs||[]).filter(l=>!/(정렬|순서 변경)/.test(l.action||'')).filter(l=>mode==='play'?playActions.has(l.action):!playActions.has(l.action));if(filter!=='all')logs=logs.filter(l=>l.actor_role===filter);
  const logHtml=logs.map(l=>{let text=l.action==='플레이 기록'?esc(l.detail?.text||''):readableLogDetail(l);const keys='',sn=l.session_id?`SESSION #${sessionMap[l.session_id]||'?'}`:translateUiText('세션 외');return `<div class="log"><div><b>${esc(l.actor_name)}</b> · ${text}${keys}</div><div class="time">${esc(sn)} · ${fmtTime(l.created_at)} ${l.target?`· ${esc(logTargetName(l.target))}`:''}</div></div>`}).join('')||'<div class="notice">해당 기록이 없습니다.</div>';
  return `<section class="panel"><div class="head"><span>플레이 기록</span><div class="inline-actions">${active?`<span class="pill">SESSION #${active.session_no} 진행 중</span><button id="endSession" class="btn small" type="button">세션 종료</button>`:'<button id="startSession" class="btn small" type="button">새 세션 시작</button>'}</div></div><div class="body"><div class="log-toolbar"><div class="segmented"><button data-log-mode="play" class="${mode==='play'?'active':''}" type="button">플레이 기록</button><button data-log-mode="change" class="${mode==='change'?'active':''}" type="button">변경 기록</button></div><select id="logFilter" class="select"><option value="all" ${filter==='all'?'selected':''}>전체 활동</option><option value="gm" ${filter==='gm'?'selected':''}>GM만</option><option value="player" ${filter==='player'?'selected':''}>플레이어만</option></select></div>${mode==='play'?`<form id="manualLog" class="inline-actions"><input id="logText" class="input" style="flex:1" placeholder="예: 폐허의 문을 열고 2층으로 진입"><button class="btn dark" type="submit">기록 추가</button></form>`:''}<div class="session-history">${sessions.slice(0,8).map(s=>`<span class="pill">#${s.session_no} ${s.ended_at?'종료':'진행 중'}</span>`).join('')||'<span class="small muted">아직 세션 기록이 없습니다.</span>'}</div><div style="margin-top:12px">${logHtml}</div></div></section>`;
}
function attachGMLogs(){
  $$('[data-log-mode]').forEach(b=>b.addEventListener('click',()=>{APP.gmLogMode=b.dataset.logMode;renderGM()}));$('#logFilter')?.addEventListener('change',e=>{APP.gmLogFilter=e.target.value;renderGM()});
  $('#startSession')?.addEventListener('click',async()=>{try{await api(`/api/rooms/${APP.creds.room}/sessions/start`,{method:'POST'});await refreshState(true);toast('세션을 시작했습니다.')}catch(e){toast(e.message,3500)}});
  $('#endSession')?.addEventListener('click',async()=>{const x=APP.state.room.active_session;if(!x||!confirmUi(`SESSION #${x.session_no}을 종료할까요?`))return;try{await api(`/api/rooms/${APP.creds.room}/sessions/${x.id}/end`,{method:'POST'});await refreshState(true);toast('세션을 종료했습니다.')}catch(e){toast(e.message,3500)}});
  $('#manualLog')?.addEventListener('submit',async e=>{e.preventDefault();const text=$('#logText').value.trim();if(!text)return;try{await api(`/api/rooms/${APP.creds.room}/logs`,{method:'POST',body:JSON.stringify({text})});await refreshState(true);toast('플레이 기록 추가')}catch(err){toast(err.message,3500)}});
}



function ensureLiveLayers(){if(!$('#diceNotifyStack'))document.body.insertAdjacentHTML('beforeend','<div id="diceNotifyStack" class="dice-notify-stack"></div>');if(!$('#rollStageStack'))document.body.insertAdjacentHTML('beforeend','<div id="rollStageStack" class="roll-stage-stack"></div>');ensureAudioEngine()}
function ownDiceKey(){return APP.state?.me?.role==='gm'?'gm':`player:${APP.state?.me?.member_id}`}
function diceStyleStorageKey(){
  const room=String(APP.creds?.room||'').trim().toUpperCase()||'NO_ROOM';
  const me=APP.state?.me;
  const actor=me?.role==='gm'?'gm':(me?.member_id!=null?`player:${me.member_id}`:(APP.creds?.role||'unknown'));
  return `${DICE_STYLE_KEY}:${room}:${actor}`;
}
function diceStyle(){
  const defaults={fill:'#ffffff',border:'#111111',text:'#111111'},key=diceStyleStorageKey();
  try{
    let raw=localStorage.getItem(key);
    if(!raw&&APP.state?.me){
      const legacy=localStorage.getItem(DICE_STYLE_KEY);
      if(legacy){raw=legacy;localStorage.setItem(key,legacy);localStorage.removeItem(DICE_STYLE_KEY)}
    }
    return {...defaults,...JSON.parse(raw||'{}')};
  }catch{return defaults}
}
function setDiceStyle(x){localStorage.setItem(diceStyleStorageKey(),JSON.stringify(x))}
function diceLabel(dice={}){return ['d2','d4','d6','d8','d10','d12'].filter(k=>Number(dice[k])>0).map(k=>`${Number(dice[k])}${k.toUpperCase()}`).join(' + ')||'주사위 없음'}
function syncLiveState(){ensureLiveLayers();APP.dicePreps={};for(const p of (APP.state?.dice_preparations||[]))APP.dicePreps[p.key]=p;renderDiceNotifications();if(APP.state?.sound_state)applyBgmState(APP.state.sound_state);if($('#soundDrawer'))renderSoundDrawer()}
function handleDiceEvent(m){ensureLiveLayers();if(m.type==='dice_prepare'){APP.dicePreps[m.preparation.key]=m.preparation;renderDiceNotifications();if(APP.diceOpenKey===m.preparation.key)renderDiceDrawer(m.preparation.key)}else if(m.type==='dice_cancel'){delete APP.dicePreps[m.key];renderDiceNotifications();if(APP.diceOpenKey===m.key)closeDiceDrawer()}else if(m.type==='dice_roll'){delete APP.dicePreps[m.roll.key];renderDiceNotifications();showDiceRollAnimation(m.roll);if(APP.diceOpenKey===m.roll.key)closeDiceDrawer()}}
function renderDiceNotifications(){const root=$('#diceNotifyStack');if(!root)return;root.innerHTML=Object.values(APP.dicePreps).map(p=>`<button class="dice-notify" style="--actor-color:${attr(p.color||'#181818')}" data-watch-dice="${attr(p.key)}" type="button"><b>🎲 <span class="actor-name">${esc(p.label||p.name)}</span></b><span>${p.context?esc(p.context)+' · ':''}주사위를 준비합니다 · ${esc(diceLabel(p.dice))}${Number(p.modifier)?` · 수정치 ${Number(p.modifier)>0?'+':''}${Number(p.modifier)}`:''}</span></button>`).join('');$$('[data-watch-dice]',root).forEach(b=>b.addEventListener('click',()=>openDiceDrawer(b.dataset.watchDice)))}
async function openOwnDice(){const key=ownDiceKey();if(!APP.dicePreps[key]){try{const r=await api(`/api/rooms/${APP.creds.room}/dice/prepare`,{method:'POST',body:JSON.stringify({dice:{d6:2},modifier:0,style:diceStyle()})});APP.dicePreps[key]=r.preparation}catch(e){return toast(e.message,3500)}}openDiceDrawer(key)}
function openDiceDrawer(key){APP.diceOpenKey=key;renderDiceDrawer(key)}
function closeDiceDrawer(){APP.diceOpenKey=null;$('#diceDrawer')?.remove()}
function diceCountsHtml(prep,editable){return ['d2','d4','d6','d8','d10','d12'].map(k=>`<div class="dice-choice"><b>${k.toUpperCase()}${k==='d2'?'<small>동전</small>':''}</b><div><button ${editable?'':'disabled'} data-dice-minus="${k}" type="button">−</button><input data-dice-count="${k}" type="number" min="0" max="20" value="${Number(prep.dice?.[k])||0}" ${editable?'':'disabled'}><button ${editable?'':'disabled'} data-dice-plus="${k}" type="button">＋</button></div></div>`).join('')}
function renderDiceDrawer(key){let root=$('#diceDrawer');if(!root){document.body.insertAdjacentHTML('beforeend','<aside id="diceDrawer" class="dice-drawer"></aside>');root=$('#diceDrawer')}const p=APP.dicePreps[key];if(!p){root.remove();APP.diceOpenKey=null;return}const own=key===ownDiceKey(),actorLabel=APP.language==='en'?`${esc(p.label||p.name)}’s Dice`:`${esc(p.label||p.name)}의 주사위`,rollModeLabel=p.roll_mode==='high'?(APP.language==='en'?'Use higher roll · ':'높은 값 사용 · '):p.roll_mode==='low'?(APP.language==='en'?'Use lower roll · ':'낮은 값 사용 · '):'',watchLabel=own?(APP.language==='en'?'Ready':'준비 중'):(APP.language==='en'?'Watching':'관전 중');root.innerHTML=`<div class="dice-drawer-head" style="--actor-color:${attr(p.color||'#181818')}"><div><b>${actorLabel}</b><span>${esc(p.context||'')}${p.context?' · ':''}${rollModeLabel}${watchLabel}</span></div><div class="dice-head-actions">${own?'<button id="diceCustomize" class="dice-custom-head" type="button">커스텀</button>':''}<button data-close-dice type="button">×</button></div></div><div class="dice-drawer-body">${diceCountsHtml(p,own)}<label class="dice-mod"><span>수정치</span><input id="diceModifier" type="number" min="-99" max="99" value="${Number(p.modifier)||0}" ${own?'':'disabled'}></label><div class="dice-summary">${esc(diceLabel(p.dice))}${Number(p.modifier)?` ${Number(p.modifier)>0?'+':'-'} ${Math.abs(Number(p.modifier))}`:''}</div>${own?'<div class="dice-quick"><button data-dice-preset="2d6" type="button">기본 판정 2D6</button><button data-dice-preset="damage" type="button">현재 피해</button><button data-dice-preset="coin" type="button">D2 동전</button></div><div class="dice-actions"><button id="cancelDice" type="button">준비 취소</button><button id="rollDice" class="primary" type="button">굴리기</button></div>':'<div class="notice">굴리기를 기다리는 중…</div>'}</div>`;attachDiceDrawer(own)}

function openDiceCustomizer(){const st=diceStyle();$('#diceCustomizeModal')?.remove();document.body.insertAdjacentHTML('beforeend',`<div id="diceCustomizeModal" class="modal dice-custom-modal"><div class="modal-card"><div class="modal-head"><b>내 주사위 커스텀</b><button id="closeDiceCustom" class="modal-x" type="button" aria-label="닫기">×</button></div><div class="modal-body"><div class="grid three"><label class="color-setting"><span>안쪽</span><input id="diceFill" type="color" value="${attr(st.fill)}"></label><label class="color-setting"><span>테두리</span><input id="diceBorder" type="color" value="${attr(st.border)}"></label><label class="color-setting"><span>숫자</span><input id="diceText" type="color" value="${attr(st.text)}"></label></div><div id="diceStylePreview" class="dice-style-preview" style="--die-fill:${attr(st.fill)};--die-border:${attr(st.border)};--die-text:${attr(st.text)}"><span class="rolling-die d2 revealed"><b class="die-face">앞</b></span><span class="rolling-die d4 revealed"><b class="die-face">4</b></span><span class="rolling-die d6 revealed"><b class="die-face">6</b></span><span class="rolling-die d8 revealed"><b class="die-face">8</b></span><span class="rolling-die d10 revealed"><b class="die-face">10</b></span><span class="rolling-die d12 revealed"><b class="die-face">12</b></span></div><button id="saveDiceCustom" class="btn dark" type="button">적용</button></div></div></div>`);const preview=()=>{const el=$('#diceStylePreview');if(!el)return;el.style.setProperty('--die-fill',$('#diceFill').value);el.style.setProperty('--die-border',$('#diceBorder').value);el.style.setProperty('--die-text',$('#diceText').value)};['#diceFill','#diceBorder','#diceText'].forEach(x=>$(x)?.addEventListener('input',preview));$('#closeDiceCustom')?.addEventListener('click',()=>$('#diceCustomizeModal')?.remove());$('#saveDiceCustom')?.addEventListener('click',async()=>{setDiceStyle({fill:$('#diceFill').value,border:$('#diceBorder').value,text:$('#diceText').value});const modal=$('#diceCustomizeModal');modal?.remove();try{const body=collectDiceDrawer(),r=await api(`/api/rooms/${APP.creds.room}/dice/prepare`,{method:'POST',body:JSON.stringify(body)});APP.dicePreps[r.preparation.key]=r.preparation;renderDiceNotifications();renderDiceDrawer(r.preparation.key)}catch{}toast('내 주사위 색을 저장했습니다.')})}

function collectDiceDrawer(){const dice={};$$('[data-dice-count]',$('#diceDrawer')).forEach(i=>{const n=Math.max(0,Number(i.value)||0);if(n)dice[i.dataset.diceCount]=n});const p=APP.dicePreps[ownDiceKey()]||{};return {dice,modifier:Number($('#diceModifier')?.value)||0,style:diceStyle(),context:p.context||'',roll_mode:p.roll_mode||'normal',minimum_total:p.minimum_total??null}}
let diceUpdateTimer=null;
function scheduleDiceUpdate(){clearTimeout(diceUpdateTimer);diceUpdateTimer=setTimeout(async()=>{if(!APP.creds||!$('#diceDrawer')||!APP.dicePreps[ownDiceKey()])return;try{const body=collectDiceDrawer();const r=await api(`/api/rooms/${APP.creds.room}/dice/prepare`,{method:'POST',body:JSON.stringify(body)},5000);APP.dicePreps[r.preparation.key]=r.preparation;renderDiceNotifications();}catch(e){toast(e.message,2500)}},180);}
function attachDiceDrawer(own){$('#diceDrawer [data-close-dice]')?.addEventListener('click',async()=>{if(!own){closeDiceDrawer();return}try{await api(`/api/rooms/${APP.creds.room}/dice/cancel`,{method:'POST'});delete APP.dicePreps[ownDiceKey()];renderDiceNotifications();closeDiceDrawer()}catch(e){toast(e.message,3000)}});if(!own)return;$('#diceCustomize')?.addEventListener('click',openDiceCustomizer);$$('[data-dice-minus],[data-dice-plus]',$('#diceDrawer')).forEach(b=>b.addEventListener('click',()=>{const k=b.dataset.diceMinus||b.dataset.dicePlus,i=$(`[data-dice-count="${k}"]`,$('#diceDrawer')),d=b.dataset.dicePlus?1:-1;i.value=Math.max(0,(Number(i.value)||0)+d);scheduleDiceUpdate()}));$$('[data-dice-count]',$('#diceDrawer')).forEach(i=>i.addEventListener('change',scheduleDiceUpdate));$('#diceModifier')?.addEventListener('change',scheduleDiceUpdate);$$('[data-dice-preset]',$('#diceDrawer')).forEach(b=>b.addEventListener('click',()=>{const preset=b.dataset.dicePreset,vals={d2:0,d4:0,d6:0,d8:0,d10:0,d12:0},prep=APP.dicePreps[ownDiceKey()]||{};prep.roll_mode='normal';prep.minimum_total=null;prep.context='';$('#diceModifier').value=0;if(preset==='2d6')vals.d6=2;else if(preset==='coin')vals.d2=1;else{const st=APP.state.me.role==='gm'?(APP.gmSelectedChar?gmCharacterBundle(APP.gmSelectedChar)?.state:null):APP.state.character?.state,die=String(st?.damage_die||'D6').toLowerCase();if(vals[die]!==undefined)vals[die]=1;$('#diceModifier').value=Number(st?.damage_bonus)||0;prep.minimum_total=0;prep.context='피해'}APP.dicePreps[ownDiceKey()]=prep;for(const [k,v] of Object.entries(vals)){const i=$(`[data-dice-count="${k}"]`,$('#diceDrawer'));if(i)i.value=v}scheduleDiceUpdate()}));$('#cancelDice')?.addEventListener('click',async()=>{try{await api(`/api/rooms/${APP.creds.room}/dice/cancel`,{method:'POST'});delete APP.dicePreps[ownDiceKey()];renderDiceNotifications();closeDiceDrawer()}catch(e){toast(e.message,3000)}});$('#rollDice')?.addEventListener('click',async e=>{e.currentTarget.disabled=true;try{const r=await api(`/api/rooms/${APP.creds.room}/dice/roll`,{method:'POST'});showDiceRollAnimation(r.roll);delete APP.dicePreps[r.roll.key];renderDiceNotifications();closeDiceDrawer()}catch(err){e.currentTarget.disabled=false;toast(err.message,3500)}})}
function faceText(r){return r.sides===2?(r.value===1?'앞':'뒤'):String(r.value)}
function diceBaseTotal(roll){if(Number.isFinite(Number(roll?.dice_total)))return Number(roll.dice_total);const vals=(roll?.results||[]).map(x=>Number(x.value)||0);if(!vals.length)return 0;if(roll?.roll_mode==='high')return Math.max(...vals);if(roll?.roll_mode==='low')return Math.min(...vals);return vals.reduce((a,b)=>a+b,0)}
function showDiceRollAnimation(roll){const stamp=`${roll.key}:${roll.rolled_at}`;if(APP.lastRollStamp===stamp)return;APP.lastRollStamp=stamp;ensureLiveLayers();const root=$('#rollStageStack'),id='roll'+Date.now()+Math.random().toString(36).slice(2);root.insertAdjacentHTML('beforeend',`<div id="${id}" class="roll-stage" style="--die-fill:${attr(roll.style?.fill||'#fff')};--die-border:${attr(roll.style?.border||'#111')};--die-text:${attr(roll.style?.text||'#111')}"><div class="roll-title" style="--actor-color:${attr(roll.color||'#181818')}"><span class="actor-name">${esc(roll.label||roll.name)}</span> · ${esc(roll.context||diceLabel(roll.dice))}${roll.roll_mode==='high'?(APP.language==='en'?' · Higher':' · 높은 값'):roll.roll_mode==='low'?(APP.language==='en'?' · Lower':' · 낮은 값'):''}</div><div class="roll-dice">${roll.results.map(r=>`<span class="rolling-die d${r.sides}" data-face="${attr(faceText(r))}"><b class="die-face">?</b></span>`).join('')}</div><div class="roll-total">${APP.language==='en'?'Rolling…':'굴리는 중…'}</div></div>`);const el=$('#'+id);setTimeout(()=>{if(!el)return;$$('.rolling-die',el).forEach(d=>{d.classList.add('revealed');const face=$('.die-face',d);if(face)face.textContent=d.dataset.face});const base=diceBaseTotal(roll),mod=Number(roll.modifier)||0,floor=roll.minimum_total,clamped=floor!==null&&floor!==undefined&&(base+mod)<Number(floor),floorNote=clamped?(APP.language==='en'?` · minimum ${Number(floor)}`:` · 최소 ${Number(floor)} 적용`):'';$('.roll-total',el).innerHTML=APP.language==='en'?`Dice Total <b>${base}</b> + Modifier <b>(${mod>=0?'+':''}${mod})</b> = <strong>${Number(roll.total)||0}</strong>${floorNote}`:`주사위 결과 <b>${base}</b> + 수정치 <b>(${mod>=0?'+':''}${mod})</b> = <strong>${Number(roll.total)||0}</strong>${floorNote}`},1350);setTimeout(()=>el?.classList.add('leaving'),5200);setTimeout(()=>el?.remove(),5900)}

function soundPrefs(){try{return JSON.parse(localStorage.getItem(SOUND_PREFS_KEY)||'{"bgm":0.7,"sfx":0.8}') }catch{return {bgm:.7,sfx:.8}}}
function setSoundPrefs(p){localStorage.setItem(SOUND_PREFS_KEY,JSON.stringify(p))}
function ensureAudioEngine(){
  if(!$('#dwBgmAudio')){
    const a=document.createElement('audio');a.id='dwBgmAudio';a.preload='metadata';
    a.addEventListener('ended',()=>handleBgmEnded());
    a.addEventListener('timeupdate',()=>{updateNowPlaying(APP.state?.sound_state);updateSoundProgress()});
    ['loadedmetadata','durationchange','canplay'].forEach(ev=>a.addEventListener(ev,()=>updateSoundProgress()));
    a.addEventListener('error',()=>{const st=APP.state?.sound_state||{},snd=st.sound||soundById(st.sound_id);if(!snd||snd.source_type!=='file'||st.status==='stopped'||!a.getAttribute('src'))return;toast('BGM 파일을 재생하지 못했습니다. 파일이 손상되었거나 브라우저가 지원하지 않는 형식일 수 있습니다.',4200);if(APP.state?.me?.role==='gm'&&!APP.soundFileErrorGuard){APP.soundFileErrorGuard=true;soundControl('stop').finally(()=>setTimeout(()=>{APP.soundFileErrorGuard=false},800))}});
    document.body.appendChild(a)
  }
}

function handleBgmEnded(){
  if(APP.state?.me?.role!=='gm'||APP.soundEndGuard)return;APP.soundEndGuard=true;setTimeout(()=>{APP.soundEndGuard=false},900);
  const mode=APP.state?.sound_state?.mode||'next';
  if(mode==='repeat_one'){const id=APP.state?.sound_state?.sound_id;if(id)soundPlay(id,'bgm')}
  else if(mode==='stop_after')soundControl('stop');
  else if(mode==='next'){const list=(APP.state?.sounds||[]).filter(x=>x.kind==='bgm').slice().sort((a,b)=>(Number(a.sort_order)||0)-(Number(b.sort_order)||0)||(Number(a.id)||0)-(Number(b.id)||0)),id=Number(APP.state?.sound_state?.sound_id),idx=list.findIndex(x=>Number(x.id)===id);if(idx>=0&&idx<list.length-1)soundControl('next');else soundControl('stop')}
  else soundControl('next')
}

function soundById(id){return (APP.state?.sounds||[]).find(x=>Number(x.id)===Number(id))}
function currentBgmPosition(){const a=$('#dwBgmAudio');return Number(a?.currentTime)||0}
function seekBgmEngine(position){const pos=Math.max(0,Number(position)||0),a=$('#dwBgmAudio');if(a&&Number.isFinite(a.duration))try{a.currentTime=Math.min(pos,a.duration||pos)}catch{}return pos}
function stopSoundEngines(){const a=$('#dwBgmAudio');if(a){a.pause();a.removeAttribute('src');try{a.load()}catch{}}}
function applyBgmState(state){
  if(!state)return;ensureAudioEngine();if(APP.state)APP.state.sound_state=state;updateNowPlaying(state);if(state.status==='stopped'||!state.sound_id){stopSoundEngines();updateSoundProgress();return}
  const snd=state.sound||soundById(state.sound_id);if(!snd)return;
  // Older campaigns may still contain legacy non-file sound entries. They remain deletable for
  // compatibility, but link playback is intentionally no longer supported.
  if(snd.source_type!=='file'){stopSoundEngines();updateSoundProgress();return}
  const prefs=soundPrefs(),serverVol=Number(state.bgm_volume??state.volume),personalVol=Number(prefs.bgm),vol=Math.max(0,Math.min(1,(Number.isFinite(serverVol)?serverVol:1)*(Number.isFinite(personalVol)?personalVol:.7))),elapsed=state.status==='playing'?Math.max(0,(Date.now()-Date.parse(state.updated_at||new Date().toISOString()))/1000):0,basePos=Math.max(0,Number(state.position)||0),freshStart=Number(APP.forceBgmStartId)===Number(state.sound_id)||(basePos===0&&elapsed<2),a=$('#dwBgmAudio'),want=new URL(snd.source,location.href).href,changing=a&&a.src!==want,pos=(freshStart||changing)?basePos:basePos+elapsed;
  if(changing){a.pause();a.src=snd.source;a.load()}a.volume=vol;const place=()=>{if(freshStart||Math.abs((a.currentTime||0)-pos)>2.5)try{a.currentTime=Math.min(pos,Number.isFinite(a.duration)&&a.duration>0?a.duration:pos)}catch{}};if(a.readyState>=1)place();else a.addEventListener('loadedmetadata',place,{once:true});if(state.status==='playing'&&APP.soundEnabled)a.play().catch(()=>{});else a.pause();
  if(Number(APP.forceBgmStartId)===Number(state.sound_id))APP.forceBgmStartId=null;updateSoundProgress()
}

function fmtClock(sec){sec=Math.max(0,Math.floor(Number(sec)||0));return `${Math.floor(sec/60)}:${String(sec%60).padStart(2,'0')}`}
function updateNowPlaying(state=APP.state?.sound_state){let el=$('#nowPlayingMini');if(!state||state.status==='stopped'||!state.sound_id){el?.remove();return}const snd=state.sound||soundById(state.sound_id);if(!snd)return;if(!el){document.body.insertAdjacentHTML('beforeend','<div id="nowPlayingMini" class="now-playing-mini"></div>');el=$('#nowPlayingMini')}el.textContent=`♫ ${snd.name}${state.status==='paused'?' · 일시정지':''}`}
function playSfxEvent(ev){if(!APP.soundEnabled)return;const snd=ev.sound;if(!snd||snd.source_type!=='file')return;const p=soundPrefs(),a=new Audio(snd.source),sv=Number(ev.volume),pv=Number(p.sfx);a.volume=Math.max(0,Math.min(1,(Number.isFinite(sv)?sv:1)*(Number.isFinite(pv)?pv:.8)));a.play().catch(()=>{})}
function openSoundPanel(){closeGMSettings();APP.soundEnabled=true;localStorage.setItem(SOUND_ENABLED_KEY,'1');renderSoundDrawer();applyBgmState(APP.state?.sound_state)}

function soundSliderVolume(selector,fallback=1){const raw=Number($(selector)?.value);return Math.max(0,Math.min(1,Number.isFinite(raw)?raw:fallback));}
function attachGmVolumeSlider(selector,kind){const input=$(selector);if(!input)return;let start=Number(input.value)||0,timer=null;input.addEventListener('pointerdown',()=>{start=Number(input.value)||0});input.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(()=>{if(APP.state?.sound_state){const v=Number(input.value)||0;if(kind==='bgm'){APP.state.sound_state.bgm_volume=v;APP.state.sound_state.volume=v}else APP.state.sound_state.sfx_volume=v;}},80)});const commit=async()=>{clearTimeout(timer);const v=Math.max(0,Math.min(1,Number(input.value)||0));if(Math.abs(v-start)<0.0001)return;start=v;await setGmSoundVolume(kind,v)};input.addEventListener('change',commit);input.addEventListener('pointerup',commit);}
function attachSoundUpload(sel,kind){$(sel)?.addEventListener('submit',async e=>{e.preventDefault();const f=new FormData(e.currentTarget),file=f.get('file');if(!file?.size)return toast('오디오 파일을 선택하세요.');const fd=new FormData();fd.append('kind',kind);fd.append('name',f.get('name')||'');fd.append('file',file);try{toast('사운드 업로드 중…',1200);await apiForm(`/api/rooms/${APP.creds.room}/sounds/upload`,fd,60000);await refreshState(true);toast('사운드를 추가했습니다.')}catch(err){toast(err.message,4000)}})}
async function setGmSoundVolume(kind,volume){try{const r=await api(`/api/rooms/${APP.creds.room}/sounds/volume`,{method:'POST',body:JSON.stringify({kind,volume})});if(APP.state?.sound_state){APP.state.sound_state.bgm_volume=r.bgm_volume;APP.state.sound_state.sfx_volume=r.sfx_volume;APP.state.sound_state.volume=r.bgm_volume}if(kind==='bgm')applyBgmState(APP.state?.sound_state)}catch(e){toast(e.message,3000)}}

/* =========================================================
   Character, spell, multiclass, and management helpers.
   ========================================================= */
const MC_BEGINNER='다중직업 (초급)';
const MC_INTERMEDIATE='다중직업 (중급)';
function spellLevelInfo(level){const raw=String(level??'').trim(),numeric=/^\d+$/.test(raw),value=numeric?Number(raw):0;return {raw,numeric,value};}
function spellLevelLabel(level){const x=spellLevelInfo(level);return x.numeric?`LV.${x.value}`:x.raw;}
function spellEffectiveLevel(level){const x=spellLevelInfo(level);return x.numeric?x.value:0;}
function validateSpellLevelValue(level){const raw=String(level??'').trim();if(!raw)return {ok:false,message:'레벨 / 분류를 입력하세요.'};if(/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(raw)){const n=Number(raw);if(!Number.isInteger(n)||n<1||n>10)return {ok:false,message:'숫자 주문 레벨은 1~10의 정수만 사용할 수 있습니다.'};return {ok:true,value:String(n),effective:n};}return {ok:true,value:raw,effective:0};}

function npcBondRow(x={}){return `<div class="npc-bond-row"><input class="input" data-npc-bond-name value="${attr(x.name||x.memo||'')}" placeholder="관계 대상 이름"><div class="npc-bond-desc-wrap"><textarea class="textarea smart-textarea" data-max-grow="220" data-npc-bond-desc placeholder="관계 설명">${rawEsc(x.desc||x.text||'')}</textarea></div><button class="btn small danger" data-npc-bond-del type="button">삭제</button></div>`}

function monsterFolderKey(folder){return folder?.id==null?'__loose__':String(folder.id)}
function monsterCatalogState(monsterId){
  const cat=(APP.state.monster_catalog_admin||[]).find(x=>Number(x.monster_id)===Number(monsterId));
  if(!cat)return {level:'none',label:'아직 출현하지 않음'};
  const keys=['name','hp','armor','attack','damage','range','tags','instinct','special','moves','description'],rv=cat.reveal||{},count=keys.filter(k=>rv[k]===true).length;
  if(count===0)return {level:'seen',label:'출현만 함 · 정보 비공개'};
  if(count===keys.length)return {level:'full',label:'모든 도감 정보 공개'};
  return {level:'partial',label:`일부 정보 공개 · ${count}/${keys.length}`};
}
function monsterCatalogDot(monsterId){const st=monsterCatalogState(monsterId);return st.level==='none'?'':`<i class="monster-catalog-dot ${st.level}" title="${attr(st.label)}" aria-label="${attr(st.label)}"></i>`;}
function renderMonsterGroup(folder){
  APP.monsterCollapsed=APP.monsterCollapsed||{};
  const mons=(APP.state.monsters||[]).filter(m=>(m.folder_id??null)===(folder?.id??null)).sort((a,b)=>(a.sort_order||9999)-(b.sort_order||9999)),label=folder?folder.name:'미분류',key=monsterFolderKey(folder),closed=!!APP.monsterCollapsed[key];
  return `<div class="monster-folder ${closed?'collapsed':''}" ${folder?`draggable="true" data-sort-kind="folders" data-sort-id="${folder.id}"`:''}><div class="monster-folder-head"><button class="monster-folder-title" data-monster-folder-toggle="${attr(key)}" type="button" title="${closed?'펼치기':'접기'}" aria-expanded="${closed?'false':'true'}"><span class="monster-folder-caret" aria-hidden="true">${closed?'▸':'▾'}</span><span class="monster-folder-name ${folder&&!monsterFolderIsBuiltin(folder)?'no-i18n':''}">${folder?recordEsc(label,monsterFolderIsBuiltin(folder)):esc(label)}</span></button>${folder?`<div class="monster-folder-actions"><button class="mini-icon" data-folder-rename="${folder.id}" title="폴더 이름 변경" aria-label="폴더 이름 변경" type="button">✎</button><button class="mini-icon danger" data-folder-delete="${folder.id}" title="폴더 삭제" aria-label="폴더 삭제" type="button">×</button></div>`:''}</div><div class="monster-folder-list" ${closed?'hidden':''}>${mons.map(m=>`<button data-monster="${m.id}" class="${m.id===APP.gmMonsterId?'active':''}" type="button">${monsterCatalogDot(m.id)}<span class="${monsterIsBuiltin(m)?'':'no-i18n'}">${recordEsc(m.name,monsterIsBuiltin(m))}</span></button>`).join('')||'<div class="side-empty small">비어 있음</div>'}</div></div>`;
}
function monsterBuilderModel(){
  const group=$('input[name="mbGroup"]:checked')?.value||'group',size=$('input[name="mbSize"]:checked')?.value||'normal',defense=Number($('input[name="mbDefense"]:checked')?.value)||0,magic=$('#mbMagicDefense')?.checked;
  const base={horde:{die:'D6',hp:3,tag:'대집단'},group:{die:'D8',hp:6,tag:'소집단'},solitary:{die:'D10',hp:12,tag:'외톨이'}}[group],tags=[base.tag],range=[];let hp=base.hp,modifier=0,armor=defense,mode='normal',count=1;
  if(size==='tiny'){modifier-=2;tags.push('매우 작음');range.push('반걸음')}else if(size==='small'){tags.push('작음');range.push('한걸음')}else if(size==='normal'){range.push('한걸음')}else if(size==='large'){hp+=4;modifier+=1;tags.push('큼');range.push('한걸음','몇걸음')}else if(size==='huge'){hp+=8;modifier+=3;tags.push('거대');range.push('몇걸음')}
  if(defense===4||magic)tags.push('마법적');
  $$('[data-mb-trait]:checked').forEach(i=>{const k=i.dataset.mbTrait;if(k==='strength'){modifier+=2;tags.push('괴력')}else if(k==='offense'){mode='high';count=2}else if(k==='defense'){armor+=1}else if(k==='endurance'){hp+=4}else if(k==='organized')tags.push('조직적');else if(k==='intelligent')tags.push('지능적');else if(k==='stealthy')tags.push('은밀');else if(k==='hoarder')tags.push('보물지기');else if(k==='planar')tags.push('이계');else if(k==='construct')tags.push('인공물');else if(k==='terrifying')tags.push('끔찍함');else if(k==='divine')tags.push('신성');});
  return {hp:Math.max(1,hp),armor:Math.max(0,armor),damage:{die:base.die,count,modifier,mode},range:[...new Set(range)].join(', '),tags:[...new Set(tags)]};
}
function updateMonsterBuilderPreview(){const out=$('#monsterBuilderPreview');if(!out)return;const m=monsterBuilderModel();out.innerHTML=`<b>HP ${m.hp} · 장갑 ${m.armor} · 피해 ${esc(monsterDamageText(m.damage))}</b><span>거리 ${htmlEscape(m.range?displayMonsterRange(m.range):translateUiText('직접 입력'))} · 태그 ${htmlEscape(m.tags.length?m.tags.map(displayMonsterTag).join(', '):translateUiText('없음'))}</span>`;}
function showMonsterBuilder(){
  document.body.insertAdjacentHTML('beforeend',`<div class="modal monster-builder-modal" id="monsterBuilderModal"><div class="modal-card monster-builder-card"><div class="modal-head"><div><b>몬스터 빠른 제작</b><span class="small">원작 GM 시트의 질문식 생성을 바탕으로 기본 수치만 채웁니다.</span></div><button class="btn small" data-close-monster-builder type="button">닫기</button></div><div class="modal-body"><div class="monster-builder-grid"><section><h3>1. 어떻게 싸우나요?</h3><label class="choice"><input type="radio" name="mbGroup" value="horde"><span>대집단 · D6 / HP 3</span></label><label class="choice"><input type="radio" name="mbGroup" value="group" checked><span>소집단 · D8 / HP 6</span></label><label class="choice"><input type="radio" name="mbGroup" value="solitary"><span>외톨이 · D10 / HP 12</span></label></section><section><h3>2. 얼마나 큰가요?</h3><label class="choice"><input type="radio" name="mbSize" value="tiny"><span>매우 작음 · 반걸음 · 피해 -2</span></label><label class="choice"><input type="radio" name="mbSize" value="small"><span>작음 · 한걸음</span></label><label class="choice"><input type="radio" name="mbSize" value="normal" checked><span>사람 크기 · 한걸음</span></label><label class="choice"><input type="radio" name="mbSize" value="large"><span>큼 · HP +4 / 피해 +1</span></label><label class="choice"><input type="radio" name="mbSize" value="huge"><span>거대 · HP +8 / 피해 +3</span></label></section><section><h3>3. 가장 중요한 방어는?</h3><label class="choice"><input type="radio" name="mbDefense" value="0" checked><span>천·살 · 장갑 0</span></label><label class="choice"><input type="radio" name="mbDefense" value="1"><span>가죽·두꺼운 가죽 · 장갑 1</span></label><label class="choice"><input type="radio" name="mbDefense" value="2"><span>사슬·비늘 · 장갑 2</span></label><label class="choice"><input type="radio" name="mbDefense" value="3"><span>판금·뼈 · 장갑 3</span></label><label class="choice"><input type="radio" name="mbDefense" value="4"><span>영구 마법 방호 · 장갑 4</span></label><label class="choice compact-choice"><input id="mbMagicDefense" type="checkbox"><span>마법적 태그 추가</span></label></section><section><h3>4. 무엇으로 유명한가요?</h3><div class="monster-builder-traits"><label><input data-mb-trait="strength" type="checkbox"> 괴력 · 피해 +2</label><label><input data-mb-trait="offense" type="checkbox"> 공격에 능숙 · 피해 고굴림</label><label><input data-mb-trait="defense" type="checkbox"> 방어에 능숙 · 장갑 +1</label><label><input data-mb-trait="endurance" type="checkbox"> 비범한 지구력 · HP +4</label><label><input data-mb-trait="organized" type="checkbox"> 조직적</label><label><input data-mb-trait="intelligent" type="checkbox"> 지능적</label><label><input data-mb-trait="stealthy" type="checkbox"> 은밀</label><label><input data-mb-trait="hoarder" type="checkbox"> 보물지기</label><label><input data-mb-trait="planar" type="checkbox"> 이계</label><label><input data-mb-trait="construct" type="checkbox"> 인공물</label><label><input data-mb-trait="terrifying" type="checkbox"> 끔찍함</label><label><input data-mb-trait="divine" type="checkbox"> 신성</label></div></section></div><div id="monsterBuilderPreview" class="monster-builder-preview"></div><div class="notice">적용 후에도 이름·공격·본능·특기·몬스터 행동과 설명은 직접 작성하세요. 이 도구는 판단을 대신하지 않고 편집기에 출발값만 넣습니다.</div><div class="modal-actions"><button id="applyMonsterBuilder" class="btn dark" type="button">현재 몬스터 편집기에 적용</button></div></div></div></div>`);
  const modal=$('#monsterBuilderModal'),close=()=>modal?.remove();$('[data-close-monster-builder]',modal)?.addEventListener('click',close);modal?.addEventListener('click',e=>{if(e.target===modal)close()});$$('input',modal).forEach(i=>i.addEventListener('change',updateMonsterBuilderPreview));$('#applyMonsterBuilder',modal)?.addEventListener('click',()=>{const m=monsterBuilderModel();$('#monsterHp').value=m.hp;$('#monsterArmor').value=m.armor;$('#monsterDamageDie').value=m.damage.die;$('#monsterDamageCount').value=m.damage.count;$('#monsterDamageMod').value=m.damage.modifier;$('#monsterDamageMode').value=m.damage.mode;$('#monsterRange').value=m.range;const allowed=new Set((APP.state.room.rules?.monster_tags||[]));$$('[data-monster-tag]').forEach(i=>{i.checked=m.tags.includes(i.value)});const missing=m.tags.filter(t=>!allowed.has(t));const tagText=$('#monsterTagText');if(tagText)tagText.textContent=m.tags.filter(t=>allowed.has(t)).map(displayMonsterTag).join(', ')||translateUiText('태그 없음');$('.monster-damage-preview b').textContent=monsterDamageText(m.damage);close();if(missing.length)toast(`캠페인 태그 목록에 없어 제외됨: ${missing.map(displayMonsterTag).join(', ')}`,4200);else toast('빠른 제작 값을 편집기에 적용했습니다. 본능과 행동을 마무리하세요.',2800)});updateMonsterBuilderPreview();
}

function renderGMMonsters(){
  const folders=[...(APP.state.monster_folders||[])].sort((a,b)=>(a.sort_order||9999)-(b.sort_order||9999)),mons=APP.state.monsters||[];if(APP.gmMonsterId&&!mons.some(x=>x.id===APP.gmMonsterId))APP.gmMonsterId=null;const selected=mons.find(x=>x.id===APP.gmMonsterId)||blankMonster(APP.gmMonsterFolderId),d=selected.data?.damage||{die:'D6',count:1,modifier:0,mode:'normal'},selectedTags=[...(selected.data?.tags||[])],tags=[...new Set([...(APP.state.room.rules?.monster_tags||[]),...selectedTags])],cat=(APP.state.monster_catalog_admin||[]).find(x=>Number(x.monster_id)===Number(selected.id)),rv=cat?.reveal||{};
  const revealKeys=MONSTER_CATALOG_REVEAL_FIELDS,builtin=monsterIsBuiltin(selected);
  return `<div class="split monster-split"><aside class="side-list monster-side sortable-list"><div class="monster-side-actions"><button id="newMonsterFolder" type="button">폴더 생성</button><button id="newMonsterLoose" type="button">${APP.language==='en'?'Create Monster':'몬스터 생성'}</button></div><div class="monster-catalog-legend"><span><i class="monster-catalog-dot seen"></i>출현</span><span><i class="monster-catalog-dot partial"></i>일부 공개</span><span><i class="monster-catalog-dot full"></i>전체 공개</span></div>${renderMonsterGroup(null)}${folders.map(renderMonsterGroup).join('')}</aside><section class="panel gm-editor"><div class="head sticky-edit-head"><span class="${builtin?'':'no-i18n'}">${selected.id?recordEsc(selected.name,builtin):'새 몬스터'}</span><div class="inline-actions"><button id="monsterQuickBuild" class="btn small" type="button">빠른 제작</button>${selected.id?`<button id="monsterAppear" class="btn small" type="button">${cat?'도감 갱신':'출현'}</button>`:''}<button id="saveMonster" class="btn small" type="button">저장</button>${selected.id?'<button id="deleteMonster" class="btn small danger" type="button">삭제</button>':''}</div></div><div class="body"><div class="grid four monster-stats"><label class="field"><span>몬스터 이름</span><input id="monsterName" class="input" ${builtin?'':'data-i18n-value="raw"'} value="${attr(contentValue(selected.name||'',builtin))}"></label><label class="field"><span>HP</span><input id="monsterHp" class="input" type="number" min="0" value="${Number(selected.data?.hp)||0}"></label><label class="field"><span>장갑</span><input id="monsterArmor" class="input" type="number" min="0" value="${Number(selected.data?.armor)||0}"></label><label class="field"><span>지역 / 폴더</span><select id="monsterFolder" class="select"><option value="">미분류</option>${folders.map(f=>`<option value="${f.id}" ${Number(selected.folder_id)===Number(f.id)?'selected':''}>${recordEsc(f.name,monsterFolderIsBuiltin(f))}</option>`).join('')}</select></label><label class="field span2"><span>공격 이름</span><input id="monsterAttack" class="input" ${builtin?'':'data-i18n-value="raw"'} value="${attr(contentValue(selected.data?.attack||'',builtin))}" placeholder="예: 깨물기"></label><label class="field span2"><span>공격 거리 / 범위</span><input id="monsterRange" class="input" ${builtin?'':'data-i18n-value="raw"'} value="${attr(contentValue(selected.data?.range||'',builtin))}" placeholder="예: 한걸음, 몇걸음"></label></div>
  <h3>공격 피해</h3><div class="monster-damage-builder"><label>주사위<select id="monsterDamageDie" class="select">${['D2','D4','D6','D8','D10','D12'].map(x=>`<option ${x===String(d.die||'D6').toUpperCase()?'selected':''}>${x}</option>`).join('')}</select></label><label>개수<input id="monsterDamageCount" class="input" type="number" min="1" max="20" value="${Number(d.count)||1}"></label><label>수정치<input id="monsterDamageMod" class="input" type="number" min="-99" max="99" value="${Number(d.modifier)||0}"></label><label>굴림 방식<select id="monsterDamageMode" class="select"><option value="normal" ${d.mode==='normal'?'selected':''}>일반</option><option value="high" ${d.mode==='high'?'selected':''}>고(높은 값)</option><option value="low" ${d.mode==='low'?'selected':''}>저(낮은 값)</option></select></label><div class="monster-damage-preview"><b>${esc(monsterDamageText(d))}</b>${selected.id?'<button id="monsterDamageRoll" class="btn dark" type="button">피해 굴리기</button>':''}</div></div>${APP.language==='en'?'<div class="small muted monster-roll-mode-note"><b>Roll Mode Guide</b> · Normal adds all dice. High uses only the highest die and Low uses only the lowest die, then applies the modifier. Example: High[2D8] + 2 = the higher of two D8s + 2. See Help → Monsters and Bestiary for details.</div>':'<div class="small muted monster-roll-mode-note"><b>굴림 방식 안내</b> · 일반은 주사위를 모두 합산합니다. 고는 여러 개 중 가장 높은 하나, 저는 가장 낮은 하나만 사용한 뒤 수정치를 적용합니다. 예: 고[2D8] + 2 = D8 두 개 중 높은 값 +2. 자세한 내용은 도움말 → 몬스터와 도감에서 확인할 수 있습니다.</div>'}
  <h3>태그</h3><div class="monster-tag-control"><div id="monsterTagText" class="monster-tag-text">${selectedTags.length?htmlEscape(selectedTags.map(displayMonsterTag).join(', ')):translateUiText('태그 없음')}</div><div class="monster-tag-picker"><button id="monsterTagPickerBtn" class="btn small" type="button">태그 선택</button><div id="monsterTagPicker" class="monster-tag-menu" hidden>${tags.map(t=>`<label><input type="checkbox" data-monster-tag value="${attr(t)}" ${selectedTags.includes(t)?'checked':''}><span>${htmlEscape(displayMonsterTag(t))}</span></label>`).join('')||'<div class="small muted">규칙에 등록된 태그가 없습니다.</div>'}</div></div></div><div class="grid two monster-text-grid"><label class="field"><span>본능</span><textarea id="monsterInstinct" class="textarea smart-textarea">${recordEsc(selected.data?.instinct||'',builtin)}</textarea></label><label class="field"><span>특기 사항</span><textarea id="monsterSpecial" class="textarea smart-textarea">${recordEsc(selected.data?.special||'',builtin)}</textarea></label></div><label class="field"><span>몬스터 행동 · 한 줄에 하나</span><textarea id="monsterMoves" class="textarea smart-textarea">${htmlEscape((selected.data?.moves||[]).map(x=>builtin?displayContent(x):String(x??'')).join('\n'))}</textarea></label><label class="field"><span>몬스터 설명</span><textarea id="monsterDescription" class="textarea smart-textarea" data-max-grow="320">${recordEsc(selected.data?.description||'',builtin)}</textarea></label>
  ${selected.id?`<section class="catalog-reveal-admin"><h3>플레이어 도감 공개</h3><div class="notice">출현 후 공개한 항목만 플레이어에게 보입니다. 공개하지 않은 정보는 ???로 표시됩니다.</div><div class="catalog-reveal-grid">${revealKeys.map(([k,l])=>`<label><input data-catalog-reveal="${k}" type="checkbox" ${rv[k]?'checked':''}> ${l}</label>`).join('')}</div><div class="inline-actions"><button id="revealAllCatalog" class="btn" type="button">전부 공개</button><button id="saveCatalogReveal" class="btn" type="button">도감 공개 설정 저장</button>${cat?'<button id="removeCatalog" class="btn danger" type="button">도감에서 제거</button>':''}</div></section>`:''}</div></section></div>`;
}
function attachGMMonsters(){
  $$('[data-monster]').forEach(b=>b.addEventListener('click',()=>{APP.gmMonsterId=Number(b.dataset.monster);const m=(APP.state.monsters||[]).find(x=>x.id===APP.gmMonsterId);APP.gmMonsterFolderId=m?.folder_id??null;renderGM()}));
  const toggleFolder=b=>{const key=b.dataset.monsterFolderToggle;APP.monsterCollapsed=APP.monsterCollapsed||{};APP.monsterCollapsed[key]=!APP.monsterCollapsed[key];const closed=!!APP.monsterCollapsed[key],folder=b.closest('.monster-folder'),list=$('.monster-folder-list',folder),caret=$('.monster-folder-caret',b);if(list)list.hidden=closed;folder?.classList.toggle('collapsed',closed);b.setAttribute('aria-expanded',closed?'false':'true');b.title=translateUiText(closed?'펼치기':'접기');if(caret)caret.textContent=closed?'▸':'▾'};
  $$('[data-monster-folder-toggle]').forEach(b=>b.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();toggleFolder(b)}));
  $('#monsterQuickBuild')?.addEventListener('click',showMonsterBuilder);
  $('#newMonsterLoose')?.addEventListener('click',()=>{APP.gmMonsterId=null;APP.gmMonsterFolderId=null;renderGM()});$('#newMonsterFolder')?.addEventListener('click',createMonsterFolder);$$('[data-folder-rename]').forEach(b=>b.addEventListener('click',()=>renameMonsterFolder(Number(b.dataset.folderRename))));$$('[data-folder-delete]').forEach(b=>b.addEventListener('click',()=>deleteMonsterFolder(Number(b.dataset.folderDelete))));$('#saveMonster')?.addEventListener('click',saveMonster);$('#deleteMonster')?.addEventListener('click',deleteMonster);$('#monsterAppear')?.addEventListener('click',monsterAppear);$('#revealAllCatalog')?.addEventListener('click',revealAllCatalog);$('#saveCatalogReveal')?.addEventListener('click',saveCatalogReveal);$('#removeCatalog')?.addEventListener('click',removeCatalog);$('#monsterDamageRoll')?.addEventListener('click',prepareMonsterDamage);
  ['#monsterDamageDie','#monsterDamageCount','#monsterDamageMod','#monsterDamageMode'].forEach(sel=>$(sel)?.addEventListener('input',()=>{const x={die:$('#monsterDamageDie').value,count:Number($('#monsterDamageCount').value)||1,modifier:Number($('#monsterDamageMod').value)||0,mode:$('#monsterDamageMode').value};$('.monster-damage-preview b').textContent=monsterDamageText(x)}));
  $('#monsterTagPickerBtn')?.addEventListener('click',e=>{e.stopPropagation();const menu=$('#monsterTagPicker');if(menu)menu.hidden=!menu.hidden});
  $$('[data-monster-tag]').forEach(i=>i.addEventListener('change',()=>{const names=$$('[data-monster-tag]:checked').map(x=>x.value),out=$('#monsterTagText');if(out){out.textContent=names.length?names.map(displayMonsterTag).join(', '):translateUiText('태그 없음');out.classList.toggle('empty',!names.length)}}));
}

function spellcastingProfile(className){
  const c=APP.state.classes?.[className]||{},raw=c.spellcasting||{},hasSpells=(APP.state.spells?.[className]||[]).length>0;
  const known=['selected','all','manual'].includes(raw.known_mode)?raw.known_mode:'manual',prepare=['known','all','none','manual'].includes(raw.prepare_mode)?raw.prepare_mode:'manual',limit=['level_sum','count','none'].includes(raw.limit_mode)?raw.limit_mode:'none';
  return {enabled:raw.enabled===undefined?hasSpells:!!raw.enabled,known_mode:known,known_label:String(raw.known_label||'습득'),prepare_mode:prepare,prepare_label:String(raw.prepare_label||'준비'),limit_mode:limit,limit_offset:Number.isFinite(Number(raw.limit_offset))?Number(raw.limit_offset):0,limit_count:Math.max(0,Number(raw.limit_count)||0),zero_level_label:String(raw.zero_level_label||'0레벨'),zero_auto_known:raw.zero_auto_known!==false,zero_auto_prepared:raw.zero_auto_prepared!==false,zero_limit_exempt:raw.zero_limit_exempt!==false,starting_choice_level:Math.max(0,Number(raw.starting_choice_level)||0),starting_choice_count:Math.max(0,Number(raw.starting_choice_count)||0),learn_per_level:Math.max(0,Number(raw.learn_per_level)||0)};
}
function spellcastingPreset(kind){
  if(kind==='wizard')return {enabled:true,known_mode:'selected',known_label:'주문서',prepare_mode:'known',prepare_label:'준비',limit_mode:'level_sum',limit_offset:1,limit_count:0,zero_level_label:'간편',zero_auto_known:true,zero_auto_prepared:true,zero_limit_exempt:true,starting_choice_level:1,starting_choice_count:3,learn_per_level:1};
  if(kind==='cleric')return {enabled:true,known_mode:'all',known_label:'받은 주문',prepare_mode:'all',prepare_label:'준비',limit_mode:'level_sum',limit_offset:1,limit_count:0,zero_level_label:'암송',zero_auto_known:true,zero_auto_prepared:true,zero_limit_exempt:true,starting_choice_level:0,starting_choice_count:0,learn_per_level:0};
  return {enabled:true,known_mode:'manual',known_label:'습득',prepare_mode:'manual',prepare_label:'준비',limit_mode:'none',limit_offset:0,limit_count:0,zero_level_label:'0레벨',zero_auto_known:true,zero_auto_prepared:true,zero_limit_exempt:true,starting_choice_level:0,starting_choice_count:0,learn_per_level:0};
}
function spellKnownCap(profile,level){if(profile.known_mode!=='selected')return Infinity;const start=Number(profile.starting_choice_count)||0,at=Math.max(0,Number(profile.starting_choice_level)||0),per=Math.max(0,Number(profile.learn_per_level)||0),lv=Math.max(1,Number(level)||1);return Math.max(0,start+(at>0?Math.max(0,lv-at)*per:Math.max(0,lv-1)*per));}
function spellPrepLimit(profile,level){if(profile.limit_mode==='level_sum')return Math.max(0,(Number(level)||1)+(Number(profile.limit_offset)||0));if(profile.limit_mode==='count')return Math.max(0,Number(profile.limit_count)||0);return Infinity;}
function spellPrepUsage(profile,names,spells){const set=new Set(names||[]);if(profile.limit_mode==='count')return [...set].filter(n=>spells.some(sp=>sp.name===n&&!(profile.zero_limit_exempt&&spellEffectiveLevel(sp.level)===0))).length;if(profile.limit_mode==='level_sum')return spells.reduce((sum,sp)=>set.has(sp.name)&&!(profile.zero_limit_exempt&&spellEffectiveLevel(sp.level)===0)?sum+Math.max(0,spellEffectiveLevel(sp.level)):sum,0);return 0;}
function spellTrackState(state,key){const raw=(state.spell_tracks||{})[key]||{};return {known:[...(raw.known||[])],prepared:[...(raw.prepared||[])],starting_complete:!!raw.starting_complete};}
function updateSpellTrack(state,key,next){state.spell_tracks={...(state.spell_tracks||{}),[key]:{known:[...(next.known||[])],prepared:[...(next.prepared||[])],starting_complete:!!next.starting_complete}};return state.spell_tracks;}
function blankClass(){return {hp:6,damage:'D6',load:8,races:[],alignments:[],bonds:[],gear:'',start:[],a25:[],a610:[],multiclass_25:false,multiclass_610:false,spellcasting:{...spellcastingPreset('manual'),enabled:false}};}
function classMoveSection(title,kind,list,multiclassLabel='',enabled=false,allAdvanced=[],className='',builtin=false){const toggleLabel=multiclassLabel?(APP.language==='en'?`Enable ${translateUiText(multiclassLabel)}`:`${multiclassLabel} 활성화`):'';return `<div class="move-range-head"><b>${esc(title)}</b>${multiclassLabel?`<label class="move-range-toggle"><span>${htmlEscape(toggleLabel)}</span><input type="checkbox" data-class-multiclass="${attr(kind)}" ${enabled?'checked':''}></label>`:''}</div>${moveEditor(kind,list||[],allAdvanced,className,builtin)}`}
function spellcastingEditor(c,builtin=false){
  const base={...spellcastingPreset('manual'),enabled:false},p={...base,...(c.spellcasting||{})};
  const opt=(v,l,cur)=>`<option value="${v}" ${cur===v?'selected':''}>${esc(l)}</option>`;
  return `<section class="spellcasting-rules-editor"><div class="row-head"><div><h3>${esc('주문 운용 규칙')}</h3><div class="small muted">${esc('직업 이름이 아니라 아래 규칙 조합으로 주문 시스템이 작동합니다. 프리셋은 값을 채워주는 편의 기능일 뿐이며 저장되는 것은 개별 규칙입니다.')}</div></div><label class="choice compact-choice"><input id="classSpellEnabled" type="checkbox" ${p.enabled?'checked':''}><span>${esc('주문 시스템 사용')}</span></label></div><div class="inline-actions spellcasting-presets"><button class="btn small" data-spellcasting-preset="wizard" type="button">${esc('마법사식 값 채우기')}</button><button class="btn small" data-spellcasting-preset="cleric" type="button">${esc('사제식 값 채우기')}</button><button class="btn small" data-spellcasting-preset="manual" type="button">${esc('자유/수동 값 채우기')}</button></div><div class="grid three spellcasting-rule-grid"><label class="field"><span>${esc('주문을 아는 방식')}</span><select id="classSpellKnownMode" class="select">${opt('selected','선택해서 습득',p.known_mode)}${opt('all','직업 주문 전체를 앎',p.known_mode)}${opt('manual','수동 관리',p.known_mode)}</select></label><label class="field"><span>${esc('습득 목록 이름')}</span><input id="classSpellKnownLabel" class="input" value="${attr(contentValue(p.known_label||'습득',builtin))}" placeholder="예: 주문서"></label><label class="field"><span>${esc('준비 방식')}</span><select id="classSpellPrepareMode" class="select">${opt('known','아는 주문에서 준비',p.prepare_mode)}${opt('all','직업 주문 전체에서 준비',p.prepare_mode)}${opt('none','준비 없이 항상 사용',p.prepare_mode)}${opt('manual','수동 관리',p.prepare_mode)}</select></label><label class="field"><span>${esc('준비 표시 이름')}</span><input id="classSpellPrepareLabel" class="input" value="${attr(contentValue(p.prepare_label||'준비',builtin))}"></label><label class="field"><span>${esc('준비 한도')}</span><select id="classSpellLimitMode" class="select">${opt('level_sum','주문 레벨 합',p.limit_mode)}${opt('count','준비 개수',p.limit_mode)}${opt('none','제한 없음',p.limit_mode)}</select></label><label class="field"><span>${esc('레벨 합 보정')}</span><input id="classSpellLimitOffset" class="input" type="number" min="-20" max="20" value="${Number(p.limit_offset)||0}"><small>${esc('레벨 합 한도 = 해당 주문직업 레벨 + 이 값')}</small></label><label class="field"><span>${esc('고정 준비 개수')}</span><input id="classSpellLimitCount" class="input" type="number" min="0" max="100" value="${Math.max(0,Number(p.limit_count)||0)}"></label><label class="field"><span>${esc('0레벨 분류 이름')}</span><input id="classSpellZeroLabel" class="input" value="${attr(contentValue(p.zero_level_label||'0레벨',builtin))}" placeholder="예: 간편, 암송"></label><label class="field"><span>${esc('시작 선택 주문 레벨')}</span><input id="classSpellStartLevel" class="input" type="number" min="0" max="10" value="${Math.max(0,Number(p.starting_choice_level)||0)}"><small>${esc('0이면 시작 선택 없음')}</small></label><label class="field"><span>${esc('시작 선택 개수')}</span><input id="classSpellStartCount" class="input" type="number" min="0" max="20" value="${Math.max(0,Number(p.starting_choice_count)||0)}"></label><label class="field"><span>${esc('레벨 상승마다 추가 습득')}</span><input id="classSpellLearnPerLevel" class="input" type="number" min="0" max="20" value="${Math.max(0,Number(p.learn_per_level)||0)}"></label></div><div class="grid three"><label class="choice settings-choice"><input id="classSpellZeroKnown" type="checkbox" ${p.zero_auto_known!==false?'checked':''}><span><b>${esc('0레벨 자동 습득')}</b></span></label><label class="choice settings-choice"><input id="classSpellZeroPrepared" type="checkbox" ${p.zero_auto_prepared!==false?'checked':''}><span><b>${esc('0레벨 자동 준비/사용')}</b></span></label><label class="choice settings-choice"><input id="classSpellZeroExempt" type="checkbox" ${p.zero_limit_exempt!==false?'checked':''}><span><b>${esc('0레벨은 준비 한도에서 제외')}</b></span></label></div></section>`;
}
function collectSpellcastingProfile(){return {enabled:!!$('#classSpellEnabled')?.checked,known_mode:$('#classSpellKnownMode')?.value||'manual',known_label:$('#classSpellKnownLabel')?.value.trim()||'습득',prepare_mode:$('#classSpellPrepareMode')?.value||'manual',prepare_label:$('#classSpellPrepareLabel')?.value.trim()||'준비',limit_mode:$('#classSpellLimitMode')?.value||'none',limit_offset:Number($('#classSpellLimitOffset')?.value)||0,limit_count:Math.max(0,Number($('#classSpellLimitCount')?.value)||0),zero_level_label:$('#classSpellZeroLabel')?.value.trim()||'0레벨',zero_auto_known:!!$('#classSpellZeroKnown')?.checked,zero_auto_prepared:!!$('#classSpellZeroPrepared')?.checked,zero_limit_exempt:!!$('#classSpellZeroExempt')?.checked,starting_choice_level:Math.max(0,Number($('#classSpellStartLevel')?.value)||0),starting_choice_count:Math.max(0,Number($('#classSpellStartCount')?.value)||0),learn_per_level:Math.max(0,Number($('#classSpellLearnPerLevel')?.value)||0)};}
function applySpellcastingPreset(kind){const p=spellcastingPreset(kind);const values={classSpellEnabled:p.enabled,classSpellKnownMode:p.known_mode,classSpellKnownLabel:p.known_label,classSpellPrepareMode:p.prepare_mode,classSpellPrepareLabel:p.prepare_label,classSpellLimitMode:p.limit_mode,classSpellLimitOffset:p.limit_offset,classSpellLimitCount:p.limit_count,classSpellZeroLabel:p.zero_level_label,classSpellZeroKnown:p.zero_auto_known,classSpellZeroPrepared:p.zero_auto_prepared,classSpellZeroExempt:p.zero_limit_exempt,classSpellStartLevel:p.starting_choice_level,classSpellStartCount:p.starting_choice_count,classSpellLearnPerLevel:p.learn_per_level};for(const [id,v] of Object.entries(values)){const el=$('#'+id);if(!el)continue;if(el.type==='checkbox')el.checked=!!v;else el.value=String(v)}toast(kind==='wizard'?'마법사식 주문 규칙 값을 채웠습니다.':kind==='cleric'?'사제식 주문 규칙 값을 채웠습니다.':'자유/수동 주문 규칙 값을 채웠습니다.');}
function structuredClassEditor(c,className='',builtin=false){
  const allAdvanced=[...(c.a25||[]),...(c.a610||[])];
  const raceCards=Object.entries(APP.state.races||{}).filter(([name,r])=>{const enabled=new Set(r.enabled_classes||Object.entries(r.per_class||{}).filter(([,v])=>String(v||'').trim()).map(([k])=>k));return className&&enabled.has(className)}).map(([name,r])=>`<article class="readonly-race-card"><div class="readonly-race-name">${recordEsc(name,raceIsBuiltin(name))}</div><div class="readonly-race-desc ${raceIsBuiltin(name)?'':'no-i18n'}">${recordEsc((r.per_class||{})[className]||r.description||'설명 없음',raceIsBuiltin(name))}</div></article>`).join('');
  return `<h3>사용 가능한 종족</h3>${APP.language==='en'?'<div class="notice">Manage race availability and class-specific race features from the <b>Races</b> menu. This view is read-only.</div>':'<div class="notice">종족의 사용 여부와 직업별 설명은 <b>종족</b> 메뉴에서 관리합니다. 이 화면에서는 읽기만 할 수 있습니다.</div>'}<div class="readonly-race-grid">${raceCards||'<div class="notice">현재 이 직업에 연결된 종족이 없습니다. 종족 메뉴에서 이 직업을 사용 가능으로 체크하세요.</div>'}</div><h3>가치관</h3><div id="alignEditor" class="editor-list">${(c.alignments||[]).map((r,i)=>editorPair('align',i,r.name,r.desc,builtin)).join('')}</div><button class="btn small" data-addrow="align" type="button">＋ 가치관</button><h3>인연</h3><textarea id="classBonds" class="textarea" rows="5">${htmlEscape((c.bonds||[]).map(x=>builtin?displayMultilineContent(x):String(x??'')).join('\n'))}</textarea><h3>시작 장비 안내</h3><textarea id="classGear" class="textarea" rows="9">${htmlEscape(builtin?displayMultilineContent(c.gear||''):String(c.gear||''))}</textarea>${spellcastingEditor(c,builtin)}${classMoveSection('직업 시작 행동','start',c.start||[],'',false,allAdvanced,className,builtin)}${classMoveSection('고급 행동 2–5','a25',c.a25||[],'다중직업(초급)',!!c.multiclass_25,allAdvanced,className,builtin)}${classMoveSection('고급 행동 6–10','a610',c.a610||[],'다중직업(중급)',!!c.multiclass_610,allAdvanced,className,builtin)}`;
}
async function saveClass(){
  const name=$('#className').value.trim();if(!name)return toast('직업 이름을 입력하세요.');const current=APP.gmClassName&&APP.gmClassName!=='__new__'?(APP.state.classes[APP.gmClassName]||{}):{};
  const data={hp:Number($('#classHp').value)||6,damage:$('#classDamage').value.trim()||'D6',load:Number($('#classLoad').value)||0,races:current.races||[],alignments:collectRows('#alignEditor .editor-row'),bonds:$('#classBonds').value.split('\n').map(x=>x.trim()).filter(Boolean),gear:$('#classGear').value,start:collectRows('[data-move-editor="start"] .editor-row'),a25:collectRows('[data-move-editor="a25"] .editor-row'),a610:collectRows('[data-move-editor="a610"] .editor-row'),multiclass_25:!!$('[data-class-multiclass="a25"]')?.checked,multiclass_610:!!$('[data-class-multiclass="a610"]')?.checked,multiclass_bundles:clone(current.multiclass_bundles||[]),spellcasting:collectSpellcastingProfile()};
  const invalidRequirement=[...data.a25,...data.a610].find(x=>x.has_requirement&&!x.requires_move);if(invalidRequirement)return toast(`${invalidRequirement.name}의 선행 행동을 선택하세요.`);
  const effectError=invalidMoveEffect(data);if(effectError)return toast(effectError,4200);
  const wasBuiltin=!!current._builtin,payload=wasBuiltin?restoreDisplayedBuiltIn({name,data},{name:APP.gmClassName,data:current}):{name,data};try{await api(`/api/rooms/${APP.creds.room}/classes`,{method:'PUT',body:JSON.stringify({name:payload.name,old_name:APP.gmClassName==='__new__'?null:(APP.gmClassName||null),data:payload.data})});APP.gmClassName=name;await refreshState(true);toast('직업 저장 · 종족 메뉴에 새 직업 설명 칸도 준비되었습니다.')}catch(e){toast(e.message,3500)}
}
function multiclassChoiceCards(source,level){const choices=multiclassChoices(source,level),builtin=classIsBuiltin(source);return choices.length?choices.map((x,i)=>`<label class="multiclass-choice-card${builtin?'':' no-i18n'}"><input type="radio" name="extraSourceMove" value="${attr(x.name)}" ${i===0?'checked':''}><span class="multiclass-choice-body"><b>${recordEsc(x.name,builtin)}</b><small>${x.bundle?'시작 행동 묶음':`요구 단계 ${x.min_level}`}</small><span>${recordEsc(x.desc||'설명 없음',builtin)}</span></span></label>`).join(''):'<div class="notice">현재 레벨에서 선택할 수 있는 행동이 없습니다.</div>'}
function renderMulticlass(bundle,gmMode,selectedTiers=[]){
  const s=bundle.state,list=s.extra_moves||[],other=Object.keys(APP.state.classes).filter(x=>x!==s.class_name),src=other[0]||'',allowed=gmMode||APP.state.room.rules?.players_can_add_extra_moves!==false,effective=Math.max(1,(Number(s.level)||1)-1),slots=Math.max(0,selectedTiers.length-list.length);
  if(!selectedTiers.length&&!list.length)return '';
  const multiclassNotice=APP.language==='en'?`Current Lv.${Number(s.level)||1} → Treat as Lv.${effective} when choosing a move from another class. Interdependent starting moves are selected together as one starting-move bundle.`:`현재 Lv.${Number(s.level)||1} → 다른 직업 행동을 고를 때 Lv.${effective}로 취급합니다. 서로 의존하는 시작 행동은 시작 행동 묶음 하나로 선택합니다.`;
  const ownedHtml=list.length?`<div class="advanced-grid">${list.map((m,i)=>{const b=classIsBuiltin(m.source_class);return `<article class="adv-card${b?'':' no-i18n'}"><div class="adv-head"><div class="adv-name">${recordEsc(m.name,b)}</div><span class="pill">${recordEsc(m.source_class,b)}</span><span class="pill added-pill">${esc('추가됨')} · ${m.source_name?rawEsc(m.source_name):esc('다중직업')}</span><button class="btn small danger" data-extra-move-del="${i}" type="button">선택 취소</button></div><div class="small muted">Lv.${m.acquired_at_level||s.level}에 획득 · 현재 ${recordEsc(m.source_class,b)} 기준 레벨 ${Math.max(1,(Number(s.level)||1)-(Number(m.acquired_at_level)||Number(s.level)||1)+1)}</div><details class="move-details" open><summary>행동 내용 / 규칙</summary><div class="move-desc">${recordEsc(m.desc||'설명 없음',b)}</div></details></article>`}).join('')}</div>`:'<div class="notice">아직 다중직업으로 가져온 행동이 없습니다.</div>';
  const picker=allowed&&slots>0?`<div class="multiclass-picker"><h3>다른 직업 행동 선택</h3><div class="multiclass-source-row"><label class="field"><span>출처 직업</span><select id="extraSourceClass" class="select">${other.map(x=>`<option value="${attr(x)}">${recordEsc(x,classIsBuiltin(x))}</option>`).join('')}</select></label><div class="small muted">선택 가능 ${slots}개 남음</div></div><div id="extraSourceChoices" class="multiclass-choice-grid">${multiclassChoiceCards(src,Number(s.level)||1)}</div><button id="addExtraMove" class="btn dark" type="button">선택한 행동 가져오기</button></div>`:slots>0?'<div class="notice warn">이 캠페인에서는 플레이어가 다중직업 행동을 직접 선택할 수 없습니다.</div>':'';
  return `<section class="panel multiclass-panel"><div class="head"><span>다중직업 행동 선택</span><span class="small">활성화한 고급 행동 하나마다 다른 직업 행동 하나를 선택합니다.</span></div><div class="body"><div class="notice">${multiclassNotice}</div>${ownedHtml}${picker}</div></section>`;
}

function renderAdvancedPage(bundle,gmMode){
  const s=bundle.state,c=classData(s),builtin=classIsBuiltin(s.class_name),owned=new Set(s.advanced_moves||[]),lv=Number(s.level)||1,points=advancedMovePointInfo(s),cap=points.cap,count=points.used,slotsLeft=points.left,extensionUsed=extensionMovePointUsage(s),baseUsed=owned.size;
  const renderList=(list,minLv)=>list.map(m=>{const has=owned.has(m.name),levelEligible=lv>=minLv,requirement=m.has_requirement?String(m.requires_move||'').trim():'',requirementMet=!requirement||owned.has(requirement),eligible=levelEligible&&requirementMet,canAdd=has||(eligible&&slotsLeft>0)||gmMode;return `<div class="adv-card ${!eligible?'locked':''}${builtin?'':' no-i18n'}"><div class="adv-head"><div class="adv-name">${recordEsc(m.name,builtin)}</div><span class="pill">${minLv===2?'레벨 2부터':'레벨 6부터'}</span>${requirement?`<span class="pill requirement-pill">조건 · ${recordEsc(requirement,builtin)}</span>`:''}<label class="move-check"><input type="checkbox" data-adv="${attr(m.name)}" ${has?'checked':''} ${!canAdd?'disabled':''}> ${has?'보유':'선택'}</label></div><details class="move-details"><summary>설명</summary><div class="move-desc">${recordEsc(m.desc||'',builtin)}</div></details>${!levelEligible?'<div class="small muted">현재 레벨에서는 획득할 수 없지만 설명은 볼 수 있습니다. 필요한 레벨이 지나도 선택 기회는 사라지지 않습니다.</div>':(!requirementMet?`<div class="small muted requirement-warning">${APP.language==='en'?`Learn <b>${recordEsc(requirement,builtin)}</b> before choosing this move.`:`먼저 <b>${recordEsc(requirement,builtin)}</b> 행동을 배워야 선택할 수 있습니다.`}</div>`:'')}</div>`}).join('');
  const multiCard=(label,minLv,enabled)=>{if(!enabled)return '';const has=owned.has(label),eligible=lv>=minLv,canAdd=has||(eligible&&slotsLeft>0)||gmMode;return `<div class="adv-card multiclass-adv-card ${!eligible?'locked':''}"><div class="adv-head"><div class="adv-name">${esc(label)}</div><span class="pill">${minLv===2?'레벨 2부터':'레벨 6부터'}</span><label class="move-check"><input type="checkbox" data-multiclass-adv="${attr(label)}" ${has?'checked':''} ${!canAdd?'disabled':''}> ${has?'보유':'선택'}</label></div><details class="move-details"><summary>설명</summary><div class="move-desc">다른 직업의 행동 하나를 선택합니다. 선택 가능한 행동을 계산할 때 자신의 레벨을 하나 낮게 취급합니다.</div></details></div>`};
  const selectedTiers=[MC_BEGINNER,MC_INTERMEDIATE].filter(x=>owned.has(x));
  const pointNotice=APP.language==='en'?`Lv.${lv}: advanced-move points ${count}/${cap} used · ${slotsLeft} remaining. Class advanced moves use ${baseUsed}; expansion Legendary/Class Moves use ${extensionUsed}. You gain 1 cumulative point for every level above 1, and unspent points never expire.`:`현재 Lv.${lv}: 고급행동 포인트 ${count}/${cap} 사용 · ${slotsLeft} 남음. 기본/다중직업 행동 ${baseUsed}점 · 확장직업 전설/직업 행동 ${extensionUsed}점. 레벨 2부터 레벨이 오를 때마다 1점씩 누적되며, 쓰지 않은 포인트는 사라지지 않습니다.`;
  return `<div class="notice">${pointNotice}</div><div class="advanced-grid" style="margin-top:12px"><section class="panel"><div class="head">고급 행동 · 레벨 2부터</div><div class="body">${multiCard(MC_BEGINNER,2,!!c.multiclass_25)}${renderList(c.a25||[],2)||(!c.multiclass_25?'<div class="muted">등록된 행동이 없습니다.</div>':'')}</div></section><section class="panel"><div class="head">고급 행동 · 레벨 6부터</div><div class="body">${multiCard(MC_INTERMEDIATE,6,!!c.multiclass_610)}${renderList(c.a610||[],6)||(!c.multiclass_610?'<div class="muted">등록된 행동이 없습니다.</div>':'')}</div></section></div>${renderMoveEffectChoices(bundle)}${renderMoveEffectGrants(bundle)}${renderMulticlass(bundle,gmMode,selectedTiers)}`;
}

function attachMoveEffectChoices(bundle,gmMode){
  const s=bundle.state,rows=activeMoveEffects(s),byKey=new Map(rows.map(r=>[r.key,r]));
  const missingAuto=rows.filter(r=>r.effect?.kind==='class_access'&&!Number(moveChoice(s,r.key).acquired_at_level));
  if(missingAuto.length){const all={...(s.move_choices||{})};for(const r of missingAuto)all[r.key]={...(all[r.key]||{}),acquired_at_level:Math.max(1,Number(s.level)||1)};s.move_choices=all;queueMicrotask(()=>patchCharacter(bundle.id,{move_choices:all},gmMode,true));}
  const saveChoice=async(key,next)=>{const all={...(s.move_choices||{})};all[key]={...(all[key]||{}),...next};s.move_choices=all;await patchCharacter(bundle.id,{move_choices:all},gmMode,true)};
  $$('[data-effect-spell]').forEach(sel=>sel.addEventListener('change',()=>{const key=sel.dataset.effectSpell,row=byKey.get(key),box=$(`[data-effect-preview="${CSS.escape(key)}"]`);if(box&&row){const sp=moveEffectSpellOptions(s,row).find(x=>Number(x.id)===Number(sel.value));box.innerHTML=spellPreviewHtml(sp)}}));
  $$('[data-effect-source]').forEach(sel=>sel.addEventListener('change',()=>{const key=sel.dataset.effectSource,row=byKey.get(key),moveSel=$(`[data-effect-move="${CSS.escape(key)}"]`),box=$(`[data-effect-preview="${CSS.escape(key)}"]`);if(!row||!moveSel)return;const opts=classMoveChoicesAt(sel.value,Number(s.level)||1);moveSel.innerHTML=`<option value="">${esc('행동 선택…')}</option>`+opts.map(x=>`<option value="${attr(x.name)}">${recordEsc(x.name,classIsBuiltin(sel.value))}</option>`).join('');if(box)box.innerHTML=movePreviewHtml(null,sel.value)}));
  $$('[data-effect-move]').forEach(sel=>sel.addEventListener('change',()=>{const key=sel.dataset.effectMove,row=byKey.get(key),source=$(`[data-effect-source="${CSS.escape(key)}"]`)?.value||String(row?.effect?.source_class||''),box=$(`[data-effect-preview="${CSS.escape(key)}"]`);if(box)box.innerHTML=movePreviewHtml(classMoveChoicesAt(source,Number(s.level)||1).find(x=>x.name===sel.value),source)}));
  $$('[data-save-move-effect]').forEach(btn=>btn.addEventListener('click',async()=>{const key=btn.dataset.saveMoveEffect,row=byKey.get(key);if(!row)return;const acquired=Math.max(1,Number(moveChoice(s,key).acquired_at_level)||Number(s.level)||1);if(row.effect.kind==='spell_level_reduce'||row.effect.kind==='spell_grant'){const id=Number($(`[data-effect-spell="${CSS.escape(key)}"]`)?.value)||0;if(!id)return toast('주문을 먼저 선택하세요.');await saveChoice(key,{spell_id:id,acquired_at_level:acquired});return}const source=$(`[data-effect-source="${CSS.escape(key)}"]`)?.value||String(row.effect.source_class||''),name=$(`[data-effect-move="${CSS.escape(key)}"]`)?.value||'';if(!source||!name)return toast('행동을 먼저 선택하세요.');await saveChoice(key,{source_class:source,move_name:name,acquired_at_level:acquired})}));
}
function attachExtraMoves(bundle,gmMode){
  const s=bundle.state,save=(arr,extraPatch={})=>{s.extra_moves=arr;Object.assign(s,extraPatch);return patchCharacter(bundle.id,{extra_moves:arr,...extraPatch},gmMode,true)};
  attachMoveEffectChoices(bundle,gmMode);
  $$('[data-multiclass-adv]').forEach(i=>i.addEventListener('change',async()=>{const label=i.dataset.multiclassAdv,set=new Set(s.advanced_moves||[]),arr=[...(s.extra_moves||[])];if(i.checked)set.add(label);else{const linked=arr.filter(x=>x.multiclass_tier===label);if(linked.length&&!confirmUi(`${translateUiText(label)}을 취소하면 연결된 다중직업 행동도 함께 취소됩니다. 계속할까요?`)){i.checked=true;return}set.delete(label);const remain=arr.filter(x=>x.multiclass_tier!==label);if(![MC_BEGINNER,MC_INTERMEDIATE].some(x=>set.has(x))){for(let n=remain.length-1;n>=0;n--)if(!remain[n].multiclass_tier)remain.splice(n,1)}try{await save(remain,{advanced_moves:[...set]})}catch{i.checked=true}return}s.advanced_moves=[...set];try{await patchCharacter(bundle.id,{advanced_moves:s.advanced_moves},gmMode,true)}catch{i.checked=false}}));
  const fill=()=>{const source=$('#extraSourceClass')?.value,box=$('#extraSourceChoices');if(!source||!box)return;box.innerHTML=multiclassChoiceCards(source,Number(s.level)||1)};$('#extraSourceClass')?.addEventListener('change',fill);
  $('#addExtraMove')?.addEventListener('click',()=>{const source=$('#extraSourceClass')?.value,name=$('input[name="extraSourceMove"]:checked')?.value;if(!source||!name)return;const opt=multiclassChoices(source,Number(s.level)||1).find(x=>x.name===name);if(!opt)return toast('선택할 수 없는 행동입니다.');const arr=[...(s.extra_moves||[])];if(arr.some(x=>x.source_class===source&&x.name===name))return toast('이미 선택한 다중직업 행동입니다.');const selected=[MC_BEGINNER,MC_INTERMEDIATE].filter(x=>(s.advanced_moves||[]).includes(x)),used=new Set(arr.map(x=>x.multiclass_tier).filter(Boolean)),tier=selected.find(x=>!used.has(x))||selected[Math.min(arr.length,Math.max(0,selected.length-1))];if(!tier)return toast('먼저 다중직업 고급 행동을 선택하세요.');arr.push({source_class:source,name,desc:opt.desc||'',source_type:'multiclass',source_name:tier,bundle:!!opt.bundle,min_level:opt.min_level,acquired_at_level:Number(s.level)||1,multiclass_tier:tier});save(arr)});
  $$('[data-extra-move-del]').forEach(b=>b.addEventListener('click',()=>{if(!confirmUi('이 다중직업 행동 선택을 취소할까요?'))return;const arr=[...(s.extra_moves||[])];arr.splice(Number(b.dataset.extraMoveDel),1);save(arr)}));
}

function renderGMSpells(){
  const real=Object.keys(APP.state.classes),classes=['__undefined__',...real];
  if(!APP.gmSpellClass||!classes.includes(APP.gmSpellClass))APP.gmSpellClass=(APP.state.spells.__undefined__||[]).length?'__undefined__':(real.find(x=>(APP.state.spells[x]||[]).length)||'__undefined__');
  const list=APP.state.spells[APP.gmSpellClass]||[];
  if(APP.gmSpellId==='__new__'){}
  else if(!APP.gmSpellId||!list.some(sp=>Number(sp.id)===Number(APP.gmSpellId)))APP.gmSpellId=list[0]?.id||'__new__';
  const isNew=APP.gmSpellId==='__new__',sp=isNew?{name:'',level:'1',desc:'',_builtin:false}:(list.find(x=>Number(x.id)===Number(APP.gmSpellId))||{name:'',level:'1',desc:'',_builtin:false}),builtin=spellIsBuiltin(sp);
  return `<div class="split classified-editor spell-admin-layout"><aside class="side-list classified-side spell-side"><label class="field compact-field"><span>주문 분류</span><select id="spellClass" class="select"><option value="__undefined__" ${APP.gmSpellClass==='__undefined__'?'selected':''}>미분류</option>${real.map(x=>`<option value="${attr(x)}" ${x===APP.gmSpellClass?'selected':''}>${recordEsc(x,classIsBuiltin(x))}</option>`).join('')}</select></label><button id="addSpell" type="button">＋ 새 주문</button>${list.map(x=>{const b=spellIsBuiltin(x);return `<button data-spell-select="${x.id}" class="classified-list-item ${!isNew&&Number(x.id)===Number(APP.gmSpellId)?'active':''}${b?'':' no-i18n'}" type="button"><span class="classified-item-name">${recordEsc(x.name,b)}</span><span class="classified-item-meta">${recordEsc(spellLevelLabel(x.level),b)}</span></button>`}).join('')||'<div class="side-empty small">등록된 주문이 없습니다.</div>'}</aside><section class="panel gm-editor"><div class="head sticky-edit-head"><span class="${builtin?'':'no-i18n'}">${isNew?'새 주문':`${recordEsc(sp.name,builtin)} · ${recordEsc(spellLevelLabel(sp.level),builtin)}`}</span><div class="inline-actions"><button id="saveSpell" class="btn small" type="button">저장</button>${isNew?'':'<button id="deleteSpell" class="btn small danger" type="button">삭제</button>'}</div></div><div class="body">${APP.gmSpellClass==='__undefined__'?'<div class="notice">종족 효과, 고급 행동, GM 특전처럼 특정 직업 기본 목록에 속하지 않는 주문을 정의합니다. 이 주문은 GM이 플레이어에게 직접 지급할 수 있습니다.</div>':''}<div class="grid two spell-editor-main"><label class="field"><span>주문 이름</span><input id="spellName" class="input" ${builtin?'':'data-i18n-value="raw"'} value="${attr(contentValue(sp.name||'',builtin))}" placeholder="주문 이름"></label><label class="field spell-level-field"><span>레벨 / 분류</span><input id="spellLevel" class="input" ${builtin?'':'data-i18n-value="raw"'} inputmode="text" maxlength="24" value="${attr(contentValue(sp.level??'1',builtin))}" placeholder="예: 1~10, 암송"><small>숫자 1~10 = 해당 레벨 · 문자는 0레벨 분류</small></label></div><label class="field"><span>주문 설명</span><textarea id="spellDesc" class="textarea smart-textarea ${builtin?'':'no-i18n'}" data-max-grow="420">${recordEsc(sp.desc||'',builtin)}</textarea></label></div></section></div>`;
}
function zeroLevelSpellLabel(className){
  const profile=spellcastingProfile(className),configured=String(profile.zero_level_label||'').trim();
  if(configured)return configured;
  const raw=(APP.state.spells?.[className]||[]).map(x=>String(x.level??'').trim()).find(x=>x&&!spellLevelInfo(x).numeric);
  return raw||'0레벨';
}
function raceCrossClassAccess(race,className){
  const rows=(race?.spell_effects?.[className]||[]).filter(x=>x&&x.kind==='cross_class_access');
  const rule=rows[0];return rule&&rule.source_class?{enabled:true,source_class:String(rule.source_class),count:Math.max(1,Number(rule.count)||1)}:{enabled:false,source_class:'',count:1};
}
function raceSpellContext(state){
  const race=APP.state.races?.[state.race_name]||{},effects=(race.spell_effects?.[state.class_name]||[]).filter(Boolean),base=(APP.state.spells?.[state.class_name]||[]).map(x=>({...x})),special=[];
  for(const e of effects){
    const sid=Number(e.spell_id)||0;if(!sid)continue;
    if(e.kind==='level_reduce'){
      const sp=base.find(x=>Number(x.id)===sid);if(!sp)continue;const n=spellEffectiveLevel(sp.level);if(n<=0)continue;const next=Math.max(0,n-Math.max(1,Number(e.amount)||1));sp.original_level=sp.level;sp.level=next<=0?zeroLevelSpellLabel(state.class_name):next;sp.race_modified=true;
    }else if(e.kind==='grant_unclassified'){
      const sp=(APP.state.spells?.__undefined__||[]).find(x=>Number(x.id)===sid);if(sp&&!special.some(x=>Number(x.id)===sid))special.push({...sp,race_auto:true});
    }
  }
  return {all:base,special};
}
function moveSpellContext(state,baseSpells){
  const all=(baseSpells||[]).map(x=>({...x}));
  for(const row of activeMoveEffects(state)){
    const e=row.effect||{},choice=moveChoice(state,row.key);
    if(e.kind==='spell_level_reduce'&&choice.spell_id){const sp=all.find(x=>Number(x.id)===Number(choice.spell_id));if(!sp)continue;const n=spellEffectiveLevel(sp.level);if(n<=0)continue;const amount=Math.max(1,Number(e.amount)||1),next=Math.max(0,n-amount);sp.original_level=sp.original_level??sp.level;sp.level=next<=0?zeroLevelSpellLabel(state.class_name):next;sp.move_modified_sources=[...(sp.move_modified_sources||[]),row.move.name]}
    if(e.kind==='spell_zero'){const sp=all.find(x=>String(x.name)===String(e.spell_name||''));if(!sp)continue;sp.original_level=sp.original_level??sp.level;sp.level=zeroLevelSpellLabel(state.class_name);sp.move_modified_sources=[...(sp.move_modified_sources||[]),row.move.name]}
  }
  return all;
}
function moveGrantedSpells(state){
  const out=[];
  for(const row of activeMoveEffects(state)){const e=row.effect||{},choice=moveChoice(state,row.key);if(e.kind!=='spell_grant'||!choice.spell_id)continue;const sp=spellById(choice.spell_id);if(!sp)continue;out.push({...sp,added_source:row.move.name,added_source_class:sp.source_class,added_source_builtin:classIsBuiltin(row.source_class),auto_book:true})}
  return out;
}
function classAccessSpellGroups(state){
  const out=[];
  for(const row of activeMoveEffects(state)){const e=row.effect||{};if(e.kind!=='class_access'||!e.source_class)continue;const choice=moveChoice(state,row.key),acquired=Math.max(1,Number(choice.acquired_at_level)||Number(state.level)||1),effective=Math.max(1,(Number(state.level)||1)-acquired+1),spells=(APP.state.spells?.[e.source_class]||[]).map(sp=>({...sp,added_source:row.move.name,added_source_class:e.source_class,class_access:true})),profile=spellcastingProfile(e.source_class);out.push({key:row.key,source_class:e.source_class,source_name:row.move.name,source_move_class:row.source_class,acquired_at_level:acquired,effective_level:effective,spells,profile})}
  return out;
}
function primarySpellPool(state){
  const raceCtx=raceSpellContext(state),base=moveSpellContext(state,raceCtx.all),granted=moveGrantedSpells(state),extra=(state.extra_spells||[]).map(x=>({...x}));return [...base,...granted,...raceCtx.special,...extra];
}

function renderSpellPage(bundle,gmMode){
  const s=bundle.state,profile=spellcastingProfile(s.class_name),raceCtx=raceSpellContext(s),base=moveSpellContext(s,raceCtx.all),raceAuto=raceCtx.special,granted=moveGrantedSpells(s),book=new Set(s.spellbook||[]),prep=new Set(s.prepared_spells||[]),lv=Number(s.level)||1,extraAll=s.extra_spells||[],gmExtra=extraAll.filter(x=>x.kind==='gm'),raceExtra=extraAll.map((x,rawIndex)=>({x,rawIndex})).filter(o=>o.x.kind!=='gm'),classAccess=classAccessSpellGroups(s);
  const classBuiltin=classIsBuiltin(s.class_name),raceBuiltin=raceIsBuiltin(s.race_name);
  const raceRule=APP.state.races?.[s.race_name]||{},accessRule=raceCrossClassAccess(raceRule,s.class_name),extraSource=accessRule.enabled&&accessRule.source_class?accessRule.source_class:null,extraLimit=Math.max(1,Number(accessRule.count)||1),extraOptions=extraSource?(APP.state.spells[extraSource]||[]):[];
  const enrichExtra=x=>{const source=String(x.source||''),match=(APP.state.spells?.[source]||[]).find(sp=>Number(x.spell_id)&&Number(sp.id)===Number(x.spell_id))||(APP.state.spells?.[source]||[]).find(sp=>sp.name===x.name);return match?{...match,...x,desc:x.desc||match.desc,level:x.level??match.level}:{...x}};
  const raceExtraCards=raceExtra.map(o=>({...o,x:enrichExtra(o.x)})),raceGranted=raceExtraCards.map(o=>({...o.x,added_source:o.x.source_name||s.race_name,added_source_class:o.x.source||extraSource||'',added_source_builtin:raceIsBuiltin(s.race_name),auto_book:true,extra_raw_index:o.rawIndex})),all=[...base,...granted,...raceGranted];
  const isZero=sp=>spellEffectiveLevel(sp.level)===0,cantrips=all.filter(isZero),numeric=all.filter(x=>!isZero(x)),groups={};numeric.forEach(x=>(groups[String(spellEffectiveLevel(x.level))]||(groups[String(spellEffectiveLevel(x.level))]=[])).push(x));
  const primaryVisible=[...all,...raceAuto,...gmExtra.map(enrichExtra)],prepLimit=spellPrepLimit(profile,lv),prepUsage=spellPrepUsage(profile,[...prep],primaryVisible),baseLearnable=numeric.filter(x=>!x.added_source),knownCount=baseLearnable.filter(x=>book.has(x.name)).length,knownCap=spellKnownCap(profile,lv),startLevel=Math.max(0,Number(profile.starting_choice_level)||0),startNeed=Math.max(0,Number(profile.starting_choice_count)||0),startChoices=baseLearnable.filter(x=>spellEffectiveLevel(x.level)===startLevel),startCount=startChoices.filter(x=>book.has(x.name)).length,startSelect=profile.enabled&&profile.known_mode==='selected'&&startLevel>0&&startNeed>0&&!s.starting_spells_complete;
  const prepNotice=()=>{if(!profile.enabled)return `<div class="notice">${esc('이 직업의 기본 주문 운용 규칙은 꺼져 있습니다. 행동/종족/GM으로 추가된 주문만 표시될 수 있습니다.')}</div>`;if(profile.prepare_mode==='none')return `<div class="notice">${esc('이 직업은 준비 단계를 사용하지 않습니다. 사용할 수 있는 주문은 항상 사용 가능으로 취급합니다.')}</div>`;if(profile.limit_mode==='none')return `<div class="notice">${esc('준비 주문에 시스템 한도를 적용하지 않습니다.')}</div>`;const label=profile.limit_mode==='level_sum'?`${esc('준비 주문 레벨 합')} ${prepUsage}/${prepLimit}`:`${esc('준비 주문 개수')} ${prepUsage}/${prepLimit}`;return `<div class="notice ${prepUsage>prepLimit?'bad':''}">${label}${profile.zero_limit_exempt?` · ${recordEsc(zeroLevelSpellLabel(s.class_name),classBuiltin)} ${esc('제외')}`:''}</div>`};
  const spellCard=(sp,isZeroCard=false)=>{const forcedBook=!!sp.auto_book,autoKnown=isZeroCard&&profile.zero_auto_known,inBook=profile.known_mode==='all'||forcedBook||autoKnown||book.has(sp.name),autoPrepared=(isZeroCard&&profile.zero_auto_prepared)||profile.prepare_mode==='none',prepared=autoPrepared||prep.has(sp.name),num=spellEffectiveLevel(sp.level),levelAllowed=num<=lv,modified=(sp.move_modified_sources||[]),open=!!sp.added_source||modified.length>0||!!sp.race_modified,knownLocked=profile.known_mode==='all'||forcedBook||autoKnown||(!levelAllowed&&!gmMode),canPrep=profile.prepare_mode==='none'?false:(profile.prepare_mode==='known'?inBook:true),prepLocked=autoPrepared||(!canPrep&&!gmMode)||(!levelAllowed&&!gmMode),badges=[sp.added_source?`<span class="pill added-pill">${esc('추가됨')} · ${recordEsc(sp.added_source,sp.added_source_builtin!==undefined?!!sp.added_source_builtin:classBuiltin)}${sp.added_source_class?` · ${recordEsc(sp.added_source_class,classIsBuiltin(sp.added_source_class))}`:''}</span>`:'',...modified.map(x=>`<span class="pill added-pill">${esc('변경됨')} · ${recordEsc(x,classBuiltin)}</span>`),sp.race_modified?`<span class="pill">${esc('종족 효과')}</span>`:''].join('');
    const knownControl=profile.enabled&&profile.known_mode!=='all'?`<label><input type="checkbox" data-spellbook="${attr(sp.name)}" ${inBook?'checked':''} ${knownLocked?'disabled':''}> ${recordEsc(profile.known_label||'습득',classBuiltin)}</label>`:(profile.enabled?`<span class="pill">${recordEsc(profile.known_label||'습득',classBuiltin)} · ${esc('자동')}</span>`:'');
    const prepControl=profile.enabled?(profile.prepare_mode==='none'?`<span class="pill">${esc('항상 사용')}</span>`:`<label><input type="checkbox" data-prepared="${attr(sp.name)}" ${prepared?'checked':''} ${prepLocked?'disabled':''}> ${recordEsc(profile.prepare_label||'준비',classBuiltin)}</label>`):'';
    return `<article class="spell-card ${sp.added_source?'added-spell-card':''}"><div class="spell-title"><div class="spell-name ${spellIsBuiltin(sp)?'':'no-i18n'}">${recordEsc(sp.name,spellIsBuiltin(sp))}</div><span class="pill spell-level-pill">${recordEsc(spellLevelLabel(sp.level),spellIsBuiltin(sp))}</span>${badges}</div><div class="spell-controls">${knownControl}${prepControl}</div><details class="move-details" ${open?'open':''}><summary>${esc('설명 보기')}</summary><div class="move-desc ${spellIsBuiltin(sp)?'':'no-i18n'}">${recordEsc(sp.desc||'설명 없음',spellIsBuiltin(sp))}</div></details>${sp.original_level!==undefined?`<div class="small muted">${recordEsc(spellLevelLabel(sp.original_level),spellIsBuiltin(sp))} → ${recordEsc(spellLevelLabel(sp.level),spellIsBuiltin(sp))}</div>`:''}${Number.isInteger(sp.extra_raw_index)?`<button class="btn small danger added-spell-remove" data-extra-del="${sp.extra_raw_index}" type="button">${esc('추가 취소')}</button>`:''}${!levelAllowed?`<div class="small muted">${esc('현재 레벨보다 높은 주문입니다.')}</div>`:''}</article>`;
  };
  const specialCard=(sp,label='GM 지급',source='')=>{const full=enrichExtra(sp),b=spellIsBuiltin(full),sourceBuiltin=source==='GM'?true:(raceIsBuiltin(source)||classIsBuiltin(source)),zero=isZero(full),always=(zero&&profile.zero_auto_prepared)||profile.prepare_mode==='none',prepared=always||prep.has(full.name),canPrep=profile.prepare_mode!=='none';return `<article class="spell-card special-spell-card added-spell-card${b?'':' no-i18n'}"><div class="spell-title"><div class="spell-name">${recordEsc(full.name,b)}</div><span class="pill spell-level-pill">${recordEsc(spellLevelLabel(full.level),b)}</span><span class="pill added-pill">${esc('추가됨')} · ${esc(label)}${source?` · ${source==='GM'?rawEsc(source):recordEsc(source,sourceBuiltin)}`:''}</span></div><div class="spell-controls">${canPrep?`<label><input type="checkbox" data-prepared="${attr(full.name)}" ${prepared?'checked':''} ${always?'disabled':''}> ${recordEsc(profile.prepare_label||'준비',classBuiltin)}</label>`:`<span class="pill">${esc('항상 사용')}</span>`}</div><details class="move-details" open><summary>${esc('설명 보기')}</summary><div class="move-desc">${recordEsc(full.desc||'설명 없음',b)}</div></details></article>`};
  const classAccessHtml=classAccess.map(a=>{
    const ap=a.profile,track=spellTrackState(s,a.key),known=new Set(track.known),preparedSet=new Set(track.prepared),available=a.spells.filter(sp=>spellEffectiveLevel(sp.level)===0||spellEffectiveLevel(sp.level)<=a.effective_level),learnable=available.filter(sp=>spellEffectiveLevel(sp.level)>0),cap=spellKnownCap(ap,a.effective_level),knownUsed=learnable.filter(sp=>known.has(sp.name)).length,limit=spellPrepLimit(ap,a.effective_level),usage=spellPrepUsage(ap,[...preparedSet],available),startLv=Math.max(0,Number(ap.starting_choice_level)||0),startN=Math.max(0,Number(ap.starting_choice_count)||0),startOpts=learnable.filter(sp=>spellEffectiveLevel(sp.level)===startLv),startUsed=startOpts.filter(sp=>known.has(sp.name)).length,startPending=ap.known_mode==='selected'&&startLv>0&&startN>0&&!track.starting_complete,byLevel={};
    for(const sp of available){const key=String(spellEffectiveLevel(sp.level));(byLevel[key]||(byLevel[key]=[])).push(sp)}
    const sourceClassBuiltin=classIsBuiltin(a.source_class),sourceMoveBuiltin=classIsBuiltin(a.source_move_class),card=sp=>{const zero=isZero(sp),autoKnown=ap.known_mode==='all'||(zero&&ap.zero_auto_known),inKnown=autoKnown||known.has(sp.name),autoPrep=ap.prepare_mode==='none'||(zero&&ap.zero_auto_prepared),isPrepared=autoPrep||preparedSet.has(sp.name),knownLocked=autoKnown,canPrep=ap.prepare_mode==='none'?false:(ap.prepare_mode==='known'?inKnown:true),prepLocked=autoPrep||!canPrep,knownCtl=ap.known_mode==='all'?`<span class="pill">${recordEsc(ap.known_label||'습득',sourceClassBuiltin)} · ${esc('자동')}</span>`:`<label><input type="checkbox" data-track-known="${attr(a.key)}" data-track-spell="${attr(sp.name)}" ${inKnown?'checked':''} ${knownLocked?'disabled':''}> ${recordEsc(ap.known_label||'습득',sourceClassBuiltin)}</label>`,prepCtl=ap.prepare_mode==='none'?`<span class="pill">${esc('항상 사용')}</span>`:`<label><input type="checkbox" data-track-prepared="${attr(a.key)}" data-track-spell="${attr(sp.name)}" ${isPrepared?'checked':''} ${prepLocked?'disabled':''}> ${recordEsc(ap.prepare_label||'준비',sourceClassBuiltin)}</label>`;return `<article class="spell-card added-spell-card"><div class="spell-title"><div class="spell-name ${spellIsBuiltin(sp)?'':'no-i18n'}">${recordEsc(sp.name,spellIsBuiltin(sp))}</div><span class="pill spell-level-pill">${recordEsc(spellLevelLabel(sp.level),spellIsBuiltin(sp))}</span><span class="pill added-pill">${esc('추가됨')} · ${esc('타직업 획득')} · ${recordEsc(a.source_class,sourceClassBuiltin)} · ${recordEsc(a.source_name,sourceMoveBuiltin)}</span></div><div class="spell-controls">${knownCtl}${prepCtl}</div><details class="move-details" open><summary>${esc('설명 보기')}</summary><div class="move-desc ${spellIsBuiltin(sp)?'':'no-i18n'}">${recordEsc(sp.desc||'설명 없음',spellIsBuiltin(sp))}</div></details></article>`};
    const levels=Object.keys(byLevel).sort((x,y)=>Number(x)-Number(y)).map(k=>`<div class="added-class-level"><h4>${k==='0'?recordEsc(zeroLevelSpellLabel(a.source_class),sourceClassBuiltin):esc(spellLevelLabel(k))} ${esc('주문')}</h4><div class="spell-grid">${byLevel[k].map(card).join('')}</div></div>`).join('');
    const prepText=ap.prepare_mode==='none'?esc('준비 없음 · 사용 가능한 주문은 항상 사용'):(ap.limit_mode==='none'?esc('준비 한도 없음'):(ap.limit_mode==='level_sum'?`${esc('준비 주문 레벨 합')} ${usage}/${limit}`:`${esc('준비 주문 개수')} ${usage}/${limit}`)),learnText=ap.known_mode==='selected'&&Number.isFinite(cap)?` · ${esc('습득')} ${knownUsed}/${cap}`:'';
    const accessSummary=APP.language==='en'?`${contentValue(a.source_name,sourceMoveBuiltin)} · Gained at Lv.${a.acquired_at_level} · ${contentValue(a.source_class,sourceClassBuiltin)} effective level ${a.effective_level}`:`${recordEsc(a.source_name,sourceMoveBuiltin)} · 획득 레벨 ${a.acquired_at_level} · ${recordEsc(a.source_class,sourceClassBuiltin)} 기준 레벨 ${a.effective_level}`;
    const startPanel=startPending?`<div class="panel wizard-start-spells"><div class="head">${recordEsc(a.source_class,sourceClassBuiltin)} · ${esc('시작 주문 선택')} <span>${startUsed}/${startN}</span></div><div class="body"><div class="notice">${esc(`${startLv}레벨 주문 중 ${startN}개를 선택하세요. 이 규칙은 출처 직업의 주문 운용 설정에서 왔습니다.`)}</div><div class="spell-grid">${startOpts.map(card).join('')}</div><button class="btn dark" data-finish-track-start="${attr(a.key)}" type="button" ${startUsed===startN?'':'disabled'}>${esc('시작 주문 확정')}</button></div></div>`:'';
    return `<section class="spell-section added-class-spells" data-spell-track-section="${attr(a.key)}"><h3>${esc('타직업 획득')} · ${recordEsc(a.source_class,sourceClassBuiltin)} · ${recordEsc(a.source_name,sourceMoveBuiltin)}</h3><div class="notice ${usage>limit?'bad':''}">${accessSummary} · ${prepText}${learnText}</div>${startPanel}${levels}</section>`;
  }).join('');
  const canAddExtra=raceExtra.length<extraLimit;
  const startPanel=startSelect?`<section class="panel wizard-start-spells"><div class="head">${esc('시작 주문 선택')} <span>${startCount}/${startNeed}</span></div><div class="body"><div class="notice">${htmlEscape(`${contentValue(zeroLevelSpellLabel(s.class_name),classBuiltin)} 주문은 설정에 따라 자동 처리됩니다. ${startLevel}레벨 주문 중 정확히 ${startNeed}개를 선택하세요.`)}</div><div class="spell-grid">${startChoices.map(x=>spellCard(x,false)).join('')}</div><button id="finishStartingSpells" class="btn dark" type="button" ${startCount===startNeed?'':'disabled'}>${esc('시작 주문 확정')}</button></div></section>`:'';
  const learnNotice=profile.enabled&&profile.known_mode==='selected'&&Number.isFinite(knownCap)?`<div class="notice ${knownCount>knownCap?'bad':''}">${recordEsc(profile.known_label||'습득',classBuiltin)} ${knownCount}/${knownCap} · ${esc('현재 레벨에서 습득 가능한 기본 주문 수')}</div>`:'';
  return `${startPanel}${learnNotice}${prepNotice()}${cantrips.length?`<section class="spell-section"><h3>${recordEsc(zeroLevelSpellLabel(s.class_name),classBuiltin)} ${esc('주문')}</h3><div class="spell-grid">${cantrips.map(x=>spellCard(x,true)).join('')}</div></section>`:''}${raceAuto.length?`<section class="spell-section"><h3>${esc('종족 자동 습득 주문')} · ${recordEsc(s.race_name,raceBuiltin)}</h3><div class="spell-grid">${raceAuto.map(x=>specialCard(x,'종족 특전',s.race_name)).join('')}</div></section>`:''}${gmExtra.length?`<section class="spell-section"><h3>${esc('GM 지급 특수 주문')}</h3><div class="spell-grid">${gmExtra.map(x=>specialCard(x,'GM 지급','GM')).join('')}</div></section>`:''}${extraSource?`<section class="spell-section"><h3>${esc('종족 특전 주문')} · ${recordEsc(s.race_name,raceBuiltin)}</h3><div class="panel"><div class="body"><div class="notice">${recordEsc(extraSource,classIsBuiltin(extraSource))} ${esc('주문 하나를')} ${recordEsc(s.class_name,classBuiltin)} ${esc('주문처럼 사용합니다. 최대')} ${extraLimit}${esc('개입니다.')}</div><div class="compact-action-row"><select id="extraSpellSelect" class="select" ${!canAddExtra?'disabled':''}><option value="">${recordEsc(extraSource,classIsBuiltin(extraSource))} ${esc('주문 선택…')}</option>${extraOptions.map(x=>`<option value="${attr(x.name)}">${recordEsc(x.name,spellIsBuiltin(x))} · ${recordEsc(spellLevelLabel(x.level),spellIsBuiltin(x))}</option>`).join('')}</select><button id="addExtraSpell" class="btn" type="button" ${!canAddExtra?'disabled':''}>${canAddExtra?esc('종족 특전 주문 등록'):`${extraLimit}${esc('개 등록됨')}`}</button></div><div id="extraSpellPreview">${spellPreviewHtml(null)}</div>${raceExtraCards.length?`<div class="small muted">${esc('추가한 주문은 위의 주문 레벨 목록에 배치되며 출처가 함께 표시됩니다.')}</div>`:''}</div></div></section>`:''}${Object.keys(groups).sort((a,b)=>Number(a)-Number(b)).map(k=>`<section class="spell-section"><h3>${esc(spellLevelLabel(k))} ${esc('주문')}</h3><div class="spell-grid">${groups[k].map(x=>spellCard(x,false)).join('')}</div></section>`).join('')}${classAccessHtml}`;
}

function renderGMPlayers(){
  const special=APP.state.spells?.__undefined__||[],chars=APP.state.characters||[];
  return `<section class="panel"><div class="head">플레이어 / 캐릭터 관리</div><div class="body"><div class="grid two">${APP.state.party.map(p=>{const full=chars.find(x=>Number(x.character_id)===Number(p.character_id))?.state||{},grants=(full.extra_spells||[]).filter(x=>x.kind==='gm'),available=special.filter(sp=>!grants.some(g=>Number(g.spell_id)===Number(sp.id)));return `<article class="player-admin-card" style="--player-color:${attr(p.color||'#1d5f91')}"><div class="row-head"><div style="flex:1"><b class="player-presence ${p.online?'online':'offline'}"><i></i><span style="color:${attr(p.color||'#1d5f91')}">${rawEsc(p.character_name||p.display_name)}</span></b><div class="small muted">${p.online?'온라인':'오프라인'} · ${rawEsc(p.display_name)} · ${recordEsc(p.class_name,classIsBuiltin(p.class_name))} · ${recordEsc(p.race_name,raceIsBuiltin(p.race_name))}</div></div><button class="btn small dark" data-edit-char="${p.character_id}" type="button">전체 시트</button></div><div class="party-extension-tags">${(p.extensions||[]).map(x=>{const th=x.data?.theme||{};return `<span class="party-ext-tag ${x.data?.hidden?'hidden':''}" style="--ext-bg:${attr(th.background||'#fff')};--ext-text:${attr(th.text||'#111')};--ext-accent:${attr(th.accent||'#111')}">${recordEsc(x.name,!!x.data?.builtin)}</span>`}).join('')}</div><div class="quick-grid"><label>HP<input class="input" data-q="hp_current" data-cid="${p.character_id}" type="number" value="${p.hp_current}"></label><label>장갑<input class="input" data-q="armor" data-cid="${p.character_id}" type="number" value="${p.armor}"></label><label>레벨<input class="input" data-q="level" data-cid="${p.character_id}" type="number" value="${p.level}"></label><label>XP<input class="input" data-q="xp" data-cid="${p.character_id}" type="number" value="${p.xp}"></label></div><div class="special-spell-admin"><b>특수 주문 직접 지급</b><div class="compact-action-row"><select class="select" data-special-spell-select="${p.character_id}"><option value="">미분류 주문 선택…</option>${available.map(sp=>`<option value="${sp.id}">${recordEsc(sp.name,spellIsBuiltin(sp))} · ${recordEsc(spellLevelLabel(sp.level),spellIsBuiltin(sp))}</option>`).join('')}</select><button class="btn small" data-special-spell-grant="${p.character_id}" type="button" ${available.length?'':'disabled'}>지급</button></div><div data-special-spell-preview="${p.character_id}">${spellPreviewHtml(null)}</div>${grants.map(g=>{const sp=special.find(x=>Number(x.id)===Number(g.spell_id)),b=sp?spellIsBuiltin(sp):false;return `<div class="granted-special-row${b?'':' no-i18n'}"><span><b>${recordEsc(g.name,b)}</b> · ${recordEsc(spellLevelLabel(g.level),b)}</span><button class="btn small danger" data-special-spell-revoke="${p.character_id}" data-spell-id="${Number(g.spell_id)||0}" type="button">회수</button></div>`}).join('')||'<div class="small muted">GM이 직접 지급한 특수 주문이 없습니다.</div>'}</div></article>`}).join('')||'<div class="notice">아직 참가한 플레이어가 없습니다.</div>'}</div></div></section>`;
}
function attachGMPlayers(){
  const special=APP.state.spells?.__undefined__||[];
  $$('[data-edit-char]').forEach(b=>b.addEventListener('click',()=>{APP.gmSelectedChar=Number(b.dataset.editChar);APP.playerTab='character';renderGM()}));$$('[data-q]').forEach(i=>i.addEventListener('change',()=>patchCharacter(Number(i.dataset.cid),{[i.dataset.q]:Number(i.value)||0},true,true)));
  $$('[data-special-spell-select]').forEach(sel=>sel.addEventListener('change',()=>{const cid=Number(sel.dataset.specialSpellSelect),sp=special.find(x=>Number(x.id)===Number(sel.value)),box=$(`[data-special-spell-preview="${cid}"]`);if(box)box.innerHTML=spellPreviewHtml(sp?{...sp,source_class:'미분류'}:null)}));
  $$('[data-special-spell-grant]').forEach(b=>b.addEventListener('click',async()=>{const cid=Number(b.dataset.specialSpellGrant),sel=$(`[data-special-spell-select="${cid}"]`),spell_id=Number(sel?.value)||0;if(!spell_id)return toast('지급할 특수 주문을 선택하세요.');try{await api(`/api/rooms/${APP.creds.room}/characters/${cid}/special-spells`,{method:'POST',body:JSON.stringify({spell_id})});await refreshState(true);toast('특수 주문을 지급했습니다.')}catch(e){toast(e.message,3500)}}));
  $$('[data-special-spell-revoke]').forEach(b=>b.addEventListener('click',async()=>{if(!confirmUi('이 특수 주문을 회수할까요?'))return;try{await api(`/api/rooms/${APP.creds.room}/characters/${b.dataset.specialSpellRevoke}/special-spells/${b.dataset.spellId}`,{method:'DELETE'});await refreshState(true)}catch(e){toast(e.message,3500)}}));
}

function workspaceToolbar(tabs,layout){const controls=tabs.map(t=>{const th=t.theme||{},on=layout.mode==='single'?layout.active===t.id:layout.windows[t.id]?.open,style=t.id.startsWith('ext:')?`style="--win-accent:${attr(th.accent||'#181818')}"`:'';return `<button class="workspace-open ${on?'active':''}" ${style} data-open-window="${attr(t.id)}" type="button">${t.id.startsWith('ext:')?recordEsc(t.label,!!t.builtin):esc(t.label)}</button>`}).join('');const locked=layout.mode==='multi'&&layout.locked;return `<div class="workspace-toolbar"><div class="workspace-tools-left"><b>화면</b>${controls}</div><div class="workspace-tools-right"><button class="btn ${layout.mode==='single'?'dark':''}" data-workspace-mode="single" type="button">기본 화면</button><button class="btn ${layout.mode==='multi'?'dark':''}" data-workspace-mode="multi" type="button">다중 창</button>${layout.mode==='multi'?`<button class="btn small" data-layout-preset="default" type="button" ${locked?'disabled':''}>기본 배치</button><button class="btn small" data-layout-preset="combat" type="button" ${locked?'disabled':''}>전투</button><button class="btn small" data-layout-preset="explore" type="button" ${locked?'disabled':''}>탐험</button><button class="btn small ${layout.locked?'dark':''}" id="layoutLock" type="button">${layout.locked?'🔒 배치 고정됨':'🔓 배치 고정'}</button><button class="btn small" id="layoutSave" type="button">배치 저장</button>`:''}</div></div>`}
function renderWorkspace(bundle,gmMode){const tabs=playerTabsFor(bundle),layout=getWorkspace(bundle,gmMode);normalizeWorkspaceZ(layout);if(layout.mode==='single')return `<section class="workspace-wrap ${gmMode?'':'player-single-workspace'}">${workspaceToolbar(tabs,layout)}<div class="single-workspace-panel">${renderPlayerPageById(bundle,gmMode,layout.active)}</div></section>`;const wins=tabs.filter(t=>layout.windows[t.id]?.open).map(t=>{const w=layout.windows[t.id],th=t.theme||{},style=`left:${Math.max(0,w.x||0)}px;top:${Math.max(0,w.y||0)}px;width:${Math.max(360,w.w||620)}px;height:${Math.max(260,w.h||560)}px;z-index:${w.z||1};${t.id.startsWith('ext:')?`--win-accent:${attr(th.accent||'#181818')};`:''}`;return `<section class="dw-window ${layout.locked?'locked':''}" data-window-id="${attr(t.id)}" style="${style}"><header class="dw-window-bar" data-drag-handle><div class="dw-window-title"><span class="window-grip">▦</span>${t.id.startsWith('ext:')?recordEsc(t.label,!!t.builtin):esc(t.label)}</div><div class="window-actions"><button data-max-window="${attr(t.id)}" title="최대화/복원" type="button" ${layout.locked?'disabled':''}>□</button><button data-close-window="${attr(t.id)}" title="닫기" type="button">×</button></div></header><div class="dw-window-body">${renderPlayerPageById(bundle,gmMode,t.id)}</div>${layout.locked?'':'<i class="dw-resize-handle" data-resize-handle></i>'}</section>`}).join('');return `<section class="workspace-wrap">${workspaceToolbar(tabs,layout)}<div class="workspace-canvas ${layout.locked?'layout-locked':''}">${wins||'<div class="workspace-empty">위 버튼을 눌러 필요한 창을 여세요.</div>'}</div></section>`}
function attachWorkspace(bundle,gmMode){
  const layout=getWorkspace(bundle,gmMode),canvas=$('.workspace-canvas');
  document.body.classList.toggle('workspace-multi-active',layout.mode==='multi');
  if(layout.mode!=='multi')APP.workspaceResizeHandler=null;
  $$('[data-workspace-mode]').forEach(b=>b.addEventListener('click',e=>{
    e.preventDefault();e.stopPropagation();
    const next=b.dataset.workspaceMode==='multi'?'multi':'single';
    if(next===layout.mode)return;
    // Capture into the same live object. A failed geometry read must never block mode exit.
    if(canvas&&layout.mode==='multi'){try{captureWorkspaceGeometry(bundle,gmMode,layout)}catch{}}
    layout.mode=next;
    if(next==='multi'&&!Object.values(layout.windows||{}).some(w=>w?.open)){
      const id=layout.windows?.[layout.active]?layout.active:(layout.windows?.character?'character':Object.keys(layout.windows||{})[0]);if(id)layout.windows[id].open=true;
    }
    saveWorkspace(bundle,gmMode);
    document.body.classList.toggle('workspace-multi-active',next==='multi');
    if(next==='single')APP.workspaceResizeHandler=null;
    rerenderCharacterContext(gmMode);
  }));
  $$('[data-open-window]').forEach(b=>b.addEventListener('click',()=>{
    const id=b.dataset.openWindow;
    if(layout.mode==='single')layout.active=id;
    else{
      const w=layout.windows[id];if(!w)return;
      w.open=!w.open;
      if(w.open){normalizeWorkspaceZ(layout);w.z=10+Object.values(layout.windows).filter(x=>x?.open).length}
    }
    saveWorkspace(bundle,gmMode);rerenderCharacterContext(gmMode)
  }));
  if(layout.mode!=='multi'||!canvas)return;
  const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
  const syncWindowZ=()=>{$$('.dw-window',canvas).forEach(node=>{const item=layout.windows[node.dataset.windowId];if(item)node.style.zIndex=String(Number(item.z)||10)})};
  const bring=(w,el)=>{
    if(!w||!el)return;
    const max=Math.max(10,...Object.values(layout.windows).filter(x=>x?.open).map(x=>Number(x.z)||10));
    w.z=max+1;
    // Compact the stack after marking this window highest, then update every live DOM window.
    // Updating only the clicked element left stale equal z-index values and made the order look fixed.
    normalizeWorkspaceZ(layout);syncWindowZ();saveWorkspace(bundle,gmMode)
  };
  const clampAll=()=>{$$('.dw-window',canvas).forEach(el=>{const w=layout.windows[el.dataset.windowId];if(!w)return;const maxW=Math.max(360,canvas.clientWidth),maxH=Math.max(260,canvas.clientHeight);w.w=Math.min(el.offsetWidth,maxW);w.h=Math.min(el.offsetHeight,maxH);w.x=clamp(el.offsetLeft,0,Math.max(0,canvas.clientWidth-w.w));w.y=clamp(el.offsetTop,0,Math.max(0,canvas.clientHeight-w.h));Object.assign(el.style,{left:w.x+'px',top:w.y+'px',width:w.w+'px',height:w.h+'px'})})};
  requestAnimationFrame(clampAll);
  $$('.dw-window',canvas).forEach(el=>{const w=layout.windows[el.dataset.windowId];el.addEventListener('pointerdown',()=>bring(w,el),{capture:true})});
  $$('[data-close-window]').forEach(b=>b.addEventListener('click',e=>{e.stopPropagation();layout.windows[b.dataset.closeWindow].open=false;normalizeWorkspaceZ(layout);saveWorkspace(bundle,gmMode);rerenderCharacterContext(gmMode)}));
  $$('[data-layout-preset]').forEach(b=>b.addEventListener('click',()=>{if(layout.locked)return;const next=defaultWorkspace(playerTabsFor(bundle),b.dataset.layoutPreset);next.mode='multi';next.locked=false;APP.workspaceLayouts[workspaceKey(bundle,gmMode)]=next;saveWorkspace(bundle,gmMode);rerenderCharacterContext(gmMode)}));
  $('#layoutLock')?.addEventListener('click',()=>{if(!layout.locked)captureWorkspaceGeometry(bundle,gmMode,layout);layout.locked=!layout.locked;saveWorkspace(bundle,gmMode);rerenderCharacterContext(gmMode)});
  $('#layoutSave')?.addEventListener('click',()=>{captureWorkspaceGeometry(bundle,gmMode,layout);saveWorkspace(bundle,gmMode);toast('현재 창 배치를 저장했습니다.')});
  $$('[data-max-window]').forEach(b=>b.addEventListener('click',e=>{e.stopPropagation();if(layout.locked)return;const id=b.dataset.maxWindow,w=layout.windows[id];if(!w)return;if(!w.max){w.restore={x:w.x,y:w.y,w:w.w,h:w.h};Object.assign(w,{x:4,y:4,w:Math.max(360,canvas.clientWidth-8),h:Math.max(260,canvas.clientHeight-8),max:true})}else{Object.assign(w,w.restore||{x:20,y:20,w:620,h:560});w.max=false}saveWorkspace(bundle,gmMode);rerenderCharacterContext(gmMode)}));
  if(layout.locked){
    APP.workspaceResizeHandler=()=>{if(document.body.classList.contains('workspace-multi-active')&&document.body.contains(canvas)){clampAll();captureWorkspaceGeometry(bundle,gmMode,layout);saveWorkspace(bundle,gmMode)}};
    return
  }
  $$('.dw-window',canvas).forEach(el=>{
    const id=el.dataset.windowId,w=layout.windows[id],bar=$('[data-drag-handle]',el),handle=$('[data-resize-handle]',el);
    bar?.addEventListener('pointerdown',e=>{if(e.target.closest('button'))return;e.preventDefault();bring(w,el);const sx=e.clientX,sy=e.clientY,ox=el.offsetLeft,oy=el.offsetTop;bar.setPointerCapture(e.pointerId);const mv=ev=>{w.x=clamp(ox+ev.clientX-sx,0,Math.max(0,canvas.clientWidth-el.offsetWidth));w.y=clamp(oy+ev.clientY-sy,0,Math.max(0,canvas.clientHeight-el.offsetHeight));el.style.left=w.x+'px';el.style.top=w.y+'px'};const up=()=>{bar.removeEventListener('pointermove',mv);bar.removeEventListener('pointerup',up);captureWorkspaceGeometry(bundle,gmMode,layout);saveWorkspace(bundle,gmMode)};bar.addEventListener('pointermove',mv);bar.addEventListener('pointerup',up)});
    handle?.addEventListener('pointerdown',e=>{e.preventDefault();e.stopPropagation();bring(w,el);const sx=e.clientX,sy=e.clientY,ow=el.offsetWidth,oh=el.offsetHeight;handle.setPointerCapture(e.pointerId);const mv=ev=>{w.w=clamp(ow+ev.clientX-sx,360,Math.max(360,canvas.clientWidth-el.offsetLeft));w.h=clamp(oh+ev.clientY-sy,260,Math.max(260,canvas.clientHeight-el.offsetTop));el.style.width=w.w+'px';el.style.height=w.h+'px'};const up=()=>{handle.removeEventListener('pointermove',mv);handle.removeEventListener('pointerup',up);captureWorkspaceGeometry(bundle,gmMode,layout);saveWorkspace(bundle,gmMode)};handle.addEventListener('pointermove',mv);handle.addEventListener('pointerup',up)})
  });
  APP.workspaceResizeHandler=()=>{if(document.body.classList.contains('workspace-multi-active')&&document.body.contains(canvas)){clampAll();captureWorkspaceGeometry(bundle,gmMode,layout);saveWorkspace(bundle,gmMode)}};
}

function stopSoundDrawerTicker(){if(APP.soundDrawerTimer){clearInterval(APP.soundDrawerTimer);APP.soundDrawerTimer=null}}
function soundDuration(){
  const st=APP.state?.sound_state||{},snd=st.sound||soundById(st.sound_id);let n=0;
  const a=$('#dwBgmAudio');n=Number(a?.duration)||0;return Number.isFinite(n)&&n>0?n:0
}
function updateSoundProgress(){
  const root=$('#soundDrawer');if(!root)return;const st=APP.state?.sound_state||{},active=!!st.sound_id&&st.status!=='stopped',pos=active?currentBgmPosition():0,dur=active?soundDuration():0,cur=$('#soundNowCurrent',root),total=$('#soundNowTotal',root),seek=$('#bgmSeek',root);
  if(seek){seek.disabled=!active;const fallback=Math.max(14400,Math.ceil(pos)+300);seek.max=String(Math.max(1,dur||fallback));if(APP.soundSeeking){if(cur)cur.textContent=fmtClock(Number(seek.value)||0);if(total)total.textContent=dur?fmtClock(dur):'불러오는 중';return}seek.value=String(Math.min(pos,Number(seek.max)||1))}
  if(cur)cur.textContent=fmtClock(pos);if(total)total.textContent=active?(dur?fmtClock(dur):'불러오는 중'):'--:--'
}
function startSoundDrawerTicker(){stopSoundDrawerTicker();if($('#soundDrawer')){updateSoundProgress();APP.soundDrawerTimer=setInterval(updateSoundProgress,350)}}
function closeSoundDrawer(){stopSoundDrawerTicker();$('#soundDrawer')?.remove()}
function updateSoundDrawerState(state){
  const root=$('#soundDrawer');if(!root||!state)return;if(APP.state)APP.state.sound_state=state;const bg=$('#gmBgmVolume',root),fx=$('#gmSfxVolume',root),now=state.sound||soundById(state.sound_id),title=$('#soundNowTitle',root),pause=$('#pauseBgm',root),stop=$('#stopBgm',root),active=!!state.sound_id&&state.status!=='stopped';
  if(bg&&!bg.matches(':active'))bg.value=String(Number(state.bgm_volume??state.volume??1));if(fx&&!fx.matches(':active'))fx.value=String(Number(state.sfx_volume??1));if(title)title.textContent=active?(now?.name||'BGM 불러오는 중'):'재생 중인 BGM 없음';if(pause){pause.disabled=!active;pause.textContent=state.status==='paused'?'▶ 계속 재생':'⏸ 일시정지'}if(stop)stop.disabled=!active;
  $$('[data-play-bgm]',root).forEach(b=>b.closest('.sound-item')?.classList.toggle('active',Number(b.dataset.playBgm)===Number(state.sound_id)&&active));updateSoundProgress();startSoundDrawerTicker()
}
function renderSoundDrawer(){
  let root=$('#soundDrawer');if(!root){document.body.insertAdjacentHTML('beforeend','<aside id="soundDrawer" class="sound-drawer"></aside>');root=$('#soundDrawer')}APP.soundAddOpen=APP.soundAddOpen||{bgm:false,sfx:false};const gm=APP.state?.me?.role==='gm',prefs=soundPrefs(),sounds=(APP.state?.sounds||[]).filter(x=>x.source_type==='file'),bgm=sounds.filter(x=>x.kind==='bgm').sort((a,b)=>(a.sort_order||9999)-(b.sort_order||9999)),sfx=sounds.filter(x=>x.kind==='sfx').sort((a,b)=>(a.sort_order||9999)-(b.sort_order||9999)),cur=APP.state?.sound_state||{},active=!!cur.sound_id&&cur.status!=='stopped',now=active?(cur.sound||soundById(cur.sound_id)):null,mode=cur.mode||'next',pos=active?currentBgmPosition():0,dur=active?soundDuration():0,seekMax=Math.max(1,dur||14400);
  const soundRow=(x,kind)=>`<div class="sound-item ${kind==='bgm'&&active&&Number(cur.sound_id)===Number(x.id)?'active':''}" draggable="true" data-sound-sort-id="${x.id}" data-sound-sort-kind="${kind}"><div><b>${rawEsc(x.name)}</b><small>${kind==='bgm'?'파일':'효과음'}</small></div><div><button ${kind==='bgm'?`data-play-bgm="${x.id}"`:`data-play-sfx="${x.id}"`} type="button">재생</button><button data-del-sound="${x.id}" type="button">삭제</button></div></div>`;
  root.innerHTML=`<div class="sound-head"><div><b>사운드 보드</b><span>${gm?'GM 전체 재생 관리':'개인 음량 설정'}</span></div><button data-close-sound type="button">×</button></div><div class="sound-drawer-scroll"><div class="now-playing-panel"><div class="now-playing-line"><div><small>현재 재생</small><b id="soundNowTitle">${now?.name?rawEsc(now.name):esc('재생 중인 BGM 없음')}</b></div>${gm?`<button id="stopBgm" class="sound-stop-current" type="button" title="재생 완전 정지" aria-label="재생 완전 정지" ${active?'':'disabled'}>×</button>`:''}</div><div class="play-time"><span id="soundNowCurrent">${fmtClock(pos)}</span><input id="bgmSeek" type="range" min="0" max="${seekMax}" value="${Math.min(pos,seekMax)}" ${active?'':'disabled'}><span id="soundNowTotal">${active?(dur?fmtClock(dur):'불러오는 중'):'--:--'}</span></div></div>${gm?`<div class="sound-transport"><button id="prevBgm" type="button">⏮ 이전</button><button id="pauseBgm" type="button" ${active?'':'disabled'}>${cur.status==='paused'?'▶ 계속 재생':'⏸ 일시정지'}</button><button id="nextBgm" type="button">다음 ⏭</button><select id="bgmMode"><option value="next" ${mode==='next'?'selected':''}>끝나면 다음 곡</option><option value="repeat_one" ${mode==='repeat_one'?'selected':''}>한 곡 반복</option><option value="repeat_all" ${mode==='repeat_all'?'selected':''}>재생목록 반복</option><option value="stop_after" ${mode==='stop_after'?'selected':''}>한 곡 후 정지</option></select></div><div class="sound-grid"><section><h3 class="sound-section-title"><span>BGM</span><button class="btn small" data-toggle-sound-add="bgm" type="button" aria-expanded="${APP.soundAddOpen.bgm?'true':'false'}">${APP.soundAddOpen.bgm?'− 닫기':'＋ 추가'}</button></h3><div class="sound-add-wrap ${APP.soundAddOpen.bgm?'':'hidden'}" data-sound-add-wrap="bgm"><form id="bgmUpload" class="sound-add"><input name="name" placeholder="BGM 이름" aria-label="BGM 이름"><div class="sound-file-picker"><input id="bgmAudioFile" class="hidden-file-input sound-file-input" name="file" type="file" accept="audio/*" aria-label="BGM 오디오 파일" required><label class="sound-file-button" for="bgmAudioFile">파일 선택</label><span class="sound-file-name" data-sound-file-name>선택된 파일 없음</span></div><button type="submit">파일 추가</button></form></div><label class="volume-line"><span>전체 BGM 기준 음량</span><input id="gmBgmVolume" type="range" min="0" max="1" step="0.05" value="${Number(cur.bgm_volume??cur.volume??1)}"></label><div class="sound-list sound-sort-list" data-sound-list-kind="bgm">${bgm.map(x=>soundRow(x,'bgm')).join('')||'<p class="small muted">저장된 BGM이 없습니다.</p>'}</div></section><section><h3 class="sound-section-title"><span>효과음</span><button class="btn small" data-toggle-sound-add="sfx" type="button" aria-expanded="${APP.soundAddOpen.sfx?'true':'false'}">${APP.soundAddOpen.sfx?'− 닫기':'＋ 추가'}</button></h3><div class="sound-add-wrap ${APP.soundAddOpen.sfx?'':'hidden'}" data-sound-add-wrap="sfx"><form id="sfxUpload" class="sound-add"><input name="name" placeholder="효과음 이름" aria-label="효과음 이름"><div class="sound-file-picker"><input id="sfxAudioFile" class="hidden-file-input sound-file-input" name="file" type="file" accept="audio/*" aria-label="효과음 오디오 파일" required><label class="sound-file-button" for="sfxAudioFile">파일 선택</label><span class="sound-file-name" data-sound-file-name>선택된 파일 없음</span></div><button type="submit">파일 추가</button></form></div><label class="volume-line"><span>전체 효과음 기준 음량</span><input id="gmSfxVolume" type="range" min="0" max="1" step="0.05" value="${Number(cur.sfx_volume??1)}"></label><div class="sound-list sound-sort-list" data-sound-list-kind="sfx">${sfx.map(x=>soundRow(x,'sfx')).join('')||'<p class="small muted">저장된 효과음이 없습니다.</p>'}</div></section></div>`:''}<div class="personal-volume"><b>내 사운드</b><label><span>BGM</span><input data-personal-volume="bgm" type="range" min="0" max="1" step="0.05" value="${Number(prefs.bgm??.7)}"></label><label><span>효과음</span><input data-personal-volume="sfx" type="range" min="0" max="1" step="0.05" value="${Number(prefs.sfx??.8)}"></label><button id="soundMute" type="button">${APP.soundEnabled?'전체 음소거':'사운드 허용'}</button></div></div>`;attachSoundDrawer();startSoundDrawerTicker()
}
function attachSoundSort(){
  $$('.sound-sort-list').forEach(list=>{let dragged=null;$$('[data-sound-sort-id]',list).forEach(row=>{row.addEventListener('dragstart',e=>{dragged=row;row.classList.add('dragging');try{e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('text/plain',row.dataset.soundSortId)}catch{}});row.addEventListener('dragend',async()=>{row.classList.remove('dragging');if(!dragged)return;dragged=null;const ids=$$('[data-sound-sort-id]',list).map(x=>Number(x.dataset.soundSortId));try{await api(`/api/rooms/${APP.creds.room}/order/sounds`,{method:'PUT',body:JSON.stringify({ids,names:[],folder_id:null})});const map=new Map(ids.map((id,i)=>[id,i+1]));for(const snd of (APP.state.sounds||[]))if(map.has(Number(snd.id)))snd.sort_order=map.get(Number(snd.id));toast('사운드 순서를 저장했습니다.',1200)}catch(e){toast(e.message,3000)}})});list.addEventListener('dragover',e=>{if(!dragged||dragged.dataset.soundSortKind!==list.dataset.soundListKind)return;e.preventDefault();const target=e.target.closest?.('[data-sound-sort-id]');if(!target||target===dragged)return;const r=target.getBoundingClientRect();list.insertBefore(dragged,e.clientY<r.top+r.height/2?target:target.nextSibling)})});
}
function attachSoundDrawer(){
  const root=$('#soundDrawer');$$('.sound-file-input',root).forEach(input=>input.addEventListener('change',()=>{const box=input.closest('.sound-file-picker'),name=$('[data-sound-file-name]',box);if(name)name.textContent=input.files?.[0]?.name||'선택된 파일 없음'}));$('#soundDrawer [data-close-sound]')?.addEventListener('click',closeSoundDrawer);$$('[data-personal-volume]',root).forEach(i=>i.addEventListener('input',()=>{const p=soundPrefs();p[i.dataset.personalVolume]=Number(i.value);setSoundPrefs(p);applyBgmState(APP.state?.sound_state)}));$('#soundMute')?.addEventListener('click',()=>{APP.soundEnabled=!APP.soundEnabled;localStorage.setItem(SOUND_ENABLED_KEY,APP.soundEnabled?'1':'0');if(!APP.soundEnabled)stopSoundEngines();else applyBgmState(APP.state?.sound_state);renderSoundDrawer()});if(APP.state?.me?.role!=='gm')return;
  $$('[data-toggle-sound-add]',root).forEach(b=>b.addEventListener('click',()=>{const kind=b.dataset.toggleSoundAdd;APP.soundAddOpen=APP.soundAddOpen||{bgm:false,sfx:false};const open=!(APP.soundAddOpen[kind]===true);APP.soundAddOpen[kind]=open;const wrap=$(`[data-sound-add-wrap=\"${kind}\"]`,root);wrap?.classList.toggle('hidden',!open);b.textContent=open?'− 닫기':'＋ 추가';b.setAttribute('aria-expanded',open?'true':'false');if(open){const name=wrap?.querySelector('input[name=\"name\"]');requestAnimationFrame(()=>{name?.focus({preventScroll:true});wrap?.scrollIntoView({block:'nearest',behavior:'smooth'})})}}));attachGmVolumeSlider('#gmBgmVolume','bgm');attachGmVolumeSlider('#gmSfxVolume','sfx');$$('[data-play-bgm]',root).forEach(b=>b.addEventListener('click',()=>soundPlay(Number(b.dataset.playBgm),'bgm')));$$('[data-play-sfx]',root).forEach(b=>b.addEventListener('click',()=>soundPlay(Number(b.dataset.playSfx),'sfx')));$$('[data-del-sound]',root).forEach(b=>b.addEventListener('click',async()=>{if(!confirmUi('이 사운드를 삭제할까요?'))return;try{await api(`/api/rooms/${APP.creds.room}/sounds/${b.dataset.delSound}`,{method:'DELETE'});await refreshState(true)}catch(e){toast(e.message,3000)}}));
  $('#stopBgm')?.addEventListener('click',()=>soundControl('stop'));$('#pauseBgm')?.addEventListener('click',async()=>{try{if(APP.state?.sound_state?.status==='paused'){await soundControl('resume')}else if(APP.state?.sound_state?.sound_id){const r=await api(`/api/rooms/${APP.creds.room}/sounds/pause`,{method:'POST',body:JSON.stringify({position:currentBgmPosition(),volume:soundSliderVolume('#gmBgmVolume',1)})});if(r.state){applyBgmState(r.state);updateSoundDrawerState(r.state)}}}catch(e){toast(e.message,3000)}});$('#nextBgm')?.addEventListener('click',()=>soundControl('next'));$('#prevBgm')?.addEventListener('click',()=>soundControl('prev'));$('#bgmMode')?.addEventListener('change',e=>soundControl('mode',e.target.value));
  const seek=$('#bgmSeek');let seekCommit=false;const previewSeek=()=>{if(!seek||seek.disabled)return;APP.soundSeeking=true;const n=Math.max(0,Number(seek.value)||0),cur=$('#soundNowCurrent');if(cur)cur.textContent=fmtClock(n)};const commitSeek=async()=>{if(!seek||seek.disabled||seekCommit)return;seekCommit=true;const pos=seekBgmEngine(seek.value);APP.soundSeeking=false;try{await soundControl('seek',null,pos)}finally{seekCommit=false;updateSoundProgress()}};seek?.addEventListener('pointerdown',previewSeek);seek?.addEventListener('input',previewSeek);seek?.addEventListener('change',commitSeek);seek?.addEventListener('pointerup',commitSeek);seek?.addEventListener('pointercancel',()=>{APP.soundSeeking=false;updateSoundProgress()});
  attachSoundUpload('#bgmUpload','bgm');attachSoundUpload('#sfxUpload','sfx');attachSoundSort();
}
async function soundControl(action,mode=null,position=0){
  try{if(['stop','next','prev'].includes(action)){APP.soundSeeking=false;stopSoundEngines();updateSoundProgress()}let r;if(action==='stop')r=await api(`/api/rooms/${APP.creds.room}/sounds/stop`,{method:'POST'});else r=await api(`/api/rooms/${APP.creds.room}/sounds/control`,{method:'POST',body:JSON.stringify({action,mode,position})});if(r?.state){applyBgmState(r.state);updateSoundDrawerState(r.state)}return r}catch(e){toast(e.message,3500);if(action!=='stop')applyBgmState(APP.state?.sound_state)}
}
async function soundPlay(id,kind){
  try{if(kind==='bgm'){APP.forceBgmStartId=Number(id);APP.soundSeeking=false;stopSoundEngines();const seek=$('#bgmSeek'),cur=$('#soundNowCurrent'),total=$('#soundNowTotal');if(seek){seek.value='0';seek.disabled=false}if(cur)cur.textContent='0:00';if(total)total.textContent='불러오는 중'}const volume=soundSliderVolume(kind==='bgm'?'#gmBgmVolume':'#gmSfxVolume',1),r=await api(`/api/rooms/${APP.creds.room}/sounds/play`,{method:'POST',body:JSON.stringify({sound_id:id,position:0,volume})});if(kind==='bgm'&&r?.state){applyBgmState(r.state);updateSoundDrawerState(r.state)}return r}catch(e){if(kind==='bgm'){APP.forceBgmStartId=null;applyBgmState(APP.state?.sound_state)}toast(e.message,3500)}
}

async function loadInviteCodes(rootSelector='#settingsInviteInfo'){const root=$(rootSelector);if(!root)return;try{const x=await api(`/api/rooms/${APP.creds.room}/invite-codes`),xs=x.invites||[];root.innerHTML=xs.length?xs.map((it,i)=>`<div class="settings-invite-row ${i===0?'recommended':''}"><div><b>${esc(it.kind||'초대')}</b><code>${esc(it.invite_code)}</code></div><button class="btn small ${i===0?'dark':''}" data-invite-copy="${i}" type="button">초대코드 복사</button></div>`).join(''):'<div class="notice warn">초대코드를 만들 네트워크 주소를 찾지 못했습니다. EXE 런처의 초대 기능을 사용하세요.</div>';$$('[data-invite-copy]',root).forEach(b=>b.addEventListener('click',()=>copyText(xs[Number(b.dataset.inviteCopy)]?.invite_code||'')))}catch(e){root.innerHTML='<div class="notice warn">초대코드를 불러오지 못했습니다. EXE 런처에서 초대코드를 복사할 수 있습니다.</div>'}}
function settingsMemberRows(){const party=APP.state.party||[];return party.map(p=>`<article class="settings-member-row"><div class="settings-member-main"><b>${rawEsc(p.character_name||p.display_name)}</b><span class="small ${p.online?'online':'offline'}">${p.online?'● 온라인':'○ 오프라인'} · ${rawEsc(p.display_name)}</span>${p.disabled?'<span class="pill danger-pill">접속 비활성</span>':''}</div><div class="settings-member-actions"><button class="btn small" data-member-kick="${p.member_id}" type="button" ${p.online?'':'disabled'}>추방</button><button class="btn small" data-member-enabled="${p.member_id}" data-enabled="${p.disabled?'0':'1'}" type="button">${p.disabled?'접속 허용':'접속 차단'}</button><button class="btn small" data-member-reconnect="${p.member_id}" type="button">재접속 코드</button><select class="select compact-member-select" data-member-character="${p.member_id}">${party.map(c=>`<option value="${c.character_id}" ${Number(c.character_id)===Number(p.character_id)?'selected':''}>${rawEsc(c.character_name||c.display_name)}</option>`).join('')}</select><button class="btn small" data-member-assign="${p.member_id}" type="button">캐릭터 재배치</button><button class="btn small danger" data-member-delete="${p.member_id}" data-member-name="${attr(p.display_name)}" type="button">영구 삭제</button></div></article>`).join('')||'<div class="small muted">아직 참가한 플레이어가 없습니다.</div>'}
const DWPACK_KIND_LABELS={rules:'규칙',core_moves:'핵심 행동',classes:'직업',spells:'주문',races:'종족',expansions:'확장직업',monster_folders:'몬스터 폴더',monsters:'몬스터',npcs:'NPC'};
function dwpackCountsText(counts={}){return Object.entries(DWPACK_KIND_LABELS).filter(([k])=>Number(counts[k]||0)>0).map(([k,v])=>`${v} ${Number(counts[k]||0)}`).join(' · ')||'데이터 없음'}
function renderDwpackPreview(x){
  const root=$('#dwpackPreview');if(!root)return;
  APP.dwpackPreview=x||null;
  if(!x){root.innerHTML='<div class="small muted">가져올 .dwpack 파일을 선택하면 적용하기 전에 내용과 같은 이름의 자료가 있는지 먼저 확인합니다.</div>';return}
  const conflicts=(x.conflicts||[]),warnings=(x.warnings||[]);
  root.innerHTML=`<div class="dwpack-preview"><div class="dwpack-preview-head"><div><b class="no-i18n">${rawEsc(x.name||'팩')}</b><span>${esc(dwpackCountsText(x.counts||{}))}</span></div><span class="pill">format v${Number(x.format_version)||1}</span></div>${warnings.length?`<div class="notice warn"><b>팩 경고 ${warnings.length}개</b><br>${warnings.slice(0,6).map(esc).join('<br>')}</div>`:''}${conflicts.length?`<div class="notice"><b>현재 캠페인과 이름이 겹치는 항목 ${Number(x.conflict_count)||conflicts.length}개</b><div class="small muted">${conflicts.slice(0,12).map(c=>`${esc(DWPACK_KIND_LABELS[c.kind]||c.kind)} · ${rawEsc(c.name)}`).join('<br>')}${conflicts.length>12?'<br>…':''}</div></div>`:'<div class="notice good">이름 충돌이 없습니다.</div>'}<div class="dwpack-import-options"><label class="field"><span>충돌 처리</span><select id="dwpackConflictMode" class="select"><option value="keep">기존 데이터 유지</option><option value="replace">가져온 데이터로 교체</option><option value="duplicate">별도 항목으로 추가</option><option value="sync">팩과 동일하게 전체 교체 · 플레이어 없는 캠페인 전용</option></select></label><label class="choice settings-choice"><input id="dwpackApplyRules" type="checkbox" ${Number(x.counts?.rules||0)?'':'disabled'}><span>캠페인 규칙도 적용 ${Number(x.counts?.rules||0)?'<small>현재 규칙을 팩의 규칙으로 교체합니다.</small>':'<small>이 팩에는 규칙이 없습니다.</small>'}</span></label><button id="dwpackApply" class="btn dark" type="button">이 팩 적용</button></div></div>`;
  $('#dwpackApply')?.addEventListener('click',applyDwpackPreview);
}
async function downloadAuthenticatedFile(url,filename){
  const headers={};if(APP.creds?.token)headers.Authorization=`Bearer ${APP.creds.token}`;
  const res=await fetch(url,{headers});if(!res.ok){let detail='파일을 받을 수 없습니다.';try{detail=(await res.json())?.detail||detail}catch{}throw new Error(detail)}
  const blob=await res.blob(),a=document.createElement('a'),href=URL.createObjectURL(blob);a.href=href;a.download=filename;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(href),1000);
}
async function previewDwpackFile(file){
  if(!file)return;if(!/\.dwpack$/i.test(file.name||''))return toast('.dwpack 파일을 선택하세요.',3000);
  const fd=new FormData();fd.append('file',file,file.name);
  const root=$('#dwpackPreview');if(root)root.innerHTML='<div class="notice">팩을 검사하는 중…</div>';
  try{const x=await apiForm(`/api/rooms/${APP.creds.room}/dwpack/preview`,fd,30000);renderDwpackPreview(x)}catch(e){renderDwpackPreview(null);toast(e.message,4200)}
}
async function applyDwpackPreview(){
  const x=APP.dwpackPreview;if(!x?.preview_token)return;
  const mode=$('#dwpackConflictMode')?.value||'keep',apply_rules=!!$('#dwpackApplyRules')?.checked;
  const labels=APP.language==='en'
    ?{keep:'Keep existing items and add only missing data.',replace:'Replace same-named definitions with imported data.',duplicate:'Add conflicting items under separate names.',sync:'Clear included data categories and rebuild them to match the pack.'}
    :{keep:'기존 항목을 유지하고 없는 데이터만 추가합니다.',replace:'같은 이름의 정의를 가져온 데이터로 교체합니다.',duplicate:'충돌 항목을 별도 이름으로 추가합니다.',sync:'팩에 포함된 데이터 종류를 비운 뒤 팩과 동일하게 다시 구성합니다.'};
  const rulesLine=apply_rules?(APP.language==='en'?'\nCampaign rules will also be replaced.':'\n캠페인 규칙도 교체합니다.'):'',ask=APP.language==='en'?'\n\nApply now?':'\n\n적용할까요?';
  if(!confirmUi(`${labels[mode]}${rulesLine}${ask}`))return;
  try{const r=await api(`/api/rooms/${APP.creds.room}/dwpack/import`,{method:'POST',body:JSON.stringify({preview_token:x.preview_token,conflict_mode:mode,apply_rules})},30000);APP.dwpackPreview=null;await refreshState(true);const applied=r.applied||{},total=Object.entries(applied).filter(([k])=>k!=='skipped').reduce((a,[,v])=>a+Number(v||0),0),skipped=Number(applied.skipped||0);toast(APP.language==='en'?`Pack applied · ${total} applied${skipped?` · ${skipped} kept`:''}`:`팩 적용 완료 · ${total}개 반영${skipped?` · ${skipped}개 유지`:''}`,4500);openGMSettings()}catch(e){toast(e.message,4500)}
}

function openGMSettings(){
  if(APP.state?.me?.role!=='gm')return;
  closeSoundDrawer();closeGMSettings();const st=APP.state.room.settings||{};
  document.body.insertAdjacentHTML('beforeend',`<aside id="gmSettingsDrawer" class="settings-drawer">
    <div class="settings-head"><div class="settings-head-title"><b>설정</b><span>캠페인 · 선택 규칙 · 팩 · 참가자 · 표시</span></div><div class="settings-head-actions"><button id="settingsSaveUi" class="settings-save-top" type="button">설정 저장</button><button data-close-settings type="button" aria-label="닫기">×</button></div></div>
    <div class="settings-body">
      <section><h3>캠페인</h3><div class="compact-action-row"><label class="field grow"><span>캠페인 이름</span><input id="settingsCampaignName" class="input" value="${attr(APP.state.room.campaign_name)}"></label><button id="settingsSaveCampaign" class="btn" type="button">이름 저장</button></div><div class="notice">${APP.language==='en'?`Player capacity: ${Number(APP.state.room.player_count||0)}/${Number(APP.state.room.max_players||4)} · GM excluded`:`플레이어 정원: ${Number(APP.state.room.player_count||0)}/${Number(APP.state.room.max_players||4)}명 · GM 제외`}</div><div class="setting-subhead">초대코드</div><div class="small muted">플레이어는 ${VERSION_LABEL} EXE의 ‘초대코드’ 칸에 붙여넣으면 됩니다. 비밀번호는 코드에 포함되지 않습니다.</div><div id="settingsInviteInfo"><div class="notice">초대코드를 만드는 중…</div></div></section>
      <section><h3>선택 규칙</h3><label class="choice settings-choice"><input id="settingsExpansionsEnabled" type="checkbox" ${st.expansions_enabled===true?'checked':''}><span><b>확장직업 사용</b> · Unlimited Dungeons / Distant Shore Pack 참고</span></label><div class="notice">확장직업은 Dungeon World 1판 원작의 기본 기능이 아닙니다. 새 캠페인에서는 기본적으로 꺼져 있습니다. 끄더라도 이미 만든 확장직업·부여 기록·개인 자원은 삭제되지 않으며, 다시 켜면 그대로 이어집니다.</div><div class="small muted">예시 확장직업 11개는 새 캠페인에 자동으로 넣지 않습니다. 확장직업을 켜면 아래 팩 영역에서 “확장직업 예시 팩”을 받을 수 있습니다. CC BY-SA 4.0 출처는 도움말에서 확인할 수 있습니다.</div></section>
      <section><h3>팩 · .dwpack</h3><div class="notice">직업·종족·주문·핵심 행동${st.expansions_enabled===true?'·확장직업':''}·몬스터·규칙처럼 GM이 관리하는 자료를 다른 캠페인으로 옮길 수 있습니다. 플레이어, 캐릭터의 현재 상태, 비밀번호와 접속 정보, 플레이 기록, 개인 화면 설정은 포함하지 않습니다.</div><div class="dwpack-export-options"><label class="choice settings-choice"><input id="dwpackExportRules" type="checkbox" checked><span>캠페인 규칙 포함</span></label><label class="choice settings-choice"><input id="dwpackExportNpcs" type="checkbox"><span>NPC 포함</span></label></div><div class="inline-actions dwpack-actions"><button id="dwpackExport" class="btn dark" type="button">현재 데이터 내보내기</button><label class="btn" for="dwpackFile">팩 가져오기</label><input id="dwpackFile" class="hidden-file-input" type="file" accept=".dwpack,application/zip"><a class="btn" href="/api/dwpack/reference" download="DungeonWorld_DWPack_Reference.zip">팩 제작 참고자료</a><a class="btn" href="/api/dwpack/core?lang=${APP.language}" download="${APP.language==='en'?'DungeonWorld_1E_Core_EN.dwpack':'DungeonWorld_1E_Core.dwpack'}">1E 기본 팩</a>${st.expansions_enabled===true?`<a class="btn" href="/api/dwpack/expansions?lang=${APP.language}" download="${APP.language==='en'?'UnlimitedDungeons_DistantShore_Expansions_EN.dwpack':'UnlimitedDungeons_DistantShore_Expansions.dwpack'}">확장직업 예시 팩</a>`:''}</div><div id="dwpackPreview"><div class="small muted">가져올 .dwpack 파일을 선택하면 적용하기 전에 내용과 같은 이름의 자료가 있는지 먼저 확인합니다.</div></div></section>
      <section><h3>참가자 / 접속 권한</h3><div class="notice">추방은 현재 연결만 끊습니다. 접속 차단은 재접속도 막습니다. 재접속 코드는 기존 캐릭터로 돌아오기 위한 일회용 코드입니다. 캐릭터 재배치는 두 참가자의 캐릭터 소유권을 안전하게 교환합니다.</div><div class="settings-member-list">${settingsMemberRows()}</div></section>
      <section><h3>주사위 / 대표색</h3><label class="choice settings-choice"><input id="settingsGmDicePublic" type="checkbox" ${st.gm_dice_public!==false?'checked':''}><span>GM 주사위 준비와 결과를 플레이어에게 공개</span></label><label class="color-setting"><span>GM ${rawEsc(APP.state.room.gm_name)}</span><input id="settingsGmColor" type="color" value="${attr(st.gm_color||'#8b1e1e')}"></label><div class="player-color-list">${(APP.state.party||[]).map(p=>`<label class="color-setting"><span>${rawEsc(p.character_name||p.display_name)}</span><input data-player-color="${p.character_id}" type="color" value="${attr((st.player_colors||{})[String(p.character_id)]||'#1d5f91')}"></label>`).join('')||'<div class="small muted">아직 플레이어가 없습니다.</div>'}</div></section>
      <section class="danger-zone"><h3>로컬 / 캠페인 데이터</h3><div class="inline-actions"><button id="settingsClearBrowser" class="btn" type="button">이 브라우저 접속 정보 초기화</button><button id="settingsDeleteCampaign" class="btn danger" type="button">캠페인 영구 삭제</button></div></section>
    </div>
  </aside>`);
  attachGMSettings();loadInviteCodes();
}

function attachGMSettings(){
  $('#dwpackFile')?.addEventListener('change',e=>previewDwpackFile(e.target.files?.[0]));
  $('#dwpackExport')?.addEventListener('click',async()=>{
    const include_npcs=!!$('#dwpackExportNpcs')?.checked,include_rules=!!$('#dwpackExportRules')?.checked;
    const filename=`${(APP.state?.room?.campaign_name||'DungeonWorld_Data').replace(/[\\/:*?"<>|]+/g,'_')}.dwpack`;
    try{await downloadAuthenticatedFile(`/api/rooms/${APP.creds.room}/dwpack/export?include_npcs=${include_npcs?'true':'false'}&include_rules=${include_rules?'true':'false'}`,filename);toast('팩을 내보냈습니다.')}catch(e){toast(e.message,4200)}
  });
  $('[data-close-settings]')?.addEventListener('click',closeGMSettings);$('#settingsSaveCampaign')?.addEventListener('click',async()=>{const name=$('#settingsCampaignName')?.value.trim();if(!name)return;try{await api(`/api/rooms/${APP.creds.room}/campaign`,{method:'PUT',body:JSON.stringify({name})});await refreshState(true);toast('캠페인 이름을 저장했습니다.');openGMSettings()}catch(e){toast(e.message,3500)}});$('#settingsSaveUi')?.addEventListener('click',async()=>{const player_colors={};$$('[data-player-color]').forEach(i=>player_colors[String(i.dataset.playerColor)]=i.value);try{await api(`/api/rooms/${APP.creds.room}/settings`,{method:'PUT',body:JSON.stringify({settings:{expansions_enabled:!!$('#settingsExpansionsEnabled')?.checked,gm_dice_public:!!$('#settingsGmDicePublic')?.checked,gm_color:$('#settingsGmColor')?.value||'#8b1e1e',player_colors}})});await refreshState(true);toast('설정을 저장했습니다.');openGMSettings()}catch(e){toast(e.message,3500)}});
  $$('[data-member-kick]').forEach(b=>b.addEventListener('click',async()=>{try{const r=await api(`/api/rooms/${APP.creds.room}/members/${b.dataset.memberKick}/kick`,{method:'POST'});toast(`현재 연결 ${Number(r.kicked_connections)||0}개를 종료했습니다.`);await refreshState(true);openGMSettings()}catch(e){toast(e.message,3500)}}));
  $$('[data-member-enabled]').forEach(b=>b.addEventListener('click',async()=>{const enabled=b.dataset.enabled!=='1';try{await api(`/api/rooms/${APP.creds.room}/members/${b.dataset.memberEnabled}/enabled`,{method:'PUT',body:JSON.stringify({enabled})});await refreshState(true);openGMSettings()}catch(e){toast(e.message,3500)}}));
  $$('[data-member-reconnect]').forEach(b=>b.addEventListener('click',async()=>{try{const r=await api(`/api/rooms/${APP.creds.room}/members/${b.dataset.memberReconnect}/reconnect-code`,{method:'POST'});await copyText(r.reconnect_code);promptUi('재접속 코드입니다. 플레이어에게 전달하세요. 클립보드에도 복사했습니다.',r.reconnect_code)}catch(e){toast(e.message,3500)}}));
  $$('[data-member-assign]').forEach(b=>b.addEventListener('click',async()=>{const mid=b.dataset.memberAssign,sel=$(`[data-member-character="${mid}"]`),cid=Number(sel?.value)||0;if(!cid)return;if(!confirmUi('선택한 참가자에게 이 캐릭터를 재배치할까요? 기존 소유자가 있으면 두 캐릭터가 서로 교환됩니다.'))return;try{await api(`/api/rooms/${APP.creds.room}/members/${mid}/character`,{method:'PUT',body:JSON.stringify({character_id:cid})});await refreshState(true);openGMSettings();toast('캐릭터 소유권을 재배치했습니다.')}catch(e){toast(e.message,3500)}}));
  $$('[data-member-delete]').forEach(b=>b.addEventListener('click',async()=>{const name=b.dataset.memberName,typed=promptUi(`참가자와 연결된 캐릭터를 영구 삭제합니다. 계속하려면 표시 이름을 입력하세요.\n${name}`);if(typed!==name)return typed!==null&&toast('이름이 일치하지 않습니다.');try{await api(`/api/rooms/${APP.creds.room}/members/${b.dataset.memberDelete}`,{method:'DELETE'});await refreshState(true);openGMSettings()}catch(e){toast(e.message,3500)}}));
  $('#settingsClearBrowser')?.addEventListener('click',()=>{if(!confirmUi('이 브라우저에 저장된 Dungeon World 접속 정보와 화면 배치를 초기화할까요?\n캠페인 데이터는 삭제되지 않습니다.'))return;clearBrowserGameData();location.replace('/?mode=host')});$('#settingsDeleteCampaign')?.addEventListener('click',async()=>{const expected=APP.state.room.campaign_name,typed=promptUi(`정말 삭제하려면 캠페인 이름을 입력하세요.\n${expected}`);if(typed!==expected)return typed!==null&&toast('캠페인 이름이 일치하지 않습니다.');try{await api(`/api/rooms/${APP.creds.room}`,{method:'DELETE'});clearCurrent();location.replace('/?mode=host')}catch(e){toast(e.message,3500)}})
}

function boot(){
  document.addEventListener('click',e=>{const lang=e.target.closest?.('[data-language-switch]');if(lang){e.preventDefault();setLanguage(APP.language==='en'?'ko':'en');return}const top=e.target.closest?.('[data-top-action]');if(top){e.preventDefault();e.stopPropagation();handleTopAction(top);return}if(e.target.closest?.('[data-global-dice]')){e.preventDefault();openOwnDice();return}if(e.target.closest?.('[data-global-sound]')){e.preventDefault();if($('#soundDrawer'))closeSoundDrawer();else openSoundPanel();return}if(e.target.closest?.('[data-global-settings]')){e.preventDefault();if($('#gmSettingsDrawer'))closeGMSettings();else openGMSettings();return}});ensureLiveLayers();
  window.addEventListener('error',e=>showGlobalError(`화면 오류: ${e.message||'알 수 없는 오류'}`));window.addEventListener('unhandledrejection',e=>showGlobalError(`처리되지 않은 오류: ${e.reason?.message||e.reason||'알 수 없는 오류'}`));window.addEventListener('resize',()=>APP.workspaceResizeHandler?.());
  const params=new URLSearchParams(location.search),requestedLang=params.get('lang');if(requestedLang==='en'||requestedLang==='ko'){APP.language=requestedLang;localStorage.setItem(LANGUAGE_KEY,requestedLang)}document.documentElement.lang=APP.language==='en'?'en':'ko';startI18nObserver();const mode=params.get('mode')||'',room=(params.get('room')||'').trim().toUpperCase();
  if(mode==='reset'){clearBrowserGameData();renderLauncherRequired('이 브라우저의 Dungeon World 화면 설정을 초기화했습니다.');return}
  loadCreds();
  if(mode==='play'&&APP.creds&&(!room||APP.creds.room===room)){refreshState(true);return}
  renderLauncherRequired(mode==='play'?'일회성 접속 티켓이 없거나 만료되었습니다. EXE 런처에서 다시 열어주세요.':'');
}
const _nativeConfirm=window.confirm.bind(window),_nativePrompt=window.prompt.bind(window),_nativeAlert=window.alert.bind(window);
function translateDialogText(v=''){const raw=String(v??'');return APP.language==='en'?translateUiText(raw):raw}
window.confirm=(msg)=>_nativeConfirm(translateDialogText(msg));
window.prompt=(msg,def)=>_nativePrompt(translateDialogText(msg),def);
window.alert=(msg)=>_nativeAlert(translateDialogText(msg));

async function loadI18nCatalogs(){
  try{const suffix=`?v=${encodeURIComponent(STATIC_CACHE_KEY)}`,opts={cache:'no-store'};const [content,ui]=await Promise.all([fetch('/static/i18n_content_en.json'+suffix,opts).then(r=>r.ok?r.json():Promise.reject(new Error('content i18n'))),fetch('/static/i18n_ui_en.json'+suffix,opts).then(r=>r.ok?r.json():Promise.reject(new Error('ui i18n')))]);APP.i18nContentEn=content.map||{};APP.i18nContentKo=Object.fromEntries(Object.entries(APP.i18nContentEn).map(([ko,en])=>[en,ko]));APP.i18nUiExact=ui.exact||{};APP.i18nUiTerms=Object.entries(ui.terms||{}).sort((a,b)=>b[0].length-a[0].length);APP.i18nUiPatterns=(ui.patterns||[]).map(([a,b])=>[new RegExp(a),b])}catch(e){console.warn('i18n catalog load failed',e)}
}
loadI18nCatalogs().finally(boot);
