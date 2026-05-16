from stella.domain.skill import Skill, OrigemSkill


def test_skill_estrutura():
    s = Skill(
        id="brainstorming",
        nome="Brainstorming",
        descricao="Antes de criar qualquer coisa nova",
        arquivo_path="stella/prompts/skills/brainstorming.md",
        gatilhos=["vamos planejar", "nova ideia"],
        modelo_minimo="sonnet",
        origem=OrigemSkill.CORE,
    )
    assert s.origem == OrigemSkill.CORE
    assert s.usos == 0


def test_origem_skill_valores():
    assert OrigemSkill.CORE.value == "core"
    assert OrigemSkill.CUSTOM.value == "custom"
