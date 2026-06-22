from typing import Any

import httpx
import pytest

from stella.adapters.research.tavily_client import buscar_noticias_tavily


class _RespFake:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:  # pragma: no cover - sem erro no teste
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


def test_buscar_noticias_mapeia_campos_e_extrai_veiculo() -> None:
    chamada: dict[str, Any] = {}

    def http_post_fake(url: str, **kwargs: Any) -> _RespFake:
        chamada["url"] = url
        chamada["json"] = kwargs["json"]
        return _RespFake(
            {
                "results": [
                    {
                        "title": "OpenAI lança agente",
                        "url": "https://techcrunch.com/2026/06/21/openai-agent",
                        "content": "resumo aqui",
                        "published_date": "2026-06-21",
                    }
                ]
            }
        )

    out = buscar_noticias_tavily(
        "inteligência artificial novidades",
        api_key="k",
        days=1,
        max_results=5,
        include_domains=["techcrunch.com"],
        http_post=http_post_fake,
    )

    assert chamada["json"]["topic"] == "news"
    assert chamada["json"]["days"] == 1
    assert chamada["json"]["include_domains"] == ["techcrunch.com"]
    assert out == [
        {
            "titulo": "OpenAI lança agente",
            "url": "https://techcrunch.com/2026/06/21/openai-agent",
            "veiculo": "techcrunch.com",
            "snippet": "resumo aqui",
            "data": "2026-06-21",
        }
    ]


def test_buscar_noticias_propaga_http_error() -> None:
    """Garante que erros HTTP (ex: 401/429) propagam para o caller."""

    def http_post_erro(url: str, **kwargs: Any) -> Any:
        req = httpx.Request("POST", url)
        resp = httpx.Response(429, request=req)
        raise httpx.HTTPStatusError("429 Too Many Requests", request=req, response=resp)

    with pytest.raises(httpx.HTTPStatusError):
        buscar_noticias_tavily("ia", api_key="k", http_post=http_post_erro)
