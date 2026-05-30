"""Testes do Planejador — 3 pautas, mix 50/25/25, evita repetição via calendário."""

from stella.agents.agente_marca_mktmagneto.planejador import Pauta, Planejador
from stella.framework.testing.fakes import FakeLLM


def test_seleciona_tres_pautas():
    """LLM devolve 3 pautas no YAML; planejador parseia."""
    yaml_resposta = """
pautas:
  - pilar: 1
    titulo: "Despertar — chat vs build"
  - pilar: 2
    titulo: "5 prompts essenciais"
  - pilar: 4
    titulo: "Case Aspargus — números reais"
"""
    p = Planejador(llm=FakeLLM(responses=[yaml_resposta]))
    pautas = p.planejar(
        pilares_briefing=[1, 2, 3, 4],
        digest=[{"titulo": "novidade X"}],
        calendario_atual=[],
    )
    assert len(pautas) == 3
    assert isinstance(pautas[0], Pauta)
    pilares = sorted(pa.pilar for pa in pautas)
    assert pilares == [1, 2, 4]
    titulos = [pa.titulo for pa in pautas]
    assert "Despertar — chat vs build" in titulos


def test_evita_repetir_pauta_ja_no_calendario():
    """O prompt mandado ao LLM contém os títulos do calendário (para o LLM evitar)."""
    yaml_resposta = """
pautas:
  - pilar: 1
    titulo: "Nova"
"""
    llm = FakeLLM(responses=[yaml_resposta])
    p = Planejador(llm=llm)
    p.planejar(
        pilares_briefing=[1, 2, 3, 4],
        digest=[],
        calendario_atual=[
            {"titulo": "Despertar — chat vs build", "pilar": 1, "status": "publicado"},
        ],
    )
    assert "Despertar — chat vs build" in llm.calls[0]


def test_resposta_invalida_devolve_lista_vazia():
    """Se o LLM devolver texto não-YAML, planejador degrada sem quebrar."""
    p = Planejador(llm=FakeLLM(responses=["isso não é YAML válido :::: garbage"]))
    pautas = p.planejar(
        pilares_briefing=[1, 2, 3, 4],
        digest=[],
        calendario_atual=[],
    )
    assert pautas == []


def test_corta_em_tres_se_llm_devolver_mais():
    """Robustez: limita a 3 mesmo se o LLM mandar 5."""
    yaml_resposta = """
pautas:
  - {pilar: 1, titulo: "A"}
  - {pilar: 2, titulo: "B"}
  - {pilar: 3, titulo: "C"}
  - {pilar: 4, titulo: "D"}
  - {pilar: 1, titulo: "E"}
"""
    p = Planejador(llm=FakeLLM(responses=[yaml_resposta]))
    pautas = p.planejar(pilares_briefing=[1, 2, 3, 4], digest=[], calendario_atual=[])
    assert len(pautas) == 3


def test_prompt_inclui_mix_e_pilares():
    """O prompt enviado ao LLM deve mencionar o mix 50/25/25 e os pilares disponíveis."""
    yaml_resposta = "pautas: []\n"
    llm = FakeLLM(responses=[yaml_resposta])
    p = Planejador(llm=llm)
    p.planejar(pilares_briefing=[1, 2, 3, 4], digest=[], calendario_atual=[])
    prompt = llm.calls[0]
    assert "50" in prompt and "25" in prompt
    assert "1" in prompt and "2" in prompt and "3" in prompt and "4" in prompt


def test_prompt_ancora_no_briefing_e_descarta_fora_do_nicho():
    """O prompt deve injetar o briefing da marca (nicho + pilares) e instruir o LLM
    a descartar tendências do digest fora do nicho. Sem isso, o planner gera pautas
    fora do nicho (ex.: decoração/Japandi) a partir de um digest contaminado."""
    yaml_resposta = "pautas: []\n"
    llm = FakeLLM(responses=[yaml_resposta])
    p = Planejador(llm=llm)
    briefing = (
        "Missão: autoridade brasileira em IA aplicada a marketing e vendas. "
        "Pilar 1 Despertar; Pilar 2 Ferramentas & Prompts; Pilar 3 Agentes & Automação."
    )
    p.planejar(
        pilares_briefing=[1, 2, 3, 4],
        digest=[{"titulo": "Tendência Japandi na decoração 2026"}],
        calendario_atual=[],
        briefing=briefing,
    )
    prompt = llm.calls[0]
    # briefing injetado (LLM passa a conhecer o nicho e o que cada pilar significa)
    assert "IA aplicada a marketing e vendas" in prompt
    # instrução explícita de descartar o que está fora do nicho
    assert "nicho" in prompt.lower()
    assert "descart" in prompt.lower() or "ignore" in prompt.lower() or "fora do" in prompt.lower()
