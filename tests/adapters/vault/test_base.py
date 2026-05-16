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


def test_vault_repository_exige_todos_os_metodos():
    """Subclasse que esquece de implementar algum método não pode instanciar."""

    class IncompletaSemNoteExists(VaultRepository):
        def read_note(self, path): ...

        def write_note(self, path, content, frontmatter): ...

        def list_notes_in_folder(self, folder):
            return []

        def update_frontmatter(self, path, updates): ...

        # Falta note_exists

    with pytest.raises(TypeError):
        IncompletaSemNoteExists()  # type: ignore[abstract]
