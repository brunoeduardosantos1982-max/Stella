from datetime import datetime

from stella.adapters.vault.obsidian_vault import ObsidianVaultRepository
from stella.usecases.atualizar_memoria import AtualizarMemoria, RegistroInteracao


def test_anexa_interacao_a_arquivo_de_conversas_do_dia(vault_tmp) -> None:
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    usecase = AtualizarMemoria(vault_repo=repo)
    momento = datetime(2026, 5, 15, 14, 32)
    usecase.execute(
        RegistroInteracao(
            momento=momento,
            usecase="capturar_ideia",
            input_usuario='anota "revisar copy"',
            resposta_stella="Anotado em [[2026-05-15 14-32 — Revisar copy]].",
        )
    )
    nota = repo.read_note("C04 Claude Obsidian/logs e memória/conversas/2026-05-15.md")
    assert "14:32" in nota.content
    assert "capturar_ideia" in nota.content
    assert 'anota "revisar copy"' in nota.content
    assert "Anotado em" in nota.content


def test_duas_interacoes_no_mesmo_dia_acumulam(vault_tmp) -> None:
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    usecase = AtualizarMemoria(vault_repo=repo)
    usecase.execute(
        RegistroInteracao(
            momento=datetime(2026, 5, 15, 9, 0),
            usecase="capturar_ideia",
            input_usuario="anota A",
            resposta_stella="Anotado A",
        )
    )
    usecase.execute(
        RegistroInteracao(
            momento=datetime(2026, 5, 15, 10, 0),
            usecase="responder_projeto",
            input_usuario="pergunta B",
            resposta_stella="Resposta B",
        )
    )
    nota = repo.read_note("C04 Claude Obsidian/logs e memória/conversas/2026-05-15.md")
    assert "09:00" in nota.content
    assert "10:00" in nota.content
    assert "anota A" in nota.content
    assert "pergunta B" in nota.content


def test_atualiza_contador_de_sessoes_no_frontmatter(vault_tmp) -> None:
    repo = ObsidianVaultRepository(vault_root=vault_tmp)
    usecase = AtualizarMemoria(vault_repo=repo)
    usecase.execute(
        RegistroInteracao(
            momento=datetime(2026, 5, 15, 9, 0),
            usecase="capturar_ideia",
            input_usuario="A",
            resposta_stella="X",
        )
    )
    usecase.execute(
        RegistroInteracao(
            momento=datetime(2026, 5, 15, 10, 0),
            usecase="capturar_ideia",
            input_usuario="B",
            resposta_stella="Y",
        )
    )
    nota = repo.read_note("C04 Claude Obsidian/logs e memória/conversas/2026-05-15.md")
    assert nota.frontmatter["sessoes"] == 2
