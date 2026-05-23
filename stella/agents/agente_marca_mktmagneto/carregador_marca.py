"""CarregadorMarca — lê os 3 docs canônicos da marca @mktmagneto.ia do vault."""

from __future__ import annotations

from dataclasses import dataclass

from stella.adapters.vault.base import VaultRepository

_BASE = "C04 Claude Obsidian/projetos e specs/mktmagneto.ia/"

_DOCS_DA_MARCA: dict[str, str] = {
    "spec": _BASE + "mktmagneto.ia — 01 Spec.md",
    "briefing": _BASE + "mktmagneto.ia — 03 Briefing do Agente de Conteúdo.md",
    "kit": _BASE + "mktmagneto.ia — 04 Kit de Identidade Visual.md",
}


@dataclass
class CarregadorMarca:
    """Lê spec + briefing + kit visual do vault e devolve o knowledge pack.

    Knowledge pack = dict[str, str] com 3 chaves: spec, briefing, kit.
    Cada valor é o content do .md correspondente.

    Erro: levanta FileNotFoundError com o nome do doc ausente se algum
    dos 3 não estiver no vault.
    """

    vault: VaultRepository

    def carregar(self) -> dict[str, str]:
        pack: dict[str, str] = {}
        for chave, path in _DOCS_DA_MARCA.items():
            try:
                pack[chave] = self.vault.read_note(path).content
            except FileNotFoundError as e:
                raise FileNotFoundError(f"Doc da marca '{chave}' não encontrado em {path}") from e
        return pack
