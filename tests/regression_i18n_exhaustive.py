from __future__ import annotations
import ast, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'static/app.js').read_text(encoding='utf-8')
SERVER=(ROOT/'app.py').read_text(encoding='utf-8')
LAUNCHER=(ROOT/'launcher/main.go').read_text(encoding='utf-8')
UI=json.loads((ROOT/'static/i18n_ui_en.json').read_text(encoding='utf-8'))
CONTENT=json.loads((ROOT/'static/i18n_content_en.json').read_text(encoding='utf-8'))
SEED=json.loads((ROOT/'data/seed_data.json').read_text(encoding='utf-8'))
EXTRA=json.loads((ROOT/'tools/i18n_ui_extra_en.json').read_text(encoding='utf-8'))
fail=[]; passed=0
def ok(name,cond,detail=''):
 global passed
 if cond: passed+=1
 else: fail.append(f'{name}: {detail}')

# Built-in data coverage and source-aligned sanity.
ok('content_unmapped_zero',CONTENT.get('unmapped')==[],repr(CONTENT.get('unmapped')[:10]))
for k,v in EXTRA.items(): ok('extra_generated_'+k,UI['exact'].get(k)==v,repr(UI['exact'].get(k)))
critical={
 '크게 편집':'Edit in Large View','관계':'Relationships','관계 대상 이름':'Related Character / NPC',
 '관계 설명':'Relationship Description','＋ 관계 추가':'＋ Add Relationship','플레이어':'Player',
 '몬스터':'Monster','규칙':'Rules','수정치':'Modifier','팩':'Pack',
 '로컬 LAN':'Local LAN','네트워크':'Network','운명 선택 중':'Choosing Destiny',
}
for k,v in critical.items(): ok('critical_'+k,UI['exact'].get(k)==v or UI['terms'].get(k)==v,(UI['exact'].get(k),UI['terms'].get(k)))

# Regression for the play-sheet column bleed that used to mix starting gear into move text.
bad_bleed=('Max Load','Dungeon Rations','Leather Armor','Adventuring Gear','Bundle Of Arrows','Choose your arms','When you gain a level from')
for cname,c in SEED['classes'].items():
 for sec in ('start','a25','a610'):
  for mv in c.get(sec,[]):
   ko=mv.get('desc',''); en=CONTENT['map'].get(ko,'')
   if ko and en: ok(f'move_no_column_bleed_{cname}_{mv.get("name")}',not any(x in en for x in bad_bleed),en[:180])
for cls,spells in SEED['spells'].items():
 for sp in spells:
  en=CONTENT['map'].get(sp.get('desc',''),'')
  if en: ok(f'spell_desc_no_duplicate_level_{cls}_{sp.get("name")}',not re.match(r'^(?:Cantrip|Rote|\d+(?:st|nd|rd|th) Level)\b',en),en[:120])


# Regression help/pack polish: optional expansion material only appears when enabled,
# English help does not surface Korean-reference notes, and Korean UI uses the familiar word '팩'.
forbidden_pack_terms=['꾸러미','자료 팩','팩를','팩는']
polish_sources='\n'.join([APP,SERVER,(ROOT/'README_KO.md').read_text(encoding='utf-8'),(ROOT/'LICENSE_ATTRIBUTION_KO.md').read_text(encoding='utf-8')])
for term in forbidden_pack_terms: ok('pack_term_'+term,term not in polish_sources,term)
ok('help_expansion_topic_conditional',"topic.title!=='확장직업'" in APP and 'visibleHelpTopics()' in APP)
ok('help_expansion_lines_conditional',"!String(line).includes('확장직업')" in APP)
ok('help_english_hides_korean_section',"title!=='한국어 공개판'" in APP)
ok('help_english_hides_korean_source_group',"group!=='한국어판'" in APP and "key!=='ud_home'" in APP)
ok('rules_expansion_section_conditional',"const expansionRules=exp?`" in APP and '확장직업 규칙' in APP and '캐릭터당 확장직업 최대' in APP)
ok('settings_expansion_pack_conditional','st.expansions_enabled===true?`<a class="btn" href="/api/dwpack/expansions' in APP)
for source in [
 '확장직업 예시는 Unlimited Dungeons / Distant Shore Pack 자료와 한국어 번역을 참고했습니다. 자세한 출처와 이용 조건은 “라이선스와 출처”에서 확인할 수 있습니다.',
 '확장직업 예시는 Dungeon World 기본 규칙이 아니라 Unlimited Dungeons / Distant Shore Pack 계열의 팬 창작 자료를 참고합니다. 이 자료와 한국어 번역은 별도의 CC BY-SA 4.0 조건과 출처 표시를 따릅니다.',
 '더 자세한 원문이나 번역 자료를 확인하고 싶을 때 사용할 수 있는 대표 링크입니다.',
]:
 value=UI['exact'].get(source,'')
 ok('english_source_neutral_'+str(abs(hash(source)))[:8],bool(value) and 'Korean' not in value and 'translation' not in value.lower(),value)
ok('legendary_move_help','다른 게임에서 사용하는 Legendary Action 규칙과는 관계가 없습니다.' in APP and UI['exact'].get('전설행동')=='Legendary Move')


# UI/editor coverage added after the final bilingual visual pass.
ok('class_bonds_linewise_display', "(c.bonds||[]).map(x=>builtin?displayMultilineContent(x):String(x??'')).join('\\n')" in APP and 'function displayMultilineContent' in APP)
ok('class_gear_display_translation', "displayMultilineContent(c.gear||'')" in APP)
ok('inventory_range_is_select', 'inventory-range-select' in APP and 'data-inv="weapon_range"' in APP and 'list="inventoryRangeOptions"' not in APP)
ok('monster_tag_summary_translated', 'selectedTags.map(displayMonsterTag).join' in APP and 'names.map(displayMonsterTag).join' in APP)
ok('english_default_currency_coin', "?'Coin':(r.currency_name||'닢')" in APP and CONTENT['map'].get('닢')=='Coin')
for k in ['크게 편집','긴 설명 편집','내용 적용','시작 장비 안내','재화 명칭','태그 없음','거리 선택…']:
 ok('ui_exact_'+k, bool(UI['exact'].get(k)), repr(UI['exact'].get(k)))
ok('shellroman_credit', 'ShellRoman' in APP and 'ShellRoman' in (ROOT/'LICENSE_ATTRIBUTION_KO.md').read_text(encoding='utf-8'))
ok('file_audio_only', "filter(x=>x.source_type==='file')" in APP and "source_type='file'" in SERVER and 'legacy-sound' not in APP)
# Native dialogs must go through translation wrappers.
raw_confirm=[m.start() for m in re.finditer(r'(?<![.\w])confirm\(',APP)]
raw_prompt=[m.start() for m in re.finditer(r'(?<![.\w])prompt\(',APP)]
ok('no_raw_confirm',not raw_confirm,raw_confirm[:10]); ok('no_raw_prompt',not raw_prompt,raw_prompt[:10])
ok('confirm_wrapper','function confirmUi(msg){return window.confirm(translateUiText(msg));}' in APP)
ok('prompt_wrapper',"function promptUi(msg,value=''){return window.prompt(translateUiText(msg),value);}" in APP)

# Screenshot/GM-tab natural English naming is contextual, not singular dictionary fallbacks.
for text in ['Players','Classes','Races','Basic Moves','Spells','Expansion Classes','NPCs','Monsters','Rules','Play Log']:
 ok('gm_tab_'+text,text in APP,text)

# User-facing terminology must stay unified. Internal migration/regex compatibility is excluded.
forbidden=['보정치','액션','마스터','데이터팩','인연 / 관계','기초 행동 묶음','직업행동','발수(ammo)','공통 행동']
ui_sources='\n'.join([APP,(ROOT/'static/index.html').read_text(encoding='utf-8'),(ROOT/'tools/i18n_ui_extra_en.json').read_text(encoding='utf-8')])
for term in forbidden: ok('term_'+term,term not in ui_sources,term)
ok('server_log_basic_move_name','공통 행동 저장' not in SERVER and '공통 행동 삭제' not in SERVER)

# Every static Korean HTTPException detail needs an English exact mapping. Dynamic f-strings are covered by patterns.
tree=ast.parse(SERVER)
static_http=[]
for n in ast.walk(tree):
 if isinstance(n,ast.Call) and ((isinstance(n.func,ast.Name) and n.func.id=='HTTPException') or (isinstance(n.func,ast.Attribute) and n.func.attr=='HTTPException')):
  vals=[]
  if len(n.args)>=2: vals.append(n.args[1])
  vals += [kw.value for kw in n.keywords if kw.arg=='detail']
  for v in vals:
   if isinstance(v,ast.Constant) and isinstance(v.value,str) and re.search('[가-힣]',v.value): static_http.append(v.value)
for msg in sorted(set(static_http)):
 ok('http_'+msg,msg in UI['exact'],repr(UI['exact'].get(msg)))

# Launcher language toggle is in-place and all key headings are present in the lexicon.
ok('launcher_no_language_reload',"$('#language').onclick=()=>{LANG=LANG==='en'?'ko':'en';localStorage.setItem(LKEY,LANG);localizeLauncher(document.body)}" in LAUNCHER)
ok('launcher_join_player',"'플레이어 참가':'Join as Player'" in LAUNCHER)
for ko in ['호스트 · GM','플레이어 참가','LAN에서 찾기','새 캠페인 참가','데이터 관리','런처 상태','로컬 LAN','네트워크']:
 ok('launcher_lex_'+ko,re.search(re.escape("'"+ko+"':"),LAUNCHER) is not None,ko)

# English session-expiry page and imported-name display handling.
ok('expired_session_bilingual',"Connection Expired" in SERVER and "접속 티켓이 만료되었습니다." in SERVER)
ok('imported_name_display','(Imported)' in APP and '가져옴' in APP)

if fail:
 print(f'FAIL {len(fail)} / PASS {passed}')
 for x in fail[:120]: print(' -',x)
 sys.exit(1)
print(f'PASS {passed}')
