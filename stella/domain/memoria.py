from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Memoria:
    perfil_usuario: dict[str, Any]
    aprendizados: list[str] = field(default_factory=list)
    decisoes_ids: list[str] = field(default_factory=list)
    projetos_ativos: list[str] = field(default_factory=list)
    ultima_atualizacao: datetime | None = None
