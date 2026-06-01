from stella.agents.agente_marca_mktmagneto.autoqa import AutoQA
from stella.framework.testing.fakes import FakeLLM


def test_prompt_copy_tem_criterios_de_crescimento() -> None:
    qa = AutoQA(llm=FakeLLM())
    p = qa._montar_prompt_copy(
        copy={"legenda": "L", "hashtags": ["#x"]},
        knowledge_pack={"briefing": "B"},
    ).lower()
    assert "gancho" in p
    assert "especific" in p
    assert "1 cta" in p or "um cta" in p
    assert "salv" in p
    assert "generic" in p
