"""Motor de setups: transforma uma Serie em uma lista de Setup nomeados.

Determinístico: a mesma Serie de entrada produz sempre a mesma lista de
Setup, com as mesmas evidências. Nenhuma função aqui toca rede, usa LLM,
aleatoriedade ou a data de hoje. `evidencias` carrega só números — nunca
texto — porque é a prova que o C03 usa para barrar número inventado no
alerta.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from stella.corpo.bolsa.coletor import Serie
from stella.corpo.bolsa.indicadores import (
    atr,
    ifr,
    maxima_periodo,
    media_movel,
    minima_periodo,
    variacao_pct,
    volume_medio,
)

CENARIOS = ("alta", "baixa", "lateralizacao", "volatilidade")

# Limiares calibrados contra a distribuição REAL do universo em 2026-09-13
# (38 papéis elegíveis). Os valores originais eram inalcançáveis na B3 e faziam
# os dois setups de mercado parado nunca dispararem, em silêncio:
#   amplitude de 60 dias .... mínimo real 15,5%, mediana 28,2% (corte antigo: 12%)
#   ATR hoje / ATR médio 60d  mínimo real 76,7%, mediana 110%  (corte antigo: 70%)
# Recalibrar exige medir a distribuição de novo, não chutar.
_AMPLITUDE_LATERAL = 0.20  # pega 7 de 38 papéis
_DERIVA_LATERAL = 8.0  # % de deriva tolerada na janela de 60 dias
_COMPRESSAO_ATR = 0.85  # pega 1 de 38 papéis


@dataclass(frozen=True)
class Setup:
    """Um setup técnico detectado em uma Serie, em um dia específico."""

    ticker: str
    nome: str
    cenario: str
    direcao: str
    preco: float
    data: date
    forca: int
    evidencias: dict[str, float]


def elegivel(serie: Serie) -> tuple[bool, str]:
    """Verifica se uma Serie passa nos filtros mínimos para entrar no radar.

    Args:
        serie: Série de candles do ticker.

    Returns:
        Tupla (elegivel, motivo). Motivo vazio quando elegivel é True; caso
        contrário, um de "CANDLES_INSUFICIENTES", "PRECO_MINIMO" ou
        "LIQUIDEZ_INSUFICIENTE".
    """
    candles = serie.candles
    if len(candles) < 200:
        return False, "CANDLES_INSUFICIENTES"

    ultimo = candles[-1]
    if ultimo.fechamento < 5.00:
        return False, "PRECO_MINIMO"

    vol_medio_21 = volume_medio(candles, 21)
    if vol_medio_21 is None:
        return False, "CANDLES_INSUFICIENTES"

    liquidez = vol_medio_21 * ultimo.fechamento
    if liquidez < 10_000_000:
        return False, "LIQUIDEZ_INSUFICIENTE"

    return True, ""


def _bonus_volume(volume_relativo: float) -> int:
    """Pontos de força pelo volume do dia relativo à média de 21 dias."""
    bonus = 0
    if volume_relativo >= 2.0:
        bonus += 15
    if volume_relativo >= 1.5:
        bonus += 10
    return bonus


def _bonus_alta_mm200(fechamento: float, mm200: float) -> int:
    """Pontos de força quando o fechamento está a mais de 10% acima da MM200."""
    if mm200 == 0:
        return 0
    return 15 if (fechamento - mm200) / mm200 > 0.10 else 0


def _bonus_ifr_sobrevenda(valor_ifr: float) -> int:
    """Pontos de força quando o IFR indica sobrevenda extrema (< 25)."""
    return 10 if valor_ifr < 25 else 0


def _bonus_ifr_perda_suporte(valor_ifr: float) -> int:
    """Pontos de força quando o IFR indica sobrecompra extrema (> 75)."""
    return 10 if valor_ifr > 75 else 0


def _bonus_rompimento_fresco(fechamento: float, extremo: float) -> int:
    """Pontos de força quando o fechamento está a menos de 3% do extremo rompido."""
    if extremo == 0:
        return 0
    return 10 if abs(fechamento - extremo) / extremo < 0.03 else 0


def detectar_ROMPIMENTO_ALTA(serie: Serie) -> Setup | None:  # noqa: N802
    """Rompimento de máxima de 60 dias com volume e tendência de fundo a favor.

    Args:
        serie: Série de candles do ticker.

    Returns:
        Setup se as três condições dispararem, senão None.
    """
    candles = serie.candles
    if len(candles) < 2:
        return None

    fechamentos = [c.fechamento for c in candles]
    ultimo = candles[-1]

    maxima_anterior = maxima_periodo(candles[:-1], 60)
    vol_medio_21 = volume_medio(candles, 21)
    mm200 = media_movel(fechamentos, 200)
    if maxima_anterior is None or vol_medio_21 is None or mm200 is None:
        return None
    if vol_medio_21 == 0:
        return None

    if not ultimo.fechamento > maxima_anterior:
        return None
    volume_relativo = ultimo.volume / vol_medio_21
    if not volume_relativo > 1.5:
        return None
    if not ultimo.fechamento > mm200:
        return None

    forca = min(
        100,
        50
        + _bonus_volume(volume_relativo)
        + _bonus_alta_mm200(ultimo.fechamento, mm200)
        + _bonus_rompimento_fresco(ultimo.fechamento, maxima_anterior),
    )
    evidencias = {
        "volume_relativo": round(volume_relativo, 4),
        "mm200": round(mm200, 4),
        "maxima_60": round(maxima_anterior, 4),
    }
    return Setup(
        ticker=serie.ticker,
        nome="ROMPIMENTO_ALTA",
        cenario="alta",
        direcao="compra",
        preco=ultimo.fechamento,
        data=ultimo.data,
        forca=forca,
        evidencias=evidencias,
    )


def detectar_PULLBACK_TENDENCIA(serie: Serie) -> Setup | None:  # noqa: N802
    """Recuo até a MM20 dentro de uma tendência de alta organizada (MM20>MM50>MM200).

    Args:
        serie: Série de candles do ticker.

    Returns:
        Setup se as quatro condições dispararem, senão None.
    """
    candles = serie.candles
    if not candles:
        return None

    fechamentos = [c.fechamento for c in candles]
    ultimo = candles[-1]

    mm20 = media_movel(fechamentos, 20)
    mm50 = media_movel(fechamentos, 50)
    mm200 = media_movel(fechamentos, 200)
    valor_ifr = ifr(fechamentos, 14)
    if mm20 is None or mm50 is None or mm200 is None or valor_ifr is None:
        return None

    if not mm20 > mm50 > mm200:
        return None
    if not ultimo.minima <= mm20:
        return None
    if not ultimo.fechamento > mm50:
        return None
    if not 35 <= valor_ifr <= 60:
        return None

    forca = min(100, 50 + _bonus_alta_mm200(ultimo.fechamento, mm200))
    evidencias = {
        "mm20": round(mm20, 4),
        "mm50": round(mm50, 4),
        "mm200": round(mm200, 4),
        "ifr": round(valor_ifr, 4),
    }
    return Setup(
        ticker=serie.ticker,
        nome="PULLBACK_TENDENCIA",
        cenario="alta",
        direcao="compra",
        preco=ultimo.fechamento,
        data=ultimo.data,
        forca=forca,
        evidencias=evidencias,
    )


def detectar_SOBREVENDA_TENDENCIA(serie: Serie) -> Setup | None:  # noqa: N802
    """IFR em sobrevenda enquanto a tendência maior (MM200) segue de pé.

    Args:
        serie: Série de candles do ticker.

    Returns:
        Setup se as duas condições dispararem, senão None.
    """
    candles = serie.candles
    if not candles:
        return None

    fechamentos = [c.fechamento for c in candles]
    ultimo = candles[-1]

    valor_ifr = ifr(fechamentos, 14)
    mm200 = media_movel(fechamentos, 200)
    if valor_ifr is None or mm200 is None:
        return None

    if not valor_ifr < 30:
        return None
    if not ultimo.fechamento > mm200:
        return None

    forca = min(
        100,
        50 + _bonus_alta_mm200(ultimo.fechamento, mm200) + _bonus_ifr_sobrevenda(valor_ifr),
    )
    evidencias = {
        "ifr": round(valor_ifr, 4),
        "mm200": round(mm200, 4),
    }
    return Setup(
        ticker=serie.ticker,
        nome="SOBREVENDA_TENDENCIA",
        cenario="alta",
        direcao="compra",
        preco=ultimo.fechamento,
        data=ultimo.data,
        forca=forca,
        evidencias=evidencias,
    )


def detectar_PERDA_SUPORTE(serie: Serie) -> Setup | None:  # noqa: N802
    """Rompimento de mínima de 60 dias com volume, abaixo da MM200.

    Args:
        serie: Série de candles do ticker.

    Returns:
        Setup se as três condições dispararem, senão None.
    """
    candles = serie.candles
    if len(candles) < 2:
        return None

    fechamentos = [c.fechamento for c in candles]
    ultimo = candles[-1]

    minima_anterior = minima_periodo(candles[:-1], 60)
    vol_medio_21 = volume_medio(candles, 21)
    mm200 = media_movel(fechamentos, 200)
    valor_ifr = ifr(fechamentos, 14)
    if minima_anterior is None or vol_medio_21 is None or mm200 is None or valor_ifr is None:
        return None
    if vol_medio_21 == 0:
        return None

    if not ultimo.fechamento < minima_anterior:
        return None
    volume_relativo = ultimo.volume / vol_medio_21
    if not volume_relativo > 1.5:
        return None
    if not ultimo.fechamento < mm200:
        return None

    forca = min(
        100,
        50
        + _bonus_volume(volume_relativo)
        + _bonus_ifr_perda_suporte(valor_ifr)
        + _bonus_rompimento_fresco(ultimo.fechamento, minima_anterior),
    )
    evidencias = {
        "volume_relativo": round(volume_relativo, 4),
        "mm200": round(mm200, 4),
        "minima_60": round(minima_anterior, 4),
        "ifr": round(valor_ifr, 4),
    }
    return Setup(
        ticker=serie.ticker,
        nome="PERDA_SUPORTE",
        cenario="baixa",
        direcao="venda",
        preco=ultimo.fechamento,
        data=ultimo.data,
        forca=forca,
        evidencias=evidencias,
    )


def detectar_FAIXA_LATERAL(serie: Serie) -> Setup | None:  # noqa: N802
    """Preço andando de lado: amplitude de 60 dias estreita e variação pequena.

    Args:
        serie: Série de candles do ticker.

    Returns:
        Setup se as duas condições dispararem, senão None.
    """
    candles = serie.candles
    if not candles:
        return None

    fechamentos = [c.fechamento for c in candles]
    ultimo = candles[-1]

    maxima_60 = maxima_periodo(candles, 60)
    minima_60 = minima_periodo(candles, 60)
    variacao = variacao_pct(fechamentos, 60)
    if maxima_60 is None or minima_60 is None or variacao is None:
        return None
    if minima_60 == 0:
        return None

    amplitude = (maxima_60 - minima_60) / minima_60
    if not amplitude < _AMPLITUDE_LATERAL:
        return None
    if not abs(variacao) < _DERIVA_LATERAL:
        return None

    forca = 50
    evidencias = {
        "maxima_60": round(maxima_60, 4),
        "minima_60": round(minima_60, 4),
        "variacao_pct_60": round(variacao, 4),
    }
    return Setup(
        ticker=serie.ticker,
        nome="FAIXA_LATERAL",
        cenario="lateralizacao",
        direcao="neutro",
        preco=ultimo.fechamento,
        data=ultimo.data,
        forca=forca,
        evidencias=evidencias,
    )


def detectar_COMPRESSAO_VOLATILIDADE(serie: Serie) -> Setup | None:  # noqa: N802
    """ATR de hoje comprimido (< 70%) contra a média dos ATRs dos 60 dias anteriores.

    Args:
        serie: Série de candles do ticker.

    Returns:
        Setup se a compressão disparar e a série não for FAIXA_LATERAL, senão None.
    """
    candles = serie.candles

    atr_hoje = atr(candles, 14)
    if atr_hoje is None:
        return None

    historico: list[float] = []
    for i in range(1, 61):
        valor = atr(candles[:-i], 14)
        if valor is not None:
            historico.append(valor)
    if not historico:
        return None

    media_historica = sum(historico) / len(historico)
    if media_historica == 0:
        return None
    if not atr_hoje < _COMPRESSAO_ATR * media_historica:
        return None

    if detectar_FAIXA_LATERAL(serie) is not None:
        return None

    ultimo = candles[-1]
    forca = 50
    evidencias = {
        "atr_14": round(atr_hoje, 4),
        "atr_medio_60d": round(media_historica, 4),
    }
    return Setup(
        ticker=serie.ticker,
        nome="COMPRESSAO_VOLATILIDADE",
        cenario="volatilidade",
        direcao="neutro",
        preco=ultimo.fechamento,
        data=ultimo.data,
        forca=forca,
        evidencias=evidencias,
    )


_DETECTORES = (
    detectar_ROMPIMENTO_ALTA,
    detectar_PULLBACK_TENDENCIA,
    detectar_SOBREVENDA_TENDENCIA,
    detectar_PERDA_SUPORTE,
    detectar_FAIXA_LATERAL,
    detectar_COMPRESSAO_VOLATILIDADE,
)


def detectar(serie: Serie) -> list[Setup]:
    """Roda todos os detectores de setup sobre uma Serie.

    Args:
        serie: Série de candles do ticker.

    Returns:
        Lista dos Setup que dispararam (pode ter mais de um, pode ser vazia).
    """
    resultado: list[Setup] = []
    for detector in _DETECTORES:
        setup = detector(serie)
        if setup is not None:
            resultado.append(setup)
    return resultado
