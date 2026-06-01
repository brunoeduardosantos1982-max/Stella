"""Pipeline end-to-end do coordenador agente_marca_mktmagneto.

v2: delega copy ao especialista `copywriter` e visual ao `designer`.
LLM só é chamado para: Planejador + AutoQA (aprova_copy + aprova_visual).
"""

from datetime import datetime, timedelta, timezone
from typing import Any, cast

from stella.adapters.llm.base import LLMProvider
from stella.adapters.llm.router import LLMRouter
from stella.agents.agente_marca_mktmagneto.agent import Agent
from stella.framework.agent import AgentOutput
from stella.framework.testing.fakes import (
    FakeCopywriter,
    FakeDesigner,
    FakeLLM,
    FakeMCP,
    FakeRegistry,
    FakeVault,
)

_BRT = timezone(timedelta(hours=-3))
_AGORA_FIXO = datetime(2026, 5, 25, 12, 0, tzinfo=_BRT)

_BASE = "C04 Claude Obsidian/projetos e specs/mktmagneto.ia/"

_PLAN_YAML = """
pautas:
  - {pilar: 1, titulo: "A"}
  - {pilar: 2, titulo: "B"}
  - {pilar: 4, titulo: "C"}
"""

_QA_OK = "veredicto: aprovado\nmotivo: ok"
_QA_REFAZER = "veredicto: refazer\nmotivo: hook fraco"
_BRIEFING_YAML = "angulo: a\ngancho_padrao_id: mito-verdade\ncta_unico: Comenta AGENTE\n"


def _coord_ok_responses() -> list[str]:
    return [
        _PLAN_YAML,
        _BRIEFING_YAML,
        _QA_OK,
        _QA_OK,
        _BRIEFING_YAML,
        _QA_OK,
        _QA_OK,
        _BRIEFING_YAML,
        _QA_OK,
        _QA_OK,
    ]


def _vault_pronto() -> FakeVault:
    vault = FakeVault(
        {
            f"{_BASE}mktmagneto.ia — 01 Spec.md": ("# Spec\n\nposicionamento", {}),
            f"{_BASE}mktmagneto.ia — 03 Briefing do Agente de Conteúdo.md": (
                "# Briefing\n\nvoz direta",
                {},
            ),
            f"{_BASE}mktmagneto.ia — 04 Kit de Identidade Visual.md": ("# Kit\n\ncores", {}),
        }
    )
    vault.write_note(
        "C04 Claude Obsidian/outputs/mktmagneto-ia/templates/capa-carrossel.html",
        "<html>{{TITULO}}</html>",
        {},
    )
    return vault


class _FakeRouter:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def select(self, complexity: str) -> LLMProvider:
        return self._llm


def _brave() -> FakeMCP:
    return FakeMCP(
        nome="tavily",
        category="research",
        resultados={f"pilar {p} tendências 2026": [{"titulo": "x"}] for p in (1, 2, 3, 4)},
    )


def _agent(llm: FakeLLM, vault: FakeVault | None = None, registry: Any = None) -> Agent:
    agent = Agent(
        vault=vault or _vault_pronto(),
        llm=cast(LLMRouter, _FakeRouter(llm)),
        mcps=[_brave()],
        registry=registry
        or FakeRegistry({"copywriter": FakeCopywriter(), "designer": FakeDesigner()}),
    )
    agent._now = lambda: _AGORA_FIXO  # type: ignore[method-assign]
    return agent


# ── testes de falha rápida ────────────────────────────────────────────────────


def test_doc_da_marca_ausente_devolve_sucesso_false() -> None:
    llm = FakeLLM(responses=[])
    registry = FakeRegistry({"copywriter": FakeCopywriter(), "designer": FakeDesigner()})
    agent = Agent(
        vault=FakeVault({}), llm=cast(LLMRouter, _FakeRouter(llm)), mcps=[], registry=registry
    )
    out = agent.execute({})
    assert out.sucesso is False
    assert any(
        "marca" in m.lower() or "spec" in m.lower() or "briefing" in m.lower()
        for m in out.mensagens
    )


def test_sem_vault_ou_llm_ou_registry_falha_graciosamente() -> None:
    out = Agent().execute({})
    assert out.sucesso is False


# ── pipeline completo ─────────────────────────────────────────────────────────


def test_pipeline_gera_3_rascunhos_na_fila() -> None:
    """Coordenador delega copy + visual e grava 3 notas .md na fila."""
    # plan(1) + 3×aprova_copy(1) + 3×aprova_visual(1) = 7
    llm = FakeLLM(responses=_coord_ok_responses())
    vault = _vault_pronto()
    agent = _agent(llm, vault=vault)
    out = agent.execute({})

    assert out.sucesso is True
    assert out.resultado["posts_em_rascunho"] == 3
    fila = [p for p in vault._store if "Stella-publicacao/fila/" in p and p.endswith(".md")]
    assert len(fila) == 3


def test_pipeline_grava_design_spec_no_frontmatter() -> None:
    llm = FakeLLM(responses=_coord_ok_responses())
    vault = _vault_pronto()
    agent = _agent(llm, vault=vault)
    agent.execute({})

    fila = [p for p in vault._store if "Stella-publicacao/fila/" in p and p.endswith(".md")]
    assert len(fila) == 3
    for path in fila:
        nota = vault.read_note(path)
        assert "design_spec" in nota.frontmatter
        assert nota.frontmatter["design_spec"] != ""


def test_pipeline_atualiza_calendario() -> None:
    llm = FakeLLM(responses=_coord_ok_responses())
    vault = _vault_pronto()
    agent = _agent(llm, vault=vault)
    agent.execute({})

    cal_path = "C04 Claude Obsidian/outputs/mktmagneto-ia/calendario.md"
    assert vault.note_exists(cal_path)
    cal = vault.read_note(cal_path)
    assert "planejado" in cal.content.lower()


def test_nota_da_fila_tem_frontmatter_correto() -> None:
    llm = FakeLLM(responses=_coord_ok_responses())
    vault = _vault_pronto()
    agent = _agent(llm, vault=vault)
    agent.execute({})

    fila = [p for p in vault._store if "Stella-publicacao/fila/" in p and p.endswith(".md")]
    for path in fila:
        nota = vault.read_note(path)
        assert nota.frontmatter["marca"] == "mktmagneto"
        assert nota.frontmatter["status"] == "pending_render"
        assert nota.frontmatter["plataformas"] == ["instagram"]


# ── QA copy: retry com feedback ───────────────────────────────────────────────


def test_autoqa_copy_refaz_e_aprova_na_segunda() -> None:
    """QA reprova copy na 1ª tentativa; coordenador reenvia com feedback → aprovado na 2ª."""
    # plan + qa_copy_refazer(post1-t1) + qa_copy_ok(post1-t2) + qa_visual_ok(post1)
    # + qa_copy_ok(post2) + qa_visual_ok(post2) + qa_copy_ok(post3) + qa_visual_ok(post3) = 8
    llm = FakeLLM(
        responses=[
            _PLAN_YAML,
            _BRIEFING_YAML,
            _QA_REFAZER,  # post 1 copy tentativa 1
            _QA_OK,  # post 1 copy tentativa 2
            _QA_OK,  # post 1 visual
            _BRIEFING_YAML,
            _QA_OK,  # post 2 copy
            _QA_OK,  # post 2 visual
            _BRIEFING_YAML,
            _QA_OK,  # post 3 copy
            _QA_OK,  # post 3 visual
        ]
    )
    copywriter = FakeCopywriter()
    agent = _agent(
        llm,
        registry=FakeRegistry({"copywriter": copywriter, "designer": FakeDesigner()}),
    )
    out = agent.execute({})
    assert out.sucesso is True
    assert out.resultado["posts_em_rascunho"] == 3
    # copywriter foi chamado 4 vezes: retry de post1 + posts 2 e 3
    assert len(copywriter.payloads) == 4
    # segundo payload tem feedback_anterior
    assert "feedback_anterior" in copywriter.payloads[1]


def test_designer_falha_num_post_nao_derruba_os_outros() -> None:
    """Se designer retorna sucesso=False, esse post é pulado mas os demais são gravados."""

    class _DesignerFalhaNaSegunda:
        call_count = 0

        def execute(self, payload: dict[str, Any]) -> AgentOutput:
            self.call_count += 1
            if self.call_count == 2:
                return AgentOutput(resultado={}, sucesso=False, mensagens=["designer crashed"])
            return AgentOutput(
                resultado={
                    "design_spec_path": "C04 Claude Obsidian/Stella-publicacao/pendentes/fake-spec.json",
                    "formato": "carrossel",
                    "template_capa": "capa-carrossel",
                    "slides_planejados": 3,
                }
            )

    # plan + 3×qa_copy + 2×qa_visual (post2 é pulado) = 6
    llm = FakeLLM(
        responses=[
            _PLAN_YAML,
            _BRIEFING_YAML,
            _QA_OK,
            _QA_OK,
            _BRIEFING_YAML,
            _QA_OK,
            _BRIEFING_YAML,
            _QA_OK,  # qa_copy posts 1, 2, 3
            _QA_OK,  # qa_visual posts 1 e 3 (post2 designer falhou)
        ]
    )
    vault = _vault_pronto()
    agent = _agent(
        llm,
        vault=vault,
        registry=FakeRegistry(
            {"copywriter": FakeCopywriter(), "designer": _DesignerFalhaNaSegunda()}
        ),
    )
    out = agent.execute({})

    assert out.resultado["posts_em_rascunho"] == 2
    assert any("designer falhou" in m for m in out.mensagens)
