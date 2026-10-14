"""Versioned file backups with integrity checks and explicit restore confirmation."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_versioned_backup(source: str, backup_root: str) -> dict[str, str]:
    src = Path(source).expanduser().resolve(strict=True)
    if not src.is_file() or src.is_symlink():
        raise ValueError("A origem precisa ser um arquivo regular, não um link.")
    root = Path(backup_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    backup_id = str(int(time.time())) + "-" + uuid.uuid4().hex[:12]
    target = root / (backup_id + ".backup")
    shutil.copy2(src, target)
    record = {
        "id": backup_id, "source_name": src.name, "backup_path": str(target),
        "sha256": _sha256(target), "size_bytes": str(target.stat().st_size),
        "created_unix": str(int(time.time())),
    }
    metadata = root / (backup_id + ".json")
    metadata.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def restore_versioned_backup(backup_path: str, destination: str, expected_sha256: str,
                             *, confirmed: bool = False) -> Path:
    if not confirmed:
        raise PermissionError("Restauração bloqueada: é necessária confirmação explícita.")
    src = Path(backup_path).expanduser().resolve(strict=True)
    if not src.is_file() or src.is_symlink():
        raise ValueError("O backup precisa ser um arquivo regular.")
    actual = _sha256(src)
    if not isinstance(expected_sha256, str) or actual != expected_sha256:
        raise ValueError("Integridade do backup não confere; restauração cancelada.")
    dst = Path(destination).expanduser().resolve()
    if dst.exists() and (not dst.is_file() or dst.is_symlink()):
        raise ValueError("O destino precisa ser um arquivo regular.")
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".restore-", suffix=".tmp", dir=str(dst.parent))
    try:
        with os.fdopen(fd, "wb") as output, src.open("rb") as input_stream:
            shutil.copyfileobj(input_stream, output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp_name, dst)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
    return dst
