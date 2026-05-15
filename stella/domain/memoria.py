from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Memoria:
    perfil_usuario: dict
    aprendizados: list[str] = field(default_factory=list)
    decisoes: list[str] = field(default_factory=list)
    projetos_ativos: list[str] = field(default_factory=list)
    ultima_atualizacao: datetime | None = None
