"""Contrato do adapter Postiz — dataclasses, Protocol e exceção.

Arquivo puro: sem rede, sem httpx. `client.py` (real) e `fake.py` (teste)
implementam `PostizClientProtocol`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class PostizError(Exception):
    """Falha ao comunicar com a API do Postiz (rede, auth, HTTP 4xx/5xx)."""


@dataclass
class PostizMidia:
    """Imagem já enviada ao Postiz — resultado de `upload_imagem`."""

    id: str
    path: str


@dataclass
class PostizAgendamento:
    """Pedido de agendamento de um post numa rede social."""

    canal_id: str
    conteudo: str
    data_utc: str
    plataforma: str = "instagram"
    post_type: str = "post"
    midias: list[PostizMidia] = field(default_factory=list)


@dataclass
class PostizResultado:
    """Resultado de um agendamento bem-sucedido.

    Falhas levantam `PostizError` — quando um `PostizResultado` é devolvido,
    o agendamento deu certo.
    """

    post_url: str | None = None


class PostizClientProtocol(Protocol):
    """Contrato comum ao cliente real e ao fake.

    Ambos os métodos levantam `PostizError` em qualquer falha.
    """

    def upload_imagem(self, dados: bytes, nome_arquivo: str) -> PostizMidia: ...

    def agendar_post(self, agendamento: PostizAgendamento) -> PostizResultado: ...
