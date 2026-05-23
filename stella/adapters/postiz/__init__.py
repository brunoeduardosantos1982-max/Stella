"""Adapter Postiz — publicação em redes sociais via API REST."""

from stella.adapters.postiz.base import (
    PostizAgendamento,
    PostizClientProtocol,
    PostizError,
    PostizMidia,
    PostizResultado,
)
from stella.adapters.postiz.client import HttpPostizClient
from stella.adapters.postiz.fake import FakePostiz

__all__ = [
    "FakePostiz",
    "HttpPostizClient",
    "PostizAgendamento",
    "PostizClientProtocol",
    "PostizError",
    "PostizMidia",
    "PostizResultado",
]
