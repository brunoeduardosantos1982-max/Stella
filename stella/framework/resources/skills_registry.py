"""SkillsRegistry — indexa skills .md de prompts/skills/.

Skills são arquivos markdown com frontmatter contendo id, nome, descricao,
gatilhos, modelo_minimo e tags. SkillsRegistry escaneia o diretorio no
__init__ e mantem indice em memoria.
"""

from __future__ import annotations

import logging
from pathlib import Path

import frontmatter as frontmatter_module

from stella.domain.enums import ModeloIA
from stella.domain.skill import OrigemSkill, Skill
from stella.framework.errors import SkillNotFoundError

_logger = logging.getLogger(__name__)


class SkillsRegistry:
    """Indexa skills compartilhadas para injecao em agentes via builder."""

    def __init__(self, skills_dir: Path) -> None:
        self._dir = Path(skills_dir)
        self._por_id: dict[str, Skill] = {}
        self._por_tag: dict[str, list[Skill]] = {}
        self._scan()

    def _scan(self) -> None:
        if not self._dir.exists():
            return
        for arquivo in sorted(self._dir.glob("*.md")):
            if arquivo.name == "README.md":
                continue
            try:
                skill = self._parsear_arquivo(arquivo)
            except (KeyError, ValueError, TypeError) as e:
                _logger.warning("Pulando skill invalida %s: %s", arquivo.name, e)
                continue
            self._por_id[skill.id] = skill
            for tag in _arquivo_tags(arquivo):
                self._por_tag.setdefault(tag, []).append(skill)

    def _parsear_arquivo(self, arquivo: Path) -> Skill:
        post = frontmatter_module.loads(arquivo.read_text(encoding="utf-8"))
        meta = post.metadata
        if "id" not in meta or "nome" not in meta or "descricao" not in meta:
            raise KeyError("frontmatter requer id, nome e descricao")
        modelo_str = meta.get("modelo_minimo", "gemma")
        return Skill(
            id=str(meta["id"]),
            nome=str(meta["nome"]),
            descricao=str(meta["descricao"]),
            arquivo_path=str(arquivo.relative_to(self._dir).as_posix()),
            gatilhos=list(meta.get("gatilhos", []) or []),
            modelo_minimo=ModeloIA(modelo_str),
            origem=OrigemSkill.CORE,
            usos=0,
        )

    def get(self, id: str) -> Skill:
        if id not in self._por_id:
            raise SkillNotFoundError(f"Skill '{id}' nao registrada em {self._dir}")
        return self._por_id[id]

    def list_all(self) -> list[Skill]:
        return list(self._por_id.values())

    def list_by_tag(self, tag: str) -> list[Skill]:
        return list(self._por_tag.get(tag, []))


def _arquivo_tags(arquivo: Path) -> list[str]:
    """Le novamente apenas as tags do frontmatter (helper isolado para
    permitir indexacao por tag mesmo quando outras keys faltam)."""
    post = frontmatter_module.loads(arquivo.read_text(encoding="utf-8"))
    tags = post.metadata.get("tags", [])
    return [str(t) for t in (tags or [])]
