"""Schema do manifest.yaml de cada agente.

Cada agente em `stella/agents/<nome>/manifest.yaml` é parseado em uma
instância de `AgentManifest`. Validação por pydantic — erro claro se
algum campo obrigatório estiver faltando ou se referência (skill/MCP/RAG)
não puder ser resolvida.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CapacidadesExternas(BaseModel):
    """Capacidades externas declaradas no manifest (decisão #7).

    Skills, MCPs e RAG são RECURSOS COMPARTILHADOS — declarados aqui
    para visibilidade central (auditoria, permissões). Tools privadas
    (helpers internos do agente) NÃO entram aqui — ficam no código.
    """

    skills: list[str] = Field(default_factory=list)
    mcps: list[str] = Field(default_factory=list)
    rag: str | None = None
