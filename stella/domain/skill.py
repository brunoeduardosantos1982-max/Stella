from dataclasses import dataclass, field
from enum import StrEnum

from stella.domain.enums import ModeloIA


class OrigemSkill(StrEnum):
    CORE = "core"
    CUSTOM = "custom"


@dataclass
class Skill:
    id: str
    nome: str
    descricao: str
    arquivo_path: str
    gatilhos: list[str] = field(default_factory=list)
    modelo_minimo: ModeloIA = ModeloIA.GEMMA
    origem: OrigemSkill = OrigemSkill.CORE
    usos: int = 0
