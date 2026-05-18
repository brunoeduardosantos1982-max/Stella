from stella.adapters.llm.base import LLMProvider
from stella.domain.enums import ModeloIA


class LLMRouter:
    """Escolhe o provedor de LLM conforme complexidade, skill/MCP ou força explícita.

    Regras (ordem de precedência):
    1. `force` explícito ("gemma" ou "sonnet") sempre vence.
    2. Se a tarefa usa skill ou MCP → Anthropic (Gemma não suporta MCP nativo).
    3. Se complexidade é "high" → Anthropic.
    4. Caso contrário → o provider `default`.

    FB-M4: slot opcional `opus` permite `with_minimum(OPUS)` retornar provider Opus
    real em vez de fallback para Sonnet.
    """

    def __init__(
        self,
        gemma: LLMProvider,
        anthropic: LLMProvider,
        opus: LLMProvider | None = None,
        default: str = "gemma",
    ):
        self._gemma = gemma
        self._anthropic = anthropic
        self._opus = opus
        self._default = default

    def select(
        self,
        complexity: str = "low",
        force: str | None = None,
        usa_skill_ou_mcp: bool = False,
    ) -> LLMProvider:
        if force == "sonnet":
            return self._anthropic
        if force == "gemma":
            return self._gemma
        if usa_skill_ou_mcp:
            return self._anthropic
        if complexity == "high":
            return self._anthropic
        return self._gemma if self._default == "gemma" else self._anthropic

    def with_minimum(self, modelo_minimo: ModeloIA) -> "LLMRouter":
        """Devolve um proxy que forca minimo de modelo nas chamadas.

        Se minimo == GEMMA: comportamento identico ao router base.
        Se minimo == SONNET: select() sempre devolve Anthropic.
        Se minimo == OPUS: usa slot `opus` se configurado, senao fallback
            para Anthropic (Sonnet) — compat com FB-M3.
        """
        return _LLMRouterComMinimo(self, modelo_minimo)


class _LLMRouterComMinimo(LLMRouter):
    """Proxy de LLMRouter que aplica floor de modelo."""

    def __init__(self, base: LLMRouter, minimo: ModeloIA) -> None:
        super().__init__(
            gemma=base._gemma,
            anthropic=base._anthropic,
            opus=base._opus,
            default=base._default,
        )
        self._minimo = minimo

    def select(
        self,
        complexity: str = "low",
        force: str | None = None,
        usa_skill_ou_mcp: bool = False,
    ) -> LLMProvider:
        if self._minimo == ModeloIA.OPUS and self._opus is not None:
            return self._opus
        if self._minimo in (ModeloIA.SONNET, ModeloIA.OPUS):
            return self._anthropic
        return super().select(complexity=complexity, force=force, usa_skill_ou_mcp=usa_skill_ou_mcp)
