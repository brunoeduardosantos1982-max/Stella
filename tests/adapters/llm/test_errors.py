"""Testes da hierarquia LLMProviderError e do encapsulamento de erros de SDK."""

from __future__ import annotations

import anthropic
import openai
import pytest

from stella.adapters.llm.anthropic_provider import AnthropicProvider
from stella.adapters.llm.base import (
    LLMAuthenticationError,
    LLMProviderError,
    LLMRateLimitError,
    LLMUnavailableError,
)
from stella.adapters.llm.gemma_nvidia import GemmaNvidiaProvider

# --- Stubs do SDK que levantam erros reais ---


class _FakeChat:
    def __init__(self, exc: Exception) -> None:
        self.completions = _FakeCompletions(exc)


class _FakeCompletions:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def create(self, **kwargs):  # noqa: ANN003
        raise self._exc


class _FakeOpenAIClient:
    def __init__(self, exc: Exception) -> None:
        self.chat = _FakeChat(exc)


class _FakeMessages:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def create(self, **kwargs):  # noqa: ANN003
        raise self._exc


class _FakeAnthropicClient:
    def __init__(self, exc: Exception) -> None:
        self.messages = _FakeMessages(exc)


# --- Hierarquia ---


def test_llm_subclasses_sao_de_llm_provider_error() -> None:
    assert issubclass(LLMAuthenticationError, LLMProviderError)
    assert issubclass(LLMRateLimitError, LLMProviderError)
    assert issubclass(LLMUnavailableError, LLMProviderError)


# --- Gemma: erros do SDK openai ---


def _fake_openai_rate_limit() -> openai.RateLimitError:
    # construtor moderno: RateLimitError(message, response=..., body=...)
    import httpx

    req = httpx.Request("POST", "https://x")
    resp = httpx.Response(429, request=req)
    return openai.RateLimitError("limite", response=resp, body=None)


def _fake_openai_auth() -> openai.AuthenticationError:
    import httpx

    req = httpx.Request("POST", "https://x")
    resp = httpx.Response(401, request=req)
    return openai.AuthenticationError("chave invalida", response=resp, body=None)


def _fake_openai_conn() -> openai.APIConnectionError:
    import httpx

    req = httpx.Request("POST", "https://x")
    return openai.APIConnectionError(request=req)


def test_gemma_converte_rate_limit() -> None:
    provider = GemmaNvidiaProvider(
        api_key="nv", client=_FakeOpenAIClient(_fake_openai_rate_limit())
    )
    with pytest.raises(LLMRateLimitError):
        provider.complete("oi")


def test_gemma_converte_authentication() -> None:
    provider = GemmaNvidiaProvider(api_key="nv", client=_FakeOpenAIClient(_fake_openai_auth()))
    with pytest.raises(LLMAuthenticationError):
        provider.complete("oi")


def test_gemma_converte_connection_em_unavailable() -> None:
    provider = GemmaNvidiaProvider(api_key="nv", client=_FakeOpenAIClient(_fake_openai_conn()))
    with pytest.raises(LLMUnavailableError):
        provider.complete("oi")


def test_gemma_converte_erro_generico_em_llm_provider_error() -> None:
    provider = GemmaNvidiaProvider(api_key="nv", client=_FakeOpenAIClient(RuntimeError("???")))
    with pytest.raises(LLMProviderError):
        provider.complete("oi")


# --- Anthropic: erros do SDK anthropic ---


def _fake_anthropic_rate_limit() -> anthropic.RateLimitError:
    import httpx

    req = httpx.Request("POST", "https://x")
    resp = httpx.Response(429, request=req)
    return anthropic.RateLimitError("limite", response=resp, body=None)


def _fake_anthropic_auth() -> anthropic.AuthenticationError:
    import httpx

    req = httpx.Request("POST", "https://x")
    resp = httpx.Response(401, request=req)
    return anthropic.AuthenticationError("chave invalida", response=resp, body=None)


def _fake_anthropic_conn() -> anthropic.APIConnectionError:
    import httpx

    req = httpx.Request("POST", "https://x")
    return anthropic.APIConnectionError(request=req)


def test_anthropic_converte_rate_limit() -> None:
    provider = AnthropicProvider(
        api_key="ant", client=_FakeAnthropicClient(_fake_anthropic_rate_limit())
    )
    with pytest.raises(LLMRateLimitError):
        provider.complete("oi")


def test_anthropic_converte_authentication() -> None:
    provider = AnthropicProvider(api_key="ant", client=_FakeAnthropicClient(_fake_anthropic_auth()))
    with pytest.raises(LLMAuthenticationError):
        provider.complete("oi")


def test_anthropic_converte_connection_em_unavailable() -> None:
    provider = AnthropicProvider(api_key="ant", client=_FakeAnthropicClient(_fake_anthropic_conn()))
    with pytest.raises(LLMUnavailableError):
        provider.complete("oi")


def test_anthropic_converte_erro_generico_em_llm_provider_error() -> None:
    provider = AnthropicProvider(api_key="ant", client=_FakeAnthropicClient(RuntimeError("???")))
    with pytest.raises(LLMProviderError):
        provider.complete("oi")
