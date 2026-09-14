from __future__ import annotations

from datetime import date

import pytest

from stella.corpo.bolsa import indicadores
from stella.corpo.bolsa.coletor import Candle


def _candle(maxima: float, minima: float, fechamento: float, volume: int = 1000) -> Candle:
    return Candle(
        data=date(2026, 1, 1),
        abertura=fechamento,
        maxima=maxima,
        minima=minima,
        fechamento=fechamento,
        volume=volume,
    )


def test_media_movel_dos_ultimos_valores() -> None:
    assert indicadores.media_movel([1.0, 2.0, 3.0, 4.0, 5.0], 3) == pytest.approx(4.0)


def test_media_exponencial_com_semente_na_media_simples() -> None:
    # semente = média(1,2,3) = 2.0; fator = 2/4 = 0.5
    # ema(4) = 4*0.5 + 2*0.5 = 3.0; ema(5) = 5*0.5 + 3*0.5 = 4.0
    assert indicadores.media_exponencial([1.0, 2.0, 3.0, 4.0, 5.0], 3) == pytest.approx(4.0)


def test_ifr_de_serie_so_de_alta_vale_100() -> None:
    # 15 fechamentos subindo 1 real por dia: perda média é 0, logo IFR = 100.0.
    fechamentos = [float(100 + i) for i in range(15)]
    assert indicadores.ifr(fechamentos) == 100.0


def test_ifr_de_valor_conhecido_conferido_a_mao() -> None:
    # Série clássica de 15 preços usada em referências de RSI de Wilder.
    # Deltas dos primeiros 14: ganho médio = 0.23857142857142832..,
    # perda média = 0.0999999999999999; RS = 2.3857142857142857;
    # IFR = 100 - 100/(1+RS) = 70.46413502109705 (conferido à parte, sem chamar indicadores.ifr).
    precos = [
        44.34,
        44.09,
        44.15,
        43.61,
        44.33,
        44.83,
        45.10,
        45.42,
        45.84,
        46.08,
        45.89,
        46.03,
        45.61,
        46.28,
        46.28,
    ]
    assert indicadores.ifr(precos, periodo=14) == pytest.approx(70.46413502109705)


def test_atr_usa_fechamento_anterior_no_true_range() -> None:
    # Day5 tem alta=9, baixa=7 (amplitude 2) mas o fechamento do dia anterior
    # foi 12, então o TR real é abs(9-12)=3 ou abs(7-12)=5 -> 5, não 2.
    candles = [
        _candle(maxima=10, minima=8, fechamento=9),
        _candle(maxima=11, minima=9, fechamento=10),
        _candle(maxima=12, minima=10, fechamento=11),
        _candle(maxima=13, minima=11, fechamento=12),
        _candle(maxima=9, minima=7, fechamento=8),
    ]
    # TRs (dias 2..5): 2, 2, 2, 5 -> semente(3) = 2.0 -> atr = (2*2+5)/3 = 3.0
    assert indicadores.atr(candles, periodo=3) == pytest.approx(3.0)


def test_maxima_e_minima_de_janela() -> None:
    candles = [
        _candle(maxima=10, minima=8, fechamento=9),
        _candle(maxima=11, minima=9, fechamento=10),
        _candle(maxima=12, minima=10, fechamento=11),
        _candle(maxima=13, minima=11, fechamento=12),
        _candle(maxima=9, minima=7, fechamento=8),
    ]
    assert indicadores.maxima_periodo(candles, 3) == 13
    assert indicadores.minima_periodo(candles, 3) == 7


def test_volume_medio_dos_ultimos_candles() -> None:
    candles = [
        _candle(maxima=1, minima=1, fechamento=1, volume=100),
        _candle(maxima=1, minima=1, fechamento=1, volume=200),
        _candle(maxima=1, minima=1, fechamento=1, volume=300),
        _candle(maxima=1, minima=1, fechamento=1, volume=400),
        _candle(maxima=1, minima=1, fechamento=1, volume=500),
    ]
    assert indicadores.volume_medio(candles, periodo=3) == pytest.approx(400.0)


def test_variacao_pct_entre_ultimo_e_periodo_atras() -> None:
    assert indicadores.variacao_pct([100.0, 110.0, 121.0], periodo=2) == pytest.approx(21.0)


def test_indicadores_devolvem_none_para_serie_curta() -> None:
    candles_curtos = [_candle(maxima=10, minima=8, fechamento=9)]
    assert indicadores.media_movel([1.0, 2.0], 3) is None
    assert indicadores.media_exponencial([1.0, 2.0], 3) is None
    assert indicadores.ifr([1.0, 2.0], periodo=14) is None
    assert indicadores.atr(candles_curtos, periodo=14) is None
    assert indicadores.maxima_periodo(candles_curtos, 3) is None
    assert indicadores.minima_periodo(candles_curtos, 3) is None
    assert indicadores.volume_medio(candles_curtos, periodo=21) is None
    assert indicadores.variacao_pct([1.0, 2.0], periodo=5) is None
