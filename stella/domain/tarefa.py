from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class StatusTarefa(StrEnum):
    PENDENTE = "pendente"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    FALHA = "falha"
    CANCELADA = "cancelada"


@dataclass
class Tarefa:
    id: str
    descricao: str
    agente: str
    delegada_em: datetime
    status: StatusTarefa = StatusTarefa.PENDENTE
    prazo: datetime | None = None
    concluida_em: datetime | None = None
    resultado_path: str | None = None
    tentativas: int = 1

    def marcar_concluida(
        self,
        resultado_path: str,
        concluida_em: datetime | None = None,
    ) -> None:
        if not resultado_path:
            raise ValueError("Tarefa concluída exige resultado_path não vazio")
        self.status = StatusTarefa.CONCLUIDA
        self.resultado_path = resultado_path
        self.concluida_em = concluida_em or datetime.now()

    def marcar_falha(self) -> None:
        self.status = StatusTarefa.FALHA

    def marcar_cancelada(self) -> None:
        self.status = StatusTarefa.CANCELADA
