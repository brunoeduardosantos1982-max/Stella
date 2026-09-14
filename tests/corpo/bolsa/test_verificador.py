"""Testes do verificador de números: a razão de existir do contrato C03.

Nenhum teste aqui toca rede, LLM ou Telegram — verificador.py é puro.
"""

from __future__ import annotations

from datetime import date

import pytest

from stella.corpo.bolsa.risco import Plano
from stella.corpo.bolsa.setups import Setup
from stella.corpo.bolsa.verificador import extrair_numeros, numeros_permitidos, verificar


def _setup(**overrides: object) -> Setup:
    base = dict(
        ticker="PETR4",
        nome="ROMPIMENTO_ALTA",
        cenario="alta",
        direcao="compra",
        preco=49.00,
        data=date(2026, 9, 11),
        forca=75,
        evidencias={"maxima_60": 51.2, "volume_relativo": 1.8, "mm200": 44.0},
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


class TestExtrairNumeros:
    def test_extrai_decimal_com_virgula(self) -> None:
        assert extrair_numeros("A ação chegou a 49,00 hoje.") == [49.0]

    def test_extrai_milhar_com_ponto_e_decimal_com_virgula(self) -> None:
        assert extrair_numeros("Volume de 1.234,56 mil.") == [1234.56]

    def test_extrai_percentual(self) -> None:
        assert extrair_numeros("Subiu 12% no mês.") == [12.0]

    def test_extrai_valor_com_prefixo_moeda(self) -> None:
        assert extrair_numeros("Fechou a R$ 49,00.") == [49.0]

    def test_nao_extrai_numero_colado_a_ticker(self) -> None:
        assert extrair_numeros("PETR4 rompeu a máxima.") == []

    def test_nao_extrai_ano(self) -> None:
        assert extrair_numeros("Em 2026 a ação decolou.") == []

    def test_extrai_varios_numeros_na_ordem(self) -> None:
        texto = "Rompimento acima dos 51,20 com volume 1,8 vez a média."
        assert extrair_numeros(texto) == [51.2, 1.8]

    def test_ano_com_decimal_nao_e_tratado_como_ano(self) -> None:
        # 2026,50 nao e um ano por extenso (tem vírgula) - deve ser extraído.
        assert extrair_numeros("Alvo teórico de 2026,50.") == [2026.5]


class TestVerificar:
    def test_aprova_tese_so_com_numeros_permitidos(self) -> None:
        setup = _setup()
        plano = _plano()
        tese = "Rompimento acima dos 51,20 com volume 1,8 vez a média."
        assert verificar(tese, setup, plano) == (True, [])

    def test_aprova_tese_com_periodo_de_indicador(self) -> None:
        setup = _setup()
        plano = _plano()
        tese = "A ação segue acima da média de 200 dias, sustentando a força compradora."
        aprovado, intrusos = verificar(tese, setup, plano)
        assert aprovado is True
        assert intrusos == []

    def test_reprova_numero_inventado_do_alvo(self) -> None:
        setup = _setup(evidencias={"maxima_60": 51.2, "volume_relativo": 1.8})
        plano = _plano(entrada=49.00)
        tese = "A ação rompeu os R$ 51,20 com volume 1,8 vez a média e deve buscar os R$ 58,00."
        assert verificar(tese, setup, plano) == (False, [58.0])

    def test_aceita_arredondamento_dentro_da_tolerancia(self) -> None:
        setup = _setup()
        plano = _plano()
        # entrada real é 49.00; 49,01 está dentro de 1,1% de tolerância relativa.
        tese = "Entrada nos 49,01 aproximadamente."
        aprovado, intrusos = verificar(tese, setup, plano)
        assert aprovado is True
        assert intrusos == []

    def test_reprova_numero_fora_da_tolerancia(self) -> None:
        setup = _setup()
        plano = _plano()
        # 55,00 não é período de indicador nem casa (dentro da tolerância) com
        # nenhum valor de evidência, preço, força ou plano deste fixture.
        tese = "Entrada por volta dos 55,00."
        aprovado, intrusos = verificar(tese, setup, plano)
        assert aprovado is False
        assert intrusos == [55.0]

    def test_reprova_mais_de_um_intruso(self) -> None:
        setup = _setup()
        plano = _plano()
        tese = "Alvo de 85,00 e depois 133,00."
        aprovado, intrusos = verificar(tese, setup, plano)
        assert aprovado is False
        assert set(intrusos) == {85.0, 133.0}

    def test_texto_sem_numero_e_sempre_aprovado(self) -> None:
        setup = _setup()
        plano = _plano()
        tese = "Rompimento com volume forte e tendência a favor."
        assert verificar(tese, setup, plano) == (True, [])


class TestNumerosPermitidos:
    def test_inclui_periodos_evidencias_preco_forca_e_plano(self) -> None:
        setup = _setup()
        plano = _plano()
        permitidos = numeros_permitidos(setup, plano)
        assert 200.0 in permitidos  # período
        assert 51.2 in permitidos  # evidência
        assert 49.0 in permitidos  # preço do setup / entrada do plano
        assert 75.0 in permitidos  # força
        assert 1.5 in permitidos  # razão_rr
        assert 200.0 in permitidos  # quantidade também é 200 aqui

    @pytest.mark.parametrize("valor", [9.0, 14.0, 20.0, 21.0, 50.0, 60.0, 100.0, 200.0])
    def test_todos_os_periodos_estao_sempre_presentes(self, valor: float) -> None:
        setup = _setup(evidencias={})
        plano = _plano()
        assert valor in numeros_permitidos(setup, plano)
