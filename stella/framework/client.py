"""Clients que executam agentes, escondendo in-process vs HTTP.

A Stella e coordenadores chamam sempre `AgentClient.execute(...)`. O client
garante a fronteira do contrato: payload validado, timeout, erro traduzido e
retorno convertido para `AgentOutput`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from stella.framework.agent import Agent, AgentOutput
from stella.framework.errors import (
    AgentExecutionError,
    AgentInputError,
    AgentTimeoutError,
    AgentUnavailableError,
)
from stella.framework.manifest import AgentManifest

_HEALTH_CHECK_TIMEOUT_S = 5.0


class AgentClient(ABC):
    """Contrato comum para chamar um agente."""

    @abstractmethod
    def execute(self, payload: dict[str, Any]) -> AgentOutput:
        """Executa o agente com o payload e devolve o output."""
        ...

    @abstractmethod
    def manifest(self) -> AgentManifest:
        """Devolve o manifest do agente para introspeccao."""
        ...


class InProcessClient(AgentClient):
    """Wrappa um `Agent` local e isola excecoes brutas."""

    def __init__(self, agent: Agent, manifest: AgentManifest) -> None:
        self._agent = agent
        self._manifest = manifest

    def execute(self, payload: dict[str, Any]) -> AgentOutput:
        try:
            return self._agent.execute(payload)
        except Exception as e:
            raise AgentExecutionError(
                f"Agent '{self._manifest.nome}' falhou em execute(): {e}"
            ) from e

    def manifest(self) -> AgentManifest:
        return self._manifest


class HttpAgentClient(AgentClient):
    """Agente remoto via HTTP POST.

    Contrato esperado no servidor remoto:
    - `GET /api/health`
    - `POST /api/execute`
    - resposta JSON: `resultado`, `sucesso`, `mensagens`, `custo_estimado_usd`
    """

    def __init__(
        self,
        manifest: AgentManifest,
        httpx_client: httpx.Client | None = None,
    ) -> None:
        if manifest.execucao != "http":
            raise ValueError(
                f"HttpAgentClient requer manifest.execucao='http', recebeu '{manifest.execucao}'"
            )
        if not manifest.endpoint:
            raise ValueError(
                f"HttpAgentClient requer manifest.endpoint preenchido (nome={manifest.nome})"
            )
        self._manifest = manifest
        self._http = httpx_client or httpx.Client()

    def execute(self, payload: dict[str, Any]) -> AgentOutput:
        self._validate_payload(payload)
        self._health_check()
        try:
            resp = self._http.post(
                f"{self._manifest.endpoint}/api/execute",
                json=payload,
                timeout=self._manifest.timeout_s,
            )
            resp.raise_for_status()
            body = resp.json()
        except httpx.TimeoutException as e:
            raise AgentTimeoutError(
                f"Agent HTTP '{self._manifest.nome}' nao respondeu em "
                f"{self._manifest.timeout_s}s - timeout."
            ) from e
        except httpx.HTTPError as e:
            raise AgentExecutionError(
                f"Agent HTTP '{self._manifest.nome}' devolveu erro: {e}"
            ) from e
        except ValueError as e:
            raise AgentExecutionError(
                f"Agent HTTP '{self._manifest.nome}' devolveu JSON invalido: {e}"
            ) from e

        if not isinstance(body, dict):
            raise AgentExecutionError(
                f"Agent HTTP '{self._manifest.nome}' devolveu {type(body).__name__}; "
                "esperado objeto JSON com resultado/sucesso/mensagens."
            )

        return AgentOutput(
            resultado=self._coerce_resultado(body),
            sucesso=bool(body.get("sucesso", True)),
            mensagens=self._coerce_mensagens(body),
            custo_estimado_usd=float(body.get("custo_estimado_usd", 0.0) or 0.0),
        )

    def manifest(self) -> AgentManifest:
        return self._manifest

    def _health_check(self) -> None:
        try:
            resp = self._http.get(
                f"{self._manifest.endpoint}/api/health",
                timeout=_HEALTH_CHECK_TIMEOUT_S,
            )
            if resp.status_code >= 400:
                raise AgentUnavailableError(
                    f"Agent HTTP '{self._manifest.nome}' offline "
                    f"({self._manifest.endpoint}): HTTP {resp.status_code}"
                )
        except httpx.HTTPError as e:
            raise AgentUnavailableError(
                f"Agent HTTP '{self._manifest.nome}' offline ({self._manifest.endpoint}): {e}"
            ) from e

    def _validate_payload(self, payload: dict[str, Any]) -> None:
        faltando = [campo for campo in self._manifest.inputs_obrigatorios if campo not in payload]
        if faltando:
            raise AgentInputError(
                f"Payload para '{self._manifest.nome}' sem campo(s) obrigatorio(s): "
                f"{', '.join(faltando)}"
            )

    def _coerce_resultado(self, body: dict[str, Any]) -> dict[str, Any]:
        resultado = body.get("resultado", {})
        if not isinstance(resultado, dict):
            raise AgentExecutionError(
                f"Agent HTTP '{self._manifest.nome}' devolveu 'resultado' "
                f"como {type(resultado).__name__}; esperado dict."
            )
        return resultado

    def _coerce_mensagens(self, body: dict[str, Any]) -> list[str]:
        mensagens = body.get("mensagens", [])
        if isinstance(mensagens, str):
            return [mensagens]
        if not isinstance(mensagens, list):
            raise AgentExecutionError(
                f"Agent HTTP '{self._manifest.nome}' devolveu 'mensagens' "
                f"como {type(mensagens).__name__}; esperado list[str]."
            )
        return [str(m) for m in mensagens]
