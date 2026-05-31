"""HiggsFieldMCP — adapta o cliente Higgsfield ao seam de MCP (category=image).

Permite injetar a geração de imagem no agente via o mesmo mecanismo das MCPs
de pesquisa: registrado em build_stella, filtrado por `category == "image"`.
Conforma ao Protocol HiggsFieldClient (generate_image) para o ResolvedorImagens.
"""

from __future__ import annotations

from dataclasses import dataclass

from stella.adapters.higgsfield.base import HiggsFieldClient
from stella.domain.conexao_mcp import ConexaoMCP


@dataclass
class HiggsFieldMCP(ConexaoMCP):
    """ConexaoMCP que envolve um HiggsFieldClient + soul_id padrão."""

    client: HiggsFieldClient | None = None
    soul_id: str | None = None

    def __post_init__(self) -> None:
        if self.category is None:
            self.category = "image"

    def generate_image(self, prompt: str, soul_id: str | None = None) -> str:
        if self.client is None:
            raise RuntimeError("HiggsFieldMCP sem client configurado")
        return self.client.generate_image(prompt, soul_id=soul_id or self.soul_id)
