"""Centralização do postável na pasta canônica da keyword.

- `centralizar_existentes`: migração retroativa (fila → pasta canônica) para todas
  as keywords do registro.
- `sincronizar_fila`: espelho no sentido inverso (canônica → fila) para publicar.

Cópia atômica (.tmp + replace) e idempotente (não sobrescreve o que já existe)."""

from __future__ import annotations

import shutil
from pathlib import Path

from stella.domain.registro_keywords import RegistroKeywords, normalizar_keyword

_NOMES = ("legenda.txt",)


def _copiar_assets(src_dir: Path, dst_dir: Path) -> bool:
    """Copia legenda.txt + slide-*.png de src→dst, pulando o que já existe.
    Retorna True se algo novo entrou."""
    if not src_dir.exists():
        return False
    dst_dir.mkdir(parents=True, exist_ok=True)
    fontes = [src_dir / n for n in _NOMES] + sorted(src_dir.glob("slide-*.png"))
    entrou = False
    for src in fontes:
        if not src.exists():
            continue
        dst = dst_dir / src.name
        if dst.exists():
            continue
        tmp = dst.with_name(dst.name + ".tmp")
        shutil.copyfile(src, tmp)
        tmp.replace(dst)
        entrou = True
    return entrou


def centralizar_existentes(
    registro: RegistroKeywords, fab_root: Path, fila_root: Path
) -> list[str]:
    """Para cada keyword/post do registro: copia fila/<post>/ → fab/<NORM>/<post>/."""
    migrados: list[str] = []
    for entrada in registro.keywords():
        norm = normalizar_keyword(entrada.keyword)
        for post_id in entrada.posts:
            if _copiar_assets(fila_root / post_id, fab_root / norm / post_id):
                migrados.append(post_id)
    return migrados


def sincronizar_fila(fab_root: Path, fila_root: Path, keyword: str, post_id: str) -> str:
    """Espelha a pasta canônica do post para a fila do Postiz (publicação)."""
    norm = normalizar_keyword(keyword)
    dst = fila_root / post_id
    _copiar_assets(fab_root / norm / post_id, dst)
    return str(dst)
