from pathlib import Path
from typing import Any

# alias para evitar shadowing com o parâmetro `frontmatter` em write_note
import frontmatter as frontmatter_module
import portalocker

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
        post = frontmatter_module.loads(full.read_text(encoding="utf-8"))
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
        full = self._full_path(path)
        full.parent.mkdir(parents=True, exist_ok=True)

        post = frontmatter_module.Post(content, **frontmatter)
        texto = frontmatter_module.dumps(post)

        tmp = full.with_suffix(full.suffix + ".tmp")
        with portalocker.Lock(str(tmp), mode="w", timeout=5, encoding="utf-8") as fh:
            fh.write(texto)
        tmp.replace(full)

    def update_frontmatter(self, path: str, updates: dict[str, Any]) -> None:
        nota = self.read_note(path)
        novo_frontmatter = {**nota.frontmatter, **updates}
        self.write_note(path, content=nota.content, frontmatter=novo_frontmatter)

    def note_exists(self, path: str) -> bool:
        # is_file() em vez de exists() para distinguir nota de diretório homônimo
        return self._full_path(path).is_file()
