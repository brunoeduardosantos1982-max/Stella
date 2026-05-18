# `stella.framework` — Framework Multi-Agente

Framework para construir agentes especialistas e coordenadores que rodam dentro da Stella (assistente pessoal do Bruno).

**Visão completa:** ver Design do Sub-projeto A em `bssurf00/C04 Claude Obsidian/projetos e specs/Sistema Multi-Agente/2026-05-16 — Sub-projeto A — Framework Base — Design.md`.

**Norte do ecossistema:** [[project-stella-ecossistema-visao]] — Stella não é assistente reativo, é ecossistema cognitivo autônomo com 8 capacidades.

## Por onde começar

### Criar um agente novo em 5 min

```powershell
.\.venv\Scripts\Activate.ps1
stella agent new agente_seo --setor marketing --tipo especialista
```

Cria 3 arquivos em `stella/agents/agente_seo/`:
- `__init__.py` — exporta `Agent` (a classe concreta)
- `agent.py` — classe `Agent(BaseAgent)` com `execute()` stub
- `manifest.yaml` — template com `nome`, `tipo`, `setor`, `vault_scope`, etc

Edite `manifest.yaml` (descrição, capacidades) e `agent.py` (`execute`), depois:

```powershell
stella agent list                # confirma que aparece no registry
stella agent show agente_seo     # mostra manifest completo
pytest tests/                    # roda toda a suite
```

## Componentes principais

### Tipos centrais (FB-M1)
- **`Agent`** — ABC. Subclasses implementam `execute(input) -> AgentOutput`.
- **`AgentOutput`** — dataclass de retorno (`resultado`, `sucesso`, `mensagens`, `custo_estimado_usd`).
- **`AgentManifest`** — pydantic. Schema parseado de `manifest.yaml`.
- **`AgentClient` (ABC)** + `InProcessClient` + `HttpAgentClient` — abstrai execução local vs HTTP.
- **`FrameworkError`** + 10 subclasses — hierarquia de erros.

### Resolução (FB-M2)
- **`AgentRegistry(agents_dir)`** — descobre `agents/*/manifest.yaml` no scan.
- **`SkillsRegistry(skills_dir)`** — indexa skills `.md` em `prompts/skills/`.
- **`MCPRegistry()`** — in-memory, expõe `list_by_category` (hook Sub-projeto F).
- **`RAGRegistry()`** — stub para corpora RAG.
- **`FrameworkDeps`** + **`build_agent(manifest, deps)`** — DI completa via `importlib`.

### Hooks de extensibilidade (FB-M2 — interfaces vazias)
- **`BackgroundScheduler`** + `IdleTask` (Sub-projeto E)
- **`SkillEditor`** (Sub-projeto G)
- **`Sandbox`** (Sub-projeto G)
- **`VaultRepository.scan_recursive`** (Sub-projeto H)
- **`MCPRegistry.list_by_category`** (Sub-projeto F)

### Qualidade (FB-M3)
- **`QualityReviewer`** + **`ReviewResult`** + **`ReviewPolicy`** — Stella revisa output via LLM.
- **`FeedbackLogger`** — Stella anota correções do Bruno em `C04/Padrões/_aprendizados.md`.

### Segurança (FB-M2)
- **`ScopedVaultRepository`** — wrapping com `PermissionError` em paths fora do glob.
- `build_agent` injeta `vault.scoped(manifest.vault_scope)` automaticamente.

### Testing (FB-M3)
- `stella.framework.testing.fakes` — `FakeVault`, `FakeLLM`, `FakeMCP`, `FakeRAG`, `FakeTracker`, `FakeLogger`.
- `stella.framework.testing.deps.make_fake_deps(...)` — helper de uma chamada.

## Inicialização típica (Stella na startup)

```python
from pathlib import Path

from stella.adapters.llm.router import LLMRouter
from stella.adapters.vault.obsidian_vault import ObsidianVaultRepository
from stella.framework import (
    AgentRegistry, FrameworkDeps, MCPRegistry, RAGRegistry, SkillsRegistry,
    build_agent,
)

vault = ObsidianVaultRepository(Path("D:/VortexBrain00/bssurf00"))
llm = LLMRouter(gemma=..., anthropic=..., default="gemma")

skills_reg = SkillsRegistry(Path("stella/prompts/skills"))
mcp_reg = MCPRegistry()
rag_reg = RAGRegistry()
registry = AgentRegistry(Path("stella/agents"))

deps = FrameworkDeps(
    vault=vault, llm=llm, skills_reg=skills_reg, mcp_reg=mcp_reg,
    rag_reg=rag_reg, tracker=None, logger=None, registry=registry,
)
# Quebra ciclo Registry <-> Builder
registry.bind_builder(lambda m: build_agent(m, deps))

# Agora qualquer get() funciona:
client = registry.get("agente_seo")
out = client.execute({"site": "exemplo.com"})
```

## Testando um agente

```python
from stella.framework.testing.deps import make_fake_deps

def test_meu_agente(tmp_path):
    deps = make_fake_deps(
        agents_dir=tmp_path / "agents",
        llm_responses=["resposta fake do LLM"],
        vault_notes={"A00 Inbox/x.md": ("conteudo", {"tipo": "ideia"})},
    )
    # ... use deps no agente
```

## Revisão de qualidade

```python
from stella.framework import QualityReviewer, ReviewPolicy

reviewer = QualityReviewer(
    llm=deps.llm, vault=deps.vault, skills_reg=deps.skills_reg,
    policy=ReviewPolicy(),
)
out = client.execute(input)
review = reviewer.review(input, out, agent_manifest=client.manifest())
if review.veredicto == "refazer":
    out = client.execute(input)  # caller refaz
    review = reviewer.review(input, out, agent_manifest=client.manifest(), tentativa=2)
# review.avisos_para_bruno passa pra UI em tom Jarvis
```

## Estado dos milestones

- **FB-M1** (Tipos base + Contratos) — ✅ merged em master
- **FB-M2** (Registries + Builder + Hooks + vault.scoped) — ✅ merged em master
- **FB-M3** (Quality + Fixtures + CLI + README) — ✅ merged em master
- **FB-M4** (Polimento + Integração Real) — ✅ Sub-projeto A 100% fechado em produção
- **Próximo:** Sub-projeto B — 1º agente piloto

### FB-M4 — o que mudou
- **Stella usa o framework de verdade.** `build_stella(config)` agora monta AgentRegistry, QualityReviewer, FeedbackLogger e chama bind_builder automaticamente.
- **Smoke test E2E** com Anthropic API real (`pytest -m live tests/e2e/`).
- **UsageTracker integrado** via `TrackerProtocol` — custo de tokens dos agentes é tracked.
- **Cross-agent loop detection** via `contextvars.ContextVar` — loop A→B→A→B é detectado.
- **`validate_manifest_resources`** loga warnings sobre skills/MCPs/RAG faltando no startup.
- **`OpusProvider` real** — `LLMRouter.with_minimum(OPUS)` retorna Opus quando configurado (era fallback Sonnet).
- **`RAGClient` ABC** — contrato definido (implementação concreta em Sub-projetos F/H).
- **CLI `stella agent show --resolve`** — mostra `✓/✗` por skill declarada.

## Limitações conhecidas (pós FB-M4)

- `RAGRegistry` aceita registros via `RAGClient` ABC, mas **não há cliente concreto** — corpora reais entram com Sub-projetos F/H.
- `BackgroundScheduler`/`SkillEditor`/`Sandbox` são ABCs vazias — implementações concretas vêm nos Sub-projetos E e G.
- `BudgetExceededError` no handler `_traduzir_erro_jarvis` traduz a mensagem mas o pause real só virá quando a Stella tiver orquestração própria de execução de agentes (Sub-projeto B).
- `_smoke_` e `_smoke_critico_` são agentes internos (sinalizados por `_underscore_`); não rodam em produção.

### Limitações fechadas em FB-M4
- ~~`OPUS` escala para Sonnet~~ → fechado: slot `opus` no LLMRouter aceita provider dedicado.
- ~~`delegate_to` cross-agent loop não detectado~~ → fechado: `ContextVar` rastreia depth entre agentes.
- ~~`UsageTracker` não integrado ao framework~~ → fechado: `TrackerProtocol`.
