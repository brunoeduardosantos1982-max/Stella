# Tarefa Codex — Corpo da Stella, parte 2: Daemon Telegram ↔ Claude

> Spec autocontida. Repo: `D:\VortexBrain00\stella` (Python 3.14, uv). Branch: criar `feat/corpo-daemon` a partir de master (ou da branch do gravador, se existir). Você NÃO commita. `pytest tests` integral ao final.

## Contexto

O Bruno quer conversar com a "Stella" pelo Telegram de qualquer lugar. A Stella-cérebro é o Claude Code CLI (`claude`) instalado nesta máquina. O daemon: lê mensagens do bot do Telegram → executa o Claude Code em modo headless → devolve a resposta no chat. SOMENTE o chat do Bruno pode comandar.

## Constantes do ambiente

- Cofre: `D:\VortexBrain00\.secrets\telegram.json` → `{"bot_token": "...", "chat_id": "..."}` (chat_id é o ÚNICO autorizado)
- Diretório de trabalho do Claude: `D:\VortexBrain00` (de lá ele enxerga vault e projetos)
- Binário: `claude` (no PATH). Invocação headless: `claude -p "<prompt>" --output-format text` (executar com `cwd=D:\VortexBrain00`)
- Estado do daemon: `D:\VortexBrain00\.secrets\daemon_state.json` (guarda `last_update_id`)
- Log: `D:\VortexBrain00\.secrets\daemon.log` (rotacionar manualmente não é necessário; append)

## Entrega 1 — `stella/corpo/daemon_telegram.py`

1. **Long-polling**: loop `GET https://api.telegram.org/bot{token}/getUpdates?offset={last+1}&timeout=50`. Persistir `last_update_id` no state file após processar cada update (at-least-once é aceitável; at-most-once é preferível: persistir ANTES de executar).
2. **Filtro de segurança**: processar SOMENTE `message.chat.id == chat_id` do cofre. Updates de outros chats: registrar em log (`chat_id` apenas) e ignorar SILENCIOSAMENTE (não responder).
3. **Execução**: para cada mensagem de texto:
   - Reagir rápido: `sendChatAction typing` e mensagem curta `⏳ Trabalhando nisso...` se a execução passar de 5s (opcional, se simples).
   - `subprocess.run(["claude", "-p", texto, "--output-format", "text"], cwd=..., timeout=600, capture_output=True, text=True, encoding="utf-8")`.
   - Sucesso: enviar stdout. Vazio → "Concluído, sem saída de texto.". Timeout → avisar. Erro → enviar resumo do stderr (máx 500 chars).
4. **Envio**: `sendMessage` SEM parse_mode (texto cru; respostas do Claude têm Markdown que o parse HTML quebraria). Quebrar em pedaços de no máximo 4000 chars (limite do Telegram é 4096), partindo preferencialmente em quebras de linha.
5. **Comandos especiais** (interceptados antes do Claude):
   - `/ping` → responde `Stella online_` + timestamp
   - `/status` → responde uptime do daemon + última execução
6. **Robustez**: exceção em um update não derruba o loop (log + continua); falha de rede → sleep 10s e retry; `KeyboardInterrupt` encerra limpo.

## Entrega 2 — comando CLI

Em `stella/frontends/cli.py`: comando `stella daemon` que inicia o loop (mensagem de boot em tom Jarvis: "Senhor, estou de ouvidos abertos no Telegram."). Sem opções na v1.

## Entrega 3 — testes (`tests/corpo/test_daemon.py`)

Sem rede real (mockar `requests`/`urllib` ou injetar transport):
- Update de chat NÃO autorizado é ignorado (nenhum sendMessage).
- Mensagem autorizada dispara subprocess com os argumentos corretos e envia stdout.
- Resposta longa é fatiada em pedaços ≤4000 chars.
- `/ping` responde sem chamar subprocess.

## Restrições

- Usar apenas stdlib + dependências JÁ presentes no repo (httpx/requests: verifique o que o repo já tem; se nenhum, stdlib `urllib.request`).
- Sem travessão (—) em strings ao usuário.
- Segurança: NUNCA logar o token; NUNCA executar mensagens de chat_id diferente; não usar shell=True.
- Type hints estritos; pre-commit/ruff limpos; suite inteira passando.

## Critérios de aceite
1. `stella daemon` sobe, responde `/ping` no chat do Bruno.
2. Mensagem comum vira execução do `claude -p` e a resposta volta fatiada.
3. Chat estranho não recebe NADA.
4. Testes novos + suite (557+) passando.
