"""Coletor de candles da B3 via API pública de gráfico do Yahoo Finance.

Busca séries de preço (OHLCV) por ticker, sem chave nem token. Este módulo
entrega só a camada de dado bruto: nenhum sinal, nenhum indicador, nenhum
envio de alerta.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

FUSO = timezone(timedelta(hours=-3))

URL_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{simbolo}"
CABECALHOS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

UNIVERSO: list[str] = [
    "PETR4",
    "PETR3",
    "VALE3",
    "ITUB4",
    "BBDC4",
    "BBAS3",
    "B3SA3",
    "WEGE3",
    "ABEV3",
    "SUZB3",
    "RENT3",
    "PRIO3",
    "RADL3",
    "HAPV3",
    "VBBR3",
    "MGLU3",
    "LREN3",
    "EGIE3",
    "EQTL3",
    "GGBR4",
    "CSNA3",
    "USIM5",
    "CMIG4",
    "SBSP3",
    "CPLE3",
    "RAIL3",
    "MOTV3",
    "KLBN11",
    "JBSS32",
    "SMTO3",
    "VIVT3",
    "TOTS3",
    "CYRE3",
    "MRVE3",
    "ASAI3",
    "RDOR3",
    "CSAN3",
    "CVCB3",
    "UGPA3",
    "ITSA4",
]

_CAMPOS_QUOTE = ("open", "high", "low", "close", "volume")


@dataclass(frozen=True)
class Candle:
    """Um candle diário (OHLCV) de uma série de preço."""

    data: date
    abertura: float
    maxima: float
    minima: float
    fechamento: float
    volume: int


@dataclass(frozen=True)
class Serie:
    """Série histórica de candles de um ticker, com metadados da coleta."""

    ticker: str
    moeda: str
    candles: list[Candle]
    coletado_em: datetime
    fonte: str


class ErroColeta(Exception):
    """Falha ao coletar ou parsear a série de um ticker."""

    def __init__(self, ticker: str, codigo: str, detalhe: str) -> None:
        self.ticker = ticker
        self.codigo = codigo
        self.detalhe = detalhe
        super().__init__(f"{ticker}: [{codigo}] {detalhe}")


def simbolo_yahoo(ticker: str) -> str:
    """Converte um ticker da B3 no símbolo esperado pelo Yahoo Finance.

    Args:
        ticker: Código do papel na B3, ex.: "petr4" ou "PETR4".

    Returns:
        Símbolo no formato do Yahoo, ex.: "PETR4.SA". Não duplica o sufixo
        se ele já estiver presente.
    """
    normalizado = ticker.strip().upper()
    if normalizado.endswith(".SA"):
        return normalizado
    return f"{normalizado}.SA"


def parsear_chart(payload: Any, ticker: str, coletado_em: datetime) -> Serie:
    """Transforma o payload cru do endpoint /chart do Yahoo em uma Serie.

    Pura: não toca rede. Descarta candles com qualquer campo nulo (pregão
    sem preço não é dado, é buraco) e nunca inventa valor.

    Args:
        payload: JSON decodificado da resposta do Yahoo (ou o texto cru,
            quando a resposta não veio como dicionário — ex.: bloqueio).
        ticker: Ticker original da B3 (sem sufixo), usado nas mensagens de erro.
        coletado_em: Instante da coleta, gravado em Serie.coletado_em.

    Returns:
        Serie com os candles válidos, em ordem cronológica.

    Raises:
        ErroColeta: payload inválido, sem resultado, erro reportado pela API,
            ou série curta demais (menos de 2 candles) depois do descarte.
    """
    if not isinstance(payload, dict):
        raise ErroColeta(ticker, "RESPOSTA_INVALIDA", "resposta não é um objeto JSON")

    chart = payload.get("chart") or {}
    erro = chart.get("error")
    if erro:
        if isinstance(erro, dict):
            codigo = str(erro.get("code", "ERRO_DESCONHECIDO"))
            detalhe = str(erro.get("description", erro))
        else:
            codigo = "ERRO_DESCONHECIDO"
            detalhe = str(erro)
        raise ErroColeta(ticker, codigo, detalhe)

    resultados = chart.get("result")
    if not resultados:
        raise ErroColeta(ticker, "SEM_RESULTADO", "chart.result vazio ou ausente")

    resultado = resultados[0]
    meta = resultado.get("meta") or {}
    timestamps = resultado.get("timestamp") or []
    quotes = (resultado.get("indicators") or {}).get("quote") or [{}]
    quote = quotes[0]

    candles: list[Candle] = []
    for i, ts in enumerate(timestamps):
        campos: list[Any] = []
        for nome in _CAMPOS_QUOTE:
            serie_campo = quote.get(nome) or []
            campos.append(serie_campo[i] if i < len(serie_campo) else None)
        if any(valor is None for valor in campos):
            continue
        abertura, maxima, minima, fechamento, volume = campos
        candles.append(
            Candle(
                data=datetime.fromtimestamp(ts, FUSO).date(),
                abertura=float(abertura),
                maxima=float(maxima),
                minima=float(minima),
                fechamento=float(fechamento),
                volume=int(volume),
            )
        )

    if len(candles) < 2:
        raise ErroColeta(ticker, "SERIE_CURTA", f"apenas {len(candles)} candle(s) válido(s)")

    return Serie(
        ticker=ticker,
        moeda=str(meta.get("currency", "")),
        candles=candles,
        coletado_em=coletado_em,
        fonte="yahoo-chart",
    )


def buscar_serie(
    ticker: str,
    *,
    intervalo: str = "2y",
    http_get: Callable[..., Any] = httpx.get,
    agora: datetime | None = None,
) -> Serie:
    """Busca e parseia a série de candles de um ticker no Yahoo Finance.

    Args:
        ticker: Ticker da B3, ex.: "PETR4".
        intervalo: Janela de tempo da série (parâmetro `range` da API).
            Default "2y" (~499 candles): a MM200 do motor de setups exige 200
            candles, e "6mo" devolve só 128 — com 6mo nenhum papel é elegível.
        http_get: Função injetável para GET HTTP (para testes).
        agora: Instante gravado como coletado_em; default datetime.now(FUSO).

    Returns:
        Serie com os candles do período.

    Raises:
        ErroColeta: propagada de parsear_chart.
    """
    simbolo = simbolo_yahoo(ticker)
    url = URL_CHART.format(simbolo=simbolo)
    resposta = http_get(
        url,
        headers=CABECALHOS,
        params={"range": intervalo, "interval": "1d"},
        timeout=20,
    )
    try:
        payload: Any = resposta.json()
    except Exception:
        payload = resposta.text
    return parsear_chart(payload, ticker, agora or datetime.now(FUSO))


def coletar_universo(
    tickers: list[str] = UNIVERSO,
    *,
    http_get: Callable[..., Any] = httpx.get,
    agora: datetime | None = None,
) -> tuple[list[Serie], list[tuple[str, str]]]:
    """Coleta a série de cada ticker do universo, sem deixar uma falha derrubar o resto.

    Args:
        tickers: Lista de tickers a coletar; default UNIVERSO.
        http_get: Função injetável para GET HTTP (para testes).
        agora: Instante gravado como coletado_em em cada Serie coletada.

    Returns:
        Tupla (series_ok, falhas): series_ok são as séries coletadas com
        sucesso; falhas é a lista de (ticker, motivo) de quem não deu certo.
    """
    momento = agora or datetime.now(FUSO)
    series_ok: list[Serie] = []
    falhas: list[tuple[str, str]] = []
    for ticker in tickers:
        try:
            series_ok.append(buscar_serie(ticker, http_get=http_get, agora=momento))
        except ErroColeta as exc:
            falhas.append((ticker, f"{exc.codigo}: {exc.detalhe}"))
        except Exception as exc:  # noqa: BLE001 - ticker isolado não pode derrubar o universo
            falhas.append((ticker, str(exc)))
    return series_ok, falhas
