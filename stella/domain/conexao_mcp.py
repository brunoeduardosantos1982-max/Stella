from dataclasses import dataclass, field
from enum import Enum

from stella.domain.enums import ModeloIA


class StatusMCP(str, Enum):
    PRE_CONFIGURADO = "pre-configurado"
    POR_DEMANDA = "por-demanda"


@dataclass
class ConexaoMCP:
    nome: str
    tipo: str
    endpoint: str
    status: StatusMCP = StatusMCP.POR_DEMANDA
    ferramentas_expostas: list[str] = field(default_factory=list)
    requer_modelo: ModeloIA = ModeloIA.SONNET
