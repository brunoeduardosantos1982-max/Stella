from pathlib import Path

import pytest

from stella.framework.errors import SkillNotFoundError
from stella.framework.resources.skills_registry import SkillsRegistry


def _escrever_skill(dir: Path, id: str, tags: list[str], modelo: str = "gemma") -> None:
    """Helper — cria um arquivo .md de skill com frontmatter mínimo."""
    tags_yaml = "[" + ", ".join(tags) + "]"
    p = dir / f"{id}.md"
    p.write_text(
        f"---\n"
        f"id: {id}\n"
        f"nome: Skill {id}\n"
        f"descricao: Descricao da skill {id} para testes\n"
        f"gatilhos: []\n"
        f"modelo_minimo: {modelo}\n"
        f"tags: {tags_yaml}\n"
        f"---\n\n"
        f"Conteudo da skill {id}.\n",
        encoding="utf-8",
    )


def test_skills_registry_vazio_quando_pasta_vazia(tmp_path: Path) -> None:
    reg = SkillsRegistry(tmp_path)
    assert reg.list_all() == []


def test_skills_registry_carrega_skills_da_pasta(tmp_path: Path) -> None:
    _escrever_skill(tmp_path, "copy-pt-br", ["marketing", "revisao"])
    _escrever_skill(tmp_path, "ab-testing", ["marketing"])
    reg = SkillsRegistry(tmp_path)
    todas = reg.list_all()
    ids = {s.id for s in todas}
    assert ids == {"copy-pt-br", "ab-testing"}


def test_skills_registry_get_devolve_skill_por_id(tmp_path: Path) -> None:
    _escrever_skill(tmp_path, "copy-pt-br", ["marketing"])
    reg = SkillsRegistry(tmp_path)
    s = reg.get("copy-pt-br")
    assert s.id == "copy-pt-br"
    assert s.nome == "Skill copy-pt-br"


def test_skills_registry_get_levanta_skill_not_found(tmp_path: Path) -> None:
    reg = SkillsRegistry(tmp_path)
    with pytest.raises(SkillNotFoundError, match="nao-existe"):
        reg.get("nao-existe")


def test_skills_registry_list_by_tag(tmp_path: Path) -> None:
    _escrever_skill(tmp_path, "copy-pt-br", ["marketing", "revisao"])
    _escrever_skill(tmp_path, "ab-testing", ["marketing"])
    _escrever_skill(tmp_path, "gramatica", ["revisao"])
    reg = SkillsRegistry(tmp_path)
    marketing = {s.id for s in reg.list_by_tag("marketing")}
    revisao = {s.id for s in reg.list_by_tag("revisao")}
    assert marketing == {"copy-pt-br", "ab-testing"}
    assert revisao == {"copy-pt-br", "gramatica"}


def test_skills_registry_ignora_arquivos_sem_frontmatter_valido(tmp_path: Path) -> None:
    """Skill com frontmatter inválido é pulada com warning, não derruba o registry."""
    (tmp_path / "quebrada.md").write_text("sem frontmatter aqui\n", encoding="utf-8")
    _escrever_skill(tmp_path, "ok", ["x"])
    reg = SkillsRegistry(tmp_path)
    ids = {s.id for s in reg.list_all()}
    assert ids == {"ok"}
