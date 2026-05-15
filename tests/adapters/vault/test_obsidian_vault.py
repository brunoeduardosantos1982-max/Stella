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


def test_write_note_cria_arquivo_com_frontmatter(vault_tmp):
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    repo.write_note(
        "A00 Inbox/nova.md",
        content="# Nova\n\nTexto novo.",
        frontmatter={"tipo": "ideia", "status": "aberta"},
    )
    nota = repo.read_note("A00 Inbox/nova.md")
    assert nota.frontmatter["tipo"] == "ideia"
    assert nota.frontmatter["status"] == "aberta"
    assert "Texto novo." in nota.content


def test_write_note_cria_pastas_intermediarias(vault_tmp):
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    repo.write_note(
        "C04 Claude Obsidian/Stella-tarefas/t1.md",
        content="# Tarefa",
        frontmatter={"id": "t1"},
    )
    assert (vault_tmp / "C04 Claude Obsidian" / "Stella-tarefas" / "t1.md").exists()


def test_write_note_nao_deixa_arquivo_tmp(vault_tmp):
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    repo.write_note("A00 Inbox/nova.md", content="# Nova", frontmatter={"tipo": "ideia"})
    tmp_files = list((vault_tmp / "A00 Inbox").glob("*.tmp"))
    assert tmp_files == []


def test_write_note_sobrescreve_existente(vault_tmp):
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    repo.write_note("A00 Inbox/ideia-um.md", content="# Atualizada", frontmatter={"tipo": "ideia"})
    nota = repo.read_note("A00 Inbox/ideia-um.md")
    assert "Atualizada" in nota.content


def test_note_exists_retorna_true_para_nota_existente(vault_tmp):
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    assert repo.note_exists("A00 Inbox/ideia-um.md") is True


def test_note_exists_retorna_false_para_nota_inexistente(vault_tmp):
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    assert repo.note_exists("A00 Inbox/nao-existe.md") is False
