"""Testes do CarregadorMarca — lê spec/briefing/kit da marca do vault."""

import pytest

from stella.agents.agente_marca_mktmagneto.carregador_marca import CarregadorMarca
from stella.framework.testing.fakes import FakeVault

_SPEC_PATH = "C04 Claude Obsidian/projetos e specs/mktmagneto.ia/mktmagneto.ia — 01 Spec.md"
_BRIEFING_PATH = (
    "C04 Claude Obsidian/projetos e specs/mktmagneto.ia/"
    "mktmagneto.ia — 03 Briefing do Agente de Conteúdo.md"
)
_KIT_PATH = (
    "C04 Claude Obsidian/projetos e specs/mktmagneto.ia/"
    "mktmagneto.ia — 04 Kit de Identidade Visual.md"
)


def _vault_com_docs() -> FakeVault:
    return FakeVault(
        {
            _SPEC_PATH: ("# Spec\n\nposicionamento", {}),
            _BRIEFING_PATH: ("# Briefing\n\nvoz", {}),
            _KIT_PATH: ("# Kit\n\ncores", {}),
        }
    )


def test_carrega_os_tres_docs():
    carregador = CarregadorMarca(vault=_vault_com_docs())
    pack = carregador.carregar()

    assert "spec" in pack and "Spec" in pack["spec"]
    assert "briefing" in pack and "Briefing" in pack["briefing"]
    assert "kit" in pack and "Kit" in pack["kit"]


def test_doc_ausente_levanta_erro_claro():
    vault = FakeVault({})  # nada
    carregador = CarregadorMarca(vault=vault)
    with pytest.raises(FileNotFoundError, match="spec"):
        carregador.carregar()


def test_pack_completo_quando_apenas_um_ausente():
    """Se faltar SÓ um dos 3, ainda assim deve levantar FileNotFoundError com o nome claro."""
    vault = FakeVault(
        {
            _SPEC_PATH: ("# Spec", {}),
            _BRIEFING_PATH: ("# Briefing", {}),
            # KIT ausente
        }
    )
    carregador = CarregadorMarca(vault=vault)
    with pytest.raises(FileNotFoundError, match="kit"):
        carregador.carregar()
