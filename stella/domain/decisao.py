from dataclasses import dataclass
from datetime import date


@dataclass
class Decisao:
    id: str
    titulo: str
    contexto: str
    decisao: str
    motivo: str
    data: date
