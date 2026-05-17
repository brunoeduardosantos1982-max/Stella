"""Schema do manifest.yaml de cada agente.

Cada agente em `stella/agents/<nome>/manifest.yaml` é parseado em uma
instância de `AgentManifest`. Validação por pydantic — erro claro se
algum campo obrigatório estiver faltando ou se referência (skill/MCP/RAG)
não puder ser resolvida.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from stella.domain.enums import ModeloIA


class CapacidadesExternas(BaseModel):
    """Capacidades externas declaradas no manifest (decisão #7).

    Skills, MCPs e RAG são RECURSOS COMPARTILHADOS — declarados aqui
    para visibilidade central (auditoria, permissões). Tools privadas
    (helpers internos do agente) NÃO entram aqui — ficam no código.
    """

    skills: list[str] = Field(default_factory=list)
    mcps: list[str] = Field(default_factory=list)
    rag: str | None = None


class AgentManifest(BaseModel):
    """Manifest declarativo de um agente. Parseado de `manifest.yaml`.

    Decisão #6 — manifest equilibrado: descrição rica + inputs obrigatórios
    + exemplo de uso + quando_usar. SEM schema completo de input/output —
    LLM trata isso como ruído visual.
    """

    nome: str = Field(min_length=1)
    tipo: Literal["coordenador", "especialista"]
    setor: str = Field(min_length=1, description="marketing, ecommerce, financeiro, etc")
    descricao: str = Field(min_length=10)
    execucao: Literal["in_process", "http"]
    modelo_minimo: ModeloIA

    # Contrato (decisão #6):
    inputs_obrigatorios: list[str]
    exemplo_uso: dict[str, Any]
    quando_usar: str = Field(min_length=10)

    # Capacidades externas (decisão #7):
    capacidades_externas: CapacidadesExternas = Field(default_factory=CapacidadesExternas)
    vault_scope: str = Field(
        default="C04 Claude Obsidian/Stella-workspace/**",
        description="Glob limitando o que este agente pode ler/escrever no vault.",
    )

    # Coordenadores opcionalmente listam seus especialistas (auditoria):
    especialistas: list[str] = Field(default_factory=list)

    # HTTP-only: endpoint do servidor remoto
    endpoint: str | None = None
