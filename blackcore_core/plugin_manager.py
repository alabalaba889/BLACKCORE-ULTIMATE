"""Permission registry for plugins. It records approvals but never imports or executes plugin code."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .plugins import validate_manifest


class PluginRegistry:
    """Small local registry; enabling a plugin is metadata only, not code execution."""

    def __init__(self, state_file: str):
        self.state_file = Path(state_file).expanduser().resolve()

    def _read(self) -> dict[str, Any]:
        if not self.state_file.exists():
            return {"schema": 1, "plugins": {}}
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("Registro de plugins inválido; não será sobrescrito.") from exc
        if not isinstance(data, dict) or data.get("schema") != 1 or not isinstance(data.get("plugins"), dict):
            raise ValueError("Formato do registro de plugins inválido.")
        return data

    def _write(self, data: dict[str, Any]) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=".plugins-", suffix=".tmp", dir=str(self.state_file.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, self.state_file)
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass

    def register(self, manifest: dict[str, Any], *, approved_permissions: list[str] | None = None,
                 user_approved: bool = False) -> dict[str, Any]:
        if not user_approved:
            raise PermissionError("Cadastro bloqueado: confirme explicitamente a instalação.")
        clean = validate_manifest(manifest)
        requested = set(clean["permissions"])
        approved = set(approved_permissions or [])
        if not approved.issubset(requested):
            raise ValueError("Só é possível conceder permissões solicitadas pelo plugin.")
        data = self._read()
        key = clean["name"].casefold()
        data["plugins"][key] = {
            "name": clean["name"], "version": clean["version"],
            "entrypoint": clean["entrypoint"], "requested_permissions": sorted(requested),
            "granted_permissions": sorted(approved), "enabled": False,
            "execution_supported": False,
        }
        self._write(data)
        return dict(data["plugins"][key])

    def set_enabled(self, name: str, enabled: bool, *, user_approved: bool = False) -> dict[str, Any]:
        if not user_approved:
            raise PermissionError("Ação bloqueada: confirme explicitamente.")
        if not isinstance(enabled, bool):
            raise ValueError("enabled precisa ser booleano.")
        data = self._read()
        key = name.casefold()
        if key not in data["plugins"]:
            raise KeyError("Plugin não cadastrado.")
        # The flag is a user preference only. This module never launches plugin code.
        data["plugins"][key]["enabled"] = enabled
        self._write(data)
        return dict(data["plugins"][key])

    def list_plugins(self) -> list[dict[str, Any]]:
        data = self._read()
        return [dict(item) for item in data["plugins"].values()]
