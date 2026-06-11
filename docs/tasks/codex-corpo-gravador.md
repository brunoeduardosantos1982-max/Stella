# Tarefa Codex — Corpo da Stella, parte 1: Gravador de Reuniões

> Spec autocontida. Repo: `D:\VortexBrain00\stella` (Python 3.14, uv, arquitetura hexagonal — ver `stella/framework/README.md`). Branch: criar `feat/corpo-gravador` a partir de master. Você NÃO commita: deixe os arquivos prontos no working tree. Rode `pytest tests` ao final.

## Contexto

Bruno grava reuniões com clientes (consultoria). O fluxo desejado: ele solta o arquivo de áudio/vídeo numa pasta → o gravador transcreve (PT-BR) → salva a transcrição no vault Obsidian → gera um resumo via LLM → envia o resumo no Telegram dele.

## Constantes do ambiente

- Pasta vigiada (criar se não existir): `D:\VortexBrain00\gravacoes` (FORA do vault; áudios são grandes)
- Vault: `D:\VortexBrain00\bssurf00` — transcrições vão em `C04 Claude Obsidian/reunioes/` (zona de escrita autônoma)
- Cofre Telegram: `D:\VortexBrain00\.secrets\telegram.json` → `{"bot_token": "...", "chat_id": "..."}`
- LLM: usar o adapter EXISTENTE `stella/adapters/llm/anthropic_provider.py` (já configurado via `.env` `ANTHROPIC_API_KEY`); modelo padrão do provider.

## Entrega 1 — dependência

`uv add faster-whisper` (transcrição local; usa CTranslate2, modelo `small` multilíngue por padrão, `device="cpu", compute_type="int8"`). Não adicionar nenhuma outra dependência.

## Entrega 2 — `stella/corpo/__init__.py` + `stella/corpo/gravador.py`

Módulo novo `stella.corpo`. Em `gravador.py`:

1. `transcrever(caminho: Path) -> str` — usa faster-whisper (`language="pt"`, `vad_filter=True`); concatena segmentos com timestamps a cada ~30s no formato `[mm:ss]`.
2. `resumir(transcricao: str, llm) -> str` — prompt em PT-BR pedindo: (a) resumo executivo em 5-8 linhas, (b) decisões tomadas, (c) ações combinadas (quem/o quê), (d) 3-5 citações literais relevantes do cliente. Saída em Markdown SEM travessão (—).
3. `salvar_no_vault(nome_base, transcricao, resumo, vault_dir) -> Path` — escreve `C04 Claude Obsidian/reunioes/AAAA-MM-DD-<nome_base>.md` com frontmatter (`tipo: reuniao`, `origem: gravador`, `criado-em`) + seção `## Resumo` + `## Transcrição completa`. Encoding UTF-8.
4. `avisar_telegram(resumo, nota_path, cofre_path)` — POST `https://api.telegram.org/bot{token}/sendMessage`, `parse_mode: "HTML"`, texto: `<b>🎙 Reunião transcrita</b>` + resumo (truncar em ~3500 chars) + nome da nota. Falha de Telegram NÃO derruba o fluxo (log e segue).
5. `processar_pasta(pasta, vault_dir, cofre_path, llm)` — varre a pasta por `.mp3/.m4a/.wav/.mp4/.ogg`; para cada arquivo NOVO (sem `.feito` marker): transcreve → resume → salva → avisa → cria `<arquivo>.feito` (marker vazio) ao lado. Erros num arquivo não derrubam os demais (log + segue).
6. Modo vigia: loop com `time.sleep(60)` chamando `processar_pasta` (sem watchdog; polling simples).

## Entrega 3 — comando CLI

Em `stella/frontends/cli.py`, adicionar comando `gravador`:
- `stella gravador` → processa a pasta uma vez e sai.
- `stella gravador --watch` → modo vigia (loop).
- Montar o LLM via o builder existente da Stella (`build_stella` expõe o necessário; se não, instanciar AnthropicProvider direto da config). Mensagens de saída em tom Jarvis como os outros comandos.

## Entrega 4 — testes

`tests/corpo/test_gravador.py` com fakes (sem rede, sem whisper real):
- `salvar_no_vault` escreve nota com frontmatter correto (usar FakeVault de `stella/framework/testing/fakes.py` OU tmp_path direto).
- `processar_pasta` ignora arquivos com `.feito` e cria o marker após sucesso (mockar transcrever/resumir/avisar).
- `resumir` monta o prompt e retorna o texto do FakeLLM.

## Restrições

- Sem travessão (—) em strings voltadas ao usuário.
- Sem dados do cliente em logs (logar nomes de arquivo, nunca conteúdo).
- Type hints estritos; passar no ruff/mypy se o repo cobra (pre-commit existe).
- `pytest tests` integral passando ao final (suite atual: 557).

## Critérios de aceite
1. `stella gravador` com pasta vazia: sai limpo com mensagem.
2. Arquivo de áudio processado gera nota no vault + marker `.feito` + tentativa de Telegram.
3. Testes novos passam; suite inteira passa.
