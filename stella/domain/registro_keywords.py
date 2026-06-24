"""Registro de keywords da fábrica de conteúdo v2 (F1).

Fonte da verdade que liga cada keyword de ManyChat ao seu material (slug do PDF)
e aos posts que a usam. Garante o dedup de material (keyword repetida = mesmo
material) e o matching acento/caixa-insensível usado pela orquestração.

Domínio puro: persiste num JSON cujo caminho é injetado de fora (a camada de CLI
fornece o path em FABRICADECONTEUDO). Escrita atômica (.tmp + replace).
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path


def normalizar_keyword(kw: str) -> str:
    """Forma canônica para matching: sem acento, maiúscula, sem espaços nas bordas."""
    nfkd = unicodedata.normalize("NFKD", kw)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sem_acento.strip().upper()


@dataclass
class EntradaKeyword:
    """Uma keyword e tudo que pende dela."""

    keyword: str
    slug: str = ""
    material: str = ""
    posts: list[str] = field(default_factory=list)


class RegistroKeywords:
    """Coleção de keywords com lookup normalizado, dedup e persistência atômica."""

    def __init__(self, entradas: dict[str, EntradaKeyword] | None = None) -> None:
        # chave interna = keyword normalizada
        self._por_norm: dict[str, EntradaKeyword] = entradas or {}

    @classmethod
    def carregar(cls, path: Path) -> RegistroKeywords:
        if not path.exists():
            return cls({})
        dados = json.loads(path.read_text(encoding="utf-8"))
        entradas: dict[str, EntradaKeyword] = {}
        for item in dados.get("keywords", []):
            entrada = EntradaKeyword(**item)
            entradas[normalizar_keyword(entrada.keyword)] = entrada
        return cls(entradas)

    def buscar(self, keyword: str) -> EntradaKeyword | None:
        return self._por_norm.get(normalizar_keyword(keyword))

    def tem_material(self, keyword: str) -> bool:
        entrada = self.buscar(keyword)
        return entrada is not None and bool(entrada.slug)

    def registrar_post(
        self,
        keyword: str,
        post_id: str,
        *,
        slug: str = "",
        material: str = "",
    ) -> EntradaKeyword:
        """Registra um post sob a keyword. Dedup: só preenche material/slug vazios."""
        norm = normalizar_keyword(keyword)
        entrada = self._por_norm.get(norm)
        if entrada is None:
            entrada = EntradaKeyword(keyword=keyword.strip(), slug=slug, material=material)
            self._por_norm[norm] = entrada
        else:
            if slug and not entrada.slug:
                entrada.slug = slug
            if material and not entrada.material:
                entrada.material = material
        if post_id not in entrada.posts:
            entrada.posts.append(post_id)
        return entrada

    def definir_material(self, keyword: str, *, slug: str, material: str = "") -> EntradaKeyword:
        """Define (sobrescreve) o material da keyword. Cria a entrada; não toca nos posts."""
        norm = normalizar_keyword(keyword)
        entrada = self._por_norm.get(norm)
        if entrada is None:
            entrada = EntradaKeyword(keyword=keyword.strip())
            self._por_norm[norm] = entrada
        entrada.slug = slug
        if material:
            entrada.material = material
        return entrada

    def keywords(self) -> list[EntradaKeyword]:
        return list(self._por_norm.values())

    def salvar(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"keywords": [asdict(e) for e in self._por_norm.values()]}
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
