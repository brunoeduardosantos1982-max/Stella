"""Módulo de risco: transforma um Setup em um plano de posição dimensionado.

Determinístico: mesma entrada produz sempre o mesmo Plano. Nenhuma função
aqui toca rede, usa LLM ou sugere venda descoberta — só descreve o cenário
e o plano; quem decide é o Bruno.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from stella.corpo.bolsa.coletor import Serie
from stella.corpo.bolsa.indicadores import atr
from stella.corpo.bolsa.setups import Setup


@dataclass(frozen=True)
class Plano:
    """Plano de posição dimensionado a partir de um Setup e sua Serie."""

    entrada: float
    stop: float
    alvo: float
    risco_por_acao: float
    retorno_por_acao: float
    razao_rr: float
    quantidade: int
    risco_total: float
    aprovado: bool
    motivo: str


def _plano_reprovado(entrada: float, motivo: str) -> Plano:
    """Monta um Plano reprovado com todos os campos numéricos zerados.

    Args:
        entrada: Preço de entrada (o único número que sempre se conhece).
        motivo: Motivo da reprovação.

    Returns:
        Plano com aprovado=False e os demais campos numéricos em zero.
    """
    return Plano(
        entrada=round(entrada, 2),
        stop=0.0,
        alvo=0.0,
        risco_por_acao=0.0,
        retorno_por_acao=0.0,
        razao_rr=0.0,
        quantidade=0,
        risco_total=0.0,
        aprovado=False,
        motivo=motivo,
    )


def dimensionar(
    setup: Setup,
    serie: Serie,
    *,
    capital_risco: float = 500.0,
    multiplo_stop: float = 2.0,
    multiplo_alvo: float = 3.0,
    rr_minimo: float = 1.5,
) -> Plano:
    """Dimensiona a posição de um Setup: entrada, stop, alvo e quantidade.

    Args:
        setup: Setup detectado (traz a direção e o preço de entrada).
        serie: Série de candles do ticker, usada para calcular o ATR(14).
        capital_risco: Quanto (em R$) o Bruno está disposto a arriscar no trade.
        multiplo_stop: Múltiplo do ATR usado para o stop.
        multiplo_alvo: Múltiplo do ATR usado para o alvo.
        rr_minimo: Razão retorno/risco mínima para o plano ser aprovado.

    Returns:
        Plano dimensionado. Quando reprovado, `motivo` é um de "SEM_ATR",
        "SEM_DIRECAO", "RR_INSUFICIENTE", "LOTE_MINIMO" ou "STOP_INVALIDO".
    """
    entrada = setup.preco

    valor_atr = atr(serie.candles, 14)
    if not valor_atr:
        return _plano_reprovado(entrada, "SEM_ATR")

    if setup.direcao not in ("compra", "venda"):
        return _plano_reprovado(entrada, "SEM_DIRECAO")

    if setup.direcao == "compra":
        stop = entrada - multiplo_stop * valor_atr
        alvo = entrada + multiplo_alvo * valor_atr
    else:
        stop = entrada + multiplo_stop * valor_atr
        alvo = entrada - multiplo_alvo * valor_atr

    if stop <= 0:
        return _plano_reprovado(entrada, "STOP_INVALIDO")

    risco_por_acao = abs(entrada - stop)
    retorno_por_acao = abs(alvo - entrada)
    if risco_por_acao == 0:
        return _plano_reprovado(entrada, "STOP_INVALIDO")

    razao_rr = retorno_por_acao / risco_por_acao
    if razao_rr < rr_minimo:
        return Plano(
            entrada=round(entrada, 2),
            stop=round(stop, 2),
            alvo=round(alvo, 2),
            risco_por_acao=round(risco_por_acao, 2),
            retorno_por_acao=round(retorno_por_acao, 2),
            razao_rr=razao_rr,
            quantidade=0,
            risco_total=0.0,
            aprovado=False,
            motivo="RR_INSUFICIENTE",
        )

    quantidade_bruta = math.floor(capital_risco / risco_por_acao)
    quantidade = (quantidade_bruta // 100) * 100

    if quantidade == 0:
        return Plano(
            entrada=round(entrada, 2),
            stop=round(stop, 2),
            alvo=round(alvo, 2),
            risco_por_acao=round(risco_por_acao, 2),
            retorno_por_acao=round(retorno_por_acao, 2),
            razao_rr=razao_rr,
            quantidade=quantidade_bruta,
            risco_total=round(quantidade_bruta * risco_por_acao, 2),
            aprovado=False,
            motivo="LOTE_MINIMO",
        )

    return Plano(
        entrada=round(entrada, 2),
        stop=round(stop, 2),
        alvo=round(alvo, 2),
        risco_por_acao=round(risco_por_acao, 2),
        retorno_por_acao=round(retorno_por_acao, 2),
        razao_rr=razao_rr,
        quantidade=quantidade,
        risco_total=round(quantidade * risco_por_acao, 2),
        aprovado=True,
        motivo="",
    )


def ranquear(
    pares: list[tuple[Setup, Plano]],
    *,
    maximo: int = 5,
) -> list[tuple[Setup, Plano]]:
    """Ordena e corta os planos aprovados para virarem alerta.

    Ordena por `forca` do Setup (decrescente); em empate, por `razao_rr` do
    Plano (decrescente); em empate total, por ticker em ordem alfabética,
    para o resultado ser estável.

    Args:
        pares: Lista de (Setup, Plano) já dimensionados.
        maximo: Quantidade máxima de pares a devolver.

    Returns:
        Os pares com `Plano.aprovado` True, ordenados e cortados em `maximo`.
    """
    aprovados = [par for par in pares if par[1].aprovado]
    ordenados = sorted(
        aprovados,
        key=lambda par: (-par[0].forca, -par[1].razao_rr, par[0].ticker),
    )
    return ordenados[:maximo]
