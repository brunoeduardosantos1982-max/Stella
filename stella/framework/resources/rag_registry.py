"""RAGRegistry — indice in-memory de corpora RAG por nome.

FB-M4: tipos estreitados para RAGClient (ABC em framework/rag.py). list_all()
devolve apenas os NOMES registrados (interface estavel mesmo com cliente
evoluindo).
"""

from __future__ import annotations

from stella.framework.errors import RAGNotFoundError
from stella.framework.rag import RAGClient


class RAGRegistry:
    """Indice de corpora RAG para injecao em agentes via builder."""

    def __init__(self) -> None:
        self._por_nome: dict[str, RAGClient] = {}

    def register(self, nome: str, cliente: RAGClient) -> None:
        self._por_nome[nome] = cliente

    def get(self, nome: str) -> RAGClient:
        if nome not in self._por_nome:
            raise RAGNotFoundError(f"RAG corpus '{nome}' nao registrado")
        return self._por_nome[nome]

    def list_all(self) -> list[str]:
        return list(self._por_nome.keys())
