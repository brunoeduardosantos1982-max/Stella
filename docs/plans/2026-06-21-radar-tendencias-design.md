# Spec — Radar de Tendências da Stella

> Design aprovado por Bruno em 2026-06-21. Próximo passo: plano de implementação (writing-plans).

## Objetivo

Toda vez que o radar dispara, a Stella busca as notícias mais frescas e quentes nos nichos do Bruno, escolhe as melhores, escreve resumo e gancho de post em português e manda um card no Telegram. O Bruno usa esses ganchos como matéria-prima para postar ao longo do dia.

## Decisões do Bruno (fixas)

| Item | Decisão |
|------|---------|
| Cadência | 3 drops/dia, **todos os dias**: 6h, 14h, 19h |
| Quantidade por drop | **5 / 3 / 3** (6h=5, 14h=3, 19h=3) |
| Formato de cada item | título · link + veículo da fonte (obrigatório) · resumo curto PT · gancho de post PT |
| Seleção | os mais frescos/quentes no geral (recência manda), sem cota fixa de variedade |
| Fontes | internacionais de preferência (sair na frente), entregue em PT |
| Motor | **híbrido A+B**: Tavily (busca de notícia) + lista curada de fontes, curadoria por Claude |
| Canal | Telegram, bot único @Stella_brunoe_bot |

## Temas (queries de busca)

Nichos (4): marketing, IA, tecnologia, publicidade.
Subnichos (6): personal brand, viagens, negócios, marketing digital, performance, criação de conteúdo.

São 10 temas usados para montar as queries de busca. A seleção final NÃO reserva cota por tema — junta todos os candidatos e escolhe os 5/3/3 mais quentes.

## Arquitetura

Espelha o padrão do `stella/corpo/seguranca.py` (tarefa determinística que monta um relatório e envia card no Telegram).

- **CLI:** novo comando `stella radar` em `stella/frontends/cli.py`. Aceita `--n` (quantidade de artigos do drop, default 5). Cada gatilho da tarefa agendada passa o `--n` explícito (6h=5, 14h=3, 19h=3).
- **Corpo:** `stella/corpo/radar.py` — orquestra busca → dedup → curadoria → card → envio → persistência.
- **Agendamento:** tarefa Windows **"Stella Radar"** com 3 gatilhos diários (6:00, 14:00, 19:00), rodando **oculta** via `stella-run-hidden.vbs` → `stella-radar.ps1` → `uv run stella radar --n <5|3|3>`. (Mesmo mecanismo anti-flash já aplicado às tarefas existentes — ver [[reference_stella_tasks_hidden]].)

## Componentes (unidades isoladas)

### 1. `RadarConfig`
- O que faz: guarda temas, allowlist de fontes, janela de recência, idioma de preferência, quantidade por drop.
- Entrada/saída: lido de constantes do módulo + `.env` (chaves) + (opcional) um arquivo de config no vault.
- Depende de: nada.

### 2. Buscador de candidatos (híbrido A+B)
- O que faz: monta a lista bruta de candidatos `{titulo, url, veiculo, data, snippet, tema}`.
  - **A (Tavily):** estende o `TavilyClient` para usar modo notícia e janela de dias (`topic="news"`, `days=1..2`). Uma query por tema (ou queries agrupadas), preferência por fontes internacionais.
  - **B (allowlist curada):** enviesa/filtra a favor de veículos confiáveis (lista-semente abaixo). Implementação: passar os domínios preferidos para o Tavily (`include_domains`) e/ou priorizar candidatos cujo domínio está na allowlist na hora de ranquear.
- Saída: lista agregada e deduplicada por URL.
- Depende de: `TavilyClient` (estendido), `RadarConfig`.

Lista-semente de fontes (ajustável):
- Marketing / publicidade / mkt digital: Marketing Dive, Search Engine Land, Search Engine Journal, Adweek, Social Media Today, Content Marketing Institute, HubSpot Blog.
- IA / tecnologia: TechCrunch, The Verge, Ars Technica, VentureBeat, MIT Technology Review, The Rundown AI.
- Personal brand / criação de conteúdo: Buffer Blog, Later Blog, Creator Economy.
- Negócios / performance: Harvard Business Review, Fast Company, First Round Review.
- Viagens: Skift, Travel + Leisure.

### 3. Anti-repetição (seen-log)
- O que faz: impede repetir artigo já enviado em drops anteriores ou nos últimos ~7 dias.
- Estado: `D:/VortexBrain00/.secrets/radar_seen.json` — lista de `{url, titulo, enviado_em}`, podada por idade (janela configurável, default 7 dias).
- Fluxo: remove dos candidatos qualquer URL/título já visto; grava os enviados ao final.
- Depende de: filesystem (portalocker, como os outros estados).

### 4. Curador (Claude)
- O que faz: dos candidatos novos, escolhe os top N (5/3/3) por frescor + relevância + potencial de post; escreve para cada um resumo PT (1-2 linhas) e gancho PT no posicionamento do Bruno (marketing com IA, com toque lifestyle quando couber), preservando link + veículo. Sem travessão ([[feedback_evitar_travessao]]).
- Entrada: candidatos `{titulo, url, veiculo, data, snippet, tema}` + N.
- Saída: lista de ≤N itens `{titulo, url, veiculo, resumo, gancho}`.
- Depende de: adapter LLM (Anthropic, chave já configurada), respeitando o `usage_tracker` existente.

### 5. Card do Telegram
- O que faz: monta o HTML do card e envia via `send_message` no bot único.
- Formato: cabeçalho `📰 RADAR <06h|14h|19h> · DD/MM`, itens numerados com título, fonte (link + veículo), resumo e `💡 Gancho:`.
- Depende de: helper de Telegram existente (`stella/corpo/daemon_telegram.py` / `lembretes.py`).

### 6. Histórico no vault (opcional, aprovado)
- O que faz: salva cada drop em `bssurf00/C04 Claude Obsidian/.../radar/AAAA-MM-DD.md` (append por drop), virando insumo de pauta e base futura de detecção de tendências.
- Zona autônoma da Stella (C04), pode escrever sozinha.

## Fluxo de dados

```
gatilho (6/14/19h, --n)
  → carrega RadarConfig + seen-log
  → Buscador (Tavily news + allowlist) → candidatos
  → remove vistos (seen-log)
  → Curador (Claude) → top N com resumo + gancho
  → monta card HTML
  → envia Telegram (bot único)
  → grava enviados no seen-log
  → (opcional) salva drop no vault
  → log em arquivo (stella-radar-tick.log)
```

## Erros e robustez

- Tavily ou Claude falham → retry curto; persistindo, envia **card degradado** (links crus + nota "curadoria indisponível neste drop") + sinaliza no log. Nunca falha em silêncio.
- Sem candidatos novos após dedup → envia "Sem novidade quente neste drop" em vez de repetir artigo velho.
- Encoding UTF-8 (padrão dos scripts `.ps1`). Texto público sem travessão.
- Respeita teto de custo via `usage_tracker`.

## Teste

- Unitários (marker não-live, Tavily e Claude fakeados):
  - dedup remove candidatos já no seen-log;
  - curador devolve no máximo N itens;
  - card bem formado e sem travessão;
  - caminho degradado quando o LLM falha;
  - mensagem de "sem novidade" quando candidatos novos = 0.
- 1 teste live opt-in (chama Tavily + Claude reais) marcado `live`.

## Contribuição à visão ecossistema

1. **Avança Detecção de tendências (#5)** diretamente; semeia Geração de oportunidades (#8) e Trabalho em tempo livre (#6 — vasculha enquanto o Bruno dorme/trabalha).
2. **Hooks de extensibilidade:** seen-log + histórico de drops no vault viram base para uma futura camada de tendências (o que esquenta ao longo do tempo) e para ligar com a fábrica de conteúdo (gancho → pauta → post agendado).
3. Nenhum item da visão fica mais difícil depois deste plano.
4. Stella fica **mais proativa e curiosa**. Bandeira verde.

## Replicabilidade (ferramenta da Gama + material)

O "Radar de tendências" é replicável para qualquer cliente/marca trocando os temas e a allowlist. Rende conteúdo de bastidor ("montei um agente que me manda oportunidades de post 3x/dia"). Registrar no playbook técnico quando implementado ([[feedback_dev_vira_ferramenta_e_material]]).

## Fora de escopo (YAGNI por enquanto)

- Geração de post completo pronto (ficou no gancho, decisão do Bruno).
- Cota fixa de variedade por tema.
- Painel/UI: a entrega é o card do Telegram.
- Detecção de tendências de longo prazo (é hook futuro, não este plano).
