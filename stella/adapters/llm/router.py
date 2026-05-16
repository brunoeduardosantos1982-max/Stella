from stella.adapters.llm.base import LLMProvider


class LLMRouter:
    """Escolhe o provedor de LLM conforme complexidade, skill/MCP ou força explícita.

    Regras (ordem de precedência):
    1. `force` explícito ("gemma" ou "sonnet") sempre vence.
    2. Se a tarefa usa skill ou MCP → Anthropic (Gemma não suporta MCP nativo).
    3. Se complexidade é "high" → Anthropic.
    4. Caso contrário → o provider `default`.
    """

    def __init__(self, gemma: LLMProvider, anthropic: LLMProvider, default: str = "gemma"):
        self._gemma = gemma
        self._anthropic = anthropic
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
