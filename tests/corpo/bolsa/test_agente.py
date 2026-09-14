"""Testes do agente do Radar da Bolsa: orquestração ponta a ponta com fakes.

Nenhum teste aqui toca rede, LLM ou Telegram real: `coletar_universo`,
`elegivel`, `detectar` e `dimensionar` são substituídos por fakes via
monkeypatch (o cálculo em si já é testado nos módulos C01/C02); o provider de
LLM é um fake local; `http_post` é um fake que só registra a chamada; e
`cofre_path` aponta para um arquivo temporário com credenciais falsas óbvias.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from stella.adapters.llm.base import LLMProvider, LLMResponse, Message
from stella.corpo.bolsa import agente
from stella.corpo.bolsa.coletor import Serie
from stella.corpo.bolsa.risco import Plano
from stella.corpo.bolsa.setups import Setup

AGORA = datetime(2026, 9, 11, 18, 30, tzinfo=UTC)


# --------------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------------


@dataclass
class _FakeProvider(LLMProvider):
    """Fake de LLMProvider: devolve um texto fixo, ou levanta se configurado."""

    texto: str = "Tese qualquer, sem número."
    levantar: bool = False

    def complete(self, prompt: str) -> LLMResponse:
        if self.levantar:
            raise RuntimeError("provider fake configurado para falhar")
        return LLMResponse(texto=self.texto)

    def chat(self, messages: list[Message]) -> LLMResponse:  # pragma: no cover - não usado aqui
        raise NotImplementedError


class _RegistradorHttpPost:
    """Fake de http_post: registra as chamadas e nunca toca rede."""

    def __init__(self, *, levantar: bool = False) -> None:
        self.chamadas: list[dict[str, Any]] = []
        self.levantar = levantar

    def __call__(self, url: str, json: dict[str, Any] | None = None, timeout: int = 20) -> Any:
        if self.levantar:
            raise ConnectionError("falha fake de rede no envio")
        self.chamadas.append({"url": url, "json": json})
        return _RespostaFake()


class _RespostaFake:
    def raise_for_status(self) -> None:
        return None


def _cofre_fake(tmp_path: Path) -> Path:
    """Arquivo de cofre com credenciais falsas óbvias, nunca reais."""
    caminho = tmp_path / "telegram_fake.json"
    caminho.write_text(
        json.dumps({"bot_token": "FAKE-BOT-TOKEN-0000", "chat_id": "000000"}),
        encoding="utf-8",
    )
    return caminho


def _serie(ticker: str) -> Serie:
    return Serie(ticker=ticker, moeda="BRL", candles=[], coletado_em=AGORA, fonte="fake")


def _setup_compra(ticker: str = "PETR4") -> Setup:
    return Setup(
        ticker=ticker,
        nome="ROMPIMENTO_ALTA",
        cenario="alta",
        direcao="compra",
        preco=49.00,
        data=date(2026, 9, 11),
        forca=75,
        evidencias={"maxima_60": 45.0, "volume_relativo": 1.8},
    )


def _setup_neutro(ticker: str = "VALE3") -> Setup:
    return Setup(
        ticker=ticker,
        nome="FAIXA_LATERAL",
        cenario="lateralizacao",
        direcao="neutro",
        preco=60.0,
        data=date(2026, 9, 11),
        forca=50,
        evidencias={"maxima_60": 62.0, "minima_60": 58.0},
    )


def _plano_aprovado(setup: Setup) -> Plano:
    return Plano(
        entrada=setup.preco,
        stop=setup.preco - 4.0,
        alvo=setup.preco + 6.0,
        risco_por_acao=4.0,
        retorno_por_acao=6.0,
        razao_rr=1.5,
        quantidade=100,
        risco_total=400.0,
        aprovado=True,
        motivo="",
    )


def _plano_sem_direcao(setup: Setup) -> Plano:
    return Plano(
        entrada=setup.preco,
        stop=0.0,
        alvo=0.0,
        risco_por_acao=0.0,
        retorno_por_acao=0.0,
        razao_rr=0.0,
        quantidade=0,
        risco_total=0.0,
        aprovado=False,
        motivo="SEM_DIRECAO",
    )


def _instalar_fakes_orquestracao(
    monkeypatch: pytest.MonkeyPatch,
    *,
    series: list[Serie],
    falhas: list[tuple[str, str]],
    setups_por_ticker: dict[str, list[Setup]],
) -> None:
    """Substitui coletar_universo/elegivel/detectar/dimensionar por fakes."""

    def fake_coletar_universo(
        *, http_get: Any = None, agora: Any = None
    ) -> tuple[list[Serie], list[tuple[str, str]]]:
        return series, falhas

    def fake_elegivel(serie: Serie) -> tuple[bool, str]:
        return True, ""

    def fake_detectar(serie: Serie) -> list[Setup]:
        return setups_por_ticker.get(serie.ticker, [])

    def fake_dimensionar(setup: Setup, serie: Serie, *, capital_risco: float = 500.0) -> Plano:
        if setup.direcao == "compra":
            return _plano_aprovado(setup)
        return _plano_sem_direcao(setup)

    monkeypatch.setattr(agente, "coletar_universo", fake_coletar_universo)
    monkeypatch.setattr(agente, "elegivel", fake_elegivel)
    monkeypatch.setattr(agente, "detectar", fake_detectar)
    monkeypatch.setattr(agente, "dimensionar", fake_dimensionar)


# --------------------------------------------------------------------------
# Testes
# --------------------------------------------------------------------------


def test_fluxo_feliz_envia_card_com_alerta_e_tese_do_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    setup = _setup_compra("PETR4")
    _instalar_fakes_orquestracao(
        monkeypatch,
        series=[_serie("PETR4")],
        falhas=[],
        setups_por_ticker={"PETR4": [setup]},
    )
    provider = _FakeProvider(texto="Rompimento com tendência de alta confirmada.")
    http_post = _RegistradorHttpPost()

    card = agente.rodar_radar_bolsa(
        provider=provider,
        cofre_path=_cofre_fake(tmp_path),
        http_post=http_post,
        agora=AGORA,
    )

    assert len(http_post.chamadas) == 1
    texto_enviado = http_post.chamadas[0]["json"]["text"]
    assert texto_enviado == card
    assert "PETR4" in texto_enviado
    assert "Rompimento com tendência de alta confirmada." in texto_enviado


def test_tese_reprovada_pelo_verificador_cai_para_deterministica(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    setup = _setup_compra("PETR4")
    _instalar_fakes_orquestracao(
        monkeypatch,
        series=[_serie("PETR4")],
        falhas=[],
        setups_por_ticker={"PETR4": [setup]},
    )
    # Número inventado que não bate com nenhum valor calculado do setup/plano.
    provider = _FakeProvider(texto="Vai buscar os R$ 999,00 nos próximos dias.")
    http_post = _RegistradorHttpPost()

    card = agente.rodar_radar_bolsa(
        provider=provider,
        cofre_path=_cofre_fake(tmp_path),
        http_post=http_post,
        agora=AGORA,
    )

    assert "999,00" not in card
    assert len(http_post.chamadas) == 1
    assert "999,00" not in http_post.chamadas[0]["json"]["text"]


def test_provider_levantando_excecao_nao_derruba_a_rodada(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    setup = _setup_compra("PETR4")
    _instalar_fakes_orquestracao(
        monkeypatch,
        series=[_serie("PETR4")],
        falhas=[],
        setups_por_ticker={"PETR4": [setup]},
    )
    provider = _FakeProvider(levantar=True)
    http_post = _RegistradorHttpPost()

    card = agente.rodar_radar_bolsa(
        provider=provider,
        cofre_path=_cofre_fake(tmp_path),
        http_post=http_post,
        agora=AGORA,
    )

    assert "PETR4" in card
    assert len(http_post.chamadas) == 1


def test_zero_setups_envia_card_vazio(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _instalar_fakes_orquestracao(
        monkeypatch,
        series=[_serie("PETR4"), _serie("VALE3")],
        falhas=[],
        setups_por_ticker={},  # nenhum ticker detecta setup algum
    )
    http_post = _RegistradorHttpPost()

    card = agente.rodar_radar_bolsa(
        provider=_FakeProvider(),
        cofre_path=_cofre_fake(tmp_path),
        http_post=http_post,
        agora=AGORA,
    )

    assert "nenhum setup direcional passou os filtros" in card
    assert len(http_post.chamadas) == 1


def test_zero_setups_com_neutros_ainda_envia_card_vazio_com_contagem(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    neutro = _setup_neutro("VALE3")
    _instalar_fakes_orquestracao(
        monkeypatch,
        series=[_serie("VALE3")],
        falhas=[],
        setups_por_ticker={"VALE3": [neutro]},
    )
    http_post = _RegistradorHttpPost()

    card = agente.rodar_radar_bolsa(
        provider=_FakeProvider(),
        cofre_path=_cofre_fake(tmp_path),
        http_post=http_post,
        agora=AGORA,
    )

    assert "nenhum setup direcional passou os filtros" in card
    assert "1 papel em lateralização" in card


def test_falha_total_da_coleta_envia_card_de_erro(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_coletar_universo(
        *, http_get: Any = None, agora: Any = None
    ) -> tuple[list[Serie], list[tuple[str, str]]]:
        raise RuntimeError("falha fake de coleta total")

    monkeypatch.setattr(agente, "coletar_universo", fake_coletar_universo)
    http_post = _RegistradorHttpPost()

    card = agente.rodar_radar_bolsa(
        provider=_FakeProvider(),
        cofre_path=_cofre_fake(tmp_path),
        http_post=http_post,
        agora=AGORA,
    )

    assert "A coleta falhou hoje" in card
    assert "falha fake de coleta total" in card
    assert len(http_post.chamadas) == 1


def test_falha_no_envio_do_telegram_nao_levanta_excecao(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    setup = _setup_compra("PETR4")
    _instalar_fakes_orquestracao(
        monkeypatch,
        series=[_serie("PETR4")],
        falhas=[],
        setups_por_ticker={"PETR4": [setup]},
    )
    http_post = _RegistradorHttpPost(levantar=True)

    card = agente.rodar_radar_bolsa(
        provider=_FakeProvider(texto="Tese sem número nenhum."),
        cofre_path=_cofre_fake(tmp_path),
        http_post=http_post,
        agora=AGORA,
    )

    # Não levantou exceção, e o card ainda é devolvido mesmo sem confirmar envio.
    assert "PETR4" in card
    assert http_post.chamadas == []  # falhou antes de registrar (levanta na chamada)


def test_falhas_parciais_de_coleta_aparecem_no_card(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    setup = _setup_compra("PETR4")
    _instalar_fakes_orquestracao(
        monkeypatch,
        series=[_serie("PETR4")],
        falhas=[("USIM5", "ERRO: timeout")],
        setups_por_ticker={"PETR4": [setup]},
    )
    http_post = _RegistradorHttpPost()

    card = agente.rodar_radar_bolsa(
        provider=_FakeProvider(texto="Tese sem número."),
        cofre_path=_cofre_fake(tmp_path),
        http_post=http_post,
        agora=AGORA,
    )

    assert "USIM5" in card
