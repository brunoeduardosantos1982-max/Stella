import pytest

from stella.framework.errors import RAGNotFoundError
from stella.framework.resources.rag_registry import RAGRegistry
from stella.framework.testing.fakes import FakeRAG


def test_rag_registry_vazio_no_inicio() -> None:
    reg = RAGRegistry()
    assert reg.list_all() == []


def test_rag_registry_register_e_get() -> None:
    reg = RAGRegistry()
    corpus = FakeRAG(docs=[{"titulo": "doc1"}])
    reg.register("corpus-copies", corpus)
    assert reg.get("corpus-copies") is corpus


def test_rag_registry_get_levanta_rag_not_found() -> None:
    reg = RAGRegistry()
    with pytest.raises(RAGNotFoundError, match="corpus-x"):
        reg.get("corpus-x")


def test_rag_registry_list_all_devolve_nomes() -> None:
    reg = RAGRegistry()
    reg.register("a", FakeRAG())
    reg.register("b", FakeRAG())
    assert set(reg.list_all()) == {"a", "b"}
