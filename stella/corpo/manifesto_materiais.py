"""Manifesto de materiais (slug -> titulo/descricao/pdf) lido pela landing do hub.

A fábrica atualiza este JSON ao publicar um material; a landing genérica
`/baixar/[slug]` no hub lê dele o título e a descrição a exibir.
"""

from __future__ import annotations

import json
from pathlib import Path


def montar_entrada_manifesto(slug: str, titulo: str, descricao: str) -> dict[str, str]:
    return {"titulo": titulo, "descricao": descricao, "pdf": f"/materiais/{slug}.pdf"}


def atualizar_manifesto(path: Path, slug: str, titulo: str, descricao: str) -> None:
    """Faz merge da entrada do slug no manifesto e grava de forma atômica."""
    try:
        dados = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        dados = {}
    dados[slug] = montar_entrada_manifesto(slug, titulo, descricao)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
