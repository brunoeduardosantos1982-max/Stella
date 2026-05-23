"""Testes do Pesquisador — cascata Brave → Perplexity → ... → digest vazio."""

from typing import Any

from stella.agents.agente_marca_mktmagneto.pesquisador import Pesquisador
from stella.framework.testing.fakes import FakeMCP


class _MCPFalhante(FakeMCP):
    """Variante do FakeMCP que sempre levanta na invoke()."""

    def invoke(self, chave: str) -> list[dict[str, Any]]:
        self.calls.append(chave)
        raise ConnectionError(f"{self.nome} offline")


def _mcp_ok(nome: str, category: str = "research") -> FakeMCP:
    return FakeMCP(
        nome=nome,
        category=category,
        resultados={
            "pilar 1 tendências 2026": [{"titulo": f"{nome}-r1", "snippet": "x"}],
            "pilar 2 tendências 2026": [{"titulo": f"{nome}-r2", "snippet": "y"}],
        },
    )


def test_brave_responde_perplexity_nao_eh_chamado():
    brave = _mcp_ok("brave-search")
    perplexity = _mcp_ok("perplexity")
    p = Pesquisador(research_mcps=[brave, perplexity])
    digest = p.pesquisar(pilares=["pilar 1", "pilar 2"])
    assert digest, "deveria voltar com resultados"
    assert brave.calls, "brave deveria ter sido chamado"
    assert not perplexity.calls, "perplexity NÃO deveria ter sido chamado"


def test_brave_falha_cai_para_perplexity():
    brave = _MCPFalhante(nome="brave-search", category="research")
    perplexity = _mcp_ok("perplexity")
    p = Pesquisador(research_mcps=[brave, perplexity])
    digest = p.pesquisar(pilares=["pilar 1"])
    assert digest, "deveria voltar com resultados via perplexity"
    assert perplexity.calls, "perplexity deveria ter sido chamado"


def test_todos_falham_devolve_digest_vazio():
    brave = _MCPFalhante(nome="brave-search", category="research")
    perplexity = _MCPFalhante(nome="perplexity", category="research")
    p = Pesquisador(research_mcps=[brave, perplexity])
    digest = p.pesquisar(pilares=["pilar 1"])
    assert digest == [], "todos falharam → digest vazio (não levanta)"


def test_sem_mcps_devolve_vazio():
    """Caso degenerado: nenhum MCP configurado."""
    p = Pesquisador(research_mcps=[])
    assert p.pesquisar(pilares=["x"]) == []


def test_queries_derivam_dos_pilares():
    brave = _mcp_ok("brave-search")
    p = Pesquisador(research_mcps=[brave])
    p.pesquisar(pilares=["pilar 1", "pilar 2"])
    # As 2 queries esperadas (uma por pilar)
    assert any("pilar 1" in c for c in brave.calls)
    assert any("pilar 2" in c for c in brave.calls)
