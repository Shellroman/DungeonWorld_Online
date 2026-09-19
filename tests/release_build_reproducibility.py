#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(rel: str) -> str:
    cp = subprocess.run([sys.executable, rel], cwd=ROOT, text=True, capture_output=True)
    if cp.returncode:
        print(cp.stdout)
        print(cp.stderr, file=sys.stderr)
        raise SystemExit(f"{rel} failed with {cp.returncode}")
    return cp.stdout


out = run("tools/build_i18n_en.py")
catalog = json.loads((ROOT / "static/i18n_content_en.json").read_text(encoding="utf-8"))
assert not catalog.get("unmapped"), catalog.get("unmapped", [])[:10]
assert len(catalog.get("map", {})) >= 1179, len(catalog.get("map", {}))
assert "unmapped 0" in out

run("tools/build_i18n_ui_en.py")
run("tools/build_bilingual_packs.py")

hangul = re.compile(r"[가-힣]")
allowed = ("김성일", "도서출판 초여명", "04(공포)", "니켈", "늑대", "빛남")
for rel in (
    "dwpack/DungeonWorld_1E_Core_EN.dwpack",
    "dwpack/UnlimitedDungeons_DistantShore_Expansions_EN.dwpack",
):
    bad: list[tuple[str, str]] = []
    with zipfile.ZipFile(ROOT / rel) as zf:
        for name in zf.namelist():
            if not name.endswith(".json"):
                continue
            obj = json.loads(zf.read(name))

            def scan(v):
                if isinstance(v, str):
                    if hangul.search(v) and not any(a in v for a in allowed):
                        bad.append((name, v))
                elif isinstance(v, list):
                    for item in v:
                        scan(item)
                elif isinstance(v, dict):
                    for key, item in v.items():
                        if isinstance(key, str) and hangul.search(key) and not any(a in key for a in allowed):
                            bad.append((name, key))
                        scan(item)

            scan(obj)
    assert not bad, bad[:10]

print("release build reproducibility ok — 1179 mapped / 0 unmapped; English packs clean")
