from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from io import BytesIO
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LAUNCHER = ROOT / "launcher"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
APP_VERSION = VERSION.split("-", 1)[0]
DISPLAY_VERSION = f"v{APP_VERSION}"
PAYLOAD_FILES = [
    "VERSION",
    "app.py",
    "requirements.txt",
    "static/app.js",
    "static/index.html",
    "static/styles.css",
    "static/i18n_content_en.json",
    "static/i18n_ui_en.json",
    "data/seed_data.json",
    "data/monster_seed.json",
    "dwpack/DungeonWorld_DWPack_Reference.zip",
    "dwpack/DungeonWorld_1E_Core.dwpack",
    "dwpack/DungeonWorld_1E_Core_EN.dwpack",
    "dwpack/UnlimitedDungeons_DistantShore_Expansions.dwpack",
    "dwpack/UnlimitedDungeons_DistantShore_Expansions_EN.dwpack",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "AI_USE_NOTICE.md",
    "LICENSE_ATTRIBUTION_KO.md",
]

RELEASE_ID_FILES = PAYLOAD_FILES + [
    "launcher/go.mod",
    "launcher/main.go",
    "launcher/process_windows.go",
    "launcher/process_other.go",
]

PAYLOAD_AAD = b"DungeonWorld::payload::v1"
PAYLOAD_MAGIC = b"DWENC1"
PAYLOAD_KEY_A = bytes([0x9c,0x21,0x73,0xa8,0xf0,0x44,0x8b,0x5d,0x11,0x6f,0xc2,0x3a,0x94,0xe7,0x50,0x1d,0x6a,0xbe,0x03,0xd1,0x87,0x59,0x2c,0xf4,0x38,0xa1,0x6d,0x0b,0xe5,0x72,0x49,0xbc])
PAYLOAD_KEY_B = bytes([0x31,0xd4,0x06,0x5f,0x82,0xae,0x19,0xc7,0xb8,0x2a,0x75,0x90,0x4d,0x13,0xe6,0xa4,0xcf,0x55,0xb9,0x2e,0x64,0xf3,0x80,0x17,0xad,0x4c,0xd8,0x61,0x09,0xfe,0x36,0x42])
PAYLOAD_KEY = bytes(a ^ b for a, b in zip(PAYLOAD_KEY_A, PAYLOAD_KEY_B))


def schema_version() -> int:
    text = (ROOT / "app.py").read_text(encoding="utf-8")
    m = re.search(r"^SCHEMA_VERSION\s*=\s*(\d+)\s*$", text, re.MULTILINE)
    if not m:
        raise RuntimeError("app.py에서 SCHEMA_VERSION을 찾을 수 없습니다.")
    return int(m.group(1))


def generate_reference_zip() -> None:
    """Rebuild the DWPack reference ZIP from its source directory.

    Keeping the archive generated prevents edited schemas/docs from drifting away from
    the ZIP embedded in a release.
    """
    src = ROOT / "dwpack" / "reference"
    dst = ROOT / "dwpack" / "DungeonWorld_DWPack_Reference.zip"
    with zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(x for x in src.rglob("*") if x.is_file()):
            rel = path.relative_to(src).as_posix()
            info = zipfile.ZipInfo(rel, date_time=(2026, 9, 14, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())

def generate_bilingual_assets() -> None:
    # English display catalogs and language-specific packs are generated from the
    # canonical rule data immediately before BUILD_ID calculation. This prevents
    # stale translations or packs from being shipped with a newer source tree.
    for rel in (
        "tools/build_i18n_en.py",
        "tools/build_i18n_ui_en.py",
        "tools/build_bilingual_packs.py",
    ):
        run([sys.executable, rel], ROOT)


def validate_sources() -> None:
    compile((ROOT / "app.py").read_text(encoding="utf-8"), str(ROOT / "app.py"), "exec")
    for rel in ("data/seed_data.json", "data/monster_seed.json", "static/i18n_content_en.json", "static/i18n_ui_en.json"):
        json.loads((ROOT / rel).read_text(encoding="utf-8"))
    content_catalog = json.loads((ROOT / "static/i18n_content_en.json").read_text(encoding="utf-8"))
    if content_catalog.get("unmapped"):
        raise RuntimeError(f"영문 기본 자료에 미번역 문자열이 남았습니다: {len(content_catalog['unmapped'])}")
    for rel in (
        "dwpack/DungeonWorld_1E_Core.dwpack",
        "dwpack/DungeonWorld_1E_Core_EN.dwpack",
        "dwpack/UnlimitedDungeons_DistantShore_Expansions.dwpack",
        "dwpack/UnlimitedDungeons_DistantShore_Expansions_EN.dwpack",
    ):
        if not (ROOT / rel).is_file():
            raise RuntimeError(f"필수 데이터팩이 없습니다: {rel}")
    node = shutil.which("node")
    if node:
        run([node, "--check", str(ROOT / "static/app.js")], ROOT)


def decrypt_payload_file(payload: Path) -> bytes:
    blob = payload.read_bytes()
    if not blob.startswith(PAYLOAD_MAGIC) or len(blob) <= len(PAYLOAD_MAGIC) + 12:
        raise RuntimeError("encrypted payload 형식 오류")
    nonce = blob[len(PAYLOAD_MAGIC):len(PAYLOAD_MAGIC)+12]
    ciphertext = blob[len(PAYLOAD_MAGIC)+12:]
    return AESGCM(PAYLOAD_KEY).decrypt(nonce, ciphertext, PAYLOAD_AAD)


def verify_payload(payload: Path, build_id: str) -> bytes:
    plain = decrypt_payload_file(payload)
    expected = PAYLOAD_FILES + ["BUILD_ID"]
    with zipfile.ZipFile(BytesIO(plain), "r") as zf:
        names = zf.namelist()
        if names != expected:
            raise RuntimeError(f"payload 파일 목록이 예상과 다릅니다: {names}")
        for rel in expected:
            source = (ROOT / rel).read_bytes()
            if zf.read(rel) != source:
                raise RuntimeError(f"payload 검증 실패: {rel}")
    if (ROOT / "BUILD_ID").read_text(encoding="utf-8").strip() != build_id:
        raise RuntimeError("BUILD_ID 검증 실패")
    return plain


def verify_embedded_payload(exe: Path, payload: Path, plain: bytes) -> None:
    enc = payload.read_bytes()
    exe_bytes = exe.read_bytes()
    if enc not in exe_bytes:
        raise RuntimeError("EXE에서 내장 payload.enc 원본 바이트를 찾지 못했습니다.")
    if plain in exe_bytes:
        raise RuntimeError("EXE 안에 평문 payload ZIP이 그대로 포함되어 있습니다.")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_build_id() -> str:
    # BUILD_ID identifies the complete runnable release, not only the Python/web
    # payload.  This prevents two EXEs with different launcher code from sharing
    # the same network compatibility identifier.
    h = hashlib.sha256()
    for rel in RELEASE_ID_FILES:
        data = (ROOT / rel).read_bytes()
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(data)
        h.update(b"\0")
    return h.hexdigest()[:16]


def build_payload(build_id: str) -> Path:
    (ROOT / "BUILD_ID").write_text(build_id + "\n", encoding="utf-8")
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel in PAYLOAD_FILES + ["BUILD_ID"]:
            data = (ROOT / rel).read_bytes()
            info = zipfile.ZipInfo(rel, date_time=(2026, 9, 10, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, data)
    plain = buf.getvalue()
    # Deterministic nonce keeps identical sources reproducible while AES-GCM still
    # authenticates the encrypted bundle. A release key must never be reused with
    # a different plaintext under the same nonce; the nonce derives from plaintext.
    nonce = hashlib.sha256(b"DW-PAYLOAD-NONCE\0" + plain + PAYLOAD_KEY).digest()[:12]
    ciphertext = AESGCM(PAYLOAD_KEY).encrypt(nonce, plain, PAYLOAD_AAD)
    out = LAUNCHER / "payload.enc"
    out.write_bytes(PAYLOAD_MAGIC + nonce + ciphertext)
    old = LAUNCHER / "payload.zip"
    if old.exists():
        old.unlink()
    return out


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def main() -> int:
    if shutil.which("go") is None:
        print("Go compiler를 찾을 수 없습니다.", file=sys.stderr)
        return 2
    generate_reference_zip()
    generate_bilingual_assets()
    # Format launcher sources before calculating BUILD_ID so the identifier is
    # stable for the exact code that will be compiled.
    run(["gofmt", "-w", "main.go", "process_windows.go", "process_other.go"], LAUNCHER)
    validate_sources()
    build_id = compute_build_id()
    payload = build_payload(build_id)
    plain_payload = verify_payload(payload, build_id)

    run(["go", "test", "./..."], LAUNCHER)
    run(["go", "vet", "./..."], LAUNCHER)

    out = ROOT / f"DungeonWorld_Online_v{APP_VERSION}.exe"
    env = os.environ.copy()
    env.update({"GOOS": "windows", "GOARCH": "amd64", "CGO_ENABLED": "0"})
    run(["go", "build", "-trimpath", "-ldflags=-s -w -H=windowsgui", "-o", str(out), "."], LAUNCHER, env)
    verify_embedded_payload(out, payload, plain_payload)

    manifest = {
        "version": VERSION,
        "display_version": DISPLAY_VERSION,
        "schema_version": schema_version(),
        "build_id": build_id,
        "payload_encrypted_sha256": sha256_file(payload),
        "payload_plain_sha256": hashlib.sha256(plain_payload).hexdigest(),
        "payload_protection": "AES-256-GCM + authenticated integrity; Go symbols stripped",
        "exe_sha256": sha256_file(out),
        "payload_files": PAYLOAD_FILES + ["BUILD_ID"],
    }
    (ROOT / "BUILD_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
