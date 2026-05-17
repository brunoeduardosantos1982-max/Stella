"""Clients que executam agentes — abstrai diferença in-process vs HTTP.

A Stella (e Coordenadores) sempre chamam `AgentClient.execute(...)` sem
saber se é um Agent local ou um POST para servidor remoto. Decisão #3.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from stella.framework.agent import Agent, AgentOutput
from stella.framework.errors import AgentExecutionError
from stella.framework.manifest import AgentManifest


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
