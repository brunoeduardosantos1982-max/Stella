"""Testes do modo warn-only do QualityReviewer (setor marketing)."""

import json
from pathlib import Path

from stella.adapters.llm.router import LLMRouter
from stella.framework.agent import AgentOutput
from stella.framework.manifest import AgentManifest, CapacidadesExternas
from stella.framework.quality.policies import ReviewPolicy
from stella.framework.quality.reviewer import QualityReviewer
from stella.framework.testing.fakes import FakeLLM, FakeVault


def _marketing_manifest() -> AgentManifest:
    return AgentManifest(
        nome="copywriter",
        tipo="especialista",
        setor="marketing",
        descricao="copywriter de teste",
        execucao="in_process",
        modelo_minimo="gemma",
        inputs_obrigatorios=[],
        exemplo_uso={},
        quando_usar="testes warn-only",
        capacidades_externas=CapacidadesExternas(),
    )


def _reviewer(llm_responses: list[str], tmp_path: Path) -> QualityReviewer:
    from stella.framework.resources.skills_registry import SkillsRegistry

    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    fake_llm = FakeLLM(responses=llm_responses)
    router = LLMRouter(gemma=fake_llm, anthropic=fake_llm)
    return QualityReviewer(
        llm=router,
        vault=FakeVault(),
        skills_reg=SkillsRegistry(skills_dir),
        policy=ReviewPolicy(),
    )


def test_marketing_warn_only_nao_levanta_quando_llm_diz_refazer(tmp_path: Path) -> None:
    """setor marketing + LLM reprova → aceitar_com_aviso (nunca bloqueia)."""
    reviewer = _reviewer(
        [json.dumps({"veredicto": "refazer", "feedback": "legenda muito longa"})],
        tmp_path,
    )
    output = AgentOutput(resultado={"legenda": "x" * 2300})
    result = reviewer.review({}, output, _marketing_manifest())

    assert result.veredicto == "aceitar_com_aviso"
    assert any("[QualityReviewer]" in m for m in result.output_final.mensagens)
    assert "legenda muito longa" in result.output_final.mensagens[-1]


def test_marketing_warn_only_aprovado_passa_limpo(tmp_path: Path) -> None:
    """setor marketing + LLM aprova → aprovado sem mudanças no output."""
    reviewer = _reviewer(
        [json.dumps({"veredicto": "aprovado", "feedback": "copy ok"})],
        tmp_path,
    )
    output = AgentOutput(resultado={"legenda": "bom"})
    result = reviewer.review({}, output, _marketing_manifest())

    assert result.veredicto == "aprovado"
    assert result.output_final.mensagens == []


def test_setor_copy_ainda_bloqueia_tentativa_1(tmp_path: Path) -> None:
    """Setor 'copy' NÃO está em warn-only — refazer na t=1 ainda é refazer."""
    from stella.framework.resources.skills_registry import SkillsRegistry

    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    fake_llm = FakeLLM(responses=[json.dumps({"veredicto": "refazer", "feedback": "erro"})])
    router = LLMRouter(gemma=fake_llm, anthropic=fake_llm)
    reviewer = QualityReviewer(
        llm=router,
        vault=FakeVault(),
        skills_reg=SkillsRegistry(skills_dir),
        policy=ReviewPolicy(),
    )
    m = AgentManifest(
        nome="ag",
        tipo="especialista",
        setor="copy",
        descricao="agente copy",
        execucao="in_process",
        modelo_minimo="gemma",
        inputs_obrigatorios=[],
        exemplo_uso={},
        quando_usar="apenas em testes do reviewer",
        capacidades_externas=CapacidadesExternas(),
    )
    result = reviewer.review({}, AgentOutput(resultado={}), m, tentativa=1)
    assert result.veredicto == "refazer"


def test_marketing_warn_only_rejeitar_tambem_vira_aceitar_com_aviso(tmp_path: Path) -> None:
    """veredicto='rejeitar' em setor warn-only também não bloqueia."""
    reviewer = _reviewer(
        [json.dumps({"veredicto": "rejeitar", "feedback": "muito fora do padrão"})],
        tmp_path,
    )
    result = reviewer.review({}, AgentOutput(resultado={}), _marketing_manifest())
    assert result.veredicto == "aceitar_com_aviso"
