from stella.framework.quality.feedback import FeedbackLogger
from stella.framework.testing.fakes import FakeVault


def test_feedback_aprender_anexa_em_aprendizados_md_existente() -> None:
    vault = FakeVault(
        notes={
            "C04 Claude Obsidian/Padrões/_aprendizados.md": (
                "conteudo previo\n",
                {"title": "aprendizados"},
            ),
        }
    )
    logger = FeedbackLogger(vault=vault)
    logger.aprender(
        correcao_do_bruno="evitar superlativos",
        contexto={"setor": "copy", "agente": "agente_copy"},
    )
    nota = vault.read_note("C04 Claude Obsidian/Padrões/_aprendizados.md")
    assert "conteudo previo" in nota.content
    assert "evitar superlativos" in nota.content
    assert "copy" in nota.content
    assert "agente_copy" in nota.content


def test_feedback_aprender_cria_arquivo_se_nao_existir() -> None:
    vault = FakeVault()
    logger = FeedbackLogger(vault=vault)
    logger.aprender(
        correcao_do_bruno="usar voz ativa",
        contexto={"setor": "copy", "agente": "agente_copy"},
    )
    assert vault.note_exists("C04 Claude Obsidian/Padrões/_aprendizados.md")
    nota = vault.read_note("C04 Claude Obsidian/Padrões/_aprendizados.md")
    assert "usar voz ativa" in nota.content


def test_feedback_aprender_preserva_frontmatter_existente() -> None:
    vault = FakeVault(
        notes={
            "C04 Claude Obsidian/Padrões/_aprendizados.md": (
                "x",
                {"title": "aprendizados", "criado-em": "2026-05-17"},
            ),
        }
    )
    logger = FeedbackLogger(vault=vault)
    logger.aprender("regra nova", {"setor": "design", "agente": "ag"})
    nota = vault.read_note("C04 Claude Obsidian/Padrões/_aprendizados.md")
    assert nota.frontmatter["title"] == "aprendizados"
    assert nota.frontmatter["criado-em"] == "2026-05-17"


def test_feedback_aprender_entradas_multiplas_acumulam_em_ordem() -> None:
    vault = FakeVault()
    logger = FeedbackLogger(vault=vault)
    logger.aprender("primeira correcao", {"setor": "copy", "agente": "ag"})
    logger.aprender("segunda correcao", {"setor": "design", "agente": "ag"})
    nota = vault.read_note("C04 Claude Obsidian/Padrões/_aprendizados.md")
    assert nota.content.index("primeira correcao") < nota.content.index("segunda correcao")
