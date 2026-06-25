"""Pacote de conteúdo por keyword: lista posts e resolve os caminhos do que é
postável (legenda + slides + PDF do material). Domínio puro: recebe o registro e
a raiz da fábrica de fora; não importa adapters."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from stella.domain.registro_keywords import RegistroKeywords, normalizar_keyword

_DATA_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


@dataclass(frozen=True)
class PostInfo:
    post_id: str
    data: str
    titulo: str


@dataclass(frozen=True)
class Pacote:
    keyword: str
    post_id: str
    legenda: Path | None
    slides: list[Path]
    material_pdf: Path | None
    manychat: Path | None


def listar_posts(registro: RegistroKeywords, keyword: str, fab_root: Path) -> list[PostInfo]:
    """Posts registrados sob a keyword (data derivada do prefixo do post_id)."""
    entrada = registro.buscar(keyword)
    if entrada is None:
        return []
    infos: list[PostInfo] = []
    for post_id in entrada.posts:
        m = _DATA_RE.match(post_id)
        infos.append(PostInfo(post_id=post_id, data=m.group(1) if m else "", titulo=""))
    return infos


def resolver_pacote(
    registro: RegistroKeywords, keyword: str, post_id: str, fab_root: Path
) -> Pacote:
    """Caminhos do pacote postável: legenda + slides do post + PDF/manychat da keyword."""
    entrada = registro.buscar(keyword)
    norm = normalizar_keyword(keyword)
    kw_dir = fab_root / norm
    post_dir = kw_dir / post_id

    legenda = post_dir / "legenda.txt"
    slides = sorted(post_dir.glob("slide-*.png")) if post_dir.exists() else []
    pdf = (kw_dir / f"{entrada.slug}.pdf") if entrada and entrada.slug else None
    manychat = next(iter(kw_dir.glob("manychat-*.txt")), None) if kw_dir.exists() else None

    return Pacote(
        keyword=norm,
        post_id=post_id,
        legenda=legenda if legenda.exists() else None,
        slides=list(slides),
        material_pdf=pdf if (pdf and pdf.exists()) else None,
        manychat=manychat,
    )
