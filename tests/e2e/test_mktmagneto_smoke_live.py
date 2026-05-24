"""Smoke test E2E live do agente de conteudo mktmagneto.

Executa o coordenador real via build_stella com LLM real.
Opt-in via: pytest -m live.
"""

import pytest


def _cfg_ou_skip():
    from stella.infra.config import StellaConfig

    try:
        cfg = StellaConfig()
        key = cfg.anthropic_api_key.get_secret_value()
        if not key or "fake" in key.lower():
            pytest.skip(".env sem STELLA_ANTHROPIC_API_KEY real")
        return cfg
    except Exception as e:  # pragma: no cover - caminho de infraestrutura
        pytest.skip(f"StellaConfig nao carregou: {e}")


@pytest.mark.live
def test_mktmagneto_smoke_pipeline_real() -> None:
    from stella.app import build_stella

    cfg = _cfg_ou_skip()
    stella = build_stella(cfg)

    client = stella.registry.get("agente_marca_mktmagneto")
    out = client.execute({})

    assert out.sucesso is True
    assert isinstance(out.resultado, dict)
    assert "posts_em_rascunho" in out.resultado
    assert out.resultado["posts_em_rascunho"] >= 1
