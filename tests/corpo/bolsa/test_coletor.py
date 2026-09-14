from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Any

import pytest

from stella.corpo.bolsa import coletor

AGORA = datetime(2026, 9, 13, 12, 0, tzinfo=coletor.FUSO)


class _RespostaFake:
    """Fake mínimo de httpx.Response: json() e text, nada de rede."""

    def __init__(self, payload: Any) -> None:
        self._payload = payload
        self.text = payload if isinstance(payload, str) else json.dumps(payload)

    def json(self) -> Any:
        if isinstance(self._payload, str):
            raise ValueError("resposta não é JSON")
        return self._payload


def _payload_valido(timestamps: list[int] | None = None) -> dict[str, Any]:
    ts = timestamps or [1786453200, 1786539600]
    n = len(ts)
    return {
        "chart": {
            "error": None,
            "result": [
                {
                    "meta": {"currency": "BRL", "symbol": "VALE3.SA"},
                    "timestamp": ts,
                    "indicators": {
                        "quote": [
                            {
                                "open": [76.31] * n,
                                "high": [76.70] * n,
                                "low": [73.71] * n,
                                "close": [74.40] * n,
                                "volume": [36211800] * n,
                            }
                        ]
                    },
                }
            ],
        }
    }


def test_simbolo_yahoo_adiciona_sufixo_sa() -> None:
    assert coletor.simbolo_yahoo("petr4") == "PETR4.SA"
    assert coletor.simbolo_yahoo("PETR4") == "PETR4.SA"


def test_simbolo_yahoo_nao_duplica_sufixo_existente() -> None:
    assert coletor.simbolo_yahoo("VALE3.SA") == "VALE3.SA"
    assert coletor.simbolo_yahoo("vale3.sa") == "VALE3.SA"


def test_parsear_chart_levanta_erro_do_chart_error() -> None:
    payload = {
        "chart": {
            "error": {"code": "Not Found", "description": "No data found, symbol may be delisted"},
            "result": None,
        }
    }
    with pytest.raises(coletor.ErroColeta) as exc_info:
        coletor.parsear_chart(payload, "EMBR3", AGORA)
    assert exc_info.value.codigo == "Not Found"
    assert exc_info.value.detalhe == "No data found, symbol may be delisted"
    assert exc_info.value.ticker == "EMBR3"


def test_parsear_chart_levanta_sem_resultado_quando_result_vazio() -> None:
    payload = {"chart": {"error": None, "result": []}}
    with pytest.raises(coletor.ErroColeta) as exc_info:
        coletor.parsear_chart(payload, "VALE3", AGORA)
    assert exc_info.value.codigo == "SEM_RESULTADO"


def test_parsear_chart_levanta_resposta_invalida_quando_nao_e_dict() -> None:
    with pytest.raises(coletor.ErroColeta) as exc_info:
        coletor.parsear_chart("Edge: Too Many Requests", "PETR4", AGORA)
    assert exc_info.value.codigo == "RESPOSTA_INVALIDA"


def test_parsear_chart_descarta_candle_com_null_e_mantem_os_demais() -> None:
    payload = {
        "chart": {
            "error": None,
            "result": [
                {
                    "meta": {"currency": "BRL", "symbol": "VALE3.SA"},
                    "timestamp": [1786453200, 1786539600, 1786626000],
                    "indicators": {
                        "quote": [
                            {
                                "open": [76.31, None, 72.20],
                                "high": [76.70, 73.54, 73.20],
                                "low": [73.71, 72.66, 71.50],
                                "close": [74.40, 73.18, 71.90],
                                "volume": [36211800, 24930300, 19535200],
                            }
                        ]
                    },
                }
            ],
        }
    }
    serie = coletor.parsear_chart(payload, "VALE3", AGORA)
    assert len(serie.candles) == 2
    assert serie.candles[0].fechamento == 74.40
    assert serie.candles[-1].volume == 19535200
    assert serie.moeda == "BRL"
    assert serie.fonte == "yahoo-chart"


def test_parsear_chart_levanta_serie_curta_com_menos_de_2_candles() -> None:
    payload = {
        "chart": {
            "error": None,
            "result": [
                {
                    "meta": {"currency": "BRL", "symbol": "VALE3.SA"},
                    "timestamp": [1786453200, 1786539600],
                    "indicators": {
                        "quote": [
                            {
                                "open": [76.31, None],
                                "high": [76.70, 73.54],
                                "low": [73.71, 72.66],
                                "close": [74.40, 73.18],
                                "volume": [36211800, 24930300],
                            }
                        ]
                    },
                }
            ],
        }
    }
    with pytest.raises(coletor.ErroColeta) as exc_info:
        coletor.parsear_chart(payload, "VALE3", AGORA)
    assert exc_info.value.codigo == "SERIE_CURTA"


def test_parsear_chart_data_do_candle_no_fuso_de_brasilia() -> None:
    # 2026-01-01T01:00:00 UTC = 2025-12-31T22:00:00-03:00: a data tem que
    # virar pelo fuso de Brasília, não pelo UTC.
    ts_alvo = int(datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC).timestamp())
    payload = _payload_valido(timestamps=[1786453200, ts_alvo])
    serie = coletor.parsear_chart(payload, "VALE3", AGORA)
    assert serie.candles[-1].data == date(2025, 12, 31)


def test_buscar_serie_manda_user_agent_de_navegador() -> None:
    chamadas: list[dict[str, Any]] = []

    def http_get_fake(url: str, **kwargs: Any) -> _RespostaFake:
        chamadas.append(kwargs)
        return _RespostaFake(_payload_valido())

    coletor.buscar_serie("VALE3", http_get=http_get_fake, agora=AGORA)
    assert len(chamadas) == 1
    assert chamadas[0]["headers"] == coletor.CABECALHOS
    assert "Mozilla" in chamadas[0]["headers"]["User-Agent"]
    assert chamadas[0]["timeout"] == 20


def test_coletar_universo_segue_em_frente_quando_um_ticker_falha() -> None:
    def http_get_fake(url: str, **kwargs: Any) -> _RespostaFake:
        if "EMBR3" in url:
            return _RespostaFake(
                {
                    "chart": {
                        "error": {
                            "code": "Not Found",
                            "description": "No data found, symbol may be delisted",
                        },
                        "result": None,
                    }
                }
            )
        return _RespostaFake(_payload_valido())

    series_ok, falhas = coletor.coletar_universo(
        ["VALE3", "EMBR3", "PETR4"], http_get=http_get_fake, agora=AGORA
    )
    assert [s.ticker for s in series_ok] == ["VALE3", "PETR4"]
    assert falhas == [("EMBR3", "Not Found: No data found, symbol may be delisted")]


@pytest.mark.live
def test_live_coletar_universo_relata_tickers_mortos() -> None:
    """Bate na API real do Yahoo e relata quais tickers do UNIVERSO não respondem.

    Não roda por default (addopts = "-m 'not live'"). Serve para validar a
    lista de tickers, não é uma asserção de sucesso total: tickers podem
    estar deslistados ou renomeados sem que isso seja falha do contrato.
    """
    series_ok, falhas = coletor.coletar_universo(coletor.UNIVERSO)
    print(f"\n[live] {len(series_ok)}/{len(coletor.UNIVERSO)} tickers responderam.")
    if falhas:
        print(f"[live] tickers sem resposta: {falhas}")
    assert len(series_ok) + len(falhas) == len(coletor.UNIVERSO)
    assert len(series_ok) > 0
