"""Adapter Postiz — publicação em redes sociais via API REST."""

from stella.adapters.postiz.base import (
    PostizAgendamento,
    PostizClientProtocol,
    PostizError,
    PostizMidia,
    PostizResultado,
)

__all__ = [
    "PostizAgendamento",
    "PostizClientProtocol",
    "PostizError",
    "PostizMidia",
    "PostizResultado",
]
