from __future__ import annotations

from datetime import date, datetime, timedelta

from stella.corpo.bolsa import setups
from stella.corpo.bolsa.coletor import Candle, Serie

DATA_INICIAL = date(2025, 1, 1)


def _candle(
    fechamento: float,
    dia: int,
    *,
    maxima: float | None = None,
    minima: float | None = None,
    volume: int = 100_000,
) -> Candle:
    return Candle(
        data=DATA_INICIAL + timedelta(days=dia),
        abertura=fechamento,
        maxima=maxima if maxima is not None else fechamento + 1,
        minima=minima if minima is not None else fechamento - 1,
        fechamento=fechamento,
        volume=volume,
    )


def _serie(candles: list[Candle], ticker: str = "TEST3") -> Serie:
    return Serie(
        ticker=ticker,
        moeda="BRL",
        candles=candles,
        coletado_em=datetime(2026, 1, 1),
        fonte="teste",
    )


def _flat_com_gatilho(
    preco_base: float,
    dias_base: int,
    fechamento_gatilho: float,
    *,
    volume_base: int = 100_000,
    volume_gatilho: int = 100_000,
    maxima_gatilho: float | None = None,
    minima_gatilho: float | None = None,
) -> list[Candle]:
    """Monta `dias_base` candles planos (fechamento constante) + 1 candle de gatilho no fim."""
    candles = [_candle(preco_base, i, volume=volume_base) for i in range(dias_base)]
    candles.append(
        _candle(
            fechamento_gatilho,
            dias_base,
            volume=volume_gatilho,
            maxima=maxima_gatilho,
            minima=minima_gatilho,
        )
    )
    return candles


def _regime(preco: float, dias: int, largura: float, dia_inicial: int) -> list[Candle]:
    """`dias` candles com fechamento constante e amplitude (maxima-minima) = largura."""
    return [
        Candle(
            data=DATA_INICIAL + timedelta(days=dia_inicial + i),
            abertura=preco,
            maxima=preco + largura / 2,
            minima=preco - largura / 2,
            fechamento=preco,
            volume=100_000,
        )
        for i in range(dias)
    ]


def _closes(valores: list[float]) -> list[Candle]:
    return [_candle(v, i) for i, v in enumerate(valores)]


# ---------------------------------------------------------------------------
# elegivel
# ---------------------------------------------------------------------------


def test_elegivel_recusa_candles_insuficientes() -> None:
    candles = [_candle(40.0, i) for i in range(199)]
    ok, motivo = setups.elegivel(_serie(candles))
    assert ok is False
    assert motivo == "CANDLES_INSUFICIENTES"


def test_elegivel_recusa_preco_abaixo_de_5() -> None:
    candles = [_candle(4.99, i, volume=1_000_000) for i in range(200)]
    ok, motivo = setups.elegivel(_serie(candles))
    assert ok is False
    assert motivo == "PRECO_MINIMO"


def test_elegivel_recusa_liquidez_abaixo_de_10_milhoes() -> None:
    # fechamento 10.00, volume 50_000 -> liquidez = 500_000 (< 10_000_000)
    candles = [_candle(10.0, i, volume=50_000) for i in range(200)]
    ok, motivo = setups.elegivel(_serie(candles))
    assert ok is False
    assert motivo == "LIQUIDEZ_INSUFICIENTE"


def test_elegivel_aceita_serie_com_preco_e_liquidez_suficientes() -> None:
    # fechamento 40.00, volume 300_000 -> liquidez = 12_000_000 (>= 10_000_000)
    candles = [_candle(40.0, i, volume=300_000) for i in range(200)]
    ok, motivo = setups.elegivel(_serie(candles))
    assert ok is True
    assert motivo == ""


# ---------------------------------------------------------------------------
# ROMPIMENTO_ALTA
# ---------------------------------------------------------------------------
# 199 candles planos em 40.0 (maxima 41, minima 39, volume 100_000) + 1 candle
# de gatilho fechando em 52.0 com o dobro e meio do volume médio.
#
# maxima_60 (dos 199 candles) = 41.0; fechamento(52) > 41 -> rompeu.
# mm200 = (199*40 + 52) / 200 = 8012/200 = 40.06; 52 > 40.06 -> acima da MM200.
# volume_medio_21 = (20*100_000 + 250_000) / 21 = 2_250_000/21 = 107_142.857...
# volume_relativo = 250_000 / 107_142.857... = 2.3333... (>= 2.0 e >= 1.5)
# forca = 50 + 15 (vol>=2.0) + 10 (vol>=1.5) + 15 (52 está 29,8% acima da MM200)
#         + 0 (distância até o extremo rompido: |52-41|/41 = 26,8%, não < 3%)
#       = 90


def test_rompimento_alta_dispara() -> None:
    candles = _flat_com_gatilho(40.0, 199, 52.0, volume_gatilho=250_000)
    setup = setups.detectar_ROMPIMENTO_ALTA(_serie(candles, "ROMP3"))
    assert setup is not None
    assert setup.nome == "ROMPIMENTO_ALTA"
    assert setup.cenario == "alta"
    assert setup.direcao == "compra"
    assert setup.ticker == "ROMP3"
    assert setup.preco == 52.0
    assert setup.data == DATA_INICIAL + timedelta(days=199)
    assert setup.forca == 90
    assert setup.evidencias["volume_relativo"] == round(250_000 / (2_250_000 / 21), 4)
    assert setup.evidencias["mm200"] == 40.06
    assert setup.evidencias["maxima_60"] == 41.0


def test_rompimento_alta_nao_dispara_sem_volume_acima_da_media() -> None:
    # mesmo rompimento de preço e de MM200, mas sem o pico de volume.
    candles = _flat_com_gatilho(40.0, 199, 52.0, volume_gatilho=100_000)
    assert setups.detectar_ROMPIMENTO_ALTA(_serie(candles)) is None


# ---------------------------------------------------------------------------
# PULLBACK_TENDENCIA
# ---------------------------------------------------------------------------
# Tendência construída em degraus (20 -> 30 -> 40 -> 50 -> 60) seguida de um
# recuo gradual até 50, terminando o pregão de hoje em 50.0 (mínima do dia
# em 49.0, por padrão, que fica abaixo da MM20).
# Valores conferidos com stella.corpo.bolsa.indicadores diretamente (não
# reaproveitados do motor de setups): mm20=54.25, mm50=33.7, mm200=23.425,
# ifr=59.95930813638875 (dentro de 35-60).
_PULLBACK_CLOSES = (
    [20.0] * 180
    + [30.0, 40.0, 50.0, 60.0]
    + [60.0] * 6
    + [59.0, 58.0, 57.0, 56.0, 55.0, 54.0, 53.0, 52.0, 51.0, 50.0]
)


def test_pullback_tendencia_dispara() -> None:
    setup = setups.detectar_PULLBACK_TENDENCIA(_serie(_closes(_PULLBACK_CLOSES)))
    assert setup is not None
    assert setup.nome == "PULLBACK_TENDENCIA"
    assert setup.cenario == "alta"
    assert setup.direcao == "compra"
    assert setup.preco == 50.0
    assert setup.evidencias["mm20"] == 54.25
    assert setup.evidencias["mm50"] == 33.7
    assert setup.evidencias["mm200"] == 23.425
    # (50 - 23.425) / 23.425 = 1.1345... > 0.10 -> bonus de MM200 concedido.
    assert setup.forca == 65


def test_pullback_tendencia_nao_dispara_com_ifr_fora_da_faixa() -> None:
    # mesma estrutura de tendência, mas com um único dia de queda (55): o IFR
    # sobe para ~68.7, fora da faixa 35-60 exigida.
    closes = [20.0] * 180 + [30.0, 40.0, 50.0, 60.0] + [60.0] * 15 + [55.0]
    assert setups.detectar_PULLBACK_TENDENCIA(_serie(_closes(closes))) is None


# ---------------------------------------------------------------------------
# SOBREVENDA_TENDENCIA
# ---------------------------------------------------------------------------
# Alta de 30 para 40 sustentada, seguida de 9 dias de queda de 1 em 1 até 31.
# mm200 = 30.725; ifr = 27.880649474255378 (< 30); fechamento(31) > mm200.
_SOBREVENDA_CLOSES = (
    [30.0] * 181 + [40.0] * 10 + [39.0, 38.0, 37.0, 36.0, 35.0, 34.0, 33.0, 32.0, 31.0]
)


def test_sobrevenda_tendencia_dispara() -> None:
    setup = setups.detectar_SOBREVENDA_TENDENCIA(_serie(_closes(_SOBREVENDA_CLOSES)))
    assert setup is not None
    assert setup.nome == "SOBREVENDA_TENDENCIA"
    assert setup.cenario == "alta"
    assert setup.direcao == "compra"
    assert setup.preco == 31.0
    assert setup.evidencias["mm200"] == 30.725
    assert setup.evidencias["ifr"] == round(27.880649474255378, 4)
    # (31-30.725)/30.725 = 0.89% (não > 10%); ifr 27.88 não é < 25.
    # Nenhum bônus se aplica.
    assert setup.forca == 50


def test_sobrevenda_tendencia_nao_dispara_com_ifr_acima_de_30() -> None:
    # apenas 5 dias de queda: ifr sobe para ~44.98, não fica abaixo de 30.
    closes = [30.0] * 185 + [40.0] * 10 + [39.0, 38.0, 37.0, 36.0, 35.0]
    assert setups.detectar_SOBREVENDA_TENDENCIA(_serie(_closes(closes))) is None


# ---------------------------------------------------------------------------
# PERDA_SUPORTE
# ---------------------------------------------------------------------------
# 199 candles planos em 40.0 + 1 candle de gatilho fechando em 28.0 com o
# quase-triplo do volume médio.
# minima_60 (dos 199 candles) = 39.0; fechamento(28) < 39 -> rompeu o suporte.
# mm200 = (199*40 + 28)/200 = 39.94; 28 < 39.94 -> abaixo da MM200.
# volume_medio_21 = (20*100_000 + 300_000)/21 = 109_523.809...
# volume_relativo = 300_000 / 109_523.809... = 2.7391304347826084 (>= 2.0)
# ifr = 0.0 (perda medía dominante após queda única) -> sem bônus de IFR.
# forca = 50 + 15 (vol>=2.0) + 10 (vol>=1.5) + 0 (ifr) + 0 (distância do
#         extremo: |28-39|/39 = 28,2%, não < 3%) = 75


def test_perda_suporte_dispara() -> None:
    candles = _flat_com_gatilho(40.0, 199, 28.0, volume_gatilho=300_000)
    setup = setups.detectar_PERDA_SUPORTE(_serie(candles, "PERD3"))
    assert setup is not None
    assert setup.nome == "PERDA_SUPORTE"
    assert setup.cenario == "baixa"
    assert setup.direcao == "venda"
    assert setup.ticker == "PERD3"
    assert setup.preco == 28.0
    assert setup.forca == 75
    assert setup.evidencias["mm200"] == 39.94
    assert setup.evidencias["minima_60"] == 39.0
    assert setup.evidencias["ifr"] == 0.0


def test_perda_suporte_nao_dispara_sem_volume_acima_da_media() -> None:
    candles = _flat_com_gatilho(40.0, 199, 28.0, volume_gatilho=100_000)
    assert setups.detectar_PERDA_SUPORTE(_serie(candles)) is None


# ---------------------------------------------------------------------------
# FAIXA_LATERAL
# ---------------------------------------------------------------------------
# 199 candles planos em 50.0 + 1 candle de gatilho fechando em 51.0.
# maxima_60 = 52.0; minima_60 = 49.0; amplitude = 3/49 = 6,12% (< 12%).
# variacao_pct(60) = 2,0% (< 5%).


def test_faixa_lateral_dispara() -> None:
    candles = _flat_com_gatilho(50.0, 199, 51.0)
    setup = setups.detectar_FAIXA_LATERAL(_serie(candles, "LATE3"))
    assert setup is not None
    assert setup.nome == "FAIXA_LATERAL"
    assert setup.cenario == "lateralizacao"
    assert setup.direcao == "neutro"
    assert setup.preco == 51.0
    assert setup.forca == 50
    assert setup.evidencias["maxima_60"] == 52.0
    assert setup.evidencias["minima_60"] == 49.0
    assert setup.evidencias["variacao_pct_60"] == 2.0


def test_faixa_lateral_nao_dispara_com_amplitude_acima_de_12_pct() -> None:
    # mesmo fechamento (variação de apenas 2%), mas o candle de hoje tem uma
    # sombra muito larga (45 a 70): amplitude de 60 dias estoura para 55,6%.
    candles = _flat_com_gatilho(50.0, 199, 51.0, maxima_gatilho=70.0, minima_gatilho=45.0)
    assert setups.detectar_FAIXA_LATERAL(_serie(candles)) is None


# ---------------------------------------------------------------------------
# COMPRESSAO_VOLATILIDADE
# ---------------------------------------------------------------------------
# 150 dias com amplitude diária de 10 (regime "alto"), seguidos de 50 dias
# com amplitude diária de 1 (regime "comprimido"). Conferido com
# stella.corpo.bolsa.indicadores.atr diretamente:
# atr_hoje = 1.2213137213739738; média dos 60 ATRs anteriores = 4.548360131679406.
# 1.2213... < 0.70 * 4.5484... (= 3.1839) -> comprimido.
_COMPRESSAO_ALTO = _regime(50.0, 150, 10.0, 0)
_COMPRESSAO_COMPRIMIDO = _regime(50.0, 50, 1.0, 150)


def test_compressao_volatilidade_dispara() -> None:
    candles = _COMPRESSAO_ALTO + _COMPRESSAO_COMPRIMIDO
    setup = setups.detectar_COMPRESSAO_VOLATILIDADE(_serie(candles, "COMP3"))
    assert setup is not None
    assert setup.nome == "COMPRESSAO_VOLATILIDADE"
    assert setup.cenario == "volatilidade"
    assert setup.direcao == "neutro"
    assert setup.forca == 50
    assert setup.evidencias["atr_14"] == round(1.2213137213739738, 4)
    assert setup.evidencias["atr_medio_60d"] == round(4.548360131679406, 4)


def test_compressao_volatilidade_nao_dispara_sem_compressao() -> None:
    # série totalmente plana: ATR de hoje é igual à média histórica (razão
    # 1.0), nunca cai abaixo de 70%.
    candles = [_candle(50.0, i) for i in range(200)]
    assert setups.detectar_COMPRESSAO_VOLATILIDADE(_serie(candles)) is None


def test_compressao_volatilidade_nao_dispara_quando_e_faixa_lateral() -> None:
    # mesma lógica de compressão (regimes de amplitude 3 -> 0.5), mas a
    # amplitude de 60 dias fica estreita o bastante para também ser
    # FAIXA_LATERAL -- a exclusão deve barrar o COMPRESSAO_VOLATILIDADE.
    alto = _regime(50.0, 150, 3.0, 0)
    comprimido = _regime(50.0, 50, 0.5, 150)
    serie = _serie(alto + comprimido)
    assert setups.detectar_FAIXA_LATERAL(serie) is not None
    assert setups.detectar_COMPRESSAO_VOLATILIDADE(serie) is None


# ---------------------------------------------------------------------------
# evidencias e detectar()
# ---------------------------------------------------------------------------


def test_evidencias_contem_apenas_numeros() -> None:
    candles = _flat_com_gatilho(40.0, 199, 52.0, volume_gatilho=250_000)
    setup = setups.detectar_ROMPIMENTO_ALTA(_serie(candles))
    assert setup is not None
    assert setup.evidencias
    for valor in setup.evidencias.values():
        assert isinstance(valor, int | float)
        assert not isinstance(valor, bool)


def test_detectar_e_deterministico_e_devolve_apenas_os_setups_disparados() -> None:
    candles = _flat_com_gatilho(40.0, 199, 52.0, volume_gatilho=250_000)
    serie = _serie(candles, "ROMP3")
    primeira = setups.detectar(serie)
    segunda = setups.detectar(serie)
    assert primeira == segunda
    assert [s.nome for s in primeira] == ["ROMPIMENTO_ALTA"]
