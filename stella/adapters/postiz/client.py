"""HttpPostizClient — cliente real da API REST do Postiz Cloud.

API: base https://api.postiz.com/public/v1, header `Authorization: <token>`.
Endpoints usados: POST /upload (multipart) e POST /posts (JSON).
Qualquer falha (rede, HTTP 4xx/5xx, resposta malformada) vira `PostizError`.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from stella.adapters.postiz.base import (
    PostizAgendamento,
    PostizError,
    PostizMidia,
    PostizResultado,
)

_API_BASE_PADRAO = "https://api.postiz.com/public/v1"
_TIMEOUT_S = 30.0

_logger = logging.getLogger(__name__)


class HttpPostizClient:
    """Cliente HTTP do Postiz. Levanta `PostizError` em qualquer falha."""

    def __init__(
        self,
        token: str,
        api_base: str = _API_BASE_PADRAO,
        http: httpx.Client | None = None,
    ) -> None:
        if not token:
            raise PostizError("token do Postiz vazio — configure STELLA_POSTIZ_TOKEN no .env")
        self._token = token
        self._api_base = api_base.rstrip("/")
        self._http = http or httpx.Client(timeout=_TIMEOUT_S)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": self._token}

    def upload_imagem(self, dados: bytes, nome_arquivo: str) -> PostizMidia:
        try:
            resp = self._http.post(
                f"{self._api_base}/upload",
                headers=self._headers(),
                files={"file": (nome_arquivo, dados)},
            )
            resp.raise_for_status()
            body: Any = resp.json()
        except httpx.HTTPStatusError as e:
            raise PostizError(
                f"falha ao enviar imagem '{nome_arquivo}' ao Postiz: {e} — body: {e.response.text}"
            ) from e
        except httpx.HTTPError as e:
            raise PostizError(f"falha ao enviar imagem '{nome_arquivo}' ao Postiz: {e}") from e
        if not isinstance(body, dict) or "id" not in body or "path" not in body:
            raise PostizError(f"resposta de upload do Postiz sem 'id'/'path': {body}")
        return PostizMidia(id=str(body["id"]), path=str(body["path"]))

    def agendar_post(self, agendamento: PostizAgendamento) -> PostizResultado:
        payload = {
            "type": "schedule",
            "date": agendamento.data_utc,
            "shortLink": False,
            "tags": [],
            "posts": [
                {
                    "integration": {"id": agendamento.canal_id},
                    "value": [
                        {
                            "content": agendamento.conteudo,
                            "image": [{"id": m.id, "path": m.path} for m in agendamento.midias],
                        }
                    ],
                    "settings": {
                        "__type": agendamento.plataforma,
                        "post_type": agendamento.post_type,
                    },
                }
            ],
        }
        try:
            resp = self._http.post(
                f"{self._api_base}/posts",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            body: Any = resp.json()
        except httpx.HTTPStatusError as e:
            raise PostizError(
                f"falha ao agendar post no Postiz: {e} — body: {e.response.text}"
            ) from e
        except httpx.HTTPError as e:
            raise PostizError(f"falha ao agendar post no Postiz: {e}") from e
        # Log do body completo da resposta — ajuda a evoluir _extrair_post_url
        # conforme aprendemos o formato real (a doc pública do Postiz não documenta).
        _logger.info("Postiz POST /posts resposta: %s", body)
        return PostizResultado(post_url=_extrair_post_url(body))


def _extrair_post_url(body: Any) -> str | None:
    """Extrai uma referência do post da resposta do Postiz.

    Prioridade: `releaseURL` (URL pública no Instagram/etc, preenchida após
    publicação) → `postUrl`/`url` (variações) → `id` (ID interno do Postiz,
    fallback para posts ainda em fila/agendados).
    """
    if isinstance(body, list) and body:
        body = body[0]
    if isinstance(body, dict):
        for chave in ("releaseURL", "postUrl", "url", "id"):
            valor = body.get(chave)
            if valor:
                return str(valor)
    return None
