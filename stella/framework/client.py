"""Clients que executam agentes — abstrai diferença in-process vs HTTP.

A Stella (e Coordenadores) sempre chamam `AgentClient.execute(...)` sem
saber se é um Agent local ou um POST para servidor remoto. Decisão #3.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from stella.framework.agent import Agent, AgentOutput
from stella.framework.errors import (
    AgentExecutionError,
    AgentTimeoutError,
    AgentUnavailableError,
)
from stella.framework.manifest import AgentManifest

# Defaults conservadores. Manifest específico pode estender.
_HEALTH_CHECK_TIMEOUT_S = 5.0
_EXECUTE_TIMEOUT_S = 300.0  # 5 min — Aspargus pode ser lento


class AgentClient(ABC):
    """Contrato comum para chamar um agente.

    Tem duas implementações:
    - InProcessClient: wrappa uma instância de Agent local
    - HttpAgentClient: POST para servidor remoto (ex: Aspargus)
    """

    @abstractmethod
    def execute(self, payload: dict[str, Any]) -> AgentOutput:
        """Executa o agente com o payload e devolve o output."""
        ...

    @abstractmethod
    def manifest(self) -> AgentManifest:
        """Devolve o manifest do agente (para introspecção)."""
        ...


class InProcessClient(AgentClient):
    """Wrappa um `Agent` que roda no mesmo processo Python da Stella.

    A maioria dos agentes do Sistema Multi-Agente é in-process (decisão #3 —
    híbrido transparente; HTTP fica reservado para integrações externas
    como o Aspargus).

    Encapsula exceções do agent em `AgentExecutionError` — protege a Stella
    de erros brutos do agente subir pela stack.
    """

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
    """Agente remoto via HTTP POST. Usado para integrar sistemas externos
    como o Aspargus (que roda em http://localhost:8000).

    Antes do POST, faz health_check no endpoint base. Se falhar, levanta
    AgentUnavailableError com mensagem útil — Stella pode usar isso para
    perguntar ao Bruno se quer iniciar o servidor.

    Timeout total da execução = _EXECUTE_TIMEOUT_S (5 min). Para tarefas
    mais longas, ajustar via manifest no futuro (não escopo de FB-M1).
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
        self._health_check()
        try:
            resp = self._http.post(
                f"{self._manifest.endpoint}/api/execute",
                json=payload,
                timeout=_EXECUTE_TIMEOUT_S,
            )
            resp.raise_for_status()
            body = resp.json()
        except httpx.TimeoutException as e:
            raise AgentTimeoutError(
                f"Agent HTTP '{self._manifest.nome}' não respondeu em "
                f"{_EXECUTE_TIMEOUT_S}s — timeout."
            ) from e
        except httpx.HTTPError as e:
            raise AgentExecutionError(
                f"Agent HTTP '{self._manifest.nome}' devolveu erro: {e}"
            ) from e

        return AgentOutput(
            resultado=body.get("resultado", {}),
            sucesso=body.get("sucesso", True),
            mensagens=body.get("mensagens", []),
            custo_estimado_usd=body.get("custo_estimado_usd", 0.0),
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
