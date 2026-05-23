from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

import stella as _stella_pkg
from stella.domain.enums import ModeloIA


def _pacote_root() -> Path:
    """Devolve a raiz do pacote `stella/` em disco — usado para defaults FB-M4."""
    return Path(_stella_pkg.__file__).parent


class StellaConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="STELLA_",
        extra="ignore",
    )

    # Chaves de API (SecretStr evita leak em logs/repr)
    nvidia_api_key: SecretStr
    anthropic_api_key: SecretStr

    # Caminho do vault Obsidian
    vault_path: Path

    # Modelo padrão
    modelo_padrao: ModeloIA = ModeloIA.GEMMA

    # Teto de orçamento mensal em USD
    teto_mensal_usd: float = Field(default=100.0, gt=0)

    # Hora da verificação de segurança diária (0-23)
    daily_check_hour: int = Field(default=7, ge=0, le=23)

    # FB-M4: paths usados pelo framework multi-agente
    agents_dir: Path = Field(default_factory=lambda: _pacote_root() / "agents")
    skills_dir: Path = Field(default_factory=lambda: _pacote_root() / "prompts" / "skills")

    # FB-Sub-B: integração de publicação em redes sociais
    postiz_token: SecretStr = Field(default=SecretStr(""))
    publicacao_modo: Literal["semi-auto", "auto"] = "semi-auto"
