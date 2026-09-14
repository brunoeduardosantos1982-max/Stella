from __future__ import annotations

from datetime import date, datetime, timedelta

from stella.corpo.bolsa import risco
from stella.corpo.bolsa.coletor import Candle, Serie
from stella.corpo.bolsa.risco import Plano
from stella.corpo.bolsa.setups import Setup

DATA_INICIAL = date(2025, 1, 1)


def _serie_atr(fechamento: float, meia_amplitude: float, dias: int = 20) -> Serie:
    """Série de candles planos cujo ATR(14) converge exatamente para `2*meia_amplitude`.

    Fechamento constante e maxima/minima = fechamento +/- meia_amplitude fazem
    o True Range de cada dia valer sempre `2*meia_amplitude` (maxima-minima),
    que também é o maior dos três termos do TR quando o fechamento não muda
    de um dia para o outro. O ATR de Wilder, semeado por essa média
    constante, permanece nesse valor por toda a série.
    """
    candles = [
        Candle(
            data=DATA_INICIAL + timedelta(days=i),
            abertura=fechamento,
            maxima=fechamento + meia_amplitude,
            minima=fechamento - meia_amplitude,
            fechamento=fechamento,
            volume=100_000,
        )
        for i in range(dias)
    ]
    return Serie(
        ticker="TEST3",
        moeda="BRL",
        candles=candles,
        coletado_em=datetime(2026, 1, 1),
        fonte="teste",
    )


def _serie_sem_atr() -> Serie:
    # 5 candles: menos que o mínimo de 15 exigido por atr(..., periodo=14).
    candles = [
        Candle(
            data=DATA_INICIAL + timedelta(days=i),
            abertura=50.0,
            maxima=51.0,
            minima=49.0,
            fechamento=50.0,
            volume=100_000,
        )
        for i in range(5)
    ]
    return Serie(
        ticker="TEST3",
        moeda="BRL",
        candles=candles,
        coletado_em=datetime(2026, 1, 1),
        fonte="teste",
    )


def _setup(
    *,
    direcao: str,
    preco: float,
    nome: str = "ROMPIMENTO_ALTA",
    cenario: str = "alta",
    ticker: str = "TEST3",
    forca: int = 80,
) -> Setup:
    return Setup(
        ticker=ticker,
        nome=nome,
        cenario=cenario,
        direcao=direcao,
        preco=preco,
        data=DATA_INICIAL,
        forca=forca,
        evidencias={},
    )


# ---------------------------------------------------------------------------
# Exemplo do item 4 do contrato, conferido à mão.
# ---------------------------------------------------------------------------


def test_dimensionar_exemplo_do_contrato() -> None:
    setup = _setup(direcao="compra", preco=50.0)
    serie = _serie_atr(50.0, 0.5)  # ATR(14) == 1.0

    plano = risco.dimensionar(setup, serie, capital_risco=500.0)

    assert plano.entrada == 50.00
    assert plano.stop == 48.00  # 50 - 2*1
    assert plano.alvo == 53.00  # 50 + 3*1
    assert plano.risco_por_acao == 2.00
    assert plano.retorno_por_acao == 3.00
    assert plano.razao_rr == 1.5
    assert plano.quantidade == 200  # floor(500/2)=250, arredondado p/ baixo em lote de 100
    assert plano.risco_total == 400.00  # 200 * 2.00
    assert plano.aprovado is True
    assert plano.motivo == ""


def test_dimensionar_espelha_stop_e_alvo_na_venda() -> None:
    setup = _setup(direcao="venda", preco=100.0, nome="PERDA_SUPORTE", cenario="baixa")
    serie = _serie_atr(100.0, 1.0)  # ATR(14) == 2.0

    plano = risco.dimensionar(setup, serie, capital_risco=500.0)

    assert plano.entrada == 100.00
    assert plano.stop == 104.00  # 100 + 2*2
    assert plano.alvo == 94.00  # 100 - 3*2
    assert plano.risco_por_acao == 4.00
    assert plano.retorno_por_acao == 6.00
    assert plano.razao_rr == 1.5
    assert plano.quantidade == 100  # floor(500/4)=125, arredondado p/ baixo em lote de 100
    assert plano.risco_total == 400.00
    assert plano.aprovado is True


# ---------------------------------------------------------------------------
# Motivos de reprovação, cada um em sua lista fechada.
# ---------------------------------------------------------------------------


def test_dimensionar_sem_atr() -> None:
    setup = _setup(direcao="compra", preco=50.0)
    plano = risco.dimensionar(setup, _serie_sem_atr())

    assert plano.aprovado is False
    assert plano.motivo == "SEM_ATR"
    assert plano.entrada == 50.00
    assert plano.stop == 0.0
    assert plano.alvo == 0.0
    assert plano.risco_por_acao == 0.0
    assert plano.retorno_por_acao == 0.0
    assert plano.razao_rr == 0.0
    assert plano.quantidade == 0
    assert plano.risco_total == 0.0


def test_dimensionar_sem_direcao_para_setup_neutro() -> None:
    setup = _setup(direcao="neutro", preco=50.0, nome="FAIXA_LATERAL", cenario="lateralizacao")
    serie = _serie_atr(50.0, 0.5)  # ATR válido (1.0), para provar que o motivo é a direção

    plano = risco.dimensionar(setup, serie)

    assert plano.aprovado is False
    assert plano.motivo == "SEM_DIRECAO"
    assert plano.entrada == 50.00
    assert plano.stop == 0.0
    assert plano.alvo == 0.0
    assert plano.risco_por_acao == 0.0
    assert plano.retorno_por_acao == 0.0
    assert plano.razao_rr == 0.0
    assert plano.quantidade == 0
    assert plano.risco_total == 0.0


def test_dimensionar_rr_insuficiente() -> None:
    setup = _setup(direcao="compra", preco=50.0)
    serie = _serie_atr(50.0, 0.5)  # ATR == 1.0

    # multiplo_alvo=2.0 -> alvo=52, retorno=2, risco=2, razao_rr=1.0 (< 1.5)
    plano = risco.dimensionar(setup, serie, capital_risco=500.0, multiplo_alvo=2.0)

    assert plano.aprovado is False
    assert plano.motivo == "RR_INSUFICIENTE"
    assert plano.stop == 48.00
    assert plano.alvo == 52.00
    assert plano.risco_por_acao == 2.00
    assert plano.retorno_por_acao == 2.00
    assert plano.razao_rr == 1.0
    assert plano.quantidade == 0
    assert plano.risco_total == 0.0


def test_dimensionar_lote_minimo_traz_quantidade_fracionaria() -> None:
    setup = _setup(direcao="compra", preco=50.0)
    serie = _serie_atr(50.0, 1.5)  # ATR == 3.0

    # stop=44, risco_por_acao=6; alvo=59, retorno_por_acao=9; razao_rr=1.5 (aprova o RR)
    # quantidade_bruta = floor(500/6) = 83; 83 // 100 * 100 = 0 -> lote mínimo não atingido.
    plano = risco.dimensionar(setup, serie, capital_risco=500.0)

    assert plano.aprovado is False
    assert plano.motivo == "LOTE_MINIMO"
    assert plano.razao_rr == 1.5
    assert plano.quantidade == 83  # quantidade fracionária, para o alerta do mercado fracionário
    assert plano.risco_total == 498.00  # 83 * 6.00


def test_dimensionar_arredonda_quantidade_para_multiplo_de_100() -> None:
    setup = _setup(direcao="compra", preco=50.0)
    serie = _serie_atr(50.0, 0.5)  # ATR == 1.0, risco_por_acao == 2.0

    # floor(999/2) = 499; 499 // 100 * 100 = 400
    plano = risco.dimensionar(setup, serie, capital_risco=999.0)

    assert plano.quantidade == 400
    assert plano.aprovado is True
    assert plano.risco_total == 800.00  # 400 * 2.00


def test_dimensionar_stop_invalido_quando_stop_fica_negativo_ou_zero() -> None:
    setup = _setup(direcao="compra", preco=5.0)
    serie = _serie_atr(5.0, 1.5)  # ATR == 3.0 -> stop = 5 - 2*3 = -1 (<= 0)

    plano = risco.dimensionar(setup, serie)

    assert plano.aprovado is False
    assert plano.motivo == "STOP_INVALIDO"
    assert plano.entrada == 5.00
    assert plano.stop == 0.0
    assert plano.quantidade == 0


# ---------------------------------------------------------------------------
# ranquear
# ---------------------------------------------------------------------------


def _plano_aprovado(razao_rr: float) -> Plano:
    return Plano(
        entrada=10.0,
        stop=9.0,
        alvo=12.0,
        risco_por_acao=1.0,
        retorno_por_acao=razao_rr,
        razao_rr=razao_rr,
        quantidade=100,
        risco_total=100.0,
        aprovado=True,
        motivo="",
    )


def _plano_reprovado() -> Plano:
    return Plano(
        entrada=10.0,
        stop=0.0,
        alvo=0.0,
        risco_por_acao=0.0,
        retorno_por_acao=0.0,
        razao_rr=0.0,
        quantidade=0,
        risco_total=0.0,
        aprovado=False,
        motivo="RR_INSUFICIENTE",
    )


def test_ranquear_ordena_por_forca_depois_razao_rr_depois_ticker() -> None:
    setup_a = _setup(direcao="compra", preco=10.0, ticker="AAAA3", forca=80)
    setup_b = _setup(direcao="compra", preco=10.0, ticker="ZZZZ3", forca=80)
    setup_c = _setup(direcao="compra", preco=10.0, ticker="BBBB3", forca=90)
    setup_d = _setup(direcao="compra", preco=10.0, ticker="CCCC3", forca=80)
    setup_e = _setup(direcao="compra", preco=10.0, ticker="DDDD3", forca=99)

    pares = [
        (setup_a, _plano_aprovado(2.0)),  # forca 80, rr 2.0
        (setup_b, _plano_aprovado(2.0)),  # forca 80, rr 2.0 (empate total com A, exceto ticker)
        (setup_c, _plano_aprovado(1.0)),  # forca 90, rr 1.0 -> maior forca vence
        (setup_d, _plano_aprovado(3.0)),  # forca 80, rr 3.0 -> mesma forca de A/B, rr maior
        (setup_e, _plano_reprovado()),  # reprovado -> nunca entra no ranking
    ]

    resultado = risco.ranquear(pares, maximo=3)

    assert [setup.ticker for setup, _ in resultado] == ["BBBB3", "CCCC3", "AAAA3"]
