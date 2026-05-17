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


def test_update_frontmatter_altera_campo_existente(vault_tmp):
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    repo.update_frontmatter("B01 Projetos/Centro Viagens.md", {"status": "concluido"})
    nota = repo.read_note("B01 Projetos/Centro Viagens.md")
    assert nota.frontmatter["status"] == "concluido"
    assert nota.frontmatter["tipo"] == "projeto"  # campo intacto


def test_update_frontmatter_adiciona_campo_novo(vault_tmp):
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    repo.update_frontmatter("B01 Projetos/Centro Viagens.md", {"prioridade": "alta"})
    nota = repo.read_note("B01 Projetos/Centro Viagens.md")
    assert nota.frontmatter["prioridade"] == "alta"


def test_update_frontmatter_preserva_conteudo(vault_tmp):
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    repo.update_frontmatter("B01 Projetos/Centro Viagens.md", {"status": "pausado"})
    nota = repo.read_note("B01 Projetos/Centro Viagens.md")
    assert "Projeto de viagens." in nota.content


def test_update_frontmatter_nota_inexistente_levanta_erro(vault_tmp):
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    with pytest.raises(FileNotFoundError):
        repo.update_frontmatter("B01 Projetos/fantasma.md", {"x": 1})


def test_scan_recursive_encontra_notas_via_glob(tmp_path) -> None:
    """HOOK Sub-projeto H: scan recursivo respeitando glob."""
    (tmp_path / "A04" / "sub").mkdir(parents=True)
    (tmp_path / "A04" / "n1.md").write_text("---\nt: 1\n---\nhello", encoding="utf-8")
    (tmp_path / "A04" / "sub" / "n2.md").write_text("---\nt: 2\n---\nworld", encoding="utf-8")
    (tmp_path / "B01" / "outro").mkdir(parents=True)
    (tmp_path / "B01" / "outro" / "n3.md").write_text("---\nt: 3\n---\nfora", encoding="utf-8")

    repo = ObsidianVaultRepository(tmp_path)
    notas = repo.scan_recursive("A04/**/*.md")
    paths = {n.path for n in notas}
    assert paths == {"A04/n1.md", "A04/sub/n2.md"}


def test_scan_recursive_filtra_por_since(tmp_path) -> None:
    """`since` filtra por mtime — apenas notas modificadas a partir do timestamp."""
    import os
    import time
    from datetime import datetime, timedelta

    pasta = tmp_path / "A04"
    pasta.mkdir()
    antiga = pasta / "antiga.md"
    nova = pasta / "nova.md"
    antiga.write_text("---\nt: a\n---\n", encoding="utf-8")
    nova.write_text("---\nt: n\n---\n", encoding="utf-8")

    uma_hora_atras = time.time() - 3600
    os.utime(antiga, (uma_hora_atras, uma_hora_atras))

    repo = ObsidianVaultRepository(tmp_path)
    corte = datetime.now() - timedelta(minutes=30)
    notas = repo.scan_recursive("A04/**/*.md", since=corte)
    paths = {n.path for n in notas}
    assert paths == {"A04/nova.md"}


def test_scan_recursive_vazio_quando_nada_bate(tmp_path) -> None:
    repo = ObsidianVaultRepository(tmp_path)
    assert repo.scan_recursive("nao-existe/**/*.md") == []
