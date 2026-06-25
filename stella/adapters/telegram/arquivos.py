"""Envio de arquivos ao Telegram (sendDocument/sendPhoto). `http_post` é injetável
para teste, no mesmo espírito do send_voice do daemon."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx


def _url(token: str, metodo: str) -> str:
    return f"https://api.telegram.org/bot{token}/{metodo}"


def _enviar(
    metodo: str,
    campo: str,
    token: str,
    chat_id: str,
    caminho: Path,
    legenda: str | None,
    http_post: Callable[..., Any],
) -> None:
    data = {"chat_id": chat_id}
    if legenda:
        data["caption"] = legenda
    with caminho.open("rb") as fh:
        resp = http_post(
            _url(token, metodo), data=data, files={campo: (caminho.name, fh)}, timeout=120
        )
    resp.raise_for_status()


def enviar_documento(
    token: str,
    chat_id: str,
    caminho: Path,
    *,
    legenda: str | None = None,
    http_post: Callable[..., Any] = httpx.post,
) -> None:
    _enviar("sendDocument", "document", token, chat_id, caminho, legenda, http_post)


def enviar_foto(
    token: str,
    chat_id: str,
    caminho: Path,
    *,
    legenda: str | None = None,
    http_post: Callable[..., Any] = httpx.post,
) -> None:
    _enviar("sendPhoto", "photo", token, chat_id, caminho, legenda, http_post)
