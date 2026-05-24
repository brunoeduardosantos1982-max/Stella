"""Testes do comando 'stella conteudo <marca>'."""

import pytest
from typer.testing import CliRunner

import stella.frontends.cli as cli_mod
from stella.framework.agent import AgentOutput

runner = CliRunner()


class _FakeAgente:
    def __init__(self, out: AgentOutput) -> None:
        self._out = out
        self.executado = False

    def execute(self, payload):
        self.executado = True
        return self._out


class _FakeRegistry:
    def __init__(self, agente):
        self._agente = agente

    def get(self, nome):
        assert nome == "agente_marca_mktmagneto"
        return self._agente


class _FakeStella:
    def __init__(self, agente):
        self.registry = _FakeRegistry(agente)


@pytest.fixture
def stub_build_stella(monkeypatch):
    """Substitui build_stella + StellaConfig para não precisar de .env real."""

    def _stub(out: AgentOutput):
        agente = _FakeAgente(out)
        stella = _FakeStella(agente)
        monkeypatch.setattr(cli_mod, "build_stella", lambda _cfg: stella)
        monkeypatch.setattr(cli_mod, "StellaConfig", lambda: object())
        return agente

    return _stub


def test_conteudo_sucesso(stub_build_stella):
    stub_build_stella(
        AgentOutput(
            resultado={"posts_em_rascunho": 3},
            sucesso=True,
            mensagens=["3 posts prontos."],
        )
    )
    result = runner.invoke(cli_mod.app, ["conteudo", "mktmagneto"])
    assert result.exit_code == 0
    assert "3" in result.stdout
    assert "rascunho" in result.stdout.lower() or "posts" in result.stdout.lower()


def test_conteudo_marca_desconhecida_falha(stub_build_stella):
    """Marca diferente de mktmagneto → exit code 2."""
    stub_build_stella(AgentOutput(resultado={}, sucesso=True, mensagens=[]))
    result = runner.invoke(cli_mod.app, ["conteudo", "centroviagens"])
    assert result.exit_code == 2
    assert "mktmagneto" in result.stdout.lower()


def test_conteudo_falha_no_agente(stub_build_stella):
    stub_build_stella(
        AgentOutput(
            resultado={},
            sucesso=False,
            mensagens=["Doc da marca ausente: spec"],
        )
    )
    result = runner.invoke(cli_mod.app, ["conteudo", "mktmagneto"])
    assert result.exit_code == 1
    assert "ausente" in result.stdout.lower() or "ruim" in result.stdout.lower()
