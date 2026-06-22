"""Radar de Tendências — busca agregada de notícias por tema.

Módulo que orquestra a coleta de candidatos (artigos) de múltiplos temas
via Tavily, aplica filtros de domínio e deduplica por URL.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta, timezone
from typing import Any

from stella.adapters.research.tavily_client import buscar_noticias_tavily

FUSO = timezone(timedelta(hours=-3))

# 4 nichos + 6 subnichos = queries de busca
TEMAS: list[str] = [
    "marketing",
    "inteligência artificial",
    "tecnologia",
    "publicidade",
    "personal branding",
    "viagens",
    "negócios",
    "marketing digital",
    "performance marketing",
    "criação de conteúdo",
]

# Allowlist curada (híbrido A+B). Ajustável.
ALLOWLIST_DOMINIOS: list[str] = [
    "techcrunch.com",
    "theverge.com",
    "arstechnica.com",
    "venturebeat.com",
    "technologyreview.com",
    "searchengineland.com",
    "searchenginejournal.com",
    "marketingdive.com",
    "adweek.com",
    "socialmediatoday.com",
    "contentmarketinginstitute.com",
    "blog.hubspot.com",
    "buffer.com",
    "hbr.org",
    "fastcompany.com",
    "skift.com",
]

JANELA_DIAS = 2


@dataclass
class Candidato:
    """Representação de um artigo candidato para o radar."""

    titulo: str
    url: str
    veiculo: str
    snippet: str
    data: str
    tema: str


def buscar_candidatos(
    temas: list[str] = TEMAS,
    *,
    api_key: str,
    days: int = JANELA_DIAS,
    include_domains: list[str] | None = ALLOWLIST_DOMINIOS,
    buscar: Callable[..., list[dict[str, Any]]] = buscar_noticias_tavily,
) -> list[Candidato]:
    """Busca notícias por tema, agrega e deduplica por URL.

    Args:
        temas: Lista de tópicos para buscar.
        api_key: Chave de API do Tavily.
        days: Janela de dias para buscar notícias.
        include_domains: Allowlist de domínios a priorizar.
        buscar: Callable que executa a busca (injetável para testes).

    Returns:
        Lista de Candidato deduplicada por URL, preservando tema.
    """
    vistos: set[str] = set()
    candidatos: list[Candidato] = []
    for tema in temas:
        try:
            brutos = buscar(
                tema,
                api_key=api_key,
                days=days,
                include_domains=include_domains,
            )
        except Exception:
            continue  # um tema que falha não derruba os outros
        for r in brutos:
            url = r.get("url", "")
            if not url or url in vistos:
                continue
            vistos.add(url)
            candidatos.append(
                Candidato(
                    titulo=r.get("titulo", ""),
                    url=url,
                    veiculo=r.get("veiculo", ""),
                    snippet=r.get("snippet", ""),
                    data=r.get("data", ""),
                    tema=tema,
                )
            )
    return candidatos
