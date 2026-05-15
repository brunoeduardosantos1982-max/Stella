from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Note:
    path: str
    frontmatter: dict
    content: str


class VaultRepository(ABC):
    """Contrato para leitura e escrita de notas no vault Obsidian.

    Todos os paths são relativos à raiz do vault.
    """

    @abstractmethod
    def read_note(self, path: str) -> Note:
        ...

    @abstractmethod
    def write_note(self, path: str, content: str, frontmatter: dict) -> None:
        ...

    @abstractmethod
    def list_notes_in_folder(self, folder: str) -> list[str]:
        ...

    @abstractmethod
    def update_frontmatter(self, path: str, updates: dict) -> None:
        ...
