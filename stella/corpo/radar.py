"""Radar de Tendências — busca agregada de notícias por tema.

Módulo que orquestra a coleta de candidatos (artigos) de múltiplos temas
via Tavily, aplica filtros de domínio e deduplica por URL.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from stella.adapters.llm.base import LLMProvider
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


SEEN_PATH = Path("D:/VortexBrain00/.secrets/radar_seen.json")
JANELA_SEEN_DIAS = 7


def carregar_seen(path: Path = SEEN_PATH) -> list[dict[str, str]]:
    """Carrega o log de URLs já vistas do disco.

    Args:
        path: Caminho do arquivo JSON de seen-log.

    Returns:
        Lista de dicts com chaves "url" e "enviado_em", ou [] se arquivo
        não existir ou conteúdo ser inválido.
    """
    try:
        dados = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return dados if isinstance(dados, list) else []


def podar_seen(
    seen: list[dict[str, str]],
    janela_dias: int = JANELA_SEEN_DIAS,
    agora: datetime | None = None,
) -> list[dict[str, str]]:
    """Remove entradas do seen-log que ficaram fora da janela de retenção.

    Args:
        seen: Lista de dicts com "url" e "enviado_em" (ISO 8601).
        janela_dias: Número de dias a reter.
        agora: Data/hora de referência (FUSO). Se None, usa datetime.now(FUSO).

    Returns:
        Lista filtrada contendo apenas entradas dentro da janela.
    """
    ref = (agora or datetime.now(FUSO)) - timedelta(days=janela_dias)
    out: list[dict[str, str]] = []
    for s in seen:
        try:
            quando = datetime.fromisoformat(s["enviado_em"])
            if quando >= ref:
                out.append(s)
        except (KeyError, ValueError, TypeError):
            continue
    return out


def filtrar_novos(candidatos: list[Candidato], seen: list[dict[str, str]]) -> list[Candidato]:
    """Filtra candidatos removendo URLs já presentes no seen-log.

    Args:
        candidatos: Lista de Candidato.
        seen: Lista de dicts com chaves "url" e "enviado_em".

    Returns:
        Sublista de candidatos cujas URLs não estão em seen.
    """
    urls_vistas = {s.get("url") for s in seen}
    return [c for c in candidatos if c.url not in urls_vistas]


def gravar_seen(
    seen: list[dict[str, str]],
    urls: list[str],
    path: Path = SEEN_PATH,
    agora: datetime | None = None,
) -> None:
    """Grava URLs novas no seen-log com timestamp ISO 8601.

    Args:
        seen: Lista atual de dicts "url"/"enviado_em".
        urls: Lista de URLs novas a adicionar.
        path: Arquivo de destino para o JSON.
        agora: Data/hora para registrar (FUSO). Se None, usa datetime.now(FUSO).
    """
    quando = (agora or datetime.now(FUSO)).isoformat()
    atualizado = list(seen) + [{"url": u, "enviado_em": quando} for u in urls]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(atualizado, ensure_ascii=False, indent=2), encoding="utf-8")


@dataclass
class ItemRadar:
    titulo: str
    url: str
    veiculo: str
    resumo: str
    gancho: str


_INSTRUCAO_CURADORIA = (
    "Você é a Stella, assistente de conteúdo do Bruno (consultor de marketing com IA, "
    "com toque lifestyle). Dos candidatos abaixo, escolha os {n} mais frescos e quentes "
    "para virar post hoje. Para cada um devolva: titulo, url e veiculo (copie exatamente "
    "do candidato), resumo (1 a 2 linhas em português) e gancho (um ângulo de post curto "
    "em português, na voz de estrategista). Não use travessão. Responda APENAS um array "
    "JSON com objetos {{titulo, url, veiculo, resumo, gancho}}, sem texto fora do JSON.\n\n"
    "Candidatos:\n{lista}"
)


def montar_prompt_curadoria(candidatos: list[Candidato], n: int) -> str:
    linhas = [
        f"{i}. [{c.tema}] {c.titulo} | {c.veiculo} | {c.url} | {c.snippet}"
        for i, c in enumerate(candidatos, start=1)
    ]
    return _INSTRUCAO_CURADORIA.format(n=n, lista="\n".join(linhas))


def _extrair_json(texto: str) -> Any:
    t = texto.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1]
        t = t.removeprefix("json").strip()
    inicio, fim = t.find("["), t.rfind("]")
    if inicio == -1 or fim == -1:
        raise ValueError("resposta do curador sem array JSON")
    return json.loads(t[inicio : fim + 1])


def curar(candidatos: list[Candidato], n: int, *, provider: LLMProvider) -> list[ItemRadar]:
    """Pede ao LLM os top N com resumo e gancho; devolve no máximo N itens."""
    if not candidatos:
        return []
    resposta = provider.complete(montar_prompt_curadoria(candidatos, n))
    dados = _extrair_json(resposta.texto)
    itens = [
        ItemRadar(
            titulo=str(d.get("titulo", "")),
            url=str(d.get("url", "")),
            veiculo=str(d.get("veiculo", "")),
            resumo=str(d.get("resumo", "")),
            gancho=str(d.get("gancho", "")),
        )
        for d in dados
    ]
    return itens[:n]
