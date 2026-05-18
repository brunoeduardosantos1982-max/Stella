from datetime import datetime, timedelta

import pytest

from stella.framework.testing.fakes import FakeVault


def test_fake_vault_vazio_por_default() -> None:
    v = FakeVault()
    assert v.list_notes_in_folder("qualquer") == []
    assert v.note_exists("x.md") is False


def test_fake_vault_aceita_notas_iniciais_via_construtor() -> None:
    v = FakeVault(
        notes={
            "A00 Inbox/ideia.md": ("conteudo", {"tipo": "ideia"}),
        }
    )
    assert v.note_exists("A00 Inbox/ideia.md") is True
    nota = v.read_note("A00 Inbox/ideia.md")
    assert nota.frontmatter == {"tipo": "ideia"}
    assert "conteudo" in nota.content


def test_fake_vault_write_note_armazena_e_le_de_volta() -> None:
    v = FakeVault()
    v.write_note("A00 Inbox/nova.md", "conteudo da nota", {"tipo": "ideia"})
    nota = v.read_note("A00 Inbox/nova.md")
    assert nota.content == "conteudo da nota"
    assert nota.frontmatter == {"tipo": "ideia"}


def test_fake_vault_read_note_inexistente_levanta_file_not_found() -> None:
    v = FakeVault()
    with pytest.raises(FileNotFoundError):
        v.read_note("nao-existe.md")


def test_fake_vault_list_notes_in_folder() -> None:
    v = FakeVault()
    v.write_note("A00 Inbox/a.md", "", {})
    v.write_note("A00 Inbox/b.md", "", {})
    v.write_note("B01 Projetos/c.md", "", {})
    listadas = v.list_notes_in_folder("A00 Inbox")
    assert set(listadas) == {"A00 Inbox/a.md", "A00 Inbox/b.md"}


def test_fake_vault_update_frontmatter() -> None:
    v = FakeVault()
    v.write_note("x.md", "corpo", {"tipo": "ideia", "status": "aberto"})
    v.update_frontmatter("x.md", {"status": "concluido", "novo": True})
    nota = v.read_note("x.md")
    assert nota.frontmatter["status"] == "concluido"
    assert nota.frontmatter["tipo"] == "ideia"
    assert nota.frontmatter["novo"] is True
    assert nota.content == "corpo"


def test_fake_vault_update_frontmatter_inexistente_levanta() -> None:
    v = FakeVault()
    with pytest.raises(FileNotFoundError):
        v.update_frontmatter("x.md", {"a": 1})


def test_fake_vault_scan_recursive_filtra_por_glob() -> None:
    v = FakeVault()
    v.write_note("A04/n1.md", "", {})
    v.write_note("A04/sub/n2.md", "", {})
    v.write_note("B01/n3.md", "", {})
    notas = v.scan_recursive("A04/**/*.md")
    paths = {n.path for n in notas}
    assert paths == {"A04/n1.md", "A04/sub/n2.md"}


def test_fake_vault_scan_recursive_filtra_por_since() -> None:
    """`since` filtra por timestamp interno do FakeVault."""
    v = FakeVault()
    momento_velho = datetime.now() - timedelta(hours=1)
    momento_novo = datetime.now()
    v.write_note("a.md", "", {}, _mtime=momento_velho)
    v.write_note("b.md", "", {}, _mtime=momento_novo)
    corte = datetime.now() - timedelta(minutes=30)
    notas = v.scan_recursive("*.md", since=corte)
    paths = {n.path for n in notas}
    assert paths == {"b.md"}


def test_fake_vault_scoped_aplica_isolamento() -> None:
    """FakeVault.scoped(pattern) usa ScopedVaultRepository real."""
    from stella.adapters.vault.scoped import ScopedVaultRepository

    v = FakeVault()
    v.write_note("marketing/copy.md", "x", {})
    scoped = v.scoped("marketing/**")
    assert isinstance(scoped, ScopedVaultRepository)
    assert scoped.note_exists("marketing/copy.md") is True
    with pytest.raises(PermissionError):
        scoped.note_exists("financeiro/x.md")


def test_fake_llm_devolve_respostas_pre_determinadas_em_ordem() -> None:
    from stella.framework.testing.fakes import FakeLLM

    llm = FakeLLM(responses=["primeira", "segunda", "terceira"])
    assert llm.complete("p1").texto == "primeira"
    assert llm.complete("p2").texto == "segunda"
    assert llm.complete("p3").texto == "terceira"


def test_fake_llm_sem_respostas_devolve_default() -> None:
    from stella.framework.testing.fakes import FakeLLM

    llm = FakeLLM()
    resp = llm.complete("oi")
    assert "fake" in resp.texto.lower()


def test_fake_llm_registra_chamadas() -> None:
    from stella.framework.testing.fakes import FakeLLM

    llm = FakeLLM(responses=["x"])
    llm.complete("primeiro prompt")
    assert len(llm.calls) == 1
    assert llm.calls[0] == "primeiro prompt"


def test_fake_llm_chat_usa_mesmo_pool_de_responses() -> None:
    from stella.adapters.llm.base import Message
    from stella.framework.testing.fakes import FakeLLM

    llm = FakeLLM(responses=["resposta chat"])
    resp = llm.chat([Message(role="user", content="oi")])
    assert resp.texto == "resposta chat"
    assert len(llm.calls) == 1


def test_fake_llm_responses_acabam_levanta_runtime_error() -> None:
    """Quando responses configuradas se esgotam, levanta erro em vez de default
    silencioso — protege testes de assumir comportamento errado."""
    from stella.framework.testing.fakes import FakeLLM

    llm = FakeLLM(responses=["unica"])
    llm.complete("p1")
    with pytest.raises(RuntimeError, match="esgotou"):
        llm.complete("p2")


def test_fake_mcp_e_conexao_mcp_com_category_e_resultados() -> None:
    from stella.framework.testing.fakes import FakeMCP

    mcp = FakeMCP(
        nome="brave-search-fake",
        category="research",
        resultados={"buscar:python": [{"titulo": "PEP 8"}]},
    )
    assert mcp.nome == "brave-search-fake"
    assert mcp.category == "research"
    assert mcp.invoke("buscar:python") == [{"titulo": "PEP 8"}]


def test_fake_mcp_invoke_chave_inexistente_devolve_lista_vazia() -> None:
    from stella.framework.testing.fakes import FakeMCP

    mcp = FakeMCP(nome="x", category=None)
    assert mcp.invoke("qualquer") == []


def test_fake_rag_busca_devolve_docs_pre_determinados() -> None:
    from stella.framework.testing.fakes import FakeRAG

    rag = FakeRAG(docs=[{"titulo": "doc1"}, {"titulo": "doc2"}])
    assert rag.search("qualquer query") == [{"titulo": "doc1"}, {"titulo": "doc2"}]


def test_fake_tracker_registra_chamadas() -> None:
    from datetime import datetime

    from stella.framework.testing.fakes import FakeTracker
    from stella.infra.usage_tracker import UsageRecord

    t = FakeTracker()
    t.record(
        UsageRecord(
            momento=datetime.now(),
            provider="nvidia",
            modelo="google/gemma-4-31b-it",
            tokens_input=100,
            tokens_output=50,
            custo_usd=0.001,
        )
    )
    t.record(
        UsageRecord(
            momento=datetime.now(),
            provider="anthropic",
            modelo="claude-sonnet-4-6",
            tokens_input=200,
            tokens_output=100,
            custo_usd=0.01,
        )
    )
    assert len(t.records) == 2
    assert t.records[0].provider == "nvidia"
    assert t.total_usd() == pytest.approx(0.011)


def test_fake_tracker_satisfaz_tracker_protocol() -> None:
    """FakeTracker e UsageTracker real ambos satisfazem TrackerProtocol."""
    from datetime import datetime

    from stella.framework.testing.fakes import FakeTracker
    from stella.framework.tracking import TrackerProtocol
    from stella.infra.usage_tracker import UsageRecord

    def aceita_tracker(t: TrackerProtocol) -> None:
        t.record(
            UsageRecord(
                momento=datetime.now(),
                provider="x",
                modelo="y",
                tokens_input=0,
                tokens_output=0,
                custo_usd=0.0,
            )
        )

    aceita_tracker(FakeTracker())


def test_fake_logger_captura_mensagens_por_nivel() -> None:
    from stella.framework.testing.fakes import FakeLogger

    log = FakeLogger()
    log.info("mensagem info")
    log.warning("mensagem warn")
    log.error("mensagem erro")
    assert log.records == [
        ("INFO", "mensagem info"),
        ("WARNING", "mensagem warn"),
        ("ERROR", "mensagem erro"),
    ]
