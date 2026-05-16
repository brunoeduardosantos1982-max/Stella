from stella.prompts.prompt_builder import ContextoDinamico, PromptBuilder


def test_carrega_e_concatena_prompts_estaticos() -> None:
    builder = PromptBuilder()
    prompt = builder.build(
        ContextoDinamico(
            memoria_resumida="Bruno gosta de tabelas.",
            tarefas_abertas="nenhuma",
            projetos_ativos="Centro Viagens",
            ultimas_interacoes="nenhuma",
            saudacao="Bom dia",
        )
    )
    assert "Você é a Stella" in prompt
    assert "Português brasileiro" in prompt
    assert "Bruno gosta de tabelas." in prompt
    assert "Bom dia" in prompt


def test_placeholders_sao_substituidos() -> None:
    builder = PromptBuilder()
    prompt = builder.build(
        ContextoDinamico(
            memoria_resumida="MEM_TEST",
            tarefas_abertas="TAREFA_TEST",
            projetos_ativos="PROJ_TEST",
            ultimas_interacoes="INTERACAO_TEST",
            saudacao="SAUDACAO_TEST",
        )
    )
    assert "{memoria_resumida}" not in prompt
    assert "MEM_TEST" in prompt
    assert "TAREFA_TEST" in prompt
    assert "PROJ_TEST" in prompt
    assert "INTERACAO_TEST" in prompt
    assert "SAUDACAO_TEST" in prompt


def test_saudacao_para_hora_da_manha() -> None:
    builder = PromptBuilder()
    assert builder.saudacao_por_hora(8) == "Bom dia, Senhor."
    assert builder.saudacao_por_hora(14) == "Boa tarde, Senhor."
    assert builder.saudacao_por_hora(20) == "Boa noite, Senhor."
    assert builder.saudacao_por_hora(2) == "Senhor."  # madrugada — sem horário
