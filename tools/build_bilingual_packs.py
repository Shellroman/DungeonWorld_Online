#!/usr/bin/env python3
from __future__ import annotations
import json,re,zipfile
from pathlib import Path
from io import BytesIO

ROOT=Path(__file__).resolve().parents[1]
APP_VERSION=(ROOT/'VERSION').read_text(encoding='utf-8').strip().split('-',1)[0]
DW=ROOT/'dwpack'
CONTENT=json.loads((ROOT/'static/i18n_content_en.json').read_text(encoding='utf-8'))['map']
UI=json.loads((ROOT/'static/i18n_ui_en.json').read_text(encoding='utf-8'))
EXACT=UI.get('exact',{})
EXACT.update({
    'Unlimited Dungeons / Distant Shore Pack 확장직업 자료':'Unlimited Dungeons / Distant Shore Pack expansion-class material',
    '생존자: 원 자료에서 Jacob Randolph의 저작물을 기반으로 한다고 표시':'Survivor: the source material credits it as based on work by Jacob Randolph',
    'Unlimited Dungeons 영어 자료의 커뮤니티 보관본입니다.':'Community archive of the English Unlimited Dungeons material.',
})
TERMS=sorted((UI.get('terms') or {}).items(),key=lambda kv:len(kv[0]),reverse=True)
HANGUL=re.compile(r'[가-힣]')

def tr(s:str)->str:
    if s in CONTENT:return CONTENT[s]
    if s in EXACT:return EXACT[s]
    # Only manifest/help-like short labels use fragment translation. Game prose is
    # translated only by exact catalog entries so rule meaning cannot drift.
    if len(s)<=120:
        out=s
        for a,b in TERMS:
            out=out.replace(a,b)
        if out!=s:return out
    return s

def walk(x):
    if isinstance(x,str):return tr(x)
    if isinstance(x,list):return [walk(v) for v in x]
    if isinstance(x,dict):return {tr(k) if isinstance(k,str) else k:walk(v) for k,v in x.items()}
    return x


def update_source_manifest_version(path:Path):
    with zipfile.ZipFile(path) as z:
        files={n:z.read(n) for n in z.namelist()}
    manifest=json.loads(files['manifest.json'])
    manifest['created_with']=APP_VERSION
    files['manifest.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in sorted(files):
            info=zipfile.ZipInfo(name,date_time=(2026,9,15,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
            z.writestr(info,files[name])

def convert(src:Path,dst:Path,kind:str):
    with zipfile.ZipFile(src) as z:
        files={n:z.read(n) for n in z.namelist()}
    out={}
    left=[]
    for name,data in files.items():
        if not name.endswith('.json'):
            out[name]=data;continue
        obj=json.loads(data)
        obj=walk(obj)
        if kind=='core' and name=='data/monsters.json' and isinstance(obj,list):
            for monster in obj:
                if isinstance(monster,dict) and isinstance(monster.get('data'),dict):
                    monster['data']['source_url']='https://www.dungeonworldsrd.com/monsters/'
        if name=='manifest.json':
            obj['created_with']=APP_VERSION
            obj['language']='en'
            obj['language_name']='English'
            if kind=='core':
                obj['name']='Dungeon World 1E Core Data · English'
                obj['attribution']='Dungeon World by Sage LaTorra and Adam Koebel'
                obj['source_url']='https://www.dungeon-world.com/'
                obj['original_source_url']='https://www.dungeon-world.com/'
                obj['official_source_repository']='https://github.com/Sagelt/Dungeon-World'
                obj.pop('translation_credit',None)
                obj.pop('translation_source_url',None)
                obj['upstream_notice']='Dungeon World official licensing identifies SRD 5.1 by Wizards of the Coast LLC as upstream CC BY 4.0 material.'
                obj['upstream_license_url']='https://creativecommons.org/licenses/by/4.0/'
                obj['notes']=['English display text is aligned to the Dungeon World original. Structured mechanics and stable UIDs are shared with the Korean pack.']
            else:
                obj['name']='Unlimited Dungeons / Distant Shore Expansion-Class Examples · English'
                obj['changes']='English presentation of the bundled expansion-class examples. Stable UIDs and structured mechanics are shared with the Korean pack.'
        def scan(v,path=''):
            if isinstance(v,str) and HANGUL.search(v): left.append((name,path,v))
            elif isinstance(v,list):
                for i,a in enumerate(v):scan(a,f'{path}[{i}]')
            elif isinstance(v,dict):
                for k,a in v.items():
                    if isinstance(k,str) and HANGUL.search(k): left.append((name,(f'{path}.{k}' if path else k)+'::<key>',k))
                    scan(a,f'{path}.{k}' if path else k)
        scan(obj)
        out[name]=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()
    with zipfile.ZipFile(dst,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in sorted(out):
            info=zipfile.ZipInfo(name,date_time=(2026,9,14,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
            z.writestr(info,out[name])
    print(dst.name,'remaining Hangul',len(left))
    for row in left[:30]:print(' ',row)
    return left

left=[]
update_source_manifest_version(DW/'DungeonWorld_1E_Core.dwpack')
update_source_manifest_version(DW/'UnlimitedDungeons_DistantShore_Expansions.dwpack')
left+=convert(DW/'DungeonWorld_1E_Core.dwpack',DW/'DungeonWorld_1E_Core_EN.dwpack','core')
left+=convert(DW/'UnlimitedDungeons_DistantShore_Expansions.dwpack',DW/'UnlimitedDungeons_DistantShore_Expansions_EN.dwpack','expansion')
# Some attribution/proper names can legitimately remain Hangul only if explicitly allowed.
# Fail on game-data Korean that escaped the translation catalog.
allowed=('김성일','도서출판 초여명','04(공포)','니켈','늑대','빛남')
bad=[x for x in left if not any(a in x[2] for a in allowed)]
if bad:
    print('Untranslated game-data strings remain:',len(bad))
    raise SystemExit(2)
