from dataclasses import dataclass, field
from enum import Enum


class OrigemSkill(str, Enum):
    CORE = "core"
    CUSTOM = "custom"


@dataclass
class Skill:
    id: str
    nome: str
    descricao: str
    arquivo_path: str
    gatilhos: list[str] = field(default_factory=list)
    modelo_minimo: str = "gemma"
    origem: OrigemSkill = OrigemSkill.CORE
    usos: int = 0
