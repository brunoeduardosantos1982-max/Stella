from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
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
    def write_note(self, path: str, content: str, frontmatter: dict[str, Any]) -> None:
        """Cria ou sobrescreve a nota no caminho. Cria pastas intermediárias."""
        ...

    @abstractmethod
    def list_notes_in_folder(self, folder: str) -> list[str]:
        """Lista paths de notas .md diretas dentro de `folder`. Não recursivo.

        Retorna `[]` se a pasta não existir (não levanta exceção). Atenção a
        typos no path: ausência da pasta é silenciosa por design.
        """
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

    @abstractmethod
    def scan_recursive(self, pattern: str, since: datetime | None = None) -> list[Note]:
        """Varredura recursiva por glob pattern. HOOK Sub-projeto H.

        Args:
            pattern: glob relativo a raiz do vault, ex: "A04 **/*.md".
            since: se fornecido, filtra notas com mtime >= since.

        Retorna lista de `Note` totalmente carregadas (frontmatter + content).
        Retorna `[]` se nada bater no pattern.
        """
        ...

    @abstractmethod
    def scoped(self, pattern: str | list[str]) -> "VaultRepository":
        """Devolve um proxy do vault limitado ao glob `pattern` (ou lista de patterns).

        Qualquer operacao em path que nao bate com `pattern` levanta
        PermissionError. Usado pelo builder para isolar cada agente ao
        escopo declarado em seu manifest (manifest.vault_scope).

        Note: Atualmente aceita str ou list[str] na assinatura, mas internamente
        processa apenas str. Task 2 estenderá ScopedVaultRepository para suportar
        múltiplos patterns.
        """
        ...

    @abstractmethod
    def read_binary(self, path: str) -> bytes:
        """Lê um arquivo binário do vault (ex: imagem). Levanta FileNotFoundError
        se não existir."""
        ...

    @abstractmethod
    def write_binary(self, path: str, dados: bytes) -> None:
        """Escreve um arquivo binário no vault (ex: imagem). Cria pastas intermediárias."""
        ...
