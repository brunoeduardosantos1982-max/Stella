"""Testes do ScopedVaultRepository — wrapping com isolamento por glob."""

from pathlib import Path

import pytest

from stella.adapters.vault.obsidian_vault import ObsidianVaultRepository


def _vault_com_arquivos(tmp_path: Path) -> ObsidianVaultRepository:
    """Helper — monta um vault temp com algumas notas em pastas diferentes."""
    (tmp_path / "marketing").mkdir()
    (tmp_path / "marketing" / "copy.md").write_text(
        "---\nt: 1\n---\nconteudo marketing", encoding="utf-8"
    )
    (tmp_path / "financeiro").mkdir()
    (tmp_path / "financeiro" / "fluxo.md").write_text(
        "---\nt: 2\n---\nconteudo financeiro", encoding="utf-8"
    )
    return ObsidianVaultRepository(tmp_path)


def test_scoped_read_dentro_do_escopo_funciona(tmp_path: Path) -> None:
    vault = _vault_com_arquivos(tmp_path)
    scoped = vault.scoped("marketing/**")
    nota = scoped.read_note("marketing/copy.md")
    assert nota.content == "conteudo marketing"


def test_scoped_read_fora_do_escopo_levanta_permission_error(tmp_path: Path) -> None:
    vault = _vault_com_arquivos(tmp_path)
    scoped = vault.scoped("marketing/**")
    with pytest.raises(PermissionError, match="financeiro/fluxo.md"):
        scoped.read_note("financeiro/fluxo.md")


def test_scoped_write_dentro_do_escopo_funciona(tmp_path: Path) -> None:
    vault = _vault_com_arquivos(tmp_path)
    scoped = vault.scoped("marketing/**")
    scoped.write_note("marketing/nova.md", "novo conteudo", {"t": 9})
    assert (tmp_path / "marketing" / "nova.md").exists()


def test_scoped_write_fora_do_escopo_levanta_permission_error(tmp_path: Path) -> None:
    vault = _vault_com_arquivos(tmp_path)
    scoped = vault.scoped("marketing/**")
    with pytest.raises(PermissionError):
        scoped.write_note("financeiro/proibido.md", "x", {})


def test_scoped_list_dentro_do_escopo_funciona(tmp_path: Path) -> None:
    vault = _vault_com_arquivos(tmp_path)
    scoped = vault.scoped("marketing/**")
    notas = scoped.list_notes_in_folder("marketing")
    assert notas == ["marketing/copy.md"]


def test_scoped_list_fora_do_escopo_levanta(tmp_path: Path) -> None:
    vault = _vault_com_arquivos(tmp_path)
    scoped = vault.scoped("marketing/**")
    with pytest.raises(PermissionError):
        scoped.list_notes_in_folder("financeiro")


def test_scoped_note_exists_fora_do_escopo_levanta(tmp_path: Path) -> None:
    vault = _vault_com_arquivos(tmp_path)
    scoped = vault.scoped("marketing/**")
    with pytest.raises(PermissionError):
        scoped.note_exists("financeiro/fluxo.md")


def test_scoped_update_frontmatter_fora_do_escopo_levanta(tmp_path: Path) -> None:
    vault = _vault_com_arquivos(tmp_path)
    scoped = vault.scoped("marketing/**")
    with pytest.raises(PermissionError):
        scoped.update_frontmatter("financeiro/fluxo.md", {"x": 1})


def test_scoped_scan_recursive_filtra_para_dentro_do_escopo(tmp_path: Path) -> None:
    """scan_recursive em scoped: forca o pattern do scope a se aplicar."""
    vault = _vault_com_arquivos(tmp_path)
    scoped = vault.scoped("marketing/**")
    notas = scoped.scan_recursive("**/*.md")
    paths = {n.path for n in notas}
    assert paths == {"marketing/copy.md"}


def test_scoped_double_scope_combina_glob(tmp_path: Path) -> None:
    """scoped().scoped() ainda valida o segundo glob (pode ser subset)."""
    vault = _vault_com_arquivos(tmp_path)
    scoped1 = vault.scoped("marketing/**")
    scoped2 = scoped1.scoped("marketing/copy*")
    assert scoped2.read_note("marketing/copy.md").content == "conteudo marketing"
    with pytest.raises(PermissionError):
        scoped2.note_exists("marketing/outra.md")
