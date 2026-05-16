from pathlib import Path

import pytest


@pytest.fixture
def vault_tmp(tmp_path: Path) -> Path:
    """Cria um vault Obsidian temporário com algumas notas para teste."""
    (tmp_path / "A00 Inbox").mkdir()
    (tmp_path / "B01 Projetos").mkdir()

    nota1 = tmp_path / "A00 Inbox" / "ideia-um.md"
    nota1.write_text(
        "---\ntipo: ideia\ntags:\n  - inbox\n---\n\n# Ideia Um\n\nConteúdo da ideia.\n",
        encoding="utf-8",
    )

    nota2 = tmp_path / "B01 Projetos" / "Centro Viagens.md"
    nota2.write_text(
        "---\ntipo: projeto\nstatus: ativo\n---\n\n# Centro Viagens\n\nProjeto de viagens.\n",
        encoding="utf-8",
    )

    return tmp_path
