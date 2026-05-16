from dataclasses import dataclass

from stella.adapters.llm.anthropic_provider import AnthropicProvider
from stella.adapters.llm.gemma_nvidia import GemmaNvidiaProvider
from stella.adapters.llm.router import LLMRouter
from stella.adapters.vault.obsidian_vault import ObsidianVaultRepository
from stella.infra.config import StellaConfig
from stella.infra.usage_tracker import UsageTracker
from stella.prompts.prompt_builder import PromptBuilder
from stella.usecases.atualizar_memoria import AtualizarMemoria
from stella.usecases.capturar_ideia import CapturarIdeia
from stella.usecases.responder_projeto import ResponderProjeto


@dataclass
class Stella:
    """Container principal — todos os componentes da Stella prontos para uso."""

    vault: ObsidianVaultRepository
    gemma: GemmaNvidiaProvider
    anthropic: AnthropicProvider
    router: LLMRouter
    prompt_builder: PromptBuilder
    capturar_ideia: CapturarIdeia
    responder_projeto: ResponderProjeto
    atualizar_memoria: AtualizarMemoria
    usage_tracker: UsageTracker


def build_stella(config: StellaConfig) -> Stella:
    """Monta toda a árvore de dependências da Stella a partir do config."""
    vault = ObsidianVaultRepository(vault_root=config.vault_path)
    tracker = UsageTracker()  # default ~/.stella/usage/

    gemma = GemmaNvidiaProvider(
        api_key=config.nvidia_api_key.get_secret_value(),
        tracker=tracker,
    )
    anthropic = AnthropicProvider(
        api_key=config.anthropic_api_key.get_secret_value(),
        tracker=tracker,
    )
    router = LLMRouter(
        gemma=gemma,
        anthropic=anthropic,
        default=config.modelo_padrao.value,
    )
    prompt_builder = PromptBuilder()

    # Roteamento de modelos para os usecases:
    # - CapturarIdeia: parse simples → Gemma (default low complexity)
    # - ResponderProjeto: contexto pode ser grande → Sonnet (high complexity)
    capturar_ideia = CapturarIdeia(
        llm=router.select(complexity="low"),
        vault_repo=vault,
    )
    responder_projeto = ResponderProjeto(
        llm=router.select(complexity="high"),
        vault_repo=vault,
    )
    atualizar_memoria = AtualizarMemoria(vault_repo=vault)

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
    )
