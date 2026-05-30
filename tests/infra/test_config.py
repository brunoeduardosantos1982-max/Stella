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


def test_modelo_padrao_invalido_levanta_erro(monkeypatch, tmp_path):
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "nv")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "ant")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("STELLA_MODELO_PADRAO", "gpt4")

    with pytest.raises(ValidationError):
        StellaConfig()


def test_config_tem_agents_dir_default_apontando_para_pacote(monkeypatch, tmp_path):
    """FB-M4 C1: StellaConfig.agents_dir default = stella/agents."""
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "fake")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(tmp_path))

    cfg = StellaConfig()
    assert cfg.agents_dir.name == "agents"
    assert "stella" in str(cfg.agents_dir)


def test_config_tem_skills_dir_default_apontando_para_prompts_skills(monkeypatch, tmp_path):
    """FB-M4 C1: StellaConfig.skills_dir default = stella/prompts/skills."""
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "fake")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(tmp_path))

    cfg = StellaConfig()
    assert cfg.skills_dir.name == "skills"
    assert "prompts" in str(cfg.skills_dir)


def test_config_tem_postiz_token(monkeypatch, tmp_path):
    """FB-Sub-B: StellaConfig expõe postiz_token (default vazio)."""
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "fake")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("STELLA_POSTIZ_TOKEN", "pos_abc123")

    from stella.infra.config import StellaConfig

    cfg = StellaConfig()
    assert cfg.postiz_token.get_secret_value() == "pos_abc123"


def test_config_postiz_token_default_vazio(monkeypatch, tmp_path):
    # chdir para tmp_path isola do `.env` real do projeto (pydantic-settings
    # carrega env_file relativo ao CWD).
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "fake")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(tmp_path))

    from stella.infra.config import StellaConfig

    cfg = StellaConfig()
    assert cfg.postiz_token.get_secret_value() == ""


def test_config_publicacao_modo_default_semi_auto(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "fake")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(tmp_path))

    from stella.infra.config import StellaConfig

    cfg = StellaConfig()
    assert cfg.publicacao_modo == "semi-auto"


def test_config_publicacao_modo_aceita_auto(monkeypatch, tmp_path):
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "fake")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("STELLA_PUBLICACAO_MODO", "auto")

    from stella.infra.config import StellaConfig

    cfg = StellaConfig()
    assert cfg.publicacao_modo == "auto"


def test_config_publicacao_modo_invalido_levanta_erro(monkeypatch, tmp_path):
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "fake")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("STELLA_PUBLICACAO_MODO", "turbo")

    from stella.infra.config import StellaConfig

    with pytest.raises(ValidationError):
        StellaConfig()


def test_config_notebooklm_defaults(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "fake")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(tmp_path))

    cfg = StellaConfig()

    assert cfg.notebooklm_notebook_id == ""
    assert cfg.notebooklm_bin == "notebooklm"
    assert cfg.notebooklm_timeout_s == 60


def test_config_notebooklm_override(monkeypatch, tmp_path):
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "fake")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("STELLA_NOTEBOOKLM_NOTEBOOK_ID", "nb_abc123")
    monkeypatch.setenv("STELLA_NOTEBOOKLM_TIMEOUT_S", "90")

    cfg = StellaConfig()

    assert cfg.notebooklm_notebook_id == "nb_abc123"
    assert cfg.notebooklm_timeout_s == 90
