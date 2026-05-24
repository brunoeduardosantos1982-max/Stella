"""Pipeline de texto end-to-end (sem visual/fila) — Task 13."""

from datetime import datetime, timedelta, timezone
from typing import Any, cast

from stella.adapters.llm.base import LLMProvider
from stella.adapters.llm.router import LLMRouter
from stella.agents.agente_marca_mktmagneto.agent import Agent
from stella.agents.agente_marca_mktmagneto.redator import PostTexto
from stella.framework.testing.fakes import FakeLLM, FakeMCP, FakeVault

_BRT = timezone(timedelta(hours=-3))
_AGORA_FIXO = datetime(2026, 5, 25, 12, 0, tzinfo=_BRT)  # segunda 25/05/2026

_BASE = "C04 Claude Obsidian/projetos e specs/mktmagneto.ia/"


def _vault_com_docs() -> FakeVault:
    return FakeVault(
        {
            f"{_BASE}mktmagneto.ia — 01 Spec.md": ("# Spec\n\nposicionamento", {}),
            f"{_BASE}mktmagneto.ia — 03 Briefing do Agente de Conteúdo.md": (
                "# Briefing\n\nvoz direta",
                {},
            ),
            f"{_BASE}mktmagneto.ia — 04 Kit de Identidade Visual.md": ("# Kit\n\ncores", {}),
        }
    )


def _vault_pronto() -> FakeVault:
    """Vault com docs da marca + template visual."""
    vault = _vault_com_docs()
    vault.write_note(
        "C04 Claude Obsidian/outputs/mktmagneto-ia/templates/capa-carrossel.html",
        "<html>{{TITULO}}</html>",
        {},
    )
    return vault


_PLAN_YAML = """
pautas:
  - {pilar: 1, titulo: "A"}
  - {pilar: 2, titulo: "B"}
  - {pilar: 4, titulo: "C"}
"""

_REDATOR_YAML = """
legenda: "🔥 H\\n\\nctx\\n\\ncorpo\\n\\n👇 CTA"
hashtags: ["#h1", "#h2", "#h3", "#h4", "#h5", "#h6", "#h7", "#h8", "#h9", "#h10", "#h11", "#h12"]
slides: ["s1", "s2", "s3"]
"""


class _FakeRouter:
    """Stub mínimo de LLMRouter — devolve sempre o mesmo FakeLLM."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def select(self, complexity: str) -> LLMProvider:
        return self._llm


def test_pipeline_de_texto_gera_3_posts() -> None:
    """Pipeline texto: 4 módulos encadeados → 3 PostTexto no resultado."""
    vault = _vault_com_docs()
    vault.write_note(
        "C04 Claude Obsidian/outputs/mktmagneto-ia/templates/capa-carrossel.html",
        "<html>{{TITULO}}</html>",
        {},
    )
    # 1 planejador + 3 redator + 3 qa aprovados = 7 respostas
    qa_yaml = "veredicto: aprovado\nmotivo: ok"
    llm = FakeLLM(
        responses=[
            _PLAN_YAML,
            _REDATOR_YAML,
            qa_yaml,
            _REDATOR_YAML,
            qa_yaml,
            _REDATOR_YAML,
            qa_yaml,
        ]
    )
    brave: Any = FakeMCP(
        nome="tavily",
        category="research",
        resultados={
            "pilar 1 tendências 2026": [{"titulo": "x"}],
            "pilar 2 tendências 2026": [{"titulo": "y"}],
            "pilar 3 tendências 2026": [{"titulo": "z"}],
            "pilar 4 tendências 2026": [{"titulo": "w"}],
        },
    )

    agent = Agent(vault=vault, llm=cast(LLMRouter, _FakeRouter(llm)), mcps=[brave])
    agent._render = _FakeRender()
    agent._now = lambda: _AGORA_FIXO
    out = agent.execute({})

    assert out.sucesso is True
    posts = out.resultado["posts_textos"]
    assert len(posts) == 3
    assert all(isinstance(p, PostTexto) for p in posts)
    assert {p.pilar for p in posts} == {1, 2, 4}


def test_doc_da_marca_ausente_devolve_sucesso_false() -> None:
    """Sem briefing no vault, agente não roda."""
    vault_vazio = FakeVault({})
    llm = FakeLLM(responses=[])
    agent = Agent(vault=vault_vazio, llm=cast(LLMRouter, _FakeRouter(llm)), mcps=[])
    out = agent.execute({})
    assert out.sucesso is False
    assert any(
        "marca" in m.lower() or "spec" in m.lower() or "briefing" in m.lower()
        for m in out.mensagens
    )


def test_sem_vault_ou_llm_falha_graciosamente() -> None:
    """Sem deps essenciais injetadas, agente devolve sucesso=False."""
    agent = Agent()  # nada injetado
    out = agent.execute({})
    assert out.sucesso is False


# ===== Pipeline com visual (Task 17) — agora gera PNGs também =====


class _FakeRender:
    """Fake renderer para testes — simula Playwright sem lançar navegador real."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []

    def render_png(self, html: str, width: int, height: int) -> bytes:
        self.calls.append((width, height))
        return b"PNGFAKE-" + html[:10].encode("utf-8", errors="ignore")


def test_pipeline_com_visual_gera_3_imagens() -> None:
    """Pipeline completo (texto + visual): 3 PostTexto + 3 imagens (bytes)."""
    vault = _vault_com_docs()
    # Acrescentar template visual ao vault
    template_path = "C04 Claude Obsidian/outputs/mktmagneto-ia/templates/capa-carrossel.html"
    vault.write_note(template_path, "<html>{{TITULO}}</html>", {})

    # 1 planejador + 3 redator + 3 qa aprovados = 7 respostas
    qa_yaml = "veredicto: aprovado\nmotivo: ok"
    llm = FakeLLM(
        responses=[
            _PLAN_YAML,
            _REDATOR_YAML,
            qa_yaml,
            _REDATOR_YAML,
            qa_yaml,
            _REDATOR_YAML,
            qa_yaml,
        ]
    )
    brave: Any = FakeMCP(
        nome="tavily",
        category="research",
        resultados={
            "pilar 1 tendências 2026": [{"titulo": "x"}],
            "pilar 2 tendências 2026": [{"titulo": "y"}],
            "pilar 3 tendências 2026": [{"titulo": "z"}],
            "pilar 4 tendências 2026": [{"titulo": "w"}],
        },
    )

    agent = Agent(vault=vault, llm=cast(LLMRouter, _FakeRouter(llm)), mcps=[brave])
    agent._render = _FakeRender()  # inject fake render
    agent._now = lambda: _AGORA_FIXO

    out = agent.execute({})
    assert out.sucesso is True
    imagens = out.resultado["imagens"]
    assert isinstance(imagens, dict)
    assert len(imagens) == 3
    for png_bytes in imagens.values():
        assert png_bytes.startswith(b"PNGFAKE")


def test_falha_no_visual_de_um_post_nao_derruba_os_outros() -> None:
    """Se MontadorVisual falhar num post, os outros prosseguem."""
    vault = _vault_com_docs()
    template_path = "C04 Claude Obsidian/outputs/mktmagneto-ia/templates/capa-carrossel.html"
    vault.write_note(template_path, "<html>{{TITULO}}</html>", {})

    # 1 planejador + 3 redator + 3 qa aprovados = 7 respostas
    qa_yaml = "veredicto: aprovado\nmotivo: ok"
    llm = FakeLLM(
        responses=[
            _PLAN_YAML,
            _REDATOR_YAML,
            qa_yaml,
            _REDATOR_YAML,
            qa_yaml,
            _REDATOR_YAML,
            qa_yaml,
        ]
    )
    brave: Any = FakeMCP(
        nome="tavily",
        category="research",
        resultados={
            "pilar 1 tendências 2026": [{"titulo": "x"}],
            "pilar 2 tendências 2026": [{"titulo": "y"}],
            "pilar 3 tendências 2026": [{"titulo": "z"}],
            "pilar 4 tendências 2026": [{"titulo": "w"}],
        },
    )

    class _RenderQueFalhaNoSegundo:
        def __init__(self) -> None:
            self.count = 0

        def render_png(self, html: str, width: int, height: int) -> bytes:  # noqa: ARG002
            self.count += 1
            if self.count == 2:
                raise RuntimeError("playwright crashed")
            return b"PNGFAKE"

    agent = Agent(vault=vault, llm=cast(LLMRouter, _FakeRouter(llm)), mcps=[brave])
    agent._render = _RenderQueFalhaNoSegundo()
    agent._now = lambda: _AGORA_FIXO

    out = agent.execute({})
    imagens = out.resultado["imagens"]
    # 3 posts texto, 2 imagens (1 falhou) — sucesso pq tem ao menos 1 post
    assert len(imagens) == 2
    assert out.sucesso is True
    assert any("visual" in m.lower() or "playwright" in m.lower() for m in out.mensagens)


# ===== Pipeline FINAL (Task 20) — gera 3 notas .md + 3 PNGs na fila do publicador =====


def test_pipeline_final_escreve_3_notas_na_fila_e_atualiza_calendario() -> None:
    """Pipeline completo: 3 notas .md no formato do publicador + 3 PNGs + calendario.md atualizado."""
    vault = _vault_pronto()

    qa_yaml = "veredicto: aprovado\nmotivo: ok"
    # 1 plan + 3 redator + 3 qa = 7 respostas
    llm = FakeLLM(
        responses=[
            _PLAN_YAML,
            _REDATOR_YAML,
            qa_yaml,
            _REDATOR_YAML,
            qa_yaml,
            _REDATOR_YAML,
            qa_yaml,
        ]
    )
    brave = FakeMCP(
        nome="tavily",
        category="research",
        resultados={f"pilar {p} tendências 2026": [{"titulo": "x"}] for p in (1, 2, 3, 4)},
    )

    agent = Agent(vault=vault, llm=cast(LLMRouter, _FakeRouter(llm)), mcps=[brave])
    agent._render = _FakeRender()  # do test anterior
    agent._now = lambda: _AGORA_FIXO  # injetar relógio fixo p/ testes

    out = agent.execute({})

    assert out.sucesso is True
    assert out.resultado["posts_em_rascunho"] == 3

    # 3 notas .md na fila + 3 PNGs
    fila_notas = [
        p
        for p in vault._store
        if p.startswith("C04 Claude Obsidian/Stella-publicacao/fila/") and p.endswith(".md")
    ]
    assert len(fila_notas) == 3

    # Cada nota tem o frontmatter no formato do publicador
    for path in fila_notas:
        nota = vault.read_note(path)
        assert nota.frontmatter["marca"] == "mktmagneto"
        assert nota.frontmatter["status"] == "rascunho"
        assert nota.frontmatter["plataformas"] == ["instagram"]
        # imagem referenciada existe (PNG anexado)
        png_name = nota.frontmatter["imagem"]
        png_full = path.rsplit("/", 1)[0] + "/" + png_name
        assert vault.read_binary(png_full).startswith(b"PNGFAKE")

    # Calendário criado/atualizado
    cal_path = "C04 Claude Obsidian/outputs/mktmagneto-ia/calendario.md"
    assert vault.note_exists(cal_path)
    cal = vault.read_note(cal_path)
    assert "planejado" in cal.content.lower() or "pilar" in cal.content.lower()


def test_autoqa_refaz_e_aceita() -> None:
    """AutoQA reprova na 1ª, aprova na 2ª — implementação chama Redator de novo."""
    vault = _vault_pronto()

    refaz_yaml = "veredicto: refazer\nmotivo: hook fraco"
    ok_yaml = "veredicto: aprovado\nmotivo: ok"
    # Planejador + 3 posts. O 1º entra no ciclo refazer: redator 1x → qa refazer → redator 2x → qa aprovado.
    # Os outros 2: redator + qa aprovado direto.
    # Sequência: plan, R1, QA-refazer, R1b, QA-aprovado, R2, QA-aprovado, R3, QA-aprovado = 9
    llm = FakeLLM(
        responses=[
            _PLAN_YAML,
            _REDATOR_YAML,
            refaz_yaml,  # 1º post: refazer
            _REDATOR_YAML,
            ok_yaml,  # 1º post: ok na 2ª
            _REDATOR_YAML,
            ok_yaml,  # 2º post
            _REDATOR_YAML,
            ok_yaml,  # 3º post
        ]
    )
    brave = FakeMCP(
        nome="tavily",
        category="research",
        resultados={f"pilar {p} tendências 2026": [{"x": 1}] for p in (1, 2, 3, 4)},
    )

    agent = Agent(vault=vault, llm=cast(LLMRouter, _FakeRouter(llm)), mcps=[brave])
    agent._render = _FakeRender()
    agent._now = lambda: _AGORA_FIXO

    out = agent.execute({})
    assert out.sucesso is True
    assert out.resultado["posts_em_rascunho"] == 3
