"""Testa que build_stella registra Brave Search MCP em category: research."""

from pathlib import Path

from pydantic import SecretStr

from stella.app import build_stella
from stella.infra.config import StellaConfig


def _make_test_config(
    tmp_path: Path,
    *,
    brave: str = "brave-fake-key",
    perplexity: str = "",
) -> StellaConfig:
    """StellaConfig mínimo para testes — chaves fakes, vault em tmp."""
    return StellaConfig(
        nvidia_api_key=SecretStr("fake-nvidia"),
        anthropic_api_key=SecretStr("fake-anthropic"),
        vault_path=tmp_path,
        brave_api_key=SecretStr(brave),
        perplexity_api_key=SecretStr(perplexity),
    )


def test_brave_registrado_em_research(tmp_path):
    """Brave Search deve ser registrada em category: research."""
    stella = build_stella(_make_test_config(tmp_path))
    research = stella.mcp_reg.list_by_category("research")
    nomes = [m.nome for m in research]
    assert "brave-search" in nomes


def test_brave_nao_registra_sem_api_key(tmp_path):
    """Sem brave_api_key, MCP não é registrada — evita ConexaoMCP inválida."""
    stella = build_stella(_make_test_config(tmp_path, brave=""))
    research = stella.mcp_reg.list_by_category("research")
    nomes = [m.nome for m in research]
    assert "brave-search" not in nomes


def test_perplexity_registrado_em_research(tmp_path):
    """Perplexity deve ser registrada em category: research quando api_key presente."""
    stella = build_stella(_make_test_config(tmp_path, perplexity="perplexity-fake-key"))
    research = stella.mcp_reg.list_by_category("research")
    nomes = [m.nome for m in research]
    assert "perplexity" in nomes


def test_perplexity_nao_registra_sem_api_key(tmp_path):
    """Sem perplexity_api_key, MCP não é registrada."""
    stella = build_stella(_make_test_config(tmp_path, brave="brave-fake", perplexity=""))
    research = stella.mcp_reg.list_by_category("research")
    nomes = [m.nome for m in research]
    assert "perplexity" not in nomes


def test_cascata_com_brave_e_perplexity(tmp_path):
    """Com ambas as chaves presentes, ambas são registradas em research; Brave é primária."""
    stella = build_stella(
        _make_test_config(tmp_path, brave="brave-fake", perplexity="perplexity-fake")
    )
    research = stella.mcp_reg.list_by_category("research")
    nomes = [m.nome for m in research]
    assert "brave-search" in nomes
    assert "perplexity" in nomes
    # Brave deve vir primeiro (primário da cascata)
    assert nomes.index("brave-search") < nomes.index("perplexity")
