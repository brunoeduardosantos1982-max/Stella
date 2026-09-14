"""Verificador de números: barra qualquer alerta que cite valor não calculado.

Camada final do cinto-e-suspensório descrito no contrato C03: o modelo escreve
só a tese em palavras, os números vêm de `Setup.evidencias` e do `Plano`, e
este módulo varre o texto do modelo em busca de número que não bata com
nenhum valor calculado. Determinístico: nenhuma função aqui toca rede, usa
LLM ou aleatoriedade.
"""

from __future__ import annotations

import re

from stella.corpo.bolsa.risco import Plano
from stella.corpo.bolsa.setups import Setup

TOLERANCIA = 0.011  # 1,1% — cobre arredondamento de 2 casas sem deixar passar número inventado

# Períodos de indicador NÃO são preço: a tese pode dizer "média de 200 dias" sem estar
# inventando número. Sem esta lista, o verificador barraria a tese por engano e o card
# cairia para a versão determinística todo dia.
PERIODOS = frozenset({9.0, 14.0, 20.0, 21.0, 50.0, 60.0, 100.0, 200.0})

_ANO_MINIMO = 1900
_ANO_MAXIMO = 2100

# Um número em português: "49", "49,00", "1.234,56". O lookbehind nega letra ou
# dígito imediatamente antes, para não colar no "4" de "PETR4". O grupo de
# percentual é opcional e não faz parte do valor numérico.
_TOKEN_NUMERO = re.compile(
    r"(?<![A-Za-zÀ-ÿ0-9])" r"(?P<num>\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)" r"(?P<pct>\s*%)?"
)


def extrair_numeros(texto: str) -> list[float]:
    """Extrai números em formato português de um texto livre.

    Reconhece inteiro (`49`), decimal com vírgula (`49,00`), milhar com ponto
    (`1.234,56`) e percentual (`12%`); o prefixo "R$" não interfere porque não
    faz parte do padrão numérico. Ignora número colado a letra (o "4" de
    "PETR4") e ano por extenso (inteiro puro entre 1900 e 2100).

    Args:
        texto: Texto livre a varrer (tipicamente a tese escrita pelo modelo).

    Returns:
        Lista de valores numéricos encontrados, na ordem em que aparecem.
    """
    numeros: list[float] = []
    for m in _TOKEN_NUMERO.finditer(texto):
        bruto = m.group("num")
        tem_percentual = bool(m.group("pct"))
        tem_milhar = "." in bruto
        tem_decimal = "," in bruto
        normalizado = bruto.replace(".", "").replace(",", ".")
        valor = float(normalizado)

        eh_ano = (
            not tem_milhar
            and not tem_decimal
            and not tem_percentual
            and valor == int(valor)
            and _ANO_MINIMO <= valor <= _ANO_MAXIMO
        )
        if eh_ano:
            continue

        numeros.append(valor)
    return numeros


def numeros_permitidos(setup: Setup, plano: Plano) -> set[float]:
    """Monta o conjunto de números que a tese tem permissão de citar.

    Junta os períodos de indicador, todas as evidências do Setup, o preço e a
    força do Setup, e todos os campos numéricos do Plano. Acrescenta cada um
    desses valores arredondado para 2 casas e para inteiro, porque o modelo
    tende a arredondar ao escrever a tese.

    Args:
        setup: Setup detectado (evidências, preço, força).
        plano: Plano dimensionado (entrada, stop, alvo etc.).

    Returns:
        Conjunto de valores numéricos permitidos na tese.
    """
    base: set[float] = set(PERIODOS)
    base.update(setup.evidencias.values())
    base.add(setup.preco)
    base.add(float(setup.forca))
    base.update(
        (
            plano.entrada,
            plano.stop,
            plano.alvo,
            plano.risco_por_acao,
            plano.retorno_por_acao,
            plano.razao_rr,
            float(plano.quantidade),
            plano.risco_total,
        )
    )

    arredondados: set[float] = set()
    for valor in base:
        arredondados.add(round(valor, 2))
        arredondados.add(float(round(valor)))
    base.update(arredondados)
    return base


def _bate(numero: float, permitido: float) -> bool:
    """Confere se `numero` casa com `permitido` dentro da TOLERANCIA relativa."""
    if permitido == 0:
        return abs(numero) <= TOLERANCIA
    return abs(numero - permitido) <= abs(permitido) * TOLERANCIA


def verificar(texto: str, setup: Setup, plano: Plano) -> tuple[bool, list[float]]:
    """Verifica se todo número citado no texto veio do cálculo.

    Args:
        texto: Texto livre a verificar (a tese escrita pelo modelo).
        setup: Setup detectado, fonte de parte dos números permitidos.
        plano: Plano dimensionado, fonte do restante dos números permitidos.

    Returns:
        `(True, [])` quando todo número do texto casa com algum permitido
        dentro da TOLERANCIA; senão `(False, [os intrusos])`, na ordem em que
        apareceram no texto.
    """
    permitidos = numeros_permitidos(setup, plano)
    intrusos = [
        numero
        for numero in extrair_numeros(texto)
        if not any(_bate(numero, permitido) for permitido in permitidos)
    ]
    return (not intrusos, intrusos)
