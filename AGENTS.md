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
- **`Stop-ScheduledTask` NÃO derruba o daemon:** o lançador solta o processo, a tarefa volta a `Ready` e o python continua vivo com o código velho. Para reiniciar de verdade, matar o processo (`Stop-Process`) e depois `Start-ScheduledTask`.
- **O daemon aparece como DOIS processos python, e isso é normal:** o segundo é filho do primeiro (par do atalho de console `stella.exe`). Confirmar com `ParentProcessId` antes de achar que há daemon duplicado brigando pelo mesmo bot.
- **Tarefa agendada não tem controle sobre o que ela dispara.** O lançador compartilhado `stella-run-hidden.vbs` (raiz do workspace) usa `sh.Run(..., 0, False)` — não espera. O `wscript` morre na hora, a tarefa volta a `Ready` com `rc=0` em menos de 1s, e o processo real fica órfão: `ExecutionTimeLimit` e `MultipleInstances: IgnoreNew` da tarefa **nunca chegam a valer**. Toda proteção tem que estar DENTRO do `.ps1`. Mordeu em 30/07/2026: `Stella Lembretes Tick` (gatilho de 1 em 1 minuto) empilhou 168 processos órfãos segurando 879 MB. O `stella-lembretes-tick.ps1` agora tem lock com PID + limite próprio de 4 min, e chama `.venv\Scripts\stella.exe` direto em vez de `uv run` (ticks concorrentes travavam no lock do venv do uv). **Consequência:** o tick não sincroniza mais dependências — depois de mexer no `pyproject.toml`, rodar `uv sync` na mão.
- **Mídia recebida pelo Telegram** (vídeo/foto/documento) cai em `D:\VortexBrain00\_entrada-midia\`, roteada pela legenda: contém "story" vai para `stories/`, o resto para `reels/`. Áudio e voz continuam indo para a transcrição, de propósito.
- Voz oficial do TTS = **Francisca**. A voz Thalita multilingual desvia para espanhol/inglês — não usar.
- Em código Windows, preferir `timezone(timedelta(hours=-3))` a `ZoneInfo("America/Sao_Paulo")` (evita dependência `tzdata`).
- O corpo das skills `.md` NÃO entra no prompt dos agentes (só o nome); a regra efetiva mora no prompt do agente/QA — editar a skill é cosmético.
- **A API de gráfico do Yahoo bloqueia pelo `User-Agent` e MENTE no erro.** Com o agente padrão do httpx a resposta é o texto `Edge: Too Many Requests`, que parece limite de taxa e não é; com `User-Agent: Mozilla/5.0 (...)` responde 200 no mesmo segundo. Os campos de dia do `meta` (`regularMarketDayHigh/Low/Volume`) vêm **zerados**: ler máxima, mínima e volume só dos vetores de candle. Usado por `stella/corpo/bolsa/coletor.py`.
- **`ruff` e `mypy` NÃO estão instalados no `.venv`**, apesar de declarados como extra `dev` no `pyproject.toml`. Rodar os binários globais (`ruff check ...`, `mypy ...`), não `python -m ruff`.
- **O Radar de Tendências (`stella/corpo/radar.py`) está quebrado desde 2026-07-01:** 162 falhas em 195 execuções, com `400 Bad Request` do Telegram em toda rodada. O cofre está bom (mensagem simples devolve 200), então o defeito é do HTML que ele monta. **Não confundir com falha de credencial.**
- **Não despejar stderr de `httpx` em log.** A mensagem de exceção carrega a URL inteira da API, com o token dentro: o `stella-radar.log` acumulou 161 cópias do token do bot por causa disso. O `stella-bolsa.ps1` mostra o padrão certo — redigir `bot\d+:[A-Za-z0-9_\-]+` antes de gravar.
- **`$proc.ExitCode` vem VAZIO depois de `WaitForExit(ms)` no PowerShell.** Só `WaitForExit()` sem argumento libera o valor. Sem isso, um `.ps1` que avisa falha por exit code manda **alarme falso** depois de execução bem-sucedida.
- O Chrome da automação (claude-in-chrome) não carrega `<audio>`/`<video>` (readyState 0); validar som via ffprobe/curl + teste manual.
