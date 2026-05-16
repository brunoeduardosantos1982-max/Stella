from dataclasses import dataclass, field


@dataclass
class Agente:
    nome: str
    endpoint: str
    descricao: str
    parametros_esperados: list[str] = field(default_factory=list)
