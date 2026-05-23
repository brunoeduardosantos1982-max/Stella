"""ScopedVaultRepository — wrapping com isolamento por glob.

Builder do framework (build_agent) usa para limitar cada agente ao escopo
declarado em manifest.vault_scope. Toda operacao em path fora do glob
levanta PermissionError, em vez de ler/escrever silenciosamente.
"""

from __future__ import annotations

from datetime import datetime
from fnmatch import fnmatchcase
from typing import Any

from stella.adapters.vault.base import Note, VaultRepository


class ScopedVaultRepository(VaultRepository):
    """Proxy que limita um VaultRepository ao paths que batem com `pattern` (ou lista de patterns)."""

    def __init__(self, inner: VaultRepository, patterns: str | list[str]) -> None:
        self._inner = inner
        # Normalizar string única → lista de 1 padrão
        if isinstance(patterns, str):
            self._patterns = [patterns]
        else:
            self._patterns = list(patterns)

    def _check(self, path: str) -> None:
        """Levanta PermissionError se `path` nao bate com NENHUM dos globs do scope (OR-match).

        Normaliza separador de path (Windows usa '\\' mas comparamos como '/').
        """
        normalizado = path.replace("\\", "/")
        # OR-match: path deve bater em pelo menos um dos padrões
        if not any(_glob_match(normalizado, pattern) for pattern in self._patterns):
            patterns_str = " OR ".join(self._patterns)
            raise PermissionError(f"Path '{path}' fora do escopo '{patterns_str}' deste vault")

    def read_note(self, path: str) -> Note:
        self._check(path)
        return self._inner.read_note(path)

    def write_note(self, path: str, content: str, frontmatter: dict[str, Any]) -> None:
        self._check(path)
        self._inner.write_note(path, content, frontmatter)

    def list_notes_in_folder(self, folder: str) -> list[str]:
        # Folder em si precisa estar dentro do scope. Como folders nao tem
        # extensao .md, usamos um path-marcador para validar.
        marcador = f"{folder.rstrip('/')}/.scope_check"
        self._check(marcador)
        return self._inner.list_notes_in_folder(folder)

    def update_frontmatter(self, path: str, updates: dict[str, Any]) -> None:
        self._check(path)
        self._inner.update_frontmatter(path, updates)

    def note_exists(self, path: str) -> bool:
        self._check(path)
        return self._inner.note_exists(path)

    def read_binary(self, path: str) -> bytes:
        self._check(path)
        return self._inner.read_binary(path)

    def scan_recursive(self, pattern: str, since: datetime | None = None) -> list[Note]:
        """Combina o glob do scope com o pattern do agente — devolve apenas
        notas que satisfazem AMBOS (intersecao via filtro no resultado).

        Usando OR-match nos padrões do scope: nota é incluída se bater em
        qualquer um dos patterns AND no pattern do agente.
        """
        bruto = self._inner.scan_recursive(pattern, since=since)
        return [
            n
            for n in bruto
            if any(_glob_match(n.path.replace("\\", "/"), p) for p in self._patterns)
        ]

    def scoped(self, pattern: str | list[str]) -> VaultRepository:
        """Permite encadear: vault.scoped(A).scoped(B). Ambos validam.

        Aceita string única ou lista de padrões. Com lista, faz OR-match:
        path é válido se bater em qualquer um dos padrões.
        """
        return ScopedVaultRepository(self, pattern)


def _glob_match(path: str, pattern: str) -> bool:
    """Match de glob compat com Path.glob — '**' bate qualquer profundidade."""
    if "**" in pattern:
        sem_double = pattern.replace("**", "*")
        if fnmatchcase(path, sem_double):
            return True
        prefixo = pattern.split("**", 1)[0].rstrip("/")
        sufixo = pattern.split("**", 1)[1].lstrip("/")
        if prefixo and not path.startswith(prefixo):
            return False
        if sufixo and not fnmatchcase(path, f"*{sufixo}"):
            return False
        return True
    return fnmatchcase(path, pattern)
