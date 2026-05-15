from datetime import datetime

from stella.domain.memoria import Memoria


def test_memoria_nasce_com_listas_vazias():
    m = Memoria(perfil_usuario={"nome": "Bruno"})
    assert m.aprendizados == []
    assert m.decisoes == []
    assert m.projetos_ativos == []
    assert m.ultima_atualizacao is None


def test_memoria_aceita_dados():
    m = Memoria(
        perfil_usuario={"nome": "Bruno"},
        aprendizados=["prefere tabelas a listas"],
        projetos_ativos=["Centro Viagens"],
        ultima_atualizacao=datetime(2026, 5, 14, 12, 0),
    )
    assert "prefere tabelas a listas" in m.aprendizados
    assert m.projetos_ativos == ["Centro Viagens"]
