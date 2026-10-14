"""Transport-agnostic pairing/session primitives. No network listener is created here."""
from __future__ import annotations

import hashlib
import secrets
import time
from collections import deque
from typing import Callable

ALLOWED_REMOTE_PERMISSIONS = {"view_screen", "mouse", "keyboard", "launch_app"}
ALLOWED_REMOTE_COMMANDS = {
    "view_screen": {"screen_snapshot"},
    "mouse": {"mouse_move", "mouse_click"},
    "keyboard": {"key_press"},
    "launch_app": {"launch_allowlisted_app"},
}


class PairingManager:
    """In-memory pairing; send the returned session token only over a trusted encrypted channel."""

    def __init__(self, *, pairing_ttl: int = 120, session_ttl: int = 900,
                 clock: Callable[[], float] = time.time, max_attempts: int = 5):
        self.pairing_ttl = max(30, min(int(pairing_ttl), 600))
        self.session_ttl = max(60, min(int(session_ttl), 3600))
        self.clock = clock
        self.max_attempts = max(1, min(int(max_attempts), 20))
        self._pairings: dict[str, dict] = {}
        self._sessions: dict[str, dict] = {}
        self._attempts: deque[float] = deque()
        self.audit_log: deque[dict] = deque(maxlen=500)

    def _audit(self, event: str, device: str = "", detail: str = "") -> None:
        self.audit_log.append({"time": int(self.clock()), "event": event,
                               "device": device[:80], "detail": detail[:160]})

    def create_pairing_code(self, *, approved_permissions: list[str] | None = None) -> str:
        perms = set(approved_permissions or [])
        if not perms.issubset(ALLOWED_REMOTE_PERMISSIONS):
            raise ValueError("Permissão remota desconhecida.")
        now = self.clock()
        code = f"{secrets.randbelow(1_000_000):06d}"
        # Replace collisions rather than accidentally pairing the wrong device.
        while code in self._pairings:
            code = f"{secrets.randbelow(1_000_000):06d}"
        self._pairings[code] = {"expires": now + self.pairing_ttl, "permissions": sorted(perms)}
        self._audit("pairing_created", detail="code_redacted")
        return code

    def pair(self, code: str, device_name: str) -> dict[str, object]:
        now = self.clock()
        while self._attempts and self._attempts[0] < now - 60:
            self._attempts.popleft()
        if len(self._attempts) >= self.max_attempts:
            self._audit("pairing_rate_limited")
            raise PermissionError("Muitas tentativas; aguarde antes de tentar novamente.")
        self._attempts.append(now)
        pairing = self._pairings.pop(str(code), None)  # one-time code, even on failed attempt
        if not pairing or pairing["expires"] < now:
            self._audit("pairing_rejected")
            raise PermissionError("Código inválido, expirado ou já utilizado.")
        device = " ".join(str(device_name).split())[:80]
        if not device:
            raise ValueError("Nome do dispositivo obrigatório.")
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        self._sessions[token_hash] = {
            "device": device, "permissions": pairing["permissions"],
            "expires": now + self.session_ttl, "revoked": False,
        }
        self._audit("device_paired", device, "token_not_logged")
        return {"session_token": token, "expires_unix": int(now + self.session_ttl),
                "permissions": list(pairing["permissions"])}

    def authorize(self, token: str, command: str, *, approved: bool = False) -> bool:
        if not approved:
            self._audit("command_blocked", detail="user_confirmation_missing")
            raise PermissionError("Ação remota exige aprovação explícita do usuário.")
        token_hash = hashlib.sha256(str(token).encode("utf-8")).hexdigest()
        session = self._sessions.get(token_hash)
        if not session or session["revoked"] or session["expires"] <= self.clock():
            self._audit("session_rejected", detail="invalid_expired_or_revoked")
            raise PermissionError("Sessão inválida, expirada ou revogada.")
        permission = next((perm for perm, commands in ALLOWED_REMOTE_COMMANDS.items()
                           if command in commands), None)
        if permission is None or permission not in session["permissions"]:
            self._audit("command_denied", session["device"], "permission_or_command_not_allowed")
            raise PermissionError("Comando não permitido pelas permissões do dispositivo.")
        self._audit("command_authorized", session["device"], command)
        return True

    def revoke(self, token: str) -> bool:
        token_hash = hashlib.sha256(str(token).encode("utf-8")).hexdigest()
        session = self._sessions.get(token_hash)
        if not session or session["revoked"]:
            return False
        session["revoked"] = True
        self._audit("device_revoked", session["device"])
        return True

    def list_devices(self) -> list[dict[str, object]]:
        now = self.clock()
        return [{"device": item["device"], "permissions": list(item["permissions"]),
                 "expires_unix": int(item["expires"]), "revoked": item["revoked"],
                 "expired": item["expires"] <= now}
                for item in self._sessions.values()]
