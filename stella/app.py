import logging
from dataclasses import dataclass

from stella.adapters.llm.anthropic_provider import AnthropicProvider
from stella.adapters.llm.gemma_nvidia import GemmaNvidiaProvider
from stella.adapters.llm.router import LLMRouter
from stella.adapters.vault.obsidian_vault import ObsidianVaultRepository
from stella.domain.conexao_mcp import ConexaoMCP
from stella.framework.builder import FrameworkDeps, build_agent
from stella.framework.manifest import validate_manifest_resources
from stella.framework.quality.feedback import FeedbackLogger
from stella.framework.quality.policies import ReviewPolicy
from stella.framework.quality.reviewer import QualityReviewer
from stella.framework.registry import AgentRegistry
from stella.framework.resources.mcp_registry import MCPRegistry
from stella.framework.resources.rag_registry import RAGRegistry
from stella.framework.resources.skills_registry import SkillsRegistry
from stella.infra.config import StellaConfig
from stella.infra.usage_tracker import UsageTracker
from stella.prompts.prompt_builder import PromptBuilder
from stella.usecases.atualizar_memoria import AtualizarMemoria
from stella.usecases.capturar_ideia import CapturarIdeia
from stella.usecases.responder_projeto import ResponderProjeto

_logger = logging.getLogger("stella.framework")


@dataclass
class Stella:
    """Container principal — todos os componentes da Stella prontos para uso.

    Campos M1+M2 (Sub-projeto Stella Fase 1) + FB-M4 (Framework Base integrado).
    """

    # M1+M2:
    vault: ObsidianVaultRepository
    gemma: GemmaNvidiaProvider
    anthropic: AnthropicProvider
    router: LLMRouter
    prompt_builder: PromptBuilder
    capturar_ideia: CapturarIdeia
    responder_projeto: ResponderProjeto
    atualizar_memoria: AtualizarMemoria
    usage_tracker: UsageTracker

    # FB-M4 (framework integrado):
    opus: AnthropicProvider
    skills_reg: SkillsRegistry
    mcp_reg: MCPRegistry
    rag_reg: RAGRegistry
    registry: AgentRegistry
    framework_deps: FrameworkDeps
    quality_reviewer: QualityReviewer
    feedback_logger: FeedbackLogger


def build_stella(config: StellaConfig) -> Stella:
    """Monta toda a árvore de dependências da Stella a partir do config."""
    vault = ObsidianVaultRepository(vault_root=config.vault_path)
    tracker = UsageTracker()

    gemma = GemmaNvidiaProvider(
        api_key=config.nvidia_api_key.get_secret_value(),
        tracker=tracker,
    )
    anthropic = AnthropicProvider(
        api_key=config.anthropic_api_key.get_secret_value(),
        tracker=tracker,
    )
    # FB-M4 B6: provider Opus dedicado
    opus = AnthropicProvider(
        api_key=config.anthropic_api_key.get_secret_value(),
        tracker=tracker,
        modelo="claude-opus-4-7",
    )
    router = LLMRouter(
        gemma=gemma,
        anthropic=anthropic,
        opus=opus,
        default=config.modelo_padrao.value,
    )
    prompt_builder = PromptBuilder()

    capturar_ideia = CapturarIdeia(
        llm=router.select(complexity="low"),
        vault_repo=vault,
    )
    responder_projeto = ResponderProjeto(
        llm=router.select(complexity="high"),
        vault_repo=vault,
    )
    atualizar_memoria = AtualizarMemoria(vault_repo=vault)

    # FB-M4 C1: framework integration
    skills_reg = SkillsRegistry(config.skills_dir)
    mcp_reg = MCPRegistry()
    mcp_reg.register(
        ConexaoMCP(
            nome="postiz",
            tipo="rest-api",
            endpoint="https://api.postiz.com/public/v1",
            category="automation",
        )
    )
    rag_reg = RAGRegistry()
    registry = AgentRegistry(config.agents_dir)

    framework_deps = FrameworkDeps(
        vault=vault,
        llm=router,
        skills_reg=skills_reg,
        mcp_reg=mcp_reg,
        rag_reg=rag_reg,
        tracker=tracker,
        logger=_logger,
        registry=registry,
    )
    registry.bind_builder(lambda m: build_agent(m, framework_deps))

    # I5: early warning sobre cross-refs faltando nos manifests descobertos
    for manifest in registry.list_manifests():
        for erro in validate_manifest_resources(manifest, framework_deps):
            _logger.warning("Manifest %s: %s", manifest.nome, erro)

    quality_reviewer = QualityReviewer(
        llm=router,
        vault=vault,
        skills_reg=skills_reg,
        policy=ReviewPolicy(),
    )
    feedback_logger = FeedbackLogger(vault=vault)

    return Stella(
        vault=vault,
        gemma=gemma,
        anthropic=anthropic,
        router=router,
        prompt_builder=prompt_builder,
        capturar_ideia=capturar_ideia,
        responder_projeto=responder_projeto,
        atualizar_memoria=atualizar_memoria,
        usage_tracker=tracker,
        opus=opus,
        skills_reg=skills_reg,
        mcp_reg=mcp_reg,
        rag_reg=rag_reg,
        registry=registry,
        framework_deps=framework_deps,
        quality_reviewer=quality_reviewer,
        feedback_logger=feedback_logger,
    )
