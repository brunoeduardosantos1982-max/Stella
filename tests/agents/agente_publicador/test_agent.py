from datetime import datetime

import pytest


def test_para_utc_iso_converte_brasilia_para_utc() -> None:
    from stella.agents.agente_publicador.agent import _para_utc_iso

    assert _para_utc_iso("2026-05-25 09:00") == "2026-05-25T12:00:00.000Z"


def test_para_utc_iso_aceita_datetime_naive() -> None:
    from stella.agents.agente_publicador.agent import _para_utc_iso

    assert _para_utc_iso(datetime(2026, 5, 25, 9, 0)) == "2026-05-25T12:00:00.000Z"


def test_para_utc_iso_string_invalida_levanta() -> None:
    from stella.agents.agente_publicador.agent import _para_utc_iso

    with pytest.raises(ValueError):
        _para_utc_iso("25/05/2026")


def test_execute_modo_invalido_devolve_falha() -> None:
    from stella.agents.agente_publicador.agent import Agent

    saida = Agent().execute({"modo": "turbo"})
    assert saida.sucesso is False
    assert "inválido" in saida.mensagens[0]
