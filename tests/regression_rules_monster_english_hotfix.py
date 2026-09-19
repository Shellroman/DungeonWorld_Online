#!/usr/bin/env python3
from pathlib import Path
import json, re, sys, zipfile

ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT/'static/app.js').read_text(encoding='utf-8')
INDEX = (ROOT/'static/index.html').read_text(encoding='utf-8')
SEED = json.loads((ROOT/'data/monster_seed.json').read_text(encoding='utf-8'))
CONTENT = json.loads((ROOT/'static/i18n_content_en.json').read_text(encoding='utf-8'))['map']
UI = json.loads((ROOT/'static/i18n_ui_en.json').read_text(encoding='utf-8'))['exact']
HANGUL = re.compile(r'[가-힣]')

checks=[]
def ok(cond, msg):
    checks.append((bool(cond),msg))
    if not cond:
        print('FAIL:',msg)

# Rules save bug: attachGMRules must bind the current rules object before the callback uses r.
ok('function attachGMRules(){const r=APP.state.room.rules;' in APP_JS,
   'attachGMRules binds r before save callback')

# Localization catalogs must be tied to the current build, not a stale browser cache.
ok('data-build-id="__BUILD_ID__"' in INDEX, 'index exposes BUILD_ID to client')
ok('STATIC_CACHE_KEY' in APP_JS and "cache:'no-store'" in APP_JS,
   'i18n catalogs use build cache key and no-store')
ok("i18n_content_en.json'+suffix" in APP_JS and "i18n_ui_en.json'+suffix" in APP_JS,
   'both English catalogs are cache-busted')

# Basic monster UI must not depend on an ambiguous log/action translation.
ok("APP.language==='en'?'Create Monster':'몬스터 생성'" in APP_JS,
   'monster create button has explicit bilingual label')
ok(UI.get('몬스터 생성') == 'Create Monster', 'UI catalog maps 몬스터 생성 to Create Monster')

# Every bundled monster needs an explicit English overlay; no Korean may leak from its built-in fields.
ok(len(SEED)==154, '154 bundled monsters')
fields=('name','attack_name','range','tags','special','instinct','moves','description')
for m in SEED:
    en=m.get('en')
    ok(isinstance(en,dict) and bool(en), f"{m.get('name')} has explicit English overlay")
    if not isinstance(en,dict):
        continue
    for field in fields:
        v=en.get(field, '')
        text='\n'.join(map(str,v)) if isinstance(v,list) else str(v)
        ok(not HANGUL.search(text), f"{m.get('name')} English {field} contains no Hangul")

# Source-aligned official setting names and monster names from the English SRD.
official_names={
 '캄캄한 동굴':set("Ankheg|Cave Rat|Choker|Cloaker|Dwarven Warrior|Earth Elemental|Fire Beetle|Gargoyle|Gelatinous Cube|Goblin|Goblin Orkaster|Goliath|Otyugh|Maggot-Squid|Purple Worm|Roper|Rot Grub|Spiderlord|Troglodyte".split('|')),
 '깊고도 깊은 곳':set("Aboleth|Apocalypse Dragon|Chaos Spawn|Chuul|Deep Elf Assassin|Deep Elf Swordmaster|Deep Elf Priest|Dragon|Gray Render|Magmin|Minotaur|Naga|Salamander".split('|')),
 '뒤틀린 실험체':set("Bulette|Chimera|Derro|Digester|Ethereal Filcher|Ettin|Girallon|Iron Golem|Flesh Golem|Kraken|Manticore|Owlbear|Pegasus|Rust Monster|Xorn".split('|')),
 '사람들':set("Acolyte|Adventurer|Bandit|Bandit King|Fool|Guardsman|Halfling Thief|Hedge Wizard|High Priest|Hunter|Knight|Merchant|Noble|Peasant|Rebel|Soldier|Spy|Tinkerer".split('|')),
 '이민족의 무리':set("Formian Drone|Formian Taskmaster|Formian Centurion|Formian Queen|Gnoll Tracker|Gnoll Emissary|Gnoll Alpha|Orc Bloodwarrior|Orc Berserker|Orc Breaker|Orc One-Eye|Orc Shaman|Orc Slaver|Orc Shadowhunter|Orc Warchief|Triton Spy|Triton Tidecaller|Triton Sub-Mariner|Triton Noble".split('|')),
 '이계의 존재':set("Angel|Barbed Devil|Chain Devil|Concept Elemental|Corrupter|Djinn|Hell Hound|Imp|Inevitable|Larvae|Nightmare|Quasit|The Tarrasque|Word Demon".split('|')),
 '부글거리는 늪지':set("Bakunawa|Basilisk|Black Pudding|Coutal|Crocodilian|Doppelgänger|Dragon Turtle|Dragon Whelp|Ekek|Fire Eels|Frogman|Hydra|Kobold|Lizardman|Medusa|Sahuagin|Sauropod|Swamp Shambler|Troll|Will-o-wisp".split('|')),
 '언데드 군단':set("Abomination|Banshee|Devourer|Dragonbone|Draugr|Ghost|Ghoul|Lich|Mohrg|Mummy|Nightwing|Shadow|Sigben|Skeleton|Spectre|Vampire|Wight-Wolf|Zombie".split('|')),
 '어두운 숲속':set("Assassin Vine|Blink Dog|Centaur|Chaos Ooze|Cockatrice|Dryad|Eagle Lord|Elvish Warrior|Elvish High Arcanist|Griffin|Hill Giant|Ogre|Razor Boar|Satyr|Sprite|Treant|Werewolf|Worg".split('|')),
}
for folder,expected in official_names.items():
    got={m['en']['name'] for m in SEED if m.get('folder')==folder}
    ok(got==expected, f'official English monster-name set: {folder}')

folder_expected={
 '캄캄한 동굴':'Cavern Dwellers',
 '깊고도 깊은 곳':'The Lower Depths',
 '뒤틀린 실험체':'Twisted Experiments',
 '사람들':'Folk of the Realm',
 '이민족의 무리':'Ravenous Hordes',
 '이계의 존재':'Planar Powers',
 '부글거리는 늪지':'Denizens of the Swamp',
 '언데드 군단':'Legions of the Undead',
 '어두운 숲속':'The Dark Woods',
}
for ko,en in folder_expected.items():
    ok(CONTENT.get(ko)==en, f'folder {ko} -> {en}')
for ko,en in {'경비병':'Guardsman','궁중광대':'Fool','야인':'Hunter'}.items():
    ok(CONTENT.get(ko)==en, f'monster {ko} -> {en}')

# A known source-aligned monster spot check.
gob=next((m for m in SEED if m.get('key')=='cavern-goblin-orkaster'),None)
ok(gob is not None,'Goblin Orkaster exists')
if gob:
    en=gob['en']
    ok(en.get('name')=='Goblin Orkaster','Goblin Orkaster English name')
    ok(en.get('attack_name')=='Acid Orb','Goblin Orkaster attack')
    ok(en.get('range')=='Near, Far','Goblin Orkaster range')
    ok(en.get('tags')==['Solitary','Small','Magical','Intelligent','Organized','Ignores Armor'],
       'Goblin Orkaster tags')
    ok(en.get('instinct')=='To tap power beyond their stature.','Goblin Orkaster instinct')

# Every canonical Korean monster string that can be displayed must have an exact English mapping.
for m in SEED:
    vals=[m.get('name',''),m.get('attack_name',''),m.get('range',''),m.get('special',''),m.get('instinct',''),m.get('description','')]
    vals += list(m.get('tags') or []) + list(m.get('moves') or [])
    for v in vals:
        if isinstance(v,str) and HANGUL.search(v):
            mapped=CONTENT.get(v,'')
            ok(bool(mapped) and not HANGUL.search(str(mapped)), f"mapped built-in monster text: {v[:45]}")

# Generated English core pack must carry all monsters and contain no Hangul in gameplay monster data.
pack=ROOT/'dwpack/DungeonWorld_1E_Core_EN.dwpack'
with zipfile.ZipFile(pack) as z:
    monsters=json.loads(z.read('data/monsters.json'))
ok(len(monsters)==154,'English core DWPack has 154 monsters')
for m in monsters:
    blob=json.dumps(m,ensure_ascii=False)
    ok(not HANGUL.search(blob), f"English DWPack monster contains no Hangul: {m.get('name')}")

failed=[m for passed,m in checks if not passed]
print(f"rules/monster English hotfix: {len(checks)-len(failed)}/{len(checks)} PASS")
if failed:
    sys.exit(1)
