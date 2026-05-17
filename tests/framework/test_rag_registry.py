import pytest

from stella.framework.errors import RAGNotFoundError
from stella.framework.resources.rag_registry import RAGRegistry


def test_rag_registry_vazio_no_inicio() -> None:
    reg = RAGRegistry()
    assert reg.list_all() == []


def test_rag_registry_register_e_get() -> None:
    reg = RAGRegistry()
    corpus_fake = object()  # cliente RAG concreto chega em milestone futuro
    reg.register("corpus-copies", corpus_fake)
    assert reg.get("corpus-copies") is corpus_fake


def test_rag_registry_get_levanta_rag_not_found() -> None:
    reg = RAGRegistry()
    with pytest.raises(RAGNotFoundError, match="corpus-x"):
        reg.get("corpus-x")


def test_rag_registry_list_all_devolve_nomes() -> None:
    reg = RAGRegistry()
    reg.register("a", object())
    reg.register("b", object())
    assert set(reg.list_all()) == {"a", "b"}
