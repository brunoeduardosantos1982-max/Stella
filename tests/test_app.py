from stella.adapters.llm.anthropic_provider import AnthropicProvider
from stella.adapters.llm.gemma_nvidia import GemmaNvidiaProvider
from stella.adapters.llm.router import LLMRouter
from stella.adapters.vault.obsidian_vault import ObsidianVaultRepository
from stella.app import Stella, build_stella
from stella.infra.config import StellaConfig
from stella.prompts.prompt_builder import PromptBuilder
from stella.usecases.atualizar_memoria import AtualizarMemoria
from stella.usecases.capturar_ideia import CapturarIdeia
from stella.usecases.responder_projeto import ResponderProjeto


def test_build_stella_monta_todos_os_componentes(monkeypatch, vault_tmp) -> None:
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "nv-teste")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "ant-teste")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(vault_tmp))

    cfg = StellaConfig()
    stella = build_stella(cfg)

    assert isinstance(stella, Stella)
    assert isinstance(stella.vault, ObsidianVaultRepository)
    assert isinstance(stella.router, LLMRouter)
    assert isinstance(stella.gemma, GemmaNvidiaProvider)
    assert isinstance(stella.anthropic, AnthropicProvider)
    assert isinstance(stella.capturar_ideia, CapturarIdeia)
    assert isinstance(stella.responder_projeto, ResponderProjeto)
    assert isinstance(stella.atualizar_memoria, AtualizarMemoria)
    assert isinstance(stella.prompt_builder, PromptBuilder)


def test_build_stella_tem_registry_e_quality_reviewer(monkeypatch, vault_tmp) -> None:
    """FB-M4 C1: Stella expoe registry, quality_reviewer, feedback_logger."""
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "fake")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(vault_tmp))

    from stella.framework import AgentRegistry, FeedbackLogger, QualityReviewer
    from stella.framework.builder import FrameworkDeps

    stella = build_stella(StellaConfig())
    assert isinstance(stella.registry, AgentRegistry)
    assert isinstance(stella.quality_reviewer, QualityReviewer)
    assert isinstance(stella.feedback_logger, FeedbackLogger)
    assert isinstance(stella.framework_deps, FrameworkDeps)


def test_build_stella_registry_tem_aspargus_descoberto(monkeypatch, vault_tmp) -> None:
    """FB-M2 deixou stella/agents/coord_ecommerce_aspargus/ — deve aparecer no scan."""
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "fake")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(vault_tmp))

    stella = build_stella(StellaConfig())
    assert "coord_ecommerce_aspargus" in stella.registry.list_nomes()


def test_build_stella_registry_bind_builder_funcionou(monkeypatch, vault_tmp) -> None:
    """registry.get('coord_ecommerce_aspargus') devolve HttpAgentClient sem RuntimeError."""
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "fake")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(vault_tmp))

    from stella.framework.client import HttpAgentClient

    stella = build_stella(StellaConfig())
    client = stella.registry.get("coord_ecommerce_aspargus")
    assert isinstance(client, HttpAgentClient)


def test_build_stella_opus_e_provider_anthropic_com_modelo_opus(monkeypatch, vault_tmp) -> None:
    """B6: Stella.opus expoe AnthropicProvider configurado com claude-opus-4-7."""
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "fake")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(vault_tmp))

    stella = build_stella(StellaConfig())
    assert isinstance(stella.opus, AnthropicProvider)
    assert stella.opus._modelo == "claude-opus-4-7"


def test_build_stella_registra_mcp_postiz(monkeypatch, vault_tmp) -> None:
    """Sub-projeto B: build_stella registra a ConexaoMCP 'postiz'."""
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "fake")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(vault_tmp))

    stella = build_stella(StellaConfig())
    postiz = stella.mcp_reg.get("postiz")
    assert postiz.nome == "postiz"
    assert "api.postiz.com" in postiz.endpoint
    assert postiz.category == "automation"
