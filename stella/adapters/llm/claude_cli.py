"""Provedor que roda o `claude -p` (assinatura do Claude Code, sem crédito de API).

Nasceu em 2026-11-17: a conta da API da Anthropic está sem crédito desde 01/10 e a
chave da NVIDIA (Gemma) foi revogada (403). Radar e Bolsa ficaram sem curadoria.
O `claude -p` usa a assinatura do Claude Code, a mesma que o daemon já usa.

`ProvedorComReserva` tenta os provedores em ordem: quando a API volta a ter
crédito, ela é usada; enquanto não tiver, o CLI assume sem ninguém mexer.
"""

import json
import re
import shutil
import subprocess
from collections.abc import Callable
from typing import Any

from stella.adapters.llm.base import LLMProvider, LLMProviderError, LLMResponse, Message

_TIMEOUT_S = 300
_CERCA = re.compile(r"^\s*```[a-zA-Z]*\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)


def limpar_json(texto: str) -> str:
    """Tira a cerca ```json ... ``` que o modelo às vezes põe em volta do JSON."""
    m = _CERCA.match(texto)
    return (m.group(1) if m else texto).strip()


class ClaudeCliProvider(LLMProvider):
    """Roda `claude -p` com o prompt pela entrada padrão.

    O prompt vai pela stdin, não pela linha de comando: o `claude` do npm é um
    shim `.cmd` e o cmd.exe corta argumentos acima de ~8 mil caracteres.
    """

    def __init__(
        self,
        modelo: str = "sonnet",
        claude_bin: str | None = None,
        timeout_s: int = _TIMEOUT_S,
        rodar: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self._modelo = modelo
        self._bin = claude_bin or shutil.which("claude") or "claude"
        self._timeout = timeout_s
        self._rodar = rodar

    def complete(self, prompt: str, schema: dict[str, Any] | None = None) -> LLMResponse:
        return self.chat([Message(role="user", content=prompt)], schema=schema)

    def chat(self, messages: list[Message], schema: dict[str, Any] | None = None) -> LLMResponse:
        partes = [m.content for m in messages]
        if schema is not None:
            partes.append(
                "Responda SOMENTE com JSON válido, sem texto antes ou depois e sem "
                "cerca de código, seguindo este JSON Schema:\n"
                + json.dumps(schema, ensure_ascii=False)
            )
        entrada = "\n\n".join(partes)
        args = [
            self._bin,
            "-p",
            "--model",
            self._modelo,
            "--output-format",
            "json",
            "--strict-mcp-config",
        ]
        try:
            r = self._rodar(
                args,
                input=entrada,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=self._timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise LLMProviderError(f"claude -p passou de {self._timeout}s") from e
        except OSError as e:
            raise LLMProviderError(f"claude -p não executou: {e}") from e
        if r.returncode != 0:
            raise LLMProviderError(f"claude -p saiu com {r.returncode}: {(r.stderr or '')[:300]}")
        try:
            dados = json.loads(r.stdout)
        except json.JSONDecodeError as e:
            raise LLMProviderError(f"claude -p devolveu saída não-JSON: {r.stdout[:200]}") from e
        texto = dados.get("result") if isinstance(dados, dict) else None
        if not isinstance(texto, str) or dados.get("is_error"):
            raise LLMProviderError(f"claude -p devolveu erro: {str(texto)[:300]}")
        if schema is not None:
            texto = limpar_json(texto)
        return LLMResponse(texto=texto)


class ProvedorComReserva(LLMProvider):
    """Tenta cada provedor em ordem; o primeiro que responder vence.

    `falhas` guarda o motivo de cada provedor que caiu na última chamada.
    """

    def __init__(self, provedores: list[LLMProvider]) -> None:
        if not provedores:
            raise ValueError("ProvedorComReserva precisa de pelo menos um provedor")
        self._provedores = provedores
        self.falhas: list[str] = []

    def _tentar(self, chamar: Callable[[LLMProvider], LLMResponse]) -> LLMResponse:
        self.falhas = []
        for p in self._provedores:
            try:
                return chamar(p)
            except Exception as e:  # noqa: BLE001 - qualquer falha passa para a reserva
                self.falhas.append(f"{type(p).__name__}: {e}")
        raise LLMProviderError("todos os provedores falharam: " + " | ".join(self.falhas))

    def complete(self, prompt: str, schema: dict[str, Any] | None = None) -> LLMResponse:
        return self._tentar(lambda p: p.complete(prompt, schema=schema))

    def chat(self, messages: list[Message], schema: dict[str, Any] | None = None) -> LLMResponse:
        return self._tentar(lambda p: p.chat(messages, schema=schema))  # type: ignore[call-arg]
