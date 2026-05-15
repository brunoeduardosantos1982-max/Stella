from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class Note:
    """Representa uma nota do vault Obsidian.

    Atributos:
        path: caminho relativo à raiz do vault (ex: "A00 Inbox/ideia.md").
        frontmatter: dicionário do bloco YAML do topo da nota (vazio se a
            nota não tiver frontmatter).
        content: corpo da nota EXCLUINDO o bloco frontmatter YAML.
    """

    path: str
    frontmatter: dict[str, Any]
    content: str


class VaultRepository(ABC):
    """Contrato para leitura e escrita de notas no vault Obsidian.

    Todos os paths são relativos à raiz do vault.
    """

    @abstractmethod
    def read_note(self, path: str) -> Note:
        """Lê uma nota do vault. Levanta FileNotFoundError se não existir."""
        ...

    @abstractmethod
    def write_note(
        self, path: str, content: str, frontmatter: dict[str, Any]
    ) -> None:
        """Cria ou sobrescreve a nota no caminho. Cria pastas intermediárias."""
        ...

    @abstractmethod
    def list_notes_in_folder(self, folder: str) -> list[str]:
        """Lista paths de notas .md diretas dentro de `folder`. Não recursivo."""
        ...

    @abstractmethod
    def update_frontmatter(self, path: str, updates: dict[str, Any]) -> None:
        """Merge `updates` no frontmatter da nota, preservando chaves não tocadas
        e o conteúdo. Levanta FileNotFoundError se a nota não existir."""
        ...

    @abstractmethod
    def note_exists(self, path: str) -> bool:
        """Retorna True se a nota existe no caminho dado."""
        ...
