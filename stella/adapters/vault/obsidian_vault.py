from datetime import datetime
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

    def write_note(self, path: str, content: str, frontmatter: dict[str, Any]) -> None:
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

    def read_binary(self, path: str) -> bytes:
        full = self._full_path(path)
        if not full.is_file():
            raise FileNotFoundError(f"Arquivo não encontrado: {path}")
        return full.read_bytes()

    def scan_recursive(self, pattern: str, since: datetime | None = None) -> list[Note]:
        cutoff = since.timestamp() if since is not None else None

        resultado: list[Note] = []
        for arquivo in sorted(self._root.glob(pattern)):
            if not arquivo.is_file() or arquivo.suffix != ".md":
                continue
            if cutoff is not None and arquivo.stat().st_mtime < cutoff:
                continue
            rel = str(arquivo.relative_to(self._root)).replace("\\", "/")
            resultado.append(self.read_note(rel))
        return resultado

    def scoped(self, pattern: str | list[str]) -> "VaultRepository":
        # Import local para evitar ciclo na carga do modulo
        from stella.adapters.vault.scoped import ScopedVaultRepository

        # Temporariamente: se receber lista, pega o primeiro padrão
        # Task 2 estenderá ScopedVaultRepository para suportar múltiplos patterns
        if isinstance(pattern, list):
            pattern = pattern[0] if pattern else "*"
        return ScopedVaultRepository(self, pattern)
