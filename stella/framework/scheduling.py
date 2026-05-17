"""HOOK Sub-projeto E — BackgroundScheduler para tempo livre da Stella.

Interface vazia: implementacao real (cron interno, fila persistente,
prioridades dinamicas) vem no Sub-projeto E. Aqui apenas garantimos que o
framework reconhece o conceito para que outros componentes (ex: agentes que
querem agendar trabalho de fundo) possam tipar contra esta interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class IdleTask:
    """Tarefa de baixa prioridade que roda quando Stella esta ociosa.

    Atributos:
        nome: descricao curta.
        prioridade: 1-10 (10 = mais alta). Sub-projeto E define o sort.
        agente_alvo: nome do agente que vai executar.
        payload: dict passado para Agent.execute() do agente alvo.
    """

    nome: str
    prioridade: int
    agente_alvo: str
    payload: dict[str, Any]


class BackgroundScheduler(ABC):
    """Interface para tarefas que rodam em tempo livre da Stella."""

    @abstractmethod
    def submit_idle_task(self, task: IdleTask) -> str:
        """Enfileira a tarefa. Devolve um id (string) para tracking."""
        ...

    @abstractmethod
    def list_pending(self) -> list[IdleTask]:
        """Lista tarefas ainda nao executadas, ordenadas conforme politica
        do Sub-projeto E (provavelmente por prioridade decrescente)."""
        ...
