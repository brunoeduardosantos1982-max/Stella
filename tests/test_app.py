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
