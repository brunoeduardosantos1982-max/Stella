import pytest

from stella.adapters.llm.base import LLMProvider, LLMResponse, Message
from stella.adapters.vault.obsidian_vault import ObsidianVaultRepository
from stella.usecases.base import EntradaInvalida
from stella.usecases.responder_projeto import (
    EntradaPergunta,
    ResponderProjeto,
)


class _LLMFake(LLMProvider):
    def __init__(self, resposta: str = "resposta da stella") -> None:
        self.resposta = resposta
        self.ultimo_chat: list[Message] | None = None

    def complete(self, prompt: str) -> LLMResponse:
        return LLMResponse(texto=self.resposta)

    def chat(self, messages: list[Message]) -> LLMResponse:
        self.ultimo_chat = messages
        return LLMResponse(texto=self.resposta)


def _criar_projeto(vault_tmp, nome: str, conteudo: str) -> None:
    pasta = vault_tmp / "B01 Projetos"
    pasta.mkdir(exist_ok=True)
    (pasta / f"{nome}.md").write_text(
        f"---\ntipo: projeto\nstatus: ativo\n---\n\n{conteudo}\n",
        encoding="utf-8",
    )


def test_responde_pergunta_lendo_projeto_correto(vault_tmp) -> None:
    _criar_projeto(vault_tmp, "Centro Viagens", "Projeto de viagens. Próxima ação: revisar copy.")
    llm = _LLMFake("Resposta sobre Centro Viagens com [[Centro Viagens]] como fonte.")
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    usecase = ResponderProjeto(llm=llm, vault_repo=repo)

    resultado = usecase.execute(
        EntradaPergunta(
            pergunta="o que está aberto?",
            projeto="Centro Viagens",
        )
    )

    assert "Centro Viagens" in resultado.resposta
    # confirma que o conteudo do projeto entrou no contexto enviado ao LLM
    assert llm.ultimo_chat is not None
    contexto_enviado = " ".join(m.content for m in llm.ultimo_chat)
    assert "Projeto de viagens" in contexto_enviado
    assert "revisar copy" in contexto_enviado
    assert resultado.fontes == ["B01 Projetos/Centro Viagens.md"]


def test_projeto_inexistente_levanta_erro(vault_tmp) -> None:
    llm = _LLMFake()
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    usecase = ResponderProjeto(llm=llm, vault_repo=repo)
    with pytest.raises(EntradaInvalida, match="não encontrado"):
        usecase.execute(EntradaPergunta(pergunta="qualquer coisa", projeto="Projeto Inexistente"))


def test_pergunta_vazia_levanta_erro(vault_tmp) -> None:
    _criar_projeto(vault_tmp, "Centro Viagens", "x")
    llm = _LLMFake()
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    usecase = ResponderProjeto(llm=llm, vault_repo=repo)
    with pytest.raises(EntradaInvalida, match="vazia"):
        usecase.execute(EntradaPergunta(pergunta="  ", projeto="Centro Viagens"))
