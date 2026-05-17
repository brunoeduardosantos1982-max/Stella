"""Clients que executam agentes — abstrai diferença in-process vs HTTP.

A Stella (e Coordenadores) sempre chamam `AgentClient.execute(...)` sem
saber se é um Agent local ou um POST para servidor remoto. Decisão #3.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from stella.framework.agent import AgentOutput
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
