from abc import ABC, abstractmethod
from dataclasses import dataclass


class LLMProviderError(Exception):
    """Erro genérico de provider de LLM (fronteira do adapter)."""


class LLMRateLimitError(LLMProviderError):
    """Quota/rate limit excedido."""


class LLMAuthenticationError(LLMProviderError):
    """Falha de autenticação (chave inválida ou expirada)."""


class LLMUnavailableError(LLMProviderError):
    """Serviço indisponível (timeout, 5xx, conexão recusada)."""


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    texto: str
    tokens_input: int = 0
    tokens_output: int = 0


class LLMProvider(ABC):
    """Contrato comum para todos os provedores de LLM.

    No M1, suporta `complete` (prompt único) e `chat` (lista de mensagens).
    Suporte a tools/function-calling é adicionado em milestones posteriores.
    """

    @abstractmethod
    def complete(self, prompt: str) -> LLMResponse: ...

    @abstractmethod
    def chat(self, messages: list[Message]) -> LLMResponse: ...
