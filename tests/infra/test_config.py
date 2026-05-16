import pytest
from pydantic import ValidationError

from stella.infra.config import StellaConfig


def test_config_carrega_de_env_vars(monkeypatch, tmp_path):
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "nv-teste")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "ant-teste")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(tmp_path))

    cfg = StellaConfig()

    assert cfg.nvidia_api_key.get_secret_value() == "nv-teste"
    assert cfg.anthropic_api_key.get_secret_value() == "ant-teste"
    assert cfg.vault_path == tmp_path


def test_api_keys_nao_aparecem_em_repr(monkeypatch, tmp_path):
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "nv-segredo")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "ant-segredo")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(tmp_path))

    cfg = StellaConfig()

    assert "nv-segredo" not in repr(cfg)
    assert "ant-segredo" not in repr(cfg)


def test_config_tem_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "nv-teste")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "ant-teste")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(tmp_path))

    cfg = StellaConfig()

    assert cfg.modelo_padrao == "gemma"
    assert cfg.teto_mensal_usd == 100.0
    assert cfg.daily_check_hour == 7


def test_config_aceita_override_de_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "nv-teste")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "ant-teste")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("STELLA_MODELO_PADRAO", "sonnet")
    monkeypatch.setenv("STELLA_TETO_MENSAL_USD", "50.0")

    cfg = StellaConfig()

    assert cfg.modelo_padrao == "sonnet"
    assert cfg.teto_mensal_usd == 50.0


def test_daily_check_hour_rejeita_valor_invalido(monkeypatch, tmp_path):
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "nv-teste")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "ant-teste")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("STELLA_DAILY_CHECK_HOUR", "99")

    with pytest.raises(ValidationError):
        StellaConfig()


def test_teto_mensal_usd_rejeita_zero(monkeypatch, tmp_path):
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "nv-teste")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "ant-teste")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("STELLA_TETO_MENSAL_USD", "0")

    with pytest.raises(ValidationError):
        StellaConfig()
