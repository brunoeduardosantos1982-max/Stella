import json
from pathlib import Path

from stella.adapters.llm.router import LLMRouter
from stella.framework.agent import AgentOutput
from stella.framework.manifest import AgentManifest, CapacidadesExternas
from stella.framework.quality.policies import ReviewPolicy
from stella.framework.quality.reviewer import QualityReviewer, ReviewResult
from stella.framework.resources.skills_registry import SkillsRegistry
from stella.framework.testing.fakes import FakeLLM, FakeVault


def _manifest(tipo: str = "especialista", setor: str = "operacional") -> AgentManifest:
    return AgentManifest(
        nome="ag",
        tipo=tipo,  # type: ignore[arg-type]
        setor=setor,
        descricao="agente de teste",
        execucao="in_process",
        modelo_minimo="gemma",
        inputs_obrigatorios=[],
        exemplo_uso={},
        quando_usar="testes do reviewer",
        capacidades_externas=CapacidadesExternas(),
    )


def test_review_result_dataclass_aceita_minimo() -> None:
    out = AgentOutput(resultado={"x": 1})
    r = ReviewResult(veredicto="aprovado", feedback="ok", output_final=out)
    assert r.veredicto == "aprovado"
    assert r.feedback == "ok"
    assert r.output_final is out
    assert r.avisos_para_bruno == []


def test_reviewer_pula_revisao_quando_policy_diz_nao() -> None:
    """Especialista em setor operacional: policy diz nao revisar -> aprovado direto."""
    reviewer = QualityReviewer(
        llm=None,
        vault=None,
        skills_reg=None,
        policy=ReviewPolicy(),
    )
    manifest = _manifest(tipo="especialista", setor="operacional")
    output = AgentOutput(resultado={"x": 1})

    result = reviewer.review(input_original={}, output=output, agent_manifest=manifest)

    assert result.veredicto == "aprovado"
    assert "pulada" in result.feedback
    assert result.output_final is output


def test_reviewer_pula_revisao_com_skip_review_explicito() -> None:
    reviewer = QualityReviewer(llm=None, vault=None, skills_reg=None, policy=ReviewPolicy())
    manifest = _manifest(tipo="coordenador")
    output = AgentOutput(resultado={})

    result = reviewer.review(
        input_original={"--skip-review": True},
        output=output,
        agent_manifest=manifest,
    )
    assert result.veredicto == "aprovado"


def _reviewer_real(
    llm_responses: list[str],
    vault_notes: dict | None = None,
    skills_dir: Path | None = None,
) -> QualityReviewer:
    fake_llm = FakeLLM(responses=llm_responses)
    router = LLMRouter(gemma=fake_llm, anthropic=fake_llm, default="gemma")
    return QualityReviewer(
        llm=router,
        vault=FakeVault(notes=vault_notes or {}),
        skills_reg=SkillsRegistry(
            skills_dir if skills_dir else Path("/tmp/skills_inexistente_path")
        ),
        policy=ReviewPolicy(),
    )


def test_reviewer_chama_llm_quando_policy_diz_revisar(tmp_path: Path) -> None:
    """Coordenador: policy revisa, LLM (FakeLLM) devolve aprovado."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    reviewer = _reviewer_real(
        llm_responses=[json.dumps({"veredicto": "aprovado", "feedback": "ok"})],
        skills_dir=skills_dir,
    )
    out = AgentOutput(resultado={"resultado": "x"})
    result = reviewer.review({}, out, _manifest(tipo="coordenador"))
    assert result.veredicto == "aprovado"
    assert result.feedback == "ok"


def test_reviewer_passa_refazer_quando_llm_devolve_refazer(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    reviewer = _reviewer_real(
        llm_responses=[json.dumps({"veredicto": "refazer", "feedback": "tom errado"})],
        skills_dir=skills_dir,
    )
    out = AgentOutput(resultado={"copy": "..."})
    result = reviewer.review({}, out, _manifest(tipo="coordenador"), tentativa=1)
    assert result.veredicto == "refazer"
    assert "tom errado" in result.feedback


def test_reviewer_resposta_llm_malformada_devolve_rejeitar_seguro(tmp_path: Path) -> None:
    """JSON malformado -> rejeitar (NAO crasha)."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    reviewer = _reviewer_real(
        llm_responses=["isto nao e JSON valido"],
        skills_dir=skills_dir,
    )
    out = AgentOutput(resultado={})
    result = reviewer.review({}, out, _manifest(tipo="coordenador"))
    assert result.veredicto == "rejeitar"
    assert "parsear" in result.feedback.lower() or "valido" in result.feedback.lower()


def test_reviewer_le_padrao_do_setor_quando_existe(tmp_path: Path) -> None:
    """Reviewer le C04/Padroes/<setor>.md se existir, inclui no contexto."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    vault_notes = {
        "C04 Claude Obsidian/Padrões/copy.md": ("REGRA: evitar superlativos", {"tipo": "padrao"}),
    }
    fake_llm = FakeLLM(responses=[json.dumps({"veredicto": "aprovado", "feedback": "ok"})])
    router = LLMRouter(gemma=fake_llm, anthropic=fake_llm, default="gemma")
    reviewer = QualityReviewer(
        llm=router,
        vault=FakeVault(notes=vault_notes),
        skills_reg=SkillsRegistry(skills_dir),
        policy=ReviewPolicy(),
    )
    reviewer.review({}, AgentOutput(resultado={"copy": "x"}), _manifest(setor="copy"))
    assert "evitar superlativos" in fake_llm.calls[0]


def test_reviewer_le_aprendizados_quando_existe(tmp_path: Path) -> None:
    """Reviewer le C04/Padroes/_aprendizados.md se existir, inclui no contexto."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    vault_notes = {
        "C04 Claude Obsidian/Padrões/_aprendizados.md": (
            "### 2026-05-01 — copy: nada de 'incrivel'",
            {"tipo": "aprendizados"},
        ),
    }
    fake_llm = FakeLLM(responses=[json.dumps({"veredicto": "aprovado", "feedback": "ok"})])
    router = LLMRouter(gemma=fake_llm, anthropic=fake_llm, default="gemma")
    reviewer = QualityReviewer(
        llm=router,
        vault=FakeVault(notes=vault_notes),
        skills_reg=SkillsRegistry(skills_dir),
        policy=ReviewPolicy(),
    )
    reviewer.review({}, AgentOutput(resultado={"x": 1}), _manifest(setor="copy"))
    assert "incrivel" in fake_llm.calls[0]


def test_reviewer_segunda_tentativa_refazer_vira_aceitar_com_aviso(tmp_path: Path) -> None:
    """Q2=E: refazer na tentativa 2 vira aceitar_com_aviso para nao travar Bruno."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    reviewer = _reviewer_real(
        llm_responses=[json.dumps({"veredicto": "refazer", "feedback": "ainda fora do padrao"})],
        skills_dir=skills_dir,
    )
    out = AgentOutput(resultado={"copy": "..."})
    result = reviewer.review({}, out, _manifest(tipo="coordenador"), tentativa=2)
    assert result.veredicto == "aceitar_com_aviso"
    assert len(result.avisos_para_bruno) == 1
    assert "tentou 2x" in result.avisos_para_bruno[0].lower()
    assert "ainda fora do padrao" in result.avisos_para_bruno[0]


def test_reviewer_terceira_tentativa_tambem_vira_aceitar_com_aviso(tmp_path: Path) -> None:
    """Qualquer tentativa >= 2 com refazer -> aceitar_com_aviso (nao trava)."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    reviewer = _reviewer_real(
        llm_responses=[json.dumps({"veredicto": "refazer", "feedback": "ainda fora"})],
        skills_dir=skills_dir,
    )
    result = reviewer.review(
        {},
        AgentOutput(resultado={}),
        _manifest(tipo="coordenador"),
        tentativa=3,
    )
    assert result.veredicto == "aceitar_com_aviso"


def test_reviewer_aprovado_na_segunda_tentativa_passa_normal(tmp_path: Path) -> None:
    """Se na tentativa 2 o LLM aprova, devolve aprovado (sem aviso)."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    reviewer = _reviewer_real(
        llm_responses=[json.dumps({"veredicto": "aprovado", "feedback": "agora sim"})],
        skills_dir=skills_dir,
    )
    result = reviewer.review(
        {},
        AgentOutput(resultado={}),
        _manifest(tipo="coordenador"),
        tentativa=2,
    )
    assert result.veredicto == "aprovado"
    assert result.avisos_para_bruno == []
