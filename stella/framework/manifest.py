"""Schema do manifest.yaml de cada agente.

Cada agente em `stella/agents/<nome>/manifest.yaml` é parseado em uma
instância de `AgentManifest`. Validação por pydantic — erro claro se
algum campo obrigatório estiver faltando ou se referência (skill/MCP/RAG)
não puder ser resolvida.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError

from stella.domain.enums import ModeloIA
from stella.framework.errors import (
    ManifestError,
    MCPNotFoundError,
    RAGNotFoundError,
    SkillNotFoundError,
)

if TYPE_CHECKING:
    from stella.framework.builder import FrameworkDeps


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


def load_manifest(path: Path) -> AgentManifest:
    """Carrega e valida um manifest.yaml.

    Levanta ManifestError com mensagem clara em qualquer falha:
    - Arquivo não existe
    - YAML malformado
    - Validação pydantic falha (campo faltando, tipo inválido, etc)
    """
    if not path.exists():
        raise ManifestError(f"Manifest não encontrado em: {path}")

    try:
        dados = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ManifestError(f"YAML malformado em {path}: {e}") from e

    if not isinstance(dados, dict):
        raise ManifestError(
            f"Manifest em {path} deve ser um objeto YAML (dict), não {type(dados).__name__}"
        )

    try:
        return AgentManifest(**dados)
    except ValidationError as e:
        raise ManifestError(
            f"Manifest inválido em {path}: campo ou valor não atende ao schema. Detalhe: {e}"
        ) from e


def validate_manifest_resources(manifest: AgentManifest, deps: FrameworkDeps) -> list[str]:
    """Valida que skills/MCPs/RAG declarados no manifest existem nos registries.

    Devolve lista de mensagens de erro (vazia = tudo OK). Nao levanta excecao —
    chamador decide se loga warning ou faz fail-fast. Usado por `build_stella`
    como early warning didatico no startup.
    """
    erros: list[str] = []
    cap = manifest.capacidades_externas

    for skill_id in cap.skills:
        try:
            deps.skills_reg.get(skill_id)
        except SkillNotFoundError:
            erros.append(f"skill '{skill_id}' declarada mas nao registrada")

    for mcp_nome in cap.mcps:
        try:
            deps.mcp_reg.get(mcp_nome)
        except MCPNotFoundError:
            erros.append(f"MCP '{mcp_nome}' declarada mas nao registrada")

    if cap.rag is not None:
        try:
            deps.rag_reg.get(cap.rag)
        except RAGNotFoundError:
            erros.append(f"RAG '{cap.rag}' declarado mas nao registrado")

    return erros
