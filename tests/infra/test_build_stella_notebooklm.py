"""build_stella registra o NotebookLMRAGClient no RAGRegistry."""

from stella.adapters.rag.notebooklm_client import NotebookLMRAGClient
from stella.app import build_stella
from stella.infra.config import StellaConfig


def _cfg(monkeypatch, tmp_path, notebook_id: str = "nb_test") -> StellaConfig:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "fake")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("STELLA_NOTEBOOKLM_NOTEBOOK_ID", notebook_id)
    return StellaConfig()


def test_build_stella_registra_notebooklm(monkeypatch, tmp_path):
    stella = build_stella(_cfg(monkeypatch, tmp_path, "nb_xyz"))
    client = stella.rag_reg.get("notebooklm")
    assert isinstance(client, NotebookLMRAGClient)
    assert client.notebook_id == "nb_xyz"
