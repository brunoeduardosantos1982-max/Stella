"""Indicadores técnicos: funções puras sobre séries de preço e candles.

Nenhuma função aqui toca rede ou mantém estado. Todas devolvem `None`
quando a série é curta demais para o período pedido — nunca levantam
exceção por falta de dado, e nunca inventam valor.
"""

from __future__ import annotations

from stella.corpo.bolsa.coletor import Candle


def media_movel(valores: list[float], periodo: int) -> float | None:
    """Média aritmética simples dos últimos `periodo` valores.

    Args:
        valores: Série de preços (ex.: fechamentos), em ordem cronológica.
        periodo: Quantidade de valores mais recentes a considerar.

    Returns:
        A média, ou None se a série tiver menos de `periodo` valores.
    """
    if periodo <= 0 or len(valores) < periodo:
        return None
    return sum(valores[-periodo:]) / periodo


def media_exponencial(valores: list[float], periodo: int) -> float | None:
    """Média móvel exponencial (EMA).

    A semente é a média simples dos primeiros `periodo` valores; o fator de
    suavização é `2/(periodo+1)`, aplicado do início ao fim da série.

    Args:
        valores: Série de preços, em ordem cronológica.
        periodo: Período da EMA.

    Returns:
        O último valor da EMA, ou None se a série tiver menos de `periodo` valores.
    """
    if periodo <= 0 or len(valores) < periodo:
        return None
    fator = 2 / (periodo + 1)
    ema = sum(valores[:periodo]) / periodo
    for valor in valores[periodo:]:
        ema = valor * fator + ema * (1 - fator)
    return ema


def ifr(valores: list[float], periodo: int = 14) -> float | None:
    """Índice de Força Relativa (IFR/RSI) de Wilder.

    Ganho e perda médios iniciais vêm da média simples dos primeiros
    `periodo` deltas; daí em diante, suavização de Wilder:
    `(anterior*(periodo-1) + atual) / periodo`.

    Args:
        valores: Série de preços (fechamentos), em ordem cronológica.
        periodo: Período do IFR (default 14).

    Returns:
        O IFR entre 0 e 100, ou None se a série não tiver `periodo+1` valores.
        Se a perda média for zero, devolve 100.0.
    """
    if periodo <= 0 or len(valores) < periodo + 1:
        return None

    deltas = [valores[i] - valores[i - 1] for i in range(1, len(valores))]

    ganho_medio = sum(d for d in deltas[:periodo] if d > 0) / periodo
    perda_medio = sum(-d for d in deltas[:periodo] if d < 0) / periodo

    for delta in deltas[periodo:]:
        ganho = delta if delta > 0 else 0.0
        perda = -delta if delta < 0 else 0.0
        ganho_medio = (ganho_medio * (periodo - 1) + ganho) / periodo
        perda_medio = (perda_medio * (periodo - 1) + perda) / periodo

    if perda_medio == 0:
        return 100.0

    rs = ganho_medio / perda_medio
    return 100 - (100 / (1 + rs))


def atr(candles: list[Candle], periodo: int = 14) -> float | None:
    """Average True Range (ATR), com suavização de Wilder.

    O True Range de cada candle é o maior entre `maxima-minima`,
    `abs(maxima - fechamento_anterior)` e `abs(minima - fechamento_anterior)`.

    Args:
        candles: Série de candles, em ordem cronológica.
        periodo: Período do ATR (default 14).

    Returns:
        O ATR, ou None se a série não tiver `periodo+1` candles.
    """
    if periodo <= 0 or len(candles) < periodo + 1:
        return None

    verdadeiras_amplitudes: list[float] = []
    for i in range(1, len(candles)):
        atual = candles[i]
        anterior = candles[i - 1]
        tr = max(
            atual.maxima - atual.minima,
            abs(atual.maxima - anterior.fechamento),
            abs(atual.minima - anterior.fechamento),
        )
        verdadeiras_amplitudes.append(tr)

    valor_atr = sum(verdadeiras_amplitudes[:periodo]) / periodo
    for tr in verdadeiras_amplitudes[periodo:]:
        valor_atr = (valor_atr * (periodo - 1) + tr) / periodo
    return valor_atr


def maxima_periodo(candles: list[Candle], periodo: int) -> float | None:
    """Maior máxima dos últimos `periodo` candles.

    Args:
        candles: Série de candles, em ordem cronológica.
        periodo: Quantidade de candles mais recentes a considerar.

    Returns:
        A maior máxima, ou None se a série tiver menos de `periodo` candles.
    """
    if periodo <= 0 or len(candles) < periodo:
        return None
    return max(c.maxima for c in candles[-periodo:])


def minima_periodo(candles: list[Candle], periodo: int) -> float | None:
    """Menor mínima dos últimos `periodo` candles.

    Args:
        candles: Série de candles, em ordem cronológica.
        periodo: Quantidade de candles mais recentes a considerar.

    Returns:
        A menor mínima, ou None se a série tiver menos de `periodo` candles.
    """
    if periodo <= 0 or len(candles) < periodo:
        return None
    return min(c.minima for c in candles[-periodo:])


def volume_medio(candles: list[Candle], periodo: int = 21) -> float | None:
    """Média simples do volume dos últimos `periodo` candles.

    Args:
        candles: Série de candles, em ordem cronológica.
        periodo: Quantidade de candles mais recentes a considerar (default 21).

    Returns:
        A média de volume, ou None se a série tiver menos de `periodo` candles.
    """
    if periodo <= 0 or len(candles) < periodo:
        return None
    return sum(c.volume for c in candles[-periodo:]) / periodo


def variacao_pct(valores: list[float], periodo: int) -> float | None:
    """Variação percentual entre o último valor e o de `periodo` candles atrás.

    Args:
        valores: Série de preços, em ordem cronológica.
        periodo: Quantos candles atrás está o valor de referência.

    Returns:
        A variação percentual, ou None se a série for curta demais ou o
        valor de referência for zero.
    """
    if periodo <= 0 or len(valores) < periodo + 1:
        return None
    referencia = valores[-(periodo + 1)]
    atual = valores[-1]
    if referencia == 0:
        return None
    return (atual - referencia) / referencia * 100
