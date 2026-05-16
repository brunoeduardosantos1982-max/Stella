from stella.domain.agente import Agente


def test_agente_estrutura():
    a = Agente(
        nome="garimpador",
        endpoint="http://localhost:8000/api/analyze",
        descricao="Analisa margem líquida por produto",
        parametros_esperados=["periodo", "foco"],
    )
    assert a.nome == "garimpador"
    assert "periodo" in a.parametros_esperados
