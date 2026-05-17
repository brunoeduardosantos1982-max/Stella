from stella.framework.agent import AgentOutput
from stella.framework.manifest import AgentManifest, CapacidadesExternas
from stella.framework.quality.policies import ReviewPolicy
from stella.framework.quality.reviewer import QualityReviewer, ReviewResult


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
