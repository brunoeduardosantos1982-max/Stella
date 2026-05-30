"""Testes dos novos métodos AutoQA — aprova_copy/feedback_copy/aprova_visual/feedback_visual."""

from stella.agents.agente_marca_mktmagneto.autoqa import AutoQA
from stella.framework.testing.fakes import FakeLLM

_COPY = {
    "legenda": "🔥 Hook\n\nContexto\n\n👇 Comenta AGENTE",
    "slides": ["Slide 1", "Slide 2", "Slide 3"],
    "hashtags": ["#ia"] * 12,
    "rationale": "PAS aplicado",
}

_KP = {
    "voz": "direto, sem hype",
    "cta_padrao": "Comenta AGENTE",
}

_DESIGNER_OUT = {
    "template_escolhido": "capa-carrossel",
    "rationale": "template certo para carrossel denso",
    "slides_renderizados": 3,
}


# ── aprova_copy ────────────────────────────────────────────────────────────────


def test_aprova_copy_retorna_true_quando_aprovado() -> None:
    qa = AutoQA(llm=FakeLLM(responses=["veredicto: aprovado\nmotivo: ok"]))
    assert qa.aprova_copy(copy=_COPY, knowledge_pack=_KP) is True


def test_aprova_copy_retorna_false_quando_refazer() -> None:
    qa = AutoQA(llm=FakeLLM(responses=["veredicto: refazer\nmotivo: legenda muito longa"]))
    assert qa.aprova_copy(copy=_COPY, knowledge_pack=_KP) is False


def test_aprova_copy_prompt_inclui_legenda_e_voz() -> None:
    llm = FakeLLM(responses=["veredicto: aprovado\nmotivo: ok"])
    qa = AutoQA(llm=llm)
    qa.aprova_copy(copy=_COPY, knowledge_pack=_KP)
    assert "Hook" in llm.calls[0]
    assert "direto" in llm.calls[0]


# ── feedback_copy (cache) ──────────────────────────────────────────────────────


def test_feedback_copy_reusa_cache_sem_segunda_chamada_llm() -> None:
    llm = FakeLLM(responses=["veredicto: refazer\nmotivo: legenda muito longa"])
    qa = AutoQA(llm=llm)
    qa.aprova_copy(copy=_COPY, knowledge_pack=_KP)
    feedback = qa.feedback_copy(copy=_COPY, knowledge_pack=_KP)
    assert "longa" in feedback
    assert len(llm.calls) == 1  # só 1 chamada LLM total


def test_feedback_copy_sem_cache_faz_chamada_llm() -> None:
    qa = AutoQA(llm=FakeLLM(responses=["veredicto: refazer\nmotivo: sem CTA visível"]))
    feedback = qa.feedback_copy(copy=_COPY, knowledge_pack=_KP)
    assert "CTA" in feedback


def test_feedback_copy_aprovado_retorna_string_vazia() -> None:
    qa = AutoQA(llm=FakeLLM(responses=["veredicto: aprovado\nmotivo: ok"]))
    qa.aprova_copy(copy=_COPY, knowledge_pack=_KP)
    assert qa.feedback_copy(copy=_COPY, knowledge_pack=_KP) == ""


# ── aprova_visual ──────────────────────────────────────────────────────────────


def test_aprova_visual_retorna_true_quando_aprovado() -> None:
    qa = AutoQA(llm=FakeLLM(responses=["veredicto: aprovado\nmotivo: ok"]))
    assert qa.aprova_visual(copy=_COPY, designer_resultado=_DESIGNER_OUT) is True


def test_aprova_visual_retorna_false_quando_refazer() -> None:
    qa = AutoQA(llm=FakeLLM(responses=["veredicto: refazer\nmotivo: contraste insuficiente"]))
    assert qa.aprova_visual(copy=_COPY, designer_resultado=_DESIGNER_OUT) is False


def test_aprova_visual_prompt_inclui_template_e_legenda() -> None:
    llm = FakeLLM(responses=["veredicto: aprovado\nmotivo: ok"])
    qa = AutoQA(llm=llm)
    qa.aprova_visual(copy=_COPY, designer_resultado=_DESIGNER_OUT)
    assert "capa-carrossel" in llm.calls[0]
    assert "Hook" in llm.calls[0]


# ── feedback_visual (cache) ────────────────────────────────────────────────────


def test_feedback_visual_reusa_cache_sem_segunda_chamada_llm() -> None:
    llm = FakeLLM(responses=["veredicto: refazer\nmotivo: template errado para esse pilar"])
    qa = AutoQA(llm=llm)
    qa.aprova_visual(copy=_COPY, designer_resultado=_DESIGNER_OUT)
    feedback = qa.feedback_visual(copy=_COPY, designer_resultado=_DESIGNER_OUT)
    assert "template" in feedback
    assert len(llm.calls) == 1


def test_feedback_visual_sem_cache_faz_chamada_llm() -> None:
    qa = AutoQA(llm=FakeLLM(responses=["veredicto: refazer\nmotivo: slides insuficientes"]))
    feedback = qa.feedback_visual(copy=_COPY, designer_resultado=_DESIGNER_OUT)
    assert "slides" in feedback


def test_feedback_visual_aprovado_retorna_string_vazia() -> None:
    qa = AutoQA(llm=FakeLLM(responses=["veredicto: aprovado\nmotivo: ok"]))
    qa.aprova_visual(copy=_COPY, designer_resultado=_DESIGNER_OUT)
    assert qa.feedback_visual(copy=_COPY, designer_resultado=_DESIGNER_OUT) == ""


def test_prompt_copy_inclui_referencia_quando_presente():
    qa = AutoQA(llm=FakeLLM())
    prompt = qa._montar_prompt_copy(
        copy={"legenda": "L", "hashtags": []},
        knowledge_pack={"briefing": "B", "referencia": "PRINCIPIO: prova concreta"},
    )
    assert "prova concreta" in prompt
