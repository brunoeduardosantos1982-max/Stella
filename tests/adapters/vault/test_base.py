import pytest

from stella.adapters.vault.base import Note, VaultRepository


def test_note_estrutura():
    n = Note(
        path="A00 Inbox/ideia.md",
        frontmatter={"tipo": "ideia"},
        content="# Ideia\n\nTexto.",
    )
    assert n.path == "A00 Inbox/ideia.md"
    assert n.frontmatter["tipo"] == "ideia"


def test_vault_repository_e_abstrato():
    with pytest.raises(TypeError):
        VaultRepository()  # type: ignore[abstract]
