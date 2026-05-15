from pathlib import Path
from typing import Any

import frontmatter

from stella.adapters.vault.base import Note, VaultRepository


class ObsidianVaultRepository(VaultRepository):
    """Implementação de VaultRepository sobre o filesystem (vault Obsidian)."""

    def __init__(self, vault_root: Path):
        self._root = Path(vault_root)

    def _full_path(self, path: str) -> Path:
        return self._root / path

    def read_note(self, path: str) -> Note:
        full = self._full_path(path)
        if not full.exists():
            raise FileNotFoundError(f"Nota não encontrada: {path}")
        post = frontmatter.loads(full.read_text(encoding="utf-8"))
        return Note(path=path, frontmatter=dict(post.metadata), content=post.content)

    def list_notes_in_folder(self, folder: str) -> list[str]:
        full = self._full_path(folder)
        if not full.exists():
            return []
        resultado = []
        for arquivo in sorted(full.glob("*.md")):
            rel = arquivo.relative_to(self._root)
            resultado.append(str(rel).replace("\\", "/"))
        return resultado

    def write_note(
        self, path: str, content: str, frontmatter: dict[str, Any]
    ) -> None:
        raise NotImplementedError("Implementado na Task 9")

    def update_frontmatter(self, path: str, updates: dict[str, Any]) -> None:
        raise NotImplementedError("Implementado na Task 10")

    def note_exists(self, path: str) -> bool:
        raise NotImplementedError("Implementado na Task 9")
