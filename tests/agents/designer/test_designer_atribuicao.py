def test_decisao_usa_atribuicao_foto_hero() -> None:
    from stella.agents.designer.agent import Agent
    from stella.framework.testing.fakes import FakeLLM

    ag = Agent.__new__(Agent)
    ag._llm = FakeLLM(responses=["rota: tipografico\n"])  # type: ignore[attr-defined]
    d = ag._decidir_template(
        knowledge_pack={},
        pauta={"tipo": "carrossel", "titulo": "5 mitos"},
        copy={"legenda": "x"},
        fotos=[],
        atribuicao={"rota": "foto-hero", "tema": "mitos", "gancho_padrao_id": "mito-verdade"},
    )
    assert d["rota"] == "foto-hero"
    assert d["tema"] == "mitos"
