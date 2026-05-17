import pytest

from stella.framework.scheduling import BackgroundScheduler, IdleTask


def test_idle_task_dataclass_minima() -> None:
    t = IdleTask(
        nome="varredura semanal de notas",
        prioridade=5,
        agente_alvo="agente_insights",
        payload={"periodo": "ultima_semana"},
    )
    assert t.nome == "varredura semanal de notas"
    assert t.prioridade == 5
    assert t.agente_alvo == "agente_insights"


def test_background_scheduler_e_abstrato() -> None:
    with pytest.raises(TypeError):
        BackgroundScheduler()  # type: ignore[abstract]


def test_background_scheduler_subclasse_pode_implementar() -> None:
    class _Fake(BackgroundScheduler):
        def __init__(self) -> None:
            self._fila: list[IdleTask] = []

        def submit_idle_task(self, task: IdleTask) -> str:
            self._fila.append(task)
            return f"id-{len(self._fila)}"

        def list_pending(self) -> list[IdleTask]:
            return list(self._fila)

    s = _Fake()
    t = IdleTask(nome="x", prioridade=1, agente_alvo="a", payload={})
    tid = s.submit_idle_task(t)
    assert tid == "id-1"
    assert s.list_pending() == [t]
