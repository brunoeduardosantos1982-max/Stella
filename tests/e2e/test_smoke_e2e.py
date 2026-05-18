"""Smoke test E2E do framework — chama Anthropic API real.

Opt-in via `pytest -m live`. Custo ~$0.03 por execucao completa.
Requer .env com STELLA_ANTHROPIC_API_KEY e STELLA_NVIDIA_API_KEY validas.
"""

import pytest


def _check_env_ou_skip():
    """Skip os testes se .env nao tem as chaves necessarias.

    Reusa o padrao dos testes live existentes em tests/usecases/.
    """
    from stella.infra.config import StellaConfig

    try:
        cfg = StellaConfig()
        if (
            not cfg.anthropic_api_key.get_secret_value()
            or "fake" in cfg.anthropic_api_key.get_secret_value().lower()
        ):
            pytest.skip(".env sem STELLA_ANTHROPIC_API_KEY real — pulando E2E")
        return cfg
    except Exception as e:
        pytest.skip(f"StellaConfig nao carrega: {e}")


@pytest.mark.live
def test_smoke_agent_executa_via_stella_completa() -> None:
    """E2E: build_stella real -> registry.get('_smoke_') -> execute -> LLM real.

    Valida: pipeline completo do framework, sem passar por QualityReviewer
    (setor 'testes' nao aciona revisao por padrao).
    """
    from stella.app import build_stella

    cfg = _check_env_ou_skip()
    stella = build_stella(cfg)

    client = stella.registry.get("_smoke_")
    out = client.execute({"texto": "ok"})

    assert out.sucesso is True
    assert out.resultado["llm_chamado"] is True
    assert isinstance(out.resultado["echo"], str)
    assert len(out.resultado["echo"]) > 0


@pytest.mark.live
def test_smoke_passa_por_quality_reviewer_quando_setor_critico() -> None:
    """E2E: agente setor=copy passa por QualityReviewer (Sonnet).

    Valida: loop completo agente -> LLM -> QualityReviewer -> review com veredicto.
    """
    from stella.app import build_stella

    cfg = _check_env_ou_skip()
    stella = build_stella(cfg)

    client = stella.registry.get("_smoke_critico_")
    out = client.execute({"texto": "uma frase curta"})
    assert out.sucesso is True

    review = stella.quality_reviewer.review(
        input_original={"texto": "uma frase curta"},
        output=out,
        agent_manifest=client.manifest(),
    )
    assert review.veredicto in ("aprovado", "refazer", "aceitar_com_aviso", "rejeitar")
    assert review.output_final is out
