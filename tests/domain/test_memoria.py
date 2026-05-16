from datetime import datetime

from stella.domain.memoria import Memoria


def test_memoria_nasce_com_listas_vazias():
    m = Memoria(perfil_usuario={"nome": "Bruno"})
    assert m.aprendizados == []
    assert m.decisoes_ids == []
    assert m.projetos_ativos == []
    assert m.ultima_atualizacao is None


def test_memoria_aceita_dados():
    m = Memoria(
        perfil_usuario={"nome": "Bruno"},
        aprendizados=["prefere tabelas a listas"],
        decisoes_ids=["2026-05-14-001"],
        projetos_ativos=["Centro Viagens"],
        ultima_atualizacao=datetime(2026, 5, 14, 12, 0),
    )
    assert "prefere tabelas a listas" in m.aprendizados
    assert m.decisoes_ids == ["2026-05-14-001"]
    assert m.projetos_ativos == ["Centro Viagens"]
