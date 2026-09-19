from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import ipaddress
import socket
import subprocess
import threading
import time
import secrets
import shutil
import sqlite3
import string
import zipfile
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
_PUBLIC_DB = BASE_DIR / "dungeonworld.db"
_LEGACY_DB = BASE_DIR / "dungeonworld_beta.db"
DB_PATH = Path(os.environ.get("DW_DB", _PUBLIC_DB if (_PUBLIC_DB.exists() or not _LEGACY_DB.exists()) else _LEGACY_DB))
SEED_PATH = BASE_DIR / "data" / "seed_data.json"
MONSTER_SEED_PATH = BASE_DIR / "data" / "monster_seed.json"
STATIC_DIR = BASE_DIR / "static"
SOUND_DIR = DB_PATH.parent / "sounds"
DWPACK_REFERENCE_PATH = BASE_DIR / "dwpack" / "DungeonWorld_DWPack_Reference.zip"
DWPACK_CORE_PATH = BASE_DIR / "dwpack" / "DungeonWorld_1E_Core.dwpack"
DWPACK_CORE_EN_PATH = BASE_DIR / "dwpack" / "DungeonWorld_1E_Core_EN.dwpack"
DWPACK_EXPANSION_PATH = BASE_DIR / "dwpack" / "UnlimitedDungeons_DistantShore_Expansions.dwpack"
DWPACK_EXPANSION_EN_PATH = BASE_DIR / "dwpack" / "UnlimitedDungeons_DistantShore_Expansions_EN.dwpack"
DWPACK_FORMAT = "dungeonworld-data-pack"
DWPACK_FORMAT_VERSION = 1
DWPACK_MAX_UPLOAD_BYTES = 8 * 1024 * 1024
DWPACK_MAX_UNCOMPRESSED_BYTES = 24 * 1024 * 1024
SOUND_DIR.mkdir(parents=True, exist_ok=True)
VERSION = "1.0.0"
SCHEMA_VERSION = 20
DEFAULT_DATA_REVISION = "1.0.0"
SERVER_PORT = int(os.environ.get("DW_PORT", "8000"))
MAX_SOUND_UPLOAD_BYTES = 50 * 1024 * 1024
BUILD_ID_PATH = BASE_DIR / "BUILD_ID"
try:
    BUILD_ID = BUILD_ID_PATH.read_text(encoding="utf-8").strip() or "dev"
except Exception:
    BUILD_ID = "dev"

SERVER_STARTED_AT = time.time()
SERVER_INSTANCE_ID = secrets.token_hex(6)
ACTIVE_CAMPAIGN_LOCK = threading.Lock()
ACTIVE_CAMPAIGN_CODE = ""
NETWORK_ADDRESS_CACHE_LOCK = threading.Lock()
NETWORK_ADDRESS_CACHE: tuple[float, list[dict[str, str]]] = (0.0, [])
NETWORK_ADDRESS_CACHE_TTL = 5.0

app = FastAPI(title="Dungeon World Online", version=VERSION)


@app.exception_handler(sqlite3.DatabaseError)
async def sqlite_error_handler(request: Request, exc: sqlite3.DatabaseError):
    return JSONResponse(status_code=500, content={"detail": "로컬 데이터베이스를 읽는 중 문제가 발생했습니다. 런처의 데이터 관리에서 백업 후 초기화를 시도해주세요.", "error_type": "database"})


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    # HTTPException은 FastAPI 기본 처리기가 먼저 처리한다. 여기에는 예기치 않은 오류만 온다.
    return JSONResponse(status_code=500, content={"detail": "예기치 않은 서버 오류가 발생했습니다. 서버 로그를 확인해주세요.", "error_type": "unexpected"})


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_spell_level(value: str | int) -> str:
    """Store numeric spell levels as integers 1..10; any non-numeric label is a level-0 category."""
    raw = str(value).strip()
    if not raw:
        raise HTTPException(400, "주문 레벨 / 분류를 입력하세요.")
    # Values that look numeric must be whole-number levels from 1 through 10.
    if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", raw):
        try:
            num = float(raw)
        except ValueError:
            raise HTTPException(400, "숫자 주문 레벨은 1~10의 정수만 사용할 수 있습니다.")
        if not num.is_integer() or not 1 <= int(num) <= 10:
            raise HTTPException(400, "숫자 주문 레벨은 1~10의 정수만 사용할 수 있습니다.")
        return str(int(num))
    # Text categories such as 간편 / 암송 are intentionally treated as effective level 0.
    return raw

def hash_password(password: str) -> str:
    """PBKDF2 password hash. Empty passwords remain empty for passwordless rooms."""
    if not password:
        return ""
    salt = secrets.token_bytes(16)
    rounds = 210_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    return f"pbkdf2_sha256${rounds}${salt.hex()}${digest.hex()}"

def verify_password(password: str, stored: str) -> bool:
    if not stored:
        return password == ""
    if stored.startswith("pbkdf2_sha256$"):
        try:
            _, rounds, salt_hex, digest_hex = stored.split("$", 3)
            digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds))
            return secrets.compare_digest(digest.hex(), digest_hex)
        except Exception:
            return False
    # Older development builds used a single SHA-256 digest. Accept it so existing campaigns remain usable.
    return secrets.compare_digest(stored, hash_token(password))


@contextmanager
def db():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 30000")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def jdump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def jload(value: str | None, default: Any = None) -> Any:
    if value is None:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


DEFAULT_RULES = {
    "stat_start": [16, 15, 13, 12, 9, 8],
    "stat_min": 3,
    "stat_max": 18,
    "level_max": 10,
    "max_expansions_per_character": 3,
    "players_can_add_extra_moves": True,
    "stat_mod_ranges": [
        {"max": 3, "mod": -3}, {"max": 5, "mod": -2}, {"max": 8, "mod": -1},
        {"max": 12, "mod": 0}, {"max": 15, "mod": 1}, {"max": 17, "mod": 2}, {"max": 99, "mod": 3},
    ],
    "currency_name": "닢",
    "xp_base": 7,
    # 원작의 예비(hold)는 행동별로 따로 쓰이므로 공통 상한은 없습니다.
    # 이 앱의 공용 예비 트래커는 0을 "제한 없음"으로 사용하고 GM이 필요하면 상한을 지정합니다.
    "reserve_max": 0,
    # Dungeon World 원작: 동전 100닢은 1무게로 취급할 수 있다.
    # 새 캠페인은 원작값을 따르고, schema 15 이전 캠페인은 migration에서 OFF로 보존한다.
    "coin_weight_enabled": True,
    "coin_weight_per": 100,
    "monster_tags": [
        "마법적", "신성", "음흉함", "부정형", "조직적", "지능적", "보물지기", "은밀",
        "끔찍함", "조심스러움", "인공물", "이계", "대집단", "소집단", "외톨이",
        "매우 작음", "작음", "큼", "거대", "괴력", "파괴적", "장갑 무시",
        "반걸음", "한걸음", "몇걸음", "중거리", "장거리"
    ],
}

DEFAULT_SETTINGS = {
    "gm_dice_public": True,
    "gm_color": "#8b1e1e",
    "player_colors": {},
    # 확장직업은 Dungeon World 1E 원작 규칙이 아니라 Unlimited Dungeons의
    # Distant Shore Pack 계열에서 가져온 선택 규칙이다. 새 캠페인은 기본 OFF.
    "expansions_enabled": False,
}

DW_SOURCE_URLS = {
    # Dungeon World English original / official references.
    "en_home": "https://www.dungeon-world.com/",
    "en_about": "https://www.dungeon-world.com/about/",
    "en_downloads": "https://www.dungeon-world.com/downloads/",
    "en_source": "https://github.com/Sagelt/Dungeon-World",
    "cc_by": "https://creativecommons.org/licenses/by/3.0/",
    "dw_license": "https://github.com/Sagelt/Dungeon-World/blob/master/LICENSE",
    "srd_51": "https://www.dndbeyond.com/srd",
    "cc_by_4": "https://creativecommons.org/licenses/by/4.0/",

    # Korean public translation actually used while structuring Korean rules text.
    # The help UI exposes one representative home link instead of repeating deep links.
    "ko_home": "https://sites.google.com/view/dwtemporary/%ED%99%88?authuser=0",

    # Optional fan-created expansion rules. The Korean translation is a real source we
    # consulted, so its attribution remains. The English link is labelled as a community
    # archive/reference because the original distribution links have moved over time.
    "ud_home": "https://sites.google.com/view/unlimiteddungeonskr/",
    "ud_en_reference": "https://drive.google.com/file/d/1JIOhe5uSeZM4rkqeOJaQC7CQ1lOyRhRB/view",
    "cc_by_sa_4": "https://creativecommons.org/licenses/by-sa/4.0/",

    # Compatibility aliases for older clients/data that still request deep-link keys.
    # They intentionally resolve to the representative home pages now.
    "ko_play": "https://sites.google.com/view/dwtemporary/%ED%99%88?authuser=0",
    "ko_master": "https://sites.google.com/view/dwtemporary/%ED%99%88?authuser=0",
    "ko_equipment": "https://sites.google.com/view/dwtemporary/%ED%99%88?authuser=0",
    "home": "https://sites.google.com/view/dwtemporary/%ED%99%88?authuser=0",
    "play": "https://sites.google.com/view/dwtemporary/%ED%99%88?authuser=0",
    "character": "https://sites.google.com/view/dwtemporary/%ED%99%88?authuser=0",
    "moves": "https://sites.google.com/view/dwtemporary/%ED%99%88?authuser=0",
    "classes": "https://sites.google.com/view/dwtemporary/%ED%99%88?authuser=0",
    "master": "https://sites.google.com/view/dwtemporary/%ED%99%88?authuser=0",
    "monsters": "https://sites.google.com/view/dwtemporary/%ED%99%88?authuser=0",
    "equipment": "https://sites.google.com/view/dwtemporary/%ED%99%88?authuser=0",
    "npc": "https://sites.google.com/view/dwtemporary/%ED%99%88?authuser=0",
    "ud_expansions": "https://sites.google.com/view/unlimiteddungeonskr/",
    "expansions": "https://sites.google.com/view/unlimiteddungeonskr/",
}
DW_MONSTER_ENVIRONMENTS = ["캄캄한 동굴","부글거리는 늪지","언데드 군단","어두운 숲속","이민족의 무리","뒤틀린 실험체","깊고도 깊은 곳","이계의 존재","사람들"]


def table_columns(con: sqlite3.Connection, table: str) -> set[str]:
    return {r["name"] for r in con.execute(f"PRAGMA table_info({table})")}


def _ensure_column(con: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    if column not in table_columns(con, table):
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def _schema_version(con: sqlite3.Connection) -> int:
    try:
        row = con.execute("SELECT value FROM app_meta WHERE key='schema_version'").fetchone()
        return int(row["value"]) if row else 0
    except Exception:
        return 0


def _set_schema_version(con: sqlite3.Connection, version: int) -> None:
    con.execute(
        "INSERT INTO app_meta(key,value) VALUES('schema_version',?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (str(version),),
    )


def init_db() -> None:
    """Create the current schema and migrate older databases exactly once.

    Earlier builds re-ran many normalization passes on every launch. The current
    keeps schema migration separate from ordinary startup so opening a campaign
    cannot silently rewrite valid GM custom data over and over.
    """
    with db() as con:
        # WAL is a database-level setting. Set it during initialization instead of
        # renegotiating journal mode on every short-lived API connection.
        con.execute("PRAGMA journal_mode = WAL")
        con.execute("CREATE TABLE IF NOT EXISTS app_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        old_version = _schema_version(con)
        if old_version > SCHEMA_VERSION:
            raise RuntimeError(f"이 DB는 더 새로운 스키마({old_version})로 만들어졌습니다. 현재 앱 스키마는 {SCHEMA_VERSION}입니다.")
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                gm_name TEXT NOT NULL,
                gm_token_hash TEXT NOT NULL,
                rules_json TEXT NOT NULL,
                campaign_name TEXT NOT NULL DEFAULT '새 캠페인',
                password_hash TEXT NOT NULL DEFAULT '',
                settings_json TEXT NOT NULL DEFAULT '{}',
                default_data_initialized INTEGER NOT NULL DEFAULT 1,
                default_data_revision TEXT NOT NULL DEFAULT '',
                max_players INTEGER NOT NULL DEFAULT 4,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                role TEXT NOT NULL DEFAULT 'player',
                display_name TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                member_id INTEGER UNIQUE NOT NULL REFERENCES members(id) ON DELETE CASCADE,
                state_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS class_defs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                data_json TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 9999,
                UNIQUE(room_id, name)
            );
            CREATE TABLE IF NOT EXISTS race_defs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                data_json TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 9999,
                UNIQUE(room_id, name)
            );
            CREATE TABLE IF NOT EXISTS spell_defs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                class_name TEXT NOT NULL,
                name TEXT NOT NULL,
                level TEXT NOT NULL,
                data_json TEXT NOT NULL,
                UNIQUE(room_id, class_name, name)
            );
            CREATE TABLE IF NOT EXISTS core_moves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                data_json TEXT NOT NULL,
                UNIQUE(room_id, name)
            );
            CREATE TABLE IF NOT EXISTS expansion_defs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                gm_condition TEXT NOT NULL DEFAULT '',
                public_intro TEXT NOT NULL DEFAULT '',
                data_json TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 9999,
                builtin_key TEXT NOT NULL DEFAULT '',
                user_modified INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                UNIQUE(room_id, name)
            );
            CREATE TABLE IF NOT EXISTS expansion_grants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
                expansion_id INTEGER NOT NULL REFERENCES expansion_defs(id) ON DELETE CASCADE,
                visible_to_party INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'accepted',
                invite_message TEXT NOT NULL DEFAULT '',
                responded_at TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(character_id, expansion_id)
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                session_no INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                UNIQUE(room_id, session_no)
            );
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                session_id INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
                actor_role TEXT NOT NULL,
                actor_name TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT NOT NULL DEFAULT '',
                detail_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sound_defs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                kind TEXT NOT NULL,
                name TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 9999,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS npc_defs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                data_json TEXT NOT NULL DEFAULT '{}',
                favorite INTEGER NOT NULL DEFAULT 0,
                sort_order INTEGER NOT NULL DEFAULT 9999,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS monster_folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 9999,
                created_at TEXT NOT NULL,
                UNIQUE(room_id, name)
            );
            CREATE TABLE IF NOT EXISTS monster_defs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                folder_id INTEGER REFERENCES monster_folders(id) ON DELETE SET NULL,
                name TEXT NOT NULL,
                data_json TEXT NOT NULL DEFAULT '{}',
                sort_order INTEGER NOT NULL DEFAULT 9999,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS monster_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                monster_id INTEGER NOT NULL REFERENCES monster_defs(id) ON DELETE CASCADE,
                reveal_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(room_id, monster_id)
            );
            CREATE TABLE IF NOT EXISTS gm_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                token_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_used_at TEXT NOT NULL,
                UNIQUE(room_id, token_hash)
            );
            """
        )

        # Structural compatibility with old DBs. These checks are tiny and safe
        # to perform on every startup; data migrations below are version-gated.
        _ensure_column(con, "rooms", "campaign_name", "TEXT NOT NULL DEFAULT '새 캠페인'")
        _ensure_column(con, "rooms", "updated_at", "TEXT")
        _ensure_column(con, "rooms", "password_hash", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(con, "rooms", "settings_json", "TEXT NOT NULL DEFAULT '{}'")
        _ensure_column(con, "rooms", "default_data_initialized", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(con, "rooms", "default_data_revision", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(con, "rooms", "max_players", "INTEGER NOT NULL DEFAULT 4")
        _ensure_column(con, "expansion_grants", "status", "TEXT NOT NULL DEFAULT 'accepted'")
        _ensure_column(con, "expansion_grants", "invite_message", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(con, "expansion_grants", "responded_at", "TEXT")
        _ensure_column(con, "logs", "session_id", "INTEGER REFERENCES sessions(id) ON DELETE SET NULL")
        for table in ("class_defs", "race_defs", "npc_defs", "monster_defs"):
            _ensure_column(con, table, "sort_order", "INTEGER NOT NULL DEFAULT 9999")
        _ensure_column(con, "npc_defs", "favorite", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(con, "expansion_defs", "sort_order", "INTEGER NOT NULL DEFAULT 9999")
        _ensure_column(con, "expansion_defs", "builtin_key", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(con, "expansion_defs", "user_modified", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(con, "sound_defs", "sort_order", "INTEGER NOT NULL DEFAULT 9999")
        _ensure_column(con, "members", "reconnect_code_hash", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(con, "members", "disabled", "INTEGER NOT NULL DEFAULT 0")
        con.execute("UPDATE rooms SET updated_at=COALESCE(updated_at,created_at)")

        # 새 컬럼을 먼저 보장한 뒤 그 컬럼을 사용하는 인덱스를 만든다.
        # Older DBs may not have favorite/sort_order yet, so migration order matters.
        con.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_members_room ON members(room_id);
            CREATE INDEX IF NOT EXISTS idx_members_room_token ON members(room_id, token_hash);
            CREATE INDEX IF NOT EXISTS idx_members_room_reconnect ON members(room_id, reconnect_code_hash);
            CREATE INDEX IF NOT EXISTS idx_chars_room ON characters(room_id);
            CREATE INDEX IF NOT EXISTS idx_logs_room ON logs(room_id, id DESC);
            CREATE INDEX IF NOT EXISTS idx_sessions_room ON sessions(room_id, session_no DESC);
            CREATE INDEX IF NOT EXISTS idx_npc_room_v2 ON npc_defs(room_id, favorite DESC, sort_order, id);
            CREATE INDEX IF NOT EXISTS idx_monster_folder_room ON monster_folders(room_id, sort_order, id);
            CREATE INDEX IF NOT EXISTS idx_monster_room_v2 ON monster_defs(room_id, folder_id, sort_order, id);
            CREATE INDEX IF NOT EXISTS idx_monster_catalog_room ON monster_catalog(room_id, monster_id);
            CREATE INDEX IF NOT EXISTS idx_expansion_room_v2 ON expansion_defs(room_id, sort_order, id);
            CREATE INDEX IF NOT EXISTS idx_expansion_grants_character_status ON expansion_grants(character_id, status, id);
            CREATE INDEX IF NOT EXISTS idx_expansion_grants_room_expansion ON expansion_grants(room_id, expansion_id, status);
            CREATE INDEX IF NOT EXISTS idx_sound_room_v2 ON sound_defs(room_id, kind, sort_order, id);
            CREATE INDEX IF NOT EXISTS idx_gm_sessions_room ON gm_sessions(room_id, last_used_at DESC, id DESC);
            CREATE INDEX IF NOT EXISTS idx_gm_sessions_room_token ON gm_sessions(room_id, token_hash);
            """
        )

        if old_version < 9:
            # Migrate older table structure once; do not reapply to current DBs.
            for table in ("class_defs", "race_defs", "npc_defs", "monster_defs"):
                rows = list(con.execute(f"SELECT id FROM {table} WHERE sort_order=9999 ORDER BY id"))
                for idx, row in enumerate(rows, 1):
                    con.execute(f"UPDATE {table} SET sort_order=? WHERE id=?", (idx, row["id"]))
            for row in con.execute("SELECT id,data_json FROM class_defs"):
                raw = jload(row["data_json"], {}) or {}
                changed = False
                for key, flag in (("a25", "multiclass_25"), ("a610", "multiclass_610")):
                    moves = list(raw.get(key) or [])
                    special = [m for m in moves if isinstance(m, dict) and str(m.get("name", "")).startswith("다중직업 (")]
                    if special:
                        raw[flag] = True
                        raw[key] = [m for m in moves if m not in special]
                        changed = True
                    elif flag not in raw:
                        raw[flag] = False
                        changed = True
                if changed:
                    con.execute("UPDATE class_defs SET data_json=? WHERE id=?", (jdump(raw), row["id"]))
            for row in con.execute("SELECT id,data_json FROM npc_defs"):
                raw = jload(row["data_json"], {}) or {}
                con.execute("UPDATE npc_defs SET favorite=? WHERE id=?", (1 if raw.get("favorite") else 0, row["id"]))
            for row in con.execute("SELECT id,data_json FROM expansion_defs"):
                raw = jload(row["data_json"], {}) or {}
                order = int(raw.get("sort_order", 9999) or 9999)
                builtin = bool(raw.get("builtin"))
                con.execute("UPDATE expansion_defs SET sort_order=?,builtin_key=CASE WHEN ? THEN name ELSE builtin_key END WHERE id=?", (order, 1 if builtin else 0, row["id"]))
            migrate_legacy_payloads(con)
            # schema 6 이하에는 race_defs가 없었으므로 그 경우에만 옛 직업 데이터에서
            # 최초 1회 변환한다. schema 7+에서 race_defs가 비어 있으면 GM이 지운 상태다.
            if old_version < 7:
                ensure_race_defs(con)
                for room in con.execute("SELECT id FROM rooms"):
                    ensure_default_race_spell_effects(con, int(room["id"]))

        if old_version < 10:
            # 첫 참가 온보딩 상태를 명시적으로 저장한다. 기존 직업 보유 캐릭터는 완료,
            # Preserve an explicit false value from older character records.
            classes_by_room: dict[int, dict[str, dict[str, Any]]] = {}
            for row in con.execute("SELECT id,room_id,state_json FROM characters"):
                room_id = int(row["room_id"])
                classes = classes_by_room.setdefault(room_id, class_map(con, room_id))
                state = normalize_character_state(jload(row["state_json"], {}) or {}, classes)
                con.execute("UPDATE characters SET state_json=? WHERE id=?", (jdump(state), row["id"]))

        if old_version < 11:
            # Bundled data is only a template for new campaigns. Existing campaigns keep their DB
            # 절대 원본으로 인정하고, 빠진 기본 직업/종족/몬스터 등을 자동 복구하지 않는다.
            con.execute("UPDATE rooms SET default_data_initialized=1 WHERE default_data_initialized IS NULL OR default_data_initialized=0")
            con.execute("UPDATE rooms SET default_data_revision=CASE WHEN default_data_revision='' THEN 'legacy' ELSE default_data_revision END")
            migrate_race_spell_effect_metadata(con)

        if old_version < 12:
            # Unify older racial spell feature formats into canonical spell_effects.
            # Legacy spell_access is consumed during normalization and is not re-emitted.
            for rr in con.execute("SELECT id,data_json FROM race_defs"):
                normalized = normalize_race_data(jload(rr["data_json"], {}) or {})
                con.execute("UPDATE race_defs SET data_json=? WHERE id=?", (jdump(normalized), rr["id"]))
            # The dwarf cleric racial feature is a separate stone-only unclassified
            # chant, not a global level reduction of the cleric spell.
            migrate_dwarf_cleric_stone_speech(con)

        if old_version < 13:
            # Display-only correction for the bundled Dwarf cleric racial chant.
            migrate_stone_speech_display_name(con)

        if old_version < 14:
            # Starting gear is kept in inventory/help instead of being injected into free memo.
            # Keep any text the player wrote after the old marker and introduce a
            # structured inventory list without trying to guess their chosen gear.
            classes_by_room: dict[int, dict[str, dict[str, Any]]] = {}
            for row in con.execute("SELECT id,room_id,state_json FROM characters"):
                room_id = int(row["room_id"])
                classes = classes_by_room.setdefault(room_id, class_map(con, room_id))
                raw = dict(jload(row["state_json"], {}) or {})
                raw.setdefault("inventory", [])
                cls = classes.get(str(raw.get("class_name", "")), {})
                gear = str(cls.get("gear", "") or "")
                memo = str(raw.get("memo", "") or "")
                prefix = gear + "\n\n[자유 메모]\n" if gear else ""
                if prefix and memo.startswith(prefix):
                    raw["memo"] = memo[len(prefix):]
                state = normalize_character_state(raw, classes)
                con.execute("UPDATE characters SET state_json=? WHERE id=?", (jdump(state), row["id"]))

        if old_version < 15:
            # Expansion classes are an explicit optional
            # campaign rule. Existing campaigns keep the feature ON so an update cannot
            # silently hide accepted expansion paths; newly created campaigns default OFF.
            for room in con.execute("SELECT id,settings_json FROM rooms"):
                raw_settings = dict(jload(room["settings_json"], {}) or {})
                if "expansions_enabled" not in raw_settings:
                    raw_settings["expansions_enabled"] = True
                    con.execute("UPDATE rooms SET settings_json=? WHERE id=?", (jdump(normalize_settings(raw_settings)), room["id"]))

        if old_version < 16:
            # Coin/load handling is an explicit optional rule.
            # Existing campaigns did not count currency toward load, so preserve that
            # behavior on migration. Brand-new campaigns use the original 100 coin = 1 weight rule.
            for room in con.execute("SELECT id,rules_json FROM rooms"):
                raw_rules = dict(jload(room["rules_json"], {}) or {})
                if "coin_weight_enabled" not in raw_rules:
                    raw_rules["coin_weight_enabled"] = False
                    raw_rules["coin_weight_per"] = 100
                    con.execute("UPDATE rooms SET rules_json=? WHERE id=?", (jdump(normalize_rules(raw_rules)), room["id"]))

        if old_version < 17:
            # Move-grant metadata was previously only prose. Add structured effects to
            # matching bundled class moves without changing any GM-edited description.
            # Existing explicit move_effects always win.
            try:
                seeded_classes = dict((json.loads(SEED_PATH.read_text(encoding="utf-8")) or {}).get("classes") or {})
            except Exception:
                seeded_classes = {}
            for row in con.execute("SELECT id,name,data_json FROM class_defs"):
                seed_class = seeded_classes.get(str(row["name"]))
                if not isinstance(seed_class, dict):
                    continue
                raw = dict(jload(row["data_json"], {}) or {})
                changed = False
                for section in ("start", "a25", "a610"):
                    seed_by_name = {str(m.get("name", "")): m for m in (seed_class.get(section) or []) if isinstance(m, dict)}
                    for move in raw.get(section) or []:
                        if not isinstance(move, dict) or move.get("move_effects"):
                            continue
                        seeded = seed_by_name.get(str(move.get("name", "")))
                        if seeded and seeded.get("move_effects"):
                            move["move_effects"] = seeded["move_effects"]
                            changed = True
                if changed:
                    con.execute("UPDATE class_defs SET data_json=? WHERE id=?", (jdump(normalize_class_data(raw)), row["id"]))
            classes_by_room: dict[int, dict[str, dict[str, Any]]] = {}
            for row in con.execute("SELECT id,room_id,state_json FROM characters"):
                room_id = int(row["room_id"]); classes = classes_by_room.setdefault(room_id, class_map(con, room_id))
                state = normalize_character_state(jload(row["state_json"], {}) or {}, classes)
                con.execute("UPDATE characters SET state_json=? WHERE id=?", (jdump(state), row["id"]))

        if old_version < 18:
            # Public v1.0.0 retains the uploaded-audio-only policy. Remove obsolete sound
            # definitions from older builds so only supported file-backed entries remain.
            con.execute("DELETE FROM sound_defs WHERE source_type<>'file'")

        if old_version < 19:
            # Public v1.0.0 tracks Dungeon World ammo as a separate inventory resource
            # item instead of attaching ammo directly to ranged weapons.  Preserve any
            # existing weapon ammo by moving it into an adjacent Ammo item once.
            classes_by_room: dict[int, dict[str, dict[str, Any]]] = {}
            for row in con.execute("SELECT id,room_id,state_json FROM characters"):
                room_id = int(row["room_id"]); classes = classes_by_room.setdefault(room_id, class_map(con, room_id))
                raw = dict(jload(row["state_json"], {}) or {})
                migrated: list[dict[str, Any]] = []
                # Read legacy ammo from the pre-schema-19 row before ordinary
                # normalization. normalize_inventory intentionally strips ammo from
                # non-Ammo items now, so doing this in the opposite order would lose
                # v2 weapon ammo during migration. Tag forms such as "발수 3" are
                # preserved as well.
                for legacy_item in list(raw.get("inventory") or []):
                    if not isinstance(legacy_item, dict):
                        continue
                    legacy = dict(legacy_item)
                    tags = str(legacy.get("tags", "") or "")
                    try:
                        legacy_max = max(0, min(9999, int(legacy.get("ammo_max", 0) or 0)))
                    except (TypeError, ValueError):
                        legacy_max = 0
                    if "ammo_max" not in legacy or legacy_max <= 0:
                        m = re.search(r"(?:탄약|발수)\s*(\d+)", tags)
                        if m:
                            legacy_max = min(9999, int(m.group(1)))
                    try:
                        legacy_current = max(0, int(legacy.get("ammo_current", legacy_max) or 0))
                    except (TypeError, ValueError):
                        legacy_current = legacy_max
                    if legacy_max > 0:
                        legacy_current = min(legacy_current, legacy_max)

                    normalized_rows = normalize_inventory([legacy])
                    if not normalized_rows:
                        continue
                    cur = dict(normalized_rows[0])
                    item_type = infer_inventory_item_type(cur)
                    migrated.append(cur)
                    if item_type != "탄약" and legacy_max > 0:
                        migrated.append({
                            "name": "탄약",
                            "item_type": "탄약", "quantity": 1, "weight": 0,
                            "uses_current": 0, "uses_max": 0,
                            "ammo_current": legacy_current, "ammo_max": legacy_max,
                            "tags": "탄약", "weapon_range": "", "damage_bonus": 0,
                            "damage": "", "armor_value": 0, "armor_bonus": 0,
                            "note": "",
                        })
                raw["inventory"] = migrated
                state = normalize_character_state(raw, classes)
                con.execute("UPDATE characters SET state_json=? WHERE id=?", (jdump(state), row["id"]))

        if old_version < 20:
            # Campaign capacity was previously unlimited. New campaigns default to four
            # player seats (GM excluded), while migrated campaigns preserve up to the
            # new public ceiling of eight seats when they already have more players.
            for room_row in con.execute("SELECT id FROM rooms"):
                active_players = int(con.execute(
                    "SELECT COUNT(*) n FROM members WHERE room_id=? AND role='player' AND disabled=0",
                    (room_row["id"],),
                ).fetchone()["n"])
                max_players = min(8, max(4, active_players))
                con.execute("UPDATE rooms SET max_players=? WHERE id=?", (max_players, room_row["id"]))

        # Spellcasting rules live in class JSON, so v1.0.0 can gain the data-driven
        # model without a SQL schema bump. Old campaigns are backfilled once and custom
        # classes retain permissive/manual behavior until a GM changes their profile.
        ensure_spellcasting_profiles(con)

        if old_version < SCHEMA_VERSION:
            _set_schema_version(con, SCHEMA_VERSION)

        # Ordinary startup deliberately does not seed game definitions.  The campaign DB
        # is authoritative after creation; deleting a built-in item is a permanent GM choice.
        cleanup_orphan_sound_dirs(con)


def seed_payload() -> dict[str, Any]:
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def monster_seed_payload() -> list[dict[str, Any]]:
    if not MONSTER_SEED_PATH.exists():
        raise RuntimeError("기본 몬스터 seed 파일을 찾을 수 없습니다.")
    try:
        raw = json.loads(MONSTER_SEED_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError("기본 몬스터 seed 파일을 읽을 수 없습니다.") from exc
    if not isinstance(raw, list):
        raise RuntimeError("기본 몬스터 seed 형식이 올바르지 않습니다.")
    return raw


def ensure_builtin_monsters(con: sqlite3.Connection, room_id: int) -> None:
    folders = {r["name"]: int(r["id"]) for r in con.execute("SELECT id,name FROM monster_folders WHERE room_id=?", (room_id,))}
    existing_keys: set[str] = set()
    for row in con.execute("SELECT data_json FROM monster_defs WHERE room_id=?", (room_id,)):
        data = jload(row["data_json"], {}) or {}
        key = str(data.get("builtin_key", "")).strip()
        if key:
            existing_keys.add(key)
    per_folder_next: dict[int | None, int] = {}
    for item in monster_seed_payload():
        key = str(item.get("key", "")).strip()
        if not key or key in existing_keys:
            continue
        folder_name = str(item.get("folder", "")).strip()
        folder_id = folders.get(folder_name)
        if folder_id is None and folder_name:
            order = int(con.execute("SELECT COALESCE(MAX(sort_order),0)+1 n FROM monster_folders WHERE room_id=?", (room_id,)).fetchone()["n"])
            cur = con.execute("INSERT INTO monster_folders(room_id,name,sort_order,created_at) VALUES(?,?,?,?)", (room_id, folder_name, order, now_iso()))
            folder_id = int(cur.lastrowid)
            folders[folder_name] = folder_id
        if folder_id not in per_folder_next:
            per_folder_next[folder_id] = int(con.execute("SELECT COALESCE(MAX(sort_order),0)+1 n FROM monster_defs WHERE room_id=? AND folder_id IS ?", (room_id, folder_id)).fetchone()["n"])
        data = {
            "hp": item.get("hp", 0), "armor": item.get("armor", 0),
            "attack": item.get("attack_name", ""), "damage": item.get("damage", {}),
            "range": item.get("range", ""), "tags": item.get("tags", []),
            "instinct": item.get("instinct", ""), "special": item.get("special", ""),
            "moves": item.get("moves", []), "description": item.get("description", ""),
            "source_url": DW_SOURCE_URLS["monsters"], "builtin_key": key, "builtin": True,
        }
        now = now_iso()
        con.execute("INSERT INTO monster_defs(room_id,folder_id,name,data_json,sort_order,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                    (room_id, folder_id, str(item.get("name", key))[:120], jdump(normalize_monster_data(data)), per_folder_next[folder_id], now, now))
        per_folder_next[folder_id] += 1
        existing_keys.add(key)


def flatten_expansion_move(move: dict[str, Any] | None) -> dict[str, str]:
    m = dict(move or {})
    name = str(m.get("name", ""))
    if not any(k in m for k in ("trigger", "roll", "success", "result_12", "result_10", "result_7", "result_6", "choices", "notes")):
        return {"name": name, "desc": str(m.get("desc", ""))}
    parts: list[str] = []
    labels = (("trigger", "발동"), ("roll", "판정"), ("success", "성공"), ("result_12", "12+"), ("result_10", "10+"), ("result_7", "7–9"), ("result_6", "6-"))
    for key, label in labels:
        value = str(m.get(key, "") or "").strip()
        if value:
            parts.append(f"{label}: {value}")
    choices = [str(x) for x in (m.get("choices") or []) if str(x).strip()]
    if choices:
        parts.append("선택지:\n" + "\n".join(f"• {x}" for x in choices))
    desc = str(m.get("desc", "") or "").strip()
    if desc:
        parts.append(desc)
    notes = str(m.get("notes", "") or "").strip()
    if notes:
        parts.append(notes)
    return {"name": name, "desc": "\n\n".join(parts)}


def normalize_expansion_data(data: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize expansion data into the current compact schema.

    Older builds stored resource widgets, arbitrary fields and structured roll
    fragments.  The current editor intentionally uses one text description per
    move, so legacy structured move data is flattened once and obsolete keys are
    discarded instead of being carried through every request.
    """
    raw = dict(data or {})
    if "legend_move" not in raw:
        old = list(raw.get("moves") or [])
        raw["legend_move"] = old[0] if old else {"name": "", "desc": ""}
        raw["class_moves"] = old[1:] if len(old) > 1 else list(raw.get("class_moves") or [])

    theme = dict(raw.get("theme") or {})
    clean_theme: dict[str, str] = {}
    for key, fallback in (("page_background", "#f2f0e8"), ("background", "#ffffff"), ("text", "#181818"), ("accent", "#181818")):
        value = str(theme.get(key, fallback))
        clean_theme[key] = value if re.fullmatch(r"#[0-9A-Fa-f]{6}", value) else fallback

    try:
        sort_order = int(raw.get("sort_order", 9999))
    except Exception:
        sort_order = 9999

    resource_raw = dict(raw.get("resource") or {})
    resource_name = str(resource_raw.get("name", raw.get("resource_name", "")) or "").strip()[:60]
    try:
        resource_max = max(0, min(9999, int(resource_raw.get("max", raw.get("resource_max", 0)) or 0)))
    except Exception:
        resource_max = 0

    clean: dict[str, Any] = {
        "legend_move": flatten_expansion_move(raw.get("legend_move") or {}),
        "class_moves": [flatten_expansion_move(x) for x in (raw.get("class_moves") or [])],
        "theme": clean_theme,
        "hidden": bool(raw.get("hidden", False)),
        "sort_order": sort_order,
        # 확장직업별 개인 자원. 이름이 비어 있으면 자원 UI를 사용하지 않는다.
        # max=0은 상한 없음으로 취급한다.
        "resource": {"name": resource_name, "max": resource_max},
    }
    # Metadata used by bundled examples/editor links remains supported.
    for key in ("builtin", "source_url", "source_note"):
        if key in raw:
            clean[key] = raw[key]
    return clean


def normalize_rules(data: dict[str, Any] | None) -> dict[str, Any]:
    raw = dict(data or {})
    clean = {**DEFAULT_RULES}
    for key in DEFAULT_RULES:
        if key in raw:
            clean[key] = raw[key]
    try:
        clean["stat_start"] = [int(x) for x in (clean.get("stat_start") or [16, 15, 13, 12, 9, 8])][:6]
    except (TypeError, ValueError):
        clean["stat_start"] = [16, 15, 13, 12, 9, 8]
    if len(clean["stat_start"]) != 6:
        clean["stat_start"] = [16, 15, 13, 12, 9, 8]
    try:
        clean["stat_min"] = int(clean.get("stat_min", 3))
    except (TypeError, ValueError):
        clean["stat_min"] = 3
    try:
        clean["stat_max"] = int(clean.get("stat_max", 18))
    except (TypeError, ValueError):
        clean["stat_max"] = 18
    try:
        clean["level_max"] = max(1, min(99, int(clean.get("level_max", 10))))
    except (TypeError, ValueError):
        clean["level_max"] = 10
    try:
        clean["max_expansions_per_character"] = max(0, min(99, int(clean.get("max_expansions_per_character", 3))))
    except (TypeError, ValueError):
        clean["max_expansions_per_character"] = 3
    clean["players_can_add_extra_moves"] = bool(clean.get("players_can_add_extra_moves", True))
    clean["currency_name"] = (str(clean.get("currency_name", "닢")).strip() or "닢")[:30]
    try:
        xp_base = int(clean.get("xp_base", 7))
    except (TypeError, ValueError):
        xp_base = 7
    clean["xp_base"] = max(0, min(100, xp_base))
    try:
        clean["reserve_max"] = max(0, min(9999, int(clean.get("reserve_max", 0) or 0)))
    except (TypeError, ValueError):
        clean["reserve_max"] = 0
    clean["coin_weight_enabled"] = bool(clean.get("coin_weight_enabled", True))
    try:
        clean["coin_weight_per"] = max(1, min(100000, int(clean.get("coin_weight_per", 100) or 100)))
    except (TypeError, ValueError):
        clean["coin_weight_per"] = 100
    ranges = []
    for item in list(clean.get("stat_mod_ranges") or []):
        try:
            ranges.append({"max": int(item.get("max")), "mod": int(item.get("mod"))})
        except Exception:
            continue
    if not ranges:
        ranges = [dict(x) for x in DEFAULT_RULES["stat_mod_ranges"]]
    ranges.sort(key=lambda x: x["max"])
    clean["stat_mod_ranges"] = ranges[:20]
    tags = []
    for tag in list(clean.get("monster_tags") or []):
        text = str(tag).strip()
        if text and text not in tags:
            tags.append(text[:60])
    clean["monster_tags"] = tags[:100]
    return clean


def normalize_settings(data: dict[str, Any] | None) -> dict[str, Any]:
    raw = dict(data or {})
    clean = {**DEFAULT_SETTINGS}
    clean["gm_dice_public"] = bool(raw.get("gm_dice_public", DEFAULT_SETTINGS["gm_dice_public"]))
    gm_color = str(raw.get("gm_color", DEFAULT_SETTINGS["gm_color"]))
    clean["gm_color"] = gm_color if re.fullmatch(r"#[0-9A-Fa-f]{6}", gm_color) else DEFAULT_SETTINGS["gm_color"]
    colors: dict[str, str] = {}
    for key, value in dict(raw.get("player_colors") or {}).items():
        color = str(value)
        if re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            colors[str(key)] = color
    clean["player_colors"] = colors
    clean["expansions_enabled"] = bool(raw.get("expansions_enabled", DEFAULT_SETTINGS["expansions_enabled"]))
    return clean


def room_expansions_enabled(room: sqlite3.Row) -> bool:
    return bool(normalize_settings(jload(room["settings_json"], {}) or {}).get("expansions_enabled", False))


def normalize_npc_data(data: dict[str, Any] | None) -> dict[str, Any]:
    raw = dict(data or {})
    bonds = []
    for item in list(raw.get("bonds") or [])[:30]:
        if isinstance(item, str):
            bonds.append({"name": "", "desc": item[:1800]})
            continue
        x = dict(item or {})
        name = str(x.get("name", x.get("memo", ""))).strip()
        desc = str(x.get("desc", x.get("text", ""))).strip()
        if name or desc:
            bonds.append({"name": name[:160], "desc": desc[:1800]})
    return {
        "appearance": str(raw.get("appearance", ""))[:4000],
        "description": str(raw.get("description", ""))[:12000],
        "bonds": bonds,
        "favorite": bool(raw.get("favorite", False)),
    }


def normalize_monster_damage(value: Any) -> dict[str, Any]:
    raw = dict(value or {}) if isinstance(value, dict) else {}
    die = str(raw.get("die", "D6") or "D6").upper()
    if die not in {"D2","D4","D6","D8","D10","D12"}:
        die = "D6"
    count = max(1, min(20, int(raw.get("count", 1) or 1)))
    modifier = max(-99, min(99, int(raw.get("modifier", 0) or 0)))
    mode = str(raw.get("mode", "normal") or "normal").lower()
    if mode not in {"normal","high","low"}:
        mode = "normal"
    return {"die": die, "count": count, "modifier": modifier, "mode": mode}


def normalize_monster_data(data: dict[str, Any] | None, allowed_tags: list[str] | None = None) -> dict[str, Any]:
    raw = dict(data or {})
    tags = []
    for tag in list(raw.get("tags") or [])[:100]:
        value = str(tag).strip()
        if value and value not in tags:
            tags.append(value[:60])
    if allowed_tags is not None:
        allowed = set(allowed_tags)
        tags = [x for x in tags if x in allowed]
    moves = [str(x).strip()[:1200] for x in list(raw.get("moves") or [])[:30] if str(x).strip()]
    attack = str(raw.get("attack", ""))[:500]
    damage = raw.get("damage")
    # Migrate older values such as "깨물기 (d10+3 피해)" when possible.
    if not isinstance(damage, dict):
        m = re.search(r"(?:(고|저)\[)?(\d*)d(2|4|6|8|10|12)(?:\])?\s*([+-]\s*\d+)?", attack, re.I)
        if m:
            damage = {"die": f"D{m.group(3)}", "count": int(m.group(2) or 1), "modifier": int((m.group(4) or "0").replace(" ", "")), "mode": "high" if m.group(1)=="고" else "low" if m.group(1)=="저" else "normal"}
        else:
            damage = {"die":"D6","count":1,"modifier":0,"mode":"normal"}
    out = {
        "hp": max(0, int(raw.get("hp", 0) or 0)),
        "armor": max(0, int(raw.get("armor", 0) or 0)),
        "attack": attack,
        "damage": normalize_monster_damage(damage),
        "range": str(raw.get("range", ""))[:500],
        "tags": tags,
        "instinct": str(raw.get("instinct", ""))[:4000],
        "special": str(raw.get("special", ""))[:6000],
        "moves": moves,
        "description": str(raw.get("description", ""))[:12000],
        "source_url": str(raw.get("source_url", ""))[:1200],
    }
    for key in ("builtin_key","builtin"):
        if key in raw:
            out[key] = raw[key]
    return out


def compact_extension_state(value: dict[str, Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for grant_id, raw_state in dict(value or {}).items():
        st = dict(raw_state or {})
        out[str(grant_id)] = {
            "legend_owned": bool(st.get("legend_owned", False)),
            "class_moves_owned": list(dict.fromkeys(str(x) for x in (st.get("class_moves_owned") or []) if str(x))),
            "resource_current": max(0, int(st.get("resource_current", 0) or 0)),
        }
    return out


def migrate_legacy_payloads(con: sqlite3.Connection) -> None:
    """Remove obsolete JSON keys while keeping playable campaign data.

    This migration is idempotent, so opening an older database multiple
    times is safe.  It deliberately does not delete campaigns or authentication
    tokens.
    """
    for row in con.execute("SELECT id,rules_json,settings_json FROM rooms"):
        rules = normalize_rules(jload(row["rules_json"], {}) or {})
        raw_settings = dict(jload(row["settings_json"], {}) or {})
        # 기존 캠페인은 업데이트 후 확장직업이 갑자기 사라지지 않도록 이전과
        # 동일하게 ON으로 이관한다. 새 캠페인만 DEFAULT_SETTINGS의 OFF를 사용한다.
        if "expansions_enabled" not in raw_settings:
            raw_settings["expansions_enabled"] = True
        settings = normalize_settings(raw_settings)
        con.execute("UPDATE rooms SET rules_json=?,settings_json=? WHERE id=?", (jdump(rules), jdump(settings), row["id"]))

    for row in con.execute("SELECT id,data_json FROM expansion_defs"):
        clean = normalize_expansion_data(jload(row["data_json"], {}) or {})
        con.execute("UPDATE expansion_defs SET data_json=? WHERE id=?", (jdump(clean), row["id"]))

    classes_by_room: dict[int, dict[str, dict[str, Any]]] = {}
    for row in con.execute("SELECT id,room_id,state_json FROM characters"):
        room_id = int(row["room_id"])
        classes = classes_by_room.setdefault(room_id, class_map(con, room_id))
        state = normalize_character_state(jload(row["state_json"], {}) or {}, classes)
        allowed_grants = {str(x["id"]) for x in con.execute("SELECT id FROM expansion_grants WHERE character_id=? AND status='accepted'", (row["id"],))}
        state["extension_state"] = {k: v for k, v in (state.get("extension_state") or {}).items() if k in allowed_grants}
        con.execute("UPDATE characters SET state_json=? WHERE id=?", (jdump(state), row["id"]))

def cleanup_orphan_sound_dirs(con: sqlite3.Connection) -> None:
    valid = {str(r["code"]).upper() for r in con.execute("SELECT code FROM rooms")}
    if not SOUND_DIR.exists():
        return
    for child in SOUND_DIR.iterdir():
        if child.is_dir() and child.name.upper() not in valid:
            shutil.rmtree(child, ignore_errors=True)










def seed_races_for_room(con: sqlite3.Connection, room_id: int) -> None:
    rows = list(con.execute("SELECT name,data_json FROM class_defs WHERE room_id=? ORDER BY id", (room_id,)))
    races: dict[str, dict[str, Any]] = {}
    for row in rows:
        cname = row["name"]
        cdata = jload(row["data_json"], {}) or {}
        for race in cdata.get("races", []) or []:
            name = str(race.get("name", "")).strip()
            if not name:
                continue
            item = races.setdefault(name, {"name": name, "description": "", "per_class": {}, "enabled_classes": [], "spell_effects": {}})
            item["per_class"][cname] = str(race.get("desc", ""))
            if cname not in item["enabled_classes"]:
                item["enabled_classes"].append(cname)
    for name, data in races.items():
        con.execute("INSERT OR IGNORE INTO race_defs(room_id,name,data_json) VALUES(?,?,?)", (room_id, name, jdump(normalize_race_data(data))))
    ensure_default_race_spell_effects(con, room_id)


def ensure_race_defs(con: sqlite3.Connection) -> None:
    for room in con.execute("SELECT id FROM rooms"):
        if not con.execute("SELECT 1 FROM race_defs WHERE room_id=? LIMIT 1", (room["id"],)).fetchone():
            seed_races_for_room(con, room["id"])


def seed_room(con: sqlite3.Connection, room_id: int) -> None:
    """Copy bundled templates into a brand-new campaign exactly once."""
    seed = seed_payload()
    for move in seed.get("core", []):
        con.execute("INSERT INTO core_moves(room_id,name,data_json) VALUES(?,?,?)", (room_id, move["name"], jdump(move)))
    for class_name, cdata in seed.get("classes", {}).items():
        con.execute("INSERT INTO class_defs(room_id,name,data_json) VALUES(?,?,?)", (room_id, class_name, jdump(cdata)))
    # Spells are inserted before races so seed-time racial spell metadata can resolve IDs.
    for class_name, spells in seed.get("spells", {}).items():
        for spell in spells:
            con.execute(
                "INSERT INTO spell_defs(room_id,class_name,name,level,data_json) VALUES(?,?,?,?,?)",
                (room_id, class_name, spell["name"], str(spell.get("level", "")), jdump(spell)),
            )
    seed_races_for_room(con, room_id)
    migrate_race_spell_effect_metadata(con, room_id)
    # Optional expansion examples live in a separate .dwpack and are not seeded into new campaigns.
    for idx, name in enumerate(DW_MONSTER_ENVIRONMENTS, 1):
        con.execute("INSERT OR IGNORE INTO monster_folders(room_id,name,sort_order,created_at) VALUES(?,?,?,?)", (room_id, name, idx, now_iso()))
    ensure_builtin_monsters(con, room_id)
    con.execute("UPDATE rooms SET default_data_initialized=1,default_data_revision=? WHERE id=?", (DEFAULT_DATA_REVISION, room_id))


def import_default_data(con: sqlite3.Connection, room_id: int, kinds: set[str]) -> dict[str, int]:
    """Explicitly import missing bundled templates without overwriting GM data."""
    allowed = {"core", "classes", "races", "spells", "monsters"}
    kinds = set(kinds) & allowed
    seed = seed_payload(); counts = {k: 0 for k in allowed}
    if "core" in kinds:
        for move in seed.get("core", []):
            cur = con.execute("INSERT OR IGNORE INTO core_moves(room_id,name,data_json) VALUES(?,?,?)", (room_id, move["name"], jdump(move)))
            counts["core"] += max(0, cur.rowcount)
    if "classes" in kinds:
        order = int(con.execute("SELECT COALESCE(MAX(sort_order),0)+1 n FROM class_defs WHERE room_id=?", (room_id,)).fetchone()["n"])
        for name, data in seed.get("classes", {}).items():
            if con.execute("SELECT 1 FROM class_defs WHERE room_id=? AND name=?", (room_id, name)).fetchone():
                continue
            con.execute("INSERT INTO class_defs(room_id,name,data_json,sort_order) VALUES(?,?,?,?)", (room_id, name, jdump(data), order)); order += 1; counts["classes"] += 1
    if "spells" in kinds:
        for class_name, spells in seed.get("spells", {}).items():
            for spell in spells:
                cur = con.execute("INSERT OR IGNORE INTO spell_defs(room_id,class_name,name,level,data_json) VALUES(?,?,?,?,?)", (room_id, class_name, spell["name"], str(spell.get("level", "")), jdump(spell)))
                counts["spells"] += max(0, cur.rowcount)
    if "races" in kinds:
        # Build race templates in memory from the bundled class race cards, but only insert
        # missing race names. Existing race definitions are never merged or overwritten.
        race_templates: dict[str, dict[str, Any]] = {}
        for cname, cdata in seed.get("classes", {}).items():
            for race in cdata.get("races", []) or []:
                name = str(race.get("name", "")).strip()
                if not name: continue
                item = race_templates.setdefault(name, {"name": name, "description": "", "per_class": {}, "enabled_classes": [], "spell_effects": {}})
                item["per_class"][cname] = str(race.get("desc", ""))
                if cname not in item["enabled_classes"]: item["enabled_classes"].append(cname)
        order = int(con.execute("SELECT COALESCE(MAX(sort_order),0)+1 n FROM race_defs WHERE room_id=?", (room_id,)).fetchone()["n"])
        inserted_names=[]
        for name, data in race_templates.items():
            if con.execute("SELECT 1 FROM race_defs WHERE room_id=? AND name=?", (room_id, name)).fetchone(): continue
            con.execute("INSERT INTO race_defs(room_id,name,data_json,sort_order) VALUES(?,?,?,?)", (room_id, name, jdump(normalize_race_data(data)), order)); order += 1; counts["races"] += 1; inserted_names.append(name)
        # Bundled spell helpers are only applied to races imported in this explicit operation.
        if "인간" in inserted_names: ensure_default_race_spell_effects(con, room_id)
        migrate_race_spell_effect_metadata(con, room_id, set(inserted_names))
    if "monsters" in kinds:
        before = int(con.execute("SELECT COUNT(*) n FROM monster_defs WHERE room_id=?", (room_id,)).fetchone()["n"])
        existing_folders = {x["name"] for x in con.execute("SELECT name FROM monster_folders WHERE room_id=?", (room_id,))}
        next_order = int(con.execute("SELECT COALESCE(MAX(sort_order),0)+1 n FROM monster_folders WHERE room_id=?", (room_id,)).fetchone()["n"])
        for folder_name in DW_MONSTER_ENVIRONMENTS:
            if folder_name not in existing_folders:
                con.execute("INSERT INTO monster_folders(room_id,name,sort_order,created_at) VALUES(?,?,?,?)", (room_id, folder_name, next_order, now_iso())); next_order += 1
        ensure_builtin_monsters(con, room_id)
        after = int(con.execute("SELECT COUNT(*) n FROM monster_defs WHERE room_id=?", (room_id,)).fetchone()["n"]); counts["monsters"] = max(0, after-before)
    con.execute("UPDATE rooms SET default_data_revision=? WHERE id=?", (DEFAULT_DATA_REVISION, room_id))
    return counts


def generate_room_code(con: sqlite3.Connection) -> str:
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(100):
        code = "".join(secrets.choice(alphabet) for _ in range(6))
        if not con.execute("SELECT 1 FROM rooms WHERE code=?", (code,)).fetchone():
            return code
    raise RuntimeError("room code generation failed")


def room_by_code(con: sqlite3.Connection, code: str) -> sqlite3.Row:
    row = con.execute("SELECT * FROM rooms WHERE code=?", (code.upper(),)).fetchone()
    if not row:
        raise HTTPException(404, "캠페인을 찾을 수 없습니다.")
    return row


def room_player_count(con: sqlite3.Connection, room_id: int) -> int:
    """Count enabled player seats. GM/system members never consume campaign capacity."""
    return int(con.execute(
        "SELECT COUNT(*) n FROM members WHERE room_id=? AND role='player' AND disabled=0",
        (room_id,),
    ).fetchone()["n"])


def room_max_players(room: sqlite3.Row) -> int:
    try:
        return max(2, min(8, int(room["max_players"] or 4)))
    except (KeyError, IndexError, TypeError, ValueError):
        return 4


def bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "인증 토큰이 필요합니다.")
    return authorization.split(" ", 1)[1].strip()


def auth_context(con: sqlite3.Connection, room: sqlite3.Row, token: str) -> dict[str, Any]:
    h = hash_token(token)
    if secrets.compare_digest(h, room["gm_token_hash"]):
        return {"role": "gm", "name": room["gm_name"], "member_id": None}
    gm_session = con.execute("SELECT id FROM gm_sessions WHERE room_id=? AND token_hash=?", (room["id"], h)).fetchone()
    if gm_session:
        con.execute("UPDATE gm_sessions SET last_used_at=? WHERE id=?", (now_iso(), gm_session["id"]))
        return {"role": "gm", "name": room["gm_name"], "member_id": None}
    member = con.execute("SELECT * FROM members WHERE room_id=? AND token_hash=?", (room["id"], h)).fetchone()
    if not member:
        raise HTTPException(401, "인증 정보가 올바르지 않습니다.")
    if "disabled" in member.keys() and bool(member["disabled"]):
        raise HTTPException(403, "GM이 이 참가자의 접속을 비활성화했습니다.")
    actor = {"role": member["role"], "name": member["display_name"], "member_id": member["id"]}
    if actor["role"] == "player":
        require_active_campaign(room, player_only=True, actor=actor)
    return actor


def active_session(con: sqlite3.Connection, room_id: int) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM sessions WHERE room_id=? AND ended_at IS NULL ORDER BY session_no DESC LIMIT 1", (room_id,)).fetchone()


def touch_room(con: sqlite3.Connection, room_id: int) -> None:
    con.execute("UPDATE rooms SET updated_at=? WHERE id=?", (now_iso(), room_id))


def log_event(con: sqlite3.Connection, room_id: int, actor: dict[str, Any], action: str, target: str = "", detail: dict[str, Any] | None = None) -> None:
    sess = active_session(con, room_id)
    con.execute(
        "INSERT INTO logs(room_id,session_id,actor_role,actor_name,action,target,detail_json,created_at) VALUES(?,?,?,?,?,?,?,?)",
        (room_id, sess["id"] if sess else None, actor["role"], actor["name"], action, target, jdump(detail or {}), now_iso()),
    )
    touch_room(con, room_id)


def compact_change_detail(before: Any, after: Any, *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Store only changed top-level fields in change logs.

    Older releases wrote whole rule/class/spell objects even when one field changed,
    which made the GM change log noisy and unnecessarily large.  Keeping the
    changed subset also lets old and new clients render concise diffs consistently.
    """
    detail: dict[str, Any] = dict(extra or {})
    if isinstance(before, dict) and isinstance(after, dict):
        keys = [k for k in dict.fromkeys([*before.keys(), *after.keys()]) if before.get(k) != after.get(k)]
        detail["changed_keys"] = keys
        detail["before"] = {k: before.get(k) for k in keys}
        detail["after"] = {k: after.get(k) for k in keys}
    else:
        detail["before"] = before
        detail["after"] = after
    return detail


_ADVANCED_REQUIREMENT_RE = re.compile(r"^\s*(?:필요|대체)\s*:\s*([^\n.]+)")

def normalize_class_move(move: dict[str, Any] | None, allow_requirement: bool = False) -> dict[str, Any]:
    d = dict(move or {})
    d["name"] = str(d.get("name", ""))[:200]
    d["desc"] = str(d.get("desc", ""))[:20000]
    # Structured effects let a move grant/select spells, moves, race features, or
    # another class without hard-coding each move into the client.  The prose is
    # still authoritative for play; this metadata only records persistent sheet
    # choices and makes those grants visible.
    effects = []
    allowed_effects = {
        "spell_level_reduce", "spell_grant", "spell_zero",
        "class_access", "move_grant", "opposite_race_feature",
    }
    for raw in list(d.get("move_effects") or [])[:20]:
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("kind", "")).strip()
        if kind not in allowed_effects:
            continue
        e: dict[str, Any] = {
            "id": str(raw.get("id", ""))[:120],
            "kind": kind,
        }
        for key in ("source_class", "target_class", "spell_name", "choice_group", "restriction_note"):
            if raw.get(key) is not None:
                e[key] = str(raw.get(key, ""))[:500]
        if raw.get("count") is not None:
            e["count"] = max(1, min(20, int(raw.get("count") or 1)))
        if raw.get("amount") is not None:
            e["amount"] = max(1, min(10, int(raw.get("amount") or 1)))
        if raw.get("exclude_unclassified") is not None:
            e["exclude_unclassified"] = bool(raw.get("exclude_unclassified"))
        if raw.get("all_classes") is not None:
            e["all_classes"] = bool(raw.get("all_classes"))
        if raw.get("grant_moves") is not None:
            e["grant_moves"] = [str(x)[:200] for x in list(raw.get("grant_moves") or [])[:20] if str(x).strip()]
        if raw.get("race_pair") is not None:
            e["race_pair"] = [str(x)[:120] for x in list(raw.get("race_pair") or [])[:8] if str(x).strip()]
        effects.append(e)
    d["move_effects"] = effects
    if not allow_requirement:
        return d

    # Older Dungeon World seed text used "필요: X" / "대체: X" inside the
    # human-readable description.  Keep that text untouched, but migrate the
    # actual selection rule to explicit metadata.  An explicit false value wins
    # over text inference so a GM can deliberately disable a condition without
    # rewriting the original description.
    if "has_requirement" in d:
        has_requirement = bool(d.get("has_requirement"))
        requires_move = str(d.get("requires_move", "")).strip()[:200]
    else:
        match = _ADVANCED_REQUIREMENT_RE.match(d["desc"])
        requires_move = match.group(1).strip()[:200] if match else ""
        has_requirement = bool(requires_move)
    if not has_requirement or not requires_move:
        has_requirement = False
        requires_move = ""
    d["has_requirement"] = has_requirement
    d["requires_move"] = requires_move
    return d

def normalize_spellcasting_profile(data: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize a class spellcasting profile without encoding class names.

    Profiles describe mechanics (what is known, what can be prepared, limits, and
    learning cadence).  Presets in the browser merely fill these fields; runtime
    rules never branch on a class being named Wizard/Cleric or any translation.
    """
    raw = dict(data or {})
    known_mode = str(raw.get("known_mode", "manual"))
    if known_mode not in {"selected", "all", "manual"}:
        known_mode = "manual"
    prepare_mode = str(raw.get("prepare_mode", "manual"))
    if prepare_mode not in {"known", "all", "none", "manual"}:
        prepare_mode = "manual"
    limit_mode = str(raw.get("limit_mode", "none"))
    if limit_mode not in {"level_sum", "count", "none"}:
        limit_mode = "none"
    try: start_level = max(0, min(10, int(raw.get("starting_choice_level", 0) or 0)))
    except (TypeError, ValueError): start_level = 0
    try: start_count = max(0, min(20, int(raw.get("starting_choice_count", 0) or 0)))
    except (TypeError, ValueError): start_count = 0
    try: learn_per_level = max(0, min(20, int(raw.get("learn_per_level", 0) or 0)))
    except (TypeError, ValueError): learn_per_level = 0
    try: limit_offset = max(-20, min(20, int(raw.get("limit_offset", 0) or 0)))
    except (TypeError, ValueError): limit_offset = 0
    try: limit_count = max(0, min(100, int(raw.get("limit_count", 0) or 0)))
    except (TypeError, ValueError): limit_count = 0
    return {
        "enabled": bool(raw.get("enabled", False)),
        "known_mode": known_mode,
        "known_label": str(raw.get("known_label", "습득") or "습득")[:40],
        "prepare_mode": prepare_mode,
        "prepare_label": str(raw.get("prepare_label", "준비") or "준비")[:40],
        "limit_mode": limit_mode,
        "limit_offset": limit_offset,
        "limit_count": limit_count,
        "zero_level_label": str(raw.get("zero_level_label", "0레벨") or "0레벨")[:40],
        "zero_auto_known": bool(raw.get("zero_auto_known", True)),
        "zero_auto_prepared": bool(raw.get("zero_auto_prepared", True)),
        "zero_limit_exempt": bool(raw.get("zero_limit_exempt", True)),
        "starting_choice_level": start_level,
        "starting_choice_count": start_count,
        "learn_per_level": learn_per_level,
    }


def normalize_class_data(data: dict[str, Any] | None) -> dict[str, Any]:
    d = dict(data or {})
    damage = str(d.get("damage", "D6") or "D6").upper().strip()
    d["damage"] = damage if damage in {"D4", "D6", "D8", "D10", "D12"} else "D6"
    d["start"] = [normalize_class_move(x, False) for x in (d.get("start") or []) if isinstance(x, dict)]
    d["a25"] = [normalize_class_move(x, True) for x in (d.get("a25") or []) if isinstance(x, dict)]
    d["a610"] = [normalize_class_move(x, True) for x in (d.get("a610") or []) if isinstance(x, dict)]
    if "spellcasting" in d:
        d["spellcasting"] = normalize_spellcasting_profile(d.get("spellcasting"))
    return d


def ensure_spellcasting_profiles(con: sqlite3.Connection, room_id: int | None = None) -> int:
    """Backfill profile metadata for old campaigns without changing DB schema.

    Official legacy classes receive the profile stored in the bundled seed data. This
    is a one-time compatibility migration, not a gameplay name check. Unknown custom
    classes with existing spells get an unrestricted manual profile so their old
    behavior keeps working until the GM chooses more precise rules.
    """
    try:
        seed_classes = dict((json.loads(SEED_PATH.read_text(encoding="utf-8")) or {}).get("classes") or {})
    except Exception:
        seed_classes = {}
    params: tuple[Any, ...] = ()
    where = ""
    if room_id is not None:
        where = " WHERE room_id=?"
        params = (int(room_id),)
    changed = 0
    for row in con.execute(f"SELECT id,room_id,name,data_json FROM class_defs{where}", params):
        raw = dict(jload(row["data_json"], {}) or {})
        if isinstance(raw.get("spellcasting"), dict):
            normalized = normalize_class_data(raw)
            if normalized != raw:
                con.execute("UPDATE class_defs SET data_json=? WHERE id=?", (jdump(normalized), row["id"]))
                changed += 1
            continue
        seeded = seed_classes.get(str(row["name"]))
        seeded_profile = seeded.get("spellcasting") if isinstance(seeded, dict) else None
        if isinstance(seeded_profile, dict):
            raw["spellcasting"] = normalize_spellcasting_profile(seeded_profile)
        else:
            spell_rows = list(con.execute(
                "SELECT level FROM spell_defs WHERE room_id=? AND class_name=? ORDER BY id",
                (int(row["room_id"]), str(row["name"])),
            ))
            label = "0레벨"
            for spell_row in spell_rows:
                level = str(spell_row["level"] or "").strip()
                if level and not re.fullmatch(r"\d+", level):
                    label = level[:40]
                    break
            raw["spellcasting"] = normalize_spellcasting_profile({
                "enabled": bool(spell_rows),
                "known_mode": "manual",
                "known_label": "습득",
                "prepare_mode": "manual",
                "prepare_label": "준비",
                "limit_mode": "none",
                "zero_level_label": label,
                "zero_auto_known": True,
                "zero_auto_prepared": True,
                "zero_limit_exempt": True,
            })
        con.execute("UPDATE class_defs SET data_json=? WHERE id=?", (jdump(normalize_class_data(raw)), row["id"]))
        changed += 1
    return changed

def _without_runtime_meta(value: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(value or {})
    out.pop("_builtin", None); out.pop("_builtin_key", None)
    return out

def _seed_classes() -> dict[str, dict[str, Any]]:
    try:
        return dict((seed_payload().get("classes") or {}))
    except Exception:
        return {}

def _seed_core_moves() -> dict[str, dict[str, Any]]:
    try:
        return {str(x.get("name", "")): dict(x) for x in (seed_payload().get("core") or []) if isinstance(x, dict)}
    except Exception:
        return {}

def _seed_spells() -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    try:
        for cname, rows in (seed_payload().get("spells") or {}).items():
            for x in rows or []:
                if isinstance(x, dict): out[(str(cname), str(x.get("name", "")))] = dict(x)
    except Exception:
        pass
    return out

def _seed_race_text() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    try:
        for cname, cdata in _seed_classes().items():
            for race in cdata.get("races", []) or []:
                if not isinstance(race, dict): continue
                name=str(race.get("name", "")).strip()
                if not name: continue
                r=out.setdefault(name,{"description":"","per_class":{},"enabled_classes":[]})
                r["per_class"][str(cname)] = str(race.get("desc", ""))
                if str(cname) not in r["enabled_classes"]: r["enabled_classes"].append(str(cname))
    except Exception:
        pass
    return out

def _class_is_builtin(name: str, data: dict[str, Any]) -> bool:
    seed = _seed_classes().get(str(name))
    if not isinstance(seed, dict): return False
    a=normalize_class_data(_without_runtime_meta(data)); b=normalize_class_data(seed)
    # Race cards are derived from race_defs at runtime and are not part of provenance.
    a.pop("races", None); b.pop("races", None)
    return a == b

def class_map(con: sqlite3.Connection, room_id: int) -> dict[str, dict[str, Any]]:
    """Return classes and mark only untouched bundled definitions as built-in.

    The marker is computed from canonical bundled data instead of the display text.
    This lets the browser translate core content while preserving GM-authored text
    even when it happens to match a bundled Korean word.
    """
    out: dict[str, dict[str, Any]] = {}
    for row in con.execute("SELECT * FROM class_defs WHERE room_id=? ORDER BY sort_order,id", (room_id,)):
        data=normalize_class_data(jload(row["data_json"], {}) or {})
        data["_builtin"]=_class_is_builtin(str(row["name"]), data)
        out[row["name"]]=data
    races = race_map(con, room_id)
    for cname, cdata in out.items():
        cards = []
        for rname, rdata in races.items():
            if cname not in set(rdata.get("enabled_classes") or []):
                continue
            cards.append({"name": rname, "desc": str((rdata.get("per_class") or {}).get(cname, "")), "_builtin": bool(rdata.get("_builtin"))})
        cdata["races"] = cards
    return out


def normalize_race_data(data: dict[str, Any] | None) -> dict[str, Any]:
    d = dict(data or {})
    d.setdefault("name", "")
    d.setdefault("description", "")
    per = dict(d.get("per_class") or {})
    d["per_class"] = {str(k): str(v or "") for k, v in per.items()}
    enabled_classes = d.get("enabled_classes")
    if enabled_classes is None:
        enabled_classes = [k for k, v in d["per_class"].items() if str(v).strip()]
    d["enabled_classes"] = list(dict.fromkeys(str(x) for x in enabled_classes if str(x)))

    # spell_effects is the single canonical representation.  Older development
    # builds stored cross-class access separately in spell_access and allowed an
    # `enabled` flag on individual effects.  We still *read* those shapes so old
    # campaign DBs import safely, but current state/storage never emits either
    # compatibility field: a present effect is active, and removing it disables it.
    legacy_access: dict[str, dict[str, Any]] = {}
    for class_name, raw in dict(d.get("spell_access") or {}).items():
        item = dict(raw or {})
        source = str(item.get("source_class", "")).strip()
        if bool(item.get("enabled", False)) and source:
            legacy_access[str(class_name)] = {
                "source_class": source,
                "count": max(1, min(10, int(item.get("count", 1) or 1))),
            }

    effects: dict[str, list[dict[str, Any]]] = {}
    for class_name, raw_list in dict(d.get("spell_effects") or {}).items():
        clean_list: list[dict[str, Any]] = []
        for raw in list(raw_list or [])[:30]:
            if not isinstance(raw, dict) or raw.get("enabled", True) is False:
                continue
            kind = str(raw.get("kind", "")).strip()
            if kind not in {"cross_class_access", "level_reduce", "grant_unclassified"}:
                continue
            if kind == "cross_class_access":
                source = str(raw.get("source_class", "")).strip()
                if not source:
                    continue
                clean_list.append({
                    "kind": kind,
                    "source_class": source,
                    "count": max(1, min(10, int(raw.get("count", 1) or 1))),
                })
                continue
            try:
                spell_id = max(0, int(raw.get("spell_id", 0) or 0))
            except Exception:
                spell_id = 0
            item: dict[str, Any] = {"kind": kind, "spell_id": spell_id}
            if kind == "level_reduce":
                item["amount"] = max(1, min(99, int(raw.get("amount", 1) or 1)))
            clean_list.append(item)
        effects[str(class_name)] = clean_list

    # Import legacy spell_access exactly once into canonical normalized state.
    for class_name, rule in legacy_access.items():
        rows = effects.setdefault(class_name, [])
        if not any(x.get("kind") == "cross_class_access" for x in rows):
            rows.insert(0, {
                "kind": "cross_class_access",
                "source_class": rule["source_class"],
                "count": rule["count"],
            })

    d.pop("spell_access", None)
    d["spell_effects"] = effects
    return d


def _spell_id_by_name(con: sqlite3.Connection, room_id: int, class_name: str, spell_name: str) -> int:
    row = con.execute("SELECT id FROM spell_defs WHERE room_id=? AND class_name=? AND name=?", (room_id, class_name, spell_name)).fetchone()
    return int(row["id"]) if row else 0


def remove_race_spell_effect_refs(con: sqlite3.Connection, room_id: int, spell_id: int) -> int:
    """Remove race-effect metadata that points at a definition no longer valid in that context."""
    changed_rows = 0
    for rr in con.execute("SELECT id,data_json FROM race_defs WHERE room_id=?", (room_id,)):
        rd = normalize_race_data(jload(rr["data_json"], {}) or {})
        effects = dict(rd.get("spell_effects") or {})
        changed = False
        for cname, rows in list(effects.items()):
            kept = [x for x in rows if int(x.get("spell_id") or 0) != int(spell_id)]
            if len(kept) != len(rows):
                effects[cname] = kept
                changed = True
        if changed:
            rd["spell_effects"] = effects
            con.execute("UPDATE race_defs SET data_json=? WHERE id=?", (jdump(rd), rr["id"]))
            changed_rows += 1
    return changed_rows


def migrate_race_spell_effect_metadata(
    con: sqlite3.Connection, room_id: int | None = None, race_names: set[str] | None = None
) -> None:
    """Convert known text-only racial spell rules into explicit metadata once.

    The optional scope preserves campaign isolation: creating or explicitly
    importing defaults for one campaign must never annotate an unrelated campaign.
    Description text is never edited.
    """
    if room_id is None:
        rows = con.execute("SELECT id,room_id,name,data_json FROM race_defs")
    else:
        rows = con.execute("SELECT id,room_id,name,data_json FROM race_defs WHERE room_id=?", (room_id,))
    for row in rows:
        if race_names is not None and str(row["name"]) not in race_names:
            continue
        data = normalize_race_data(jload(row["data_json"], {}) or {})
        per = data.get("per_class") or {}
        effects = dict(data.get("spell_effects") or {})
        changed = False
        if row["name"] == "엘프" and "마법 탐지가 간편주문" in str(per.get("마법사", "")):
            sid = _spell_id_by_name(con, int(row["room_id"]), "마법사", "마법 탐지")
            cur = list(effects.get("마법사") or [])
            if sid and not any(x.get("kind") == "level_reduce" and int(x.get("spell_id") or 0) == sid for x in cur):
                cur.append({"kind": "level_reduce", "spell_id": sid, "amount": 1})
                effects["마법사"] = cur; changed = True
        if row["name"] == "드워프" and "목석의 말이 암송주문" in str(per.get("사제", "")):
            sid = ensure_dwarf_stone_speech_spell(con, int(row["room_id"]))
            cur = list(effects.get("사제") or [])
            if sid and not any(x.get("kind") == "grant_unclassified" and int(x.get("spell_id") or 0) == sid for x in cur):
                cur.append({"kind": "grant_unclassified", "spell_id": sid})
                effects["사제"] = cur; changed = True
        if changed:
            data["spell_effects"] = effects
            con.execute("UPDATE race_defs SET data_json=? WHERE id=?", (jdump(normalize_race_data(data)), row["id"]))


def race_map(con: sqlite3.Connection, room_id: int) -> dict[str, dict[str, Any]]:
    seed=_seed_race_text(); out={}
    for row in con.execute("SELECT * FROM race_defs WHERE room_id=? ORDER BY sort_order,id", (room_id,)):
        data=normalize_race_data(jload(row["data_json"], {})); ref=seed.get(str(row["name"]))
        builtin=False
        if ref:
            builtin=(str(data.get("description",""))==str(ref.get("description","")) and
                     dict(data.get("per_class") or {})==dict(ref.get("per_class") or {}) and
                     set(data.get("enabled_classes") or [])==set(ref.get("enabled_classes") or []))
        data["_builtin"]=builtin; out[row["name"]]=data
    return out
DWARF_STONE_SPEECH_NAME = "목석의 말 · 돌"
DWARF_STONE_SPEECH_OLD_NAME = "목석의 말(돌)"
DWARF_STONE_SPEECH_DESC = "돌을 만지며 이 주문을 걸면 그 안의 영들과 대화할 수 있습니다. 사제는 대상 물체에게 질문을 세 가지 할 수 있습니다. 돌은 이에 능력껏 대답할 것입니다."


def ensure_dwarf_stone_speech_spell(con: sqlite3.Connection, room_id: int) -> int:
    """Return the unclassified stone-only racial spell, creating the bundled definition if needed."""
    row = con.execute(
        "SELECT id FROM spell_defs WHERE room_id=? AND class_name='__undefined__' AND name=?",
        (room_id, DWARF_STONE_SPEECH_NAME),
    ).fetchone()
    if row:
        return int(row["id"])
    data = {"name": DWARF_STONE_SPEECH_NAME, "level": "암송", "desc": DWARF_STONE_SPEECH_DESC}
    cur = con.execute(
        "INSERT INTO spell_defs(room_id,class_name,name,level,data_json) VALUES(?,?,?,?,?)",
        (room_id, "__undefined__", DWARF_STONE_SPEECH_NAME, "암송", jdump(data)),
    )
    return int(cur.lastrowid)


def migrate_dwarf_cleric_stone_speech(con: sqlite3.Connection) -> None:
    """Fix an older interpretation of the Dwarf cleric racial spell.

    Only the exact bundled dwarf/cleric rule plus the exact old level-reduction metadata
    is converted. GM-created or already-customized race effects are left untouched.
    """
    for row in con.execute("SELECT id,room_id,data_json FROM race_defs WHERE name='드워프'"):
        data = normalize_race_data(jload(row["data_json"], {}) or {})
        if "돌에 대해서만 쓸 수 있는 목석의 말이 암송주문" not in str((data.get("per_class") or {}).get("사제", "")):
            continue
        old_spell = con.execute(
            "SELECT id FROM spell_defs WHERE room_id=? AND class_name='사제' AND name='목석의 말'",
            (row["room_id"],),
        ).fetchone()
        if not old_spell:
            continue
        old_sid = int(old_spell["id"])
        effects = dict(data.get("spell_effects") or {})
        cleric = list(effects.get("사제") or [])
        matched = [x for x in cleric if x.get("kind") == "level_reduce" and int(x.get("spell_id") or 0) == old_sid and int(x.get("amount") or 0) >= 5]
        if not matched:
            continue
        special_sid = ensure_dwarf_stone_speech_spell(con, int(row["room_id"]))
        cleric = [x for x in cleric if x not in matched]
        if not any(x.get("kind") == "grant_unclassified" and int(x.get("spell_id") or 0) == special_sid for x in cleric):
            cleric.append({"kind": "grant_unclassified", "spell_id": special_sid})
        effects["사제"] = cleric
        data["spell_effects"] = effects
        con.execute("UPDATE race_defs SET data_json=? WHERE id=?", (jdump(normalize_race_data(data)), row["id"]))



def migrate_stone_speech_display_name(con: sqlite3.Connection) -> None:
    """Rename only the bundled Dwarf cleric stone-only spell from its older label.

    Campaign data remains authoritative.  The migration touches a spell only when the
    old name, chant level and bundled description all match the shipped definition,
    so a GM-created spell that merely shares the old name is left alone.
    """
    for row in list(con.execute(
        "SELECT id,room_id,level,data_json FROM spell_defs "
        "WHERE class_name='__undefined__' AND name=?",
        (DWARF_STONE_SPEECH_OLD_NAME,),
    )):
        data = jload(row["data_json"], {}) or {}
        if str(row["level"]) != "암송" or str(data.get("desc", "")) != DWARF_STONE_SPEECH_DESC:
            continue
        old_id = int(row["id"]); room_id = int(row["room_id"])
        existing = con.execute(
            "SELECT id FROM spell_defs WHERE room_id=? AND class_name='__undefined__' AND name=?",
            (room_id, DWARF_STONE_SPEECH_NAME),
        ).fetchone()
        if existing and int(existing["id"]) != old_id:
            new_id = int(existing["id"])
            # Move racial effect references to the already-existing corrected definition.
            for rr in con.execute("SELECT id,data_json FROM race_defs WHERE room_id=?", (room_id,)):
                race = normalize_race_data(jload(rr["data_json"], {}) or {})
                changed = False
                effects = dict(race.get("spell_effects") or {})
                for cls, rows in list(effects.items()):
                    fixed = []
                    for eff in list(rows or []):
                        eff = dict(eff)
                        if int(eff.get("spell_id") or 0) == old_id:
                            eff["spell_id"] = new_id; changed = True
                        fixed.append(eff)
                    effects[cls] = fixed
                if changed:
                    race["spell_effects"] = effects
                    con.execute("UPDATE race_defs SET data_json=? WHERE id=?", (jdump(normalize_race_data(race)), rr["id"]))
            target_id = new_id
            con.execute("DELETE FROM spell_defs WHERE id=?", (old_id,))
        else:
            data["name"] = DWARF_STONE_SPEECH_NAME
            con.execute(
                "UPDATE spell_defs SET name=?,data_json=? WHERE id=?",
                (DWARF_STONE_SPEECH_NAME, jdump(data), old_id),
            )
            target_id = old_id

        # GM-granted copies keep a cached display name/description in character JSON.
        classes = class_map(con, room_id)
        for crow in con.execute("SELECT id,state_json FROM characters WHERE room_id=?", (room_id,)):
            state = normalize_character_state(jload(crow["state_json"], {}) or {}, classes)
            changed = False
            for extra in state.get("extra_spells", []):
                if int(extra.get("spell_id") or 0) in {old_id, target_id} and extra.get("name") == DWARF_STONE_SPEECH_OLD_NAME:
                    extra["spell_id"] = target_id
                    extra["name"] = DWARF_STONE_SPEECH_NAME
                    extra["level"] = "암송"
                    extra["desc"] = DWARF_STONE_SPEECH_DESC
                    changed = True
            if DWARF_STONE_SPEECH_OLD_NAME in (state.get("prepared_spells") or []):
                state["prepared_spells"] = [DWARF_STONE_SPEECH_NAME if x == DWARF_STONE_SPEECH_OLD_NAME else x for x in state.get("prepared_spells", [])]
                changed = True
            if changed:
                con.execute("UPDATE characters SET state_json=?,updated_at=? WHERE id=?", (jdump(state), now_iso(), crow["id"]))

def ensure_default_race_spell_effects(con: sqlite3.Connection, room_id: int) -> None:
    """Seed the official Human cross-class spell helpers into spell_effects."""
    row = con.execute("SELECT id,data_json FROM race_defs WHERE room_id=? AND name=?", (room_id, "인간")).fetchone()
    if not row:
        return
    data = normalize_race_data(jload(row["data_json"], {}) or {})
    effects = dict(data.get("spell_effects") or {})
    changed = False
    classes = {x["name"] for x in con.execute("SELECT name FROM class_defs WHERE room_id=?", (room_id,))}
    for target, source in (("마법사", "사제"), ("사제", "마법사")):
        if target not in classes or source not in classes:
            continue
        rows = list(effects.get(target) or [])
        if any(x.get("kind") == "cross_class_access" for x in rows):
            continue
        rows.insert(0, {"kind": "cross_class_access", "source_class": source, "count": 1})
        effects[target] = rows
        changed = True
    if changed:
        data["spell_effects"] = effects
        con.execute("UPDATE race_defs SET data_json=? WHERE id=?", (jdump(normalize_race_data(data)), row["id"]))



def spell_map(con: sqlite3.Connection, room_id: int) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}; seed=_seed_spells()
    for row in con.execute("SELECT * FROM spell_defs WHERE room_id=? ORDER BY class_name,id", (room_id,)):
        item = jload(row["data_json"], {}) or {}
        ref=seed.get((str(row["class_name"]), str(row["name"])))
        item["_builtin"] = bool(ref and str(item.get("desc",""))==str(ref.get("desc","")) and str(row["level"] or "")==str(ref.get("level","")))
        # Bundled compatibility spell created by migration is also core content.
        if str(row["class_name"])=="__undefined__" and str(row["name"])==DWARF_STONE_SPEECH_NAME and str(item.get("desc",""))==DWARF_STONE_SPEECH_DESC:
            item["_builtin"] = True
        item["id"] = row["id"]
        item["class_name"] = row["class_name"]
        out.setdefault(row["class_name"], []).append(item)
    return out


def core_move_list(con: sqlite3.Connection, room_id: int) -> list[dict[str, Any]]:
    out = []; seed=_seed_core_moves()
    for row in con.execute("SELECT * FROM core_moves WHERE room_id=? ORDER BY id", (room_id,)):
        item = jload(row["data_json"], {}) or {}; ref=seed.get(str(row["name"]))
        item["_builtin"] = bool(ref and _without_runtime_meta(item)==_without_runtime_meta(ref))
        item["id"] = row["id"]
        out.append(item)
    return out


INVENTORY_ITEM_TYPES = {"일반 장비", "무기", "탄약", "갑옷", "던전 장비", "소모품", "독", "마법 물품", "중요한 물건"}

def infer_inventory_item_type(raw: dict[str, Any]) -> str:
    explicit = str(raw.get("item_type", "")).strip()
    if explicit in INVENTORY_ITEM_TYPES:
        return explicit
    name = str(raw.get("name", "")).strip()
    tags = str(raw.get("tags", "")).strip()
    hay = f"{name} {tags}"
    if any(x in hay for x in ("갑옷", "방패", "장갑 ", "장갑+", "장갑 +")):
        return "갑옷"
    if any(x in hay for x in ("탄약", "화살 다발", "화살 한 다발", "화살 묶음", "쇠뇌살", "볼트 묶음")):
        return "탄약"
    if any(x in hay for x in ("독", "타기트 기름", "박혈초", "황금근", "뱀눈물")):
        return "독"
    if "마법" in hay:
        return "마법 물품"
    weapon_words = ("활", "쇠뇌", "단검", "단도", "비수", "소검", "장검", "검", "도끼", "전투망치", "철퇴", "창", "지팡이", "레이피어", "할버드", "곤봉", "몽둥이", "고유병기")
    if "무기" in tags or any(x in name for x in weapon_words):
        return "무기"
    dungeon_gear = ("모험 장비", "붕대", "연고와 약초", "책 자루", "던전용 식량", "고급 도시락", "드워프 건빵", "엘프 빵", "하플링 담뱃잎", "해독제", "치료약")
    if any(x in name for x in dungeon_gear):
        return "던전 장비"
    try:
        uses_max = int(raw.get("uses_max", 0) or 0)
    except (TypeError, ValueError):
        uses_max = 0
    if uses_max > 0 or "소모품" in tags or "회분" in tags:
        return "소모품"
    return "일반 장비"

def normalize_inventory(value: Any) -> list[dict[str, Any]]:
    """Normalize the text-first inventory without turning it into a rules engine.

    Items stay text-first, while quantity/weight/use counters are structured so
    the client can calculate current load reliably.  Price is intentionally not
    stored as a required field: coin remains a character resource and item value
    can be written in tags/notes when the table cares about it.
    """
    out: list[dict[str, Any]] = []
    for raw in list(value or [])[:200]:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name", ""))[:240]
        qty = max(1, min(9999, int(raw.get("quantity", 1) or 1)))
        try:
            weight = float(raw.get("weight", 0) or 0)
        except (TypeError, ValueError):
            weight = 0.0
        weight = max(0.0, min(9999.0, weight))
        uses_max = max(0, min(9999, int(raw.get("uses_max", 0) or 0)))
        uses_current = max(0, min(9999, int(raw.get("uses_current", uses_max) or 0)))
        if uses_max > 0:
            uses_current = min(uses_current, uses_max)
        tags = str(raw.get("tags", ""))[:1200]
        item_type = infer_inventory_item_type({**raw, "name": name, "tags": tags, "uses_max": uses_max})
        note = str(raw.get("note", ""))[:6000]
        # Structured details stay intentionally narrow.  Numeric values that are
        # unambiguous in the original rules can be counted, while descriptive
        # effects such as precise/piercing/slow remain free-text tags.
        weapon_range = str(raw.get("weapon_range", ""))[:120]

        legacy_damage = str(raw.get("damage", ""))[:160]
        try:
            damage_bonus = int(raw.get("damage_bonus", 0) or 0)
        except (TypeError, ValueError):
            damage_bonus = 0
        if "damage_bonus" not in raw and legacy_damage.strip():
            m = re.search(r"([+-])\s*(\d+)", legacy_damage)
            if m:
                damage_bonus = int(m.group(2)) * (1 if m.group(1) == "+" else -1)
        damage_bonus = max(-99, min(99, damage_bonus))

        def _bounded_nonneg(key: str, default: int = 0) -> int:
            try:
                return max(0, min(9999, int(raw.get(key, default) or 0)))
            except (TypeError, ValueError):
                return max(0, default)

        armor_value = _bounded_nonneg("armor_value")
        armor_bonus = _bounded_nonneg("armor_bonus")
        if "armor_value" not in raw:
            m = re.search(r"(?:^|[,，·/\n]\s*)장갑\s*(?!\+)\s*(\d+)", tags)
            if m:
                armor_value = min(99, int(m.group(1)))
        if "armor_bonus" not in raw:
            m = re.search(r"장갑\s*\+\s*(\d+)", tags)
            if m:
                armor_bonus = min(99, int(m.group(1)))

        ammo_max = _bounded_nonneg("ammo_max")
        ammo_current = _bounded_nonneg("ammo_current", ammo_max)
        if "ammo_max" not in raw:
            m = re.search(r"(?:탄약|발수)\s*(\d+)", tags)
            if m:
                ammo_max = min(9999, int(m.group(1)))
                ammo_current = ammo_max
        if ammo_max > 0:
            ammo_current = min(ammo_current, ammo_max)
        # Since schema 19 ammo is its own inventory resource.  Ignore stale
        # weapon-attached ammo values submitted by old clients after migration.
        if item_type != "탄약":
            ammo_current = 0
            ammo_max = 0

        # Empty editor drafts stay in the browser until the player types something.
        # Drop completely empty persisted/legacy noise during normalization.
        if not name.strip() and not tags.strip() and not note.strip() and not weapon_range.strip() and damage_bonus == 0 and armor_value == 0 and armor_bonus == 0 and ammo_max == 0 and weight == 0 and uses_max == 0:
            continue
        out.append({
            "name": name,
            "item_type": item_type,
            "quantity": qty,
            "weight": weight,
            "uses_current": uses_current,
            "uses_max": uses_max,
            "ammo_current": ammo_current,
            "ammo_max": ammo_max,
            "tags": tags,
            "weapon_range": weapon_range,
            "damage_bonus": damage_bonus,
            # Legacy client compatibility.
            "damage": (f"{damage_bonus:+d} 피해" if damage_bonus else ""),
            "armor_value": armor_value,
            "armor_bonus": armor_bonus,
            "note": note,
        })
    return out


def stat_modifier(score: int | float, rules: dict[str, Any] | None = None) -> int:
    """Return the Dungeon World ability modifier for a raw ability score.

    Campaigns may customize the modifier ranges, so server-side derived values
    (notably Load) must use the same rule table as the browser instead of the
    raw score itself.
    """
    clean_rules = normalize_rules(rules or DEFAULT_RULES)
    try:
        value = int(score or 0)
    except (TypeError, ValueError):
        value = 0
    ranges = list(clean_rules.get("stat_mod_ranges") or DEFAULT_RULES["stat_mod_ranges"])
    for row in ranges:
        if value <= int(row.get("max", 99)):
            return int(row.get("mod", 0) or 0)
    return int((ranges[-1] if ranges else {"mod": 0}).get("mod", 0) or 0)


def inventory_weight(state: dict[str, Any], rules: dict[str, Any] | None = None) -> float:
    item_weight = sum(
        max(1, int(x.get("quantity", 1) or 1)) * max(0.0, float(x.get("weight", 0) or 0))
        for x in normalize_inventory(state.get("inventory"))
    )
    clean_rules = normalize_rules(rules or DEFAULT_RULES)
    coin_weight = 0.0
    if clean_rules.get("coin_weight_enabled") is True:
        per = max(1, int(clean_rules.get("coin_weight_per", 100) or 100))
        coins = max(0, int(state.get("currency", 0) or 0))
        coin_weight = coins / per
    return round(item_weight + coin_weight, 2)


def default_character_state(display_name: str, classes: dict[str, dict[str, Any]], class_name: str | None = None, race_name: str | None = None) -> dict[str, Any]:
    # A new participant deliberately begins without a class or race.  Passing a
    # valid class/race is kept for migrations/tests, but first-join no longer
    # supplies them.
    assigned = bool(class_name and class_name in classes)
    class_name = class_name if assigned else ""
    c = classes.get(class_name, {})
    races = c.get("races", [])
    aligns = c.get("alignments", [])
    chosen_race = race_name if assigned and race_name and any(r.get("name") == race_name for r in races) else (races[0]["name"] if assigned and races else "")
    return {
        "profile": {"name": display_name, "gender": "", "age": "", "body": "", "personality": ""},
        "class_name": class_name,
        "race_name": chosen_race,
        "onboarding_complete": assigned,
        "alignment_name": aligns[0]["name"] if assigned and aligns else "",
        "stats": {"str": 0, "dex": 0, "con": 0, "int": 0, "wis": 0, "cha": 0},
        "stats_initialized": False,
        "hp_current": int(c.get("hp", 0)) if assigned else 0,
        "armor_base": 0,
        "armor": 0,
        "damage_die": str(c.get("damage", "D6")) if assigned else "D6",
        "damage_bonus": 0,
        "bonus_stat_points": 0,
        "stat_growth_spent": 0,
        "level": 1,
        "xp": 0,
        "currency": 0,
        "reserve": 0,
        "inventory": [],
        "bonds": [str(x) for x in list(c.get("bonds", []))] if assigned else [],
        "advanced_moves": [],
        "extra_moves": [],
        "move_choices": {},
        "spellbook": [],
        "prepared_spells": [],
        "extra_spells": [],
        "starting_spells_complete": False,
        "spell_tracks": {},
        "memo": "",
        "extension_state": {},
    }


def normalize_character_state(state: dict[str, Any], classes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Return only fields used by the current character sheet.

    Older clients could leave arbitrary JSON keys in state_json. A
    whitelist prevents obsolete test values from accumulating forever.
    """
    raw = dict(state or {})
    class_name = str(raw.get("class_name", ""))
    c = classes.get(class_name, {})
    prof = dict(raw.get("profile") or {})
    profile = {
        "name": str(prof.get("name", ""))[:120],
        "gender": str(prof.get("gender", ""))[:120],
        "age": str(prof.get("age", ""))[:120],
        "body": str(prof.get("body", ""))[:240],
        "personality": str(prof.get("personality", ""))[:2000],
    }
    stats_raw = dict(raw.get("stats") or {})
    stats = {k: int(stats_raw.get(k, 0) or 0) for k in ("str", "dex", "con", "int", "wis", "cha")}
    bonds = []
    for item in list(raw.get("bonds") or [])[:30]:
        if isinstance(item, str):
            bonds.append(item[:3000])
        else:
            x = dict(item or {})
            text = str(x.get("desc", x.get("text", x.get("name", ""))))
            if text:
                bonds.append(text[:3000])
    spellbook = list(dict.fromkeys(str(x) for x in (raw.get("spellbook") or []) if str(x)))[:200]
    prepared = list(dict.fromkeys(str(x) for x in (raw.get("prepared_spells") or []) if str(x)))[:200]
    adv = list(dict.fromkeys(str(x) for x in (raw.get("advanced_moves") or []) if str(x)))[:200]
    extra_moves = [dict(x) for x in (raw.get("extra_moves") or []) if isinstance(x, dict)][:100]
    move_choices: dict[str, dict[str, Any]] = {}
    for key, value in list(dict(raw.get("move_choices") or {}).items())[:100]:
        if not isinstance(value, dict):
            continue
        item: dict[str, Any] = {}
        if value.get("spell_id") is not None:
            try: item["spell_id"] = max(0, int(value.get("spell_id") or 0))
            except (TypeError, ValueError): pass
        for sk in ("source_class", "move_name", "race_name"):
            if value.get(sk) is not None:
                item[sk] = str(value.get(sk, ""))[:200]
        if value.get("acquired_at_level") is not None:
            try: item["acquired_at_level"] = max(1, int(value.get("acquired_at_level") or 1))
            except (TypeError, ValueError): pass
        move_choices[str(key)[:200]] = item
    extra_spells = [dict(x) for x in (raw.get("extra_spells") or []) if isinstance(x, dict)][:30]
    spell_tracks: dict[str, dict[str, Any]] = {}
    for key, value in list(dict(raw.get("spell_tracks") or {}).items())[:60]:
        if not isinstance(value, dict):
            continue
        known = list(dict.fromkeys(str(x) for x in (value.get("known") or []) if str(x)))[:200]
        track_prepared = list(dict.fromkeys(str(x) for x in (value.get("prepared") or []) if str(x)))[:200]
        spell_tracks[str(key)[:200]] = {
            "known": known,
            "prepared": track_prepared,
            "starting_complete": bool(value.get("starting_complete", False)),
        }
    raw_damage_die = str(raw.get("damage_die") or c.get("damage") or "D6").upper().strip()
    damage_die = raw_damage_die if raw_damage_die in {"D4", "D6", "D8", "D10", "D12"} else str(c.get("damage", "D6") or "D6").upper().strip()
    if damage_die not in {"D4", "D6", "D8", "D10", "D12"}:
        damage_die = "D6"
    initialized = raw.get("stats_initialized")
    if initialized is None:
        initialized = any(v != 0 for v in stats.values())  # legacy characters are not re-locked
    onboarding = raw.get("onboarding_complete")
    if onboarding is None:
        # Existing characters from older versions already chose an identity.
        onboarding = bool(class_name and class_name in classes)
    return {
        "profile": profile,
        "class_name": class_name,
        "race_name": str(raw.get("race_name", ""))[:120],
        "onboarding_complete": bool(onboarding),
        "alignment_name": str(raw.get("alignment_name", ""))[:120],
        "stats": stats,
        "stats_initialized": bool(initialized),
        "hp_current": int(raw.get("hp_current", int(c.get("hp", 1))) or 0),
        "armor_base": int(raw.get("armor_base", 0) or 0),
        "armor": int(raw.get("armor", 0) or 0),
        "damage_die": damage_die,
        "damage_bonus": int(raw.get("damage_bonus", 0) or 0),
        "bonus_stat_points": max(0, int(raw.get("bonus_stat_points", 0) or 0)),
        "stat_growth_spent": None if raw.get("stat_growth_spent") is None else max(0, int(raw.get("stat_growth_spent", 0) or 0)),
        "level": max(1, int(raw.get("level", 1) or 1)),
        "xp": max(0, int(raw.get("xp", 0) or 0)),
        "currency": max(0, int(raw.get("currency", 0) or 0)),
        "reserve": max(0, int(raw.get("reserve", 0) or 0)),
        "inventory": normalize_inventory(raw.get("inventory")),
        "bonds": bonds,
        "advanced_moves": adv,
        "extra_moves": extra_moves,
        "move_choices": move_choices,
        "spellbook": spellbook,
        "prepared_spells": prepared,
        "extra_spells": extra_spells,
        "starting_spells_complete": bool(raw.get("starting_spells_complete", False)),
        "spell_tracks": spell_tracks,
        "memo": str(raw.get("memo", ""))[:50000],
        "extension_state": compact_extension_state(raw.get("extension_state")),
    }

def xp_required(level: int, rules: dict[str, Any]) -> int:
    try:
        base = int(rules.get("xp_base", 7))
    except (TypeError, ValueError):
        base = 7
    return max(1, int(level) + max(0, base))


def advanced_move_point_cap(state: dict[str, Any], rules: dict[str, Any]) -> int:
    """Cumulative advanced-move points earned by level.

    Level 1 starts at 0. Each level above 1 adds one point. Unspent points are
    intentionally cumulative and never expire; the campaign's configured maximum
    level only limits how far the character can advance.
    """
    try:
        level = max(1, int(state.get("level", 1) or 1))
    except (TypeError, ValueError):
        level = 1
    try:
        level_max = max(1, int(rules.get("level_max", 10) or 10))
    except (TypeError, ValueError):
        level_max = 10
    return max(0, min(level, level_max) - 1)


def extension_move_point_usage(state: dict[str, Any]) -> int:
    """Points spent on accepted expansion-class move selections in character state."""
    total = 0
    for raw in dict(state.get("extension_state") or {}).values():
        st = dict(raw or {})
        if bool(st.get("legend_owned", False)):
            total += 1
        total += len({str(x) for x in (st.get("class_moves_owned") or []) if str(x)})
    return total


def advanced_move_point_usage(state: dict[str, Any]) -> int:
    """Shared point spend: class advanced moves + expansion legendary/class moves."""
    base = len({str(x) for x in (state.get("advanced_moves") or []) if str(x)})
    return base + extension_move_point_usage(state)


def validate_advanced_move_point_budget(before: dict[str, Any], after: dict[str, Any], rules: dict[str, Any]) -> None:
    """Enforce the shared point pool while allowing legacy overspend to be reduced.

    Older builds let expansion moves be toggled for free. If such a character is
    already over budget, they may remove selections until legal, but cannot increase
    or keep an over-budget spend through a point-affecting edit.
    """
    cap = advanced_move_point_cap(after, rules)
    used = advanced_move_point_usage(after)
    if used <= cap:
        return
    before_used = advanced_move_point_usage(before)
    if before_used > cap and used < before_used:
        return
    raise HTTPException(400, f"고급행동 포인트가 부족합니다. 현재 {used}/{cap}점을 사용 중입니다.")


SUPPORTED_DAMAGE_DICE = {"D4", "D6", "D8", "D10", "D12"}


def _validate_damage_die(value: Any) -> str:
    die = str(value or "D6").upper().strip()
    if die not in SUPPORTED_DAMAGE_DICE:
        raise HTTPException(400, "피해 주사위는 D4, D6, D8, D10, D12 중 하나여야 합니다.")
    return die


def stat_growth_point_cap(state: dict[str, Any]) -> int:
    return max(0, int(state.get("level", 1) or 1) - 1) + max(0, int(state.get("bonus_stat_points", 0) or 0))


def validate_stat_growth_budget(before: dict[str, Any], after: dict[str, Any]) -> None:
    cap = stat_growth_point_cap(after)
    used = max(0, int(after.get("stat_growth_spent", 0) or 0))
    if used <= cap:
        return
    before_used = max(0, int(before.get("stat_growth_spent", 0) or 0))
    if before_used > cap and used < before_used:
        return
    raise HTTPException(400, f"능력치 성장 포인트가 부족합니다. 현재 {used}/{cap}점을 사용 중입니다.")


def validate_stat_bounds(state: dict[str, Any], rules: dict[str, Any], *, allow_unassigned_zero: bool = False) -> None:
    lo = int(rules.get("stat_min", 3) or 3)
    hi = int(rules.get("stat_max", 18) or 18)
    for key in ("str", "dex", "con", "int", "wis", "cha"):
        value = int((state.get("stats") or {}).get(key, 0) or 0)
        if allow_unassigned_zero and value == 0:
            continue
        if value < lo or value > hi:
            raise HTTPException(400, f"능력치는 {lo}~{hi} 범위에서만 설정할 수 있습니다.")


def _validate_initial_stat_assignment(before: dict[str, Any], after: dict[str, Any], rules: dict[str, Any]) -> None:
    """During initial setup, assigned values must come from stat_start and obey campaign bounds."""
    if bool(before.get("stats_initialized")):
        after["stats_initialized"] = True
        validate_stat_bounds(after, rules)
        return
    start = [int(x) for x in (rules.get("stat_start") or [16,15,13,12,9,8])][:6]
    vals = [int((after.get("stats") or {}).get(k, 0) or 0) for k in ("str","dex","con","int","wis","cha")]
    remaining = list(start)
    for val in vals:
        if val == 0:
            continue
        if val not in remaining:
            raise HTTPException(400, "초기 능력치는 GM이 설정한 시작 값에서 배분해주세요. 배분이 끝난 뒤에는 자유롭게 수정할 수 있습니다.")
        remaining.remove(val)
    validate_stat_bounds(after, rules, allow_unassigned_zero=True)
    after["stats_initialized"] = not remaining and all(v != 0 for v in vals)


def _max_hp_for(state: dict[str, Any], classes: dict[str, dict[str, Any]]) -> int:
    c = classes.get(state.get("class_name"), {})
    return max(1, int(c.get("hp", 1) or 1) + int((state.get("stats") or {}).get("con", 0) or 0))
def damage_text(state: dict[str, Any], cdata: dict[str, Any]) -> str:
    die = str(state.get("damage_die") or cdata.get("damage") or "D6").upper()
    bonus = int(state.get("damage_bonus", 0) or 0)
    if bonus == 0:
        return die
    return f"{die} {'+' if bonus > 0 else '-'} {abs(bonus)}"


def public_grants(con: sqlite3.Connection, char_id: int, viewer_character_id: int | None, viewer_is_gm: bool) -> list[dict[str, Any]]:
    grants = []
    for g in con.execute(
        """SELECT g.*, e.name, e.public_intro, e.data_json, e.builtin_key, e.user_modified
           FROM expansion_grants g JOIN expansion_defs e ON e.id=g.expansion_id
           WHERE g.character_id=? AND g.status='accepted' ORDER BY g.id""",
        (char_id,),
    ):
        if viewer_is_gm or viewer_character_id == char_id or g["visible_to_party"]:
            grants.append({
                "grant_id": g["id"], "expansion_id": g["expansion_id"], "name": g["name"],
                "public_intro": g["public_intro"], "visible_to_party": bool(g["visible_to_party"]),
                "data": {**normalize_expansion_data(jload(g["data_json"], {})), "builtin": bool(g["builtin_key"]) and not bool(g["user_modified"])},
            })
    grants.sort(key=lambda x: (int((x.get("data") or {}).get("sort_order", 9999)), x.get("name", "")))
    return grants


def character_summary(
    con: sqlite3.Connection,
    char_row: sqlite3.Row,
    classes: dict[str, dict[str, Any]],
    viewer_character_id: int | None = None,
    viewer_is_gm: bool = False,
    expansions_enabled: bool = True,
) -> dict[str, Any]:
    state = normalize_character_state(jload(char_row["state_json"], {}), classes)
    c = classes.get(state.get("class_name"), {})
    onboarding_complete = bool(state.get("onboarding_complete"))
    max_hp = _max_hp_for(state, classes) if onboarding_complete else 0
    member = con.execute("SELECT display_name FROM members WHERE id=?", (char_row["member_id"],)).fetchone()
    room = con.execute("SELECT rules_json FROM rooms WHERE id=?", (char_row["room_id"],)).fetchone()
    rules = normalize_rules(jload(room["rules_json"], {}) or {}) if room else DEFAULT_RULES
    return {
        "character_id": char_row["id"], "member_id": char_row["member_id"],
        "display_name": member["display_name"] if member else state.get("profile", {}).get("name", "플레이어"),
        "character_name": state.get("profile", {}).get("name", ""),
        "onboarding_complete": onboarding_complete,
        "class_name": state.get("class_name", "") if onboarding_complete else "무직",
        "race_name": state.get("race_name", "") if onboarding_complete else "없음",
        "status_text": "" if onboarding_complete else "자신의 운명을 결정하는 중",
        "level": int(state.get("level", 1) or 1), "xp": int(state.get("xp", 0) or 0),
        "xp_required": xp_required(int(state.get("level", 1) or 1), rules),
        "hp_current": int(state.get("hp_current", 0) or 0) if onboarding_complete else 0, "hp_max": max_hp,
        "armor": int(state.get("armor", 0) or 0) if onboarding_complete else 0, "armor_base": int(state.get("armor_base", 0) or 0) if onboarding_complete else 0,
        "damage": damage_text(state, c) if onboarding_complete else "—", "currency": int(state.get("currency", 0) or 0),
        "load_current": inventory_weight(state, rules) if onboarding_complete else 0,
        "load_max": max(0, int(c.get("load", 0) or 0) + stat_modifier((state.get("stats") or {}).get("str", 0), rules)) if onboarding_complete else 0,
        "reserve": int(state.get("reserve", 0) or 0), "reserve_max": int(rules.get("reserve_max", 0) or 0),
        "extensions": public_grants(con, char_row["id"], viewer_character_id, viewer_is_gm) if expansions_enabled else [],
    }




def validate_player_state(
    new_state: dict[str, Any],
    classes: dict[str, dict[str, Any]],
    rules: dict[str, Any],
    changed_keys: set[str] | None = None,
) -> None:
    """Validate structure/identity, not tabletop rulings.

    The server deliberately avoids hard-enforcing level-up choices after initial
    character setup.  The UI still presents Dungeon World guidance and warnings,
    but the table and GM remain authoritative.
    """
    changed = changed_keys or set(new_state.keys())
    class_name = new_state.get("class_name")
    if class_name not in classes:
        raise HTTPException(400, "존재하지 않는 직업입니다.")
    c = classes[class_name]
    if changed & {"class_name", "race_name"}:
        race_names = {r.get("name") for r in c.get("races", []) if r.get("name")}
        if new_state.get("race_name") not in race_names:
            raise HTTPException(400, "현재 직업에서 선택할 수 없는 종족입니다.")
    if changed & {"class_name", "alignment_name"}:
        align_names = {a.get("name") for a in c.get("alignments", [])}
        if align_names and new_state.get("alignment_name") not in align_names:
            raise HTTPException(400, "현재 직업에서 선택할 수 없는 가치관입니다.")
    if "level" in changed:
        level = int(new_state.get("level", 1) or 1)
        level_max = max(1, int(rules.get("level_max", 10) or 10))
        if level < 1 or level > level_max:
            raise HTTPException(400, f"레벨은 1~{level_max} 범위에서만 설정할 수 있습니다.")
        new_state["level"] = level
    if "xp" in changed:
        new_state["xp"] = max(0, int(new_state.get("xp", 0) or 0))
    if "reserve" in changed:
        reserve = max(0, int(new_state.get("reserve", 0) or 0))
        reserve_max = max(0, int(rules.get("reserve_max", 0) or 0))
        new_state["reserve"] = min(reserve, reserve_max) if reserve_max > 0 else reserve
    if "currency" in changed:
        new_state["currency"] = max(0, int(new_state.get("currency", 0) or 0))
    if "inventory" in changed:
        new_state["inventory"] = normalize_inventory(new_state.get("inventory"))
    if "stats" in changed:
        stats = new_state.setdefault("stats", {})
        for key in ("str", "dex", "con", "int", "wis", "cha"):
            stats[key] = int(stats.get(key, 0) or 0)
    if "armor_base" in changed:
        new_state["armor_base"] = int(new_state.get("armor_base", 0) or 0)
    if "armor" in changed:
        new_state["armor"] = int(new_state.get("armor", 0) or 0)
    if changed & {"damage_die", "class_name"}:
        new_state["damage_die"] = _validate_damage_die(new_state.get("damage_die") or c.get("damage") or "D6")
    if "damage_bonus" in changed:
        new_state["damage_bonus"] = int(new_state.get("damage_bonus", 0) or 0)
    if "advanced_moves" in changed:
        new_state["advanced_moves"] = list(dict.fromkeys(str(x) for x in (new_state.get("advanced_moves") or []) if str(x)))[:200]
    if changed & {"advanced_moves", "level", "class_name"}:
        owned = set(new_state.get("advanced_moves") or [])
        allowed_min: dict[str, int] = {}
        for move in c.get("a25") or []:
            name = str(move.get("name", "")).strip()
            if name:
                allowed_min[name] = 2
        for move in c.get("a610") or []:
            name = str(move.get("name", "")).strip()
            if name:
                allowed_min[name] = 6
        if bool(c.get("multiclass_25")):
            allowed_min["다중직업(초급)"] = 2
        if bool(c.get("multiclass_610")):
            allowed_min["다중직업(중급)"] = 6
        unknown = sorted(x for x in owned if x not in allowed_min)
        if unknown:
            raise HTTPException(400, f"현재 직업에서 선택할 수 없는 고급 행동입니다: {unknown[0]}")
        level = max(1, int(new_state.get("level", 1) or 1))
        locked = sorted(x for x in owned if level < allowed_min.get(x, 999))
        if locked:
            raise HTTPException(400, f"{locked[0]} 행동은 아직 현재 레벨에서 해금되지 않았습니다.")
        for move in list(c.get("a25") or []) + list(c.get("a610") or []):
            name = str(move.get("name", "")).strip()
            requirement = str(move.get("requires_move", "")).strip() if move.get("has_requirement") else ""
            if name and requirement and name in owned and requirement not in owned:
                raise HTTPException(400, f"{name} 행동을 선택하려면 먼저 {requirement} 행동을 배워야 합니다.")
    if "extra_moves" in changed:
        # Verify identity against current source-class data. We do not judge whether
        # taking the move was a good tabletop choice, but effect-bearing moves must
        # not be forgeable by arbitrary source/name strings.
        clean_extra = []
        effective_multiclass_level = max(1, int(new_state.get("level", 1) or 1) - 1)
        for item in list(new_state.get("extra_moves") or [])[:100]:
            if not isinstance(item, dict):
                continue
            source = str(item.get("source_class", "")).strip()
            name = str(item.get("name", "")).strip()
            if not source or not name or source not in classes or source == class_name:
                raise HTTPException(400, "선택할 수 없는 타직업 행동입니다.")
            if name not in _class_move_option_names(classes[source], effective_multiclass_level):
                raise HTTPException(400, "현재 레벨에서 선택할 수 없는 타직업 행동입니다.")
            clean_extra.append({
                "source_class": source,
                "name": name,
                "desc": str(item.get("desc", ""))[:12000],
                "source_type": str(item.get("source_type", "multiclass")),
                "source_name": str(item.get("source_name", ""))[:200],
                "bundle": bool(item.get("bundle")),
                "acquired_at_level": max(1, int(item.get("acquired_at_level", new_state.get("level", 1)) or 1)),
                "min_level": max(1, int(item.get("min_level", 1) or 1)),
                "multiclass_tier": str(item.get("multiclass_tier", ""))[:120],
            })
        new_state["extra_moves"] = clean_extra
    if changed & {"move_choices", "advanced_moves", "extra_moves", "class_name"}:
        raw_choices = dict(new_state.get("move_choices") or {})
        allowed_keys = {str(row.get("key", "")) for row in _active_move_effect_rows(new_state, classes) if str(row.get("key", ""))}
        new_state["move_choices"] = {k: v for k, v in raw_choices.items() if k in allowed_keys}




def validate_extra_spell_choices(
    con: sqlite3.Connection,
    room_id: int,
    state: dict[str, Any],
    before: dict[str, Any],
    *,
    strict: bool = True,
) -> None:
    """Canonicalize player-selectable extra spells and protect GM special grants.

    Cross-class racial features may choose spells only from an actual class list. The
    special ``__undefined__`` pool is deliberately excluded: those spells can be
    granted only by explicit race metadata (automatic) or the GM special-spell API.
    Cached display text in character JSON is rebuilt from the spell definition so a
    client cannot change the mechanics by changing language or submitted text.
    """
    races = race_map(con, room_id)
    race = races.get(str(state.get("race_name", "")), {})
    class_name = str(state.get("class_name", ""))
    allowed: dict[str, int] = {}
    for effect in (race.get("spell_effects") or {}).get(class_name, []) or []:
        if not isinstance(effect, dict) or effect.get("kind") != "cross_class_access":
            continue
        source = str(effect.get("source_class", "")).strip()
        if not source or source == "__undefined__":
            continue
        allowed[source] = allowed.get(source, 0) + max(1, min(10, int(effect.get("count", 1) or 1)))

    protected_gm = [dict(x) for x in (before.get("extra_spells") or []) if isinstance(x, dict) and x.get("kind") == "gm"]
    requested = [dict(x) for x in (state.get("extra_spells") or []) if isinstance(x, dict) and x.get("kind") != "gm"]
    clean: list[dict[str, Any]] = []
    used: dict[str, int] = {}
    seen_ids: set[int] = set()

    def invalid(message: str) -> None:
        if strict:
            raise HTTPException(400, message)

    for raw in requested[:30]:
        sid = int(raw.get("spell_id", 0) or 0)
        source = str(raw.get("source", "")).strip()
        if sid <= 0 or not source or source == "__undefined__" or source not in allowed:
            invalid("미분류 주문이나 허용되지 않은 주문은 일반 주문 습득으로 추가할 수 없습니다.")
            if not strict:
                continue
        row = con.execute(
            "SELECT id,class_name,name,level,data_json FROM spell_defs WHERE id=? AND room_id=?",
            (sid, room_id),
        ).fetchone()
        if not row or str(row["class_name"]) != source or str(row["class_name"]) == "__undefined__":
            invalid("선택한 주문이 허용된 타직업 주문 목록에 없습니다.")
            if not strict:
                continue
        if sid in seen_ids:
            invalid("같은 추가 주문을 두 번 선택할 수 없습니다.")
            if not strict:
                continue
        if used.get(source, 0) >= allowed.get(source, 0):
            invalid("이 종족 특성으로 선택할 수 있는 추가 주문 수를 넘었습니다.")
            if not strict:
                continue
        data = jload(row["data_json"], {}) or {}
        clean.append({
            "kind": "race",
            "spell_id": int(row["id"]),
            "name": str(data.get("name") or row["name"]),
            "source": source,
            "level": data.get("level", row["level"]),
            "desc": str(data.get("desc", "")),
            "source_name": str(state.get("race_name", "")),
            "note": "",
        })
        seen_ids.add(sid)
        used[source] = used.get(source, 0) + 1

    # A normal character patch can neither forge nor delete GM-granted special spells.
    state["extra_spells"] = (protected_gm + clean)[:30]


def _move_effect_key(move: dict[str, Any], effect: dict[str, Any], index: int) -> str:
    return str(effect.get("id") or f"{move.get('name','')}:{effect.get('kind','')}:{index}")[:200]


def _extra_move_definitions(state: dict[str, Any], classes: dict[str, dict[str, Any]]) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    """Resolve multiclass-acquired moves back to their source-class definitions.

    Effects are never copied into character JSON. This keeps the source class as the
    single source of truth and means a move such as God Amidst the Wastes carries its
    class-access metadata even when another class learned that move through multiclass.
    """
    out: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for raw in state.get("extra_moves") or []:
        if not isinstance(raw, dict):
            continue
        source = str(raw.get("source_class", "")).strip()
        name = str(raw.get("name", "")).strip()
        c = classes.get(source)
        if not source or not name or not isinstance(c, dict):
            continue
        if bool(raw.get("bundle")):
            bundle = next((b for b in (c.get("multiclass_bundles") or []) if isinstance(b, dict) and str(b.get("name", "")) == name), None)
            for member in (bundle or {}).get("moves") or []:
                move = next((m for m in (c.get("start") or []) if isinstance(m, dict) and str(m.get("name", "")) == str(member)), None)
                if move:
                    out.append((source, move, raw))
            continue
        move = next((m for m in list(c.get("start") or []) + list(c.get("a25") or []) + list(c.get("a610") or []) if isinstance(m, dict) and str(m.get("name", "")) == name), None)
        if move:
            out.append((source, move, raw))
    return out


def _active_move_effect_rows(state: dict[str, Any], classes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Return structured effects for all moves the character currently owns.

    Runtime effects are resolved from data, never from class-name branches. Starting
    moves and selected advanced moves come from the current class; multiclass-acquired
    moves are resolved from their source class and carry the same effect metadata.
    """
    current_class = str(state.get("class_name", ""))
    c = classes.get(current_class, {})
    owned = {str(x) for x in (state.get("advanced_moves") or []) if str(x)}
    rows: list[dict[str, Any]] = []
    seen_moves: set[str] = set()

    def add_move(source: str, move: dict[str, Any], origin: dict[str, Any] | None = None) -> None:
        identity = f"{source}::{str(move.get('name', ''))}"
        if identity in seen_moves:
            return
        seen_moves.add(identity)
        for index, effect in enumerate(move.get("move_effects") or []):
            if not isinstance(effect, dict):
                continue
            rows.append({
                "move": move,
                "effect": effect,
                "key": _move_effect_key(move, effect, index),
                "source_class": source,
                "origin": origin,
            })

    for move in c.get("start") or []:
        if isinstance(move, dict):
            add_move(current_class, move)
    for move in list(c.get("a25") or []) + list(c.get("a610") or []):
        if isinstance(move, dict) and str(move.get("name", "")) in owned:
            add_move(current_class, move)
    for source, move, origin in _extra_move_definitions(state, classes):
        add_move(source, move, origin)
    return rows


def _class_move_option_names(class_data: dict[str, Any], level: int) -> set[str]:
    """Mirror the selectable cross-class move list used by the browser."""
    effective = max(1, int(level or 1))
    names: set[str] = set()
    bundled: set[str] = set()
    for bundle in class_data.get("multiclass_bundles") or []:
        if not isinstance(bundle, dict):
            continue
        members = [str(x) for x in (bundle.get("moves") or []) if str(x)]
        existing = {str(m.get("name", "")) for m in (class_data.get("start") or []) if isinstance(m, dict)}
        if members and all(x in existing for x in members):
            bname = str(bundle.get("name") or "").strip()
            if bname:
                names.add(bname)
            bundled.update(members)
    for move in class_data.get("start") or []:
        if isinstance(move, dict) and str(move.get("name", "")) and str(move.get("name", "")) not in bundled:
            names.add(str(move.get("name")))
    if effective >= 2:
        names.update(str(m.get("name")) for m in (class_data.get("a25") or []) if isinstance(m, dict) and str(m.get("name", "")))
    if effective >= 6:
        names.update(str(m.get("name")) for m in (class_data.get("a610") or []) if isinstance(m, dict) and str(m.get("name", "")))
    return names


def _numeric_spell_level(value: Any) -> int | None:
    raw = str(value or "").strip()
    if not re.fullmatch(r"\d+", raw):
        return None
    n = int(raw)
    return n if n > 0 else None


def validate_move_choices(
    con: sqlite3.Connection,
    room_id: int,
    state: dict[str, Any],
    classes: dict[str, dict[str, Any]],
    *,
    strict: bool = False,
) -> None:
    """Validate/sanitize persistent choices created by class-move effects.

    The browser is intentionally descriptive rather than a tabletop rules judge, but
    these choices alter persistent character data. The server therefore verifies
    their *identity* and source. In particular, ordinary move-based spell choices can
    never acquire the special ``__undefined__`` spell pool; that pool is reserved for
    explicit GM/special grants.
    """
    active = _active_move_effect_rows(state, classes)
    by_key = {row["key"]: row for row in active}
    raw = dict(state.get("move_choices") or {})
    clean: dict[str, dict[str, Any]] = {}
    used_groups: dict[str, int] = {}
    current_class = str(state.get("class_name", ""))
    level = max(1, int(state.get("level", 1) or 1))

    def invalid(message: str) -> None:
        if strict:
            raise HTTPException(400, message)

    for key, value in raw.items():
        row = by_key.get(str(key))
        if not row or not isinstance(value, dict):
            continue
        effect = row["effect"]
        kind = str(effect.get("kind", ""))
        item = dict(value)
        out: dict[str, Any] = {}
        acquired = max(1, int(item.get("acquired_at_level", level) or level))
        out["acquired_at_level"] = min(acquired, level)

        if kind in {"spell_level_reduce", "spell_grant"}:
            sid = int(item.get("spell_id", 0) or 0)
            if sid <= 0:
                # An unmade optional choice is valid; keep only acquisition metadata.
                clean[str(key)] = out
                continue
            spell = con.execute(
                "SELECT id,class_name,name,level FROM spell_defs WHERE id=? AND room_id=?",
                (sid, room_id),
            ).fetchone()
            if not spell or str(spell["class_name"]) == "__undefined__":
                invalid("미분류 주문은 일반 주문 선택으로 습득할 수 없습니다.")
                if not strict:
                    continue
            if spell is None:
                continue
            source_class = str(spell["class_name"])
            if kind == "spell_level_reduce":
                if source_class != current_class or _numeric_spell_level(spell["level"]) is None:
                    invalid("현재 직업의 숫자 레벨 주문만 이 행동으로 선택할 수 있습니다.")
                    if not strict:
                        continue
            else:
                fixed_source = str(effect.get("source_class", "")).strip()
                if fixed_source and fixed_source != "*" and source_class != fixed_source:
                    invalid("이 행동에서 선택할 수 없는 직업의 주문입니다.")
                    if not strict:
                        continue
                if not bool(effect.get("all_classes", False)) and not fixed_source and source_class != current_class:
                    invalid("이 행동에서 선택할 수 없는 직업의 주문입니다.")
                    if not strict:
                        continue
            group = str(effect.get("choice_group", "")).strip()
            if group:
                previous = used_groups.get(group)
                if previous and previous != sid:
                    # Different choices are expected in one group; duplicate spell ids are not.
                    pass
                elif previous == sid:
                    invalid("서로 다른 주문을 선택해야 합니다.")
                    if not strict:
                        continue
                used_groups[group] = sid
            out["spell_id"] = sid
            clean[str(key)] = out
            continue

        if kind == "move_grant":
            fixed = str(effect.get("source_class", "")).strip()
            source = fixed if fixed and fixed != "*" else str(item.get("source_class", "")).strip()
            move_name = str(item.get("move_name", "")).strip()
            if not source or source not in classes or source == current_class:
                invalid("선택할 수 없는 타직업입니다.")
                if not strict:
                    continue
            if fixed and fixed != "*" and source != fixed:
                invalid("이 행동의 타직업 출처를 변경할 수 없습니다.")
                if not strict:
                    continue
            if not move_name:
                clean[str(key)] = out
                continue
            if move_name not in _class_move_option_names(classes[source], level):
                invalid("선택할 수 없는 타직업 행동입니다.")
                if not strict:
                    continue
            out["source_class"] = source
            out["move_name"] = move_name[:200]
            clean[str(key)] = out
            continue

        if kind == "class_access":
            source = str(effect.get("source_class", "")).strip()
            if not source or source not in classes:
                invalid("존재하지 않는 타직업 획득 효과입니다.")
                if not strict:
                    continue
            # No player-selectable source is stored: the move metadata is authoritative.
            clean[str(key)] = out
            continue

        if kind == "opposite_race_feature":
            # The opposite race is derived from current race + metadata, not chosen by client.
            clean[str(key)] = out
            continue

        if kind == "spell_zero":
            # Fixed target spell is metadata-only; no client selection is accepted.
            clean[str(key)] = out
            continue

        # Unknown kinds are dropped by normalization, but keep this future-proof.
        invalid("지원하지 않는 행동 효과 선택입니다.")

    # Enforce duplicate exclusion for each spell choice group after all rows are known.
    for group in {str(r["effect"].get("choice_group", "")).strip() for r in active if str(r["effect"].get("choice_group", "")).strip()}:
        members = []
        for r in active:
            if str(r["effect"].get("choice_group", "")).strip() != group:
                continue
            sid = int((clean.get(r["key"]) or {}).get("spell_id", 0) or 0)
            if sid:
                members.append((r["key"], sid))
        seen: set[int] = set()
        for choice_key, sid in members:
            if sid not in seen:
                seen.add(sid)
                continue
            invalid("연결된 행동에서는 서로 다른 주문을 선택해야 합니다.")
            if not strict:
                clean.pop(choice_key, None)

    state["move_choices"] = clean


def _spell_effective_level(value: Any) -> int:
    """Numeric spell levels count toward limits; named/zero-level categories count as 0."""
    raw = str(value or "").strip()
    if not re.fullmatch(r"\d+", raw):
        return 0
    return max(0, int(raw))


def _spell_known_cap(profile: dict[str, Any], level: int) -> int | None:
    if str(profile.get("known_mode")) != "selected":
        return None
    start = max(0, int(profile.get("starting_choice_count", 0) or 0))
    start_level = max(0, int(profile.get("starting_choice_level", 0) or 0))
    per_level = max(0, int(profile.get("learn_per_level", 0) or 0))
    level = max(1, int(level or 1))
    gained = max(0, level - start_level) * per_level if start_level > 0 else max(0, level - 1) * per_level
    return max(0, start + gained)


def _spell_prepare_limit(profile: dict[str, Any], level: int) -> int | None:
    mode = str(profile.get("limit_mode", "none"))
    if mode == "level_sum":
        return max(0, max(1, int(level or 1)) + int(profile.get("limit_offset", 0) or 0))
    if mode == "count":
        return max(0, int(profile.get("limit_count", 0) or 0))
    return None


def _spell_prepare_usage(profile: dict[str, Any], prepared: list[str], levels: dict[str, int]) -> int:
    names = set(str(x) for x in prepared if str(x))
    exempt_zero = bool(profile.get("zero_limit_exempt", True))
    mode = str(profile.get("limit_mode", "none"))
    if mode == "count":
        return sum(1 for name in names if name in levels and not (exempt_zero and levels[name] == 0))
    if mode == "level_sum":
        return sum(max(0, int(levels[name])) for name in names if name in levels and not (exempt_zero and levels[name] == 0))
    return 0


def _spell_rows_for_class(con: sqlite3.Connection, room_id: int, class_name: str) -> list[dict[str, Any]]:
    return [
        {"id": int(row["id"]), "name": str(row["name"]), "level": _spell_effective_level(row["level"]), "raw_level": str(row["level"] or "")}
        for row in con.execute(
            "SELECT id,name,level FROM spell_defs WHERE room_id=? AND class_name=? ORDER BY id",
            (room_id, class_name),
        )
    ]


def _primary_spell_levels(
    con: sqlite3.Connection,
    room_id: int,
    state: dict[str, Any],
    classes: dict[str, dict[str, Any]],
) -> tuple[dict[str, int], set[str], set[str]]:
    """Return visible primary spell levels plus base and auto-known names.

    This mirrors the browser's data-driven spell page. It intentionally keys by
    canonical spell name because legacy character state stores spellbook/prepared
    selections by name. Class-access spell systems are namespaced separately in
    ``spell_tracks`` and therefore do not collide with this primary track.
    """
    class_name = str(state.get("class_name", ""))
    base_rows = _spell_rows_for_class(con, room_id, class_name)
    levels = {row["name"]: int(row["level"]) for row in base_rows}
    base_names = set(levels)
    auto_known: set[str] = set()
    by_id = {row["id"]: row for row in base_rows}

    # Race effects can lower a current-class spell or grant an explicit special
    # spell. The race data is metadata-driven; no race/class names are encoded here.
    race_name = str(state.get("race_name", ""))
    race = race_map(con, room_id).get(race_name, {}) if race_name else {}
    for effect in (race.get("spell_effects") or {}).get(class_name, []) or []:
        if not isinstance(effect, dict):
            continue
        kind = str(effect.get("kind", ""))
        sid = int(effect.get("spell_id", 0) or 0)
        if kind == "level_reduce" and sid in by_id:
            row = by_id[sid]
            levels[row["name"]] = max(0, levels[row["name"]] - max(1, int(effect.get("amount", 1) or 1)))
        elif kind == "grant_unclassified" and sid > 0:
            row = con.execute("SELECT name,level FROM spell_defs WHERE room_id=? AND id=? AND class_name='__undefined__'", (room_id, sid)).fetchone()
            if row:
                name = str(row["name"])
                levels[name] = _spell_effective_level(row["level"])
                auto_known.add(name)

    # Move metadata alters spell identity/level or auto-grants a selected spell.
    for row in _active_move_effect_rows(state, classes):
        effect = row.get("effect") or {}
        kind = str(effect.get("kind", ""))
        choice = dict((state.get("move_choices") or {}).get(row["key"]) or {})
        if kind == "spell_level_reduce":
            sid = int(choice.get("spell_id", 0) or 0)
            base = by_id.get(sid)
            if base:
                levels[base["name"]] = max(0, levels[base["name"]] - max(1, int(effect.get("amount", 1) or 1)))
        elif kind == "spell_zero":
            name = str(effect.get("spell_name", "")).strip()
            if name in levels:
                levels[name] = 0
        elif kind == "spell_grant":
            sid = int(choice.get("spell_id", 0) or 0)
            if sid > 0:
                spell = con.execute("SELECT name,level,class_name FROM spell_defs WHERE room_id=? AND id=?", (room_id, sid)).fetchone()
                if spell and str(spell["class_name"]) != "__undefined__":
                    name = str(spell["name"])
                    levels[name] = _spell_effective_level(spell["level"])
                    auto_known.add(name)

    # Explicit GM/race grants are persistent state and are always considered known.
    for item in state.get("extra_spells") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        levels[name] = _spell_effective_level(item.get("level"))
        auto_known.add(name)
    return levels, base_names, auto_known


def validate_spellcasting_state(
    con: sqlite3.Connection,
    room_id: int,
    state: dict[str, Any],
    classes: dict[str, dict[str, Any]],
    *,
    enforce_limits: bool = True,
    strict: bool = False,
) -> None:
    """Validate primary and cross-class spell tracks from class metadata.

    Runtime behavior is entirely profile/effect driven. There are deliberately no
    Wizard/Cleric name checks here: a custom class can use any profile, and a
    ``class_access`` move (for example a Ranger gaining Cleric spellcasting) inherits
    the *source class profile* automatically.
    """
    level = max(1, int(state.get("level", 1) or 1))
    class_name = str(state.get("class_name", ""))
    profile = normalize_spellcasting_profile((classes.get(class_name) or {}).get("spellcasting"))

    def invalid(message: str) -> None:
        if strict:
            raise HTTPException(400, message)

    levels, base_names, auto_known = _primary_spell_levels(con, room_id, state, classes)
    available_base = {name for name in base_names if levels.get(name, 0) == 0 or levels.get(name, 0) <= level}

    # Primary known list only stores selected/manual base-class spells. Automatically
    # known grants and all-known profiles do not need duplicate state entries.
    raw_known = [str(x) for x in state.get("spellbook") or [] if str(x)]
    clean_known: list[str] = []
    for name in raw_known:
        if name not in base_names or name not in available_base:
            invalid("현재 직업/레벨에서 습득할 수 없는 주문입니다.")
            continue
        if name not in clean_known:
            clean_known.append(name)
    if profile.get("known_mode") == "all":
        clean_known = []
    elif enforce_limits and profile.get("known_mode") == "selected":
        cap = _spell_known_cap(profile, level)
        counted = [name for name in clean_known if levels.get(name, 0) > 0]
        if cap is not None and len(counted) > cap:
            invalid(f"현재 레벨에서 습득 가능한 주문 수는 {cap}개입니다.")
            if not strict:
                keep = set(counted[:cap]) | {name for name in clean_known if levels.get(name, 0) == 0}
                clean_known = [name for name in clean_known if name in keep]
    state["spellbook"] = clean_known

    known_set = set(clean_known) | auto_known
    if profile.get("known_mode") == "all":
        known_set |= available_base
    if bool(profile.get("zero_auto_known", True)):
        known_set |= {name for name in available_base if levels.get(name, 0) == 0}

    # Disabled base spellcasting can still display/prepare explicitly granted spells.
    allowed_prepared = set(levels)
    if not bool(profile.get("enabled", False)):
        allowed_prepared = set(auto_known)
    raw_prepared = [str(x) for x in state.get("prepared_spells") or [] if str(x)]
    clean_prepared: list[str] = []
    for name in raw_prepared:
        if name not in allowed_prepared or (name in base_names and name not in available_base):
            invalid("현재 사용할 수 없는 주문은 준비할 수 없습니다.")
            continue
        if profile.get("prepare_mode") == "known" and name not in known_set:
            invalid("습득하지 않은 주문은 준비할 수 없습니다.")
            continue
        if name not in clean_prepared:
            clean_prepared.append(name)
    if profile.get("prepare_mode") == "none":
        clean_prepared = []
    if enforce_limits:
        limit = _spell_prepare_limit(profile, level)
        usage = _spell_prepare_usage(profile, clean_prepared, levels)
        if limit is not None and usage > limit:
            invalid(f"준비 주문 한도({limit})를 초과했습니다.")
            if not strict:
                # Preserve deterministic order while trimming until within the profile.
                while clean_prepared and _spell_prepare_usage(profile, clean_prepared, levels) > limit:
                    clean_prepared.pop()
    state["prepared_spells"] = clean_prepared

    # Each active class_access move gets its own namespaced track. Source class
    # profile + effective source level define the mechanics, so future custom spell
    # classes work without adding a new branch here.
    active_access: dict[str, dict[str, Any]] = {}
    for row in _active_move_effect_rows(state, classes):
        effect = row.get("effect") or {}
        if str(effect.get("kind", "")) != "class_access":
            continue
        source = str(effect.get("source_class", "")).strip()
        if not source or source not in classes:
            continue
        choice = dict((state.get("move_choices") or {}).get(row["key"]) or {})
        acquired = max(1, min(level, int(choice.get("acquired_at_level", level) or level)))
        effective = max(1, level - acquired + 1)
        active_access[row["key"]] = {"source": source, "level": effective}

    raw_tracks = dict(state.get("spell_tracks") or {})
    clean_tracks: dict[str, dict[str, Any]] = {}
    for key, access in active_access.items():
        source = access["source"]
        effective = int(access["level"])
        source_profile = normalize_spellcasting_profile((classes.get(source) or {}).get("spellcasting"))
        source_rows = _spell_rows_for_class(con, room_id, source)
        source_levels = {row["name"]: int(row["level"]) for row in source_rows}
        available = {name for name, spell_level in source_levels.items() if spell_level == 0 or spell_level <= effective}
        raw_track = dict(raw_tracks.get(key) or {})
        track_known = []
        for name in [str(x) for x in raw_track.get("known") or [] if str(x)]:
            if name not in available:
                invalid("타직업 주문 체계에서 현재 레벨에 사용할 수 없는 주문입니다.")
                continue
            if name not in track_known:
                track_known.append(name)
        if source_profile.get("known_mode") == "all":
            track_known = []
        elif enforce_limits and source_profile.get("known_mode") == "selected":
            cap = _spell_known_cap(source_profile, effective)
            counted = [name for name in track_known if source_levels.get(name, 0) > 0]
            if cap is not None and len(counted) > cap:
                invalid(f"{source} 주문 습득 한도({cap})를 초과했습니다.")
                if not strict:
                    keep = set(counted[:cap]) | {name for name in track_known if source_levels.get(name, 0) == 0}
                    track_known = [name for name in track_known if name in keep]

        source_known = set(track_known)
        if source_profile.get("known_mode") == "all":
            source_known |= available
        if bool(source_profile.get("zero_auto_known", True)):
            source_known |= {name for name in available if source_levels.get(name, 0) == 0}

        track_prepared: list[str] = []
        for name in [str(x) for x in raw_track.get("prepared") or [] if str(x)]:
            if name not in available:
                invalid("타직업 주문 체계에서 현재 사용할 수 없는 주문은 준비할 수 없습니다.")
                continue
            if source_profile.get("prepare_mode") == "known" and name not in source_known:
                invalid("타직업 주문 체계에서 습득하지 않은 주문은 준비할 수 없습니다.")
                continue
            if name not in track_prepared:
                track_prepared.append(name)
        if source_profile.get("prepare_mode") == "none":
            track_prepared = []
        if enforce_limits:
            limit = _spell_prepare_limit(source_profile, effective)
            usage = _spell_prepare_usage(source_profile, track_prepared, source_levels)
            if limit is not None and usage > limit:
                invalid(f"{source} 준비 주문 한도({limit})를 초과했습니다.")
                if not strict:
                    while track_prepared and _spell_prepare_usage(source_profile, track_prepared, source_levels) > limit:
                        track_prepared.pop()
        clean_tracks[key] = {
            "known": track_known,
            "prepared": track_prepared,
            "starting_complete": bool(raw_track.get("starting_complete", False)),
        }
    state["spell_tracks"] = clean_tracks


def normalize_extension_resource_values(con: sqlite3.Connection, char_id: int, state: dict[str, Any], strict: bool = True) -> None:
    state["extension_state"] = compact_extension_state(state.get("extension_state"))
    allowed: dict[str, dict[str, Any]] = {}
    for row in con.execute(
        """SELECT g.id grant_id,e.data_json FROM expansion_grants g
           JOIN expansion_defs e ON e.id=g.expansion_id WHERE g.character_id=? AND g.status='accepted'""", (char_id,)
    ):
        allowed[str(row["grant_id"])] = normalize_expansion_data(jload(row["data_json"], {}))
    for gid, val in list((state.get("extension_state") or {}).items()):
        if gid not in allowed:
            if strict:
                raise HTTPException(403, "부여되지 않은 확장직업 상태는 수정할 수 없습니다.")
            state["extension_state"].pop(gid, None)
            continue
        resource = dict((allowed[gid] or {}).get("resource") or {})
        amount = max(0, int((val or {}).get("resource_current", 0) or 0))
        maximum = max(0, int(resource.get("max", 0) or 0))
        val["resource_current"] = min(amount, maximum) if maximum > 0 else amount


def validate_player_extension_state(con: sqlite3.Connection, char_id: int, state: dict[str, Any]) -> None:
    normalize_extension_resource_values(con, char_id, state, strict=True)
    allowed: dict[str, dict[str, Any]] = {}
    for row in con.execute(
        """SELECT g.id grant_id,e.data_json FROM expansion_grants g
           JOIN expansion_defs e ON e.id=g.expansion_id WHERE g.character_id=? AND g.status='accepted'""", (char_id,)
    ):
        allowed[str(row["grant_id"])] = normalize_expansion_data(jload(row["data_json"], {}))
    ext_state = state.get("extension_state") or {}
    for gid, val in ext_state.items():
        if gid not in allowed:
            raise HTTPException(403, "부여되지 않은 확장직업 상태는 수정할 수 없습니다.")
        d = allowed[gid]
        owned = list(dict.fromkeys((val or {}).get("class_moves_owned") or []))
        valid = {m.get("name") for m in d.get("class_moves", [])}
        if any(x not in valid for x in owned):
            raise HTTPException(400, "존재하지 않는 확장직업 행동입니다.")
        if owned and not bool((val or {}).get("legend_owned")):
            raise HTTPException(400, "전설행동을 먼저 획득해야 직업 행동을 획득할 수 있습니다.")
        val["class_moves_owned"] = owned


# ==================================================
# Dungeon World Data Pack (.dwpack)
# ==================================================

DWPACK_DATA_FILES = {
    "rules": "data/rules.json",
    "core_moves": "data/core_moves.json",
    "classes": "data/classes.json",
    "spells": "data/spells.json",
    "races": "data/races.json",
    "expansions": "data/expansions.json",
    "monster_folders": "data/monster_folders.json",
    "monsters": "data/monsters.json",
    "npcs": "data/npcs.json",
}
DWPACK_PREVIEW_TTL = 15 * 60
DWPACK_UID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
dwpack_previews: dict[str, dict[str, Any]] = {}


def _cleanup_dwpack_previews() -> None:
    now = time.time()
    for key in list(dwpack_previews):
        if float(dwpack_previews[key].get("expires_at", 0)) <= now:
            dwpack_previews.pop(key, None)


def _dwpack_uid(kind: str, *parts: Any) -> str:
    raw = "\0".join([kind, *(str(x) for x in parts)]).encode("utf-8")
    return f"{kind}-{hashlib.sha256(raw).hexdigest()[:20]}"


def _dwpack_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n").encode("utf-8")


def _dwpack_zip_bytes(files: dict[str, Any]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 10, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, _dwpack_json_bytes(files[name]))
    return out.getvalue()




def _dwpack_export_room(con: sqlite3.Connection, room: sqlite3.Row, include_npcs: bool = False, include_rules: bool = True) -> tuple[bytes, dict[str, Any]]:
    room_id = int(room["id"])
    warnings: list[str] = []

    core_rows = list(con.execute("SELECT id,name,data_json FROM core_moves WHERE room_id=? ORDER BY id", (room_id,)))
    class_rows = list(con.execute("SELECT id,name,data_json,sort_order FROM class_defs WHERE room_id=? ORDER BY sort_order,id", (room_id,)))
    spell_rows = list(con.execute("SELECT id,class_name,name,level,data_json FROM spell_defs WHERE room_id=? ORDER BY class_name,id", (room_id,)))
    race_rows = list(con.execute("SELECT id,name,data_json,sort_order FROM race_defs WHERE room_id=? ORDER BY sort_order,id", (room_id,)))
    expansion_rows = list(con.execute("SELECT id,name,gm_condition,public_intro,data_json,sort_order FROM expansion_defs WHERE room_id=? ORDER BY sort_order,id", (room_id,)))
    folder_rows = list(con.execute("SELECT id,name,sort_order FROM monster_folders WHERE room_id=? ORDER BY sort_order,id", (room_id,)))
    monster_rows = list(con.execute("SELECT id,folder_id,name,data_json,sort_order FROM monster_defs WHERE room_id=? ORDER BY sort_order,id", (room_id,)))
    npc_rows = list(con.execute("SELECT id,name,data_json,favorite,sort_order FROM npc_defs WHERE room_id=? ORDER BY favorite DESC,sort_order,id", (room_id,))) if include_npcs else []

    class_uid_by_name = {r["name"]: _dwpack_uid("class", r["name"]) for r in class_rows}
    spell_uid_by_id: dict[int, str] = {}
    for r in spell_rows:
        spell_uid_by_id[int(r["id"])] = _dwpack_uid("spell", r["class_name"], r["name"], r["id"])
    folder_uid_by_id = {int(r["id"]): _dwpack_uid("folder", r["name"], r["id"]) for r in folder_rows}

    core_items = []
    for r in core_rows:
        data = dict(jload(r["data_json"], {}) or {})
        core_items.append({"uid": _dwpack_uid("core", r["name"]), "name": r["name"], "data": data})

    class_items = []
    for r in class_rows:
        data = normalize_class_data(jload(r["data_json"], {}) or {})
        data.pop("races", None)
        class_items.append({"uid": class_uid_by_name[r["name"]], "name": r["name"], "sort_order": int(r["sort_order"]), "data": data})

    spell_items = []
    for r in spell_rows:
        data = dict(jload(r["data_json"], {}) or {})
        data["name"] = r["name"]
        data["level"] = str(r["level"])
        spell_items.append({
            "uid": spell_uid_by_id[int(r["id"])],
            "class_name": r["class_name"],
            "name": r["name"],
            "level": str(r["level"]),
            "desc": str(data.get("desc", "")),
        })

    race_items = []
    for r in race_rows:
        data = normalize_race_data(jload(r["data_json"], {}) or {})
        data.pop("spell_access", None)
        exported_effects: dict[str, list[dict[str, Any]]] = {}
        for class_name, rows in dict(data.get("spell_effects") or {}).items():
            out_rows = []
            for effect in rows:
                effect = dict(effect or {})
                kind = effect.get("kind")
                if kind == "cross_class_access":
                    out_rows.append({
                        "kind": "cross_class_access",
                        "source_class": str(effect.get("source_class", "")),
                        "count": max(1, min(10, int(effect.get("count", 1) or 1))),
                    })
                elif kind in {"level_reduce", "grant_unclassified"}:
                    sid = int(effect.get("spell_id") or 0)
                    suid = spell_uid_by_id.get(sid)
                    if not suid:
                        warnings.append(f"종족 {r['name']}의 주문 효과가 존재하지 않는 주문 ID {sid}를 참조하여 해당 효과를 제외했습니다.")
                        continue
                    item = {"kind": kind, "spell_uid": suid}
                    if kind == "level_reduce":
                        item["amount"] = max(1, min(99, int(effect.get("amount", 1) or 1)))
                    out_rows.append(item)
            exported_effects[class_name] = out_rows
        data["spell_effects"] = exported_effects
        race_items.append({"uid": _dwpack_uid("race", r["name"]), "name": r["name"], "sort_order": int(r["sort_order"]), "data": data})

    expansion_items = []
    for r in expansion_rows:
        data = normalize_expansion_data(jload(r["data_json"], {}) or {})
        data.pop("builtin", None)
        expansion_items.append({
            "uid": _dwpack_uid("expansion", r["name"], r["id"]),
            "name": r["name"],
            "gm_condition": r["gm_condition"],
            "public_intro": r["public_intro"],
            "sort_order": int(r["sort_order"]),
            "data": data,
        })

    folder_items = [{"uid": folder_uid_by_id[int(r["id"])], "name": r["name"], "sort_order": int(r["sort_order"])} for r in folder_rows]
    monster_items = []
    for r in monster_rows:
        folder_uid = folder_uid_by_id.get(int(r["folder_id"])) if r["folder_id"] is not None else None
        monster_items.append({
            "uid": _dwpack_uid("monster", r["name"], r["folder_id"], r["sort_order"], r["id"]),
            "name": r["name"],
            "folder_uid": folder_uid,
            "sort_order": int(r["sort_order"]),
            "data": normalize_monster_data(jload(r["data_json"], {}) or {}, None),
        })

    npc_items = []
    for r in npc_rows:
        data = normalize_npc_data(jload(r["data_json"], {}) or {})
        data["favorite"] = bool(r["favorite"])
        npc_items.append({
            "uid": _dwpack_uid("npc", r["name"], r["sort_order"], r["id"]),
            "name": r["name"],
            "favorite": bool(r["favorite"]),
            "sort_order": int(r["sort_order"]),
            "data": data,
        })

    contents = {
        "rules": 1 if include_rules else 0,
        "core_moves": len(core_items),
        "classes": len(class_items),
        "spells": len(spell_items),
        "races": len(race_items),
        "expansions": len(expansion_items),
        "monster_folders": len(folder_items),
        "monsters": len(monster_items),
        "npcs": len(npc_items),
    }
    manifest = {
        "format": DWPACK_FORMAT,
        "format_version": DWPACK_FORMAT_VERSION,
        "name": f"{room['campaign_name']} 데이터",
        "created_with": VERSION,
        "created_at": now_iso(),
        "contents": contents,
        "warnings": warnings,
    }
    files: dict[str, Any] = {"manifest.json": manifest}
    if include_rules:
        files[DWPACK_DATA_FILES["rules"]] = normalize_rules(jload(room["rules_json"], {}) or {})
    files[DWPACK_DATA_FILES["core_moves"]] = core_items
    files[DWPACK_DATA_FILES["classes"]] = class_items
    files[DWPACK_DATA_FILES["spells"]] = spell_items
    files[DWPACK_DATA_FILES["races"]] = race_items
    files[DWPACK_DATA_FILES["expansions"]] = expansion_items
    files[DWPACK_DATA_FILES["monster_folders"]] = folder_items
    files[DWPACK_DATA_FILES["monsters"]] = monster_items
    if include_npcs:
        files[DWPACK_DATA_FILES["npcs"]] = npc_items
    return _dwpack_zip_bytes(files), manifest


def _dwpack_read_upload(raw: bytes) -> dict[str, Any]:
    if not raw:
        raise HTTPException(400, "빈 팩입니다.")
    if len(raw) > DWPACK_MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"팩은 최대 {DWPACK_MAX_UPLOAD_BYTES // (1024*1024)}MB까지 가져올 수 있습니다.")
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw), "r")
    except zipfile.BadZipFile:
        raise HTTPException(400, "올바른 .dwpack ZIP 패키지가 아닙니다.")
    with zf:
        infos = zf.infolist()
        if len(infos) > 64:
            raise HTTPException(400, "팩 안의 파일 수가 너무 많습니다.")
        total_uncompressed = sum(max(0, int(x.file_size)) for x in infos)
        if total_uncompressed > DWPACK_MAX_UNCOMPRESSED_BYTES:
            raise HTTPException(400, "압축 해제된 팩의 크기가 허용 범위를 넘습니다.")
        for info in infos:
            if info.flag_bits & 0x1:
                raise HTTPException(400, "암호화된 팩은 지원하지 않습니다.")
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or "../" in name or name.endswith("/"):
                if name.endswith("/"):
                    continue
                raise HTTPException(400, "안전하지 않은 팩 경로가 포함되어 있습니다.")
        if "manifest.json" not in zf.namelist():
            raise HTTPException(400, "manifest.json이 없는 팩입니다.")

        def read_json(name: str, default: Any) -> Any:
            if name not in zf.namelist():
                return default
            try:
                return json.loads(zf.read(name).decode("utf-8-sig"))
            except Exception:
                raise HTTPException(400, f"{name}을 JSON으로 읽을 수 없습니다.")

        manifest = read_json("manifest.json", {})
        if not isinstance(manifest, dict) or manifest.get("format") != DWPACK_FORMAT:
            raise HTTPException(400, "Dungeon World Online 팩 형식이 아닙니다.")
        try:
            fmt = int(manifest.get("format_version", 0))
        except Exception:
            fmt = 0
        if fmt != DWPACK_FORMAT_VERSION:
            raise HTTPException(400, f"지원하지 않는 .dwpack 형식 버전입니다. 지원: {DWPACK_FORMAT_VERSION}, 파일: {fmt}")

        names_set = set(zf.namelist())
        pack: dict[str, Any] = {"manifest": manifest, "_present": {k: (v in names_set) for k, v in DWPACK_DATA_FILES.items()}}
        pack["rules"] = read_json(DWPACK_DATA_FILES["rules"], None)
        for key in ("core_moves", "classes", "spells", "races", "expansions", "monster_folders", "monsters", "npcs"):
            value = read_json(DWPACK_DATA_FILES[key], [])
            if not isinstance(value, list):
                raise HTTPException(400, f"{DWPACK_DATA_FILES[key]}은 배열이어야 합니다.")
            pack[key] = value
    _dwpack_validate_pack(pack)
    return pack


def _dwpack_require_uid(item: dict[str, Any], kind: str) -> str:
    uid = str(item.get("uid", "")).strip()
    if not uid or not DWPACK_UID_RE.fullmatch(uid):
        raise HTTPException(400, f"{kind} 항목에 올바른 uid가 필요합니다.")
    return uid


def _dwpack_validate_pack(pack: dict[str, Any]) -> None:
    seen_uids: set[str] = set()
    spell_uids: set[str] = set()
    folder_uids: set[str] = set()

    if pack.get("rules") is not None and not isinstance(pack.get("rules"), dict):
        raise HTTPException(400, "data/rules.json은 객체여야 합니다.")

    limits = {"core_moves": 1000, "classes": 300, "spells": 5000, "races": 1000, "expansions": 1000, "monster_folders": 1000, "monsters": 10000, "npcs": 10000}
    for key, limit in limits.items():
        if len(pack.get(key) or []) > limit:
            raise HTTPException(400, f"{key} 항목 수가 허용 범위를 넘습니다.")
        for raw in pack.get(key) or []:
            if not isinstance(raw, dict):
                raise HTTPException(400, f"{key}에는 객체만 들어갈 수 있습니다.")
            uid = _dwpack_require_uid(raw, key)
            if uid in seen_uids:
                raise HTTPException(400, f"중복 uid가 있습니다: {uid}")
            seen_uids.add(uid)
            name = str(raw.get("name", "")).strip()
            if key != "monster_folders" and not name:
                raise HTTPException(400, f"{key} 항목에 이름이 필요합니다.")
            if key == "monster_folders" and not name:
                raise HTTPException(400, "몬스터 폴더 이름이 비어 있습니다.")
            if len(name) > 200:
                raise HTTPException(400, f"이름이 너무 깁니다: {name[:40]}")
            if key == "spells":
                class_name = str(raw.get("class_name", "")).strip()
                if not class_name:
                    raise HTTPException(400, f"주문 {name}에 class_name이 필요합니다.")
                normalize_spell_level(raw.get("level", ""))
                spell_uids.add(uid)
            if key == "monster_folders":
                folder_uids.add(uid)

    for raw in pack.get("races") or []:
        data = raw.get("data") or {}
        if not isinstance(data, dict):
            raise HTTPException(400, f"종족 {raw.get('name','')}의 data는 객체여야 합니다.")
        effects = dict(data.get("spell_effects") or {})
        for _, rows in effects.items():
            if not isinstance(rows, list):
                raise HTTPException(400, "종족 spell_effects는 배열이어야 합니다.")
            for effect in rows:
                if not isinstance(effect, dict):
                    raise HTTPException(400, "종족 주문 효과는 객체여야 합니다.")
                kind = str(effect.get("kind", ""))
                if kind not in {"cross_class_access", "level_reduce", "grant_unclassified"}:
                    raise HTTPException(400, f"지원하지 않는 종족 주문 효과입니다: {kind}")
                if kind in {"level_reduce", "grant_unclassified"}:
                    suid = str(effect.get("spell_uid", "")).strip()
                    if not suid or suid not in spell_uids:
                        raise HTTPException(400, f"종족 주문 효과가 팩 안에 없는 주문 uid를 참조합니다: {suid or '(없음)'}")

    for raw in pack.get("monsters") or []:
        fuid = raw.get("folder_uid")
        if fuid not in (None, "") and str(fuid) not in folder_uids:
            raise HTTPException(400, f"몬스터 {raw.get('name','')}가 팩 안에 없는 폴더 uid를 참조합니다: {fuid}")


def _dwpack_counts(pack: dict[str, Any]) -> dict[str, int]:
    return {
        "rules": 1 if pack.get("rules") is not None else 0,
        "core_moves": len(pack.get("core_moves") or []),
        "classes": len(pack.get("classes") or []),
        "spells": len(pack.get("spells") or []),
        "races": len(pack.get("races") or []),
        "expansions": len(pack.get("expansions") or []),
        "monster_folders": len(pack.get("monster_folders") or []),
        "monsters": len(pack.get("monsters") or []),
        "npcs": len(pack.get("npcs") or []),
    }


def _dwpack_conflicts(con: sqlite3.Connection, room_id: int, pack: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if pack.get("rules") is not None:
        out.append({"kind": "rules", "name": "캠페인 규칙"})
    for x in pack.get("core_moves") or []:
        if con.execute("SELECT 1 FROM core_moves WHERE room_id=? AND name=?", (room_id, x["name"])).fetchone(): out.append({"kind":"core_moves","name":x["name"]})
    for x in pack.get("classes") or []:
        if con.execute("SELECT 1 FROM class_defs WHERE room_id=? AND name=?", (room_id, x["name"])).fetchone(): out.append({"kind":"classes","name":x["name"]})
    for x in pack.get("spells") or []:
        if con.execute("SELECT 1 FROM spell_defs WHERE room_id=? AND class_name=? AND name=?", (room_id, x["class_name"], x["name"])).fetchone(): out.append({"kind":"spells","name":f"{x['class_name']} · {x['name']}"})
    for x in pack.get("races") or []:
        if con.execute("SELECT 1 FROM race_defs WHERE room_id=? AND name=?", (room_id, x["name"])).fetchone(): out.append({"kind":"races","name":x["name"]})
    for x in pack.get("expansions") or []:
        if con.execute("SELECT 1 FROM expansion_defs WHERE room_id=? AND name=?", (room_id, x["name"])).fetchone(): out.append({"kind":"expansions","name":x["name"]})
    for x in pack.get("monster_folders") or []:
        if con.execute("SELECT 1 FROM monster_folders WHERE room_id=? AND name=?", (room_id, x["name"])).fetchone(): out.append({"kind":"monster_folders","name":x["name"]})
    folder_name_by_uid = {x["uid"]: x["name"] for x in pack.get("monster_folders") or []}
    current_folders = {r["name"]: int(r["id"]) for r in con.execute("SELECT id,name FROM monster_folders WHERE room_id=?", (room_id,))}
    for x in pack.get("monsters") or []:
        fname = folder_name_by_uid.get(x.get("folder_uid"), "")
        folder_id = current_folders.get(fname) if fname else None
        if con.execute("SELECT 1 FROM monster_defs WHERE room_id=? AND folder_id IS ? AND name=?", (room_id, folder_id, x["name"])).fetchone(): out.append({"kind":"monsters","name":f"{fname + ' · ' if fname else ''}{x['name']}"})
    for x in pack.get("npcs") or []:
        if con.execute("SELECT 1 FROM npc_defs WHERE room_id=? AND name=?", (room_id, x["name"])).fetchone(): out.append({"kind":"npcs","name":x["name"]})
    return out


def _dwpack_unique_name(con: sqlite3.Connection, table: str, room_id: int, base: str, class_name: str | None = None, folder_id: int | None = None) -> str:
    root = f"{base} (가져옴)"
    candidate = root
    idx = 2
    while True:
        if table == "spell_defs":
            exists = con.execute("SELECT 1 FROM spell_defs WHERE room_id=? AND class_name=? AND name=?", (room_id, class_name or "", candidate)).fetchone()
        elif table == "monster_defs":
            exists = con.execute("SELECT 1 FROM monster_defs WHERE room_id=? AND folder_id IS ? AND name=?", (room_id, folder_id, candidate)).fetchone()
        else:
            exists = con.execute(f"SELECT 1 FROM {table} WHERE room_id=? AND name=?", (room_id, candidate)).fetchone()
        if not exists:
            return candidate[:200]
        candidate = f"{root} {idx}"
        idx += 1


def _dwpack_transform_race_data(data: dict[str, Any], class_name_map: dict[str, str], spell_id_by_uid: dict[str, int]) -> dict[str, Any]:
    raw = dict(data or {})
    per = {}
    for cname, desc in dict(raw.get("per_class") or {}).items():
        per[class_name_map.get(str(cname), str(cname))] = str(desc or "")
    enabled = [class_name_map.get(str(c), str(c)) for c in list(raw.get("enabled_classes") or [])]
    effects: dict[str, list[dict[str, Any]]] = {}
    for cname, rows in dict(raw.get("spell_effects") or {}).items():
        out_rows = []
        for e in list(rows or []):
            e = dict(e or {})
            kind = str(e.get("kind", ""))
            if kind == "cross_class_access":
                out_rows.append({"kind": kind, "source_class": class_name_map.get(str(e.get("source_class", "")), str(e.get("source_class", ""))), "count": max(1, min(10, int(e.get("count", 1) or 1)))})
            elif kind in {"level_reduce", "grant_unclassified"}:
                sid = spell_id_by_uid.get(str(e.get("spell_uid", "")))
                if not sid:
                    raise HTTPException(400, "종족 주문 효과의 주문 참조를 가져올 수 없습니다.")
                item = {"kind": kind, "spell_id": sid}
                if kind == "level_reduce": item["amount"] = max(1, min(99, int(e.get("amount", 1) or 1)))
                out_rows.append(item)
        effects[class_name_map.get(str(cname), str(cname))] = out_rows
    raw["per_class"] = per
    raw["enabled_classes"] = list(dict.fromkeys(enabled))
    raw["spell_effects"] = effects
    raw.pop("spell_access", None)
    return normalize_race_data(raw)


def _dwpack_sync_clear(con: sqlite3.Connection, room_id: int, pack: dict[str, Any]) -> None:
    """Clear only content categories explicitly present in a pack.

    Exact-sync is intentionally restricted to campaigns without player members because
    replacing class/race/spell/expansion definitions under live character data can create
    broken semantic references even when SQLite foreign keys remain valid.
    """
    if con.execute("SELECT 1 FROM members WHERE room_id=? AND role='player' LIMIT 1", (room_id,)).fetchone():
        raise HTTPException(400, "팩과 동일하게 전체 교체는 아직 플레이어가 없는 캠페인에서만 사용할 수 있습니다. 기존 캠페인에서는 충돌 처리 방식을 사용하세요.")
    present = dict(pack.get("_present") or {})
    # Relationships first. monster_catalog is cascaded by monster_defs; grants are absent
    # when there are no player characters, but delete explicitly for a clean definition set.
    if present.get("expansions"):
        con.execute("DELETE FROM expansion_grants WHERE room_id=?", (room_id,))
        con.execute("DELETE FROM expansion_defs WHERE room_id=?", (room_id,))
    if present.get("monsters"):
        con.execute("DELETE FROM monster_defs WHERE room_id=?", (room_id,))
    if present.get("monster_folders"):
        con.execute("DELETE FROM monster_folders WHERE room_id=?", (room_id,))
    if present.get("races"):
        con.execute("DELETE FROM race_defs WHERE room_id=?", (room_id,))
    if present.get("spells"):
        con.execute("DELETE FROM spell_defs WHERE room_id=?", (room_id,))
    if present.get("classes"):
        con.execute("DELETE FROM class_defs WHERE room_id=?", (room_id,))
    if present.get("core_moves"):
        con.execute("DELETE FROM core_moves WHERE room_id=?", (room_id,))
    if present.get("npcs"):
        con.execute("DELETE FROM npc_defs WHERE room_id=?", (room_id,))


def _dwpack_apply(con: sqlite3.Connection, room: sqlite3.Row, pack: dict[str, Any], conflict_mode: str, apply_rules: bool) -> dict[str, int]:
    room_id = int(room["id"])
    if conflict_mode not in {"keep", "replace", "duplicate"}:
        raise HTTPException(400, "충돌 처리 방식이 올바르지 않습니다.")
    counts = {"rules":0,"core_moves":0,"classes":0,"spells":0,"races":0,"expansions":0,"monster_folders":0,"monsters":0,"npcs":0,"skipped":0}

    if apply_rules and pack.get("rules") is not None:
        con.execute("UPDATE rooms SET rules_json=? WHERE id=?", (jdump(normalize_rules(pack["rules"])), room_id))
        counts["rules"] = 1

    # Core moves
    for x in pack.get("core_moves") or []:
        name = str(x["name"]).strip()
        data = dict(x.get("data") or {}); data["name"] = name
        row = con.execute("SELECT id FROM core_moves WHERE room_id=? AND name=?", (room_id, name)).fetchone()
        if row and conflict_mode == "keep": counts["skipped"] += 1; continue
        if row and conflict_mode == "replace": con.execute("UPDATE core_moves SET data_json=? WHERE id=?", (jdump(data), row["id"])); counts["core_moves"] += 1; continue
        if row and conflict_mode == "duplicate": name = _dwpack_unique_name(con, "core_moves", room_id, name); data["name"] = name
        con.execute("INSERT INTO core_moves(room_id,name,data_json) VALUES(?,?,?)", (room_id, name, jdump(data))); counts["core_moves"] += 1

    # Classes first so spell/race class references can be remapped.
    class_name_map: dict[str, str] = {}
    applied_class_targets: list[str] = []
    next_class_order = int(con.execute("SELECT COALESCE(MAX(sort_order),0)+1 n FROM class_defs WHERE room_id=?", (room_id,)).fetchone()["n"])
    for x in pack.get("classes") or []:
        original = str(x["name"]).strip(); target = original
        row = con.execute("SELECT id FROM class_defs WHERE room_id=? AND name=?", (room_id, target)).fetchone()
        if row and conflict_mode == "duplicate": target = _dwpack_unique_name(con, "class_defs", room_id, original); row = None
        class_name_map[original] = target
        data = normalize_class_data(dict(x.get("data") or {})); data.pop("races", None)
        if row and conflict_mode == "keep": counts["skipped"] += 1; continue
        if row and conflict_mode == "replace":
            con.execute("UPDATE class_defs SET data_json=? WHERE id=?", (jdump(data), row["id"])); counts["classes"] += 1; applied_class_targets.append(target); continue
        con.execute("INSERT INTO class_defs(room_id,name,data_json,sort_order) VALUES(?,?,?,?)", (room_id, target, jdump(data), next_class_order)); next_class_order += 1; counts["classes"] += 1; applied_class_targets.append(target)

    # Remap move-effect class references only in class definitions that this pack
    # actually inserted/replaced. A keep-conflict must never rewrite GM data.
    for target in applied_class_targets:
        row = con.execute("SELECT id,data_json FROM class_defs WHERE room_id=? AND name=?", (room_id, target)).fetchone()
        if not row: continue
        data = normalize_class_data(jload(row["data_json"], {}) or {}); changed = False
        for section in ("start", "a25", "a610"):
            for move in data.get(section, []) or []:
                for effect in move.get("move_effects", []) or []:
                    source = str(effect.get("source_class", ""))
                    mapped = class_name_map.get(source, source)
                    if source and source != "*" and mapped != source:
                        effect["source_class"] = mapped; changed = True
        if changed: con.execute("UPDATE class_defs SET data_json=? WHERE id=?", (jdump(data), row["id"]))

    # Spells create the portable uid -> local DB id map used by racial spell effects.
    spell_id_by_uid: dict[str, int] = {}
    for x in pack.get("spells") or []:
        original_class = str(x["class_name"]).strip()
        target_class = class_name_map.get(original_class, original_class)
        if target_class != "__undefined__" and not con.execute("SELECT 1 FROM class_defs WHERE room_id=? AND name=?", (room_id, target_class)).fetchone():
            raise HTTPException(400, f"주문 {x['name']}의 직업 {target_class}을 찾을 수 없습니다.")
        level = normalize_spell_level(x.get("level", ""))
        target_name = str(x["name"]).strip()
        row = con.execute("SELECT id FROM spell_defs WHERE room_id=? AND class_name=? AND name=?", (room_id, target_class, target_name)).fetchone()
        if row and conflict_mode == "duplicate": target_name = _dwpack_unique_name(con, "spell_defs", room_id, target_name, class_name=target_class); row = None
        item = {"name": target_name, "level": level, "desc": str(x.get("desc", ""))[:20000]}
        if row and conflict_mode == "keep": spell_id_by_uid[str(x["uid"])] = int(row["id"]); counts["skipped"] += 1; continue
        if row and conflict_mode == "replace":
            con.execute("UPDATE spell_defs SET level=?,data_json=? WHERE id=?", (level, jdump(item), row["id"])); spell_id_by_uid[str(x["uid"])] = int(row["id"]); counts["spells"] += 1; continue
        cur = con.execute("INSERT INTO spell_defs(room_id,class_name,name,level,data_json) VALUES(?,?,?,?,?)", (room_id, target_class, target_name, level, jdump(item)))
        spell_id_by_uid[str(x["uid"])] = int(cur.lastrowid); counts["spells"] += 1

    # Races after spells.
    next_race_order = int(con.execute("SELECT COALESCE(MAX(sort_order),0)+1 n FROM race_defs WHERE room_id=?", (room_id,)).fetchone()["n"])
    for x in pack.get("races") or []:
        name = str(x["name"]).strip()
        row = con.execute("SELECT id FROM race_defs WHERE room_id=? AND name=?", (room_id, name)).fetchone()
        if row and conflict_mode == "duplicate": name = _dwpack_unique_name(con, "race_defs", room_id, name); row = None
        data = _dwpack_transform_race_data(dict(x.get("data") or {}), class_name_map, spell_id_by_uid)
        data["name"] = name
        if row and conflict_mode == "keep": counts["skipped"] += 1; continue
        if row and conflict_mode == "replace": con.execute("UPDATE race_defs SET data_json=? WHERE id=?", (jdump(data), row["id"])); counts["races"] += 1; continue
        con.execute("INSERT INTO race_defs(room_id,name,data_json,sort_order) VALUES(?,?,?,?)", (room_id, name, jdump(data), next_race_order)); next_race_order += 1; counts["races"] += 1

    # Expansions are always treated as GM-owned definitions after import.
    next_exp_order = int(con.execute("SELECT COALESCE(MAX(sort_order),0)+1 n FROM expansion_defs WHERE room_id=?", (room_id,)).fetchone()["n"])
    for x in pack.get("expansions") or []:
        name = str(x["name"]).strip()
        row = con.execute("SELECT id FROM expansion_defs WHERE room_id=? AND name=?", (room_id, name)).fetchone()
        if row and conflict_mode == "duplicate": name = _dwpack_unique_name(con, "expansion_defs", room_id, name); row = None
        data = normalize_expansion_data(dict(x.get("data") or {})); data.pop("builtin", None)
        gm_condition = str(x.get("gm_condition", ""))[:12000]; public_intro = str(x.get("public_intro", ""))[:12000]
        if row and conflict_mode == "keep": counts["skipped"] += 1; continue
        if row and conflict_mode == "replace":
            con.execute("UPDATE expansion_defs SET gm_condition=?,public_intro=?,data_json=?,user_modified=1,builtin_key='' WHERE id=?", (gm_condition, public_intro, jdump(data), row["id"])); counts["expansions"] += 1; continue
        con.execute("INSERT INTO expansion_defs(room_id,name,gm_condition,public_intro,data_json,sort_order,builtin_key,user_modified,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (room_id, name, gm_condition, public_intro, jdump(data), next_exp_order, "", 1, now_iso())); next_exp_order += 1; counts["expansions"] += 1

    # Monster folders and their portable references.
    folder_id_by_uid: dict[str, int] = {}
    next_folder_order = int(con.execute("SELECT COALESCE(MAX(sort_order),0)+1 n FROM monster_folders WHERE room_id=?", (room_id,)).fetchone()["n"])
    for x in pack.get("monster_folders") or []:
        name = str(x["name"]).strip()
        row = con.execute("SELECT id FROM monster_folders WHERE room_id=? AND name=?", (room_id, name)).fetchone()
        if row and conflict_mode == "duplicate": name = _dwpack_unique_name(con, "monster_folders", room_id, name); row = None
        if row:
            folder_id_by_uid[str(x["uid"])] = int(row["id"])
            if conflict_mode == "keep": counts["skipped"] += 1; continue
            if conflict_mode == "replace": counts["monster_folders"] += 1; continue
        cur = con.execute("INSERT INTO monster_folders(room_id,name,sort_order,created_at) VALUES(?,?,?,?)", (room_id, name, next_folder_order, now_iso())); next_folder_order += 1
        folder_id_by_uid[str(x["uid"])] = int(cur.lastrowid); counts["monster_folders"] += 1

    imported_tags: list[str] = []
    next_monster_order: dict[int | None, int] = {}
    for x in pack.get("monsters") or []:
        folder_id = folder_id_by_uid.get(str(x.get("folder_uid"))) if x.get("folder_uid") not in (None, "") else None
        name = str(x["name"]).strip()
        row = con.execute("SELECT id FROM monster_defs WHERE room_id=? AND folder_id IS ? AND name=? ORDER BY id LIMIT 1", (room_id, folder_id, name)).fetchone()
        if row and conflict_mode == "duplicate": name = _dwpack_unique_name(con, "monster_defs", room_id, name, folder_id=folder_id); row = None
        data = normalize_monster_data(dict(x.get("data") or {}), None)
        imported_tags.extend(data.get("tags") or [])
        if row and conflict_mode == "keep": counts["skipped"] += 1; continue
        if row and conflict_mode == "replace":
            con.execute("UPDATE monster_defs SET data_json=?,updated_at=? WHERE id=?", (jdump(data), now_iso(), row["id"])); counts["monsters"] += 1; continue
        if folder_id not in next_monster_order:
            next_monster_order[folder_id] = int(con.execute("SELECT COALESCE(MAX(sort_order),0)+1 n FROM monster_defs WHERE room_id=? AND folder_id IS ?", (room_id, folder_id)).fetchone()["n"])
        order = next_monster_order[folder_id]; next_monster_order[folder_id] += 1
        t = now_iso(); con.execute("INSERT INTO monster_defs(room_id,folder_id,name,data_json,sort_order,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", (room_id, folder_id, name, jdump(data), order, t, t)); counts["monsters"] += 1

    # Keep imported monster tags selectable even when the full rules block is not applied.
    if imported_tags:
        rr = normalize_rules(jload(con.execute("SELECT rules_json FROM rooms WHERE id=?", (room_id,)).fetchone()["rules_json"], {}) or {})
        tags = list(rr.get("monster_tags") or [])
        for tag in imported_tags:
            if tag not in tags: tags.append(tag)
        rr["monster_tags"] = tags[:100]
        con.execute("UPDATE rooms SET rules_json=? WHERE id=?", (jdump(normalize_rules(rr)), room_id))

    next_npc_order = int(con.execute("SELECT COALESCE(MAX(sort_order),0)+1 n FROM npc_defs WHERE room_id=?", (room_id,)).fetchone()["n"])
    for x in pack.get("npcs") or []:
        name = str(x["name"]).strip()
        row = con.execute("SELECT id FROM npc_defs WHERE room_id=? AND name=? ORDER BY id LIMIT 1", (room_id, name)).fetchone()
        if row and conflict_mode == "duplicate": name = _dwpack_unique_name(con, "npc_defs", room_id, name); row = None
        data = normalize_npc_data(dict(x.get("data") or {})); favorite = 1 if bool(x.get("favorite", data.get("favorite", False))) else 0
        if row and conflict_mode == "keep": counts["skipped"] += 1; continue
        if row and conflict_mode == "replace": con.execute("UPDATE npc_defs SET data_json=?,favorite=?,updated_at=? WHERE id=?", (jdump(data), favorite, now_iso(), row["id"])); counts["npcs"] += 1; continue
        t=now_iso(); con.execute("INSERT INTO npc_defs(room_id,name,data_json,favorite,sort_order,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", (room_id, name, jdump(data), favorite, next_npc_order, t, t)); next_npc_order += 1; counts["npcs"] += 1

    # Packs created before data-driven spellcasting profiles can still be
    # imported safely. After both classes and spells exist, fill only missing
    # profiles with seed metadata or a permissive manual profile.
    ensure_spellcasting_profiles(con, room_id)
    touch_room(con, room_id)
    return counts


class CreateRoomIn(BaseModel):
    gm_name: str = Field(min_length=1, max_length=40)
    campaign_name: str = Field(default="새 캠페인", min_length=1, max_length=80)
    password: str = Field(default="", max_length=80)
    max_players: int = Field(default=4, ge=2, le=8)


class JoinRoomIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=40)
    password: str = Field(default="", max_length=80)
    # First join creates an unassigned character until onboarding is completed.
    # Old launchers may still send these fields; they are intentionally ignored.
    class_name: str | None = None
    race_name: str | None = None


class PatchCharacterIn(BaseModel):
    patch: dict[str, Any]


class FinishOnboardingIn(BaseModel):
    class_name: str = Field(min_length=1, max_length=60)
    race_name: str = Field(min_length=1, max_length=60)


class ClassDefIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    old_name: str | None = None
    data: dict[str, Any]


class RulesIn(BaseModel):
    rules: dict[str, Any]


class SettingsIn(BaseModel):
    settings: dict[str, Any]


class NPCIn(BaseModel):
    id: int | None = None
    name: str = Field(min_length=1, max_length=120)
    data: dict[str, Any] = Field(default_factory=dict)


class MonsterFolderIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class MonsterIn(BaseModel):
    id: int | None = None
    folder_id: int | None = None
    name: str = Field(min_length=1, max_length=120)
    data: dict[str, Any] = Field(default_factory=dict)


class MonsterCatalogIn(BaseModel):
    reveal: dict[str, bool] = Field(default_factory=dict)


class ReorderIn(BaseModel):
    ids: list[int] = Field(default_factory=list, max_length=500)
    names: list[str] = Field(default_factory=list, max_length=500)
    folder_id: int | None = None


class CampaignIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class SpellIn(BaseModel):
    id: int | None = None
    class_name: str
    name: str
    level: str | int
    desc: str = ""


class ExpansionIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    gm_condition: str = ""
    public_intro: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


class ExpansionOrderIn(BaseModel):
    ids: list[int] = Field(default_factory=list, max_length=200)


class GrantIn(BaseModel):
    character_id: int
    visible_to_party: bool = False
    message: str = Field(default="", max_length=1200)


class GrantResponseIn(BaseModel):
    accept: bool


class RaceDefIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    old_name: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class ManualLogIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class DicePrepareIn(BaseModel):
    dice: dict[str, int] = Field(default_factory=dict)
    modifier: int = 0
    style: dict[str, str] = Field(default_factory=dict)
    context: str = Field(default="", max_length=180)
    roll_mode: str = "normal"
    minimum_total: int | None = None


class SoundLinkIn(BaseModel):
    name: str = Field(default="", max_length=120)
    kind: str = "bgm"
    url: str = Field(min_length=1, max_length=1000)


class SoundPlayIn(BaseModel):
    sound_id: int | None = None
    position: float = 0.0
    volume: float = 1.0


class SoundVolumeIn(BaseModel):
    kind: str = "bgm"
    volume: float = 1.0


class SoundControlIn(BaseModel):
    action: str = "next"
    mode: str | None = None
    position: float = 0.0


class MemberReconnectIn(BaseModel):
    reconnect_code: str = Field(min_length=4, max_length=64)


class MemberEnabledIn(BaseModel):
    enabled: bool = True


class AssignCharacterIn(BaseModel):
    character_id: int


class SpecialSpellGrantIn(BaseModel):
    spell_id: int


class DefaultDataImportIn(BaseModel):
    kinds: list[str] = Field(default_factory=list, max_length=10)


class DataPackImportIn(BaseModel):
    preview_token: str = Field(min_length=8, max_length=120)
    conflict_mode: str = Field(default="keep", max_length=20)
    apply_rules: bool = False


class WSManager:
    def __init__(self) -> None:
        self.rooms: dict[str, set[WebSocket]] = {}
        self.roles: dict[WebSocket, str] = {}
        self.members: dict[WebSocket, int | None] = {}

    async def connect(self, code: str, ws: WebSocket, role: str, member_id: int | None = None) -> None:
        await ws.accept()
        self.rooms.setdefault(code, set()).add(ws)
        self.roles[ws] = role
        self.members[ws] = member_id

    def disconnect(self, code: str, ws: WebSocket) -> None:
        group = self.rooms.get(code)
        self.roles.pop(ws, None)
        self.members.pop(ws, None)
        if group:
            group.discard(ws)
            if not group:
                self.rooms.pop(code, None)

    def online_member_ids(self, code: str) -> set[int]:
        return {int(self.members[w]) for w in self.rooms.get(code, set()) if self.roles.get(w) != "gm" and self.members.get(w) is not None}

    async def kick_member(self, code: str, member_id: int) -> int:
        kicked = 0
        for ws in list(self.rooms.get(code, set())):
            if self.members.get(ws) != member_id:
                continue
            try:
                await ws.send_json({"type": "kicked", "reason": "gm_kick"})
                await ws.close(code=4403)
            except Exception:
                pass
            self.disconnect(code, ws)
            kicked += 1
        return kicked

    async def broadcast(self, code: str, payload: dict[str, Any], roles: set[str] | None = None) -> None:
        dead = []
        for ws in list(self.rooms.get(code, set())):
            if roles is not None and self.roles.get(ws) not in roles:
                continue
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(code, ws)


manager = WSManager()

# Ephemeral live-session state. Persistent game data remains in SQLite.
dice_preparations: dict[str, dict[str, dict[str, Any]]] = {}
sound_states: dict[str, dict[str, Any]] = {}
session_tickets: dict[str, dict[str, Any]] = {}

def _cleanup_session_tickets() -> None:
    now = time.time()
    for key in list(session_tickets):
        if float(session_tickets[key].get("expires_at", 0)) <= now:
            session_tickets.pop(key, None)


def actor_key(actor: dict[str, Any]) -> str:
    return "gm" if actor.get("role") == "gm" else f"player:{actor.get('member_id')}"

def actor_display(con: sqlite3.Connection, room_id: int, actor: dict[str, Any]) -> str:
    if actor.get("role") == "gm":
        return str(actor.get("name") or "GM")
    row = con.execute("SELECT state_json FROM characters WHERE room_id=? AND member_id=?", (room_id, actor.get("member_id"))).fetchone()
    if row:
        st = jload(row["state_json"], {}) or {}
        return str((st.get("profile") or {}).get("name") or actor.get("name") or "플레이어")
    return str(actor.get("name") or "플레이어")

def actor_color(con: sqlite3.Connection, room: sqlite3.Row, actor: dict[str, Any]) -> str:
    settings = normalize_settings(jload(room["settings_json"], {}) or {})
    if actor.get("role") == "gm":
        return settings.get("gm_color", DEFAULT_SETTINGS["gm_color"])
    row = con.execute("SELECT id FROM characters WHERE room_id=? AND member_id=?", (room["id"], actor.get("member_id"))).fetchone()
    if row:
        return settings.get("player_colors", {}).get(str(row["id"]), "#1d5f91")
    return "#1d5f91"

def normalize_dice(raw: dict[str, int]) -> dict[str, int]:
    allowed = ("d2", "d4", "d6", "d8", "d10", "d12")
    out = {}
    total = 0
    for key in allowed:
        try:
            n = max(0, min(20, int(raw.get(key, 0) or 0)))
        except Exception:
            n = 0
        if n:
            out[key] = n
            total += n
    if total < 1:
        raise HTTPException(400, "굴릴 주사위를 하나 이상 선택하세요.")
    if total > 30:
        raise HTTPException(400, "한 번에 굴릴 수 있는 주사위는 최대 30개입니다.")
    return out


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/ping")
def ping():
    return {"ok": True, "version": VERSION, "schema_version": SCHEMA_VERSION, "build": BUILD_ID, "uptime": max(0, int(time.time()-SERVER_STARTED_AT)), "instance": SERVER_INSTANCE_ID}


def require_local_request(request: Request) -> None:
    host = request.client.host if request.client else ""
    if host not in {"127.0.0.1", "::1"}:
        raise HTTPException(403, "호스트 PC에서만 사용할 수 있습니다.")


def _default_route_ipv4() -> str:
    """Best-effort IPv4 used for ordinary outbound traffic."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.2)
        sock.connect(("8.8.8.8", 80))
        value = str(sock.getsockname()[0] or "")
        sock.close()
        return value
    except Exception:
        return ""


def _scan_local_network_addresses() -> list[dict[str, str]]:
    """Best-effort LAN/VPN IPv4 scan, ordered by usefulness."""
    found: set[str] = set()
    preferred = _default_route_ipv4()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            found.add(info[4][0])
    except Exception:
        pass
    if preferred:
        found.add(preferred)
    # Windows often exposes virtual-adapter addresses most reliably through ipconfig.
    if os.name == "nt":
        try:
            cp = subprocess.run(["ipconfig"], capture_output=True, text=True, errors="ignore", timeout=2)
            for line in (cp.stdout or "").splitlines():
                if "IPv4" not in line:
                    continue
                for ip in re.findall(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])", line):
                    found.add(ip)
        except Exception:
            pass
    out: list[dict[str, str]] = []
    for raw in found:
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            continue
        if ip.version != 4 or ip.is_loopback or ip.is_link_local or ip.is_unspecified:
            continue
        kind = "네트워크"
        rank = 50
        if raw.startswith("25."):
            kind, rank = "VPN · Hamachi", 30
        elif ip in ipaddress.ip_network("100.64.0.0/10"):
            kind, rank = "VPN · Tailscale", 25
        elif ip.is_private:
            kind, rank = "로컬 LAN", 10 if raw == preferred else 20
        elif raw == preferred:
            rank = 40
        out.append({"ip": raw, "url": f"http://{raw}:{SERVER_PORT}", "kind": kind, "_rank": rank})
    out.sort(key=lambda x: (int(x.get("_rank", 99)), str(x.get("ip", ""))))
    for x in out:
        x.pop("_rank", None)
    return out


def local_network_addresses() -> list[dict[str, str]]:
    """Return a short-lived cached network scan.

    Windows adapter discovery can invoke ipconfig, so repeated settings/invite refreshes
    should not spawn a process every time. Five seconds is short enough to notice network
    changes while keeping the hot UI path cheap.
    """
    global NETWORK_ADDRESS_CACHE
    now = time.monotonic()
    with NETWORK_ADDRESS_CACHE_LOCK:
        cached_at, cached = NETWORK_ADDRESS_CACHE
        if cached and now - cached_at < NETWORK_ADDRESS_CACHE_TTL:
            return [dict(x) for x in cached]
    scanned = _scan_local_network_addresses()
    with NETWORK_ADDRESS_CACHE_LOCK:
        NETWORK_ADDRESS_CACHE = (now, [dict(x) for x in scanned])
    return scanned


def preferred_invite_addresses() -> list[dict[str, str]]:
    """Collapse duplicate adapter choices while keeping genuinely distinct VPN routes.

    One ordinary LAN invite is enough. Hamachi/Tailscale/public-network routes remain
    independently useful. Loopback is intentionally omitted: a player on the same PC
    can open the host directly and does not need a portable invite code.
    """
    result: list[dict[str, str]] = []
    seen_kind: set[str] = set()
    for item in local_network_addresses():
        kind = str(item.get("kind") or "네트워크")
        group = "로컬 LAN" if kind == "로컬 LAN" else kind
        if group in seen_kind:
            continue
        seen_kind.add(group)
        result.append(item)
    return result


def set_active_campaign_code(code: str | None) -> str:
    global ACTIVE_CAMPAIGN_CODE
    value = str(code or "").strip().upper()
    with ACTIVE_CAMPAIGN_LOCK:
        ACTIVE_CAMPAIGN_CODE = value
    return value


def get_active_campaign_code() -> str:
    with ACTIVE_CAMPAIGN_LOCK:
        return ACTIVE_CAMPAIGN_CODE


def require_active_campaign(room: sqlite3.Row, *, player_only: bool = False, actor: dict[str, Any] | None = None) -> None:
    """Reject player entry to campaigns that the host has not currently opened.

    A host may keep many campaigns in the local database, but only one is exposed
    to players at a time.  This server-side check mirrors launcher discovery so a
    stale recent-entry button, direct URL, or handcrafted request cannot enter an
    offline campaign. GM maintenance remains available for local campaign management.
    """
    if player_only and actor is not None and actor.get("role") == "gm":
        return
    active = get_active_campaign_code()
    if not active or str(room["code"]).upper() != active:
        raise HTTPException(409, "현재 열려 있는 캠페인이 아닙니다. GM이 이 캠페인을 열어야 접속할 수 있습니다.")


def active_campaign_payload(con: sqlite3.Connection) -> dict[str, Any]:
    code = get_active_campaign_code()
    if not code:
        return {"active": False, "room_code": "", "instance": SERVER_INSTANCE_ID}
    room = con.execute("SELECT id,code,campaign_name,gm_name,max_players FROM rooms WHERE code=?", (code,)).fetchone()
    if not room:
        set_active_campaign_code("")
        return {"active": False, "room_code": "", "instance": SERVER_INSTANCE_ID}
    player_count = room_player_count(con, int(room["id"]))
    return {
        "active": True,
        "room_code": room["code"],
        "campaign_name": room["campaign_name"],
        "gm_name": room["gm_name"],
        "player_count": player_count,
        "max_players": room_max_players(room),
        "full": player_count >= room_max_players(room),
        "instance": SERVER_INSTANCE_ID,
    }


@app.get("/api/active-campaign")
def active_campaign():
    with db() as con:
        return active_campaign_payload(con)


@app.get("/api/local/active-campaign")
def local_active_campaign(request: Request):
    require_local_request(request)
    with db() as con:
        return active_campaign_payload(con)


@app.post("/api/local/active-campaign/{code}")
def local_set_active_campaign(code: str, request: Request):
    require_local_request(request)
    with db() as con:
        room = room_by_code(con, code)
        set_active_campaign_code(room["code"])
        return active_campaign_payload(con)


@app.delete("/api/local/active-campaign")
def local_clear_active_campaign(request: Request):
    require_local_request(request)
    set_active_campaign_code("")
    return {"ok": True, "active": False, "room_code": "", "instance": SERVER_INSTANCE_ID}


@app.get("/api/local/campaigns")
def local_campaigns(request: Request):
    require_local_request(request)
    with db() as con:
        rows = []
        for x in con.execute("SELECT id,code,campaign_name,gm_name,max_players,created_at,updated_at FROM rooms ORDER BY updated_at DESC,id DESC"):
            d = dict(x)
            d["player_count"] = room_player_count(con, int(x["id"]))
            d["max_players"] = room_max_players(x)
            d.pop("id", None)
            rows.append(d)
        return {"campaigns": rows}


def encode_launcher_invite(host: str, room_code: str) -> str:
    payload = {"f": 2, "h": host, "p": SERVER_PORT, "r": room_code.upper(), "v": VERSION, "b": BUILD_ID}
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "DW2-" + base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


@app.get("/api/local/network-info")
def local_network_info(request: Request):
    require_local_request(request)
    return {"local_url": f"http://127.0.0.1:{SERVER_PORT}", "addresses": local_network_addresses(), "port": SERVER_PORT}


@app.get("/api/rooms/{code}/invite-codes")
def room_invite_codes(code: str, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
    candidates = []
    for item in preferred_invite_addresses():
        ip = str(item.get("ip") or "").strip()
        if not ip:
            continue
        candidates.append({**item, "invite_code": encode_launcher_invite(ip, code)})
    return {"ok": True, "room": code.upper(), "version": VERSION, "build": BUILD_ID, "invites": candidates}



@app.post("/api/local/campaigns/clear-all")
async def local_clear_all_campaigns(request: Request):
    require_local_request(request)
    with db() as con:
        codes = [r["code"] for r in con.execute("SELECT code FROM rooms")]
        con.execute("DELETE FROM rooms")
    set_active_campaign_code("")
    for code in codes:
        dice_preparations.pop(code.upper(), None)
        sound_states.pop(code.upper(), None)
        shutil.rmtree(SOUND_DIR / code.upper(), ignore_errors=True)
        await manager.broadcast(code, {"type": "deleted", "room": code, "reason": "local_reset"})
    return {"ok": True, "deleted": len(codes)}


@app.delete("/api/local/campaigns/{code}")
async def local_campaign_delete(code: str, request: Request):
    require_local_request(request)
    code = code.upper()
    with db() as con:
        room = room_by_code(con, code)
        con.execute("DELETE FROM rooms WHERE id=?", (room["id"],))
    if get_active_campaign_code() == code:
        set_active_campaign_code("")
    dice_preparations.pop(code, None)
    sound_states.pop(code, None)
    shutil.rmtree(SOUND_DIR / code, ignore_errors=True)
    await manager.broadcast(code, {"type": "deleted", "room": code})
    return {"ok": True, "room_code": code}


@app.post("/api/local/campaigns/{code}/resume")
def local_campaign_resume(code: str, request: Request):
    require_local_request(request)
    token = secrets.token_urlsafe(32)
    with db() as con:
        room = room_by_code(con, code)
        now = now_iso()
        con.execute("INSERT INTO gm_sessions(room_id,token_hash,created_at,last_used_at) VALUES(?,?,?,?)", (room["id"], hash_token(token), now, now))
        old_sessions = list(con.execute("SELECT id FROM gm_sessions WHERE room_id=? ORDER BY last_used_at DESC,id DESC LIMIT -1 OFFSET 20", (room["id"],)))
        if old_sessions:
            con.executemany("DELETE FROM gm_sessions WHERE id=?", [(x["id"],) for x in old_sessions])
        con.execute("UPDATE rooms SET updated_at=? WHERE id=?", (now, room["id"]))
        set_active_campaign_code(room["code"])
        return {"room_code": room["code"], "campaign_name": room["campaign_name"], "gm_name": room["gm_name"], "gm_token": token, "role": "gm"}


@app.post("/api/rooms")
async def create_room(body: CreateRoomIn, request: Request):
    # Campaign creation is host-local. LAN/VPN clients must not create campaigns
    # 호스트의 DB에 임의 캠페인을 만들 수 없도록 로컬 요청만 허용한다.
    require_local_request(request)
    token = secrets.token_urlsafe(32)
    with db() as con:
        code = generate_room_code(con)
        t = now_iso()
        cur = con.execute(
            "INSERT INTO rooms(code,gm_name,gm_token_hash,rules_json,campaign_name,password_hash,settings_json,default_data_initialized,default_data_revision,max_players,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (code, body.gm_name.strip(), hash_token(token), jdump(DEFAULT_RULES), body.campaign_name.strip(), hash_password(body.password), jdump(DEFAULT_SETTINGS), 1, DEFAULT_DATA_REVISION, int(body.max_players), t, t),
        )
        room_id = int(cur.lastrowid)
        seed_room(con, room_id)
        actor = {"role": "gm", "name": body.gm_name.strip()}
        log_event(con, room_id, actor, "캠페인 생성", code, {"version": VERSION, "campaign_name": body.campaign_name.strip(), "max_players": int(body.max_players)})
    set_active_campaign_code(code)
    return {"room_code": code, "gm_token": token, "role": "gm", "campaign_name": body.campaign_name.strip(), "max_players": int(body.max_players)}


@app.get("/api/rooms/{code}/join-info")
def join_info(code: str):
    with db() as con:
        room = room_by_code(con, code)
        require_active_campaign(room)
        classes = class_map(con, room["id"])
        return {
            "room_code": room["code"],
            "campaign_name": room["campaign_name"],
            "gm_name": room["gm_name"],
            "player_count": room_player_count(con, int(room["id"])),
            "max_players": room_max_players(room),
            "full": room_player_count(con, int(room["id"])) >= room_max_players(room),
            "password_required": bool(room["password_hash"]), "source_urls": DW_SOURCE_URLS,
            "classes": [{"name": name, "races": [r.get("name", "") for r in (data.get("races", []) or []) if r.get("name")]} for name, data in classes.items()],
        }


@app.post("/api/rooms/{code}/join")
async def join_room(code: str, body: JoinRoomIn):
    token = secrets.token_urlsafe(32)
    with db() as con:
        room = room_by_code(con, code)
        require_active_campaign(room)
        if room["password_hash"] and not verify_password(body.password, room["password_hash"]):
            raise HTTPException(403, "캠페인 비밀번호가 올바르지 않습니다.")
        # Serialize the seat check with the member insert so two simultaneous joins
        # cannot both claim the last available player slot.
        con.execute("BEGIN IMMEDIATE")
        if room_player_count(con, int(room["id"])) >= room_max_players(room):
            raise HTTPException(409, "캠페인 정원이 가득 찼습니다. GM이 참가자를 정리한 뒤 다시 시도하세요.")
        classes = class_map(con, room["id"])
        cur = con.execute(
            "INSERT INTO members(room_id,role,display_name,token_hash,created_at) VALUES(?,?,?,?,?)",
            (room["id"], "player", body.display_name.strip(), hash_token(token), now_iso()),
        )
        member_id = int(cur.lastrowid)
        state = default_character_state(body.display_name.strip(), classes)
        ccur = con.execute(
            "INSERT INTO characters(room_id,member_id,state_json,created_at,updated_at) VALUES(?,?,?,?,?)",
            (room["id"], member_id, jdump(state), now_iso(), now_iso()),
        )
        char_id = int(ccur.lastrowid)
        actor = {"role": "player", "name": body.display_name.strip(), "member_id": member_id}
        log_event(con, room["id"], actor, "캠페인 입장", f"character:{char_id}", {"status": "운명 선택 중"})
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "join"})
    return {"room_code": code.upper(), "player_token": token, "member_id": member_id, "character_id": char_id, "role": "player", "campaign_name": room["campaign_name"]}



@app.post("/api/rooms/{code}/members/{member_id}/kick")
async def kick_member(code: str, member_id: int, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        member = con.execute("SELECT * FROM members WHERE id=? AND room_id=? AND role='player'", (member_id, room["id"])).fetchone()
        if not member: raise HTTPException(404, "참가자를 찾을 수 없습니다.")
    count = await manager.kick_member(code.upper(), member_id)
    return {"ok": True, "kicked_connections": count}


@app.post("/api/rooms/{code}/members/{member_id}/reconnect-code")
async def member_reconnect_code(code: str, member_id: int, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    raw = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(8))
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        member = con.execute("SELECT * FROM members WHERE id=? AND room_id=? AND role='player'", (member_id, room["id"])).fetchone()
        if not member: raise HTTPException(404, "참가자를 찾을 수 없습니다.")
        con.execute("UPDATE members SET reconnect_code_hash=?,disabled=0 WHERE id=?", (hash_token(raw), member_id))
        log_event(con, room["id"], actor, "재접속 코드 발급", member["display_name"], {"member_id": member_id})
    return {"ok": True, "reconnect_code": f"{code.upper()}-{raw}"}


@app.post("/api/rooms/{code}/reconnect")
async def reconnect_member(code: str, body: MemberReconnectIn):
    supplied = body.reconnect_code.strip().upper()
    if "-" in supplied:
        maybe_room, supplied = supplied.split("-", 1)
        if maybe_room != code.upper():
            raise HTTPException(400, "재접속 코드의 캠페인이 일치하지 않습니다.")
    with db() as con:
        room = room_by_code(con, code)
        require_active_campaign(room)
        h = hash_token(supplied)
        member = con.execute("SELECT * FROM members WHERE room_id=? AND reconnect_code_hash=? AND role='player'", (room["id"], h)).fetchone()
        if not member: raise HTTPException(403, "재접속 코드가 올바르지 않거나 이미 사용되었습니다.")
        token = secrets.token_urlsafe(32)
        con.execute("UPDATE members SET token_hash=?,reconnect_code_hash='',disabled=0 WHERE id=?", (hash_token(token), member["id"]))
        char = con.execute("SELECT id FROM characters WHERE member_id=?", (member["id"],)).fetchone()
    return {"ok": True, "room_code": code.upper(), "player_token": token, "member_id": member["id"], "character_id": int(char["id"]) if char else None, "display_name": member["display_name"]}


@app.put("/api/rooms/{code}/members/{member_id}/enabled")
async def set_member_enabled(code: str, member_id: int, body: MemberEnabledIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        member = con.execute("SELECT * FROM members WHERE id=? AND room_id=? AND role='player'", (member_id, room["id"])).fetchone()
        if not member: raise HTTPException(404, "참가자를 찾을 수 없습니다.")
        if body.enabled and bool(member["disabled"]):
            if room_player_count(con, int(room["id"])) >= room_max_players(room):
                raise HTTPException(409, "캠페인 정원이 가득 차 있어 이 참가자를 다시 활성화할 수 없습니다.")
        con.execute("UPDATE members SET disabled=? WHERE id=?", (0 if body.enabled else 1, member_id))
    if not body.enabled:
        await manager.kick_member(code.upper(), member_id)
    await manager.broadcast(code.upper(), {"type":"refresh","reason":"member"})
    return {"ok": True, "enabled": body.enabled}


@app.put("/api/rooms/{code}/members/{member_id}/character")
async def assign_member_character(code: str, member_id: int, body: AssignCharacterIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        member = con.execute("SELECT * FROM members WHERE id=? AND room_id=? AND role='player'", (member_id, room["id"])).fetchone()
        if not member: raise HTTPException(404, "참가자를 찾을 수 없습니다.")
        target = con.execute("SELECT * FROM characters WHERE id=? AND room_id=?", (body.character_id, room["id"])).fetchone()
        if not target: raise HTTPException(404, "캐릭터를 찾을 수 없습니다.")
        if int(target["member_id"]) == int(member_id):
            return {"ok": True, "character_id": int(target["id"]), "swapped": False}
        old_owner = int(target["member_id"])
        current = con.execute("SELECT * FROM characters WHERE member_id=? AND room_id=?", (member_id, room["id"])).fetchone()
        temp_token = hash_token(secrets.token_urlsafe(32))
        cur = con.execute("INSERT INTO members(room_id,role,display_name,token_hash,created_at,reconnect_code_hash,disabled) VALUES(?,?,?,?,?,?,?)", (room["id"], "system", "__character_swap__", temp_token, now_iso(), "", 1))
        temp_member = int(cur.lastrowid)
        con.execute("UPDATE characters SET member_id=? WHERE id=?", (temp_member, target["id"]))
        if current:
            con.execute("UPDATE characters SET member_id=? WHERE id=?", (old_owner, current["id"]))
        con.execute("UPDATE characters SET member_id=? WHERE id=?", (member_id, target["id"]))
        con.execute("DELETE FROM members WHERE id=?", (temp_member,))
        log_event(con, room["id"], actor, "캐릭터 재배치", member["display_name"], {"member_id": member_id, "character_id": int(target["id"]), "swapped_character_id": int(current["id"]) if current else None})
    await manager.kick_member(code.upper(), member_id)
    await manager.kick_member(code.upper(), old_owner)
    await manager.broadcast(code.upper(), {"type":"refresh","reason":"member_character"})
    return {"ok": True, "character_id": int(body.character_id), "swapped": bool(current)}


@app.delete("/api/rooms/{code}/members/{member_id}")
async def delete_member(code: str, member_id: int, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        member = con.execute("SELECT * FROM members WHERE id=? AND room_id=? AND role='player'", (member_id, room["id"])).fetchone()
        if not member: raise HTTPException(404, "참가자를 찾을 수 없습니다.")
        con.execute("DELETE FROM members WHERE id=?", (member_id,))
        log_event(con, room["id"], actor, "참가자 삭제", member["display_name"], {"member_id": member_id})
    await manager.kick_member(code.upper(), member_id)
    await manager.broadcast(code.upper(), {"type":"refresh","reason":"member"})
    return {"ok": True}


class SessionTicketIn(BaseModel):
    pass


@app.post("/api/rooms/{code}/session-ticket")
def create_session_ticket(code: str, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code)
        actor = auth_context(con, room, token)
        payload = {
            "room": room["code"],
            "token": token,
            "role": actor["role"],
            "name": actor.get("name", ""),
            "expires_at": time.time() + 60.0,
        }
    _cleanup_session_tickets()
    ticket = secrets.token_urlsafe(28)
    session_tickets[ticket] = payload
    return {"ticket": ticket, "expires_in": 60, "url": f"/session/{ticket}"}


@app.get("/session/{ticket}", response_class=HTMLResponse)
def consume_session_ticket(ticket: str, request: Request):
    _cleanup_session_tickets()
    lang = "ko" if request.query_params.get("lang", "").lower() == "ko" else "en"
    payload = session_tickets.pop(ticket, None)
    if not payload or float(payload.get("expires_at", 0)) <= time.time():
        if lang == "en":
            body = "<!doctype html><meta charset='utf-8'><title>Connection Expired</title><body style='font-family:sans-serif;padding:40px'><h1>Your connection ticket has expired.</h1><p>Open Dungeon World again from the EXE launcher.</p></body>"
        else:
            body = "<!doctype html><meta charset='utf-8'><title>접속 만료</title><body style='font-family:sans-serif;padding:40px'><h1>접속 티켓이 만료되었습니다.</h1><p>Dungeon World EXE 런처에서 다시 열어주세요.</p></body>"
        return HTMLResponse(body, status_code=410)
    session = {"room": payload["room"], "token": payload["token"], "role": payload["role"]}
    js_session = json.dumps(session, ensure_ascii=False).replace("<", "\\u003c")
    js_room = json.dumps(payload["room"], ensure_ascii=False)
    js_lang = json.dumps(lang)
    return HTMLResponse(f"""<!doctype html><html lang='{lang}'><head><meta charset='utf-8'><title>Dungeon World</title></head><body><script>sessionStorage.setItem('dw_session_v2', JSON.stringify({js_session}));location.replace('/?mode=play&room='+encodeURIComponent({js_room})+'&lang='+encodeURIComponent({js_lang}));</script></body></html>""")


@app.get("/api/rooms/{code}/state")
def get_state(code: str, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code)
        actor = auth_context(con, room, token)
        settings = normalize_settings(jload(room["settings_json"], {}) or {})
        rules = normalize_rules(jload(room["rules_json"], {}) or {})
        classes = class_map(con, room["id"])
        spells = spell_map(con, room["id"])
        core_moves = core_move_list(con, room["id"])
        races = race_map(con, room["id"])
        sounds = [dict(x) for x in con.execute("SELECT id,kind,name,source_type,source,sort_order,created_at FROM sound_defs WHERE room_id=? AND source_type='file' ORDER BY kind,sort_order,id", (room["id"],))]
        # Join member metadata once instead of issuing one query per character. State is
        # the hottest endpoint because every WebSocket refresh eventually reaches it.
        char_rows = list(con.execute(
            """SELECT c.*,m.disabled AS member_disabled,m.reconnect_code_hash AS member_reconnect_code_hash
               FROM characters c JOIN members m ON m.id=c.member_id
               WHERE c.room_id=? ORDER BY c.id""",
            (room["id"],),
        ))
        online_members = manager.online_member_ids(code.upper())
        my_char = next((c for c in char_rows if int(c["member_id"]) == int(actor.get("member_id") or -1)), None) if actor["role"] != "gm" else None
        my_char_id = my_char["id"] if my_char else None
        expansions_enabled = bool(settings.get("expansions_enabled", False))
        party = [character_summary(con, c, classes, my_char_id, actor["role"] == "gm", expansions_enabled) for c in char_rows]
        for item, row in zip(party, char_rows):
            item["online"] = int(row["member_id"]) in online_members
            item["color"] = settings.get("player_colors", {}).get(str(row["id"]), "#1d5f91")
            item["disabled"] = bool(row["member_disabled"])
            item["reconnect_ready"] = bool(row["member_reconnect_code_hash"])
        sess = active_session(con, room["id"])
        response: dict[str, Any] = {
            "room": {
                "code": room["code"], "campaign_name": room["campaign_name"], "gm_name": room["gm_name"],
                "player_count": room_player_count(con, int(room["id"])), "max_players": room_max_players(room),
                "created_at": room["created_at"], "updated_at": room["updated_at"], "rules": rules, "settings": settings, "password_required": bool(room["password_hash"]), "source_urls": DW_SOURCE_URLS,
                "default_data_initialized": bool(room["default_data_initialized"]), "default_data_revision": str(room["default_data_revision"] or ""),
                "active_session": {"id": sess["id"], "session_no": sess["session_no"], "started_at": sess["started_at"]} if sess else None,
            },
            "me": {"role": actor["role"], "name": actor["name"], "member_id": actor.get("member_id"), "character_id": my_char_id},
            "classes": classes, "races": races, "spells": spells, "core_moves": core_moves, "party": party,
            "sounds": sounds, "sound_state": sound_states.get(code.upper(), {"status":"stopped","sound_id":None,"position":0.0,"volume":1.0,"bgm_volume":1.0,"sfx_volume":1.0,"mode":"next","updated_at":now_iso()}),
            "dice_preparations": [x for x in dice_preparations.get(code.upper(), {}).values() if actor["role"] == "gm" or bool(x.get("public", True))],
        }
        if actor["role"] == "gm":
            full_chars = []
            for c in char_rows:
                full_chars.append({"character_id": c["id"], "member_id": c["member_id"], "state": normalize_character_state(jload(c["state_json"], {}), classes)})
            expansions = []
            for e in con.execute("SELECT * FROM expansion_defs WHERE room_id=? ORDER BY sort_order,id", (room["id"],)):
                expansions.append({
                    "id": e["id"], "name": e["name"], "gm_condition": e["gm_condition"], "public_intro": e["public_intro"],
                    "data": {**normalize_expansion_data(jload(e["data_json"], {})), "sort_order": int(e["sort_order"]), "builtin": bool(e["builtin_key"]) and not bool(e["user_modified"])}, "created_at": e["created_at"],
                })
            expansions.sort(key=lambda x: (int((x.get("data") or {}).get("sort_order", 9999)), x.get("name", "")))
            grants = [dict(g) for g in con.execute("SELECT * FROM expansion_grants WHERE room_id=? ORDER BY id", (room["id"],))]
            logs = []
            for l in con.execute("SELECT * FROM logs WHERE room_id=? ORDER BY id DESC LIMIT 400", (room["id"],)):
                logs.append({
                    "id": l["id"], "session_id": l["session_id"], "actor_role": l["actor_role"], "actor_name": l["actor_name"],
                    "action": l["action"], "target": l["target"], "detail": jload(l["detail_json"], {}), "created_at": l["created_at"],
                })
            sessions = [dict(x) for x in con.execute("SELECT * FROM sessions WHERE room_id=? ORDER BY session_no DESC LIMIT 100", (room["id"],))]
            npcs = []
            for n in con.execute("SELECT * FROM npc_defs WHERE room_id=? ORDER BY favorite DESC,sort_order,id", (room["id"],)):
                nd = normalize_npc_data(jload(n["data_json"], {}) or {}); nd["favorite"] = bool(n["favorite"])
                npcs.append({"id": n["id"], "name": n["name"], "data": nd, "sort_order": n["sort_order"], "created_at": n["created_at"], "updated_at": n["updated_at"]})
            monster_folders = [dict(x) for x in con.execute("SELECT * FROM monster_folders WHERE room_id=? ORDER BY sort_order,name,id", (room["id"],))]
            for f in monster_folders: f["builtin"] = str(f.get("name","")) in set(DW_MONSTER_ENVIRONMENTS)
            allowed_tags = rules.get("monster_tags", [])
            monsters = [{"id": m["id"], "folder_id": m["folder_id"], "name": m["name"], "data": normalize_monster_data(jload(m["data_json"], {}) or {}, allowed_tags), "sort_order": m["sort_order"], "created_at": m["created_at"], "updated_at": m["updated_at"]} for m in con.execute("SELECT * FROM monster_defs WHERE room_id=? ORDER BY sort_order,id", (room["id"],))]
            catalog = [{"id": c["id"], "monster_id": c["monster_id"], "reveal": jload(c["reveal_json"], {}) or {}, "created_at": c["created_at"], "updated_at": c["updated_at"]} for c in con.execute("SELECT * FROM monster_catalog WHERE room_id=? ORDER BY id", (room["id"],))]
            response.update({"characters": full_chars, "expansions": expansions, "grants": grants, "logs": logs, "sessions": sessions, "npcs": npcs, "monster_folders": monster_folders, "monsters": monsters, "monster_catalog_admin": catalog})
        else:
            response["character"] = {"character_id": my_char["id"], "state": normalize_character_state(jload(my_char["state_json"], {}), classes)} if my_char else None
            public_catalog = []
            for crow in con.execute(
                """SELECT c.*,m.name AS monster_name,m.data_json AS monster_data_json
                   FROM monster_catalog c JOIN monster_defs m ON m.id=c.monster_id
                   WHERE c.room_id=? AND m.room_id=c.room_id ORDER BY c.id""",
                (room["id"],),
            ):
                data = normalize_monster_data(jload(crow["monster_data_json"], {}) or {}, rules.get("monster_tags", []))
                reveal = {k: bool(v) for k,v in dict(jload(crow["reveal_json"], {}) or {}).items()}
                def vis(key, value): return value if reveal.get(key, False) else "???"
                public_catalog.append({
                    "id": crow["id"], "monster_id": crow["monster_id"],
                    "name": vis("name", crow["monster_name"]), "hp": vis("hp", data.get("hp")), "armor": vis("armor", data.get("armor")),
                    "attack": vis("attack", data.get("attack", "")), "damage": data.get("damage") if reveal.get("damage") else None,
                    "range": vis("range", data.get("range", "")), "tags": list(data.get("tags", [])) if reveal.get("tags") else None,
                    "instinct": vis("instinct", data.get("instinct", "")), "special": vis("special", data.get("special", "")),
                    "moves": list(data.get("moves", [])) if reveal.get("moves") else None, "description": vis("description", data.get("description", "")),
                    "builtin": bool(data.get("builtin")), "reveal": reveal, "updated_at": crow["updated_at"]
                })
            response["monster_catalog"] = public_catalog
            invites = []
            if my_char and expansions_enabled:
                for g in con.execute("""SELECT g.*,e.name,e.public_intro,e.data_json,e.builtin_key,e.user_modified FROM expansion_grants g JOIN expansion_defs e ON e.id=g.expansion_id WHERE g.character_id=? AND g.status='pending' ORDER BY g.id""", (my_char["id"],)):
                    data = normalize_expansion_data(jload(g["data_json"], {}))
                    invites.append({"grant_id": g["id"], "expansion_id": g["expansion_id"], "name": g["name"], "public_intro": g["public_intro"], "message": g["invite_message"], "theme": data.get("theme", {}), "hidden": bool(data.get("hidden")), "builtin": bool(g["builtin_key"]) and not bool(g["user_modified"])})
            response["expansion_invites"] = invites
        return response


@app.post("/api/rooms/{code}/characters/{character_id}/onboarding")
async def finish_character_onboarding(code: str, character_id: int, body: FinishOnboardingIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code)
        actor = auth_context(con, room, token)
        char = con.execute("SELECT * FROM characters WHERE id=? AND room_id=?", (character_id, room["id"])).fetchone()
        if not char:
            raise HTTPException(404, "캐릭터를 찾을 수 없습니다.")
        if actor["role"] != "player" or char["member_id"] != actor.get("member_id"):
            raise HTTPException(403, "본인의 첫 직업과 종족만 선택할 수 있습니다.")
        classes = class_map(con, room["id"])
        before = normalize_character_state(jload(char["state_json"], {}), classes)
        if before.get("onboarding_complete"):
            raise HTTPException(409, "이미 직업과 종족 선택을 마쳤습니다. 이후 변경은 GM에게 요청해주세요.")
        class_name = body.class_name.strip()
        race_name = body.race_name.strip()
        if class_name not in classes:
            raise HTTPException(400, "존재하지 않는 직업입니다.")
        c = classes[class_name]
        race_names = {str(r.get("name", "")) for r in (c.get("races", []) or []) if r.get("name")}
        if race_name not in race_names:
            raise HTTPException(400, "현재 직업에서 선택할 수 없는 종족입니다.")
        aligns = c.get("alignments", []) or []
        after = dict(before)
        after.update({
            "class_name": class_name,
            "race_name": race_name,
            "onboarding_complete": True,
            "alignment_name": str(aligns[0].get("name", "")) if aligns else "",
            "hp_current": int(c.get("hp", 1) or 1),
            "armor_base": 0,
            "armor": 0,
            "damage_die": str(c.get("damage", "D6") or "D6").upper(),
            "damage_bonus": 0,
            "bonds": [str(x) for x in list(c.get("bonds", []) or [])],
            "advanced_moves": [],
            "extra_moves": [],
            "move_choices": {},
            "spellbook": [],
            "prepared_spells": [],
            "starting_spells_complete": False,
            "spell_tracks": {},
            "inventory": [],
            "memo": "",
        })
        # Keep GM-granted special spells if any were granted while the player was deciding.
        after["extra_spells"] = [dict(x) for x in (before.get("extra_spells") or []) if isinstance(x, dict)]
        after = normalize_character_state(after, classes)
        con.execute("UPDATE characters SET state_json=?,updated_at=? WHERE id=?", (jdump(after), now_iso(), character_id))
        log_event(con, room["id"], actor, "운명 선택", f"character:{character_id}", {"class": class_name, "race": race_name})
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "onboarding"})
    return {"ok": True, "class_name": class_name, "race_name": race_name}


@app.patch("/api/rooms/{code}/characters/{character_id}")
async def patch_character(code: str, character_id: int, body: PatchCharacterIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code)
        actor = auth_context(con, room, token)
        char = con.execute("SELECT * FROM characters WHERE id=? AND room_id=?", (character_id, room["id"])).fetchone()
        if not char:
            raise HTTPException(404, "캐릭터를 찾을 수 없습니다.")
        if actor["role"] != "gm" and char["member_id"] != actor["member_id"]:
            raise HTTPException(403, "다른 플레이어의 캐릭터는 수정할 수 없습니다.")
        if actor["role"] != "gm" and "bonus_stat_points" in body.patch:
            raise HTTPException(403, "추가 능력치 포인트는 GM만 수정할 수 있습니다.")
        if actor["role"] != "gm":
            if "class_name" in body.patch or "race_name" in body.patch:
                raise HTTPException(403, "직업과 종족은 캐릭터 생성 후 GM만 변경할 수 있습니다.")
            if "profile" in body.patch and str((body.patch.get("profile") or {}).get("name", "")) != str((jload(char["state_json"], {}) or {}).get("profile", {}).get("name", "")):
                raise HTTPException(403, "캐릭터 이름은 생성 후 GM만 변경할 수 있습니다.")
        classes = class_map(con, room["id"])
        before = normalize_character_state(jload(char["state_json"], {}), classes)
        after = dict(before); after.update(body.patch)
        rules = normalize_rules(jload(room["rules_json"], {}) or {})
        changed = set(body.patch.keys())
        if actor["role"] != "gm" and "extra_moves" in changed and rules.get("players_can_add_extra_moves") is False:
            before_keys = {(str(x.get("source_class", "")), str(x.get("name", ""))) for x in (before.get("extra_moves") or []) if isinstance(x, dict)}
            requested_keys = {(str(x.get("source_class", "")), str(x.get("name", ""))) for x in (body.patch.get("extra_moves") or []) if isinstance(x, dict)}
            if requested_keys - before_keys:
                raise HTTPException(403, "이 캠페인에서는 다중직업 행동 추가를 GM만 할 수 있습니다.")
        if "extension_state" in changed and not room_expansions_enabled(room):
            raise HTTPException(409, "이 캠페인에서는 확장직업 기능이 꺼져 있습니다.")
        if actor["role"] != "gm":
            if "stats" in changed:
                was_initialized = bool(before.get("stats_initialized"))
                _validate_initial_stat_assignment(before, after, rules)
                if was_initialized:
                    tracked = before.get("stat_growth_spent")
                    if tracked is None:
                        base_total = sum(int(x) for x in (rules.get("stat_start") or [16,15,13,12,9,8])[:6])
                        tracked = max(0, sum(int(x) for x in (before.get("stats") or {}).values()) - base_total)
                    delta_total = sum(int(x) for x in (after.get("stats") or {}).values()) - sum(int(x) for x in (before.get("stats") or {}).values())
                    after["stat_growth_spent"] = max(0, int(tracked or 0) + delta_total)
                elif bool(after.get("stats_initialized")):
                    after["stat_growth_spent"] = 0
            if changed & {"stats", "level"}:
                validate_stat_growth_budget(before, after)
            validate_player_state(after, classes, rules, changed)
            if "extension_state" in changed:
                validate_player_extension_state(con, character_id, after)
            if changed & {"advanced_moves", "extension_state", "level"}:
                validate_advanced_move_point_budget(before, after, rules)
        else:
            # GM can override move-choice limits, but the campaign maximum level is
            # a real campaign rule and remains authoritative for every character.
            if "level" in changed:
                after["level"] = max(1, min(int(rules.get("level_max", 10) or 10), int(after.get("level", 1) or 1)))
            if "stats" in changed:
                after["stats"] = {k:int((after.get("stats") or {}).get(k,0) or 0) for k in ("str","dex","con","int","wis","cha")}
                validate_stat_bounds(after, rules, allow_unassigned_zero=not bool(after.get("stats_initialized")))
            after["damage_die"] = _validate_damage_die(after.get("damage_die") or classes.get(after.get("class_name"), {}).get("damage") or "D6")
            after["damage_bonus"] = int(after.get("damage_bonus", 0) or 0)
            after["armor_base"] = int(after.get("armor_base", 0) or 0)
            after["armor"] = int(after.get("armor", 0) or 0)
            after["bonus_stat_points"] = max(0, int(after.get("bonus_stat_points", 0) or 0))

        if "reserve" in changed:
            reserve = max(0, int(after.get("reserve", 0) or 0))
            reserve_max = max(0, int(rules.get("reserve_max", 0) or 0))
            after["reserve"] = min(reserve, reserve_max) if reserve_max > 0 else reserve
        if actor["role"] == "gm" and "extension_state" in changed:
            # GM은 행동 선행조건은 우회할 수 있지만 개인 자원의 숫자/상한은 동일하게 정규화한다.
            normalize_extension_resource_values(con, character_id, after, strict=False)

        # CON or class-base HP changes adjust current HP by exactly the max-HP
        # delta. They never fully heal the character.
        if ("stats" in changed or "class_name" in changed) and "hp_current" not in changed:
            delta = _max_hp_for(after, classes) - _max_hp_for(before, classes)
            after["hp_current"] = int(before.get("hp_current", 0) or 0) + delta
        if "hp_current" in changed or "stats" in changed or "class_name" in changed:
            after["hp_current"] = max(0, min(_max_hp_for(after, classes), int(after.get("hp_current", 0) or 0)))
        after = normalize_character_state(after, classes)
        # Structured move choices change persistent sheet identity (chosen spells,
        # cross-class moves, class access). Validate their source on the server so
        # language/UI changes cannot alter mechanics and special unclassified spells
        # remain GM-only. Stale legacy choices are pruned when unrelated fields change;
        # an explicit move-choice patch is rejected if it tries to forge an invalid one.
        if changed & {"extra_spells", "class_name", "race_name"}:
            validate_extra_spell_choices(con, room["id"], after, before, strict=("extra_spells" in changed))
        validate_move_choices(con, room["id"], after, classes, strict=("move_choices" in changed))
        spell_fields = {"spellbook", "prepared_spells", "starting_spells_complete", "spell_tracks"}
        validate_spellcasting_state(
            con,
            room["id"],
            after,
            classes,
            enforce_limits=(actor["role"] != "gm"),
            strict=(actor["role"] != "gm" and bool(changed & spell_fields)),
        )
        con.execute("UPDATE characters SET state_json=?,updated_at=? WHERE id=?", (jdump(after), now_iso(), character_id))
        detail = {"changed_keys": list(body.patch.keys()), "before": {k: before.get(k) for k in body.patch}, "after": {k: after.get(k) for k in body.patch}}
        log_event(con, room["id"], actor, "캐릭터 수정", f"character:{character_id}", detail)
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "character"})
    return {"ok": True}


@app.put("/api/rooms/{code}/campaign")
async def rename_campaign(code: str, body: CampaignIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        before = room["campaign_name"]
        con.execute("UPDATE rooms SET campaign_name=?,updated_at=? WHERE id=?", (body.name.strip(), now_iso(), room["id"]))
        log_event(con, room["id"], actor, "캠페인 이름 변경", body.name.strip(), {"before": before, "after": body.name.strip()})
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "campaign"})
    return {"ok": True}


@app.delete("/api/rooms/{code}")
async def delete_campaign(code: str, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        con.execute("DELETE FROM rooms WHERE id=?", (room["id"],))
    if get_active_campaign_code() == code.upper():
        set_active_campaign_code("")
    dice_preparations.pop(code.upper(), None)
    sound_states.pop(code.upper(), None)
    shutil.rmtree(SOUND_DIR / code.upper(), ignore_errors=True)
    await manager.broadcast(code.upper(), {"type": "deleted", "room": code.upper()})
    return {"ok": True}


def _finish_host_shutdown() -> None:
    """Stop through the launcher when available so its watchdog will not restart us.

    Development runs may not have a launcher; in that case we fall back to terminating
    the uvicorn process directly after the browser has received the response.
    """
    launcher = os.environ.get("DW_LAUNCHER_BASE", "").strip().rstrip("/")
    if launcher:
        try:
            req = urllib.request.Request(launcher + "/api/stop", data=b"{}", method="POST", headers={"Content-Type":"application/json"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                resp.read(64)
            return
        except Exception:
            pass
    os._exit(0)


@app.post("/api/rooms/{code}/server-stop")
async def stop_host_server(code: str, authorization: str | None = Header(default=None)):
    # GM 인증 자체가 서버 종료 권한이다. GM이 LAN/VPN 주소로 호스트 화면을
    # 열어도 request.client가 127.0.0.1이 아니므로 막히던 v0.5 제한을 제거했다.
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm":
            raise HTTPException(403, "GM 권한이 필요합니다.")
        touch_room(con, room["id"])
    await manager.broadcast(code.upper(), {"type": "server_stopping", "room": code.upper()})
    # Let the launcher mark this as an intentional stop before the Python process exits.
    # Otherwise its watchdog correctly interprets the exit as a crash and restarts it.
    threading.Timer(0.45, _finish_host_shutdown).start()
    return {"ok": True}


@app.post("/api/local/server-stop")
async def local_stop_host_server(request: Request):
    """Graceful stop endpoint for the Windows launcher on the host PC."""
    require_local_request(request)
    for room_code in list(manager.rooms.keys()):
        await manager.broadcast(room_code, {"type": "server_stopping", "room": room_code})
    threading.Timer(0.9, lambda: os._exit(0)).start()
    return {"ok": True}


@app.post("/api/rooms/{code}/sessions/start")
async def start_session(code: str, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        if active_session(con, room["id"]): raise HTTPException(400, "이미 진행 중인 세션이 있습니다.")
        no = int(con.execute("SELECT COALESCE(MAX(session_no),0)+1 n FROM sessions WHERE room_id=?", (room["id"],)).fetchone()["n"])
        cur = con.execute("INSERT INTO sessions(room_id,session_no,started_at) VALUES(?,?,?)", (room["id"], no, now_iso()))
        log_event(con, room["id"], actor, "세션 시작", f"session:{no}")
        sid = int(cur.lastrowid)
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "session"})
    return {"ok": True, "session_id": sid, "session_no": no}


@app.post("/api/rooms/{code}/sessions/{session_id}/end")
async def end_session(code: str, session_id: int, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        sess = con.execute("SELECT * FROM sessions WHERE id=? AND room_id=?", (session_id, room["id"])).fetchone()
        if not sess or sess["ended_at"]: raise HTTPException(404, "진행 중인 세션을 찾을 수 없습니다.")
        log_event(con, room["id"], actor, "세션 종료", f"session:{sess['session_no']}")
        con.execute("UPDATE sessions SET ended_at=? WHERE id=?", (now_iso(), session_id))
        touch_room(con, room["id"])
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "session"})
    return {"ok": True}


@app.put("/api/rooms/{code}/rules")
async def update_rules(code: str, body: RulesIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        old = normalize_rules(jload(room["rules_json"], {}) or {})
        new = normalize_rules({**old, **body.rules})
        if new["stat_min"] > new["stat_max"]: raise HTTPException(400, "능력치 최소값이 최대값보다 클 수 없습니다.")
        if any(int(x) < int(new["stat_min"]) or int(x) > int(new["stat_max"]) for x in new.get("stat_start", [])):
            raise HTTPException(400, "초기 능력치 배분 값은 능력치 최소~최대 범위 안에 있어야 합니다.")
        highest_level = 1
        classes_for_rules = class_map(con, room["id"])
        for crow in con.execute("SELECT id,state_json FROM characters WHERE room_id=?", (room["id"],)):
            raw_state = jload(crow["state_json"], {}) or {}
            try:
                highest_level = max(highest_level, int(raw_state.get("level", 1) or 1))
            except (TypeError, ValueError):
                pass
            st = normalize_character_state(raw_state, classes_for_rules)
            if st.get("stats_initialized"):
                try:
                    validate_stat_bounds(st, new)
                except HTTPException:
                    raise HTTPException(400, "현재 캐릭터 능력치가 새 최소/최대 범위를 벗어납니다. 먼저 캐릭터 능력치를 조정해주세요.")
        expansion_limit = int(new.get("max_expansions_per_character", 0) or 0)
        if expansion_limit > 0:
            over = con.execute("SELECT character_id,COUNT(*) n FROM expansion_grants WHERE room_id=? AND status IN ('pending','accepted') GROUP BY character_id HAVING COUNT(*)>? LIMIT 1", (room["id"], expansion_limit)).fetchone()
            if over:
                raise HTTPException(400, "현재 보유/대기 중인 확장직업 수보다 낮은 최대값으로 줄일 수 없습니다.")
        if int(new.get("level_max", 10) or 10) < highest_level:
            raise HTTPException(400, f"최대 레벨을 {highest_level}보다 낮출 수 없습니다. 먼저 높은 레벨의 캐릭터를 조정해주세요.")
        con.execute("UPDATE rooms SET rules_json=?,updated_at=? WHERE id=?", (jdump(new), now_iso(), room["id"]))
        # 공용 예비 상한을 낮추면 현재값도 새 상한을 넘지 않도록 맞춘다. 0은 제한 없음.
        reserve_max = int(new.get("reserve_max", 0) or 0)
        if reserve_max > 0:
            classes = class_map(con, room["id"])
            for crow in con.execute("SELECT id,state_json FROM characters WHERE room_id=?", (room["id"],)):
                st = normalize_character_state(jload(crow["state_json"], {}) or {}, classes)
                if int(st.get("reserve", 0) or 0) > reserve_max:
                    st["reserve"] = reserve_max
                    con.execute("UPDATE characters SET state_json=?,updated_at=? WHERE id=?", (jdump(st), now_iso(), crow["id"]))
        # 태그 카탈로그에서 제거한 값은 기존 몬스터 카드에서도 정리한다.
        for m in con.execute("SELECT id,data_json FROM monster_defs WHERE room_id=?", (room["id"],)):
            cleaned = normalize_monster_data(jload(m["data_json"], {}) or {}, new.get("monster_tags", []))
            con.execute("UPDATE monster_defs SET data_json=?,updated_at=? WHERE id=?", (jdump(cleaned), now_iso(), m["id"]))
        log_event(con, room["id"], actor, "규칙 수정", "room_rules", compact_change_detail(old, new))
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "rules"})
    return {"ok": True}


@app.put("/api/rooms/{code}/settings")
async def update_settings(code: str, body: SettingsIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        old = normalize_settings(jload(room["settings_json"], {}) or {})
        new = normalize_settings({**old, **body.settings})
        con.execute("UPDATE rooms SET settings_json=?,updated_at=? WHERE id=?", (jdump(new), now_iso(), room["id"]))
        log_event(con, room["id"], actor, "설정 수정", "room_settings", compact_change_detail(old, new))
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "settings"})
    return {"ok": True, "settings": new}


@app.put("/api/rooms/{code}/npcs")
async def save_npc(code: str, body: NPCIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        data = normalize_npc_data(body.data)
        favorite = 1 if data.get("favorite") else 0
        now = now_iso()
        if body.id:
            row = con.execute("SELECT * FROM npc_defs WHERE id=? AND room_id=?", (body.id, room["id"])).fetchone()
            if not row: raise HTTPException(404, "NPC를 찾을 수 없습니다.")
            con.execute("UPDATE npc_defs SET name=?,data_json=?,favorite=?,updated_at=? WHERE id=?", (body.name.strip(), jdump(data), favorite, now, body.id))
            npc_id = int(body.id); action = "NPC 수정"
        else:
            order = int(con.execute("SELECT COALESCE(MAX(sort_order),0)+1 n FROM npc_defs WHERE room_id=?", (room["id"],)).fetchone()["n"])
            cur = con.execute("INSERT INTO npc_defs(room_id,name,data_json,sort_order,favorite,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", (room["id"], body.name.strip(), jdump(data), order, favorite, now, now))
            npc_id = int(cur.lastrowid); action = "NPC 생성"
        log_event(con, room["id"], actor, action, body.name.strip(), {"id": npc_id})
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "npc"})
    return {"ok": True, "id": npc_id}


@app.delete("/api/rooms/{code}/npcs/{npc_id}")
async def delete_npc(code: str, npc_id: int, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        row = con.execute("SELECT * FROM npc_defs WHERE id=? AND room_id=?", (npc_id, room["id"])).fetchone()
        if not row: raise HTTPException(404, "NPC를 찾을 수 없습니다.")
        con.execute("DELETE FROM npc_defs WHERE id=?", (npc_id,))
        log_event(con, room["id"], actor, "NPC 삭제", row["name"], {"id": npc_id})
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "npc"})
    return {"ok": True}


@app.post("/api/rooms/{code}/monster-folders")
async def create_monster_folder(code: str, body: MonsterFolderIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        try:
            order = int(con.execute("SELECT COALESCE(MAX(sort_order),0)+1 n FROM monster_folders WHERE room_id=?", (room["id"],)).fetchone()["n"])
            cur = con.execute("INSERT INTO monster_folders(room_id,name,sort_order,created_at) VALUES(?,?,?,?)", (room["id"], body.name.strip(), order, now_iso()))
        except sqlite3.IntegrityError:
            raise HTTPException(400, "같은 이름의 몬스터 폴더가 이미 있습니다.")
        fid = int(cur.lastrowid)
        log_event(con, room["id"], actor, "몬스터 폴더 생성", body.name.strip(), {"id": fid})
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "monster_folder"})
    return {"ok": True, "id": fid}


@app.put("/api/rooms/{code}/monster-folders/{folder_id}")
async def rename_monster_folder(code: str, folder_id: int, body: MonsterFolderIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        row = con.execute("SELECT * FROM monster_folders WHERE id=? AND room_id=?", (folder_id, room["id"])).fetchone()
        if not row: raise HTTPException(404, "몬스터 폴더를 찾을 수 없습니다.")
        try:
            con.execute("UPDATE monster_folders SET name=? WHERE id=?", (body.name.strip(), folder_id))
        except sqlite3.IntegrityError:
            raise HTTPException(400, "같은 이름의 몬스터 폴더가 이미 있습니다.")
        log_event(con, room["id"], actor, "몬스터 폴더 수정", body.name.strip(), {"id": folder_id, "before": row["name"]})
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "monster_folder"})
    return {"ok": True}


@app.delete("/api/rooms/{code}/monster-folders/{folder_id}")
async def delete_monster_folder(code: str, folder_id: int, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        row = con.execute("SELECT * FROM monster_folders WHERE id=? AND room_id=?", (folder_id, room["id"])).fetchone()
        if not row: raise HTTPException(404, "몬스터 폴더를 찾을 수 없습니다.")
        con.execute("DELETE FROM monster_folders WHERE id=?", (folder_id,))
        log_event(con, room["id"], actor, "몬스터 폴더 삭제", row["name"], {"id": folder_id})
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "monster_folder"})
    return {"ok": True}


@app.put("/api/rooms/{code}/monsters")
async def save_monster(code: str, body: MonsterIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        if body.folder_id is not None and not con.execute("SELECT 1 FROM monster_folders WHERE id=? AND room_id=?", (body.folder_id, room["id"])).fetchone():
            raise HTTPException(400, "선택한 몬스터 폴더가 존재하지 않습니다.")
        rules = normalize_rules(jload(room["rules_json"], {}) or {})
        data = normalize_monster_data(body.data, rules.get("monster_tags", []))
        now = now_iso()
        if body.id:
            row = con.execute("SELECT * FROM monster_defs WHERE id=? AND room_id=?", (body.id, room["id"])).fetchone()
            if not row: raise HTTPException(404, "몬스터를 찾을 수 없습니다.")
            con.execute("UPDATE monster_defs SET folder_id=?,name=?,data_json=?,updated_at=? WHERE id=?", (body.folder_id, body.name.strip(), jdump(data), now, body.id))
            mid = int(body.id); action = "몬스터 수정"
        else:
            order = int(con.execute("SELECT COALESCE(MAX(sort_order),0)+1 n FROM monster_defs WHERE room_id=? AND folder_id IS ?", (room["id"], body.folder_id)).fetchone()["n"])
            cur = con.execute("INSERT INTO monster_defs(room_id,folder_id,name,data_json,sort_order,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", (room["id"], body.folder_id, body.name.strip(), jdump(data), order, now, now))
            mid = int(cur.lastrowid); action = "몬스터 생성"
        log_event(con, room["id"], actor, action, body.name.strip(), {"id": mid, "folder_id": body.folder_id})
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "monster"})
    return {"ok": True, "id": mid}


@app.delete("/api/rooms/{code}/monsters/{monster_id}")
async def delete_monster(code: str, monster_id: int, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        row = con.execute("SELECT * FROM monster_defs WHERE id=? AND room_id=?", (monster_id, room["id"])).fetchone()
        if not row: raise HTTPException(404, "몬스터를 찾을 수 없습니다.")
        con.execute("DELETE FROM monster_defs WHERE id=?", (monster_id,))
        log_event(con, room["id"], actor, "몬스터 삭제", row["name"], {"id": monster_id})
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "monster"})
    return {"ok": True}


@app.post("/api/rooms/{code}/monsters/{monster_id}/appear")
async def monster_appear(code: str, monster_id: int, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        row = con.execute("SELECT id,name FROM monster_defs WHERE id=? AND room_id=?", (monster_id, room["id"])).fetchone()
        if not row: raise HTTPException(404, "몬스터를 찾을 수 없습니다.")
        now = now_iso()
        cur = con.execute("SELECT id FROM monster_catalog WHERE room_id=? AND monster_id=?", (room["id"], monster_id)).fetchone()
        if not cur:
            con.execute("INSERT INTO monster_catalog(room_id,monster_id,reveal_json,created_at,updated_at) VALUES(?,?,?,?,?)", (room["id"], monster_id, jdump({}), now, now))
            log_event(con, room["id"], actor, "몬스터 출현", row["name"], {"monster_id": monster_id})
    await manager.broadcast(code.upper(), {"type":"refresh","reason":"monster_catalog"})
    return {"ok": True}


@app.put("/api/rooms/{code}/monsters/{monster_id}/catalog")
async def monster_catalog_update(code: str, monster_id: int, body: MonsterCatalogIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    allowed = {"name","hp","armor","attack","damage","range","tags","instinct","special","moves","description"}
    clean = {k: bool(v) for k,v in dict(body.reveal or {}).items() if k in allowed}
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        if not con.execute("SELECT 1 FROM monster_defs WHERE id=? AND room_id=?", (monster_id, room["id"])).fetchone(): raise HTTPException(404, "몬스터를 찾을 수 없습니다.")
        now=now_iso()
        con.execute("INSERT INTO monster_catalog(room_id,monster_id,reveal_json,created_at,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(room_id,monster_id) DO UPDATE SET reveal_json=excluded.reveal_json,updated_at=excluded.updated_at", (room["id"], monster_id, jdump(clean), now, now))
    await manager.broadcast(code.upper(), {"type":"refresh","reason":"monster_catalog"})
    return {"ok": True}


@app.delete("/api/rooms/{code}/monsters/{monster_id}/catalog")
async def monster_catalog_remove(code: str, monster_id: int, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        con.execute("DELETE FROM monster_catalog WHERE room_id=? AND monster_id=?", (room["id"], monster_id))
    await manager.broadcast(code.upper(), {"type":"refresh","reason":"monster_catalog"})
    return {"ok": True}


@app.put("/api/rooms/{code}/classes")
async def save_class(code: str, body: ClassDefIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization); name = body.name.strip()
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        lookup_name = (body.old_name or name).strip()
        oldrow = con.execute("SELECT data_json FROM class_defs WHERE room_id=? AND name=?", (room["id"], lookup_name)).fetchone()
        old = jload(oldrow["data_json"], None) if oldrow else None
        is_new = oldrow is None
        old_base_hp = max(1, int((old or {}).get("hp", body.data.get("hp", 6)) or 1))
        if body.old_name and lookup_name != name:
            if not oldrow: raise HTTPException(404, "이름을 바꿀 기존 직업을 찾을 수 없습니다.")
            if con.execute("SELECT 1 FROM class_defs WHERE room_id=? AND name=?", (room["id"], name)).fetchone(): raise HTTPException(400, "변경하려는 직업명이 이미 존재합니다.")
        requested_damage = _validate_damage_die((body.data or {}).get("damage", "D6"))
        d = normalize_class_data(dict(body.data)); d["hp"] = max(1, int(d.get("hp", 6))); d["load"] = max(0, int(d.get("load", 8))); d["damage"] = requested_damage
        for key in ("alignments", "bonds", "start", "a25", "a610"): d.setdefault(key, [])
        # 종족 연결/설명은 v0.6부터 race_defs가 단일 원본이다. 직업 편집기에서
        # 넘어온 races 값은 신뢰하지 않고 아래에서 race_defs를 기준으로 재생성한다.
        d["races"] = []
        d.setdefault("gear", "")
        if body.old_name and lookup_name != name:
            con.execute("UPDATE class_defs SET name=?,data_json=? WHERE room_id=? AND name=?", (name, jdump(d), room["id"], lookup_name))
            con.execute("UPDATE spell_defs SET class_name=? WHERE room_id=? AND class_name=?", (name, room["id"], lookup_name))
            # 종족 원본의 직업별 설명/사용 가능 설정도 새 직업명으로 함께 이동한다.
            for rr in con.execute("SELECT id,data_json FROM race_defs WHERE room_id=?", (room["id"],)):
                rd = normalize_race_data(jload(rr["data_json"], {}))
                per = dict(rd.get("per_class") or {})
                if lookup_name in per:
                    per[name] = per.pop(lookup_name)
                enabled = [name if x == lookup_name else x for x in (rd.get("enabled_classes") or [])]
                effects = dict(rd.get("spell_effects") or {})
                if lookup_name in effects:
                    effects[name] = effects.pop(lookup_name)
                for rows in effects.values():
                    for rule in rows:
                        if isinstance(rule, dict) and rule.get("kind") == "cross_class_access" and rule.get("source_class") == lookup_name:
                            rule["source_class"] = name
                rd["per_class"] = per; rd["enabled_classes"] = list(dict.fromkeys(enabled)); rd["spell_effects"] = effects
                rd = normalize_race_data(rd)
                con.execute("UPDATE race_defs SET data_json=? WHERE id=?", (jdump(rd), rr["id"]))
            # Structured class-move effects may refer to the renamed class as a
            # cross-class source. Rewrite those stable references together with
            # spell/race/character references.
            for cr in con.execute("SELECT id,data_json FROM class_defs WHERE room_id=?", (room["id"],)):
                cd = normalize_class_data(jload(cr["data_json"], {}) or {})
                changed_cd = False
                for section in ("start", "a25", "a610"):
                    for move in cd.get(section, []) or []:
                        for effect in move.get("move_effects", []) or []:
                            if isinstance(effect, dict) and effect.get("source_class") == lookup_name:
                                effect["source_class"] = name
                                changed_cd = True
                if changed_cd:
                    con.execute("UPDATE class_defs SET data_json=? WHERE id=?", (jdump(cd), cr["id"]))
            for crow in con.execute("SELECT id,state_json FROM characters WHERE room_id=?", (room["id"],)):
                st = normalize_character_state(jload(crow["state_json"], {}), class_map(con, room["id"]))
                changed = False
                if st.get("class_name") == lookup_name:
                    delta_hp = int(d.get("hp", old_base_hp)) - old_base_hp
                    st["class_name"] = name
                    if delta_hp:
                        st["hp_current"] = max(0, min(_max_hp_for(st, class_map(con, room["id"])), int(st.get("hp_current", 0) or 0) + delta_hp))
                    changed = True
                for em in st.get("extra_moves", []):
                    if em.get("source_class") == lookup_name: em["source_class"] = name; changed = True
                for choice in (st.get("move_choices") or {}).values():
                    if isinstance(choice, dict) and choice.get("source_class") == lookup_name:
                        choice["source_class"] = name; changed = True
                for extra_spell in st.get("extra_spells", []) or []:
                    if isinstance(extra_spell, dict) and extra_spell.get("source") == lookup_name:
                        extra_spell["source"] = name; changed = True
                if changed: con.execute("UPDATE characters SET state_json=?,updated_at=? WHERE id=?", (jdump(st), now_iso(), crow["id"]))
            action = "직업 이름 변경"
        else:
            con.execute("INSERT INTO class_defs(room_id,name,data_json) VALUES(?,?,?) ON CONFLICT(room_id,name) DO UPDATE SET data_json=excluded.data_json", (room["id"], name, jdump(d)))
            if old:
                delta_hp = int(d.get("hp", old_base_hp)) - old_base_hp
                if delta_hp:
                    classes_after = class_map(con, room["id"])
                    for crow in con.execute("SELECT id,state_json FROM characters WHERE room_id=?", (room["id"],)):
                        raw_state = jload(crow["state_json"], {}) or {}
                        if raw_state.get("class_name") != name:
                            continue
                        st = normalize_character_state(raw_state, classes_after)
                        st["hp_current"] = max(0, min(_max_hp_for(st, classes_after), int(st.get("hp_current", 0) or 0) + delta_hp))
                        con.execute("UPDATE characters SET state_json=?,updated_at=? WHERE id=?", (jdump(st), now_iso(), crow["id"]))
            action = "직업 저장" if old else "직업 추가"
            if is_new:
                # 새 직업은 모든 종족 편집 화면에 즉시 빈 설명 슬롯이 생기도록
                # per_class 키를 준비한다. 사용 가능 여부는 종족 화면의 체크로 결정한다.
                for rr in con.execute("SELECT id,data_json FROM race_defs WHERE room_id=?", (room["id"],)):
                    rd = normalize_race_data(jload(rr["data_json"], {}))
                    per = dict(rd.get("per_class") or {}); per.setdefault(name, "")
                    rd["per_class"] = per
                    con.execute("UPDATE race_defs SET data_json=? WHERE id=?", (jdump(rd), rr["id"]))
        # Keep character selections consistent with the edited class definition.
        # Deleted/renamed moves must not remain hidden in state while still consuming points.
        classes_after = class_map(con, room["id"])
        current_class = classes_after.get(name, d)
        valid_primary = {str(m.get("name", "")) for section in ("a25", "a610") for m in (current_class.get(section) or []) if isinstance(m, dict) and str(m.get("name", ""))}
        if current_class.get("multiclass_25"):
            valid_primary.add("다중직업(초급)")
        if current_class.get("multiclass_610"):
            valid_primary.add("다중직업(중급)")
        all_source_names = _class_move_option_names(current_class, 999)
        for crow in con.execute("SELECT id,state_json FROM characters WHERE room_id=?", (room["id"],)):
            st = normalize_character_state(jload(crow["state_json"], {}) or {}, classes_after)
            changed_st = False
            if st.get("class_name") == name:
                pruned = [x for x in (st.get("advanced_moves") or []) if x in valid_primary]
                if pruned != list(st.get("advanced_moves") or []):
                    st["advanced_moves"] = pruned; changed_st = True
            pruned_extra = [x for x in (st.get("extra_moves") or []) if not (isinstance(x, dict) and x.get("source_class") == name and x.get("name") not in all_source_names)]
            if pruned_extra != list(st.get("extra_moves") or []):
                st["extra_moves"] = pruned_extra; changed_st = True
            if changed_st:
                validate_move_choices(con, room["id"], st, classes_after, strict=False)
                validate_spellcasting_state(con, room["id"], st, classes_after, enforce_limits=False, strict=False)
                con.execute("UPDATE characters SET state_json=?,updated_at=? WHERE id=?", (jdump(normalize_character_state(st, classes_after)), now_iso(), crow["id"]))
        log_event(con, room["id"], actor, action, name, compact_change_detail(old or {}, d, extra={"old_name": lookup_name}))
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "class"}); return {"ok": True}


@app.delete("/api/rooms/{code}/classes/{class_name}")
async def delete_class(code: str, class_name: str, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        row = con.execute("SELECT * FROM class_defs WHERE room_id=? AND name=?", (room["id"], class_name)).fetchone()
        if not row: raise HTTPException(404, "직업을 찾을 수 없습니다.")
        for crow in con.execute("SELECT state_json FROM characters WHERE room_id=?", (room["id"],)):
            st = jload(crow["state_json"], {})
            if st.get("class_name") == class_name: raise HTTPException(400, "현재 사용 중인 직업은 삭제할 수 없습니다.")
            if any(x.get("source_class") == class_name for x in st.get("extra_moves", []) or []): raise HTTPException(400, "추가 행동의 출처로 사용 중인 직업은 삭제할 수 없습니다.")
        for rr in con.execute("SELECT id,data_json FROM race_defs WHERE room_id=?", (room["id"],)):
            rd = normalize_race_data(jload(rr["data_json"], {}))
            if any(rule.get("kind") == "cross_class_access" and rule.get("source_class") == class_name for rows in (rd.get("spell_effects") or {}).values() for rule in rows if isinstance(rule, dict)):
                raise HTTPException(400, "종족의 다른 직업 주문 습득 설정에서 출처로 사용 중인 직업은 삭제할 수 없습니다.")
        for cr in con.execute("SELECT data_json FROM class_defs WHERE room_id=?", (room["id"],)):
            cd = normalize_class_data(jload(cr["data_json"], {}) or {})
            for section in ("start", "a25", "a610"):
                for move in cd.get(section, []) or []:
                    if any(isinstance(e, dict) and e.get("source_class") == class_name for e in (move.get("move_effects") or [])):
                        raise HTTPException(400, "다른 행동의 타직업 획득 설정에서 출처로 사용 중인 직업은 삭제할 수 없습니다.")
        con.execute("DELETE FROM spell_defs WHERE room_id=? AND class_name=?", (room["id"], class_name)); con.execute("DELETE FROM class_defs WHERE id=?", (row["id"],))
        for rr in con.execute("SELECT id,data_json FROM race_defs WHERE room_id=?", (room["id"],)):
            rd = normalize_race_data(jload(rr["data_json"], {})); per = dict(rd.get("per_class") or {})
            per.pop(class_name, None)
            rd["per_class"] = per
            rd["enabled_classes"] = [x for x in (rd.get("enabled_classes") or []) if x != class_name]
            effects = dict(rd.get("spell_effects") or {}); effects.pop(class_name, None); rd["spell_effects"] = effects
            rd = normalize_race_data(rd)
            con.execute("UPDATE race_defs SET data_json=? WHERE id=?", (jdump(rd), rr["id"]))
        log_event(con, room["id"], actor, "직업 삭제", class_name, {})
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "class"}); return {"ok": True}


class CoreMoveIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    desc: str = ""
    old_name: str | None = None


@app.put("/api/rooms/{code}/races")
async def save_race(code: str, body: RaceDefIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        name = body.name.strip(); old = body.old_name.strip() if body.old_name else name
        data = normalize_race_data(dict(body.data or {})); data["name"] = name
        class_names = {x["name"] for x in con.execute("SELECT name FROM class_defs WHERE room_id=?", (room["id"],))}
        per = {k: str(v or "") for k, v in (data.get("per_class") or {}).items() if k in class_names}
        for cname in class_names: per.setdefault(cname, "")
        enabled = [x for x in (data.get("enabled_classes") or []) if x in class_names]
        effects: dict[str, list[dict[str, Any]]] = {}
        for cname, rows in (data.get("spell_effects") or {}).items():
            if cname not in class_names: continue
            clean_rows=[]
            for raw in list(rows or [])[:30]:
                if not isinstance(raw, dict): continue
                kind=str(raw.get("kind", "")); legacy_disabled=raw.get("enabled", True) is False
                if legacy_disabled:
                    continue
                if kind == "cross_class_access":
                    src=str(raw.get("source_class", "")).strip()
                    if src not in class_names or src == cname: continue
                    clean_rows.append({"kind": kind, "source_class": src, "count": max(1,min(9,int(raw.get("count",1) or 1)))})
                    continue
                sid=max(0,int(raw.get("spell_id",0) or 0))
                if kind == "level_reduce":
                    sp=con.execute("SELECT id FROM spell_defs WHERE id=? AND room_id=? AND class_name=?", (sid, room["id"], cname)).fetchone()
                    if not sp: continue
                    clean_rows.append({"kind": kind, "spell_id": sid, "amount": max(1,min(99,int(raw.get("amount",1) or 1)))})
                elif kind == "grant_unclassified":
                    sp=con.execute("SELECT id FROM spell_defs WHERE id=? AND room_id=? AND class_name='__undefined__'", (sid, room["id"])).fetchone()
                    if not sp: continue
                    clean_rows.append({"kind": kind, "spell_id": sid})
            effects[cname]=clean_rows
        data.update({"per_class": per, "enabled_classes": list(dict.fromkeys(enabled)), "spell_effects": effects})
        data = normalize_race_data(data)
        existing = con.execute("SELECT * FROM race_defs WHERE room_id=? AND name=?", (room["id"], old)).fetchone()
        if old != name and con.execute("SELECT 1 FROM race_defs WHERE room_id=? AND name=?", (room["id"], name)).fetchone():
            raise HTTPException(400, "변경하려는 종족명이 이미 존재합니다.")
        if existing:
            con.execute("UPDATE race_defs SET name=?,data_json=? WHERE id=?", (name, jdump(data), existing["id"]))
        else:
            order = int(con.execute("SELECT COALESCE(MAX(sort_order),0)+1 n FROM race_defs WHERE room_id=?", (room["id"],)).fetchone()["n"])
            con.execute("INSERT INTO race_defs(room_id,name,data_json,sort_order) VALUES(?,?,?,?)", (room["id"], name, jdump(data), order))
        if old != name:
            classes = class_map(con, room["id"])
            for cr in con.execute("SELECT id,data_json FROM class_defs WHERE room_id=?", (room["id"],)):
                cd = normalize_class_data(jload(cr["data_json"], {}) or {})
                changed_cd = False
                for section in ("start", "a25", "a610"):
                    for move in cd.get(section, []) or []:
                        for effect in move.get("move_effects", []) or []:
                            if isinstance(effect, dict) and effect.get("kind") == "opposite_race_feature" and old in (effect.get("race_pair") or []):
                                effect["race_pair"] = [name if x == old else x for x in (effect.get("race_pair") or [])]
                                changed_cd = True
                if changed_cd:
                    con.execute("UPDATE class_defs SET data_json=? WHERE id=?", (jdump(normalize_class_data(cd)), cr["id"]))
            for crow in con.execute("SELECT id,state_json FROM characters WHERE room_id=?", (room["id"],)):
                st = normalize_character_state(jload(crow["state_json"], {}) or {}, classes)
                changed_st = False
                if st.get("race_name") == old:
                    st["race_name"] = name; changed_st = True
                for extra_spell in st.get("extra_spells", []) or []:
                    if isinstance(extra_spell, dict) and extra_spell.get("source_name") == old:
                        extra_spell["source_name"] = name; changed_st = True
                if changed_st:
                    con.execute("UPDATE characters SET state_json=?,updated_at=? WHERE id=?", (jdump(st), now_iso(), crow["id"]))
        log_event(con, room["id"], actor, "종족 저장", name, {"old_name": old, "enabled_classes": enabled, "spell_effects": sum(len(x) for x in effects.values())})
    await manager.broadcast(code.upper(), {"type":"refresh","reason":"race"}); return {"ok":True}


@app.delete("/api/rooms/{code}/races/{race_name}")
async def delete_race(code: str, race_name: str, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        row = con.execute("SELECT * FROM race_defs WHERE room_id=? AND name=?", (room["id"], race_name)).fetchone()
        if not row: raise HTTPException(404, "종족을 찾을 수 없습니다.")
        for crow in con.execute("SELECT state_json FROM characters WHERE room_id=?", (room["id"],)):
            if (jload(crow["state_json"], {}) or {}).get("race_name") == race_name:
                raise HTTPException(400, "현재 캐릭터가 사용 중인 종족은 삭제할 수 없습니다. 먼저 GM이 캐릭터의 종족을 변경해주세요.")
        for cr in con.execute("SELECT data_json FROM class_defs WHERE room_id=?", (room["id"],)):
            cd = normalize_class_data(jload(cr["data_json"], {}) or {})
            for section in ("start", "a25", "a610"):
                for move in cd.get(section, []) or []:
                    for effect in move.get("move_effects", []) or []:
                        if isinstance(effect, dict) and effect.get("kind") == "opposite_race_feature" and race_name in (effect.get("race_pair") or []):
                            raise HTTPException(400, "다른 종족 특성 함께 사용 효과에서 참조 중인 종족은 삭제할 수 없습니다.")
        con.execute("DELETE FROM race_defs WHERE id=?", (row["id"],))
        log_event(con, room["id"], actor, "종족 삭제", race_name, {})
    await manager.broadcast(code.upper(), {"type":"refresh","reason":"race"}); return {"ok":True}


@app.put("/api/rooms/{code}/core-move")
async def save_core_move(code: str, body: CoreMoveIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization); name = body.name.strip()
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        old_name = (body.old_name or name).strip(); old = con.execute("SELECT * FROM core_moves WHERE room_id=? AND name=?", (room["id"], old_name)).fetchone(); item = {"name": name, "desc": body.desc}
        if old and old_name != name:
            if con.execute("SELECT 1 FROM core_moves WHERE room_id=? AND name=?", (room["id"], name)).fetchone(): raise HTTPException(400, "같은 이름의 핵심 행동이 이미 있습니다.")
            con.execute("UPDATE core_moves SET name=?,data_json=? WHERE id=?", (name, jdump(item), old["id"]))
        else:
            con.execute("INSERT INTO core_moves(room_id,name,data_json) VALUES(?,?,?) ON CONFLICT(room_id,name) DO UPDATE SET data_json=excluded.data_json", (room["id"], name, jdump(item)))
        log_event(con, room["id"], actor, "핵심 행동 저장", name, compact_change_detail(jload(old["data_json"], {}) if old else {}, item))
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "core_move"}); return {"ok": True}


@app.delete("/api/rooms/{code}/core-move/{move_name}")
async def delete_core_move(code: str, move_name: str, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        row = con.execute("SELECT * FROM core_moves WHERE room_id=? AND name=?", (room["id"], move_name)).fetchone()
        if not row: raise HTTPException(404, "행동을 찾을 수 없습니다.")
        con.execute("DELETE FROM core_moves WHERE id=?", (row["id"],)); log_event(con, room["id"], actor, "핵심 행동 삭제", move_name, {})
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "core_move"}); return {"ok": True}


@app.put("/api/rooms/{code}/spell")
async def save_spell(code: str, body: SpellIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        if body.class_name != "__undefined__" and not con.execute("SELECT 1 FROM class_defs WHERE room_id=? AND name=?", (room["id"], body.class_name)).fetchone(): raise HTTPException(400, "존재하지 않는 직업입니다.")
        level = normalize_spell_level(body.level)
        item = {"name": body.name.strip(), "level": level, "desc": body.desc}
        if body.id:
            old = con.execute("SELECT * FROM spell_defs WHERE id=? AND room_id=?", (body.id, room["id"])).fetchone()
            if not old: raise HTTPException(404, "주문을 찾을 수 없습니다.")
            old_name, old_class = old["name"], old["class_name"]
            con.execute("UPDATE spell_defs SET class_name=?,name=?,level=?,data_json=? WHERE id=?", (body.class_name, item["name"], level, jdump(item), body.id)); before = jload(old["data_json"], {})
            if old_class != body.class_name:
                # A race effect is scoped to the spell's old class (or to the unclassified pool).
                # Moving the definition invalidates that effect rather than silently retargeting it.
                remove_race_spell_effect_refs(con, int(room["id"]), int(body.id))
            if old_name != item["name"] or old_class != body.class_name:
                classes = class_map(con, room["id"])
                for crow in con.execute("SELECT id,state_json FROM characters WHERE room_id=?", (room["id"],)):
                    st = normalize_character_state(jload(crow["state_json"], {}) or {}, classes); changed=False
                    if old_class == st.get("class_name"):
                        if old_class == body.class_name:
                            st["spellbook"] = [item["name"] if x == old_name else x for x in st.get("spellbook", [])]
                            st["prepared_spells"] = [item["name"] if x == old_name else x for x in st.get("prepared_spells", [])]
                        else:
                            st["spellbook"] = [x for x in st.get("spellbook", []) if x != old_name]
                            st["prepared_spells"] = [x for x in st.get("prepared_spells", []) if x != old_name]
                        changed = True
                    # class_access tracks are namespaced by move-effect key; update only
                    # tracks whose metadata points at the spell's former source class.
                    source_by_key = {
                        r["key"]: str((r.get("effect") or {}).get("source_class", ""))
                        for r in _active_move_effect_rows(st, classes)
                        if str((r.get("effect") or {}).get("kind", "")) == "class_access"
                    }
                    for key, track in (st.get("spell_tracks") or {}).items():
                        if source_by_key.get(key) != old_class or not isinstance(track, dict):
                            continue
                        if old_class == body.class_name:
                            track["known"] = [item["name"] if x == old_name else x for x in track.get("known", [])]
                            track["prepared"] = [item["name"] if x == old_name else x for x in track.get("prepared", [])]
                        else:
                            track["known"] = [x for x in track.get("known", []) if x != old_name]
                            track["prepared"] = [x for x in track.get("prepared", []) if x != old_name]
                        changed = True
                    for ex in st.get("extra_spells", []):
                        if int(ex.get("spell_id") or 0) == int(body.id):
                            ex["name"] = item["name"]; ex["level"] = level; ex["desc"] = body.desc
                            if ex.get("source") == old_class: ex["source"] = body.class_name
                            changed=True
                    if changed: con.execute("UPDATE characters SET state_json=?,updated_at=? WHERE id=?", (jdump(st), now_iso(), crow["id"]))
        else:
            old = con.execute("SELECT * FROM spell_defs WHERE room_id=? AND class_name=? AND name=?", (room["id"], body.class_name, item["name"])).fetchone(); before = jload(old["data_json"], None) if old else None
            con.execute("INSERT INTO spell_defs(room_id,class_name,name,level,data_json) VALUES(?,?,?,?,?) ON CONFLICT(room_id,class_name,name) DO UPDATE SET level=excluded.level,data_json=excluded.data_json", (room["id"], body.class_name, item["name"], level, jdump(item)))
        log_event(con, room["id"], actor, "주문 저장", f"{body.class_name}:{item['name']}", compact_change_detail(before or {}, item))
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "spell"}); return {"ok": True}


@app.delete("/api/rooms/{code}/spell/{spell_id}")
async def delete_spell(code: str, spell_id: int, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        row = con.execute("SELECT * FROM spell_defs WHERE id=? AND room_id=?", (spell_id, room["id"])).fetchone()
        if not row: raise HTTPException(404, "주문을 찾을 수 없습니다.")
        # Remove race-effect references to the deleted definition.
        remove_race_spell_effect_refs(con, int(room["id"]), spell_id)
        # Remove stale character references by both ID and the legacy name lists.
        classes=class_map(con, room["id"]); removed_name=row["name"]
        for crow in con.execute("SELECT id,state_json FROM characters WHERE room_id=?", (room["id"],)):
            st=normalize_character_state(jload(crow["state_json"], {}) or {}, classes); changed=False
            if st.get("class_name")==row["class_name"]:
                b=[x for x in st.get("spellbook",[]) if x!=removed_name]; p=[x for x in st.get("prepared_spells",[]) if x!=removed_name]
                if b!=st.get("spellbook",[]) or p!=st.get("prepared_spells",[]): st["spellbook"]=b; st["prepared_spells"]=p; changed=True
            source_by_key = {
                r["key"]: str((r.get("effect") or {}).get("source_class", ""))
                for r in _active_move_effect_rows(st, classes)
                if str((r.get("effect") or {}).get("kind", "")) == "class_access"
            }
            for key, track in (st.get("spell_tracks") or {}).items():
                if source_by_key.get(key) != row["class_name"] or not isinstance(track, dict):
                    continue
                known=[x for x in track.get("known",[]) if x!=removed_name]; prepared=[x for x in track.get("prepared",[]) if x!=removed_name]
                if known!=track.get("known",[]) or prepared!=track.get("prepared",[]): track["known"]=known; track["prepared"]=prepared; changed=True
            extra=[x for x in st.get("extra_spells",[]) if int(x.get("spell_id") or 0)!=int(spell_id)]
            if len(extra)!=len(st.get("extra_spells",[])): st["extra_spells"]=extra; st["prepared_spells"]=[x for x in st.get("prepared_spells",[]) if x!=removed_name]; changed=True
            if changed: con.execute("UPDATE characters SET state_json=?,updated_at=? WHERE id=?", (jdump(st), now_iso(), crow["id"]))
        con.execute("DELETE FROM spell_defs WHERE id=?", (spell_id,)); log_event(con, room["id"], actor, "주문 삭제", f"{row['class_name']}:{row['name']}", {})
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "spell"}); return {"ok": True}


@app.post("/api/rooms/{code}/characters/{character_id}/special-spells")
async def grant_special_spell(code: str, character_id: int, body: SpecialSpellGrantIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        char = con.execute("SELECT * FROM characters WHERE id=? AND room_id=?", (character_id, room["id"])).fetchone()
        if not char: raise HTTPException(404, "캐릭터를 찾을 수 없습니다.")
        sp = con.execute("SELECT * FROM spell_defs WHERE id=? AND room_id=? AND class_name='__undefined__'", (body.spell_id, room["id"])).fetchone()
        if not sp: raise HTTPException(404, "'미분류' 주문을 찾을 수 없습니다.")
        classes = class_map(con, room["id"]); state = normalize_character_state(jload(char["state_json"], {}), classes)
        item = jload(sp["data_json"], {}) or {}
        extra = [dict(x) for x in (state.get("extra_spells") or []) if isinstance(x, dict)]
        if any((x.get("kind") == "gm" and int(x.get("spell_id") or 0) == int(sp["id"])) for x in extra):
            return {"ok": True, "already": True}
        extra.append({"name": item.get("name") or sp["name"], "source": "GM 지급", "kind": "gm", "spell_id": int(sp["id"]), "level": item.get("level", sp["level"]), "desc": item.get("desc", "")})
        state["extra_spells"] = extra[:30]
        con.execute("UPDATE characters SET state_json=?,updated_at=? WHERE id=?", (jdump(state), now_iso(), char["id"]))
        log_event(con, room["id"], actor, "특수 주문 지급", item.get("name") or sp["name"], {"character_id": character_id, "spell_id": int(sp["id"])})
    await manager.broadcast(code.upper(), {"type":"refresh","reason":"special_spell"})
    return {"ok": True}


@app.delete("/api/rooms/{code}/characters/{character_id}/special-spells/{spell_id}")
async def revoke_special_spell(code: str, character_id: int, spell_id: int, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        char = con.execute("SELECT * FROM characters WHERE id=? AND room_id=?", (character_id, room["id"])).fetchone()
        if not char: raise HTTPException(404, "캐릭터를 찾을 수 없습니다.")
        classes = class_map(con, room["id"]); state = normalize_character_state(jload(char["state_json"], {}), classes)
        before = [dict(x) for x in (state.get("extra_spells") or []) if isinstance(x, dict)]
        removed = [x for x in before if x.get("kind") == "gm" and int(x.get("spell_id") or 0) == int(spell_id)]
        if not removed: raise HTTPException(404, "지급된 특수 주문을 찾을 수 없습니다.")
        state["extra_spells"] = [x for x in before if not (x.get("kind") == "gm" and int(x.get("spell_id") or 0) == int(spell_id))]
        for x in removed:
            while x.get("name") in (state.get("prepared_spells") or []): state["prepared_spells"].remove(x.get("name"))
        con.execute("UPDATE characters SET state_json=?,updated_at=? WHERE id=?", (jdump(state), now_iso(), char["id"]))
        log_event(con, room["id"], actor, "특수 주문 회수", removed[0].get("name", ""), {"character_id": character_id, "spell_id": spell_id})
    await manager.broadcast(code.upper(), {"type":"refresh","reason":"special_spell"})
    return {"ok": True}


@app.post("/api/rooms/{code}/default-data/import")
async def import_room_default_data(code: str, body: DefaultDataImportIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        kinds=set(str(x) for x in body.kinds) or {"core","classes","races","spells","expansions","monsters"}
        counts=import_default_data(con, int(room["id"]), kinds)
        log_event(con, room["id"], actor, "기본 데이터 가져오기", "", {"kinds": sorted(kinds), "added": counts})
    await manager.broadcast(code.upper(), {"type":"refresh","reason":"default_data_import"})
    return {"ok": True, "added": counts}

@app.get("/api/dwpack/reference")
def download_dwpack_reference():
    if not DWPACK_REFERENCE_PATH.exists():
        raise HTTPException(404, "DWPack 참고 파일을 찾을 수 없습니다.")
    return FileResponse(DWPACK_REFERENCE_PATH, media_type="application/zip", filename="DungeonWorld_DWPack_Reference.zip")


@app.get("/api/dwpack/core")
def download_dwpack_core(lang: str = "ko"):
    english = str(lang).lower().startswith("en")
    path = DWPACK_CORE_EN_PATH if english else DWPACK_CORE_PATH
    if not path.exists():
        raise HTTPException(404, "Dungeon World 1E 기본 팩을 찾을 수 없습니다.")
    filename = "DungeonWorld_1E_Core_EN.dwpack" if english else "DungeonWorld_1E_Core.dwpack"
    return FileResponse(path, media_type="application/zip", filename=filename)


@app.get("/api/dwpack/expansions")
def download_dwpack_expansions(lang: str = "ko"):
    english = str(lang).lower().startswith("en")
    path = DWPACK_EXPANSION_EN_PATH if english else DWPACK_EXPANSION_PATH
    if not path.exists():
        raise HTTPException(404, "Unlimited Dungeons 확장직업 팩을 찾을 수 없습니다.")
    filename = "UnlimitedDungeons_DistantShore_Expansions_EN.dwpack" if english else "UnlimitedDungeons_DistantShore_Expansions.dwpack"
    return FileResponse(path, media_type="application/zip", filename=filename)


@app.get("/api/rooms/{code}/dwpack/export")
def export_room_dwpack(code: str, include_npcs: bool = False, include_rules: bool = True, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        payload, manifest = _dwpack_export_room(con, room, include_npcs=include_npcs, include_rules=include_rules)
        filename = "DungeonWorld_Data.dwpack"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-DWPack-Format-Version": str(DWPACK_FORMAT_VERSION),
        "X-DWPack-Items": str(sum(int(v or 0) for v in dict(manifest.get("contents") or {}).values())),
    }
    return StreamingResponse(io.BytesIO(payload), media_type="application/octet-stream", headers=headers)


@app.post("/api/rooms/{code}/dwpack/preview")
async def preview_room_dwpack(code: str, file: UploadFile = File(...), authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    _cleanup_dwpack_previews()
    if file.filename and not str(file.filename).lower().endswith(".dwpack"):
        raise HTTPException(400, "확장자가 .dwpack인 팩을 선택하세요.")
    raw = await file.read(DWPACK_MAX_UPLOAD_BYTES + 1)
    if len(raw) > DWPACK_MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"팩은 최대 {DWPACK_MAX_UPLOAD_BYTES // (1024*1024)}MB까지 가져올 수 있습니다.")
    pack = _dwpack_read_upload(raw)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        conflicts = _dwpack_conflicts(con, int(room["id"]), pack)
        preview_token = secrets.token_urlsafe(24)
        dwpack_previews[preview_token] = {
            "room_id": int(room["id"]),
            "actor": actor_key(actor),
            "pack": pack,
            "expires_at": time.time() + DWPACK_PREVIEW_TTL,
        }
    manifest = dict(pack.get("manifest") or {})
    return {
        "ok": True,
        "preview_token": preview_token,
        "name": str(manifest.get("name") or file.filename or "팩"),
        "created_with": str(manifest.get("created_with") or ""),
        "format_version": int(manifest.get("format_version") or DWPACK_FORMAT_VERSION),
        "counts": _dwpack_counts(pack),
        "conflicts": conflicts[:200],
        "conflict_count": len(conflicts),
        "warnings": list(manifest.get("warnings") or [])[:100],
        "expires_in": DWPACK_PREVIEW_TTL,
    }


@app.post("/api/rooms/{code}/dwpack/import")
async def import_room_dwpack(code: str, body: DataPackImportIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    _cleanup_dwpack_previews()
    preview = dwpack_previews.get(body.preview_token)
    if not preview:
        raise HTTPException(400, "팩 미리보기가 만료되었습니다. 파일을 다시 선택하세요.")
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        if int(preview.get("room_id", 0)) != int(room["id"]) or str(preview.get("actor")) != actor_key(actor):
            raise HTTPException(403, "다른 캠페인에서 만든 팩 미리보기입니다.")
        pack = preview.get("pack") or {}
        _dwpack_validate_pack(pack)
        mode = str(body.conflict_mode or "keep")
        if mode == "sync":
            _dwpack_sync_clear(con, int(room["id"]), pack)
            counts = _dwpack_apply(con, room, pack, "keep", body.apply_rules)
        else:
            counts = _dwpack_apply(con, room, pack, mode, body.apply_rules)
        manifest = dict(pack.get("manifest") or {})
        log_event(con, int(room["id"]), actor, "팩 가져오기", str(manifest.get("name") or "DWPack"), {"mode": mode, "apply_rules": body.apply_rules, "result": counts})
    dwpack_previews.pop(body.preview_token, None)
    await manager.broadcast(code.upper(), {"type":"refresh","reason":"dwpack_import"})
    return {"ok": True, "applied": counts}


@app.post("/api/rooms/{code}/expansions")
async def create_expansion(code: str, body: ExpansionIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        clean = normalize_expansion_data(body.data)
        order = int(con.execute("SELECT COALESCE(MAX(sort_order),0)+1 n FROM expansion_defs WHERE room_id=?", (room["id"],)).fetchone()["n"])
        try:
            cur = con.execute("INSERT INTO expansion_defs(room_id,name,gm_condition,public_intro,data_json,sort_order,builtin_key,user_modified,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (room["id"], body.name.strip(), body.gm_condition, body.public_intro, jdump(clean), order, "", 1, now_iso()))
        except sqlite3.IntegrityError: raise HTTPException(400, "같은 이름의 확장직업이 이미 있습니다.")
        eid = int(cur.lastrowid); log_event(con, room["id"], actor, "확장직업 추가", body.name.strip(), {"id": eid})
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "expansion"}); return {"ok": True, "id": eid}


@app.put("/api/rooms/{code}/expansions/{expansion_id}")
async def update_expansion(code: str, expansion_id: int, body: ExpansionIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        old = con.execute("SELECT * FROM expansion_defs WHERE id=? AND room_id=?", (expansion_id, room["id"])).fetchone()
        if not old: raise HTTPException(404, "확장직업을 찾을 수 없습니다.")
        clean = normalize_expansion_data(body.data)
        try:
            con.execute("UPDATE expansion_defs SET name=?,gm_condition=?,public_intro=?,data_json=?,user_modified=1 WHERE id=?", (body.name.strip(), body.gm_condition, body.public_intro, jdump(clean), expansion_id))
        except sqlite3.IntegrityError: raise HTTPException(400, "같은 이름의 확장직업이 이미 있습니다.")
        # 개인 자원 최대치를 낮추면 이미 획득한 캐릭터의 현재값도 함께 보정한다.
        resource_max = max(0, int((clean.get("resource") or {}).get("max", 0) or 0))
        if resource_max > 0:
            classes = class_map(con, room["id"])
            for grant in con.execute("SELECT id,character_id FROM expansion_grants WHERE room_id=? AND expansion_id=? AND status='accepted'", (room["id"], expansion_id)):
                crow = con.execute("SELECT state_json FROM characters WHERE id=?", (grant["character_id"],)).fetchone()
                if not crow:
                    continue
                st = normalize_character_state(jload(crow["state_json"], {}) or {}, classes)
                ext = compact_extension_state(st.get("extension_state"))
                key = str(grant["id"])
                if key in ext and int(ext[key].get("resource_current", 0) or 0) > resource_max:
                    ext[key]["resource_current"] = resource_max
                    st["extension_state"] = ext
                    con.execute("UPDATE characters SET state_json=?,updated_at=? WHERE id=?", (jdump(st), now_iso(), grant["character_id"]))
        log_event(con, room["id"], actor, "확장직업 수정", body.name.strip(), {"before_name": old["name"], "after": {"name": body.name}})
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "expansion"}); return {"ok": True}


@app.put("/api/rooms/{code}/expansion-order")
async def reorder_expansions(code: str, body: ExpansionOrderIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        rows = list(con.execute("SELECT id FROM expansion_defs WHERE room_id=?", (room["id"],)))
        existing = {int(r["id"]) for r in rows}; ids = [int(x) for x in body.ids]
        if len(ids) != len(set(ids)) or set(ids) != existing:
            raise HTTPException(400, "확장직업 정렬 목록이 현재 캠페인 데이터와 일치하지 않습니다.")
        for index, expansion_id in enumerate(ids, start=1):
            con.execute("UPDATE expansion_defs SET sort_order=? WHERE id=?", (index, expansion_id))
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "expansion_order"})
    return {"ok": True}


def remove_extension_state_entry(con: sqlite3.Connection, character_id: int, grant_id: int) -> None:
    row = con.execute("SELECT state_json FROM characters WHERE id=?", (character_id,)).fetchone()
    if not row:
        return
    state = jload(row["state_json"], {}) or {}
    ext = compact_extension_state(state.get("extension_state"))
    if str(grant_id) not in ext:
        return
    ext.pop(str(grant_id), None)
    state["extension_state"] = ext
    con.execute("UPDATE characters SET state_json=?,updated_at=? WHERE id=?", (jdump(state), now_iso(), character_id))


@app.delete("/api/rooms/{code}/expansions/{expansion_id}")
async def delete_expansion(code: str, expansion_id: int, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        row = con.execute("SELECT * FROM expansion_defs WHERE id=? AND room_id=?", (expansion_id, room["id"])).fetchone()
        if not row: raise HTTPException(404, "확장직업을 찾을 수 없습니다.")
        grants = list(con.execute("SELECT id,character_id FROM expansion_grants WHERE expansion_id=? AND room_id=?", (expansion_id, room["id"])))
        for grant in grants:
            remove_extension_state_entry(con, int(grant["character_id"]), int(grant["id"]))
        con.execute("DELETE FROM expansion_defs WHERE id=?", (expansion_id,)); log_event(con, room["id"], actor, "확장직업 삭제", row["name"], {"removed_grants": len(grants)})
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "expansion"}); return {"ok": True}


@app.post("/api/rooms/{code}/expansions/{expansion_id}/grant")
async def grant_expansion(code: str, expansion_id: int, body: GrantIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        if not room_expansions_enabled(room): raise HTTPException(409, "이 캠페인에서는 확장직업 기능이 꺼져 있습니다.")
        exp = con.execute("SELECT * FROM expansion_defs WHERE id=? AND room_id=?", (expansion_id, room["id"])).fetchone(); char = con.execute("SELECT * FROM characters WHERE id=? AND room_id=?", (body.character_id, room["id"])).fetchone()
        if not exp or not char: raise HTTPException(404, "확장직업 또는 캐릭터를 찾을 수 없습니다.")
        rules = normalize_rules(jload(room["rules_json"], {}) or {}); count = con.execute("SELECT COUNT(*) n FROM expansion_grants WHERE character_id=? AND status IN ('pending','accepted')", (body.character_id,)).fetchone()["n"]
        existing = con.execute("SELECT * FROM expansion_grants WHERE character_id=? AND expansion_id=?", (body.character_id, expansion_id)).fetchone()
        if existing and existing["status"] == "accepted": raise HTTPException(400, "이미 획득한 확장직업입니다.")
        expansion_limit = max(0, int(rules.get("max_expansions_per_character", 3) or 0))
        adds_active_grant = existing is None or existing["status"] not in {"pending", "accepted"}
        if adds_active_grant and expansion_limit > 0 and count >= expansion_limit: raise HTTPException(400, "이 캐릭터의 확장직업 최대 개수에 도달했습니다.")
        if existing:
            con.execute("UPDATE expansion_grants SET status='pending',invite_message=?,visible_to_party=?,responded_at=NULL,created_at=? WHERE id=?", (body.message, int(body.visible_to_party), now_iso(), existing["id"])); grant_id=int(existing["id"])
        else:
            cur = con.execute("INSERT INTO expansion_grants(room_id,character_id,expansion_id,visible_to_party,status,invite_message,created_at) VALUES(?,?,?,?,?,?,?)", (room["id"], body.character_id, expansion_id, int(body.visible_to_party), 'pending', body.message, now_iso())); grant_id=int(cur.lastrowid)
        log_event(con, room["id"], actor, "확장직업 제안", f"character:{body.character_id}", {"grant_id": grant_id, "expansion": exp["name"]})
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "grant"}); return {"ok": True, "grant_id": grant_id}


@app.post("/api/rooms/{code}/grants/{grant_id}/respond")
async def respond_expansion(code: str, grant_id: int, body: GrantResponseIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if not room_expansions_enabled(room): raise HTTPException(409, "이 캠페인에서는 확장직업 기능이 꺼져 있습니다.")
        row = con.execute("SELECT g.*,e.name,c.member_id FROM expansion_grants g JOIN expansion_defs e ON e.id=g.expansion_id JOIN characters c ON c.id=g.character_id WHERE g.id=? AND g.room_id=?", (grant_id, room["id"])).fetchone()
        if not row: raise HTTPException(404, "확장직업 제안을 찾을 수 없습니다.")
        if actor["role"] != "gm" and actor.get("member_id") != row["member_id"]: raise HTTPException(403, "본인의 확장직업 제안만 응답할 수 있습니다.")
        status = 'accepted' if body.accept else 'declined'
        con.execute("UPDATE expansion_grants SET status=?,responded_at=? WHERE id=?", (status, now_iso(), grant_id))
        log_event(con, room["id"], actor, "확장직업 수락" if body.accept else "확장직업 거절", f"character:{row['character_id']}", {"expansion":row["name"]})
    await manager.broadcast(code.upper(), {"type":"refresh","reason":"grant_response"}); return {"ok":True,"status":status}


@app.delete("/api/rooms/{code}/grants/{grant_id}")
async def revoke_expansion(code: str, grant_id: int, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        row = con.execute("SELECT g.*,e.name FROM expansion_grants g JOIN expansion_defs e ON e.id=g.expansion_id WHERE g.id=? AND g.room_id=?", (grant_id, room["id"])).fetchone()
        if not row: raise HTTPException(404, "부여 기록을 찾을 수 없습니다.")
        remove_extension_state_entry(con, int(row["character_id"]), grant_id)
        con.execute("DELETE FROM expansion_grants WHERE id=?", (grant_id,)); log_event(con, room["id"], actor, "확장직업 회수", f"character:{row['character_id']}", {"expansion": row["name"]})
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "grant"}); return {"ok": True}


def normalize_dice_style(raw: dict[str, Any] | None) -> dict[str, str]:
    defaults = {"fill": "#ffffff", "border": "#111111", "text": "#111111"}
    out = dict(defaults)
    for key in defaults:
        value = str((raw or {}).get(key, "")).strip()
        if re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
            out[key] = value.lower()
    return out


@app.post("/api/rooms/{code}/dice/prepare")
async def dice_prepare(code: str, body: DicePrepareIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        dice = normalize_dice(body.dice)
        settings = normalize_settings(jload(room["settings_json"], {}) or {})
        name = actor_display(con, room["id"], actor)
        public = True if actor["role"] != "gm" else bool(settings.get("gm_dice_public", True))
        minimum_total = None if body.minimum_total is None else max(-9999, min(9999, int(body.minimum_total)))
        item = {"key": actor_key(actor), "name": name, "label": f"GM {name}" if actor["role"] == "gm" else name, "role": actor["role"], "color": actor_color(con, room, actor), "public": public, "dice": dice, "modifier": max(-99, min(99, int(body.modifier or 0))), "style": normalize_dice_style(body.style), "context": str(body.context or "")[:180], "roll_mode": str(body.roll_mode or "normal") if str(body.roll_mode or "normal") in {"normal","high","low"} else "normal", "minimum_total": minimum_total, "updated_at": now_iso()}
        dice_preparations.setdefault(code.upper(), {})[item["key"]] = item
    await manager.broadcast(code.upper(), {"type": "dice_prepare", "preparation": item}, None if public else {"gm"})
    return {"ok": True, "preparation": item}


@app.post("/api/rooms/{code}/dice/cancel")
async def dice_cancel(code: str, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        key = actor_key(actor)
        prep = dice_preparations.setdefault(code.upper(), {}).get(key)
    dice_preparations.setdefault(code.upper(), {}).pop(key, None)
    roles = {"gm"} if prep and not bool(prep.get("public", True)) else None
    await manager.broadcast(code.upper(), {"type": "dice_cancel", "key": key}, roles)
    return {"ok": True}


@app.post("/api/rooms/{code}/dice/roll")
async def dice_roll(code: str, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        key = actor_key(actor)
        prep = dice_preparations.get(code.upper(), {}).get(key)
        if not prep:
            raise HTTPException(400, "먼저 주사위를 준비하세요.")
        results = []
        values = []
        for die, count in prep.get("dice", {}).items():
            sides = int(die[1:])
            for _ in range(int(count)):
                value = secrets.randbelow(sides) + 1
                results.append({"die": die, "sides": sides, "value": value})
                values.append(value)
        mode = str(prep.get("roll_mode", "normal") or "normal")
        if mode == "high" and values:
            dice_total = max(values)
        elif mode == "low" and values:
            dice_total = min(values)
        else:
            dice_total = sum(values)
        total = dice_total + int(prep.get("modifier", 0) or 0)
        minimum_total = prep.get("minimum_total")
        if minimum_total is not None:
            total = max(int(minimum_total), total)
        roll = {"key": key, "name": prep["name"], "label": prep.get("label", prep["name"]), "role": prep["role"], "color": prep.get("color", "#181818"), "public": bool(prep.get("public", True)), "dice": prep["dice"], "modifier": prep["modifier"], "style": normalize_dice_style(prep.get("style")), "context": str(prep.get("context", ""))[:180], "roll_mode": mode, "minimum_total": minimum_total, "results": results, "dice_total": dice_total, "total": total, "rolled_at": now_iso()}
        log_event(con, room["id"], actor, "주사위 굴림", prep["name"], {"dice": prep["dice"], "modifier": prep["modifier"], "results": results, "dice_total": dice_total, "total": total, "public": bool(prep.get("public", True))})
    dice_preparations.setdefault(code.upper(), {}).pop(key, None)
    roles = {"gm"} if not bool(roll.get("public", True)) else None
    await manager.broadcast(code.upper(), {"type": "dice_roll", "roll": roll}, roles)
    return {"ok": True, "roll": roll}


@app.put("/api/rooms/{code}/order/{kind}")
async def reorder_entities(code: str, kind: str, body: ReorderIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    table_map = {"classes":"class_defs", "races":"race_defs", "npcs":"npc_defs", "folders":"monster_folders", "sounds":"sound_defs"}
    if kind == "monsters":
        raise HTTPException(409, "몬스터는 드래그로 이동할 수 없습니다. 몬스터 편집기의 지역 / 폴더에서 이동해주세요.")
    table = table_map.get(kind)
    if not table:
        raise HTTPException(404, "정렬 대상을 찾을 수 없습니다.")
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        if kind in {"classes", "races"} and body.names:
            for pos, entity_name in enumerate(body.names, 1):
                con.execute(f"UPDATE {table} SET sort_order=? WHERE name=? AND room_id=?", (pos, entity_name, room["id"]))
        else:
            for pos, entity_id in enumerate(body.ids, 1):
                if kind == "sounds":
                    con.execute("UPDATE sound_defs SET sort_order=? WHERE id=? AND room_id=?", (pos, entity_id, room["id"]))
                else:
                    con.execute(f"UPDATE {table} SET sort_order=? WHERE id=? AND room_id=?", (pos, entity_id, room["id"]))
    await manager.broadcast(code.upper(), {"type":"refresh","reason":"reorder"})
    return {"ok": True}


@app.put("/api/rooms/{code}/monsters/{monster_id}/move")
async def move_monster(code: str, monster_id: int, body: ReorderIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        raise HTTPException(409, "몬스터는 드래그로 이동할 수 없습니다. 몬스터 편집기의 지역 / 폴더에서 이동해주세요.")


@app.post("/api/rooms/{code}/sounds/upload")
async def sound_upload(code: str, kind: str = Form("bgm"), name: str = Form(""), file: UploadFile = File(...), authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        room_code = str(room["code"]); room_id = int(room["id"])
    kind = kind if kind in {"bgm", "sfx"} else "bgm"
    ext = Path(file.filename or "sound.bin").suffix.lower()
    if ext not in {".mp3", ".ogg", ".wav", ".m4a", ".aac", ".webm"}:
        raise HTTPException(400, "지원하는 오디오 파일 형식이 아닙니다.")
    room_dir = SOUND_DIR / room_code
    room_dir.mkdir(parents=True, exist_ok=True)
    fname = secrets.token_hex(12) + ext
    target = room_dir / fname
    temp = room_dir / (fname + ".part")
    written = 0
    try:
        with temp.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_SOUND_UPLOAD_BYTES:
                    raise HTTPException(400, "사운드 파일은 50MB 이하만 업로드할 수 있습니다.")
                out.write(chunk)
        temp.replace(target)
        source = f"/media/{room_code}/{fname}"
        label = (name.strip() or Path(file.filename or "사운드").stem)[:120]
        with db() as con:
            room = room_by_code(con, code); actor = auth_context(con, room, token)
            if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
            if int(room["id"]) != room_id: raise HTTPException(409, "캠페인 상태가 변경되었습니다. 다시 시도해주세요.")
            order = int(con.execute("SELECT COALESCE(MAX(sort_order),0)+1 n FROM sound_defs WHERE room_id=? AND kind=?", (room_id, kind)).fetchone()["n"])
            cur = con.execute("INSERT INTO sound_defs(room_id,kind,name,source_type,source,sort_order,created_at) VALUES(?,?,?,?,?,?,?)", (room_id, kind, label, "file", source, order, now_iso()))
            sid = int(cur.lastrowid)
            log_event(con, room_id, actor, "사운드 추가", label, {"id": sid, "kind": kind, "source_type": "file"})
    except Exception:
        temp.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    await manager.broadcast(code.upper(), {"type":"refresh","reason":"sound_library"})
    return {"ok": True, "id": sid}


@app.delete("/api/rooms/{code}/sounds/{sound_id}")
async def sound_delete(code: str, sound_id: int, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        row = con.execute("SELECT * FROM sound_defs WHERE id=? AND room_id=?", (sound_id, room["id"])).fetchone()
        if not row: raise HTTPException(404, "사운드를 찾을 수 없습니다.")
        con.execute("DELETE FROM sound_defs WHERE id=?", (sound_id,))
        if row["source_type"] == "file" and str(row["source"]).startswith("/media/"):
            try:
                rel = str(row["source"])[len("/media/"):]
                (SOUND_DIR / rel).unlink(missing_ok=True)
            except Exception:
                pass
        log_event(con, room["id"], actor, "사운드 삭제", row["name"], {"id": sound_id})
    await manager.broadcast(code.upper(), {"type":"refresh","reason":"sound_library"})
    return {"ok": True}


def sound_state_volume(state: dict[str, Any], key: str, fallback: float = 1.0) -> float:
    raw = state.get(key, fallback)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = fallback
    return max(0.0, min(1.0, value))


@app.post("/api/rooms/{code}/sounds/play")
async def sound_play(code: str, body: SoundPlayIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        if body.sound_id is None: raise HTTPException(400, "사운드를 선택하세요.")
        row = con.execute("SELECT * FROM sound_defs WHERE id=? AND room_id=? AND source_type='file'", (body.sound_id, room["id"])).fetchone()
        if not row: raise HTTPException(404, "사운드를 찾을 수 없습니다.")
        item = dict(row)
        old_state = dict(sound_states.get(code.upper(), {}))
        if item["kind"] == "sfx":
            sfx_volume = max(0.0, min(1.0, float(body.volume)))
            old_state.setdefault("status", "stopped"); old_state.setdefault("sound_id", None); old_state.setdefault("position", 0.0); old_state.setdefault("bgm_volume", sound_state_volume(old_state, "volume"))
            old_state["sfx_volume"] = sfx_volume
            old_state.setdefault("updated_at", now_iso())
            sound_states[code.upper()] = old_state
            event = {"type":"sound_sfx", "sound": item, "volume": sfx_volume, "played_at": now_iso()}
            await manager.broadcast(code.upper(), event)
            return {"ok": True}
        bgm_volume = max(0.0, min(1.0, float(body.volume)))
        state = {"status":"playing","sound_id":item["id"],"sound":item,"position":max(0.0,float(body.position)),"volume":bgm_volume,"bgm_volume":bgm_volume,"sfx_volume":sound_state_volume(old_state, "sfx_volume"),"mode":str(old_state.get("mode","next") or "next"),"updated_at":now_iso()}
        sound_states[code.upper()] = state
    await manager.broadcast(code.upper(), {"type":"sound_bgm","state":state})
    return {"ok": True, "state": state}


@app.post("/api/rooms/{code}/sounds/pause")
async def sound_pause(code: str, body: SoundPlayIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
    state = dict(sound_states.get(code.upper(), {})); state.update({"status":"paused","position":max(0.0,float(body.position)),"updated_at":now_iso()}); sound_states[code.upper()] = state
    await manager.broadcast(code.upper(), {"type":"sound_bgm","state":state})
    return {"ok": True, "state": state}


@app.post("/api/rooms/{code}/sounds/stop")
async def sound_stop(code: str, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
    old_state = dict(sound_states.get(code.upper(), {}))
    bgm_volume = sound_state_volume(old_state, "bgm_volume", sound_state_volume(old_state, "volume")); sfx_volume = sound_state_volume(old_state, "sfx_volume")
    state = {"status":"stopped","sound_id":None,"position":0.0,"volume":bgm_volume,"bgm_volume":bgm_volume,"sfx_volume":sfx_volume,"mode":str(old_state.get("mode","next") or "next"),"updated_at":now_iso()}; sound_states[code.upper()] = state
    await manager.broadcast(code.upper(), {"type":"sound_bgm","state":state})
    return {"ok": True, "state": state}


@app.post("/api/rooms/{code}/sounds/control")
async def sound_control(code: str, body: SoundControlIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        bgms = [dict(x) for x in con.execute("SELECT * FROM sound_defs WHERE room_id=? AND kind='bgm' AND source_type='file' ORDER BY sort_order,id", (room["id"],))]
        state = dict(sound_states.get(code.upper(), {"status":"stopped","sound_id":None,"position":0.0,"bgm_volume":1.0,"sfx_volume":1.0,"mode":"next","updated_at":now_iso()}))
        if body.mode in {"next","repeat_one","repeat_all","stop_after"}: state["mode"] = body.mode
        action = str(body.action or "").lower()
        if action in {"next","prev"} and bgms:
            ids=[int(x["id"]) for x in bgms]; cur=int(state.get("sound_id") or 0)
            try: idx=ids.index(cur)
            except ValueError: idx=-1 if action=="next" else 0
            if action=="next": idx=(idx+1)%len(ids)
            else: idx=(idx-1)%len(ids)
            item=bgms[idx]; state.update({"status":"playing","sound_id":item["id"],"sound":item,"position":0.0,"updated_at":now_iso()})
        elif action=="seek":
            state["position"] = max(0.0,float(body.position)); state["updated_at"] = now_iso()
        elif action=="resume" and state.get("sound_id"):
            state["status"] = "playing"; state["updated_at"] = now_iso()
        sound_states[code.upper()] = state
    await manager.broadcast(code.upper(), {"type":"sound_bgm","state":state})
    return {"ok": True, "state": state}


@app.post("/api/rooms/{code}/sounds/volume")
async def sound_volume(code: str, body: SoundVolumeIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
    kind = body.kind if body.kind in {"bgm", "sfx"} else "bgm"
    value = max(0.0, min(1.0, float(body.volume)))
    state = dict(sound_states.get(code.upper(), {"status":"stopped","sound_id":None,"position":0.0,"volume":1.0,"bgm_volume":1.0,"sfx_volume":1.0,"mode":"next","updated_at":now_iso()}))
    if kind == "bgm":
        state["bgm_volume"] = value; state["volume"] = value
    else:
        state["sfx_volume"] = value
    sound_states[code.upper()] = state
    await manager.broadcast(code.upper(), {"type":"sound_mixer","bgm_volume":float(state.get("bgm_volume", state.get("volume", 1.0))),"sfx_volume":float(state.get("sfx_volume", 1.0))})
    if kind == "bgm" and state.get("sound_id"):
        await manager.broadcast(code.upper(), {"type":"sound_bgm","state":state})
    return {"ok": True, "bgm_volume":float(state.get("bgm_volume", state.get("volume", 1.0))), "sfx_volume":float(state.get("sfx_volume", 1.0))}


@app.post("/api/rooms/{code}/logs")
async def manual_log(code: str, body: ManualLogIn, authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    with db() as con:
        room = room_by_code(con, code); actor = auth_context(con, room, token)
        if actor["role"] != "gm": raise HTTPException(403, "GM 권한이 필요합니다.")
        log_event(con, room["id"], actor, "플레이 기록", "manual", {"text": body.text})
    await manager.broadcast(code.upper(), {"type": "refresh", "reason": "log"}); return {"ok": True}


@app.websocket("/ws/{code}")
async def websocket_endpoint(ws: WebSocket, code: str):
    code = code.upper(); token = ws.query_params.get("token", "")
    try:
        with db() as con:
            room = room_by_code(con, code); actor = auth_context(con, room, token)
            role = actor.get("role", "player")
    except Exception:
        await ws.close(code=4401); return
    await manager.connect(code, ws, role, actor.get("member_id"))
    await manager.broadcast(code, {"type":"refresh","reason":"presence"})
    try:
        await ws.send_json({"type": "connected"})
        while True: await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(code, ws)
        try:
            await manager.broadcast(code, {"type":"refresh","reason":"presence"})
        except Exception:
            pass


app.mount("/media", StaticFiles(directory=SOUND_DIR), name="media")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def index_response() -> HTMLResponse:
    app_version = VERSION.split("-", 1)[0]
    display_version = f"v{app_version}"
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    html = (html.replace("__BUILD_ID__", BUILD_ID)
                .replace("__APP_VERSION__", app_version)
                .replace("__DISPLAY_VERSION__", display_version))
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


@app.get("/")
def index():
    return index_response()


@app.get("/{path:path}")
def spa_fallback(path: str):
    if path.startswith("api/") or path.startswith("ws/"): raise HTTPException(404)
    return index_response()
