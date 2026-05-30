from enum import StrEnum


class ModeloIA(StrEnum):
    """Modelos de LLM disponíveis no sistema Stella.

    Usado em `Skill.modelo_minimo`, `ConexaoMCP.requer_modelo` e
    `StellaConfig.modelo_padrao` para evitar strings soltas.
    """

    GEMMA = "gemma"
    SONNET = "sonnet"
    OPUS = "opus"
