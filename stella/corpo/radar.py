"""Radar de Tendências — busca agregada de notícias por tema.

Módulo que orquestra a coleta de candidatos (artigos) de múltiplos temas
via Tavily, aplica filtros de domínio e deduplica por URL.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html import escape as _esc
from pathlib import Path
from typing import Any

import httpx

from stella.adapters.llm.anthropic_provider import AnthropicProvider
from stella.adapters.llm.base import LLMProvider
from stella.adapters.research.tavily_client import buscar_noticias_tavily
from stella.infra.config import StellaConfig

logger = logging.getLogger("stella.radar")

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
        except Exception as exc:
            logger.warning("radar: busca do tema %r falhou: %s", tema, exc)
            continue  # um tema que falha nao derruba os outros
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
    parsed = json.loads(t[inicio : fim + 1])
    if not isinstance(parsed, list):
        raise ValueError("resposta do curador nao e um array JSON")
    return parsed


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


def montar_card(itens: list[ItemRadar], horario_label: str, agora: datetime | None = None) -> str:
    """Monta card HTML do Telegram a partir dos itens curados.

    Args:
        itens: Lista de ItemRadar com notícias curadas.
        horario_label: Rótulo da hora (ex: "06h", "14h").
        agora: Data/hora de referência (FUSO). Se None, usa datetime.now(FUSO).

    Returns:
        String formatada com HTML tags (<b>, <a>, <i>) para Telegram parse_mode=HTML.
        Sem em-dash (—), pronto para envio público.
    """
    quando = agora or datetime.now(FUSO)
    cabecalho = f"📰 <b>RADAR {horario_label} · {quando:%d/%m}</b>"
    if not itens:
        return f"{cabecalho}\n\nSem novidade quente neste drop, Senhor."
    blocos = [cabecalho, ""]
    for i, it in enumerate(itens, start=1):
        blocos.append(
            f"<b>{i}. {_esc(it.titulo)}</b>\n"
            f'🔗 <a href="{_esc(it.url, quote=True)}">{_esc(it.veiculo)}</a>\n'
            f"{_esc(it.resumo)}\n"
            f"💡 <i>{_esc(it.gancho)}</i>"
        )
        blocos.append("")
    return "\n".join(blocos).strip()


COFRE_TELEGRAM = Path("D:/VortexBrain00/.secrets/telegram.json")
VAULT_DIR = Path("D:/VortexBrain00/bssurf00")
RADAR_DIR_REL = "C04 Claude Obsidian/radar"


def enviar_telegram(
    texto: str,
    cofre_path: Path = COFRE_TELEGRAM,
    http_post: Callable[..., Any] = httpx.post,
) -> None:
    """Envia mensagem HTML para Telegram.

    Args:
        texto: Conteudo da mensagem em HTML.
        cofre_path: Caminho do arquivo com credenciais (bot_token, chat_id).
        http_post: Funcao injetavel para POST HTTP (para testes).
    """
    cofre = json.loads(cofre_path.read_text(encoding="utf-8"))
    resp = http_post(
        f"https://api.telegram.org/bot{cofre['bot_token']}/sendMessage",
        json={
            "chat_id": str(cofre["chat_id"]),
            "text": texto,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=20,
    )
    resp.raise_for_status()


def salvar_no_vault(
    itens: list[ItemRadar],
    horario_label: str,
    vault_dir: Path = VAULT_DIR,
    agora: datetime | None = None,
) -> Path:
    """Salva itens curados em arquivo .md no vault.

    Args:
        itens: Lista de ItemRadar com noticias curadas.
        horario_label: Rotulo da hora (ex: "06h", "14h").
        vault_dir: Raiz do vault Obsidian.
        agora: Data/hora de referencia (FUSO). Se None, usa datetime.now(FUSO).

    Returns:
        Path do arquivo .md criado/atualizado.
    """
    quando = agora or datetime.now(FUSO)
    destino = vault_dir / RADAR_DIR_REL / f"{quando:%Y-%m-%d}.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    linhas = [f"\n## Drop {horario_label} ({quando:%H:%M})\n"]
    for it in itens:
        linhas.append(f"- [{it.titulo}]({it.url}) | {it.veiculo}")
        linhas.append(f"  - Resumo: {it.resumo}")
        linhas.append(f"  - Gancho: {it.gancho}")
    with destino.open("a", encoding="utf-8") as arq:
        arq.write("\n".join(linhas) + "\n")
    return destino


_LABELS_HORA: dict[int, str] = {6: "06h", 14: "14h", 19: "19h"}
_MODELO_CURADOR = "claude-sonnet-4-6"


def label_horario(agora: datetime | None = None) -> str:
    """Converte hora atual em label legivel para o card.

    Args:
        agora: Data/hora de referencia (FUSO). Se None, usa datetime.now(FUSO).

    Returns:
        Label como "06h", "14h", "19h" ou "HHh" para outras horas.
    """
    quando = agora or datetime.now(FUSO)
    return _LABELS_HORA.get(quando.hour, f"{quando:%H}h")


def construir_provider() -> LLMProvider:
    """Constroi AnthropicProvider com credenciais de StellaConfig.

    Returns:
        Instancia de AnthropicProvider configurada com modelo curador.
    """
    cfg = StellaConfig()
    return AnthropicProvider(
        api_key=cfg.anthropic_api_key.get_secret_value(), modelo=_MODELO_CURADOR
    )


def _card_degradado(candidatos: list[Candidato], n: int, label: str, agora: datetime) -> str:
    """Monta um card com links crus quando a curadoria falha.

    Args:
        candidatos: Lista de candidatos brutos.
        n: Numero maximo de itens.
        label: Label de horario para o cabecalho.
        agora: Data/hora de referencia.

    Returns:
        Card no mesmo formato Telegram-markup que montar_card, sem curadoria LLM.
    """
    itens = [
        ItemRadar(
            titulo=c.titulo,
            url=c.url,
            veiculo=c.veiculo,
            resumo=c.snippet,
            gancho="(curadoria indisponivel neste drop)",
        )
        for c in candidatos[:n]
    ]
    return montar_card(itens, label, agora=agora)


def rodar_radar(
    n: int,
    *,
    api_key: str | None = None,
    provider: LLMProvider | None = None,
    horario_label: str | None = None,
    buscar: Callable[..., list[dict[str, Any]]] = buscar_noticias_tavily,
    enviar: Callable[[str], None] | None = None,
    salvar: bool = True,
    agora: datetime | None = None,
) -> list[ItemRadar]:
    """Orquestra ciclo completo do Radar de Tendencias.

    Busca candidatos, deduplica via seen-log, curar com LLM, envia card
    e grava seen-log. Em caso de falha do curador, degrada para card com
    links crus.

    Args:
        n: Numero de itens a selecionar.
        api_key: Chave Tavily. Se None, carrega de StellaConfig.
        provider: LLMProvider injetavel. Se None, usa construir_provider().
        horario_label: Rotulo de hora. Se None, deriva de agora.
        buscar: Callable de busca injetavel (padrao: buscar_noticias_tavily).
        enviar: Callable de envio injetavel (padrao: enviar_telegram).
        salvar: Se True, salva card no vault Obsidian.
        agora: Data/hora de referencia (FUSO). Se None, usa datetime.now(FUSO).

    Returns:
        Lista de ItemRadar curados (vazia em caso de degradacao ou sem novidade).
    """
    quando = agora or datetime.now(FUSO)
    label = horario_label or label_horario(quando)

    if api_key is None:
        api_key = StellaConfig().tavily_api_key.get_secret_value()
    if provider is None:
        provider = construir_provider()
    if enviar is None:
        enviar = enviar_telegram

    # Captura seen_path do global no momento da chamada (permite monkeypatch nos testes)
    seen_path = SEEN_PATH

    candidatos = buscar_candidatos(api_key=api_key, buscar=buscar)
    seen = podar_seen(carregar_seen(seen_path), agora=quando)
    novos = filtrar_novos(candidatos, seen)

    itens: list[ItemRadar] = []
    if novos:
        try:
            itens = curar(novos, n, provider=provider)
        except Exception:
            card = _card_degradado(novos, n, label, quando)
            enviar(card)
            gravar_seen(seen, [c.url for c in novos[:n]], path=seen_path, agora=quando)
            return itens

    card = montar_card(itens, label, agora=quando)
    enviar(card)
    if itens:
        gravar_seen(seen, [it.url for it in itens], path=seen_path, agora=quando)
        if salvar:
            try:
                salvar_no_vault(itens, label, agora=quando)
            except Exception as exc:
                logger.warning("radar: salvar_no_vault falhou: %s", exc)
    return itens
