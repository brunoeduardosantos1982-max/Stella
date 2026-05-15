from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class StellaConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="STELLA_",
        extra="ignore",
    )

    # Chaves de API
    nvidia_api_key: str
    anthropic_api_key: str

    # Caminho do vault Obsidian
    vault_path: Path

    # Modelo padrão: "gemma" | "sonnet"
    modelo_padrao: str = "gemma"

    # Teto de orçamento mensal em USD
    teto_mensal_usd: float = 100.0

    # Hora da verificação de segurança diária (0-23)
    daily_check_hour: int = 7
