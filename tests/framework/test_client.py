from dataclasses import dataclass

import httpx
import pytest

from stella.framework.agent import Agent, AgentOutput
from stella.framework.client import AgentClient, HttpAgentClient, InProcessClient
from stella.framework.errors import (
    AgentExecutionError,
    AgentTimeoutError,
    AgentUnavailableError,
)
from stella.framework.manifest import AgentManifest, CapacidadesExternas


def test_agent_client_e_abstrato() -> None:
    with pytest.raises(TypeError):
        AgentClient()  # type: ignore[abstract]


def _manifest_dummy() -> AgentManifest:
    return AgentManifest(
        nome="dummy",
        tipo="especialista",
        setor="testes",
        descricao="agente para testes do framework",
        execucao="in_process",
        modelo_minimo="gemma",
        inputs_obrigatorios=[],
        exemplo_uso={},
        quando_usar="apenas em testes — não use em produção",
        capacidades_externas=CapacidadesExternas(),
    )


class _AgenteEcho(Agent):
    """Devolve o que recebe — usado para validar o pipeline do client."""

    def execute(self, input: dict) -> AgentOutput:
        return AgentOutput(resultado={"echo": input})


class _AgenteQueExplode(Agent):
    """Sempre levanta exceção — para testar isolamento do client."""

    def execute(self, input: dict) -> AgentOutput:
        raise ZeroDivisionError("falha de propósito")


def test_inprocess_client_chama_execute_do_agente() -> None:
    c = InProcessClient(agent=_AgenteEcho(), manifest=_manifest_dummy())
    out = c.execute({"x": 1})
    assert out.resultado == {"echo": {"x": 1}}


def test_inprocess_client_devolve_manifest() -> None:
    m = _manifest_dummy()
    c = InProcessClient(agent=_AgenteEcho(), manifest=m)
    assert c.manifest() is m


def test_inprocess_client_encapsula_exception_em_agent_execution_error() -> None:
    c = InProcessClient(agent=_AgenteQueExplode(), manifest=_manifest_dummy())
    with pytest.raises(AgentExecutionError, match="falha de propósito"):
        c.execute({})


def _manifest_http() -> AgentManifest:
    return AgentManifest(
        nome="coord_ecommerce_aspargus",
        tipo="coordenador",
        setor="ecommerce",
        descricao="adapter HTTP para o Aspargus existente",
        execucao="http",
        endpoint="http://localhost:8000",
        modelo_minimo="sonnet",
        inputs_obrigatorios=["acao"],
        exemplo_uso={"acao": "analise_margem_semanal"},
        quando_usar="qualquer tarefa relacionada a Amazon Aspargus Store",
        capacidades_externas=CapacidadesExternas(),
    )


# --- Dublê do httpx.Client para testes sem rede ---


@dataclass
class _FakeResponse:
    status_code: int
    _body: dict

    def json(self) -> dict:
        return self._body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=None,  # type: ignore[arg-type]
                response=None,  # type: ignore[arg-type]
            )


class _FakeHttpxClient:
    """Substitui httpx.Client em testes — responde conforme programado."""

    def __init__(
        self,
        health_status: int = 200,
        execute_status: int = 200,
        execute_body: dict | None = None,
        raise_on_execute: Exception | None = None,
    ) -> None:
        self._health_status = health_status
        self._execute_status = execute_status
        self._execute_body = execute_body or {"resultado": {"ok": True}, "sucesso": True}
        self._raise_on_execute = raise_on_execute
        self.calls: list[tuple[str, str, dict | None]] = []

    def get(self, url: str, timeout: float | None = None) -> _FakeResponse:
        self.calls.append(("GET", url, None))
        return _FakeResponse(self._health_status, {})

    def post(self, url: str, json: dict, timeout: float | None = None) -> _FakeResponse:
        self.calls.append(("POST", url, json))
        if self._raise_on_execute is not None:
            raise self._raise_on_execute
        return _FakeResponse(self._execute_status, self._execute_body)


def test_http_client_executa_post_quando_health_ok() -> None:
    fake = _FakeHttpxClient(execute_body={"resultado": {"copy": "ok"}, "sucesso": True})
    c = HttpAgentClient(manifest=_manifest_http(), httpx_client=fake)  # type: ignore[arg-type]
    out = c.execute({"acao": "analise_margem"})
    assert out.resultado == {"copy": "ok"}
    assert any(call[0] == "GET" for call in fake.calls), "health_check deve ter sido chamado"
    assert any(call[0] == "POST" for call in fake.calls), "execute deve ter sido chamado"


def test_http_client_levanta_unavailable_quando_health_falha() -> None:
    fake = _FakeHttpxClient(health_status=503)
    c = HttpAgentClient(manifest=_manifest_http(), httpx_client=fake)  # type: ignore[arg-type]
    with pytest.raises(AgentUnavailableError, match="coord_ecommerce_aspargus"):
        c.execute({"acao": "x"})


def test_http_client_levanta_timeout_quando_httpx_levanta_timeout() -> None:
    fake = _FakeHttpxClient(raise_on_execute=httpx.TimeoutException("timeout"))
    c = HttpAgentClient(manifest=_manifest_http(), httpx_client=fake)  # type: ignore[arg-type]
    with pytest.raises(AgentTimeoutError):
        c.execute({"acao": "x"})


def test_http_client_devolve_manifest() -> None:
    m = _manifest_http()
    fake = _FakeHttpxClient()
    c = HttpAgentClient(manifest=m, httpx_client=fake)  # type: ignore[arg-type]
    assert c.manifest() is m
