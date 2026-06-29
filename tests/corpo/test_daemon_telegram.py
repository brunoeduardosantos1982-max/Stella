"""Testes do daemon Telegram, foco no bug de continuidade de sessão.

Root cause (2026-06-25): o persona grande passado INLINE via --append-system-prompt
mangla o argumento no claude.CMD (wrapper batch do Windows), o output vira texto
plano em vez de JSON, json.loads falha e o session_id nunca é salvo -> todo
follow-up perde o contexto. Fix: passar o persona por --append-system-prompt-file.
"""

from pathlib import Path

from stella.corpo.daemon_telegram import (
    PERSONA_CONTEUDO,
    _args_claude,
    _eh_nova_solicitacao,
)


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


# --- Buraco residual da continuidade (2026-06-28) ------------------------------
# Um follow-up que RESPONDE ao menu de opções ('faz a opção 2 do roteiro') contém
# verbo de criação + palavra de conteúdo, então o detector antigo o tratava como
# pedido NOVO e ZERAVA a sessão -> a Stella perdia o contexto no meio do fluxo.


def test_resposta_de_selecao_no_meio_do_fluxo_nao_e_nova_solicitacao():
    # exatamente o caso relatado pelo Bruno
    assert _eh_nova_solicitacao("faz a opção 2 do roteiro", conteudo_ja_ativo=True) is False
    assert _eh_nova_solicitacao("manda a opção 1", conteudo_ja_ativo=True) is False
    assert _eh_nova_solicitacao("a segunda", conteudo_ja_ativo=True) is False


def test_pedido_de_tema_novo_no_meio_do_fluxo_ainda_reseta():
    # mudar de assunto dentro do TTL continua zerando a sessão (comportamento intencional)
    assert _eh_nova_solicitacao("cria um script sobre vendas", conteudo_ja_ativo=True) is True


def test_pedido_novo_em_chat_frio_reseta():
    assert _eh_nova_solicitacao("cria um roteiro sobre IA", conteudo_ja_ativo=False) is True


def test_conversa_normal_nao_e_solicitacao_de_conteudo():
    assert _eh_nova_solicitacao("bom dia, tudo certo?", conteudo_ja_ativo=False) is False


# --- Ear-prompter aposentado: ETAPA 2 entrega bullets de gravação (2026-06-29) ---
# Decisão do Bruno: falar a partir de bullets sai mais natural que recitar o áudio
# palavra por palavra. O módulo ear_prompter fica dormente; a persona muda.


def test_persona_conteudo_etapa2_entrega_bullets_sem_ear_prompter():
    persona = PERSONA_CONTEUDO.lower()
    assert "bullets" in persona  # ETAPA 2 monta bullets de gravação
    assert "bullets-gravacao.md" in PERSONA_CONTEUDO  # artefato salvo na pasta
    assert "ear-prompter" not in persona  # áudio aposentado
    assert "enviar-audio" not in persona
