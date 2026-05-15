from datetime import datetime

import pytest

from stella.domain.tarefa import Tarefa, StatusTarefa


def test_tarefa_nasce_pendente():
    t = Tarefa(
        id="2026-05-14-001",
        descricao="análise de margem",
        agente="garimpador",
        delegada_em=datetime(2026, 5, 14, 14, 30),
    )
    assert t.status == StatusTarefa.PENDENTE
    assert t.tentativas == 1
    assert t.resultado_path is None
    assert t.concluida_em is None


def test_marcar_concluida_exige_resultado_path():
    t = Tarefa(
        id="2026-05-14-001",
        descricao="análise de margem",
        agente="garimpador",
        delegada_em=datetime(2026, 5, 14, 14, 30),
    )
    with pytest.raises(ValueError, match="resultado_path"):
        t.marcar_concluida("")


def test_marcar_concluida_preenche_campos():
    momento = datetime(2026, 5, 15, 10, 0)
    t = Tarefa(
        id="2026-05-14-001",
        descricao="análise de margem",
        agente="garimpador",
        delegada_em=datetime(2026, 5, 14, 14, 30),
    )
    t.marcar_concluida("C04 Claude Obsidian/outputs/garimpador/r1.md", concluida_em=momento)
    assert t.status == StatusTarefa.CONCLUIDA
    assert t.resultado_path == "C04 Claude Obsidian/outputs/garimpador/r1.md"
    assert t.concluida_em == momento


def test_status_serializa_como_string():
    assert StatusTarefa.EM_ANDAMENTO.value == "em_andamento"


def test_marcar_falha_muda_status():
    t = Tarefa(
        id="2026-05-14-001",
        descricao="análise de margem",
        agente="garimpador",
        delegada_em=datetime(2026, 5, 14, 14, 30),
    )
    t.marcar_falha()
    assert t.status == StatusTarefa.FALHA


def test_marcar_cancelada_muda_status():
    t = Tarefa(
        id="2026-05-14-001",
        descricao="análise de margem",
        agente="garimpador",
        delegada_em=datetime(2026, 5, 14, 14, 30),
    )
    t.marcar_cancelada()
    assert t.status == StatusTarefa.CANCELADA
