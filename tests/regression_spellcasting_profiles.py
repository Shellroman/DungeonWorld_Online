from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("DW_DB", str(Path(tempfile.gettempdir()) / "dw_regression_spellcasting_profiles.db"))
sys.path.insert(0, str(ROOT))
import app as srv  # noqa: E402

APP_JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
APP_PY = (ROOT / "app.py").read_text(encoding="utf-8")
SEED = json.loads((ROOT / "data" / "seed_data.json").read_text(encoding="utf-8"))

fails: list[str] = []
passed = 0

def ok(name: str, cond: bool, detail: object = "") -> None:
    global passed
    if cond:
        passed += 1
    else:
        fails.append(f"{name}: {detail}")

# Public version/schema stay fixed during this refactor.
ok("version_1_0_0", (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "1.0.0")
ok("server_version_1_0_0", bool(re.search(r'^VERSION\s*=\s*"1\.0\.0"\s*$', APP_PY, re.M)))
ok("schema_20", bool(re.search(r"^SCHEMA_VERSION\s*=\s*20\s*$", APP_PY, re.M)))

wizard = SEED["classes"]["마법사"]["spellcasting"]
cleric = SEED["classes"]["사제"]["spellcasting"]
ok("wizard_selected_known", wizard["known_mode"] == "selected")
ok("wizard_start_3_level_1", wizard["starting_choice_level"] == 1 and wizard["starting_choice_count"] == 3)
ok("wizard_learn_one_per_level", wizard["learn_per_level"] == 1)
ok("wizard_prepare_from_known", wizard["prepare_mode"] == "known" and wizard["limit_mode"] == "level_sum" and wizard["limit_offset"] == 1)
ok("cleric_knows_all", cleric["known_mode"] == "all")
ok("cleric_no_start_selection", cleric["starting_choice_count"] == 0 and cleric["learn_per_level"] == 0)
ok("cleric_prepare_from_all", cleric["prepare_mode"] == "all" and cleric["limit_mode"] == "level_sum" and cleric["limit_offset"] == 1)

# Official class-access moves are metadata, not special runtime branches.
def class_accesses(class_name: str):
    c = SEED["classes"][class_name]
    for section in ("start", "a25", "a610"):
        for move in c.get(section, []):
            for effect in move.get("move_effects", []):
                if effect.get("kind") == "class_access":
                    yield move, effect

ranger = list(class_accesses("사냥꾼"))
paladin = list(class_accesses("성기사"))
ok("ranger_god_amidst_wastes_metadata", any(m["name"] == "황무지의 신" and e.get("source_class") == "사제" for m, e in ranger))
ok("paladin_divine_favor_metadata", any(m["name"] == "신의 은혜" and e.get("source_class") == "사제" for m, e in paladin))

# No runtime class-name checks may decide spell mechanics. Wizard/Cleric names are
# allowed only as UI preset labels/content, never as state.class_name conditions.
for pat in (
    r"class_name\s*===\s*['\"](?:마법사|사제)['\"]",
    r"class_name\s*!==\s*['\"](?:마법사|사제)['\"]",
    r"className\s*===\s*['\"](?:마법사|사제)['\"]",
    r"className\s*!==\s*['\"](?:마법사|사제)['\"]",
):
    ok("no_runtime_name_branch_" + str(abs(hash(pat))), re.search(pat, APP_JS) is None and re.search(pat, APP_PY) is None, pat)
ok("profile_runtime_helper", "function spellcastingProfile(className)" in APP_JS)
ok("profile_saved_with_class", "spellcasting:collectSpellcastingProfile()" in APP_JS)
ok("source_profile_inherited", "profile=spellcastingProfile(e.source_class)" in APP_JS)
ok("separate_spell_tracks", "spell_tracks" in APP_JS and '"spell_tracks"' in APP_PY)
ok("multiclass_move_effects_resolved", "function extraMoveDefinitions(state)" in APP_JS and "def _extra_move_definitions" in APP_PY)

# Minimal DB for server-side mechanics tests.
con = sqlite3.connect(":memory:")
con.row_factory = sqlite3.Row
con.executescript("""
CREATE TABLE class_defs(id INTEGER PRIMARY KEY, room_id INTEGER, name TEXT, data_json TEXT, sort_order INTEGER DEFAULT 1);
CREATE TABLE race_defs(id INTEGER PRIMARY KEY, room_id INTEGER, name TEXT, data_json TEXT, sort_order INTEGER DEFAULT 1);
CREATE TABLE spell_defs(id INTEGER PRIMARY KEY, room_id INTEGER, class_name TEXT, name TEXT, level TEXT, data_json TEXT);
""")

book_profile = srv.normalize_spellcasting_profile({
    "enabled": True, "known_mode": "selected", "known_label": "Book",
    "prepare_mode": "known", "prepare_label": "Prepared", "limit_mode": "level_sum",
    "limit_offset": 1, "zero_level_label": "Cantrip", "zero_auto_known": True,
    "zero_auto_prepared": True, "zero_limit_exempt": True,
    "starting_choice_level": 1, "starting_choice_count": 1, "learn_per_level": 1,
})
all_profile = srv.normalize_spellcasting_profile({
    "enabled": True, "known_mode": "all", "known_label": "All",
    "prepare_mode": "all", "prepare_label": "Prepared", "limit_mode": "level_sum",
    "limit_offset": 1, "zero_level_label": "Rote", "zero_auto_known": True,
    "zero_auto_prepared": True, "zero_limit_exempt": True,
})
manual_profile = srv.normalize_spellcasting_profile({"enabled": False})
classes = {
    "BookCaster": {"spellcasting": book_profile, "start": [], "a25": [], "a610": []},
    "AllCaster": {"spellcasting": all_profile, "start": [], "a25": [], "a610": []},
    "Carrier": {"spellcasting": manual_profile, "start": [], "a25": [{"name": "Gain All", "move_effects": [{"id": "carrier.gain", "kind": "class_access", "source_class": "AllCaster", "grant_moves": []}]}], "a610": []},
    "Source": {"spellcasting": manual_profile, "start": [], "a25": [{"name": "Nested Gain", "move_effects": [{"id": "source.nested", "kind": "class_access", "source_class": "AllCaster", "grant_moves": []}]}], "a610": []},
}
for idx, (name, data) in enumerate(classes.items(), 1):
    con.execute("INSERT INTO class_defs(id,room_id,name,data_json,sort_order) VALUES(?,?,?,?,?)", (idx, 1, name, json.dumps(data, ensure_ascii=False), idx))
for idx, (cls, name, level) in enumerate([
    ("BookCaster", "B0", "Cantrip"), ("BookCaster", "B1A", "1"), ("BookCaster", "B1B", "1"), ("BookCaster", "B2", "2"),
    ("AllCaster", "A0", "Rote"), ("AllCaster", "A1", "1"), ("AllCaster", "A2", "2"), ("AllCaster", "A3", "3"),
], 1):
    con.execute("INSERT INTO spell_defs(id,room_id,class_name,name,level,data_json) VALUES(?,?,?,?,?,?)", (idx, 1, cls, name, level, json.dumps({"name": name, "level": level, "desc": ""})))
con.commit()

# Custom class with Wizard-like settings behaves Wizard-like without being named Wizard.
state = {
    "class_name": "BookCaster", "race_name": "", "level": 1,
    "advanced_moves": [], "extra_moves": [], "move_choices": {}, "extra_spells": [],
    "spellbook": ["B1A", "B1B"], "prepared_spells": [], "spell_tracks": [],
}
try:
    srv.validate_spellcasting_state(con, 1, state, classes, enforce_limits=True, strict=True)
    over_cap_rejected = False
except srv.HTTPException:
    over_cap_rejected = True
ok("custom_selected_profile_enforced", over_cap_rejected)

# All-known source class requires no fake spellbook state and can prepare directly.
state = {
    "class_name": "AllCaster", "race_name": "", "level": 2,
    "advanced_moves": [], "extra_moves": [], "move_choices": {}, "extra_spells": [],
    "spellbook": ["A1"], "prepared_spells": ["A1", "A2"], "spell_tracks": {},
}
srv.validate_spellcasting_state(con, 1, state, classes, enforce_limits=True, strict=True)
ok("all_known_clears_redundant_book", state["spellbook"] == [])
ok("all_known_prepares_directly", state["prepared_spells"] == ["A1", "A2"])

# Direct class_access inherits source-class profile and effective source level.
state = {
    "class_name": "Carrier", "race_name": "", "level": 3,
    "advanced_moves": ["Gain All"], "extra_moves": [],
    "move_choices": {"carrier.gain": {"acquired_at_level": 2}}, "extra_spells": [],
    "spellbook": [], "prepared_spells": [],
    "spell_tracks": {"carrier.gain": {"known": ["A1"], "prepared": ["A1", "A2"], "starting_complete": False}},
}
srv.validate_move_choices(con, 1, state, classes, strict=True)
srv.validate_spellcasting_state(con, 1, state, classes, enforce_limits=True, strict=True)
track = state["spell_tracks"]["carrier.gain"]
ok("class_access_uses_source_all_known", track["known"] == [])
ok("class_access_effective_level_2", track["prepared"] == ["A1", "A2"])

# If another class multiclasses into a move that itself grants class access, the
# source move's metadata remains active instead of being lost in copied display text.
state = {
    "class_name": "Carrier", "race_name": "", "level": 3,
    "advanced_moves": [],
    "extra_moves": [{"source_class": "Source", "name": "Nested Gain", "bundle": False, "acquired_at_level": 3}],
    "move_choices": {"source.nested": {"acquired_at_level": 3}}, "extra_spells": [],
    "spellbook": [], "prepared_spells": [],
    "spell_tracks": {"source.nested": {"known": [], "prepared": ["A1"], "starting_complete": False}},
}
rows = srv._active_move_effect_rows(state, classes)
ok("nested_multiclass_class_access_active", any(r["key"] == "source.nested" and r["effect"].get("source_class") == "AllCaster" for r in rows))
srv.validate_move_choices(con, 1, state, classes, strict=True)
srv.validate_spellcasting_state(con, 1, state, classes, enforce_limits=True, strict=True)
ok("nested_multiclass_spell_track_survives", state["spell_tracks"].get("source.nested", {}).get("prepared") == ["A1"])

if fails:
    print("FAIL")
    for f in fails:
        print(" -", f)
    raise SystemExit(1)
print(f"PASS {passed}/{passed}")
