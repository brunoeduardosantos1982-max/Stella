"""Integration tests do pipeline v2 — Time de Marketing completo.

Testa o coordenador + copywriter + designer + AutoQA + EscritorFila
wired together com Fakes, sem depender de LLM ou vault real.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, cast

from stella.adapters.llm.base import LLMProvider
from stella.adapters.llm.router import LLMRouter
from stella.adapters.postiz.fake import FakePostiz
from stella.agents.agente_marca_mktmagneto.agent import Agent as Coordenador
from stella.agents.agente_publicador.agent import Agent as Publicador
from stella.agents.copywriter.agent import Agent as Copywriter
from stella.agents.designer.agent import Agent as Designer
from stella.framework.testing.fakes import (
    FakeCopywriter,
    FakeDesigner,
    FakeLLM,
    FakeMCP,
    FakeRegistry,
    FakeVault,
)

_BRT = timezone(timedelta(hours=-3))
_AGORA_FIXO = datetime(2026, 5, 26, 12, 0, tzinfo=_BRT)  # terça → próximas datas: qua, sex, seg

_BASE = "C04 Claude Obsidian/projetos e specs/mktmagneto.ia/"
_TEMPLATE_PATH = "C04 Claude Obsidian/outputs/mktmagneto-ia/templates/capa-carrossel.html"

_PLAN_YAML = """
pautas:
  - {pilar: 1, titulo: "99% conversa 1% constrói"}
  - {pilar: 3, titulo: "Como criar agentes com Python"}
  - {pilar: 4, titulo: "Minha stack em 2026"}
"""

_COPY_YAML = """
legenda: "🔥 Hook forte\n\nContexto\n\n👇 Comenta AGENTE"
slides:
  - "Slide 1 — intro"
  - "Slide 2 — como"
  - "Slide 3 — resultado"
hashtags:
  - "#ia"
  - "#python"
  - "#agentes"
  - "#automacao"
  - "#marketing"
  - "#conteudo"
  - "#instagram"
  - "#creator"
  - "#tech"
  - "#ia2025"
  - "#build"
  - "#produtividade"
rationale: "PAS aplicado"
"""

_DESIGN_YAML = """
template_escolhido: capa-carrossel
rationale: "Template ideal para carrossel denso"
"""

_QA_OK = "veredicto: aprovado\nmotivo: ok"
_QA_REFAZER = "veredicto: refazer\nmotivo: legenda muito longa, encurtar"


class _FakeRouter:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def select(self, complexity: str) -> LLMProvider:
        return self._llm


def _vault() -> FakeVault:
    vault = FakeVault(
        {
            f"{_BASE}mktmagneto.ia — 01 Spec.md": ("# Spec\n\nposicionamento IA", {}),
            f"{_BASE}mktmagneto.ia — 03 Briefing do Agente de Conteúdo.md": (
                "voz: direto, sem hype\ncta_padrao: Comenta AGENTE",
                {},
            ),
            f"{_BASE}mktmagneto.ia — 04 Kit de Identidade Visual.md": (
                "paleta: ciano+oliva",
                {},
            ),
        }
    )
    vault.write_note(_TEMPLATE_PATH, "<html><body>{{TITULO}} {{SLIDE_1}}</body></html>", {})
    return vault


def _tavily() -> FakeMCP:
    return FakeMCP(
        nome="tavily",
        category="research",
        resultados={f"pilar {p} tendências 2026": [{"titulo": "tendência"}] for p in (1, 2, 3, 4)},
    )


def _wired_agent(
    coord_llm: FakeLLM,
    copy_llm: FakeLLM,
    design_llm: FakeLLM,
    vault: FakeVault | None = None,
) -> Coordenador:
    """Monta coordenador com especialistas reais (não Fakes) via Registry inline."""
    v = vault or _vault()
    copy_router = cast(LLMRouter, _FakeRouter(copy_llm))
    design_router = cast(LLMRouter, _FakeRouter(design_llm))

    class _InlineRegistry:
        def get(self, nome: str) -> Any:
            if nome == "copywriter":
                return Copywriter(llm=copy_router)
            if nome == "designer":
                return Designer(llm=design_router, vault=v)
            raise KeyError(f"agente desconhecido: {nome}")

    coord = Coordenador(
        vault=v,
        llm=cast(LLMRouter, _FakeRouter(coord_llm)),
        mcps=[_tavily()],
        registry=_InlineRegistry(),
    )
    coord._now = lambda: _AGORA_FIXO  # type: ignore[method-assign]
    return coord


# ── pipeline completo ─────────────────────────────────────────────────────────


def test_pipeline_completo_gera_3_rascunhos() -> None:
    """Coordenador → Copywriter → Designer → AutoQA → EscritorFila: 3 notas na fila."""
    # Coordenador LLM: plan(1) + 3×qa_copy(1) + 3×qa_visual(1) = 7
    coord_llm = FakeLLM(responses=[_PLAN_YAML, _QA_OK, _QA_OK, _QA_OK, _QA_OK, _QA_OK, _QA_OK])
    # Copywriter LLM: 3 chamadas (1 por pauta)
    copy_llm = FakeLLM(responses=[_COPY_YAML, _COPY_YAML, _COPY_YAML])
    # Designer LLM: 3 chamadas (1 por pauta)
    design_llm = FakeLLM(responses=[_DESIGN_YAML, _DESIGN_YAML, _DESIGN_YAML])

    vault = _vault()
    agent = _wired_agent(coord_llm, copy_llm, design_llm, vault=vault)
    out = agent.execute({})

    assert out.sucesso is True
    assert out.resultado["posts_em_rascunho"] == 3

    fila = [p for p in vault._store if "Stella-publicacao/fila/" in p and p.endswith(".md")]
    assert len(fila) == 3

    for path in fila:
        nota = vault.read_note(path)
        assert "design_spec" in nota.frontmatter
        assert nota.frontmatter["status"] == "pending_render"


def test_legenda_copywriter_chega_na_nota_da_fila() -> None:
    """A legenda gerada pelo copywriter aparece no corpo da nota .md gravada."""
    coord_llm = FakeLLM(responses=[_PLAN_YAML, _QA_OK, _QA_OK, _QA_OK, _QA_OK, _QA_OK, _QA_OK])
    copy_llm = FakeLLM(responses=[_COPY_YAML, _COPY_YAML, _COPY_YAML])
    design_llm = FakeLLM(responses=[_DESIGN_YAML, _DESIGN_YAML, _DESIGN_YAML])

    vault = _vault()
    agent = _wired_agent(coord_llm, copy_llm, design_llm, vault=vault)
    agent.execute({})

    fila = [p for p in vault._store if "Stella-publicacao/fila/" in p and p.endswith(".md")]
    for path in fila:
        nota = vault.read_note(path)
        assert "🔥" in nota.content


def test_qa_warn_only_nao_bloqueia_post() -> None:
    """QA reprova copy mas é warn-only: post ainda é gravado, erro fica em mensagens."""
    coord_llm = FakeLLM(
        responses=[
            _PLAN_YAML,
            _QA_REFAZER,  # post 1 copy t1 — reprovado
            _QA_REFAZER,  # post 1 copy t2 — ainda reprovado → aviso
            _QA_OK,  # post 1 visual
            _QA_OK,
            _QA_OK,  # post 2 copy + visual
            _QA_OK,
            _QA_OK,  # post 3 copy + visual
        ]
    )
    copy_llm = FakeLLM(responses=[_COPY_YAML, _COPY_YAML, _COPY_YAML, _COPY_YAML])
    design_llm = FakeLLM(responses=[_DESIGN_YAML, _DESIGN_YAML, _DESIGN_YAML])

    vault = _vault()
    agent = _wired_agent(coord_llm, copy_llm, design_llm, vault=vault)
    out = agent.execute({})

    # Todos os 3 posts são gravados mesmo com aviso
    assert out.resultado["posts_em_rascunho"] == 3
    # Aviso aparece em mensagens
    assert any("QA aviso" in m for m in out.mensagens)
    fila = sorted(p for p in vault._store if "Stella-publicacao/fila/" in p and p.endswith(".md"))
    nota_com_aviso = vault.read_note(fila[0])
    assert nota_com_aviso.frontmatter["status"] == "needs_review"
    assert "qa_warnings" in nota_com_aviso.frontmatter


def test_pautas_nos_metadados_do_resultado() -> None:
    """Resultado inclui pautas com pilar e titulo corretos."""
    coord_llm = FakeLLM(responses=[_PLAN_YAML, _QA_OK, _QA_OK, _QA_OK, _QA_OK, _QA_OK, _QA_OK])
    copy_llm = FakeLLM(responses=[_COPY_YAML, _COPY_YAML, _COPY_YAML])
    design_llm = FakeLLM(responses=[_DESIGN_YAML, _DESIGN_YAML, _DESIGN_YAML])

    agent = _wired_agent(coord_llm, copy_llm, design_llm)
    out = agent.execute({})

    pautas = out.resultado["pautas"]
    assert len(pautas) == 3
    pilares = {p.pilar for p in pautas}
    assert pilares == {1, 3, 4}


def test_calendario_atualizado_apos_pipeline() -> None:
    """Calendário .md é criado/atualizado com as 3 pautas programadas."""
    coord_llm = FakeLLM(responses=[_PLAN_YAML, _QA_OK, _QA_OK, _QA_OK, _QA_OK, _QA_OK, _QA_OK])
    copy_llm = FakeLLM(responses=[_COPY_YAML, _COPY_YAML, _COPY_YAML])
    design_llm = FakeLLM(responses=[_DESIGN_YAML, _DESIGN_YAML, _DESIGN_YAML])

    vault = _vault()
    agent = _wired_agent(coord_llm, copy_llm, design_llm, vault=vault)
    agent.execute({})

    cal_path = "C04 Claude Obsidian/outputs/mktmagneto-ia/calendario.md"
    assert vault.note_exists(cal_path)
    cal = vault.read_note(cal_path)
    assert "planejado" in cal.content.lower()
    assert "conversa" in cal.content.lower()  # titulo do pilar 1


def test_coordenador_passa_variedade_contexto_acumulando_rotas() -> None:
    coord_llm = FakeLLM(responses=[_PLAN_YAML, _QA_OK, _QA_OK, _QA_OK, _QA_OK, _QA_OK, _QA_OK])
    designer = FakeDesigner(
        outputs=[
            {
                "design_spec_path": "C04 Claude Obsidian/Stella-publicacao/pendentes/1.json",
                "rota": "foto-local",
            },
            {
                "design_spec_path": "C04 Claude Obsidian/Stella-publicacao/pendentes/2.json",
                "rota": "tipografico",
            },
            {
                "design_spec_path": "C04 Claude Obsidian/Stella-publicacao/pendentes/3.json",
                "rota": "foto-local",
            },
        ]
    )
    registry = FakeRegistry({"copywriter": FakeCopywriter(), "designer": designer})
    coord = Coordenador(
        vault=_vault(),
        llm=cast(LLMRouter, _FakeRouter(coord_llm)),
        mcps=[_tavily()],
        registry=registry,
    )
    coord._now = lambda: _AGORA_FIXO  # type: ignore[method-assign]

    out = coord.execute({})

    assert out.sucesso is True
    assert len(designer.payloads) == 3
    assert designer.payloads[0]["variedade_contexto"] == []
    assert "foto-local" in designer.payloads[1]["variedade_contexto"]
    assert designer.payloads[2]["variedade_contexto"] == ["foto-local", "tipografico"]


def test_pipeline_designspec_render_simulado_publicador_publica_carrossel() -> None:
    """E2E local: marketing gera fila, render simulado preenche imagens, publicador agenda."""
    coord_llm = FakeLLM(responses=[_PLAN_YAML, _QA_OK, _QA_OK, _QA_OK, _QA_OK, _QA_OK, _QA_OK])
    copy_llm = FakeLLM(responses=[_COPY_YAML, _COPY_YAML, _COPY_YAML])
    design_llm = FakeLLM(responses=[_DESIGN_YAML, _DESIGN_YAML, _DESIGN_YAML])

    vault = _vault()
    vault.write_note(
        "C04 Claude Obsidian/Stella-publicacao/marcas.md",
        "",
        {"marcas": {"mktmagneto": {"instagram": "canal-ig-1"}}},
    )
    coordenador = _wired_agent(coord_llm, copy_llm, design_llm, vault=vault)
    out = coordenador.execute({})
    assert out.sucesso is True

    fila = sorted(p for p in vault._store if "Stella-publicacao/fila/" in p and p.endswith(".md"))
    assert fila
    post_path = fila[0]
    post_id = post_path.rsplit("/", 1)[-1].removesuffix(".md")

    vault.write_binary(
        f"C04 Claude Obsidian/Stella-publicacao/fila/{post_id}/slide-00.png", b"PNG0"
    )
    vault.write_binary(
        f"C04 Claude Obsidian/Stella-publicacao/fila/{post_id}/slide-01.png", b"PNG1"
    )
    vault.update_frontmatter(
        post_path,
        {
            "status": "rascunho",
            "imagens": [f"{post_id}/slide-00.png", f"{post_id}/slide-01.png"],
        },
    )

    postiz = FakePostiz()
    pub = Publicador(vault=vault, postiz_client=postiz)
    publicado = pub.execute({"modo": "auto"})

    assert publicado.sucesso is True
    assert post_path in publicado.resultado["publicados"]
    assert postiz.uploads == [("slide-00.png", b"PNG0"), ("slide-01.png", b"PNG1")]
    assert len(postiz.agendamentos[0].midias) == 2
