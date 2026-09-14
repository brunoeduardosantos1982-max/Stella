"""Testes do apresentador: formatação do card do Radar da Bolsa.

Nenhum teste aqui toca rede, LLM ou Telegram — apresentador.py só formata
texto a partir de Setup/Plano já calculados.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from stella.corpo.bolsa.apresentador import (
    montar_bloco_alerta,
    montar_card,
    montar_card_erro,
    montar_card_vazio,
    tese_deterministica,
)
from stella.corpo.bolsa.risco import Plano
from stella.corpo.bolsa.setups import Setup
from stella.corpo.bolsa.verificador import extrair_numeros

AGORA = datetime(2026, 9, 11, 18, 30, tzinfo=UTC)


def _setup(**overrides: object) -> Setup:
    base = dict(
        ticker="PETR4",
        nome="ROMPIMENTO_ALTA",
        cenario="alta",
        direcao="compra",
        preco=49.00,
        data=date(2026, 9, 11),
        forca=75,
        evidencias={"maxima_60": 51.2, "volume_relativo": 1.8},
    )
    base.update(overrides)
    return Setup(**base)  # type: ignore[arg-type]


def _plano(**overrides: object) -> Plano:
    base = dict(
        entrada=49.00,
        stop=47.00,
        alvo=52.00,
        risco_por_acao=2.00,
        retorno_por_acao=3.00,
        razao_rr=1.5,
        quantidade=200,
        risco_total=400.00,
        aprovado=True,
        motivo="",
    )
    base.update(overrides)
    return Plano(**base)  # type: ignore[arg-type]


def _neutro(nome: str, ticker: str = "VALE3") -> Setup:
    return Setup(
        ticker=ticker,
        nome=nome,
        cenario="lateralizacao" if nome == "FAIXA_LATERAL" else "volatilidade",
        direcao="neutro",
        preco=60.0,
        data=date(2026, 9, 11),
        forca=50,
        evidencias={"maxima_60": 60.0, "minima_60": 55.0},
    )


class TestMontarBlocoAlerta:
    def test_contem_ticker_nome_cenario_forca_e_valores_do_plano(self) -> None:
        bloco = montar_bloco_alerta(_setup(), _plano(), "Rompimento com força compradora.")
        assert "PETR4" in bloco
        assert "alta" in bloco
        assert "força 75/100" in bloco
        assert "49,00" in bloco  # entrada
        assert "47,00" in bloco  # stop
        assert "52,00" in bloco  # alvo
        assert "1,5" in bloco  # razão risco/retorno
        assert "200 ações" in bloco  # tamanho

    def test_escapa_html_vindo_da_tese(self) -> None:
        bloco = montar_bloco_alerta(_setup(), _plano(), "<script>alert(1)</script>")
        assert "<script>" not in bloco
        assert "&lt;script&gt;" in bloco


class TestTeseDeterministica:
    def test_nao_inventa_numero_para_nenhum_setup_conhecido(self) -> None:
        for nome in (
            "ROMPIMENTO_ALTA",
            "PULLBACK_TENDENCIA",
            "SOBREVENDA_TENDENCIA",
            "PERDA_SUPORTE",
            "FAIXA_LATERAL",
            "COMPRESSAO_VOLATILIDADE",
        ):
            tese = tese_deterministica(_setup(nome=nome), _plano())
            assert extrair_numeros(tese) == []

    def test_setup_desconhecido_ainda_assim_nao_inventa_numero(self) -> None:
        tese = tese_deterministica(_setup(nome="ALGO_NOVO"), _plano())
        assert extrair_numeros(tese) == []


class TestMontarCard:
    def test_card_com_blocos_traz_aviso_de_nao_recomendacao(self) -> None:
        bloco = montar_bloco_alerta(_setup(), _plano(), "Tese qualquer.")
        card = montar_card([bloco], AGORA)
        assert "não recomendação de investimento" in card
        assert "Fonte: yahoo-chart" in card

    def test_linha_de_cenario_aparece_com_contagem_certa(self) -> None:
        neutros = [
            _neutro("FAIXA_LATERAL", "VALE3"),
            _neutro("FAIXA_LATERAL", "ITUB4"),
            _neutro("FAIXA_LATERAL", "BBAS3"),
            _neutro("FAIXA_LATERAL", "B3SA3"),
            _neutro("COMPRESSAO_VOLATILIDADE", "WEGE3"),
        ]
        card = montar_card([], AGORA, neutros=neutros)
        assert "4 papéis em lateralização" in card
        assert "1 em compressão de volatilidade" in card

    def test_linha_de_cenario_some_quando_nao_ha_neutros(self) -> None:
        card = montar_card([], AGORA, neutros=[])
        assert "Cenário:" not in card

    def test_falhas_de_coleta_aparecem_no_rodape(self) -> None:
        card = montar_card([], AGORA, falhas=[("USIM5", "ERRO: timeout")])
        assert "1 ticker(s) não responderam" in card
        assert "USIM5" in card

    def test_neutro_nunca_vira_bloco_de_alerta(self) -> None:
        # montar_card só recebe blocos já prontos; um Setup neutro não tem
        # bloco algum - só pode aparecer via a linha de contagem.
        neutros = [_neutro("FAIXA_LATERAL")]
        card = montar_card([], AGORA, neutros=neutros)
        assert "🎯" not in card  # marcador exclusivo de bloco de alerta
        assert "VALE3" not in card


class TestMontarCardVazio:
    def test_diz_quantos_tickers_foram_varridos(self) -> None:
        card = montar_card_vazio(AGORA, varridos=38)
        assert "38" in card
        assert "nenhum setup direcional passou os filtros" in card

    def test_traz_linha_de_cenario_quando_ha_neutros(self) -> None:
        card = montar_card_vazio(AGORA, neutros=[_neutro("COMPRESSAO_VOLATILIDADE")], varridos=38)
        assert "1 em compressão de volatilidade" in card

    def test_traz_aviso_de_nao_recomendacao(self) -> None:
        card = montar_card_vazio(AGORA, varridos=0)
        assert "não recomendação de investimento" in card


class TestMontarCardErro:
    def test_diz_o_que_falhou(self) -> None:
        card = montar_card_erro("timeout na coleta do universo", AGORA)
        assert "timeout na coleta do universo" in card

    def test_escapa_html_do_erro(self) -> None:
        card = montar_card_erro("<script>x</script>", AGORA)
        assert "<script>" not in card

    def test_traz_aviso_de_nao_recomendacao(self) -> None:
        card = montar_card_erro("erro qualquer", AGORA)
        assert "não recomendação de investimento" in card


def test_card_avisa_quando_nao_houve_pregao_hoje() -> None:
    """Card com dado de outro dia diz isso, em vez de carimbar a data de hoje."""
    agora = datetime(2026, 9, 14, 18, 30, tzinfo=UTC)
    card = montar_card_vazio(agora, varridos=40, data_pregao=date(2026, 9, 11))
    assert "Sem pregão hoje" in card
    assert "11/09" in card


def test_card_nao_avisa_quando_o_dado_e_de_hoje() -> None:
    """Em dia de pregão o aviso some: ele é exceção, não decoração."""
    agora = datetime(2026, 9, 14, 18, 30, tzinfo=UTC)
    card = montar_card_vazio(agora, varridos=40, data_pregao=date(2026, 9, 14))
    assert "Sem pregão" not in card


def test_card_cheio_tambem_avisa_sem_pregao() -> None:
    """O aviso vale para o card com alertas, não só para o vazio."""
    agora = datetime(2026, 9, 14, 18, 30, tzinfo=UTC)
    card = montar_card(["<b>bloco</b>"], agora, data_pregao=date(2026, 9, 11))
    assert "Sem pregão hoje" in card
    assert "<b>bloco</b>" in card


def test_card_da_manha_diz_que_o_pregao_ainda_vai_abrir() -> None:
    """Segunda 09:15 com dado de sexta: o pregão de hoje ainda não abriu.

    Dizer "sem pregão hoje" aqui seria mentira, e é o caso normal do card da
    manhã, que roda antes da abertura das 10h.
    """
    agora = datetime(2026, 9, 14, 9, 15, tzinfo=UTC)  # segunda-feira
    card = montar_card_vazio(agora, varridos=40, data_pregao=date(2026, 9, 11))
    assert "abre às 10h" in card
    assert "Sem pregão hoje" not in card
    assert "11/09" in card


def test_card_do_fim_de_semana_diz_que_nao_houve_pregao() -> None:
    """Domingo: não é pré-abertura, é ausência de pregão mesmo."""
    agora = datetime(2026, 9, 13, 9, 15, tzinfo=UTC)  # domingo
    card = montar_card_vazio(agora, varridos=40, data_pregao=date(2026, 9, 11))
    assert "Sem pregão hoje" in card
    assert "abre às 10h" not in card


def test_dia_util_depois_da_abertura_sem_candle_e_ausencia_de_pregao() -> None:
    """Dia útil às 18:30 sem candle de hoje: feriado, não pré-abertura."""
    agora = datetime(2026, 9, 14, 18, 30, tzinfo=UTC)  # segunda, pos-fechamento
    card = montar_card_vazio(agora, varridos=40, data_pregao=date(2026, 9, 11))
    assert "Sem pregão hoje" in card
