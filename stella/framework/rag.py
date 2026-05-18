"""RAGClient — contrato para clientes de corpora RAG.

Implementacao concreta (vetorial) vem quando Sub-projeto F (Web Research)
ou H (Notes Insights) demandar. FB-M4 so define o contrato — quem implementa
escolhe stack (Chroma, Qdrant, etc).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class RAGClient(ABC):
    """Contrato minimo de cliente RAG."""

    @abstractmethod
    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Busca semantica no corpus. Devolve top-k documentos como dicts."""
        ...
