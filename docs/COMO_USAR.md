# Como usar a Stella (M2)

## Capturando ideias

```powershell
stella anota "revisar copy do Centro Viagens antes de sexta"
```

A Stella usa o Gemma (NVIDIA, grátis) para extrair título e tags, depois
escreve a nota em `A00 Inbox/YYYY-MM-DD HH-MM — Título.md` com frontmatter
completo (`tipo: ideia`, `criado-em`, `tags`).

Se o LLM falhar ou devolver JSON inválido, a Stella usa fallback (primeiras
palavras do texto como título, sem tags) — captura nunca é perdida.

## Perguntando sobre projetos

```powershell
stella pergunta "Centro Viagens" "qual a proxima acao?"
```

A Stella lê `B01 Projetos/Centro Viagens.md` no vault, monta o contexto e
usa Sonnet 4.6 para compor a resposta no formato:

1. **TL;DR** em 1 frase
2. **Detalhe** em tabela ou lista
3. **Próxima ação sugerida**
4. **Fontes** (wikilinks consultados)

## Log de conversas

Cada interação (`anota` ou `pergunta`) é registrada em
`bssurf00/C04 Claude Obsidian/logs e memória/conversas/YYYY-MM-DD.md`.
O frontmatter tem um contador de sessões do dia.

## Rastreamento de uso (tokens + custo)

Toda chamada LLM (Gemma ou Sonnet) é registrada em
`~/.stella/usage/YYYY-MM-DD.jsonl` com tokens consumidos e custo estimado em USD.
Essa é a base para o teto de US$100/mês que o M6 vai aplicar.

## Logs técnicos

Logs operacionais em `~/.stella/logs/stella.log` (rotativo, 7 backups).

## O que NÃO funciona ainda (próximos milestones)

| Comando | Milestone |
|---|---|
| `stella delega garimpador "X"` | M3 |
| `stella tarefas` | M3 |
| `stella daily-check` (automático) | M5 |
| `stella skills`, `stella mcp` | M6 |
| `stella budget` | M6 |
| Comando interativo (`stella` sem args) | M3 ou Fase 2 |

## Solução de problemas

**`stella` não reconhecido:**
Verifique que o venv está ativo (`.venv\Scripts\Activate.ps1`) e que rodou
`pip install -e ".[dev]"`.

**`STELLA_NVIDIA_API_KEY` exigido:**
Copie `.env.example` para `.env` e preencha as chaves.

**Pre-commit bloqueando commit:**
Leia o erro do hook (ruff/mypy/pytest), corrija e tente de novo.
NUNCA use `--no-verify` — o hook está lá por uma razão.
