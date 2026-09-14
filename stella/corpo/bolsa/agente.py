"""Agente do Radar da Bolsa: orquestra coleta, setups, risco, tese e envio.

Fecha a fase 1 do Radar da Bolsa: pega o que os módulos puros (`coletor`,
`indicadores`, `setups`, `risco`) calculam, escreve a tese com o LLM só em
palavras (nunca em número), barra qualquer tese com número inventado via
`verificador.verificar`, monta o card e envia no Telegram do Bruno. O card
sai todo dia de pregão, mesmo sem setup e mesmo quando a coleta falha.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from stella.adapters.llm.anthropic_provider import AnthropicProvider
from stella.adapters.llm.base import LLMProvider
from stella.corpo.bolsa.apresentador import (
    montar_bloco_alerta,
    montar_card,
    montar_card_erro,
    montar_card_vazio,
    montar_tese,
    tese_deterministica,
)
from stella.corpo.bolsa.coletor import FUSO, coletar_universo
from stella.corpo.bolsa.risco import Plano, dimensionar, ranquear
from stella.corpo.bolsa.setups import Setup, detectar, elegivel
from stella.corpo.bolsa.verificador import verificar
from stella.infra.config import StellaConfig

logger = logging.getLogger("stella.bolsa")

COFRE_TELEGRAM = Path("D:/VortexBrain00/.secrets/telegram.json")
_MODELO_TESE = "claude-sonnet-4-6"


def enviar_telegram(
    texto: str,
    cofre_path: Path = COFRE_TELEGRAM,
    http_post: Callable[..., Any] = httpx.post,
) -> None:
    """Envia mensagem HTML para o Telegram.

    Mesma forma injetável de `stella.corpo.radar.enviar_telegram`.

    Args:
        texto: Conteúdo da mensagem em HTML.
        cofre_path: Caminho do arquivo com credenciais (bot_token, chat_id).
        http_post: Função injetável para POST HTTP (para testes).
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


def _enviar_seguro(texto: str, cofre_path: Path, http_post: Callable[..., Any]) -> None:
    """Envia o card e engole qualquer falha do Telegram, sem derrubar a rotina.

    Mesmo padrão de `stella.corpo.seguranca.rodar_seguranca_diaria`.
    """
    try:
        enviar_telegram(texto, cofre_path=cofre_path, http_post=http_post)
    except Exception as exc:  # noqa: BLE001 - falha de envio nunca derruba a rotina
        logger.warning("bolsa: falha ao enviar card no Telegram: %s", exc)


def _construir_provider() -> LLMProvider:
    """Constrói AnthropicProvider com credenciais de StellaConfig."""
    cfg = StellaConfig()
    return AnthropicProvider(api_key=cfg.anthropic_api_key.get_secret_value(), modelo=_MODELO_TESE)


def rodar_radar_bolsa(
    *,
    http_get: Callable[..., Any] = httpx.get,
    provider: LLMProvider | None = None,
    cofre_path: Path = COFRE_TELEGRAM,
    http_post: Callable[..., Any] = httpx.post,
    agora: datetime | None = None,
    maximo: int = 5,
    capital_risco: float = 500.0,
) -> str:
    """Orquestra o ciclo completo do Radar da Bolsa e devolve o card enviado.

    Coleta o universo, detecta setups, dimensiona o risco, ranqueia os
    melhores, escreve a tese de cada um (com verificador barrando número
    inventado) e envia o card no Telegram. Envia sempre, mesmo sem setup
    algum ou com a coleta inteira falhando.

    Args:
        http_get: Função injetável de GET HTTP, repassada à coleta.
        provider: Provider de LLM injetável. Se None, usa `_construir_provider()`,
            e só é construído quando há setup aprovado a redigir.
        cofre_path: Caminho do cofre de credenciais do Telegram.
        http_post: Função injetável de POST HTTP, repassada ao envio.
        agora: Data/hora de referência (FUSO). Se None, usa `datetime.now(FUSO)`.
        maximo: Número máximo de alertas no card.
        capital_risco: Risco em reais por operação, repassado a `dimensionar`.

    Returns:
        O texto do card que foi enviado (cheio, vazio ou de erro).
    """
    quando = agora or datetime.now(FUSO)

    try:
        series, falhas = coletar_universo(http_get=http_get, agora=quando)
    except Exception as exc:  # noqa: BLE001 - a coleta inteira não pode derrubar o card
        card = montar_card_erro(str(exc), quando)
        _enviar_seguro(card, cofre_path, http_post)
        return card

    aprovados: list[tuple[Setup, Plano]] = []
    neutros: list[Setup] = []
    # Data do candle mais recente entre as séries: é ela que diz se houve
    # pregão hoje. Sem isso o card carimbaria a data de hoje em dado de sexta.
    data_pregao = max(
        (s.candles[-1].data for s in series if s.candles),
        default=None,
    )

    for serie in series:
        ok, _motivo_inelegivel = elegivel(serie)
        if not ok:
            continue
        for setup in detectar(serie):
            plano = dimensionar(setup, serie, capital_risco=capital_risco)
            if plano.aprovado:
                aprovados.append((setup, plano))
            elif plano.motivo == "SEM_DIRECAO":
                neutros.append(setup)
            # reprovado por outro motivo (RR_INSUFICIENTE, LOTE_MINIMO, SEM_ATR,
            # STOP_INVALIDO) é descartado: não vira alerta nem entra na contagem.

    escolhidos = ranquear(aprovados, maximo=maximo)

    if not escolhidos:
        card = montar_card_vazio(
            quando,
            neutros=neutros,
            falhas=falhas,
            varridos=len(series),
            data_pregao=data_pregao,
        )
        _enviar_seguro(card, cofre_path, http_post)
        return card

    provider_ativo = provider if provider is not None else _construir_provider()
    blocos: list[str] = []
    for setup, plano in escolhidos:
        try:
            tese = montar_tese(setup, plano, provider=provider_ativo)
        except Exception as exc:  # noqa: BLE001 - falha do provider não derruba o card
            logger.warning(
                "bolsa: provider falhou para %s, usando tese determinística: %s", setup.ticker, exc
            )
            tese = tese_deterministica(setup, plano)
        else:
            tese_ok, intrusos = verificar(tese, setup, plano)
            if not tese_ok:
                logger.warning(
                    "bolsa: tese de %s reprovada pelo verificador (números intrusos: %s); "
                    "caindo para a determinística",
                    setup.ticker,
                    intrusos,
                )
                tese = tese_deterministica(setup, plano)
        blocos.append(montar_bloco_alerta(setup, plano, tese))

    card = montar_card(blocos, quando, neutros=neutros, falhas=falhas, data_pregao=data_pregao)
    _enviar_seguro(card, cofre_path, http_post)
    return card
