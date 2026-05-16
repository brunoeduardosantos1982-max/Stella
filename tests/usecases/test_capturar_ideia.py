import json
from datetime import datetime

import pytest

from stella.adapters.llm.base import LLMProvider, LLMResponse, Message
from stella.adapters.vault.obsidian_vault import ObsidianVaultRepository
from stella.usecases.base import EntradaInvalida
from stella.usecases.capturar_ideia import CapturarIdeia, EntradaCaptura


class _LLMFake(LLMProvider):
    def __init__(self, resposta_json: str) -> None:
        self._resposta = resposta_json

    def complete(self, prompt: str) -> LLMResponse:
        return LLMResponse(texto=self._resposta)

    def chat(self, messages: list[Message]) -> LLMResponse:
        return LLMResponse(texto=self._resposta)


def test_captura_cria_nota_em_inbox_com_frontmatter(vault_tmp) -> None:
    (vault_tmp / "A00 Inbox").mkdir(exist_ok=True)
    llm = _LLMFake(
        json.dumps({"titulo": "Revisar copy do Centro Viagens", "tags": ["copy", "marketing"]})
    )
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    usecase = CapturarIdeia(llm=llm, vault_repo=repo)

    resultado = usecase.execute(
        EntradaCaptura(
            texto="revisar copy do centro viagens",
            momento=datetime(2026, 5, 15, 14, 32),
        )
    )

    assert resultado.path.startswith("A00 Inbox/2026-05-15 14-32 —")
    nota = repo.read_note(resultado.path)
    assert nota.frontmatter["tipo"] == "ideia"
    assert nota.frontmatter["criado-em"] == "2026-05-15T14:32:00"
    assert "copy" in nota.frontmatter["tags"]
    assert "revisar copy do centro viagens" in nota.content


def test_entrada_vazia_levanta_erro(vault_tmp) -> None:
    llm = _LLMFake("{}")
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    usecase = CapturarIdeia(llm=llm, vault_repo=repo)
    with pytest.raises(EntradaInvalida, match="vazio"):
        usecase.execute(EntradaCaptura(texto="   ", momento=datetime(2026, 5, 15, 14, 32)))


def test_llm_devolve_json_invalido_usa_fallback(vault_tmp) -> None:
    (vault_tmp / "A00 Inbox").mkdir(exist_ok=True)
    llm = _LLMFake("isto não é JSON")
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    usecase = CapturarIdeia(llm=llm, vault_repo=repo)

    resultado = usecase.execute(
        EntradaCaptura(
            texto="ideia qualquer",
            momento=datetime(2026, 5, 15, 14, 32),
        )
    )

    nota = repo.read_note(resultado.path)
    # fallback: usa as primeiras palavras do texto como título e sem tags
    assert nota.frontmatter["tipo"] == "ideia"
    assert nota.frontmatter["tags"] == []
