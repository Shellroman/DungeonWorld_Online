from __future__ import annotations
import json, os, re, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP_JS=(ROOT/'static/app.js').read_text(encoding='utf-8')
CSS=(ROOT/'static/styles.css').read_text(encoding='utf-8')
SERVER=(ROOT/'app.py').read_text(encoding='utf-8')
UI=json.loads((ROOT/'static/i18n_ui_en.json').read_text(encoding='utf-8'))
EXTRA=json.loads((ROOT/'tools/i18n_ui_extra_en.json').read_text(encoding='utf-8'))
checks=[]
def ok(name, cond, detail=''):
    if not cond: raise AssertionError(f'{name}: {detail}')
    checks.append(name)

def tr(raw:str)->str:
    core=raw.strip()
    if not re.search('[가-힣]',core): return core
    if core in UI.get('exact',{}): return UI['exact'][core]
    for pattern,repl in UI.get('patterns',[]):
        m=re.search(pattern,core)
        if m:
            out=core
            # Browser catalog replacements use $1, $2 ...
            py_repl=re.sub(r'\$(\d+)',lambda x:'\\g<'+x.group(1)+'>',repl)
            return re.sub(pattern,py_repl,out)
    if len(core)<=120:
        out=core
        for ko,en in sorted(UI.get('terms',{}).items(),key=lambda kv:-len(kv[0])):
            out=out.replace(ko,en)
        if out!=core and not re.search('[가-힣]',out): return out
    return core

# Version / schema identity for the final release source.
ok('version_file',(ROOT/'VERSION').read_text(encoding='utf-8').strip()=='1.0.0')
ok('app_version','VERSION = "1.0.0"' in SERVER)
ok('schema_20','SCHEMA_VERSION = 20' in SERVER)
ok('revision_200','DEFAULT_DATA_REVISION = "1.0.0"' in SERVER)
ok('browser_version',"v1.0.0" in APP_JS)
ok('launcher_output_name','DungeonWorld_Online_v1.0.0.exe' in (ROOT/'build_windows_launcher.bat').read_text(encoding='utf-8'))

# Settings drawer must fully localize in English, including sentences that used to leak Korean.
settings_samples=[
 '설정','캠페인 · 선택 규칙 · 팩 · 참가자 · 표시','캠페인','캠페인 이름','이름 저장','초대코드',
 "플레이어는 v1.0.0 EXE의 ‘초대코드’ 칸에 붙여넣으면 됩니다. 비밀번호는 코드에 포함되지 않습니다.",
 '초대코드를 만드는 중…','선택 규칙','확장직업 사용','Unlimited Dungeons / Distant Shore Pack 참고',
 '확장직업은 Dungeon World 1판 원작의 기본 기능이 아닙니다. 새 캠페인에서는 기본적으로 꺼져 있습니다. 끄더라도 이미 만든 확장직업·부여 기록·개인 자원은 삭제되지 않으며, 다시 켜면 그대로 이어집니다.',
 '예시 확장직업 11개는 새 캠페인에 자동으로 넣지 않습니다. 확장직업을 켜면 아래 팩 영역에서 “확장직업 예시 팩”을 받을 수 있습니다. CC BY-SA 4.0 출처는 도움말에서 확인할 수 있습니다.',
 '팩 · .dwpack','캠페인 규칙 포함','NPC 포함','현재 데이터 내보내기','팩 가져오기','팩 제작 참고자료','1E 기본 팩','확장직업 예시 팩',
 '가져올 .dwpack 파일을 선택하면 적용하기 전에 내용과 같은 이름의 자료가 있는지 먼저 확인합니다.',
 '참가자 / 접속 권한','추방은 현재 연결만 끊습니다. 접속 차단은 재접속도 막습니다. 재접속 코드는 기존 캐릭터로 돌아오기 위한 일회용 코드입니다. 캐릭터 재배치는 두 참가자의 캐릭터 소유권을 안전하게 교환합니다.',
 '주사위 / 대표색','GM 주사위 준비와 결과를 플레이어에게 공개','아직 플레이어가 없습니다.','설정 저장','로컬 / 캠페인 데이터','이 브라우저 접속 정보 초기화','캠페인 영구 삭제',
 '● 온라인','○ 오프라인','접속 비활성','추방','접속 허용','접속 차단','재접속 코드','캐릭터 재배치','영구 삭제','아직 참가한 플레이어가 없습니다.'
]
for s in settings_samples:
    out=tr(s); ok('settings_en_'+str(abs(hash(s))),not re.search('[가-힣]',out),repr(out))
ok('import_pack_natural',UI['exact'].get('팩 가져오기')=='Import Pack',UI['exact'].get('팩 가져오기'))
ok('reassign_character_natural',UI['exact'].get('캐릭터 재배치')=='Reassign Character',UI['exact'].get('캐릭터 재배치'))
ok('dwpack_confirm_contextual_english',"Keep existing items and add only missing data." in APP_JS and "Campaign rules will also be replaced." in APP_JS and "Apply now?" in APP_JS)
ok('dwpack_result_contextual_english',"Pack applied · ${total} applied" in APP_JS)

# Change logs are compact and have their own context-aware English action names.
ok('compact_change_helper','def compact_change_detail' in SERVER)
for snippet in [
 '"규칙 수정", "room_rules", compact_change_detail(old, new)',
 '"설정 수정", "room_settings", compact_change_detail(old, new)',
]: ok('compact_endpoint_'+str(abs(hash(snippet))),snippet in SERVER,snippet)
ok('log_action_context','const LOG_ACTION_EN={' in APP_JS and 'function logActionName' in APP_JS)
ok('log_no_json_dump','return JSON.stringify(v)' not in APP_JS)
ok('log_room_targets',"raw==='room_rules'" in APP_JS and "raw==='room_settings'" in APP_JS)

# Help text was rewritten around fiction-first play and readable results.
for text in [
 'Dungeon World에서는 행동 이름을 먼저 고르기보다, 캐릭터가 실제로 무엇을 하는지 이야기하는 것이 먼저입니다. 그 설명이 행동의 조건에 맞으면 판정을 합니다.',
 '플레이어가 무엇을 하는지 먼저 듣고, 행동의 조건이 맞을 때 판정을 요청하세요. 결과가 나오면 준비해 둔 정답에 맞추기보다 그 결과에서 이어지는 상황을 보여주세요.',
 '장비는 이름, 종류, 수량, 무게와 태그를 중심으로 기록합니다. 종류는 목록을 정리하기 위한 분류이고, 실제 효과는 태그와 필요한 수치, 설명을 함께 보고 판단합니다.',
]:
    ok('help_source_'+str(abs(hash(text))),text in APP_JS)
    ok('help_en_'+str(abs(hash(text))),bool(UI['exact'].get(text)),repr(UI['exact'].get(text)))

# File-audio-only release: runtime, state, migration and UI all reject obsolete source types.
ok('sound_migration',"DELETE FROM sound_defs WHERE source_type<>'file'" in SERVER)
ok('sound_state_file_only',"source_type='file'" in SERVER)
ok('sound_ui_file_only',"filter(x=>x.source_type==='file')" in APP_JS)
ok('no_legacy_sound_ui','legacy-sound' not in APP_JS)
# Build the forbidden service names without embedding them in release files as literals.
for needle in [('you'+'tube'),('youtu'+'.be')]:
    hits=[]
    for path in ROOT.rglob('*'):
        if not path.is_file() or any(part in {'.git','__pycache__'} for part in path.parts): continue
        if path.suffix.lower() in {'.db','.png','.jpg','.jpeg','.gif','.ico','.exe','.zip','.enc'}: continue
        try: text=path.read_text(encoding='utf-8').lower()
        except Exception: continue
        if needle in text: hits.append(str(path.relative_to(ROOT)))
    ok('no_named_video_service_'+needle,not hits,repr(hits[:20]))

# Final readability pass must remain in the stylesheet.
ok('readability_pass','Public v1.0.0 release readability pass' in CSS)
for selector in ['.log{','.settings-body>section{','.help-manual{','.help-section p{','.input,.select,.textarea{']:
    ok('readability_'+selector,selector in CSS,selector)

# Integration: one-field settings/rules changes must store only that field in the log.
with tempfile.TemporaryDirectory(prefix='dw_v300_release_') as td:
    db_path=Path(td)/'test.db'
    os.environ['DW_DB']=str(db_path)
    sys.path.insert(0,str(ROOT))
    import app as dw
    from fastapi.testclient import TestClient
    with TestClient(dw.app, client=('127.0.0.1',50123)) as c:
        created=c.post('/api/rooms',json={'gm_name':'GM','campaign_name':'Release','password':'1234'})
        ok('integration_create',created.status_code==200,created.text)
        room=created.json()['room_code']; hdr={'Authorization':'Bearer '+created.json()['gm_token']}
        state=c.get(f'/api/rooms/{room}/state',headers=hdr).json()
        xp0=int(state['room']['rules']['xp_base'])
        rr=c.put(f'/api/rooms/{room}/rules',headers=hdr,json={'rules':{'xp_base':xp0+1}})
        ok('rule_update',rr.status_code==200,rr.text)
        st=c.get(f'/api/rooms/{room}/state',headers=hdr).json()
        log=next(x for x in st['logs'] if x['action']=='규칙 수정')
        ok('rule_log_one_key',log['detail'].get('changed_keys')==['xp_base'],repr(log['detail']))
        ok('rule_log_compact',set(log['detail'].get('before',{}))=={'xp_base'} and set(log['detail'].get('after',{}))=={'xp_base'},repr(log['detail']))
        old_public=bool(st['room']['settings'].get('gm_dice_public',True))
        sr=c.put(f'/api/rooms/{room}/settings',headers=hdr,json={'settings':{'gm_dice_public':not old_public}})
        ok('settings_update',sr.status_code==200,sr.text)
        st2=c.get(f'/api/rooms/{room}/state',headers=hdr).json()
        slog=next(x for x in st2['logs'] if x['action']=='설정 수정')
        ok('settings_log_one_key',slog['detail'].get('changed_keys')==['gm_dice_public'],repr(slog['detail']))
        ok('settings_log_compact',set(slog['detail'].get('before',{}))=={'gm_dice_public'} and set(slog['detail'].get('after',{}))=={'gm_dice_public'},repr(slog['detail']))
        # Force an old unsupported sound row, mark DB as schema 17, then run migration.
        with dw.db() as con:
            rid=con.execute('SELECT id FROM rooms WHERE code=?',(room,)).fetchone()['id']
            con.execute("INSERT INTO sound_defs(room_id,kind,name,source_type,source,sort_order,created_at) VALUES(?,?,?,?,?,?,?)",(rid,'bgm','old','remote','legacy',9999,dw.now_iso()))
            dw._set_schema_version(con,17)
        dw.init_db()
        with dw.db() as con:
            count=con.execute("SELECT COUNT(*) n FROM sound_defs WHERE source_type<>'file'").fetchone()['n']
        ok('schema18_sound_cleanup',count==0,str(count))

print('PASS',len(checks),'/',len(checks))
