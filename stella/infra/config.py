from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from stella.domain.enums import ModeloIA


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
