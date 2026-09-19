#!/usr/bin/env python3
"""Build English display catalog for canonical Korean built-in data.

The game keeps canonical campaign data untouched. This catalog is display-only:
exact Korean seed strings map to English source-aligned text. Custom/edited text that
no longer matches the seed is deliberately left as authored.
"""
from __future__ import annotations
import json,re
from functools import lru_cache
from pathlib import Path
import fitz

ROOT=Path(__file__).resolve().parents[1]
SEED=json.loads((ROOT/'data/seed_data.json').read_text(encoding='utf-8'))
MONSTERS=json.loads((ROOT/'data/monster_seed.json').read_text(encoding='utf-8'))
PDF_PATH=Path('/mnt/data/dw_refs/Dungeon_World_Play_Sheets.pdf')
PDF=fitz.open(PDF_PATH) if PDF_PATH.exists() else None

# Keep the checked-in exact catalog as a release-safe baseline.  The optional
# reference PDF is a developer aid used to refresh source-aligned wording, but a
# clean release build must not lose translations merely because that external PDF
# is not present on the build machine.  New/changed canonical Korean strings are
# still caught by the unmapped scan at the end of this script.
CATALOG_PATH = ROOT/'static/i18n_content_en.json'
try:
    _existing_catalog = json.loads(CATALOG_PATH.read_text(encoding='utf-8')) if CATALOG_PATH.exists() else {}
except (OSError, json.JSONDecodeError):
    _existing_catalog = {}
M: dict[str,str] = dict(_existing_catalog.get('map') or {})

def add(ko,en):
    if isinstance(ko,str) and ko and isinstance(en,str) and en:
        M[ko]=en

@lru_cache(None)
def page_lines(pno:int):
    if PDF is None: return []
    p=PDF[pno-1]; out=[]
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines',[]):
            spans=sorted(l.get('spans',[]), key=lambda s:s['bbox'][0])
            if not spans: continue
            txt=''.join(s['text'] for s in spans).replace('\xa0',' ').strip()
            if not txt: continue
            out.append({'x':min(s['bbox'][0] for s in spans),'y':min(s['bbox'][1] for s in spans),'x1':max(s['bbox'][2] for s in spans),'y1':max(s['bbox'][3] for s in spans),'text':txt,'spans':spans})
    return sorted(out,key=lambda z:(z['y'],z['x']))

@lru_cache(None)
def title_lines(pno:int):
    out=[]
    for l in page_lines(pno):
        if any(('Bold' in s['font'] or 'Black' in s['font']) and 9.5<=s['size']<=10.5 for s in l['spans']) and max(s['size'] for s in l['spans'])<=10.6:
            out.append(l)
    return out

@lru_cache(None)
def centers(pno:int):
    xs=sorted(t['x'] for t in title_lines(pno)); groups=[]
    for x in xs:
        if not groups or abs(x-sum(groups[-1])/len(groups[-1]))>35: groups.append([x])
        else: groups[-1].append(x)
    return [sum(g)/len(g) for g in groups]

def clean_lines(raw:list[str]) -> str:
    texts=[]
    for t in raw:
        t=re.sub(r'\s+',' ',t.replace('\xa0',' ').strip())
        if t:texts.append(t)
    out=[]; cur=''
    for t in texts:
        bullet=t.startswith('•')
        if bullet:
            if cur: out.append(cur.strip()); cur=''
            out.append(t)
        else:
            if out and out[-1].startswith('•') and not re.search(r'[.!?]$',out[-1]):
                out[-1]+=' '+t
            elif cur:
                if cur.endswith('-') and t and t[0].islower(): cur=cur[:-1]+t
                else: cur+=' '+t
            else: cur=t
    if cur:out.append(cur.strip())
    return '\n'.join(out)

def extract(pno:int,title:str)->str:
    if PDF is None: return ''
    ls=page_lines(pno); ts=title_lines(pno)
    target=next((t for t in ts if t['text']==title),None); split=None
    if not target:
        for t in ts:
            if title.startswith(t['text']) and len(t['text'])>8:
                cand=[u for u in ts if abs(u['x']-t['x'])<5 and 0<u['y']-t['y']<14]
                if cand and (t['text']+' '+cand[0]['text'])==title:
                    target=t;split=cand[0];break
    if not target: return ''
    cs=centers(pno); c=min(cs,key=lambda x:abs(x-target['x'])); idx=cs.index(c)
    # Play-sheet class pages place starting gear in a narrow column to the left
    # of the first advanced-move column.  Treat the title x-position as the
    # beginning of that text column so gear lines cannot bleed into move text.
    lo=(c-30) if idx==0 else (cs[idx-1]+c)/2
    hi=1e9 if idx==len(cs)-1 else (c+cs[idx+1])/2
    y0=(split['y1'] if split else target['y1'])+.1
    same=[]
    for u in ts:
        uc=min(cs,key=lambda x:abs(x-u['x']))
        if abs(uc-c)<1 and u['y']>target['y']+(13 if split else .5): same.append(u)
    yend=min([u['y'] for u in same],default=790)
    # The 2–5 and 6–10 move groups are separated by an ordinary text line,
    # not a bold title.  Without this boundary the last move in a group absorbs
    # the next group's heading.
    if 8 <= pno <= 27:
        section_breaks=[l['y'] for l in ls if l['y']>y0 and lo<=l['x']<hi and l['text'].startswith('When you gain a level from ')]
        if section_breaks:
            yend=min(yend,min(section_breaks))
    raw=[]
    for l in ls:
        if l['y']<y0 or l['y']>=yend: continue
        if not (lo<=l['x']<hi): continue
        if max(s['size'] for s in l['spans'])>9.2: continue
        raw.append(l['text'])
    return clean_lines(raw)

class_names={'도적':'Thief','마법사':'Wizard','사냥꾼':'Ranger','사제':'Cleric','성기사':'Paladin','드루이드':'Druid','음유시인':'Bard','전사':'Fighter'}
for k,v in class_names.items(): add(k,v)
for k,v in {'선':'Good','중립':'Neutral','악':'Evil','혼돈':'Chaotic','질서':'Lawful','인간':'Human','엘프':'Elf','드워프':'Dwarf','하플링':'Halfling','간편':'Cantrip','암송':'Rote','미분류':'Unclassified','탄약':'Ammo'}.items(): add(k,v)

core_map={
'접근전':'Hack and Slash','사격':'Volley','위험 돌파':'Defy Danger','방어':'Defend','지식 더듬기':'Spout Lore','상황 파악':'Discern Realities','협상':'Parley','협조 또는 방해':'Aid or Interfere','황천길':'Last Breath','짐':'Encumbrance','야영':'Make Camp','파수':'Take Watch','험난한 여정':'Undertake a Perilous Journey','레벨업':'Level Up','축하연':'Carouse','세션 종료':'End of Session','보급':'Supply','회복':'Recover','구인':'Recruit','악명':'Outstanding Warrants','수련':'Bolster'}
core_pages={'Hack and Slash':2,'Volley':2,'Defy Danger':2,'Defend':2,'Spout Lore':2,'Discern Realities':2,'Parley':2,'Aid or Interfere':2,'Last Breath':3,'Encumbrance':3,'Make Camp':3,'Take Watch':3,'Undertake a Perilous Journey':3,'End of Session':3,'Level Up':3,'Outstanding Warrants':3,'Carouse':3,'Supply':3,'Recover':3,'Recruit':3,'Bolster':3}
for item in SEED['core']:
    en=core_map.get(item['name']);
    if en:
        add(item['name'],en)
        desc=extract(core_pages[en],en)
        if desc:add(item.get('desc',''),desc)

move_map={
'덫 전문가':'Trap Expert','프로의 솜씨':'Tricks Of The Trade','암습':'Backstab','희박한 도덕관념':'Flexible Morals','독의 기술':'Poisoner','급소 가격':'Cheap Shot','신중함':'Cautious','부와 교양':'Wealth And Taste','선수필승':'Shoot First','독의 달인':'Poison Master','독칼':'Envenom','독제사':'Brewer','오기':'Underdog','연줄':'Connections','치사한 수법':'Dirty Fighter','극도로 신중함':'Extremely Cautious','독학박사':'Alchemist','투지':'Serious Underdog','위험 초월':'Evasion','철완의 투척':'Strong Arm, True Aim','탈출로':'Escape Route','변장':'Disguise','대도적':'Heist',
'주문서':'Spellbook','주문 준비':'Prepare Spells','주문 시전':'Cast A Spell','주문 방어':'Spell Defense','마법 의식':'Ritual','천재':'Prodigy','주문 강화':'Empowered Magic','지식의 샘':'Fount Of Knowledge','만물박사':'Know-It-All','증보':'Expanded Spellbook','물품 분석':'Enchanter','논리적':'Logical','마력의 방패':'Arcane Ward','주문 차단':'Counterspell','주문 추리':'Quick Study','대가':'Master','상급 주문 강화':'Greater Empowered Magic','물품 강화':'Enchanter’s Soul','매우 논리적':'Highly Logical','마력의 갑옷':'Arcane Armor','마법 차폐':'Protective Counter','에테르의 끈':'Ethereal Tether','꼭두각시':'Mystical Puppet Strings','주문 접지':'Spell Augmentation','마력 응집':'Self-Powered',
'사냥과 추적':'Hunt & Track','정조준':'Called Shot','동물친구':'Animal Companion','명령':'Command','하프엘프':'Half-elven','야성의 교감':'Wild Empathy','익숙한 사냥감':'Familiar Prey','독사의 일격':'Viper’s Strike','위장술':'Camouflage','이러면 안전하오':'A Safe Place','헌신적인 친구':'Man’s Best Friend','태양을 가리리라':'Blot Out The Sun','재주꾼':'Well-trained','황무지의 신':'God Amidst The Wastes','여행길의 친구':'Follow Me','야성의 언어':'Wild Speech','사냥의 지식':'Hunter’s Prey','독사의 이빨':'Viper’s Fangs','약점 공략':'Smaug’s Belly','여행길의 스승':'Strider','이러면 더 안전하오':'A Safer Place','관찰력':'Observant','특별한 재주':'Special Trick','괴물 친구':'Unnatural Ally',
'신':'Deity','탄원':'Divine Guidance','예배':'Commune','언데드 퇴치':'Turn Undead','선택 받은 자':'Chosen One','활력':'Invigorate','생사의 저울':'The Scales Of Life And Death','평정':'Serenity','응급처치':'First Aid','신의 보우':'Divine Intervention','속죄':'Penitent','이끌어 주십시오':'Orison For Guidance','믿음의 갑옷':'Divine Protection','치유의 달인':'Devoted Healer','기름으로 바른 자':'Anointed','신격':'Apotheosis','장례':'Reaper','은총':'Providence','상급 응급처치':'Greater First Aid','신의 가호':'Divine Invincibility','회개':'Martyr','믿음의 보루':'Divine Armor',
'안수치료':'Lay On Hands','갑옷을 옷처럼':'Armored','내가 법이다':'I Am The Law','신성한 임무':'Quest','신의 은혜':'Divine Favor','피의 보루':'Bloody Aegis','의로운 분노':'Smite','척살':'Exterminatus','돌격!':'Charge!','견고한 방어':'Staunch Defender','연계 공격':'Setup Strike','정의의 갑옷':'Holy Protection','권위의 음성':'Voice Of Authority','치료사':'Hospitaller','신앙의 증거':'Evidence Of Faith','거룩한 분노':'Holy Smite','끝없는 전진':'Ever Onward','무적의 방어':'Impervious Defender','협공':'Tandem Strike','신의 갑옷':'Divine Protection','천상의 권위':'Divine Authority','치료사의 모범':'Perfect Hospitaller','불굴':'Indomitable','기사의 귀감':'Perfect Knight',
'대지의 아들/딸':'Born Of The Soil','자연의 보살핌':'By Nature Sustained','신령어':'Spirit Tongue','변신':'Shapeshifter','본질의 연구':'Studied Essence','사냥꾼의 형제':'Hunter’s Brother','피 묻은 이빨과 발톱':'Red Of Tooth And Claw','신령의 속삭임':'Communion Of Whispers','나무껍질':'Barkskin','호랑이의 눈':'Eyes Of The Tiger','허물 벗기':'Shed','목석과의 대화':'Thing-talker','변신의 명수':'Formcrafter','원소의 주인':'Elemental Mastery','조화':'Balance','형태의 자유':'Embracing No Form','흉내':'Doppleganger’s Dance','피와 천둥':'Blood And Thunder','드루이드의 잠':'The Druid Sleep','만물과의 대화':'World-talker','숲사람의 자매':'Stalker’s Sister','변신의 달인':'Formshaper','합성수':'Chimera','날씨 짜기':'Weather Weaver',
'마법의 곡조':'Arcane Art','시인의 학식':'Bardic Lore','진솔한 대화':'Charming & Open','추억의 거리':'A Port In The Storm','치유의 노래':'Healing Song','날카로운 불협화음':'Vicious Cacophony','이건 11까지 올라가지':'It Goes To Eleven','쇳소리':'Metal Hurlant','오는 정 가는 정':'A Little Help From My Friends','이계의 음률':'Eldritch Tones','결투사의 호신술':'Duelist’s Parry','현란한 말솜씨':'Bamboozle','치유의 합창':'Healing Chorus','날카로운 폭발음':'Vicious Blast','잊지 못할 얼굴':'Unforgettable Face','유명인':'Reputation','이계의 화음':'Eldritch Chord','마법을 듣는 귀':'An Ear For Magic','교활':'Devious','결투사의 호신비결':'Duelist’s Block','청산유수':'Con',
'창살을 굽히고 문을 들어올린다':'Bend Bars, Lift Gates','고유병기':'Signature Weapon','무자비':'Merciless','병기의 영':'Heirloom','방어의 요령':'Armor Mastery','무기 강화':'Improved Weapon','전사의 눈':'Seeing Red','협박':'Interrogator','피의 향기':'Scent Of Blood','무쇠의 몸':'Iron Hide','대장장이':'Blacksmith','살기등등':'Bloodthirsty','방어의 비법':'Armored Perfection','압도적인 시선':'Evil Eye','피의 맛':'Taste Of Blood','강철의 몸':'Steel Hide','죽음의 예감':'Through Death’s Eyes','무기 감정':'Eye For Weaponry','전쟁의 화신':'Superior Warrior'}
class_pages={'음유시인':(8,9),'사제':(10,11),'드루이드':(14,15),'전사':(16,17),'성기사':(20,21),'사냥꾼':(22,23),'도적':(24,25),'마법사':(26,27)}
for cname,c in SEED['classes'].items():
    startp,advp=class_pages[cname]
    for sec in ('start','a25','a610'):
        for mv in c.get(sec,[]):
            en=move_map.get(mv['name'])
            if not en: continue
            add(mv['name'],en)
            lookup=en
            if mv['name']=='주문 시전': lookup='Cast A Spell (INT)' if cname=='마법사' else 'Cast A Spell (WIS)'
            if mv['name']=='안수치료': lookup='Lay On Hands (CHA)'
            if mv['name']=='사냥과 추적': lookup='Hunt & Track (WIS)'
            desc=extract(startp if sec=='start' else advp,lookup)
            if desc:add(mv.get('desc',''),desc)

spell_map={'빛':'Light','보이지 않는 하인':'Unseen Servant','소마법':'Prestidigitation','혼령소환':'Contact Spirits','마법 탐지':'Detect Magic','마음의 대화':'Telepathy','매혹':'Charm Person','투명화':'Invisibility','마탄':'Magic Missile','경보':'Alarm','마법 해제':'Dispel magic','미래를 보는 눈':'Visions Through Time','화염탄':'Fireball','둔갑':'Mimic','환영 분신':'Mirror Image','수면':'Sleep','마력의 우리':'Cage','이계 접촉':'Contact Other Plane','강제 변신':'Polymorph','괴물소환':'Summon Monster','정신 조종':'Dominate','진실의 눈':'True Seeing','그림자 문':'Shadow Walk','대기 주문':'Contingency','죽음의 안개':'Cloudkill','기피':'Antipathy','소식':'Alert','영혼석':'Soul Gem','마법의 요새':'Shelter','대소환':'Perfect Summons','축성':'Sanctify','인도':'Guidance','축복':'Bless','소치유':'Cure Light Wounds','가치관 탐지':'Detect Alignment','망자와의 대화':'Speak With Dead','공포 유발':'Cause Fear','무기 축성':'Magic Weapon','안식처':'Sanctuary','시체 각성':'Animate Dead','치유':'Cure Moderate Wounds','암흑':'Darkness','부활':'Resurrection','포박':'Hold Person','계시':'Revelation','대치유':'Cure Critical Wounds','신탁':'Divination','감염':'Contagion','목석의 말':'Words Of The Unspeaking','영혼 포획':'Trap Soul','귀환의 진언':'Word Of Recall','완치':'Heal','천벌':'Harm','절단':'Sever','죽음의 룬':'Mark Of Death','날씨 조종':'Control Weather','진노의 폭풍':'Storm Of Vengeance','돌이킴':'Repair','신의 위세':'Divine Presence','언데드 흡수':'Consume Unlife','역병':'Plague','목석의 말 · 돌':'Words Of The Unspeaking · Stone'}
cleric12={'Light','Sanctify','Guidance','Bless','Cure Light Wounds','Detect Alignment','Speak With Dead','Cause Fear','Magic Weapon','Sanctuary','Animate Dead','Cure Moderate Wounds','Darkness','Resurrection','Hold Person'}
cleric13=set(spell_map.values())-cleric12
wizard28={'Light','Unseen Servant','Prestidigitation','Contact Spirits','Detect Magic','Telepathy','Charm Person','Invisibility','Magic Missile','Alarm','Dispel magic','Visions Through Time','Fireball','Mimic','Mirror Image','Sleep'}
for cls,spells in SEED['spells'].items():
    for sp in spells:
        en=spell_map.get(sp['name']);
        if not en: continue
        add(sp['name'],en)
        pno=None
        if cls=='마법사': pno=28 if en in wizard28 else 29
        elif cls=='사제': pno=12 if en in cleric12 else 13
        elif cls=='__undefined__': pno=13
        lookup='Words Of The Unspeaking' if en=='Words Of The Unspeaking · Stone' else en
        desc=extract(pno,lookup) if pno else ''
        if desc:
            # Level/category/school are rendered by the spell UI already. Keep only
            # the original rules text so the same Korean description cannot pick
            # up a different class label (for example Light: Cantrip vs Rote).
            desc=re.sub(r'^(?:Cantrip|Rote|\d+(?:st|nd|rd|th) Level)\s+','',desc)
            desc=re.sub(r'^(?:Summoning|Divination|Enchantment|Illusion|Evocation)\s+','',desc)
            desc=re.sub(r'^\(ongoing\)\s+','',desc,flags=re.I)
            add(sp.get('desc',''),desc)

# Source-aligned race and alignment descriptions from the official play sheets.
for cname,c in SEED['classes'].items():
    pno=class_pages[cname][0]
    for r in c.get('races',[]):
        en_name={'인간':'Human','엘프':'Elf','드워프':'Dwarf','하플링':'Halfling'}.get(r['name'])
        if en_name:
            desc=extract(pno,en_name)
            if desc:add(r.get('desc',''),desc)
    for a in c.get('alignments',[]):
        en_name={'선':'Good','중립':'Neutral','악':'Evil','혼돈':'Chaotic','질서':'Lawful'}.get(a['name'])
        if en_name:
            desc=extract(pno,en_name)
            if desc:add(a.get('desc',''),desc)

# Bonds: exact English play-sheet wording, aligned to each canonical Korean seed line.
bond_en={
'도적':['I stole something from ________.','________ has my back when things go wrong.','________ knows incriminating details about me.','________ and I have a con running.'],
'마법사':['________ will play an important role in the events to come. I have foreseen it!','________ is keeping an important secret from me.','________ is woefully misinformed about the world; I will teach them all that I can.'],
'사냥꾼':['I have guided ________ before and they owe me for it.','________ is a friend of nature, so I will be their friend as well.','________ has no respect for nature, so I have no respect for them.','________ does not understand life in the wild, so I will teach them.'],
'사제':['________ has insulted my deity; I do not trust them.','________ is a good and faithful person; I trust them implicitly.','________ is in constant danger, I will keep them safe.','I am working on converting ________ to my faith.'],
'성기사':['________’s misguided behavior endangers their very soul!','________ has stood by me in battle and can be trusted completely.','I respect the beliefs of ________ but hope they will someday see the true way.','________ is a brave soul, I have much to learn from them.'],
'드루이드':['________ smells more like prey than a hunter.','The spirits spoke to me of a great danger that follows ________.','I have showed ________ a secret rite of the Land.','________ has tasted my blood and I theirs. We are bound by it.'],
'음유시인':['This is not my first adventure with ________.','I sang stories of ________ long before I ever met them in person.','________ is often the butt of my jokes.','I am writing a ballad about the adventures of ________.','________ trusted me with a secret.','________ does not trust me, and for good reason.'],
'전사':['________ owes me their life, whether they admit it or not.','I have sworn to protect ________.','I worry about the ability of ________ to survive in the dungeon.','________ is soft, but I will make them hard like me.']}
for cname,c in SEED['classes'].items():
    for ko,en in zip(c.get('bonds',[]),bond_en[cname]): add(ko,en)

gear_en={
'도적':'''[Starting Gear — Thief]\nMax Load: 9 + STR\n\nStarting gear\n• Dungeon Rations (5 uses)\n• Leather Armor (1 armor)\n• 3 uses of your chosen poison\n• 10 Coin\n\nArms — choose one\n• Dagger + Short Sword\n• Rapier\n\nRanged weapon — choose one\n• 3 Throwing Daggers\n• Ragged Bow + Bundle of Arrows\n\nAdditional gear — choose one\n• Adventuring Gear (5 uses)\n• Healing Potion''',
'마법사':'''[Starting Gear — Wizard]\nMax Load: 7 + STR\n\nStarting gear\n• Spellbook\n• Dungeon Rations (5 uses)\n\nDefenses — choose one\n• Leather Armor (1 armor)\n• Bag of Books (5 uses) + 3 Healing Potions\n\nWeapon — choose one\n• Dagger\n• Staff (two-handed)\n\nAdditional gear — choose one\n• Healing Potion\n• 3 Antitoxin''',
'사냥꾼':'''[Starting Gear — Ranger]\nMax Load: 11 + STR\n\nStarting gear\n• Adventuring Gear (5 uses)\n• Dungeon Rations (5 uses)\n• Leather Armor (1 armor)\n• Bundle of Arrows (3 ammo)\n\nWeapon — choose one\n• Hunter’s Bow + Short Sword\n• Hunter’s Bow + Spear\n\nAdditional gear — choose one\n• Dungeon Rations (5 uses)\n• Bundle of Arrows (3 ammo)''',
'사제':'''[Starting Gear — Cleric]\nMax Load: 10 + STR\n\nStarting gear\n• Dungeon Rations (5 uses)\n• A symbol of your deity\n\nDefenses — choose one\n• Chainmail (1 armor)\n• Shield (+1 armor)\n\nWeapon — choose one\n• Warhammer\n• Mace\n• Staff (two-handed) + Bandages (3 uses)\n\nAdditional gear — choose one\n• Adventuring Gear (5 uses) + Dungeon Rations (5 uses)\n• Healing Potion''',
'성기사':'''[Starting Gear — Paladin]\nMax Load: 12 + STR\n\nStarting gear\n• Dungeon Rations (5 uses)\n• Scale Armor (2 armor)\n• A symbol of your deity\n\nWeapon — choose one\n• Halberd (two-handed, +1 damage)\n• Long Sword (+1 damage) + Shield (+1 armor)\n\nAdditional gear — choose one\n• Adventuring Gear (5 uses)\n• Healing Potion + Dungeon Rations (5 uses)''',
'드루이드':'''[Starting Gear — Druid]\nMax Load: 6 + STR\n\nDefenses — choose one\n• Hide Armor (1 armor)\n• Wooden Shield (+1 armor)\n\nWeapon — choose one\n• Shillelagh\n• Staff (two-handed)\n• Spear (thrown, near)\n\nAdditional gear — choose one\n• Adventuring Gear (5 uses)\n• Poultices and Herbs (2 uses)\n• Halfling Pipeleaf (6 uses)\n• 3 Antitoxin''',
'음유시인':'''[Starting Gear — Bard]\nMax Load: 9 + STR\n\nStarting gear\n• Dungeon Rations (5 uses)\n\nInstrument — choose one (0 weight for you)\n• Your father’s mandolin, repaired\n• A fine lute, a gift from a noble\n• The pipes with which you courted your first love\n• A stolen horn\n• A fiddle, never before played\n• A songbook in a forgotten tongue\n\nClothing — choose one\n• Leather Armor (1 armor)\n• Ostentatious Clothes\n\nWeapon — choose one\n• Dueling Rapier\n• Worn Bow + Bundle of Arrows + Short Sword\n\nAdditional gear — choose one\n• Adventuring Gear (5 uses)\n• Bandages (3 uses)\n• Halfling Pipeleaf (6 uses)\n• 3 Coin''',
'전사':'''[Starting Gear — Fighter]\nMax Load: 12 + STR\n\nStarting gear\n• Signature Weapon (2 weight)\n• Dungeon Rations (5 uses)\n\nDefenses — choose one\n• Chainmail (1 armor) + Adventuring Gear (5 uses)\n• Scale Armor (2 armor)\n\nAdditional gear — choose two\n• Poultices and Herbs (2 uses)\n• Antitoxin\n• Dungeon Rations (5 uses)\n• 2 Healing Potions\n• Shield (+1 armor)\n• 22 Coin'''}
for cname,c in SEED['classes'].items(): add(c.get('gear',''),gear_en[cname])

# Common rule/data terms found in built-in text.
terms={
'닢':'Coin','받은 주문':'Granted Spells','준비':'Prepared','근력':'Strength','민첩':'Dexterity','민첩성':'Dexterity','체력':'Constitution','지능':'Intelligence','지혜':'Wisdom','매력':'Charisma',
'반걸음':'hand','한걸음':'close','몇걸음':'reach','중거리':'near','장거리':'far','파괴적':'messy','강력':'forceful','관통':'piercing','정밀':'precise','느림':'slow','양손':'two-handed','착용':'worn','위험':'dangerous','발수':'ammo','장갑 무시':'ignores armor',
'대집단':'Horde','소집단':'Group','외톨이':'Solitary','소형':'Small','거대':'Huge','대형':'Large','은밀':'Stealthy','조직적':'Organized','지능적':'Intelligent','마법적':'Magical','끔찍함':'Terrifying','신중':'Cautious','인공물':'Construct','이계':'Planar','축재':'Hoarder','교활함':'Devious','비정형':'Amorphous'}
for k,v in terms.items():add(k,v)

# Expansion examples: English display translations use the known English concept/name where
# obvious and preserve every numeric/mechanical clause verbatim in meaning. The canonical
# Korean data stays authoritative; this catalog cannot alter game state.
exp_names={'암살자':'Assassin','전쟁군주':'Warlord','폭풍술사':'Stormcaller','병기 지배자':'Weapon Master','룬의 달인':'Runemaster','생존자':'Survivor','녹색 기사':'Green Knight','강령술사':'Necromancer','광전사':'Berserker','괴물 사냥꾼':'Monster Hunter','공허를 말하는 자':'Void Speaker'}
exp_move_names={
'죽음의 일격':'Death Strike','재에서 재로':'Ashes to Ashes','그림자 발걸음':'Shadow Step','행방불명':'Gone Without a Trace',
'전쟁 지도자':'War Leader','전선을 유지해':'Hold the Line','군주의 자질':'Warlord’s Bearing','전투 상징':'Banner of Battle',
'기상조작':'Weather Mastery','벼락술사':'Stormbolt','깃털처럼 가볍게':'Light as a Feather','세기의 폭풍':'Storm of the Century',
'칼날의 유대':'Bond of the Blade','룬 새기기':'Inscribe Rune','바위를 깎은 말':'Words Carved in Stone','영혼조각가':'Soul Carver','룬 통달':'Runic Mastery',
'잿더미를 딛고':'From the Ashes','멈출 수 없는 힘':'Unstoppable Force','움직일 수 없는 존재':'Immovable Object','나홀로 세상에 맞서서':'Alone Against the World',
'녹색의 선물':'The Green Gift','영혼 교감':'Spirit Communion','야생의 부름':'Call of the Wild','숲걸음':'Forest Walk',
'일어나라!':'Rise!','필멸을 넘어서':'Beyond Mortality','고기 방패':'Meat Shield','완벽한 조종':'Perfect Control',
'광전사의 분노':'Berserker Rage','야만적인 계략':'Savage Cunning','무시무시한 명성':'Terrible Reputation','파괴 본능':'Destructive Instinct',
'괴물 공략':'Study the Monster','괴물 백과':'Monster Lore','전리품 사냥꾼':'Trophy Hunter','괴물 학살자':'Monster Slayer',
'밤은 깊고 공포로 가득하노라':'The Night Is Dark and Full of Terrors','어둠 속의 칼날':'Blade in the Dark','장막 횡단':'Cross the Veil','굶주린 어둠':'Hungry Darkness'}
for k,v in exp_names.items():add(k,v)
for k,v in exp_move_names.items():add(k,v)
add('전설행동을 획득하면 직업 행동을 이어서 획득할 수 있는 확장직업입니다.','Once you gain the legendary move, you can continue by gaining this expansion class’s class moves.')
add('이 확장직업은 Unlimited Dungeons / Distant Shore Pack의 공개 예시를 바탕으로 정리한 자료입니다. 자세한 출처와 이용 조건은 도움말의 “라이선스와 출처”에서 확인하세요.','This expansion-class example is based on material from Unlimited Dungeons / Distant Shore Pack. See “License & Sources” in Help for attribution and reuse terms.')
add('이 확장직업은 Unlimited Dungeons / Distant Shore Pack의 공개 예시를 바탕으로 정리한 자료입니다. 자세한 출처와 이용 조건은 도움말의 “라이선스와 출처”에서 확인하세요. 원 자료에서는 이 확장직업이 Jacob Randolph의 저작물을 기반으로 한다고 별도 표시합니다.','This expansion-class example is based on material from Unlimited Dungeons / Distant Shore Pack. See “License & Sources” in Help for attribution and reuse terms. The source separately credits this expansion class as based on work by Jacob Randolph.')
# Natural English translations of the compact structured example text. Mechanics/numbers retained.
exp_desc={
'발동: 대상의 약점/접근법을 파악해 표적을 쌓고, 눈치채지 못한 대상에게 접근한다.\n\n판정: +표적\n\n성공: 성공하면 묘사한 방식으로 암살한다.\n\n12+: 3개 선택\n\n10+: 2개 선택\n\n7–9: 1개 선택\n\n6-: 암살 실패. 그 대상이 죽기 전까지 새 표적 획득 제한.\n\n선택지:\n• 경보 없이 처리\n• 최후의 저항 억제\n• 추적 증거 제거\n\n표적을 쌓아 치명적인 암살을 시도한다.':'Trigger: Study the target’s weakness or approach to build Target, then get close to an unaware target.\n\nRoll: +Target\n\nHit: On a hit, assassinate them in the way you described.\n\n12+: Choose 3\n\n10+: Choose 2\n\n7–9: Choose 1\n\n6-: The assassination fails. You cannot gain a new Target until this target dies.\n\nChoices:\n• Do it without raising an alarm\n• Prevent a final act of resistance\n• Leave no evidence to follow\n\nBuild Target and attempt a lethal assassination.',
'암살한 대상의 흔적을 소거한다.':'Erase the traces left by someone you assassinated.',
'발동: 그림자로 이동하거나 추적을 따돌린다.\n\n판정: +민첩\n\n10+: 2개 선택\n\n7–9: 1개 선택\n\n선택지:\n• 시야/추적 이탈\n• 빠른 도착\n• 추적 흔적 없음\n\n그림자를 이용해 은밀히 이동한다.':'Trigger: Move through shadows or shake off pursuit.\n\nRoll: +DEX\n\n10+: Choose 2\n\n7–9: Choose 1\n\nChoices:\n• Break line of sight / pursuit\n• Arrive quickly\n• Leave no trail\n\nUse the shadows to move unseen.',
'군중과 그림자 속에서 사라진다.':'Disappear into crowds and shadows.',
'발동: 용병대를 모집해 전투를 직접 지휘한다.\n\n판정: +매력\n\n10+: 예비 3\n\n7–9: 예비 2\n\n6-: 예비 1을 받을 수 있으나 전장이 크게 악화된다.\n\n선택지:\n• 공세\n• 방어\n• 질서 있는 퇴각\n• 위험 회피\n• 항복자 보호\n• 공포 억제\n• 전열 회복\n\n용병대를 모아 전투를 지휘한다.':'Trigger: Recruit a warband and personally command it in battle.\n\nRoll: +CHA\n\n10+: Hold 3\n\n7–9: Hold 2\n\n6-: You may take 1 hold, but the battlefield worsens dramatically.\n\nChoices:\n• Press the attack\n• Hold the defense\n• Make an orderly retreat\n• Avoid a danger\n• Protect those who surrender\n• Suppress fear\n• Restore the line\n\nGather a warband and command the battle.',
'지휘로 아군 전선을 안정시킨다.':'Use command to steady the allied line.',
'전쟁 지도자의 예비를 강화한다.':'Strengthen the hold generated by War Leader.',
'상징으로 주변 전우를 고무한다.':'Use your symbol to inspire nearby comrades.',
'발동: 탁 트인 하늘 아래에서 원하는 날씨 변화를 명령한다.\n\n판정: +지혜\n\n성공: 선택한 날씨 변화가 발생한다.\n\n7–9: 효과 약화/단기화 또는 원치 않는 부작용 중 1개.\n\n6-: 날씨가 혼란스럽고 기괴하게 변한다.\n\n선택지:\n• 짙은 안개\n• 혹한\n• 바람 방향/세기\n• 비 또는 눈\n\n날씨를 명령해 원하는 변화를 일으킨다.':'Trigger: Beneath an open sky, command the weather to change.\n\nRoll: +WIS\n\nHit: The chosen weather change occurs.\n\n7–9: Choose one: the effect is weaker or shorter-lived, or an unwanted side effect occurs.\n\n6-: The weather becomes chaotic and strange.\n\nChoices:\n• Dense fog\n• Bitter cold\n• Wind direction / strength\n• Rain or snow\n\nCommand the weather and bring about the change you want.',
'비와 번개를 공격에 활용한다.':'Turn rain and lightning into weapons.',
'강풍을 타고 이동한다.':'Ride strong winds to move.',
'강력한 초자연적 폭풍을 일으킨다.':'Call up a devastating supernatural storm.',
'발동: 세상에 하나뿐인 고유병기와 그 특별한 힘을 정한다.\n\n선택지:\n• 화염\n• 신성\n• 특정 적 파멸\n• 장갑 무시\n• 치유 방해\n• 초강력 절삭\n• 마법 파괴\n• 위험 감지\n\n세상에 하나뿐인 무기를 성장시킨다.\n\n고유병기는 욕구/목표를 가지며, 이를 만족시키면 추가 힘을 얻을 수 있다.':'Trigger: Define a one-of-a-kind signature weapon and its extraordinary powers.\n\nChoices:\n• Flame\n• Holy\n• Bane of a chosen foe\n• Ignores armor\n• Prevent healing\n• Supernatural cutting power\n• Break magic\n• Sense danger\n\nGrow a unique weapon unlike any other.\n\nThe signature weapon has desires or goals; satisfying them can awaken additional power.',
'병기와 인연을 맺어 피해를 강화한다.':'Forge a bond with the weapon and increase its damage.',
'발동: 고유병기의 영에게 현 상황의 관점을 묻는다.\n\n판정: +매력\n\n10+: 상세한 정보\n\n7–9: 대략적인 인상\n\n병기의 영에게 정보와 관점을 묻는다.':'Trigger: Ask the spirit of your signature weapon for its view of the current situation.\n\nRoll: +CHA\n\n10+: Detailed information\n\n7–9: A broad impression\n\nAsk the weapon’s spirit for information and perspective.',
'마법 무기의 힘을 고유병기에 옮긴다.':'Transfer the power of a magic weapon into your signature weapon.',
'발동: 알고 있는 룬을 물건에 새기고 원하는 효과를 설명한다.\n\n판정: +지능\n\n10+: 3항목 중 2개\n\n7–9: 3항목 중 1개\n\n6-: 대상이 저주받는다.\n\n선택지:\n• 지속성\n• 부작용 없음\n• 발동 제한 없음\n\n룬으로 사물에 마법 효과를 부여한다.\n\n기본적으로 유지 가능한 룬은 하나. 룬이 새겨진 물건은 최소 무게 1.':'Trigger: Inscribe a rune you know onto an object and describe the effect you want.\n\nRoll: +INT\n\n10+: Choose 2 of 3\n\n7–9: Choose 1 of 3\n\n6-: The subject is cursed.\n\nChoices:\n• Lasting\n• No side effects\n• No restriction on activation\n\nUse runes to give objects magical effects.\n\nBy default you can maintain one rune. An item bearing a rune has at least 1 weight.',
'새긴 룬을 훨씬 오래 유지한다.':'Make your inscribed runes last much longer.',
'살아있는 대상에게도 룬을 새긴다.':'Inscribe runes on living subjects as well.',
'탁월한 룬 새기기로 효과를 완성한다.':'Perfect the effect through masterful rune inscription.',
'발동: 대재앙의 흔적 2개를 선택하고 고통을 자원으로 사용한다.\n\n선택지:\n• 위험 감지 흉터\n• 피해 반격 서약\n• 괴력의 손\n• 고통 극복\n• 정신 지배 저항\n• 황천길 강화\n• 장갑 +1\n\n시련의 흔적과 고통을 힘으로 삼는다.\n\n새 생존자 직업 행동을 얻을 때 고통 +1. 고통 1을 써서 고통스러운 피해를 무시하고 새 흔적을 적용할 수 있다.':'Trigger: Choose 2 marks left by catastrophe and use Pain as a resource.\n\nChoices:\n• Scar that senses danger\n• Vow of retaliation\n• Hand of impossible strength\n• Overcome pain\n• Resist mind control\n• Stronger Last Breath\n• +1 armor\n\nTurn the marks of hardship and your pain into strength.\n\nGain +1 Pain when you gain a new Survivor class move. Spend 1 Pain to ignore painful harm and take on a new mark.',
'발동: 쇠약·질병·속박·괴롭힘을 견딘다.\n\n판정: +체력\n\n10+: 예비 3\n\n7–9: 예비 2\n\n6-: 예비 1 가능 + 이후 상태 악화\n\n쇠약과 속박을 버텨낸다.':'Trigger: Endure debility, disease, restraint, or torment.\n\nRoll: +CON\n\n10+: Hold 3\n\n7–9: Hold 2\n\n6-: You may take 1 hold, and your condition worsens afterward.\n\nEndure weakness and restraint.',
'방어와 버티기를 강화한다.':'Become better at defending and holding your ground.',
'발동: 막대한 위협에 홀로 맞선다.\n\n판정: +체력\n\n10+: 피해를 감수하고 위협을 몰아낸다.\n\n7–9: 위협을 몰아내지만 지울 수 없는 상처.\n\n6-: 황천길.\n\n거대한 위협에 홀로 맞선다.':'Trigger: Face an overwhelming threat alone.\n\nRoll: +CON\n\n10+: Suffer the harm and drive the threat back.\n\n7–9: Drive it back, but take a lasting scar.\n\n6-: Last Breath.\n\nStand alone against an overwhelming threat.',
'발동: 나무에 손을 대고 숲에 도움을 요청한다.\n\n판정: +지혜\n\n성공: 숲이 가능한 도움을 주고 대가를 요구한다.\n\n10+: 3개 모두\n\n7–9: 3개 중 2개\n\n선택지:\n• 즉시 도움\n• 일행도 혜택\n• 효과 장기 지속\n\n숲에게 도움을 요청하고 대가를 치른다.\n\n미해결된 숲의 부탁이 있으면 녹색 기사 행동에 불리.':'Trigger: Touch a tree and ask the forest for aid.\n\nRoll: +WIS\n\nHit: The forest gives whatever help it can and asks a price.\n\n10+: All 3\n\n7–9: Choose 2 of 3\n\nChoices:\n• Help comes immediately\n• Your companions benefit too\n• The effect lasts a long time\n\nAsk the forest for aid and pay its price.\n\nIf you still owe the forest an unresolved favor, you are disadvantaged on Green Knight moves.',
'발동: 동물을 만져 기억과 생각을 읽는다.\n\n판정: +지혜\n\n성공: 동물의 과거 기억/생각을 읽는다.\n\n7–9: 연결 후 잠시 동물의 습성이 남는다.\n\n동물과 대화하고 기억을 읽는다.':'Trigger: Touch an animal and read its memories and thoughts.\n\nRoll: +WIS\n\nHit: Read the animal’s past memories or thoughts.\n\n7–9: After the connection ends, some of the animal’s habits linger in you for a while.\n\nSpeak with animals and read their memories.',
'발동: 원하는 종류의 동물을 지정 장소로 부른다.\n\n판정: +지혜\n\n성공: 동물들이 모인다.\n\n7–9: 지연/장소 오차/의도치 않은 동물 중 1개.\n\n원하는 동물들을 불러 모은다.':'Trigger: Call a chosen kind of animal to a place you name.\n\nRoll: +WIS\n\nHit: The animals gather.\n\n7–9: Choose one: delay, they gather in the wrong place, or unwanted animals come as well.\n\nCall the animals you want to you.',
'발동: 큰 나무를 통해 같은 종류의 나무가 있는 장소로 이동한다.\n\n판정: +지혜\n\n성공: 목적지로 이동.\n\n10+: 동행/유리한 출현/대가 없음 중 1개.\n\n나무를 통해 먼 곳으로 이동한다.':'Trigger: Step through a great tree to a place where the same kind of tree grows.\n\nRoll: +WIS\n\nHit: Travel to the destination.\n\n10+: Choose one: bring companions, arrive in an advantageous position, or pay no price.\n\nTravel great distances through trees.',
'발동: 시신/신체 조각에 의식을 행해 언데드 하수인을 만든다.\n\n판정: +지능\n\n10+: 결점 1개\n\n7–9: 결점 2개\n\n6-: 결점 3개\n\n선택지:\n• 좋지 않은 본능\n• 지속 공급 필요\n• 복잡한 명령 이해 불가\n\n시신을 언데드 하수인으로 일으킨다.\n\n기본 하수인: HP 6, 피해 D6, 기량 +0, 언데드 태그, 고유 행동 1개.':'Trigger: Perform a rite over a corpse or body part to make an undead minion.\n\nRoll: +INT\n\n10+: 1 flaw\n\n7–9: 2 flaws\n\n6-: 3 flaws\n\nChoices:\n• A troublesome instinct\n• Requires an ongoing supply\n• Cannot understand complex commands\n\nRaise a corpse as an undead minion.\n\nBasic minion: HP 6, damage D6, skill +0, undead tag, 1 unique move.',
'언데드 하수인에게 능력을 부여한다.':'Grant new abilities to an undead minion.',
'하수인이 공격을 대신 받게 한다.':'Have a minion take an attack in your place.',
'언데드 하수인을 직접 조종한다.':'Take direct control of an undead minion.',
'발동: 극도로 폭력적인 광란에 들어간다.\n\n판정: +체력\n\n10+: 3개 선택\n\n7–9: 2개 선택\n\n6-: 1개 선택 + 심각한 부수 피해\n\n선택지:\n• 근접 파괴적/괴력\n• 공포·정신조종 면역\n• 장갑 3\n• 약화 무시\n• 종료 후 피로 없음\n\n광란에 들어가 전투 능력을 끌어올린다.':'Trigger: Enter an extremely violent battle frenzy.\n\nRoll: +CON\n\n10+: Choose 3\n\n7–9: Choose 2\n\n6-: Choose 1 and cause serious collateral damage.\n\nChoices:\n• Messy / mighty in melee\n• Immune to fear and mind control\n• Armor 3\n• Ignore debilities\n• No exhaustion when the rage ends\n\nEnter a frenzy and push your combat ability to its limit.',
'분노 중 상황 파악 방식을 바꾼다.':'Change how you Discern Realities while raging.',
'광란의 소문이 먼저 퍼져나간다.':'Let the stories of your rages arrive before you do.',
'공격 성공 시 파괴를 더한다.':'Add destruction when your attacks hit.',
'발동: 괴물을 잠시 주의 깊게 관찰하고 질문 하나를 고른다.\n\n판정: +지능\n\n성공: 관찰 가능한 범위에서 답을 얻는다.\n\n7–9: 답 전에 필요한 행동/조건이 생긴다.\n\n6-: 불리한 답 또는 매우 어려운 선행 조건.\n\n선택지:\n• 괴물의 강함\n• 특별한 능력\n• 통하지 않는 공격\n\n괴물을 관찰해 능력과 방어를 파악한다.':'Trigger: Carefully observe a monster for a moment and choose one question.\n\nRoll: +INT\n\nHit: Learn the answer insofar as it can be observed.\n\n7–9: There is something you must do or a condition you must meet before getting the answer.\n\n6-: The answer is unfavorable or requires an extremely difficult prerequisite.\n\nQuestions:\n• What makes the monster strong?\n• What special ability does it have?\n• What kind of attack will not work?\n\nObserve a monster to learn its abilities and defenses.',
'괴물의 약점까지 알아낸다.':'Learn a monster’s weaknesses as well.',
'발동: 관찰한 괴물의 전리품에서 영혼의 힘을 불러낸다.\n\n판정: +체력\n\n성공: 전리품에 대응하는 비마법 행동 사용.\n\n7–9: 사용 후 전리품 파괴.\n\n전리품에서 괴물의 힘을 끌어낸다.':'Trigger: Draw out the spirit-power of a monster from a trophy you took from it.\n\nRoll: +CON\n\nHit: Use a non-magical move corresponding to the trophy.\n\n7–9: The trophy is destroyed after use.\n\nDraw a monster’s power out of its trophy.',
'피를 본 대상을 끝까지 추적한다.':'Once you have drawn a target’s blood, track it relentlessly.',
'발동: 넓은 영역을 마법적 어둠으로 채우고 그 안의 존재를 부른다.\n\n판정: +체력\n\n10+: 2개 선택\n\n7–9: 1개 선택\n\n6-: 굶주린 무언가가 어둠에서 나온다.\n\n선택지:\n• 동료 2명 어둠시야\n• 대상 공포·다음 판정 유리\n• 대상에 대한 피해 굴림 유리\n\n마법적 어둠과 심연의 존재를 불러낸다.':'Trigger: Fill a wide area with magical darkness and call to what lives within it.\n\nRoll: +CON\n\n10+: Choose 2\n\n7–9: Choose 1\n\n6-: Something hungry comes out of the dark.\n\nChoices:\n• Two allies can see in the darkness\n• Frighten a target and gain advantage on the next roll against it\n• Gain advantage on damage rolls against the target\n\nCall forth magical darkness and the things that dwell beyond the veil.',
'그림자로 장갑을 무시하는 칼날을 만든다.':'Shape a blade of shadow that ignores armor.',
'발동: 그림자의 영역에서 빠져나오며 실체를 되찾는다.\n\n판정: +체력\n\n10+: 문제 없이 복귀\n\n7–9: 그림자 영역의 무언가가 함께 새어 나옴\n\n그림자 영역을 통해 물체를 통과한다.':'Trigger: Step back out of the shadow realm and regain physical form.\n\nRoll: +CON\n\n10+: Return without trouble.\n\n7–9: Something from the shadow realm leaks through with you.\n\nPass through solid things by traveling through the realm of shadows.',
'어둠 속 공격으로 힘을 회복한다.':'Recover your strength through attacks made from darkness.'}
for k,v in exp_desc.items(): add(k,v)

# Monster names/folders and fields. English names follow the original Dungeon World bestiary.
folder_map={'캄캄한 동굴':'Cavern Dwellers','부글거리는 늪지':'Denizens of the Swamp','언데드 군단':'Legions of the Undead','어두운 숲속':'The Dark Woods','이민족의 무리':'Ravenous Hordes','뒤틀린 실험체':'Twisted Experiments','깊고도 깊은 곳':'The Lower Depths','이계의 존재':'Planar Powers','사람들':'Folk of the Realm'}
monster_name_map={'가고일':'Gargoyle','동굴쥐':'Cave Rat','드워프 전사':'Dwarven Warrior','생살벌레':'Rot Grub','개구리인간':'Frogman','거대 악어':'Crocodilian','도펠겡어':'Doppelgänger','용 거북':'Dragon Turtle','구울':'Ghoul','그림자의 정령':'Shadow','미라':'Mummy','해골룡':'Dragonbone','그리폰':'Griffin','암살덩굴':'Assassin Vine','오거':'Ogre','트리엔트':'Treant','혼돈의 즙':'Chaos Ooze','스프라이트':'Sprite','신기루개':'Blink Dog','켄타우로스':'Centaur','놀 추적수':'Gnoll Tracker','놀 사절':'Gnoll Emissary','오크 노예잡이':'Orc Slaver','기랄론':'Girallon','녹괴물':'Rust Monster','데로':'Derro','나가':'Naga','마그민':'Magmin','미노타우로스':'Minotaur','살라만더':'Salamander','아볼레스':'Aboleth','용':'Dragon','종말의 용':'Apocalypse Dragon','지저엘프 자객':'Deep Elf Assassin','지저엘프 검호':'Deep Elf Swordmaster','지저엘프 사제':'Deep Elf Priest','추울':'Chuul','혼돈의 종자':'Chaos Spawn','회색 갈퀴발톱':'Gray Render','가시 악마':'Barbed Devil','경비병':'Guardsman','궁중광대':'Fool','기사':'Knight','귀족':'Noble','농부':'Peasant','대사제':'High Priest','모험가':'Adventurer','반도':'Rebel','발명가':'Tinkerer','병사':'Soldier','산적':'Bandit','산적 두목':'Bandit King','상인':'Merchant','야인':'Hunter','잡마술사':'Hedge Wizard','첩자':'Spy','하급 사제':'Acolyte','하플링 도둑':'Halfling Thief'}
for k,v in folder_map.items():add(k,v)
for k,v in monster_name_map.items():add(k,v)
# Translate bestiary prose from the shipped Korean text. Mechanical values are separate fields and never translated.
# Compact/common field translations are deliberately exact-string based.
common_monster_terms={'물기':'Bite','발톱':'Claw','창':'Spear','검':'Sword','도끼':'Axe','철퇴':'Mace','곤봉':'Club','촉수':'Tentacles','돌진':'Charge','가시':'Thorns','단검':'Dagger','비전 화염':'Arcane Fire','화염':'Flames','산성 구체':'Acid Orb','깨물기':'Gnaw','압살':'Crush','질식':'Choke','휘감기':'Constrict','삼키기':'Engulf','할퀴기':'Rake','독침':'Sting','주먹':'Fist','장갑 무시':'Ignores Armor','장갑 무시.':'Ignores Armor.'}
for k,v in common_monster_terms.items():add(k,v)

# New bestiary entries carry their English display strings next to the Korean seed data.
# Runtime mechanics never depend on these labels; this only builds the English display map.
for mon in MONSTERS:
    en=mon.get('en') if isinstance(mon,dict) else None
    if not isinstance(en,dict):
        continue
    for field in ('name','attack_name','range','special','instinct','description'):
        add(mon.get(field,''),en.get(field,''))
    km=mon.get('moves') if isinstance(mon.get('moves'),list) else []
    em=en.get('moves') if isinstance(en.get('moves'),list) else []
    for ko_s,en_s in zip(km,em): add(ko_s,en_s)
    kt=mon.get('tags') if isinstance(mon.get('tags'),list) else []
    et=en.get('tags') if isinstance(en.get('tags'),list) else []
    for ko_s,en_s in zip(kt,et): add(ko_s,en_s)

# Generic source/metadata strings in data files.
for k,v in {
'Dungeon World 1판 기본 자료':'Dungeon World 1st Edition Core Data',
'Dungeon World 1판 기본 콘텐츠':'Dungeon World 1st Edition Core Content',
'확장직업 예시':'Expansion Class Examples',
'없음':'None','없음.':'None.','제한 없음':'No limit','무직':'No class','종족 없음':'No race'}.items(): add(k,v)

# Final English display coverage for all shipped Korean seed strings.
# This is display-only; structured mechanics remain language-independent.
remaining_display = {'04(공포)': '04 (Horror)', 'Unlimited Dungeons / Distant Shore Pack 확장 직업': 'Unlimited Dungeons / Distant Shore Pack Expansion Classes', 'Unlimited Dungeons 영어 자료의 커뮤니티 보관본입니다. 원 배포 링크가 여러 차례 이동한 이력이 있어 공식 홈페이지 링크로 표기하지 않습니다.': 'Community archive of the English Unlimited Dungeons material. The original distribution link has moved several times, so this is not presented as an official homepage.', '가둔다.': 'Trap them.', '가시 돋친 칼': 'Barbed Blade', '가장 약한 순간에 공격한다.': 'Strike at the weakest moment.', '가지 휘두르기': 'Slam with Branches', '갈퀴발톱과 이빨': 'Rending Claws and Teeth', '갈퀴손톱': 'Raking Claws', '갉기': 'Gnaw', '강력한 갈퀴와 이빨을 지녔지만 한 주인에게 충성하는 파괴적인 괴수.': 'A destructive beast with mighty claws and teeth, fiercely loyal to a single master.', '거대한 집게발로 무언가를 붙잡아 자른다.': 'Seize something in its massive claws and cut it apart.', '거래를 제안한다.': 'Offer a bargain.', '계략을 실행한다.': 'Put a scheme into motion.', '계약을 제안한다.': 'Offer a contract.', '고대의 주문을 사용한다.': 'Use an ancient spell.', '고통을 퍼뜨린다.': 'Spread pain.', '곡괭이': 'Pickaxe', '공개 확장직업 예시를 프로그램에서 사용하기 쉽도록 정리한 변형 자료입니다.': 'Adapted presentation of the public expansion-class examples, organized for convenient use in this program.', '공격 관통 1.': 'Attacks have 1 piercing.', '공격 관통 3.': 'Attacks have 3 piercing.', '공물을 요구한다.': 'Demand tribute.', '광란 속에서 적들을 쓰러뜨린다.': 'Defeat enemies while in a battle frenzy.', '괴력': 'Forceful', '교단을 섬긴다.': 'Serve the cult.', '교단의 높은 자리에 올라 신의 뜻을 전하는 지도자.': 'A leader high in the faith who speaks the will of the deity.', '교단의 일상을 떠받치며 신앙을 전하는 낮은 계급의 사제.': 'A low-ranking priest who sustains the daily life of the faith and spreads its teachings.', '교단의 일을 맡긴다.': 'Entrust someone with the work of the faith.', '교리에 따른다.': 'Follow doctrine.', '교환이나 거래를 제안한다.': 'Offer an exchange or trade.', '궁핍과 탐욕 속에서 남의 것을 빼앗는 무리.': 'A band driven by want and greed to take what belongs to others.', '권능의 룬을 새기는 법을 숙련한다.': 'Master the carving of runes of power.', '권력자 앞에서도 진실을 농담과 풍자로 말하는 광대.': 'A jester who speaks truth through jokes and satire, even before the powerful.', '그림자의 몸.': 'Body of shadow.', '그림자의 손길': 'Shadow Touch', '금속을 녹슬게 한다.': 'Rust metal.', '금속을 먹고 힘을 얻는다.': 'Feed on metal and grow stronger.', '기득권을 무너뜨린다.': 'Overthrow the entrenched powers.', '기묘한 물건과 이야기를 싣고 떠도는 장인.': 'A wandering craftsperson carrying strange wares and stranger stories.', '기본': 'Basic', '기습과 채찍으로 사람을 사로잡는 오크 노예잡이.': 'An orc slaver who captures people with ambushes and a whip.', '기습한다.': 'Ambush them.', '기존 직업/행동/주문 데이터와 GM 커스텀 데이터를 보존하며 규칙 도움말, 몬스터 태그, 환경 폴더 기본값을 보강합니다.': 'Preserves existing classes, moves, spells, and GM-created data while supplementing rules help, monster tags, and default monster-setting folders.', '기존 질서를 무너뜨린다.': 'Overthrow the established order.', '기존의 질서를 무너뜨린다.': 'Overthrow the established order.', '길을 잃게 만든다.': 'Make them lose their way.', '김성일 · 도서출판 초여명': 'Kim Seong-il · Choyeomyeong Publishing', '끈질기게 사냥감을 쫓는다.': 'Relentlessly pursue prey.', '끝없는 열의.': 'Endless zeal.', '나무.': 'Wooden body.', '날개 달린 석상 같은 옛 경비병. 폐허와 동굴에 둥지를 틀고 보물 주변을 지킨다.': 'An ancient guardian like a winged stone statue, nesting in ruins and caves and keeping watch over treasure.', '날개, 요정 마법.': 'Wings, faerie magic.', '날개.': 'Wings.', '날아오른다.': 'Take to the air.', '낡은 활': 'Worn Bow', '남들에게 감동을 준다.': 'Inspire others.', '남의 정신에 기이한 생각을 심는다.': 'Plant strange thoughts in another mind.', '냄새 추적.': 'Tracks by scent.', '냄새를 따라 끝까지 사냥감을 추적하는 놀 사냥꾼.': 'A gnoll hunter that follows a scent until the prey is run to ground.', '놀라운 속도로 상처를 회복한다.': 'Recover from wounds with astonishing speed.', '놀린다.': 'Mock them.', '놀의 신과 무리를 섬긴다.': 'Serve the gnoll god and the pack.', '누군가를 집어던진다.': 'Pick someone up and throw them.', '늪에 숨어 사냥감을 물어 끌고 가는 거대한 악어.': 'A giant crocodile that hides in the swamp, bites its prey, and drags it away.', '늪에서 작은 왕국과 전쟁을 벌이는 개구리 모습의 종족.': 'A frog-like people who wage wars and build small kingdoms in the swamp.', '다른 이의 자리를 빼앗는다.': 'Take another person’s place.', '다스린다.': 'Rule.', '다시 일어난다.': 'Rise again.', '대의를 위해 죽는다.': 'Die for the cause.', '대재난을 일으킨다.': 'Unleash a catastrophe.', '대체: 주문 강화.\n주문을 시전할 때, 10~11이면 원할 경우 7~9의 부작용을 하나 택하고, 다음의 두 효과 중 하나를 고를 수 있습니다. 12이면 부작용을 고르지 않고 효과를 하나 택합니다:\n•주문의 효과가 2배 됩니다.\n•주문의 대상의 수가 2배 됩니다': 'Replaces: Empowered Magic.\nWhen you cast a spell, on a 10–11 you may choose one of the 7–9 consequences to also choose one of these effects. On a 12, choose one without taking a consequence:\n• The spell’s effects are doubled.\n• The spell’s number of targets is doubled.', '던전월드 한국어 공개판 임시 웹페이지': 'Dungeon World Korean Public Edition', '도시의 틈에서 기존 질서를 뒤엎으려는 조직.': 'An organization in the cracks of the city that seeks to overturn the existing order.', '도움을 구한다.': 'Ask for help.', '독 묻은 칼': 'Poisoned Blade', '독과 은밀한 침투로 지상 종족을 노리는 지저엘프 자객.': 'A deep elf assassin who hunts surface folk with poison and stealthy infiltration.', '독을 투여한다.': 'Administer poison.', '돈을 받고 어설픈 주문을 건다.': 'Cast a dubious spell for coin.', '돌 틈에 숨는다.': 'Hide among the stones.', '동업을 제안한다.': 'Propose a partnership.', '두꺼운 금속 껍질, 초자연적 지식, 날개. 공격 관통 4.': 'Thick metal hide, supernatural knowledge, wings. Attacks have 4 piercing.', '두꺼운 등껍질을 가진 거대한 수륙양서 괴수.': 'A gigantic amphibious beast protected by a thick shell.', '둥지를 지킨다.': 'Protect the nest.', '뒤틀기': 'Twist', '드워프들을 대체한다.': 'Replace the dwarves.', '드워프의 터전을 지킨다.': 'Defend dwarven lands.', '든든한 단도': 'Sturdy Dagger', '등껍질, 수륙양서.': 'Shell, amphibious.', '따르다 죽을 명령을 부하에게 내린다.': 'Order a follower to obey even unto death.', '땅굴을 판다.': 'Burrow.', '땅을 일구며 공동체의 삶을 떠받치는 평범한 사람.': 'An ordinary person who works the land and sustains the life of the community.', '때려부수기': 'Smash', '떼지어 덮친다.': 'Swarm over them.', '마법사 기초 주문술 묶음': 'Wizard Basic Spellcasting Bundle', '마법으로 만들어진 거대한 그림자 정령.': 'A huge shadow spirit shaped by magic.', '마을과 도시의 질서를 지키는 영주의 경비병.': 'A lord’s guard charged with keeping order in towns and cities.', '막을 수 없는 힘으로 움직인다.': 'Move with unstoppable force.', '만든다.': 'Create.', '매우 작음': 'Tiny', '먹는다.': 'Eat.', '먹어치운다.': 'Devour.', '먹은 고기의 기억을 얻는다.': 'Gain the memories of flesh it has eaten.', '먼 나라의 모험거리를 들려준다.': 'Tell of adventures in distant lands.', '명령과 생존 사이에서 전쟁터를 버티는 보통 병사.': 'An ordinary soldier enduring the battlefield between orders and survival.', '명령에 따른다.': 'Follow orders.', '명령을 내린다.': 'Give orders.', '명령한다.': 'Command.', '몇 가지 술법으로 생계를 꾸리는 떠돌이 마술사.': 'A wandering hedge wizard who makes a living with a handful of tricks and spells.', '모험을 떠난다.': 'Seek adventure.', '몽둥이': 'Club', '무덤과 부장품을 지키기 위해 일어나는 귀하게 보존된 망자.': 'A carefully preserved dead noble who rises to guard a tomb and its grave goods.', '무리를 지킨다.': 'Protect the pack.', '무언가/누군가를 찢어발긴다.': 'Tear something or someone apart.', '무언가를 훔친다.': 'Steal something.', '문명보다 자연에 가까운 삶을 사는 사냥꾼.': 'A hunter who lives closer to the wild than to civilization.', '물 속으로 후퇴한다.': 'Retreat into the water.', '물건과 정보를 돈으로 바꾸는 거래의 전문가.': 'An expert at turning goods and information into coin.', '미래를 완벽하게 내다보고 행동한다.': 'Act with perfect foresight.', '미로와 지하에서 상대의 방향 감각을 무너뜨리는 황소머리 괴물.': 'A bull-headed monster that destroys its prey’s sense of direction in mazes and underground passages.', '미천한 존재들을 업신여기는 행동을 한다.': 'Show contempt for lesser beings.', '반인반마.': 'Half human, half horse.', '밟고 지나간다.': 'Trample through.', '배신한다.': 'Betray.', '배운다.': 'Learn.', '법을 지킨다.': 'Uphold the law.', '변신.': 'Shapeshifting.', '변화시킨다.': 'Transform.', '병사들을 이끌고 싸움에 뛰어든다.': 'Lead soldiers into battle.', '병사들을 이끌고 큰 전투에서 승리한다.': 'Lead soldiers to victory in a major battle.', '보물과 영역을 지배하며 원소의 힘을 다루는 거대한 용.': 'A mighty dragon that rules treasure and territory and commands elemental power.', '보물지기': 'Hoarder', '부식 촉수': 'Corrosive Tentacles', '부식시킨다.': 'Corrode.', '부정형': 'Amorphous', '부하들을 시켜 적을 공격한다.': 'Have servants attack an enemy.', '분노한다.': 'Rage.', '불과 흑요석을 다루며 다른 세계의 문을 통해 나타나는 뱀꼬리 전사.': 'A serpent-tailed warrior of fire and obsidian that enters through gates from another world.', '불로 태워 없앤다.': 'Burn it away.', '불신자들을 응징한다.': 'Punish unbelievers.', '불의 정수를 소환한다.': 'Summon the essence of fire.', '불의 피.': 'Blood of fire.', '불이나 마법으로 공격한다.': 'Attack with fire or magic.', '불타는 망치': 'Burning Hammer', '불타는 창': 'Burning Spear', '붕대로 감싼다.': 'Entangle them in wrappings.', '비리와 불의를 공개한다.': 'Expose corruption and injustice.', '비수': 'Dirk', '빛과 생기를 꺼뜨린다.': 'Snuff out light and life.', '빼앗는다.': 'Take what belongs to others.', '뿌리를 내린다.': 'Take root.', '사냥한다.': 'Hunt.', '사람 머리와 뱀 몸을 지닌 야심가로 사교와 마법을 이용한다.': 'An ambitious being with a human head and serpent body, wielding cult influence and magic.', '사람과 가재가 섞인 듯한 수륙양서 괴물.': 'An amphibious horror resembling a cross between a human and a crayfish.', '사람을 겁내지 않는 거대한 동굴쥐 무리.': 'A horde of giant cave rats with no fear of people.', '사람의 감각을 어지럽힌다.': 'Confuse someone’s senses.', '사람의 모습을 흉내 내어 정체를 숨기는 변신 괴물.': 'A shapeshifting monster that hides its identity by imitating human form.', '사람의 인품을 판단한다.': 'Judge a person’s character.', '사슴 군주에게 녹색 기사로 인정받는다.': 'Be recognized as a Green Knight by the Stag Lord.', '사실을 보고한다.': 'Report the facts.', '사자와 독수리를 닮은 도도하고 충성스러운 하늘의 사냥꾼.': 'A proud and loyal hunter of the skies, part lion and part eagle.', '산야의 소식을 전한다.': 'Bring news from the wilds.', '산적들을 통솔하며 공포와 보상으로 지배하는 우두머리.': 'A bandit chief who rules through fear and reward.', '살 속에 파고든다.': 'Burrow into flesh.', '살아 있는 살을 탐하는 굶주린 언데드.': 'A ravenous undead creature that craves living flesh.', '살을 파고 들어감.': 'Burrows into flesh.', '상금을 내건다.': 'Put a bounty on someone.', '상대가 딱 필요로 하는 물건을 제시하고 값을 부른다.': 'Offer exactly what someone needs and name a price.', '상대를 혼란스럽게 만든다.': 'Confuse them.', '상처와 살 속을 파고드는 작은 벌레 떼.': 'A swarm of tiny worms that burrow into wounds and flesh.', '생각 없이 행동한다.': 'Act without thinking.', '생존한다.': 'Survive.', '서로 의존하는 마법사의 시작 행동을 다중직업 선택 하나로 취급합니다.': 'Treat the Wizard’s interdependent starting moves as one multiclass choice.', '세계를 끝낸다.': 'End the world.', '세계의 심장에서 깨어나 종말을 가져온다고 전해지는 전설적인 용.': 'A legendary dragon said to awaken at the heart of the world and bring the apocalypse.', '속임수를 녹여 없앤다.': 'Burn away deception.', '수륙 양면에서 공격한다.': 'Attack from land or water.', '수륙양서, 위장색.': 'Amphibious, camouflage.', '수륙양서.': 'Amphibious.', '수륙양서. 공격 관통 3.': 'Amphibious. Attacks have 3 piercing.', '수많은 가시들. 공격 관통 3.': 'Countless barbs. Attacks have 3 piercing.', '수치 없는 인물.': 'No numeric combat stats.', '순식간에 새순을 틔우고 뻗어낸다.': 'Sprout and spread new growth in an instant.', '숲과 언덕 아래에서 살아가는 강인하고 야만적인 종족.': 'A hardy and savage people who live among forests and beneath the hills.', '숲에서 사냥감을 덩굴로 붙잡아 끌고 가는 포식성 식물.': 'A predatory plant that catches prey with vines and drags it away through the forest.', '숲을 지키며 움직이는 거대한 나무 존재.': 'A gigantic tree-being that walks to defend the forest.', '숲의 영역을 지키는 반인반마 부족.': 'A tribe of centaurs that guards its woodland territory.', '쉬지 않고 빠르게 달린다.': 'Run swiftly without tiring.', '식물.': 'Plant.', '신과 밀접한 관계.': 'Close connection to a deity.', '신성': 'Divine', '신성한 벼락을 맞고도 살아남는다.': 'Survive being struck by a holy thunderbolt.', '신성한 의식과 명령으로 놀 무리를 이끄는 사절.': 'An emissary who leads a gnoll pack through sacred rites and commands.', '신에게 받은 비밀을 드러낸다.': 'Reveal a secret granted by the deity.', '신의 계시를 드러낸다.': 'Reveal divine revelation.', '신의 뜻에 따를 보상을 설파한다.': 'Preach the rewards of following the deity’s will.', '신의 벌을 내린다.': 'Visit divine punishment.', '신체 부위를 물어서 뜯어낸다.': 'Bite off a body part.', '싸운다.': 'Fight.', '악의와 혐오의 주문을 시전한다.': 'Cast a spell of malice and hate.', '암살자 조직에서 첫 암살의 가치를 인정받는다.': 'Have your first assassination recognized by an assassins’ guild.', '암흑 속 존재에게 금단의 비밀을 배운다.': 'Learn a forbidden secret from a being in the darkness.', '약해진 자를 사냥한다.': 'Hunt the weak.', '양심에 따른다.': 'Follow your conscience.', '어둠을 유리하게 이용한다.': 'Use darkness to your advantage.', '여러 개의 팔을 가진 거대한 마법 실험 유인원.': 'A gigantic many-armed ape born of magical experimentation.', '영역을 지킨다.': 'Defend its territory.', '영원한 안식을 즐긴다.': 'Enjoy eternal rest.', '옛 마법을 사용한다.': 'Use old magic.', '옛 마법을 퍼뜨린다.': 'Spread ancient magic.', '옛 모험 이야기를 한다.': 'Tell stories of old adventures.', '온몸에 가시가 돋은 이계의 악마.': 'A planar demon covered from head to toe in barbs.', '외양이나 본질을 변화시킨다.': 'Alter appearance or essence.', '요구한다.': 'Make demands.', '용암 깊은 곳에서 불과 마법의 물건을 만드는 장인 종족.': 'A people of crafters who forge fire and magical goods in the depths of the lava.', '용의 뼈로 이루어진 언데드.': 'Undead made from dragon bones.', '원군을 부른다.': 'Call for reinforcements.', '원소를 뜻대로 조종한다.': 'Command the elements at will.', '원소를 불러낸다.': 'Call forth the elements.', '원소를 뿜어낸다.': 'Breathe forth an element.', '원소의 피, 날개. 공격 관통 4.': 'Elemental blood, wings. Attacks have 4 piercing.', '원칙과 봉사의 상징이자 무장한 귀족 전사.': 'An armed noble warrior who embodies principle and service.', '원칙에 따라 산다.': 'Live by principle.', '위에서부터 내려와 공격한다.': 'Swoop down to attack.', '위험과 보물을 찾아다니는 또 다른 모험가 무리.': 'Another band of adventurers searching for danger and treasure.', '율법을 정한다.': 'Lay down the law.', '음흉함': 'Devious', '이계에서 새어든 혼돈이 응고되어 움직이는 점액질 괴물.': 'A living ooze formed from chaos that leaked in from another plane.', '이끈다.': 'Lead.', '이루 말할 수 없는 고통을 가한다.': 'Inflict unspeakable pain.', '이익을 낸다.': 'Turn a profit.', '이익을 본다.': 'Profit from the situation.', '일시적으로 이 세계와 이계를 연결한다.': 'Temporarily bridge this world and another plane.', '자란다.': 'Grow.', '자른다.': 'Cut.', '자연을 보호한다.': 'Protect nature.', '자연이 필요로 하는 마법을 쓴다.': 'Use the magic nature needs.', '작고 영리하며 요정 마법으로 사람을 곤란하게 하는 존재.': 'A small, clever faerie creature that uses magic to make trouble for people.', '작은 감사의 표시를 제시한다.': 'Offer a small token of thanks.', '작은 체구와 친근한 인상을 이용해 물건을 훔치는 도둑.': 'A thief who uses a small frame and friendly manner to steal things.', '작음': 'Small', '잔혹하면서도 우아한 검술을 쓰는 지저엘프 정예 검사.': 'An elite deep elf swordsman whose style is both graceful and cruel.', '잡아 뜯고 찢어발긴다.': 'Seize, tear, and rend.', '잡아 찢기': 'Rend', '장난을 벌인다.': 'Make mischief.', '장난을 쳐서 상대의 본성을 드러낸다.': 'Play a trick that reveals someone’s true nature.', '장난을 친다.': 'Play a prank.', '재산과 권력을 바탕으로 사람과 영지를 지배하는 자.': 'A ruler who commands people and lands through wealth and power.', '저주를 건다.': 'Lay a curse.', '적들을 정글에서 몰아낸다.': 'Drive enemies out of the jungle.', '전설적 괴물을 쓰러뜨리고 전리품을 취한다.': 'Slay a legendary monster and claim a trophy.', '전설적 무기에 특별한 힘을 깃들인다.': 'Imbue a legendary weapon with a special power.', '전쟁을 한다.': 'Make war.', '전투를 향해 진군한다.': 'March into battle.', '점액질. 이계의 조각들이 박혀 있음.': 'Amorphous slime studded with fragments of other planes.', '정신을 침범한다.': 'Invade a mind.', '정제된 금속을 부식시켜 먹는 촉수 달린 인공 생물.': 'A tentacled creature that corrodes and devours worked metal.', '정체를 숨기고 비밀을 모아 주인에게 전달하는 자.': 'An infiltrator who hides their identity, gathers secrets, and carries them back to a master.', '제물이 바쳐지는 곳에 나타난다.': 'Appear where sacrifices are offered.', '제사용 단도': 'Sacrificial Dagger', '조심스러움': 'Cautious', '주문을 시전할 때, 10+가 나오더라도 원하면 7~9의 부작용을 하나 택할 수 있습니다. 그럴 경우 다음의 두 효과 중 하나를 고릅니다:\n•주문의 효과가 2배 됩니다.\n•주문의 대상의 수가 2배 됩니다': 'When you cast a spell, on a 10+ you may choose one of the 7–9 consequences. If you do, choose one:\n• The spell’s effects are doubled.\n• The spell’s number of targets is doubled.', '주인을 섬긴다.': 'Serve its master.', '주제에 맞지 않는 거래를 한다.': 'Offer a strange or inappropriate bargain.', '죽은 용의 뼈로 만들어져 강력한 사령술사를 섬기는 괴물.': 'A monster made from the bones of a dead dragon, bound to serve a powerful necromancer.', '죽은 자를 속박하는 방법을 찾아낸다.': 'Discover a way to bind the dead.', '중거리, 장거리': 'Near, Far', '지배한다.': 'Dominate.', '지상 종족을 해친다.': 'Harm the surface races.', '지저엘프들을 선동한다.': 'Rouse the deep elves.', '지킨다.': 'Guard.', '지하 호수에서 텔레파시로 노예를 지배하는 거대한 물고기 괴물.': 'A gigantic fish-like horror that rules slaves by telepathy from an underground lake.', '지하의 거점과 동족을 지키는 드워프 전사.': 'A dwarven warrior defending an underground hold and their people.', '지하의 신들과 언약을 맺고 신성한 힘을 쓰는 지저엘프 사제.': 'A deep elf priest bound by covenant to the gods below and wielding divine power.', '짐승을 죽인다.': 'Kill a beast.', '짐승의 정신을 조종한다.': 'Control the mind of a beast.', '집게발': 'Claw', '채찍': 'Whip', '촉수로 금속을 부식.': 'Tentacles corrode metal.', '친구를 태우고 하늘을 난다.': 'Carry a friend through the sky.', '침투한다.': 'Infiltrate.', '큼': 'Large', '텔레파시 능력을 가진 뒤틀린 드워프 계통의 실험 종족.': 'A twisted offshoot of dwarven stock, altered by experimentation and gifted with telepathy.', '텔레파시.': 'Telepathy.', '특수': 'Special', '특이한 물건을 팔려 한다.': 'Try to sell an unusual item.', '틀림 없는 방향감각.': 'Unerring sense of direction.', '파고들기': 'Burrow In', '파멸적인 사건에서 끝내 살아남는다.': 'Survive a catastrophic event against all odds.', '팔이 많음.': 'Many arms.', '포로를 잡는다.': 'Take captives.', '하루하루 살아간다.': 'Get through each day.', '한 덩어리가 되어 싸운다.': 'Fight as a single unit.', '한걸음, 몇걸음': 'Close, Reach', '한걸음, 몇걸음, 중거리': 'Close, Reach, Near', '헛수고나 헛걸음을 한다.': 'Waste time or effort on a fruitless errand.', '현실을 고쳐 쓴다.': 'Rewrite reality.', '협박하고 공갈한다.': 'Threaten and extort.', '호의적인 척한다.': 'Pretend to be friendly.', '혼돈을 쏟아낸다.': 'Pour forth chaos.', '혼돈의 손길': 'Touch of Chaos', '혼돈의 신에게 자기 형체마저 내어준 변이된 사교도.': 'A warped cultist who surrendered even their own form to a god of chaos.', '혼돈의 형상.': 'Form of chaos.', '환상.': 'Illusory.', '환상과 순간적인 위치 변화로 사냥하는 마법적인 개 무리.': 'A pack of magical hounds that hunt with illusion and sudden shifts of position.', '환상을 만든다.': 'Create an illusion.', '활': 'Bow', '활을 완벽하게 쏜다.': 'Shoot with perfect accuracy.', '훔친 돈으로 호사스레 산다.': 'Live lavishly on stolen coin.', '훔친다.': 'Steal.'}
add('동물 친구와 함께 행동하는 경우에 한하여 사용할 수 있습니다.','You can use this move only while acting together with your animal companion.')

for k,v in remaining_display.items(): add(k,v)

# Recursively collect remaining Korean strings so coverage is visible during development.
def walk(x):
    if isinstance(x,str): yield x
    elif isinstance(x,list):
        for v in x: yield from walk(v)
    elif isinstance(x,dict):
        for v in x.values(): yield from walk(v)
all_strings=set(walk(SEED))|set(walk(MONSTERS))
remaining=sorted(s for s in all_strings if re.search('[가-힣]',s) and s not in M)

out=ROOT/'static/i18n_content_en.json'
out.write_text(json.dumps({'map':M,'unmapped':remaining},ensure_ascii=False,indent=2),encoding='utf-8')
print('mapped',len(M),'unmapped',len(remaining))
for s in remaining[:250]: print('UNMAPPED',repr(s))
