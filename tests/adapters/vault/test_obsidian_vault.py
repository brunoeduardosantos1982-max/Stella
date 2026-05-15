import pytest

from stella.adapters.vault.obsidian_vault import ObsidianVaultRepository


def test_read_note_le_frontmatter_e_conteudo(vault_tmp):
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    nota = repo.read_note("A00 Inbox/ideia-um.md")
    assert nota.frontmatter["tipo"] == "ideia"
    assert "Conteúdo da ideia." in nota.content


def test_read_note_inexistente_levanta_erro(vault_tmp):
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    with pytest.raises(FileNotFoundError):
        repo.read_note("A00 Inbox/nao-existe.md")


def test_list_notes_in_folder(vault_tmp):
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    notas = repo.list_notes_in_folder("B01 Projetos")
    assert notas == ["B01 Projetos/Centro Viagens.md"]


def test_list_notes_in_folder_vazia_retorna_lista_vazia(vault_tmp):
    (vault_tmp / "B03 Arquivos").mkdir()
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    assert repo.list_notes_in_folder("B03 Arquivos") == []
