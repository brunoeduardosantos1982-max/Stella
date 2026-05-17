from stella.framework.agent import AgentOutput


def test_agent_output_minimo() -> None:
    out = AgentOutput(resultado={"texto": "ok"})
    assert out.resultado == {"texto": "ok"}
    assert out.sucesso is True
    assert out.mensagens == []
    assert out.custo_estimado_usd == 0.0


def test_agent_output_com_aviso() -> None:
    out = AgentOutput(
        resultado={"copy": "..."},
        sucesso=True,
        mensagens=["abaixo do padrão de tom"],
        custo_estimado_usd=0.012,
    )
    assert out.sucesso is True
    assert "abaixo do padrão de tom" in out.mensagens
    assert out.custo_estimado_usd == 0.012


def test_agent_output_falha() -> None:
    out = AgentOutput(resultado={}, sucesso=False, mensagens=["timeout"])
    assert out.sucesso is False
