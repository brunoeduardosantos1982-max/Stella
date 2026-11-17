import json
import subprocess
from typing import Any

import pytest

from stella.adapters.llm.base import LLMProvider, LLMProviderError, LLMResponse, Message
from stella.adapters.llm.claude_cli import ClaudeCliProvider, ProvedorComReserva, limpar_json


def _rodar_fake(saida: dict[str, Any] | str, code: int = 0, chamadas: list | None = None):
    def rodar(args, **kwargs):
        if chamadas is not None:
            chamadas.append((args, kwargs))
        stdout = saida if isinstance(saida, str) else json.dumps(saida)
        return subprocess.CompletedProcess(args, code, stdout=stdout, stderr="erro x")

    return rodar


def test_complete_le_result_do_json_e_passa_prompt_pela_stdin():
    chamadas: list = []
    p = ClaudeCliProvider(
        claude_bin="claude",
        rodar=_rodar_fake({"result": "olá", "is_error": False}, chamadas=chamadas),
    )
    r = p.complete("prompt longo")
    assert r.texto == "olá"
    args, kwargs = chamadas[0]
    assert "prompt longo" not in args  # vai pela stdin, não pela linha de comando
    assert kwargs["input"].startswith("prompt longo")
    assert "--output-format" in args and "json" in args
    assert "--strict-mcp-config" in args


def test_schema_vira_instrucao_e_resposta_sai_sem_cerca_de_codigo():
    chamadas: list = []
    p = ClaudeCliProvider(
        claude_bin="claude",
        rodar=_rodar_fake({"result": '```json\n{"itens": []}\n```'}, chamadas=chamadas),
    )
    r = p.complete("cure", schema={"type": "object"})
    assert json.loads(r.texto) == {"itens": []}
    assert "JSON" in chamadas[0][1]["input"]


def test_codigo_de_saida_nao_zero_vira_erro():
    p = ClaudeCliProvider(claude_bin="claude", rodar=_rodar_fake("", code=1))
    with pytest.raises(LLMProviderError):
        p.complete("x")


def test_is_error_no_json_vira_erro():
    p = ClaudeCliProvider(
        claude_bin="claude", rodar=_rodar_fake({"result": "falhou", "is_error": True})
    )
    with pytest.raises(LLMProviderError):
        p.complete("x")


def test_timeout_vira_erro():
    def rodar(args, **kwargs):
        raise subprocess.TimeoutExpired(args, 1)

    p = ClaudeCliProvider(claude_bin="claude", rodar=rodar)
    with pytest.raises(LLMProviderError):
        p.complete("x")


def test_chat_junta_system_e_mensagens():
    chamadas: list = []
    p = ClaudeCliProvider(
        claude_bin="claude", rodar=_rodar_fake({"result": "ok"}, chamadas=chamadas)
    )
    p.chat([Message("system", "regra"), Message("user", "pergunta")])
    entrada = chamadas[0][1]["input"]
    assert "regra" in entrada and "pergunta" in entrada


def test_limpar_json_preserva_json_puro():
    assert limpar_json('{"a": 1}') == '{"a": 1}'
    assert limpar_json("```\n[1]\n```") == "[1]"


class _Falha(LLMProvider):
    def complete(self, prompt, schema=None):
        raise LLMProviderError("sem crédito")

    def chat(self, messages, schema=None):
        raise LLMProviderError("sem crédito")


class _Ok(LLMProvider):
    def __init__(self) -> None:
        self.chamado = False

    def complete(self, prompt, schema=None):
        self.chamado = True
        return LLMResponse(texto="reserva")

    def chat(self, messages, schema=None):
        return LLMResponse(texto="reserva")


def test_reserva_assume_quando_o_principal_falha():
    ok = _Ok()
    p = ProvedorComReserva([_Falha(), ok])
    assert p.complete("x").texto == "reserva"
    assert ok.chamado
    assert "sem crédito" in p.falhas[0]


def test_reserva_nao_e_chamada_quando_o_principal_responde():
    reserva = _Ok()
    principal = _Ok()
    ProvedorComReserva([principal, reserva]).complete("x")
    assert principal.chamado and not reserva.chamado


def test_todos_falham_levanta_com_todos_os_motivos():
    with pytest.raises(LLMProviderError, match="sem crédito"):
        ProvedorComReserva([_Falha(), _Falha()]).complete("x")
