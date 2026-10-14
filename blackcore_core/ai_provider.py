"""Safe, minimal AI provider abstraction for local Ollama and OpenAI-compatible APIs.

This module only sends chat messages and returns text. It does not execute model output.
Credentials are read from environment variables and must never be committed.
"""
from __future__ import annotations
import json
import os
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlsplit

_ALLOWED_ROLES = {"system", "user", "assistant"}
_MAX_MESSAGES = 40
_MAX_MESSAGE_CHARS = 20_000
_MAX_RESPONSE_BYTES = 2_000_000

class AIProviderError(RuntimeError):
    """Safe provider error without leaking credentials."""

def _messages_for_request(messages: Iterable[dict]) -> list[dict]:
    result = []
    for item in messages:
        if not isinstance(item, dict):
            raise ValueError("Cada mensagem deve ser um objeto.")
        role, content = item.get("role"), item.get("content")
        if role not in _ALLOWED_ROLES:
            raise ValueError("Papel de mensagem não permitido.")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("O conteúdo da mensagem não pode estar vazio.")
        if len(content) > _MAX_MESSAGE_CHARS:
            raise ValueError("Mensagem muito grande (limite de 20.000 caracteres).")
        result.append({"role": role, "content": content})
        if len(result) > _MAX_MESSAGES:
            raise ValueError("Limite de 40 mensagens por pedido excedido.")
    if not result:
        raise ValueError("Adicione pelo menos uma mensagem.")
    return result

class AIClient:
    """Reads provider configuration from environment; stores no credentials in source."""
    def __init__(self, environ=None, timeout: float = 45.0):
        env = os.environ if environ is None else environ
        self.provider = env.get("BLACKCORE_AI_PROVIDER", "ollama").strip().lower()
        self.model = env.get("BLACKCORE_AI_MODEL", "").strip()
        self.timeout = max(1.0, min(float(timeout), 120.0))
        if self.provider == "ollama":
            self.endpoint = env.get("BLACKCORE_AI_ENDPOINT", "http://127.0.0.1:11434/api/chat").strip()
            self.api_key = ""
            self.model = self.model or "llama3.2"
        elif self.provider == "openai_compatible":
            self.endpoint = env.get("BLACKCORE_AI_ENDPOINT", "https://api.openai.com/v1/chat/completions").strip()
            self.api_key = env.get("BLACKCORE_AI_API_KEY", "").strip()
            if not self.api_key:
                raise ValueError("Defina BLACKCORE_AI_API_KEY no ambiente do sistema.")
            self.model = self.model or "gpt-4o-mini"
        else:
            raise ValueError("BLACKCORE_AI_PROVIDER deve ser 'ollama' ou 'openai_compatible'.")
        parsed = urlsplit(self.endpoint)
        if parsed.username or parsed.password or not parsed.hostname:
            raise ValueError("Endpoint inválido.")
        is_local_http = parsed.scheme == "http" and parsed.hostname.lower() in {"127.0.0.1", "localhost", "::1"}
        is_secure_https = parsed.scheme == "https"
        if not (is_local_http or is_secure_https):
            raise ValueError("Endpoint bloqueado: use localhost para IA local ou HTTPS para serviço remoto.")
        if self.provider == "ollama" and not is_local_http:
            raise ValueError("Ollama só pode usar endpoint local nesta versão.")
        if not self.model or len(self.model) > 160:
            raise ValueError("Nome do modelo inválido.")

    def chat(self, messages: Iterable[dict]) -> str:
        safe_messages = _messages_for_request(messages)
        payload = {"model": self.model, "messages": safe_messages, "stream": False}
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        request = Request(self.endpoint, data=json.dumps(payload).encode("utf-8"),
                          headers=headers, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
            if len(raw) > _MAX_RESPONSE_BYTES:
                raise AIProviderError("Resposta da IA excedeu o limite permitido.")
            data = json.loads(raw.decode("utf-8"))
        except HTTPError as exc:
            raise AIProviderError(f"O provedor de IA respondeu com HTTP {exc.code}.") from None
        except (URLError, TimeoutError, OSError):
            raise AIProviderError("Não foi possível conectar ao provedor de IA. Verifique endpoint e conexão.") from None
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise AIProviderError("O provedor retornou uma resposta inválida.") from None
        try:
            answer = data["message"]["content"] if self.provider == "ollama" else data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise AIProviderError("A resposta não contém texto no formato esperado.") from None
        if not isinstance(answer, str) or not answer.strip():
            raise AIProviderError("O provedor retornou uma resposta vazia.")
        return answer.strip()
