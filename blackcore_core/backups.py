"""Explicit, local backup/restore helpers. No automatic deletion or background repair."""
from __future__ import annotations
import shutil
from pathlib import Path


def create_backup(source: str, backup_root: str) -> Path:
    src = Path(source).expanduser().resolve()
    root = Path(backup_root).expanduser().resolve()
    if not src.exists() or not src.is_file():
        raise ValueError("A origem precisa ser um arquivo existente.")
    root.mkdir(parents=True, exist_ok=True)
    target = root / (src.name + ".backup")
    if target.exists():
        raise FileExistsError(f"Backup já existe: {target}")
    shutil.copy2(src, target)
    return target


def restore_backup(backup: str, destination: str, *, confirmed: bool = False) -> Path:
    """Restore to an explicit destination; requires caller to pass confirmed=True."""
    if not confirmed:
        raise PermissionError("Restauração bloqueada: confirme explicitamente antes de continuar.")
    src = Path(backup).expanduser().resolve()
    dst = Path(destination).expanduser().resolve()
    if not src.is_file():
        raise ValueError("O arquivo de backup não existe.")
    if dst.exists() and not dst.is_file():
        raise ValueError("O destino existe e não é um arquivo.")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst
