"""Apresentador: monta o texto do card do Radar da Bolsa a partir de dados calculados.

Só formata. Nenhuma função aqui decide número: os valores vêm sempre de um
`Setup` já detectado e de um `Plano` já dimensionado. A única função que fala
com um LLM é `montar_tese` — e mesmo essa recebe o provider injetado, para o
teste não chamar modelo nenhum. Todo texto de origem livre (a tese) é
escapado com `html.escape` antes de entrar no HTML do Telegram.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, time
from html import escape as _esc

from stella.adapters.llm.base import LLMProvider
from stella.corpo.bolsa.risco import Plano
from stella.corpo.bolsa.setups import Setup

_AVISO = (
    "⚠️ Isto é leitura de dados, não recomendação de investimento. "
    "Conferir preço e liquidez na corretora antes de operar. A decisão é sua."
)

_DESCRICAO_SETUP: dict[str, str] = {
    "ROMPIMENTO_ALTA": "rompimento de máxima de 60 dias",
    "PULLBACK_TENDENCIA": "pullback na tendência de alta",
    "SOBREVENDA_TENDENCIA": "sobrevenda dentro da tendência de alta",
    "PERDA_SUPORTE": "rompimento de mínima de 60 dias",
    "FAIXA_LATERAL": "lateralização de preço",
    "COMPRESSAO_VOLATILIDADE": "compressão de volatilidade",
}

_TESE_DETERMINISTICA: dict[str, str] = {
    "ROMPIMENTO_ALTA": (
        "Rompeu a máxima recente com volume acima da média e segue sobre a média de longo prazo."
    ),
    "PULLBACK_TENDENCIA": (
        "Recuou até a média de curto prazo dentro de uma tendência de alta organizada."
    ),
    "SOBREVENDA_TENDENCIA": (
        "Entrou em sobrevenda de curto prazo dentro de uma tendência de alta ainda válida."
    ),
    "PERDA_SUPORTE": (
        "Rompeu a mínima recente com volume acima da média e segue abaixo da média de longo prazo."
    ),
    "FAIXA_LATERAL": "Preço andando de lado, sem direção definida.",
    "COMPRESSAO_VOLATILIDADE": "Volatilidade comprimida frente à média recente, sem direção definida.",
}

_PROMPT_TESE = (
    "Você é analista técnico. Em no máximo 2 frases, em português, explique o porquê "
    "de o setup abaixo ter disparado, em linguagem simples para o Bruno decidir se opera. "
    "PROIBIDO citar qualquer número (preço, percentual, quantidade, força ou período): "
    "os números já aparecem no card, escreva só o racional. Responda apenas as frases, "
    "sem saudação e sem repetir o ticker.\n\n"
    "Ticker: {ticker}\n"
    "Setup: {nome}\n"
    "Cenário: {cenario}\n"
    "Direção: {direcao}\n"
)


def _fmt(valor: float) -> str:
    """Formata número no padrão pt-BR: ponto de milhar, vírgula decimal."""
    texto = f"{valor:,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_rr(valor: float) -> str:
    """Formata a razão risco/retorno em pt-BR, sem zero decimal supérfluo.

    O card mostra "1,5 : 1", não "1,50 : 1" — 2 casas quando fazem falta,
    nunca mais que isso.
    """
    texto = f"{valor:.2f}".rstrip("0").rstrip(".")
    if not texto or texto == "-":
        texto = "0"
    return texto.replace(".", ",")


def montar_tese(setup: Setup, plano: Plano, *, provider: LLMProvider) -> str:
    """Pede ao LLM a tese em palavras (sem números) para um Setup e seu Plano.

    Args:
        setup: Setup detectado.
        plano: Plano dimensionado (não citado diretamente no prompt; os
            números do card vêm dele, não da tese).
        provider: Provider de LLM injetável (para o teste não chamar modelo).

    Returns:
        Texto cru devolvido pelo modelo (ainda não escapado para HTML).
    """
    prompt = _PROMPT_TESE.format(
        ticker=setup.ticker,
        nome=setup.nome,
        cenario=setup.cenario,
        direcao=setup.direcao,
    )
    resposta = provider.complete(prompt)
    return resposta.texto.strip()


def tese_deterministica(setup: Setup, plano: Plano) -> str:
    """Tese de fallback, sem LLM: nunca inventa e nunca cita número.

    Usada quando o provider falha ou quando o verificador reprova a tese do
    modelo.

    Args:
        setup: Setup detectado.
        plano: Plano dimensionado (não usado no texto; existe pela simetria
            de assinatura com `montar_tese`).

    Returns:
        Frase fixa e determinística, sem número.
    """
    return _TESE_DETERMINISTICA.get(
        setup.nome,
        f"Setup {setup.nome} detectado, sem descrição cadastrada.",
    )


def montar_bloco_alerta(setup: Setup, plano: Plano, tese: str) -> str:
    """Monta o bloco HTML de um alerta (1 setup) para o card do Telegram.

    Args:
        setup: Setup detectado.
        plano: Plano dimensionado (aprovado).
        tese: Texto da tese (do modelo ou determinística); é escapado aqui.

    Returns:
        Bloco de texto HTML pronto para entrar no card.
    """
    nome_legivel = _DESCRICAO_SETUP.get(setup.nome, setup.nome)
    linhas = [
        f"🎯 <b>{_esc(setup.ticker)}</b> · {_esc(nome_legivel)}",
        f"Cenário: {_esc(setup.cenario)} · força {setup.forca}/100",
        "",
        _esc(tese),
        "",
        f"Entrada  R$ {_fmt(plano.entrada)}",
        f"Stop     R$ {_fmt(plano.stop)}   (risco R$ {_fmt(plano.risco_por_acao)} por ação)",
        f"Alvo     R$ {_fmt(plano.alvo)}   (retorno R$ {_fmt(plano.retorno_por_acao)} por ação)",
        f"Risco/retorno  {_fmt_rr(plano.razao_rr)} : 1",
        f"Tamanho  {plano.quantidade} ações  (risco total R$ {_fmt(plano.risco_total)})",
    ]
    return "\n".join(linhas)


def _linha_cenario(neutros: Sequence[Setup]) -> str:
    """Linha de rodapé com a CONTAGEM dos setups neutros do dia (não é alerta)."""
    if not neutros:
        return ""
    lateral = sum(1 for s in neutros if s.nome == "FAIXA_LATERAL")
    compressao = sum(1 for s in neutros if s.nome == "COMPRESSAO_VOLATILIDADE")
    outros = len(neutros) - lateral - compressao

    segmentos: list[str] = []
    if lateral:
        palavra = "papel" if lateral == 1 else "papéis"
        segmentos.append(f"{lateral} {palavra} em lateralização")
    if compressao:
        segmentos.append(f"{compressao} em compressão de volatilidade")
    if outros:
        segmentos.append(f"{outros} em outro cenário neutro")

    if not segmentos:
        return ""
    return "📊 Cenário: " + ", ".join(segmentos) + " (candidatos a estrutura de opções)."


ABERTURA_PREGAO = time(10, 0)


def _linha_pregao(data_pregao: date | None, agora: datetime) -> str:
    """Explica de quando são os dados quando o candle mais recente não é de hoje.

    São três situações diferentes e o card não pode confundi-las:

    1. Dado é de hoje: nada a dizer.
    2. Dia útil ANTES das 10h (o pregão da B3 abre às 10h): o candle de hoje
       ainda não existe porque o mercado não abriu. É o caso normal do card
       da manhã, e dizer "sem pregão hoje" aqui seria mentira.
    3. Fim de semana, feriado ou dia útil já com o mercado aberto sem candle:
       não houve pregão. Evita manter calendário de feriado da B3.

    Args:
        data_pregao: Data do candle mais recente coletado, ou None.
        agora: Data/hora de referência do card.

    Returns:
        A linha de contexto, ou string vazia quando os dados são de hoje.
    """
    if data_pregao is None or data_pregao == agora.date():
        return ""
    dia_util = agora.weekday() < 5
    antes_da_abertura = agora.time() < ABERTURA_PREGAO
    if dia_util and antes_da_abertura:
        return (
            f"🔔 O pregão de hoje abre às 10h. A leitura abaixo é do "
            f"fechamento de {data_pregao:%d/%m}."
        )
    return f"🗓️ Sem pregão hoje. Os dados abaixo são do pregão de {data_pregao:%d/%m}."


def _linha_falhas(falhas: Sequence[tuple[str, str]]) -> str:
    """Linha de rodapé com os tickers cuja coleta falhou hoje."""
    if not falhas:
        return ""
    tickers = ", ".join(ticker for ticker, _motivo in falhas)
    return f"⚠️ {len(falhas)} ticker(s) não responderam: {tickers}"


def _rodape(agora: datetime) -> list[str]:
    return [
        _AVISO,
        f"Fonte: yahoo-chart · coletado às {agora:%H:%M}",
    ]


def montar_card(
    blocos: Sequence[str],
    agora: datetime,
    *,
    neutros: Sequence[Setup] = (),
    falhas: Sequence[tuple[str, str]] = (),
    data_pregao: date | None = None,
) -> str:
    """Monta o card HTML inteiro, com os blocos de alerta do dia.

    Args:
        blocos: Blocos de alerta já montados (`montar_bloco_alerta`), na
            ordem em que devem aparecer.
        agora: Data/hora de referência (usada no cabeçalho e no rodapé).
        neutros: Setups de direção "neutro" detectados hoje (viram só a linha
            de contagem, nunca um bloco de alerta).
        falhas: Falhas de coleta do dia, como (ticker, motivo).

    Returns:
        Texto HTML pronto para `enviar_telegram`.
    """
    partes = [f"📈 <b>RADAR DA BOLSA · {agora:%d/%m}</b>", ""]
    linha_pregao = _linha_pregao(data_pregao, agora)
    if linha_pregao:
        partes.extend([linha_pregao, ""])
    for bloco in blocos:
        partes.append(bloco)
        partes.append("")

    linha_cenario = _linha_cenario(neutros)
    if linha_cenario:
        partes.append(linha_cenario)
        partes.append("")

    linha_falhas = _linha_falhas(falhas)
    if linha_falhas:
        partes.append(linha_falhas)
        partes.append("")

    partes.extend(_rodape(agora))
    return "\n".join(partes).strip()


def montar_card_vazio(
    agora: datetime,
    *,
    neutros: Sequence[Setup] = (),
    falhas: Sequence[tuple[str, str]] = (),
    varridos: int = 0,
    data_pregao: date | None = None,
) -> str:
    """Monta o card para o dia em que nenhum setup direcional passou os filtros.

    Args:
        agora: Data/hora de referência.
        neutros: Setups neutros detectados hoje (linha de contagem).
        falhas: Falhas de coleta do dia.
        varridos: Quantos tickers foram varridos com sucesso.

    Returns:
        Texto HTML dizendo que a varredura rodou e quantos tickers cobriu.
    """
    partes = [
        f"📈 <b>RADAR DA BOLSA · {agora:%d/%m}</b>",
        "",
        f"Varredura completa: {varridos} ticker(s) analisados, "
        "nenhum setup direcional passou os filtros hoje.",
        "",
    ]

    linha_pregao = _linha_pregao(data_pregao, agora)
    if linha_pregao:
        partes.insert(2, linha_pregao)
        partes.insert(3, "")

    linha_cenario = _linha_cenario(neutros)
    if linha_cenario:
        partes.append(linha_cenario)
        partes.append("")

    linha_falhas = _linha_falhas(falhas)
    if linha_falhas:
        partes.append(linha_falhas)
        partes.append("")

    partes.extend(_rodape(agora))
    return "\n".join(partes).strip()


def montar_card_erro(erro: str, agora: datetime) -> str:
    """Monta o card do dia em que a coleta falhou inteira.

    Args:
        erro: Descrição do que falhou (texto livre, escapado aqui).
        agora: Data/hora de referência.

    Returns:
        Texto HTML dizendo o que falhou, sem inventar dado nenhum.
    """
    partes = [
        f"📈 <b>RADAR DA BOLSA · {agora:%d/%m}</b>",
        "",
        f"🚨 A coleta falhou hoje: {_esc(erro)}",
        "",
    ]
    partes.extend(_rodape(agora))
    return "\n".join(partes).strip()
