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
- **Geradores de conteúdo têm dono e são separados** (`stella/corpo/geradores.py`, 2026-09-28). O modo conteúdo do daemon (`PERSONA_CONTEUDO`, gatilho `script|roteiro|reels?|pauta|conteúdo`) é SÓ do @brunoe.santos; antes da separação, pedido de outro canal caía nele em Opus, com persona, sessão sticky e pasta de saída erradas. Agora o gerador com nome é roteado em `process_update` ANTES do chat: não chama `claude -p` do chat e não toca em `SESSION_STATE` nem `CONTEUDO_STATE`. Hoje: `brujosie` (mensagem com "brujosie", "bru josie" ou "@brujosie.preparados") dispara `bssurf00/B01 Projetos/brujosie-preparados/pipeline/rotina-pauta.ps1 -Tema ... [-Data AAAA-MM-DD]`, que escreve roteiro e copy em `pautas/` e avisa no Telegram. Exemplos: `brujosie engasgo`, `pauta brujosie: choque elétrico amanhã`, `brujosie afogamento 02/10`. **Gerador novo = entrada nova em `rotear_gerador` + handler em `responder_gerador` + teste.** Nunca ampliar o regex do modo conteúdo para outra marca.

## Pegadinhas

- **Teste que chama `process_update` sem `log_path` grava no `daemon.log` de PRODUÇÃO** (`_append_log` usa `DAEMON_LOG` por padrão): dois `OSError` de teste apareceram como falha real do gerador em 2026-09-28. Sempre passar `log_path=tmp_path / "daemon.log"`.
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
- **O Radar de Tendências ficou mudo de 2026-07-01 a 2026-10-01** (213 falhas). A causa não era HTML: a conta da API da Anthropic ficou sem crédito, a curadoria caía, o card degradado levava o trecho bruto de cada notícia e passava de 4096 caracteres, e o Telegram devolvia `400 message is too long`. Hoje `montar_card` nunca passa de `TELEGRAM_LIMITE`, o card avisa quando a curadoria cai e o `stella-radar.ps1` avisa no Telegram se o comando falhar. **`400` do Telegram com cofre bom: leia o `description` da resposta antes de suspeitar do conteúdo.**
- **Crédito da API Anthropic acabou de novo em 2026-10-01 e a chave NVIDIA (Gemma) está revogada (403).** Desde 2026-11-17, Radar e Bolsa usam `ProvedorComReserva([AnthropicProvider, ClaudeCliProvider])` (`stella/adapters/llm/claude_cli.py`): se a API falha, cai no `claude -p` da assinatura do Claude Code. O prompt vai pela **stdin** (o shim `claude.cmd` corta argumento longo). Agente novo que precisa de LLM sem custo de API: usar o mesmo padrão. Os agentes de conteúdo (copywriter/designer) ainda usam só a API.
- **`StellaConfig` lê o `.env` relativo ao diretório atual.** Rodado fora de `stella/`, todo comando falha com `validation errors for StellaConfig`. As tarefas agendadas não definem pasta de início: o `.ps1` tem de fixá-la (`Set-Location` ou `-WorkingDirectory`). Foi o que derrubou o Radar da Bolsa de 15/09 a 30/09.
- **Não despejar stderr de `httpx` em log.** A mensagem de exceção carrega a URL inteira da API, com o token dentro: o `stella-radar.log` acumulou 161 cópias do token do bot por causa disso. O `stella-bolsa.ps1` mostra o padrão certo — redigir `bot\d+:[A-Za-z0-9_\-]+` antes de gravar.
- **`$proc.ExitCode` de `Start-Process -PassThru` vem VAZIO no PowerShell** se ninguém leu `$proc.Handle` antes de o processo terminar; nem `WaitForExit()` resolve. Ler `$null = $proc.Handle` logo depois do `Start-Process` e tratar código vazio como falha. O `stella-bolsa.ps1` convertia o vazio em 0 e registrou 11 pregões quebrados como sucesso, sem aviso.
- O Chrome da automação (claude-in-chrome) não carrega `<audio>`/`<video>` (readyState 0); validar som via ffprobe/curl + teste manual.
