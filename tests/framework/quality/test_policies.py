from stella.framework.manifest import AgentManifest, CapacidadesExternas
from stella.framework.quality.policies import ReviewPolicy


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
        quando_usar="testes da policy",
        capacidades_externas=CapacidadesExternas(),
    )


def test_policy_coordenador_sempre_revisa() -> None:
    p = ReviewPolicy()
    assert p.deve_revisar(_manifest(tipo="coordenador"), {}) is True


def test_policy_especialista_em_setor_critico_revisa() -> None:
    p = ReviewPolicy()
    for setor in ("design", "copy", "codigo"):
        assert p.deve_revisar(_manifest(tipo="especialista", setor=setor), {}) is True


def test_policy_especialista_em_setor_operacional_nao_revisa() -> None:
    p = ReviewPolicy()
    assert p.deve_revisar(_manifest(tipo="especialista", setor="operacional"), {}) is False


def test_policy_input_com_skip_review_pula_mesmo_em_setor_critico() -> None:
    p = ReviewPolicy()
    assert p.deve_revisar(_manifest(setor="copy"), {"--skip-review": True}) is False


def test_policy_skip_review_false_nao_pula() -> None:
    p = ReviewPolicy()
    assert p.deve_revisar(_manifest(setor="copy"), {"--skip-review": False}) is True
