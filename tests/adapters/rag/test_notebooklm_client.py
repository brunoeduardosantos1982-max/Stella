"""Testes do NotebookLMRAGClient - subprocess mockado (sem CLI real)."""

import json
import subprocess
from typing import Any

import pytest

from stella.adapters.rag.notebooklm_client import NotebookLMError, NotebookLMRAGClient


class _Proc:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_auth_check_true_quando_exit_0(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Proc(returncode=0))
    client = NotebookLMRAGClient(notebook_id="nb_1")
    assert client.auth_check() is True


def test_auth_check_false_quando_exit_nao_zero(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Proc(returncode=1))
    client = NotebookLMRAGClient(notebook_id="nb_1")
    assert client.auth_check() is False


def test_auth_check_false_quando_binario_ausente(monkeypatch):
    def _raise(*a: Any, **k: Any):
        raise FileNotFoundError("notebooklm not found")

    monkeypatch.setattr(subprocess, "run", _raise)
    client = NotebookLMRAGClient(notebook_id="nb_1")
    assert client.auth_check() is False


def test_search_parseia_json_em_doc(monkeypatch):
    payload = json.dumps({"answer": "Hooks de curiosidade funcionam.", "citations": [{"n": 1}]})
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Proc(returncode=0, stdout=payload))
    client = NotebookLMRAGClient(notebook_id="nb_1")

    docs = client.search("hooks que engajam")

    assert len(docs) == 1
    assert "curiosidade" in docs[0]["texto"]
    assert docs[0]["citacoes"] == [{"n": 1}]


def test_search_passa_notebook_e_json_no_comando(monkeypatch):
    chamadas = {}

    def _capture(cmd, **k):
        chamadas["cmd"] = cmd
        return _Proc(returncode=0, stdout=json.dumps({"answer": "ok"}))

    monkeypatch.setattr(subprocess, "run", _capture)
    NotebookLMRAGClient(notebook_id="nb_xyz").search("pergunta")

    assert "ask" in chamadas["cmd"]
    assert "--notebook" in chamadas["cmd"] and "nb_xyz" in chamadas["cmd"]
    assert "--json" in chamadas["cmd"]


def test_subprocess_decodifica_utf8_no_windows(monkeypatch):
    """Regressão: no Windows `text=True` sem `encoding` decodifica com cp1252,
    a thread de leitura morre em bytes UTF-8 (acentos) e `stdout` vira None →
    json.loads(None). Ambas as chamadas devem fixar encoding=utf-8."""
    kwargs: dict[str, Any] = {}

    def _capture(cmd, **k):
        kwargs.clear()
        kwargs.update(k)
        return _Proc(returncode=0, stdout=json.dumps({"answer": "ção"}))

    monkeypatch.setattr(subprocess, "run", _capture)
    client = NotebookLMRAGClient(notebook_id="nb_1")

    client.search("pergunta com acentuação")
    assert kwargs.get("encoding") == "utf-8"

    client.auth_check()
    assert kwargs.get("encoding") == "utf-8"


def test_search_levanta_em_exit_nao_zero(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Proc(returncode=1, stderr="boom"))
    with pytest.raises(NotebookLMError):
        NotebookLMRAGClient(notebook_id="nb_1").search("x")


def test_search_vazio_quando_sem_resposta(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: _Proc(returncode=0, stdout=json.dumps({})),
    )
    assert NotebookLMRAGClient(notebook_id="nb_1").search("x") == []


def _fake_run_multi(respostas: dict[str, _Proc]):
    """Roteia subprocess.run: `list` devolve os notebooks, `ask` responde por id."""
    notebooks = {"notebooks": [{"id": nb} for nb in respostas]}

    def _run(cmd, **k):
        if "list" in cmd:
            return _Proc(returncode=0, stdout=json.dumps(notebooks))
        nb = cmd[cmd.index("--notebook") + 1]
        return respostas[nb]

    return _run


def test_search_sem_notebook_id_consulta_todos(monkeypatch):
    respostas = {
        "nb_a": _Proc(returncode=0, stdout=json.dumps({"answer": "resposta A"})),
        "nb_b": _Proc(returncode=0, stdout=json.dumps({"answer": "resposta B"})),
    }
    monkeypatch.setattr(subprocess, "run", _fake_run_multi(respostas))

    docs = NotebookLMRAGClient().search("pergunta")

    assert {d["notebook"] for d in docs} == {"nb_a", "nb_b"}
    assert {d["texto"] for d in docs} == {"resposta A", "resposta B"}


def test_search_todos_tolera_falha_parcial(monkeypatch):
    respostas = {
        "nb_a": _Proc(returncode=1, stderr="boom"),
        "nb_b": _Proc(returncode=0, stdout=json.dumps({"answer": "sobreviveu"})),
    }
    monkeypatch.setattr(subprocess, "run", _fake_run_multi(respostas))

    docs = NotebookLMRAGClient().search("pergunta")

    assert len(docs) == 1
    assert docs[0]["texto"] == "sobreviveu"


def test_search_todos_levanta_quando_todos_falham(monkeypatch):
    respostas = {
        "nb_a": _Proc(returncode=1, stderr="boom a"),
        "nb_b": _Proc(returncode=1, stderr="boom b"),
    }
    monkeypatch.setattr(subprocess, "run", _fake_run_multi(respostas))

    with pytest.raises(NotebookLMError):
        NotebookLMRAGClient().search("pergunta")


def test_search_todos_vazio_quando_conta_sem_notebooks(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run_multi({}))
    assert NotebookLMRAGClient().search("pergunta") == []
