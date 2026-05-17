from datetime import datetime, timedelta

import pytest

from stella.framework.testing.fakes import FakeVault


def test_fake_vault_vazio_por_default() -> None:
    v = FakeVault()
    assert v.list_notes_in_folder("qualquer") == []
    assert v.note_exists("x.md") is False


def test_fake_vault_aceita_notas_iniciais_via_construtor() -> None:
    v = FakeVault(
        notes={
            "A00 Inbox/ideia.md": ("conteudo", {"tipo": "ideia"}),
        }
    )
    assert v.note_exists("A00 Inbox/ideia.md") is True
    nota = v.read_note("A00 Inbox/ideia.md")
    assert nota.frontmatter == {"tipo": "ideia"}
    assert "conteudo" in nota.content


def test_fake_vault_write_note_armazena_e_le_de_volta() -> None:
    v = FakeVault()
    v.write_note("A00 Inbox/nova.md", "conteudo da nota", {"tipo": "ideia"})
    nota = v.read_note("A00 Inbox/nova.md")
    assert nota.content == "conteudo da nota"
    assert nota.frontmatter == {"tipo": "ideia"}


def test_fake_vault_read_note_inexistente_levanta_file_not_found() -> None:
    v = FakeVault()
    with pytest.raises(FileNotFoundError):
        v.read_note("nao-existe.md")


def test_fake_vault_list_notes_in_folder() -> None:
    v = FakeVault()
    v.write_note("A00 Inbox/a.md", "", {})
    v.write_note("A00 Inbox/b.md", "", {})
    v.write_note("B01 Projetos/c.md", "", {})
    listadas = v.list_notes_in_folder("A00 Inbox")
    assert set(listadas) == {"A00 Inbox/a.md", "A00 Inbox/b.md"}


def test_fake_vault_update_frontmatter() -> None:
    v = FakeVault()
    v.write_note("x.md", "corpo", {"tipo": "ideia", "status": "aberto"})
    v.update_frontmatter("x.md", {"status": "concluido", "novo": True})
    nota = v.read_note("x.md")
    assert nota.frontmatter["status"] == "concluido"
    assert nota.frontmatter["tipo"] == "ideia"
    assert nota.frontmatter["novo"] is True
    assert nota.content == "corpo"


def test_fake_vault_update_frontmatter_inexistente_levanta() -> None:
    v = FakeVault()
    with pytest.raises(FileNotFoundError):
        v.update_frontmatter("x.md", {"a": 1})


def test_fake_vault_scan_recursive_filtra_por_glob() -> None:
    v = FakeVault()
    v.write_note("A04/n1.md", "", {})
    v.write_note("A04/sub/n2.md", "", {})
    v.write_note("B01/n3.md", "", {})
    notas = v.scan_recursive("A04/**/*.md")
    paths = {n.path for n in notas}
    assert paths == {"A04/n1.md", "A04/sub/n2.md"}


def test_fake_vault_scan_recursive_filtra_por_since() -> None:
    """`since` filtra por timestamp interno do FakeVault."""
    v = FakeVault()
    momento_velho = datetime.now() - timedelta(hours=1)
    momento_novo = datetime.now()
    v.write_note("a.md", "", {}, _mtime=momento_velho)
    v.write_note("b.md", "", {}, _mtime=momento_novo)
    corte = datetime.now() - timedelta(minutes=30)
    notas = v.scan_recursive("*.md", since=corte)
    paths = {n.path for n in notas}
    assert paths == {"b.md"}


def test_fake_vault_scoped_aplica_isolamento() -> None:
    """FakeVault.scoped(pattern) usa ScopedVaultRepository real."""
    from stella.adapters.vault.scoped import ScopedVaultRepository

    v = FakeVault()
    v.write_note("marketing/copy.md", "x", {})
    scoped = v.scoped("marketing/**")
    assert isinstance(scoped, ScopedVaultRepository)
    assert scoped.note_exists("marketing/copy.md") is True
    with pytest.raises(PermissionError):
        scoped.note_exists("financeiro/x.md")
