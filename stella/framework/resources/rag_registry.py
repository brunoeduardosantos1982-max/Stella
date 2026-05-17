"""RAGRegistry — indice in-memory de corpora RAG por nome.

Stub minimal em FB-M2: tipo do cliente RAG e `object` (concreto entra em
milestone futuro com adapter vetorial real). list_all() devolve apenas os
NOMES registrados (interface estavel mesmo com tipo do cliente evoluindo).
"""

from __future__ import annotations

from stella.framework.errors import RAGNotFoundError


class RAGRegistry:
    """Indice de corpora RAG para injecao em agentes via builder."""

    def __init__(self) -> None:
        self._por_nome: dict[str, object] = {}

    def register(self, nome: str, cliente: object) -> None:
        self._por_nome[nome] = cliente

    def get(self, nome: str) -> object:
        if nome not in self._por_nome:
            raise RAGNotFoundError(f"RAG corpus '{nome}' nao registrado")
        return self._por_nome[nome]

    def list_all(self) -> list[str]:
        return list(self._por_nome.keys())
