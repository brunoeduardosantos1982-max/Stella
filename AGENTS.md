# stella (fábrica Python da Stella)

Fábrica de pipelines da assistente pessoal Stella: daemon Telegram↔Claude, agentes de marca/conteúdo (copywriter, designer, publicador), radar de tendências e voz (STT whisper + TTS edge-tts). O "cérebro" da Stella é o Claude Code (skills e vault); este repo é a fábrica de volume. Regras compartilhadas do workspace: `D:\VortexBrain00\AGENTS.md`.

## Stack

Python ≥3.11, `pyproject.toml` (hatchling), venv em `.venv/`. Branch base: **master** (não main). Repo: `github.com/brunoeduardosantos1982-max/Stella`.

## Comandos

- Setup: `python -m venv .venv` → `.venv\Scripts\Activate.ps1` → `pip install -e ".[dev]"` → `copy .env.example .env`
- `pytest` — testes rápidos (exclui `live` por default)
- `pytest -m live` — E2E com APIs reais (exige `.env`; faz skip se faltar chave)
- `ruff check .` / `ruff format` — lint/format
- `mypy stella` — tipos
- `pre-commit install` / `pre-commit run` — hooks de qualidade rodam em cada commit
- CLI: `stella --help` (entrypoint `stella.frontends.cli:main`; ex.: `stella conteudo`, `stella publicar`, `stella radar`, `stella seguranca`)

## Variáveis de ambiente (nomes)

`STELLA_ANTHROPIC_API_KEY`, `STELLA_NVIDIA_API_KEY`, `STELLA_VAULT_PATH`, `STELLA_MODELO_PADRAO`, `STELLA_TETO_MENSAL_USD`, `STELLA_DAILY_CHECK_HOUR`, `STELLA_TAVILY_API_KEY`, `STELLA_PERPLEXITY_API_KEY`. Referência em `.env.example`. `ear-prompter` exige `ffmpeg` no PATH.

## Convenções

- Fila de publicação e arquivos de marca moram no vault: `bssurf00/C04 Claude Obsidian/Stella-publicacao/` (`STELLA_VAULT_PATH` aponta para o vault).
- Specs para Codex ficam em `docs/` (ex.: `docs/reforma-fabrica-codex.md`) — autocontidas.
- PRs pequenos com body "o que mudou / como testei / risco conhecido".

## Pegadinhas

- **O daemon Telegram carrega o código só no start.** Editar/commitar não muda o bot em execução: reiniciar a tarefa do Windows "Stella Daemon Telegram" (os `.ps1` do daemon/watchdog moram na RAIZ do workspace, não neste repo).
- Voz oficial do TTS = **Francisca**. A voz Thalita multilingual desvia para espanhol/inglês — não usar.
- Em código Windows, preferir `timezone(timedelta(hours=-3))` a `ZoneInfo("America/Sao_Paulo")` (evita dependência `tzdata`).
- O corpo das skills `.md` NÃO entra no prompt dos agentes (só o nome); a regra efetiva mora no prompt do agente/QA — editar a skill é cosmético.
- O Chrome da automação (claude-in-chrome) não carrega `<audio>`/`<video>` (readyState 0); validar som via ffprobe/curl + teste manual.
