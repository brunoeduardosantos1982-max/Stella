"""Registro e resolução de apelidos dos itens do Radar.

Cada item curado pelo Radar ganha um apelido kebab-case temático (ex.:
'ia-google-agentes'). Este módulo garante a unicidade desses apelidos, persiste
o registro (apelido -> item) e resolve uma referência do Bruno de forma tolerante
(exata -> parcial por palavra -> ambígua), para o modo carrossel puxar a notícia-fonte.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

DROPS_PATH = Path("D:/VortexBrain00/.secrets/radar_drops.json")
JANELA_DROPS_DIAS = 14
FUSO = timezone(timedelta(hours=-3))


def slug_apelido(texto: str) -> str:
    """Normaliza para kebab-case: sem acento, minúsculo, só [a-z0-9-]."""
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")


def garantir_unicos(novos: list[str], existentes: set[str]) -> list[str]:
    """Devolve apelidos únicos: colisões (no lote ou com `existentes`) ganham -2, -3."""
    usados = set(existentes)
    out: list[str] = []
    for nome in novos:
        cand = nome
        i = 2
        while cand in usados:
            cand = f"{nome}-{i}"
            i += 1
        usados.add(cand)
        out.append(cand)
    return out


def resolver_drop(ref: str, registro: list[dict[str, str]]) -> list[dict[str, str]]:
    """Resolve uma referência. Exato tem prioridade; senão parcial por palavra.

    Retorna lista: 0 = não achou, 1 = resolvido, >1 = ambíguo (a Stella pergunta qual).
    """
    ref_slug = slug_apelido(ref)
    if not ref_slug:
        return []
    exatos = [e for e in registro if slug_apelido(e.get("apelido", "")) == ref_slug]
    if exatos:
        return exatos
    tokens = set(ref_slug.split("-"))
    parciais: list[dict[str, str]] = []
    for e in registro:
        ap = slug_apelido(e.get("apelido", ""))
        if tokens <= set(ap.split("-")) or ref_slug in ap:
            parciais.append(e)
    return parciais


def carregar_drops(path: Path = DROPS_PATH) -> list[dict[str, str]]:
    try:
        dados = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return dados if isinstance(dados, list) else []


def podar_drops(
    registro: list[dict[str, str]],
    janela_dias: int = JANELA_DROPS_DIAS,
    agora: datetime | None = None,
) -> list[dict[str, str]]:
    ref = (agora or datetime.now(FUSO)) - timedelta(days=janela_dias)
    out: list[dict[str, str]] = []
    for e in registro:
        try:
            if datetime.fromisoformat(e["registrado_em"]) >= ref:
                out.append(e)
        except (KeyError, ValueError, TypeError):
            continue
    return out


def salvar_drops(
    registro: list[dict[str, str]],
    novos: list[dict[str, str]],
    path: Path = DROPS_PATH,
    agora: datetime | None = None,
) -> None:
    """Anexa `novos` (com timestamp), poda a janela e grava de forma atômica."""
    quando = (agora or datetime.now(FUSO)).isoformat()
    carimbados = [{**n, "registrado_em": quando} for n in novos]
    atualizado = podar_drops(list(registro) + carimbados, agora=agora)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(atualizado, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
