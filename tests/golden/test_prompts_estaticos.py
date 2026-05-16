"""Golden tests dos prompts — detectam mudanças não-intencionais nos arquivos .md.

Quando você EDITAR conscientemente um prompt (tom_jarvis.md, identidade.md, etc),
este teste vai falhar. Para aceitar a mudança:
1. Delete `tests/golden/snapshots/system_prompt_completo.txt`
2. Rode `pytest tests/golden/test_prompts_estaticos.py -v` (recria o snapshot)
3. Inspecione o diff visualmente via `git diff`
4. Se aprovado, commite o snapshot atualizado junto com a mudança no prompt
"""

from pathlib import Path

from stella.prompts.prompt_builder import ContextoDinamico, PromptBuilder

_SNAPSHOTS = Path(__file__).parent / "snapshots"


def _ctx_canonico() -> ContextoDinamico:
    return ContextoDinamico(
        memoria_resumida="(memoria stub para golden test)",
        tarefas_abertas="(tarefas stub)",
        projetos_ativos="(projetos stub)",
        ultimas_interacoes="(interacoes stub)",
        saudacao="Bom dia, Senhor.",
    )


def test_system_prompt_completo_bate_com_snapshot() -> None:
    builder = PromptBuilder()
    atual = builder.build(_ctx_canonico())
    _SNAPSHOTS.mkdir(exist_ok=True)
    snapshot_path = _SNAPSHOTS / "system_prompt_completo.txt"

    if not snapshot_path.exists():
        snapshot_path.write_text(atual, encoding="utf-8")
        return  # primeira execução: cria o snapshot e passa

    esperado = snapshot_path.read_text(encoding="utf-8")
    assert atual == esperado, (
        "System prompt mudou. Se intencional, regrave o snapshot:\n"
        f"  rm {snapshot_path}\n"
        "  pytest tests/golden/test_prompts_estaticos.py -v\n"
        "  git add tests/golden/snapshots/system_prompt_completo.txt\n"
    )


def test_marcadores_chave_presentes_no_prompt() -> None:
    """Independente do conteudo exato, certos marcadores DEVEM existir."""
    builder = PromptBuilder()
    prompt = builder.build(_ctx_canonico())

    marcadores_obrigatorios = [
        "Você é a Stella",
        "Bruno Eduardo Santos",
        "J.A.R.V.I.S",
        "Português brasileiro",
        '"Senhor"',
        "TL;DR",
        "puxa a orelha",
    ]
    for marcador in marcadores_obrigatorios:
        assert marcador in prompt, f"marcador obrigatório ausente: {marcador!r}"
