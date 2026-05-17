"""Fixtures de teste reusaveis para o framework multi-agente.

Todas as Fake* num arquivo so para visibilidade central. Cada Fake implementa
o contrato da ABC correspondente, com estado in-memory para testes rapidos.
"""

from __future__ import annotations

from datetime import datetime
from fnmatch import fnmatchcase
from typing import Any

from stella.adapters.vault.base import Note, VaultRepository


class FakeVault(VaultRepository):
    """VaultRepository in-memory.

    Notas sao armazenadas em dict {path: (content, frontmatter, mtime)}.
    `notes` no construtor aceita {path: (content, frontmatter)} para conveniencia
    (mtime e setado automaticamente para datetime.now()).
    """

    def __init__(
        self,
        notes: dict[str, tuple[str, dict[str, Any]]] | None = None,
    ) -> None:
        self._store: dict[str, tuple[str, dict[str, Any], datetime]] = {}
        if notes:
            agora = datetime.now()
            for path, (content, fm) in notes.items():
                self._store[path] = (content, dict(fm), agora)

    def read_note(self, path: str) -> Note:
        if path not in self._store:
            raise FileNotFoundError(f"Nota nao encontrada: {path}")
        content, fm, _ = self._store[path]
        return Note(path=path, frontmatter=dict(fm), content=content)

    def write_note(
        self,
        path: str,
        content: str,
        frontmatter: dict[str, Any],
        _mtime: datetime | None = None,
    ) -> None:
        """Argumento `_mtime` e extensao do FakeVault para controlar timestamp
        em testes de scan_recursive(since=...). Producao usa datetime.now()."""
        self._store[path] = (content, dict(frontmatter), _mtime or datetime.now())

    def list_notes_in_folder(self, folder: str) -> list[str]:
        prefixo = folder.rstrip("/") + "/"
        return [p for p in self._store if p.startswith(prefixo) and "/" not in p[len(prefixo) :]]

    def update_frontmatter(self, path: str, updates: dict[str, Any]) -> None:
        if path not in self._store:
            raise FileNotFoundError(f"Nota nao encontrada: {path}")
        content, fm, mtime = self._store[path]
        novo_fm = {**fm, **updates}
        self._store[path] = (content, novo_fm, mtime)

    def note_exists(self, path: str) -> bool:
        return path in self._store

    def scan_recursive(self, pattern: str, since: datetime | None = None) -> list[Note]:
        cutoff = since.timestamp() if since is not None else None
        resultado: list[Note] = []
        for path, (content, fm, mtime) in self._store.items():
            if not _fake_glob_match(path, pattern):
                continue
            if cutoff is not None and mtime.timestamp() < cutoff:
                continue
            resultado.append(Note(path=path, frontmatter=dict(fm), content=content))
        return resultado

    def scoped(self, pattern: str) -> VaultRepository:
        from stella.adapters.vault.scoped import ScopedVaultRepository

        return ScopedVaultRepository(self, pattern)


def _fake_glob_match(path: str, pattern: str) -> bool:
    """Match de glob compat com Path.glob — '**' bate qualquer profundidade.

    Replica logica de stella/adapters/vault/scoped.py:_glob_match para que
    FakeVault.scan_recursive funcione sem depender do filesystem real.
    """
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
