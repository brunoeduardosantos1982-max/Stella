"""Testes do Redator — legenda padrão + slides + hashtags."""

from stella.agents.agente_marca_mktmagneto.planejador import Pauta
from stella.agents.agente_marca_mktmagneto.redator import PostTexto, Redator
from stella.framework.testing.fakes import FakeLLM

_RESPOSTA_OK = """
legenda: |
  🔥 Hook impactante aqui.

  Contexto em duas linhas para situar.
  Mais uma linha de contexto.

  Corpo: o "como" real, com passos concretos.
  → Ponto 1
  → Ponto 2

  👇 Comenta "AGENTE" que te mando no direct.
hashtags:
  - "#ia"
  - "#marketingdigital"
  - "#chatgpt"
  - "#agentesdeia"
  - "#empreendedorismo"
  - "#vendas"
  - "#automacao"
  - "#produtividade"
  - "#copywriting"
  - "#instagram"
  - "#brasil"
  - "#negociosdigitais"
slides:
  - "01 - Hook"
  - "02 - Problema"
  - "03 - Solução"
  - "04 - CTA"
"""


def test_gera_post_completo():
    r = Redator(llm=FakeLLM(responses=[_RESPOSTA_OK]))
    pauta = Pauta(pilar=1, titulo="Hook impactante aqui.")
    post = r.escrever(
        pauta=pauta,
        knowledge={"briefing": "voz: direta", "spec": "", "kit": ""},
    )
    assert isinstance(post, PostTexto)
    assert post.pilar == 1
    assert post.titulo == "Hook impactante aqui."
    assert "🔥" in post.legenda
    assert "👇" in post.legenda
    assert 12 <= len(post.hashtags) <= 15
    assert len(post.slides) >= 3


def test_prompt_inclui_briefing_e_pauta():
    llm = FakeLLM(responses=[_RESPOSTA_OK])
    r = Redator(llm=llm)
    pauta = Pauta(pilar=2, titulo="5 prompts essenciais")
    r.escrever(
        pauta=pauta,
        knowledge={"briefing": "VOZ_DA_MARCA_AQUI", "spec": "", "kit": ""},
    )
    prompt = llm.calls[0]
    assert "VOZ_DA_MARCA_AQUI" in prompt
    assert "5 prompts essenciais" in prompt
    assert "2" in prompt  # pilar


def test_resposta_invalida_devolve_post_vazio():
    """LLM resposta não-YAML: degrada sem quebrar."""
    r = Redator(llm=FakeLLM(responses=["garbage :::: not yaml"]))
    pauta = Pauta(pilar=1, titulo="x")
    post = r.escrever(pauta=pauta, knowledge={"briefing": "", "spec": "", "kit": ""})
    assert isinstance(post, PostTexto)
    assert post.legenda == ""
    assert post.hashtags == []
    assert post.slides == []


def test_yaml_sem_alguns_campos_devolve_defaults():
    """Robustez: faltando hashtags/slides, defaults vazios."""
    yaml_resp = """
legenda: "só legenda"
"""
    r = Redator(llm=FakeLLM(responses=[yaml_resp]))
    pauta = Pauta(pilar=1, titulo="x")
    post = r.escrever(pauta=pauta, knowledge={"briefing": "", "spec": "", "kit": ""})
    assert post.legenda == "só legenda"
    assert post.hashtags == []
    assert post.slides == []
