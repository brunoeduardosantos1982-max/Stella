from stella.framework.manifest import CapacidadesExternas


def test_capacidades_externas_padrao_vazio() -> None:
    c = CapacidadesExternas()
    assert c.skills == []
    assert c.mcps == []
    assert c.rag is None


def test_capacidades_externas_com_listas() -> None:
    c = CapacidadesExternas(
        skills=["marketing-copy-pt-br", "ab-testing"],
        mcps=["brave-search"],
        rag="corpus-copies-anteriores",
    )
    assert "marketing-copy-pt-br" in c.skills
    assert "brave-search" in c.mcps
    assert c.rag == "corpus-copies-anteriores"
