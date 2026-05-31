"""CreativeIndex - catalogo curado do banco de imagens (fotos + referencias).

Puro e tolerante: parse nunca levanta; indice ausente vira indice vazio.
O designer injeta o brief filtrado no prompt - metadados, nao so nomes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

_INDEX_PATH = "A03 Banco de Imagens/creative-index.json"


@dataclass
class CreativeIndex:
    fotos_bruno: list[dict[str, Any]] = field(default_factory=list)
    referencias: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ReferenceBrief:
    fotos: list[dict[str, Any]] = field(default_factory=list)
    referencias: list[dict[str, Any]] = field(default_factory=list)


def parse_index(texto: str) -> CreativeIndex:
    """Parseia o JSON do catalogo. Qualquer erro vira indice vazio."""
    try:
        dados = json.loads(texto) if texto.strip() else {}
    except (json.JSONDecodeError, ValueError):
        return CreativeIndex()
    if not isinstance(dados, dict):
        return CreativeIndex()
    fotos = dados.get("fotos_bruno") or []
    refs = dados.get("referencias") or []
    return CreativeIndex(
        fotos_bruno=[f for f in fotos if isinstance(f, dict)],
        referencias=[r for r in refs if isinstance(r, dict)],
    )


def carregar_index(vault: Any, path: str = _INDEX_PATH) -> CreativeIndex:
    """Le o catalogo do vault. Ausente/erro de IO vira indice vazio."""
    try:
        bruto = vault.read_binary(path).decode("utf-8")
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return CreativeIndex()
    return parse_index(bruto)


def filtrar(
    index: CreativeIndex,
    pauta: dict[str, Any],
    copy: dict[str, Any],
    max_fotos: int = 3,
    max_refs: int = 2,
) -> ReferenceBrief:
    """Seleciona um subconjunto relevante para o designer.

    v1 prioriza qualidade alta nas fotos e referencias cujo tipo_post casa com
    o tipo da pauta. A escolha fina fica com o LLM, que agora ve metadados.
    """
    tipo = str(pauta.get("tipo", "carrossel"))

    fotos_ordenadas = sorted(
        index.fotos_bruno,
        key=lambda f: 0 if str(f.get("qualidade", "")).lower() == "alta" else 1,
    )
    refs_casadas = [r for r in index.referencias if str(r.get("tipo_post", "")) == tipo]
    refs = refs_casadas or index.referencias

    return ReferenceBrief(fotos=fotos_ordenadas[:max_fotos], referencias=refs[:max_refs])


def brief_para_prompt(brief: ReferenceBrief) -> str:
    """Formata o brief pro prompt do designer. Vazio vira string vazia."""
    if not brief.fotos and not brief.referencias:
        return ""
    linhas: list[str] = []
    if brief.fotos:
        linhas.append("FOTOS DO BRUNO DISPONIVEIS (com contexto):")
        for f in brief.fotos:
            usos = ", ".join(f.get("uso_recomendado", []))
            linhas.append(
                f"  - {f.get('arquivo')}: uso={usos}; enquadramento={f.get('enquadramento')}; "
                f"expressao={f.get('expressao')}; usar quando={f.get('quando_usar')}; "
                f"evitar quando={f.get('quando_evitar')}"
            )
    if brief.referencias:
        linhas.append("\nREFERENCIAS CURADAS (inspire-se na composicao, NAO copie):")
        for r in brief.referencias:
            princ = ", ".join(r.get("principios", []))
            linhas.append(
                f"  - {r.get('arquivo')}: padrao={r.get('padrao_visual')}; "
                f"principios=[{princ}]; usar quando={r.get('quando_usar')}"
            )
    return "\n".join(linhas)
