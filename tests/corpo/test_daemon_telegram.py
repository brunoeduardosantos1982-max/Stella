"""Testes do daemon Telegram, foco no bug de continuidade de sessão.

Root cause (2026-06-25): o persona grande passado INLINE via --append-system-prompt
mangla o argumento no claude.CMD (wrapper batch do Windows), o output vira texto
plano em vez de JSON, json.loads falha e o session_id nunca é salvo -> todo
follow-up perde o contexto. Fix: passar o persona por --append-system-prompt-file.
"""

from pathlib import Path

from stella.corpo.daemon_telegram import _args_claude


def test_args_claude_persona_vai_por_arquivo_nao_inline():
    args = _args_claude("claude", "oi", modelo="claude-opus-4-8", persona="SOU A STELLA")
    assert "--append-system-prompt" not in args  # nunca inline (mangla no .CMD)
    assert "--append-system-prompt-file" in args
    idx = args.index("--append-system-prompt-file")
    persona_file = Path(args[idx + 1])
    assert persona_file.exists()
    assert "SOU A STELLA" in persona_file.read_text(encoding="utf-8")
    assert args[-2:] == ["--output-format", "json"]


def test_args_claude_resume_sem_persona_nao_referencia_arquivo():
    args = _args_claude("claude", "oi", resume="abc-123", mcp_on=True)
    assert "--append-system-prompt-file" not in args
    assert "--append-system-prompt" not in args
    assert args[args.index("--resume") + 1] == "abc-123"
