"""HOOK Sub-projeto G — Sandbox: area isolada para testar teorias.

Implementacao real (filesystem snapshot, vault diff, rollback) vem no
Sub-projeto G. Aqui apenas o contrato — Stella e agentes podem rodar
em sandbox sem riscos a producao.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from stella.framework.agent import Agent, AgentOutput


class Sandbox(ABC):
    """Area isolada onde Stella testa hipoteses sem afetar producao."""

    @abstractmethod
    def run_isolated(self, agent: Agent, payload: dict[str, Any]) -> AgentOutput:
        """Roda o agent com o payload em isolamento total do estado real."""
        ...

    @abstractmethod
    def snapshot_state(self) -> dict[str, Any]:
        """Devolve dump do estado interno do sandbox (para auditoria/diff)."""
        ...
