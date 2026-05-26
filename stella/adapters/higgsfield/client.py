"""HttpHiggsFieldClient — chama a API REST Higgsfield Soul ID."""

from __future__ import annotations

import time
from typing import Any

import httpx

from stella.adapters.higgsfield.base import HiggsFieldError

_BASE_URL = "https://api.higgsfield.ai/v1"
_POLL_INTERVAL_S = 2
_POLL_MAX_ATTEMPTS = 30  # 60s total


class HttpHiggsFieldClient:
    """Cliente HTTP para a API Higgsfield.

    Args:
        token: Bearer token da conta Higgsfield.
        soul_id: ID do perfil Soul ID (opcional).
        _transport: Injetável para testes (httpx.MockTransport).
    """

    def __init__(
        self,
        token: str,
        soul_id: str | None = None,
        _transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._headers = {"Authorization": f"Bearer {token}"}
        self._soul_id = soul_id
        self._client = httpx.Client(transport=_transport, timeout=30)

    def generate_image(self, prompt: str, soul_id: str | None = None) -> str:
        """Submete geração e faz polling até completar. Retorna URL da imagem."""
        payload: dict[str, Any] = {"prompt": prompt}
        sid = soul_id or self._soul_id
        if sid:
            payload["soul_id"] = sid

        try:
            r = self._client.post(
                f"{_BASE_URL}/images/generate", json=payload, headers=self._headers
            )
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HiggsFieldError(
                f"Higgsfield HTTP {e.response.status_code}: {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise HiggsFieldError(f"Higgsfield conexão falhou: {e}") from e

        job_id: str = r.json()["job_id"]
        return self._aguardar(job_id)

    def _aguardar(self, job_id: str) -> str:
        for _ in range(_POLL_MAX_ATTEMPTS):
            time.sleep(_POLL_INTERVAL_S)
            try:
                r = self._client.get(f"{_BASE_URL}/jobs/{job_id}", headers=self._headers)
                r.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise HiggsFieldError(f"Higgsfield polling HTTP {e.response.status_code}") from e

            data = r.json()
            status = data.get("status", "")
            if status == "completed":
                return str(data["image_url"])
            if status == "failed":
                raise HiggsFieldError(f"Higgsfield geração falhou: {data.get('error', 'unknown')}")

        raise HiggsFieldError(
            f"Higgsfield job {job_id} não completou em {_POLL_MAX_ATTEMPTS * _POLL_INTERVAL_S}s"
        )
