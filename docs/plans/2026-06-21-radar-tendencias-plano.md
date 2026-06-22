# Radar de Tendências — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar o comando `stella radar` que, 3x/dia, busca as notícias mais frescas dos nichos do Bruno, cura os top N com Claude, e manda um card no Telegram com link, resumo e gancho de post.

**Architecture:** Módulo autocontido `stella/corpo/radar.py` no mesmo estilo de `stella/corpo/seguranca.py` (funções puras + dataclasses + httpx direto + injeção de dependências por parâmetro default para teste). Busca via função de notícias do Tavily (híbrido: `include_domains` com allowlist curada), curadoria via `AnthropicProvider`, entrega via Telegram (bot único). Anti-repetição com seen-log em JSON. Agendamento por tarefa Windows oculta (3 gatilhos).

**Tech Stack:** Python 3.11, typer (CLI), httpx, dataclasses, pydantic-settings (`StellaConfig`), Anthropic SDK (via `AnthropicProvider`), pytest.

## Global Constraints

- Python `>=3.11`. Ruff line-length 100 (E501 ignorado). Mypy `strict` (todo código novo tipado; `tests/` excluído do mypy).
- Testes default são offline: `addopts = -m 'not live'`. Chamadas reais a API só em testes marcados `@pytest.mark.live`.
- Injeção de dependência por parâmetro com default (padrão do `seguranca.py`): funções recebem `http_post`, `buscar`, `provider`, `agora` etc. com default real, e os testes passam dublês. Nunca mockar via monkeypatch global quando dá pra injetar.
- Datas/hora: usar `FUSO = timezone(timedelta(hours=-3))` e `datetime.now(FUSO)`. NÃO usar `ZoneInfo` (evita dep `tzdata` no Windows).
- Texto público (card do Telegram e arquivo no vault): **sem travessão `—`** (usar vírgula, dois-pontos ou `|`). Tudo em português.
- Segredos via `StellaConfig` (`.env`, prefixo `STELLA_`); ler valor com `.get_secret_value()`. Nunca logar segredo.
- Telegram: bot único, cofre `D:/VortexBrain00/.secrets/telegram.json` (`{"bot_token","chat_id"}`).
- Encoding UTF-8 em toda leitura/escrita de arquivo.
- Todo commit termina com os trailers `Co-Authored-By:` e `Claude-Session:` (ver CLAUDE.md). Commits frequentes (um por tarefa).

---

## File Structure

- `stella/adapters/research/tavily_client.py` — **modificar**: adicionar função module-level `buscar_noticias_tavily(...)` (modo notícia + janela de dias + include_domains). Não mexe na classe `TavilyClient` existente.
- `stella/corpo/radar.py` — **criar**: módulo autocontido do radar (models, config, busca-agregada, seen-log, curador, card, envio, persistência, orquestrador).
- `stella/frontends/cli.py` — **modificar**: registrar comando `radar`.
- `stella-radar.ps1` — **criar** (em `D:/VortexBrain00/`): wrapper que roda `uv run stella radar --n <N>` e loga.
- `tests/adapters/research/test_tavily_noticias.py` — **criar**.
- `tests/corpo/test_radar.py` — **criar**.

---

### Task 1: Busca de notícias no Tavily (modo news + allowlist)

**Files:**
- Modify: `stella/adapters/research/tavily_client.py`
- Test: `tests/adapters/research/test_tavily_noticias.py`

**Interfaces:**
- Consumes: nada novo.
- Produces:
  ```python
  def buscar_noticias_tavily(
      query: str,
      api_key: str,
      *,
      days: int = 2,
      max_results: int = 10,
      include_domains: list[str] | None = None,
      http_post: Callable[..., Any] = httpx.post,
  ) -> list[dict[str, Any]]:
      # devolve [{"titulo","url","veiculo","snippet","data"}, ...]
  ```

- [ ] **Step 1: Write the failing test**

```python
# tests/adapters/research/test_tavily_noticias.py
from typing import Any

from stella.adapters.research.tavily_client import buscar_noticias_tavily


class _RespFake:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:  # pragma: no cover - sem erro no teste
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


def test_buscar_noticias_mapeia_campos_e_extrai_veiculo() -> None:
    chamada: dict[str, Any] = {}

    def http_post_fake(url: str, **kwargs: Any) -> _RespFake:
        chamada["url"] = url
        chamada["json"] = kwargs["json"]
        return _RespFake(
            {
                "results": [
                    {
                        "title": "OpenAI lança agente",
                        "url": "https://techcrunch.com/2026/06/21/openai-agent",
                        "content": "resumo aqui",
                        "published_date": "2026-06-21",
                    }
                ]
            }
        )

    out = buscar_noticias_tavily(
        "inteligência artificial novidades",
        api_key="k",
        days=1,
        max_results=5,
        include_domains=["techcrunch.com"],
        http_post=http_post_fake,
    )

    assert chamada["json"]["topic"] == "news"
    assert chamada["json"]["days"] == 1
    assert chamada["json"]["include_domains"] == ["techcrunch.com"]
    assert out == [
        {
            "titulo": "OpenAI lança agente",
            "url": "https://techcrunch.com/2026/06/21/openai-agent",
            "veiculo": "techcrunch.com",
            "snippet": "resumo aqui",
            "data": "2026-06-21",
        }
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /d/VortexBrain00/stella && uv run pytest tests/adapters/research/test_tavily_noticias.py -v`
Expected: FAIL com `ImportError: cannot import name 'buscar_noticias_tavily'`.

- [ ] **Step 3: Write minimal implementation**

Adicionar ao fim de `stella/adapters/research/tavily_client.py` (e garantir os imports `from collections.abc import Callable` e `from urllib.parse import urlparse` no topo):

```python
def buscar_noticias_tavily(
    query: str,
    api_key: str,
    *,
    days: int = 2,
    max_results: int = 10,
    include_domains: list[str] | None = None,
    http_post: Callable[..., Any] = httpx.post,
) -> list[dict[str, Any]]:
    """Busca notícias recentes no Tavily (topic=news) e normaliza os campos.

    `include_domains` enviesa a busca para a allowlist curada (híbrido A+B).
    """
    payload: dict[str, Any] = {
        "api_key": api_key,
        "query": query,
        "topic": "news",
        "days": days,
        "max_results": max_results,
    }
    if include_domains:
        payload["include_domains"] = include_domains

    resp = http_post(_TAVILY_ENDPOINT, json=payload, timeout=_TIMEOUT_S)
    resp.raise_for_status()
    resultados = resp.json().get("results", [])
    itens: list[dict[str, Any]] = []
    for r in resultados:
        url = r.get("url", "")
        itens.append(
            {
                "titulo": r.get("title", ""),
                "url": url,
                "veiculo": urlparse(url).netloc.removeprefix("www."),
                "snippet": r.get("content", ""),
                "data": r.get("published_date", ""),
            }
        )
    return itens
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /d/VortexBrain00/stella && uv run pytest tests/adapters/research/test_tavily_noticias.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add stella/adapters/research/tavily_client.py tests/adapters/research/test_tavily_noticias.py
git commit -m "feat(radar): busca de noticias no Tavily (news + allowlist)"
```

---

### Task 2: Models, config e busca agregada de candidatos

**Files:**
- Create: `stella/corpo/radar.py`
- Test: `tests/corpo/test_radar.py`

**Interfaces:**
- Consumes: `buscar_noticias_tavily` (Task 1).
- Produces:
  ```python
  FUSO = timezone(timedelta(hours=-3))
  TEMAS: list[str]            # 10 temas (queries)
  ALLOWLIST_DOMINIOS: list[str]
  JANELA_DIAS: int = 2

  @dataclass
  class Candidato:
      titulo: str
      url: str
      veiculo: str
      snippet: str
      data: str
      tema: str

  def buscar_candidatos(
      temas: list[str] = TEMAS,
      *,
      api_key: str,
      days: int = JANELA_DIAS,
      include_domains: list[str] | None = ALLOWLIST_DOMINIOS,
      buscar: Callable[..., list[dict[str, Any]]] = buscar_noticias_tavily,
  ) -> list[Candidato]:
      ...
  ```

- [ ] **Step 1: Write the failing test**

```python
# tests/corpo/test_radar.py
from typing import Any

from stella.corpo import radar


def test_buscar_candidatos_agrega_temas_e_deduplica_por_url() -> None:
    chamadas: list[str] = []

    def buscar_fake(query: str, api_key: str, **kwargs: Any) -> list[dict[str, Any]]:
        chamadas.append(query)
        return [
            {
                "titulo": f"Artigo de {query}",
                "url": "https://x.com/a" if query == "marketing" else "https://x.com/b",
                "veiculo": "x.com",
                "snippet": "s",
                "data": "2026-06-21",
            }
        ]

    cands = radar.buscar_candidatos(
        temas=["marketing", "IA", "tecnologia"],
        api_key="k",
        buscar=buscar_fake,
    )

    # uma busca por tema
    assert chamadas == ["marketing", "IA", "tecnologia"]
    # url repetida (IA e tecnologia retornaram /b) deduplicada
    urls = sorted(c.url for c in cands)
    assert urls == ["https://x.com/a", "https://x.com/b"]
    assert all(isinstance(c, radar.Candidato) for c in cands)
    # o tema fica registrado
    assert {c.tema for c in cands} == {"marketing", "IA"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /d/VortexBrain00/stella && uv run pytest tests/corpo/test_radar.py::test_buscar_candidatos_agrega_temas_e_deduplica_por_url -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'stella.corpo.radar'`.

- [ ] **Step 3: Write minimal implementation**

```python
# stella/corpo/radar.py
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta, timezone
from typing import Any

from stella.adapters.research.tavily_client import buscar_noticias_tavily

FUSO = timezone(timedelta(hours=-3))

# 4 nichos + 6 subnichos = queries de busca
TEMAS: list[str] = [
    "marketing",
    "inteligência artificial",
    "tecnologia",
    "publicidade",
    "personal branding",
    "viagens",
    "negócios",
    "marketing digital",
    "performance marketing",
    "criação de conteúdo",
]

# Allowlist curada (híbrido A+B). Ajustável.
ALLOWLIST_DOMINIOS: list[str] = [
    "techcrunch.com",
    "theverge.com",
    "arstechnica.com",
    "venturebeat.com",
    "technologyreview.com",
    "searchengineland.com",
    "searchenginejournal.com",
    "marketingdive.com",
    "adweek.com",
    "socialmediatoday.com",
    "contentmarketinginstitute.com",
    "blog.hubspot.com",
    "buffer.com",
    "hbr.org",
    "fastcompany.com",
    "skift.com",
]

JANELA_DIAS = 2


@dataclass
class Candidato:
    titulo: str
    url: str
    veiculo: str
    snippet: str
    data: str
    tema: str


def buscar_candidatos(
    temas: list[str] = TEMAS,
    *,
    api_key: str,
    days: int = JANELA_DIAS,
    include_domains: list[str] | None = ALLOWLIST_DOMINIOS,
    buscar: Callable[..., list[dict[str, Any]]] = buscar_noticias_tavily,
) -> list[Candidato]:
    """Busca notícias por tema, agrega e deduplica por URL."""
    vistos: set[str] = set()
    candidatos: list[Candidato] = []
    for tema in temas:
        try:
            brutos = buscar(tema, api_key=api_key, days=days, include_domains=include_domains)
        except Exception:
            continue  # um tema que falha não derruba os outros
        for r in brutos:
            url = r.get("url", "")
            if not url or url in vistos:
                continue
            vistos.add(url)
            candidatos.append(
                Candidato(
                    titulo=r.get("titulo", ""),
                    url=url,
                    veiculo=r.get("veiculo", ""),
                    snippet=r.get("snippet", ""),
                    data=r.get("data", ""),
                    tema=tema,
                )
            )
    return candidatos
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /d/VortexBrain00/stella && uv run pytest tests/corpo/test_radar.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add stella/corpo/radar.py tests/corpo/test_radar.py
git commit -m "feat(radar): models, temas/allowlist e busca agregada de candidatos"
```

---

### Task 3: Anti-repetição (seen-log)

**Files:**
- Modify: `stella/corpo/radar.py`
- Test: `tests/corpo/test_radar.py`

**Interfaces:**
- Consumes: `Candidato` (Task 2).
- Produces:
  ```python
  SEEN_PATH: Path
  JANELA_SEEN_DIAS: int = 7

  def carregar_seen(path: Path = SEEN_PATH) -> list[dict[str, str]]: ...
  def podar_seen(seen: list[dict[str, str]], janela_dias: int = JANELA_SEEN_DIAS,
                 agora: datetime | None = None) -> list[dict[str, str]]: ...
  def filtrar_novos(candidatos: list[Candidato], seen: list[dict[str, str]]) -> list[Candidato]: ...
  def gravar_seen(seen: list[dict[str, str]], urls: list[str], path: Path = SEEN_PATH,
                  agora: datetime | None = None) -> None: ...
  ```

- [ ] **Step 1: Write the failing test**

```python
# adicionar em tests/corpo/test_radar.py
import json
from datetime import datetime
from pathlib import Path

from stella.corpo import radar


def _cand(url: str) -> radar.Candidato:
    return radar.Candidato(titulo="t", url=url, veiculo="v", snippet="s", data="d", tema="IA")


def test_filtrar_novos_remove_urls_ja_vistas() -> None:
    seen = [{"url": "https://x.com/velho", "enviado_em": "2026-06-20T10:00:00-03:00"}]
    cands = [_cand("https://x.com/velho"), _cand("https://x.com/novo")]
    novos = radar.filtrar_novos(cands, seen)
    assert [c.url for c in novos] == ["https://x.com/novo"]


def test_podar_seen_descarta_entradas_antigas() -> None:
    agora = datetime(2026, 6, 21, 12, 0, tzinfo=radar.FUSO)
    seen = [
        {"url": "a", "enviado_em": "2026-06-20T12:00:00-03:00"},  # 1 dia: fica
        {"url": "b", "enviado_em": "2026-06-01T12:00:00-03:00"},  # 20 dias: sai
    ]
    podado = radar.podar_seen(seen, janela_dias=7, agora=agora)
    assert [s["url"] for s in podado] == ["a"]


def test_gravar_seen_anexa_urls_com_timestamp(tmp_path: Path) -> None:
    p = tmp_path / "seen.json"
    agora = datetime(2026, 6, 21, 6, 0, tzinfo=radar.FUSO)
    radar.gravar_seen([], ["https://x.com/novo"], path=p, agora=agora)
    dados = json.loads(p.read_text(encoding="utf-8"))
    assert dados[0]["url"] == "https://x.com/novo"
    assert dados[0]["enviado_em"].startswith("2026-06-21T06:00")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /d/VortexBrain00/stella && uv run pytest tests/corpo/test_radar.py -k "seen or novos" -v`
Expected: FAIL com `AttributeError: module 'stella.corpo.radar' has no attribute 'filtrar_novos'`.

- [ ] **Step 3: Write minimal implementation**

Adicionar imports no topo de `radar.py` (`import json`, `from datetime import datetime`, `from pathlib import Path`) e o bloco:

```python
SEEN_PATH = Path("D:/VortexBrain00/.secrets/radar_seen.json")
JANELA_SEEN_DIAS = 7


def carregar_seen(path: Path = SEEN_PATH) -> list[dict[str, str]]:
    try:
        dados = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return dados if isinstance(dados, list) else []


def podar_seen(
    seen: list[dict[str, str]],
    janela_dias: int = JANELA_SEEN_DIAS,
    agora: datetime | None = None,
) -> list[dict[str, str]]:
    ref = (agora or datetime.now(FUSO)) - timedelta(days=janela_dias)
    out: list[dict[str, str]] = []
    for s in seen:
        try:
            quando = datetime.fromisoformat(s["enviado_em"])
        except (KeyError, ValueError):
            continue
        if quando >= ref:
            out.append(s)
    return out


def filtrar_novos(
    candidatos: list[Candidato], seen: list[dict[str, str]]
) -> list[Candidato]:
    urls_vistas = {s.get("url") for s in seen}
    return [c for c in candidatos if c.url not in urls_vistas]


def gravar_seen(
    seen: list[dict[str, str]],
    urls: list[str],
    path: Path = SEEN_PATH,
    agora: datetime | None = None,
) -> None:
    quando = (agora or datetime.now(FUSO)).isoformat()
    atualizado = list(seen) + [{"url": u, "enviado_em": quando} for u in urls]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(atualizado, ensure_ascii=False, indent=2), encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /d/VortexBrain00/stella && uv run pytest tests/corpo/test_radar.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add stella/corpo/radar.py tests/corpo/test_radar.py
git commit -m "feat(radar): seen-log anti-repeticao (carregar/podar/filtrar/gravar)"
```

---

### Task 4: Curador (Claude escolhe top N + resumo + gancho)

**Files:**
- Modify: `stella/corpo/radar.py`
- Test: `tests/corpo/test_radar.py`

**Interfaces:**
- Consumes: `Candidato` (Task 2), `LLMProvider`/`LLMResponse` de `stella.adapters.llm.base`.
- Produces:
  ```python
  @dataclass
  class ItemRadar:
      titulo: str
      url: str
      veiculo: str
      resumo: str
      gancho: str

  def montar_prompt_curadoria(candidatos: list[Candidato], n: int) -> str: ...
  def curar(candidatos: list[Candidato], n: int, *, provider: LLMProvider) -> list[ItemRadar]: ...
  ```

- [ ] **Step 1: Write the failing test**

```python
# adicionar em tests/corpo/test_radar.py
from stella.adapters.llm.base import LLMProvider, LLMResponse, Message


class _ProviderFake(LLMProvider):
    def __init__(self, texto: str) -> None:
        self._texto = texto
        self.prompt_recebido = ""

    def complete(self, prompt: str) -> LLMResponse:
        self.prompt_recebido = prompt
        return LLMResponse(texto=self._texto)

    def chat(self, messages: list[Message]) -> LLMResponse:  # pragma: no cover
        return LLMResponse(texto=self._texto)


def test_curar_parseia_json_e_limita_em_n() -> None:
    resposta = """```json
    [
      {"titulo": "A", "url": "https://x.com/a", "veiculo": "x.com",
       "resumo": "resumo a", "gancho": "gancho a"},
      {"titulo": "B", "url": "https://x.com/b", "veiculo": "x.com",
       "resumo": "resumo b", "gancho": "gancho b"}
    ]
    ```"""
    provider = _ProviderFake(resposta)
    cands = [_cand("https://x.com/a"), _cand("https://x.com/b"), _cand("https://x.com/c")]
    itens = radar.curar(cands, n=2, provider=provider)
    assert len(itens) == 2
    assert itens[0].titulo == "A"
    assert itens[0].gancho == "gancho a"
    assert "https://x.com/a" in provider.prompt_recebido  # candidatos vão no prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /d/VortexBrain00/stella && uv run pytest tests/corpo/test_radar.py -k curar -v`
Expected: FAIL (`curar` não existe).

- [ ] **Step 3: Write minimal implementation**

Adicionar import `from stella.adapters.llm.base import LLMProvider` no topo, e o bloco:

```python
@dataclass
class ItemRadar:
    titulo: str
    url: str
    veiculo: str
    resumo: str
    gancho: str


_INSTRUCAO_CURADORIA = (
    "Você é a Stella, assistente de conteúdo do Bruno (consultor de marketing com IA, "
    "com toque lifestyle). Dos candidatos abaixo, escolha os {n} mais frescos e quentes "
    "para virar post hoje. Para cada um devolva: titulo, url e veiculo (copie exatamente "
    "do candidato), resumo (1 a 2 linhas em português) e gancho (um ângulo de post curto "
    "em português, na voz de estrategista). Não use travessão. Responda APENAS um array "
    "JSON com objetos {{titulo, url, veiculo, resumo, gancho}}, sem texto fora do JSON.\n\n"
    "Candidatos:\n{lista}"
)


def montar_prompt_curadoria(candidatos: list[Candidato], n: int) -> str:
    linhas = [
        f"{i}. [{c.tema}] {c.titulo} | {c.veiculo} | {c.url} | {c.snippet}"
        for i, c in enumerate(candidatos, start=1)
    ]
    return _INSTRUCAO_CURADORIA.format(n=n, lista="\n".join(linhas))


def _extrair_json(texto: str) -> Any:
    t = texto.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1]
        t = t.removeprefix("json").strip()
    inicio, fim = t.find("["), t.rfind("]")
    if inicio == -1 or fim == -1:
        raise ValueError("resposta do curador sem array JSON")
    return json.loads(t[inicio : fim + 1])


def curar(candidatos: list[Candidato], n: int, *, provider: LLMProvider) -> list[ItemRadar]:
    """Pede ao LLM os top N com resumo e gancho; devolve no máximo N itens."""
    if not candidatos:
        return []
    resposta = provider.complete(montar_prompt_curadoria(candidatos, n))
    dados = _extrair_json(resposta.texto)
    itens = [
        ItemRadar(
            titulo=str(d.get("titulo", "")),
            url=str(d.get("url", "")),
            veiculo=str(d.get("veiculo", "")),
            resumo=str(d.get("resumo", "")),
            gancho=str(d.get("gancho", "")),
        )
        for d in dados
    ]
    return itens[:n]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /d/VortexBrain00/stella && uv run pytest tests/corpo/test_radar.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add stella/corpo/radar.py tests/corpo/test_radar.py
git commit -m "feat(radar): curador Claude (top N + resumo + gancho, JSON)"
```

---

### Task 5: Card HTML do Telegram

**Files:**
- Modify: `stella/corpo/radar.py`
- Test: `tests/corpo/test_radar.py`

**Interfaces:**
- Consumes: `ItemRadar` (Task 4).
- Produces:
  ```python
  def montar_card(itens: list[ItemRadar], horario_label: str,
                  agora: datetime | None = None) -> str: ...
  ```

- [ ] **Step 1: Write the failing test**

```python
# adicionar em tests/corpo/test_radar.py
def test_montar_card_formata_itens_sem_travessao() -> None:
    itens = [
        radar.ItemRadar(
            titulo="IA muda SEO",
            url="https://searchengineland.com/x",
            veiculo="searchengineland.com",
            resumo="Google corta cliques.",
            gancho="Se você ainda otimiza pro Google de 2023, repense.",
        )
    ]
    agora = datetime(2026, 6, 21, 6, 0, tzinfo=radar.FUSO)
    card = radar.montar_card(itens, "06h", agora=agora)
    assert "RADAR 06h" in card
    assert "21/06" in card
    assert 'href="https://searchengineland.com/x"' in card
    assert "searchengineland.com" in card
    assert "IA muda SEO" in card
    assert "—" not in card  # sem travessão em texto público


def test_montar_card_vazio_avisa_sem_novidade() -> None:
    card = radar.montar_card([], "14h", agora=datetime(2026, 6, 21, 14, 0, tzinfo=radar.FUSO))
    assert "Sem novidade" in card
    assert "—" not in card
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /d/VortexBrain00/stella && uv run pytest tests/corpo/test_radar.py -k card -v`
Expected: FAIL (`montar_card` não existe).

- [ ] **Step 3: Write minimal implementation**

```python
def montar_card(
    itens: list[ItemRadar], horario_label: str, agora: datetime | None = None
) -> str:
    quando = agora or datetime.now(FUSO)
    cabecalho = f"📰 <b>RADAR {horario_label} · {quando:%d/%m}</b>"
    if not itens:
        return f"{cabecalho}\n\nSem novidade quente neste drop, Senhor."
    blocos = [cabecalho, ""]
    for i, it in enumerate(itens, start=1):
        blocos.append(
            f"<b>{i}. {it.titulo}</b>\n"
            f'🔗 <a href="{it.url}">{it.veiculo}</a>\n'
            f"{it.resumo}\n"
            f"💡 <i>{it.gancho}</i>"
        )
        blocos.append("")
    return "\n".join(blocos).strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /d/VortexBrain00/stella && uv run pytest tests/corpo/test_radar.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add stella/corpo/radar.py tests/corpo/test_radar.py
git commit -m "feat(radar): card HTML do Telegram (com fallback sem novidade)"
```

---

### Task 6: Envio Telegram (HTML) + persistência no vault

**Files:**
- Modify: `stella/corpo/radar.py`
- Test: `tests/corpo/test_radar.py`

**Interfaces:**
- Consumes: `ItemRadar` (Task 4).
- Produces:
  ```python
  COFRE_TELEGRAM: Path
  VAULT_DIR: Path
  RADAR_DIR_REL: str

  def enviar_telegram(texto: str, cofre_path: Path = COFRE_TELEGRAM,
                      http_post: Callable[..., Any] = httpx.post) -> None: ...
  def salvar_no_vault(itens: list[ItemRadar], horario_label: str,
                      vault_dir: Path = VAULT_DIR, agora: datetime | None = None) -> Path: ...
  ```

- [ ] **Step 1: Write the failing test**

```python
# adicionar em tests/corpo/test_radar.py
def test_enviar_telegram_usa_parse_mode_html(tmp_path: Path) -> None:
    cofre = tmp_path / "telegram.json"
    cofre.write_text(json.dumps({"bot_token": "T", "chat_id": "C"}), encoding="utf-8")
    capturado: dict[str, Any] = {}

    class _Resp:
        def raise_for_status(self) -> None:
            return None

    def post_fake(url: str, **kwargs: Any) -> "_Resp":
        capturado["url"] = url
        capturado["json"] = kwargs["json"]
        return _Resp()

    radar.enviar_telegram("oi", cofre_path=cofre, http_post=post_fake)
    assert "/botT/sendMessage" in capturado["url"]
    assert capturado["json"]["chat_id"] == "C"
    assert capturado["json"]["parse_mode"] == "HTML"


def test_salvar_no_vault_escreve_md(tmp_path: Path) -> None:
    itens = [radar.ItemRadar("T", "https://x.com/a", "x.com", "r", "g")]
    agora = datetime(2026, 6, 21, 6, 0, tzinfo=radar.FUSO)
    caminho = radar.salvar_no_vault(itens, "06h", vault_dir=tmp_path, agora=agora)
    conteudo = caminho.read_text(encoding="utf-8")
    assert "06h" in conteudo
    assert "https://x.com/a" in conteudo
    assert caminho.name == "2026-06-21.md"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /d/VortexBrain00/stella && uv run pytest tests/corpo/test_radar.py -k "telegram or vault" -v`
Expected: FAIL (`enviar_telegram`/`salvar_no_vault` não existem).

- [ ] **Step 3: Write minimal implementation**

Adicionar import `import httpx` no topo do `radar.py` e o bloco:

```python
COFRE_TELEGRAM = Path("D:/VortexBrain00/.secrets/telegram.json")
VAULT_DIR = Path("D:/VortexBrain00/bssurf00")
RADAR_DIR_REL = "C04 Claude Obsidian/radar"


def enviar_telegram(
    texto: str,
    cofre_path: Path = COFRE_TELEGRAM,
    http_post: Callable[..., Any] = httpx.post,
) -> None:
    cofre = json.loads(cofre_path.read_text(encoding="utf-8"))
    resp = http_post(
        f"https://api.telegram.org/bot{cofre['bot_token']}/sendMessage",
        json={
            "chat_id": str(cofre["chat_id"]),
            "text": texto,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=20,
    )
    resp.raise_for_status()


def salvar_no_vault(
    itens: list[ItemRadar],
    horario_label: str,
    vault_dir: Path = VAULT_DIR,
    agora: datetime | None = None,
) -> Path:
    quando = agora or datetime.now(FUSO)
    destino = vault_dir / RADAR_DIR_REL / f"{quando:%Y-%m-%d}.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    linhas = [f"\n## Drop {horario_label} ({quando:%H:%M})\n"]
    for it in itens:
        linhas.append(f"- [{it.titulo}]({it.url}) | {it.veiculo}")
        linhas.append(f"  - Resumo: {it.resumo}")
        linhas.append(f"  - Gancho: {it.gancho}")
    with destino.open("a", encoding="utf-8") as arq:
        arq.write("\n".join(linhas) + "\n")
    return destino
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /d/VortexBrain00/stella && uv run pytest tests/corpo/test_radar.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add stella/corpo/radar.py tests/corpo/test_radar.py
git commit -m "feat(radar): envio Telegram HTML e persistencia do drop no vault"
```

---

### Task 7: Orquestrador `rodar_radar` (com degradação)

**Files:**
- Modify: `stella/corpo/radar.py`
- Test: `tests/corpo/test_radar.py`

**Interfaces:**
- Consumes: tudo das Tasks 2-6.
- Produces:
  ```python
  def label_horario(agora: datetime | None = None) -> str: ...
  def construir_provider() -> LLMProvider: ...   # usa StellaConfig
  def rodar_radar(
      n: int,
      *,
      api_key: str | None = None,
      provider: LLMProvider | None = None,
      horario_label: str | None = None,
      enviar: Callable[[str], None] | None = None,
      salvar: bool = True,
      agora: datetime | None = None,
  ) -> list[ItemRadar]: ...
  ```

- [ ] **Step 1: Write the failing test**

```python
# adicionar em tests/corpo/test_radar.py
def test_rodar_radar_fluxo_feliz(tmp_path: Path, monkeypatch) -> None:
    enviados: list[str] = []
    seen_path = tmp_path / "seen.json"
    monkeypatch.setattr(radar, "SEEN_PATH", seen_path)

    def buscar_fake(query: str, api_key: str, **kw: Any) -> list[dict[str, Any]]:
        return [{"titulo": f"T {query}", "url": f"https://x.com/{query}",
                 "veiculo": "x.com", "snippet": "s", "data": "2026-06-21"}]

    provider = _ProviderFake(
        '[{"titulo":"T","url":"https://x.com/marketing","veiculo":"x.com",'
        '"resumo":"r","gancho":"g"}]'
    )

    itens = radar.rodar_radar(
        n=1,
        api_key="k",
        provider=provider,
        enviar=enviados.append,
        salvar=False,
        agora=datetime(2026, 6, 21, 6, 0, tzinfo=radar.FUSO),
        # injeção da busca via patch do default de buscar_candidatos:
    )
    # ver Step 3: rodar_radar aceita buscar via parâmetro
```

> Nota de implementação: para manter o teste limpo, `rodar_radar` recebe também
> `buscar: Callable = buscar_noticias_tavily`. Ajustar o teste para passar
> `buscar=buscar_fake` e assertar `len(itens) == 1`, `enviados` com 1 card contendo
> "RADAR 06h", e `seen_path` gravado com a url enviada.

Versão final do teste:

```python
def test_rodar_radar_fluxo_feliz(tmp_path: Path, monkeypatch: Any) -> None:
    enviados: list[str] = []
    seen_path = tmp_path / "seen.json"
    monkeypatch.setattr(radar, "SEEN_PATH", seen_path)

    def buscar_fake(query: str, api_key: str, **kw: Any) -> list[dict[str, Any]]:
        return [{"titulo": f"T {query}", "url": f"https://x.com/{query}",
                 "veiculo": "x.com", "snippet": "s", "data": "2026-06-21"}]

    provider = _ProviderFake(
        '[{"titulo":"T","url":"https://x.com/marketing","veiculo":"x.com",'
        '"resumo":"r","gancho":"g"}]'
    )
    itens = radar.rodar_radar(
        n=1, api_key="k", provider=provider, buscar=buscar_fake,
        enviar=enviados.append, salvar=False,
        agora=datetime(2026, 6, 21, 6, 0, tzinfo=radar.FUSO),
    )
    assert len(itens) == 1
    assert len(enviados) == 1 and "RADAR 06h" in enviados[0]
    assert json.loads(seen_path.read_text(encoding="utf-8"))[0]["url"] == "https://x.com/marketing"


def test_rodar_radar_degrada_quando_curador_falha(tmp_path: Path, monkeypatch: Any) -> None:
    enviados: list[str] = []
    monkeypatch.setattr(radar, "SEEN_PATH", tmp_path / "seen.json")

    def buscar_fake(query: str, api_key: str, **kw: Any) -> list[dict[str, Any]]:
        return [{"titulo": "Bruto", "url": "https://x.com/bruto", "veiculo": "x.com",
                 "snippet": "s", "data": "d"}]

    class _ProviderQuebra(_ProviderFake):
        def complete(self, prompt: str) -> Any:
            raise RuntimeError("LLM fora do ar")

    radar.rodar_radar(
        n=1, api_key="k", provider=_ProviderQuebra(""), buscar=buscar_fake,
        enviar=enviados.append, salvar=False,
        agora=datetime(2026, 6, 21, 14, 0, tzinfo=radar.FUSO),
    )
    assert len(enviados) == 1
    assert "https://x.com/bruto" in enviados[0]  # card degradado com links crus
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /d/VortexBrain00/stella && uv run pytest tests/corpo/test_radar.py -k rodar_radar -v`
Expected: FAIL (`rodar_radar` não existe).

- [ ] **Step 3: Write minimal implementation**

Adicionar imports `from stella.adapters.llm.anthropic_provider import AnthropicProvider` e `from stella.infra.config import StellaConfig` no topo, e o bloco:

```python
_LABELS_HORA = {6: "06h", 14: "14h", 19: "19h"}
_MODELO_CURADOR = "claude-sonnet-4-6"


def label_horario(agora: datetime | None = None) -> str:
    quando = agora or datetime.now(FUSO)
    return _LABELS_HORA.get(quando.hour, f"{quando:%H}h")


def construir_provider() -> LLMProvider:
    cfg = StellaConfig()  # type: ignore[call-arg]
    return AnthropicProvider(
        api_key=cfg.anthropic_api_key.get_secret_value(), modelo=_MODELO_CURADOR
    )


def _card_degradado(candidatos: list[Candidato], n: int, label: str, agora: datetime) -> str:
    itens = [
        ItemRadar(titulo=c.titulo, url=c.url, veiculo=c.veiculo,
                  resumo=c.snippet, gancho="(curadoria indisponível neste drop)")
        for c in candidatos[:n]
    ]
    return montar_card(itens, label, agora=agora)


def rodar_radar(
    n: int,
    *,
    api_key: str | None = None,
    provider: LLMProvider | None = None,
    horario_label: str | None = None,
    buscar: Callable[..., list[dict[str, Any]]] = buscar_noticias_tavily,
    enviar: Callable[[str], None] | None = None,
    salvar: bool = True,
    agora: datetime | None = None,
) -> list[ItemRadar]:
    quando = agora or datetime.now(FUSO)
    label = horario_label or label_horario(quando)
    if api_key is None:
        api_key = StellaConfig().tavily_api_key.get_secret_value()  # type: ignore[call-arg]
    if provider is None:
        provider = construir_provider()
    if enviar is None:
        enviar = enviar_telegram

    candidatos = buscar_candidatos(api_key=api_key, buscar=buscar)
    seen = podar_seen(carregar_seen(), agora=quando)
    novos = filtrar_novos(candidatos, seen)

    itens: list[ItemRadar] = []
    if novos:
        try:
            itens = curar(novos, n, provider=provider)
        except Exception:
            card = _card_degradado(novos, n, label, quando)
            itens = []
            enviar(card)
            return itens
    card = montar_card(itens, label, agora=quando)
    enviar(card)
    if itens:
        gravar_seen(seen, [it.url for it in itens], agora=quando)
        if salvar:
            try:
                salvar_no_vault(itens, label, agora=quando)
            except Exception:
                pass
    return itens
```

> Ajuste: no caminho degradado, gravar no seen-log as urls dos candidatos enviados
> também (para não repetir o link cru amanhã). Acrescentar antes do `return` do
> ramo `except`: `gravar_seen(seen, [c.url for c in novos[:n]], agora=quando)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /d/VortexBrain00/stella && uv run pytest tests/corpo/test_radar.py -v`
Expected: PASS (todos os testes do radar).

- [ ] **Step 5: Commit**

```bash
git add stella/corpo/radar.py tests/corpo/test_radar.py
git commit -m "feat(radar): orquestrador rodar_radar com degradacao e sem-novidade"
```

---

### Task 8: Comando CLI `stella radar`

**Files:**
- Modify: `stella/frontends/cli.py`

**Interfaces:**
- Consumes: `rodar_radar`, `montar_card`, `label_horario` (Task 7).
- Produces: comando `stella radar --n N`.

- [ ] **Step 1: Adicionar o comando (segue o padrão lazy-import do `seguranca`)**

No bloco de comandos do `app` (perto de `seguranca`), adicionar:

```python
@app.command()
def radar(
    n: int = typer.Option(5, "--n", help="Quantos artigos neste drop (6h=5, 14h=3, 19h=3)."),
) -> None:
    """Busca notícias quentes dos nichos do Bruno e manda o card no Telegram."""
    from stella.corpo.radar import label_horario, montar_card, rodar_radar

    try:
        itens = rodar_radar(n=n)
    except Exception as e:
        typer.echo(f"Senhor, o radar falhou: {e}", err=True)
        raise typer.Exit(code=1) from e
    typer.echo(montar_card(itens, label_horario()))
```

- [ ] **Step 2: Verificar que o comando aparece**

Run: `cd /d/VortexBrain00/stella && uv run stella radar --help`
Expected: ajuda do comando com a opção `--n`.

- [ ] **Step 3: Smoke real (opt-in, manda Telegram de verdade)**

Run: `cd /d/VortexBrain00/stella && uv run stella radar --n 3`
Expected: chega um card no Telegram e o terminal imprime o card. (Se Tavily/Claude indisponíveis, vem card degradado ou "sem novidade", sem stacktrace.)

- [ ] **Step 4: Rodar a suíte completa**

Run: `cd /d/VortexBrain00/stella && uv run pytest -q`
Expected: tudo verde.

- [ ] **Step 5: Commit**

```bash
git add stella/frontends/cli.py
git commit -m "feat(radar): comando CLI stella radar --n"
```

---

### Task 9: Agendamento Windows (3 drops ocultos)

**Files:**
- Create: `D:/VortexBrain00/stella-radar.ps1`

**Interfaces:** usa o lançador oculto já existente `D:/VortexBrain00/stella-run-hidden.vbs` (ver [[reference_stella_tasks_hidden]]).

- [ ] **Step 1: Criar o wrapper PowerShell**

`D:/VortexBrain00/stella-radar.ps1` (espelha `stella-lembretes-tick.ps1`; recebe `-N` por drop):

```powershell
param([int]$N = 5)
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$log = "D:\VortexBrain00\stella-radar.log"
Set-Location "D:\VortexBrain00\stella"
"=== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | radar --n $N | inicio ===" | Out-File $log -Append -Encoding utf8
$saida = & uv run stella radar --n $N 2>&1 | Out-String
$saida | Out-File $log -Append -Encoding utf8
"=== exit: $LASTEXITCODE ===" | Out-File $log -Append -Encoding utf8
```

- [ ] **Step 2: Testar o wrapper manualmente**

Run (PowerShell): `& "D:\VortexBrain00\stella-radar.ps1" -N 3`
Expected: card chega no Telegram; `D:\VortexBrain00\stella-radar.log` registra início e `exit: 0`.

- [ ] **Step 3: Registrar a tarefa agendada com 3 gatilhos, oculta**

Como o `.vbs` só repassa um script, criar 3 gatilhos chamando o wrapper com o N certo. O `.vbs` atual não repassa argumentos extras; então criar a tarefa com 3 ações distintas NÃO é possível por trigger. Solução: 3 tarefas (uma por horário) OU estender o `.vbs` para repassar argumentos. **Escolha do plano: estender o `.vbs`** para repassar argumentos ao script, mantendo retrocompatibilidade.

Editar `D:/VortexBrain00/stella-run-hidden.vbs` para repassar argumentos extras:

```vbs
' Lancador oculto. Uso: wscript stella-run-hidden.vbs "script.ps1" [args...]
Set sh = CreateObject("WScript.Shell")
ps1 = WScript.Arguments(0)
extra = ""
For i = 1 To WScript.Arguments.Count - 1
  extra = extra & " " & WScript.Arguments(i)
Next
sh.Run "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File """ & ps1 & """" & extra, 0, False
```

Registrar a tarefa "Stella Radar" com 3 gatilhos diários (PowerShell):

```powershell
$vbs = "D:\VortexBrain00\stella-run-hidden.vbs"
$ps1 = "D:\VortexBrain00\stella-radar.ps1"
$acao6  = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$vbs`" `"$ps1`" -N 5"
$t6  = New-ScheduledTaskTrigger -Daily -At 6:00am
$t14 = New-ScheduledTaskTrigger -Daily -At 2:00pm
$t19 = New-ScheduledTaskTrigger -Daily -At 7:00pm
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive
Register-ScheduledTask -TaskName "Stella Radar" -Action $acao6 -Trigger $t6,$t14,$t19 -Principal $principal -Force
```

> Limitação: uma tarefa com múltiplos gatilhos compartilha a MESMA ação (mesmo `-N`).
> Para honrar 5/3/3, registrar **3 tarefas separadas** ("Stella Radar 06h", "...14h", "...19h"),
> cada uma com seu gatilho e seu `-N` (5, 3, 3). Usar este bloco como template, trocando
> `-At` e `-N` em cada uma. Confirmar `Settings.Hidden` irrelevante (o `.vbs` já garante sem janela).

- [ ] **Step 4: Verificar as tarefas**

Run (PowerShell):
```powershell
Get-ScheduledTask | Where-Object { $_.TaskName -like 'Stella Radar*' } |
  Select-Object TaskName, State
(Get-ScheduledTaskInfo -TaskName "Stella Radar 06h").NextRunTime
```
Expected: 3 tarefas `Ready`, próximos disparos em 6/14/19h.

- [ ] **Step 5: Disparar uma vez e conferir log + Telegram**

Run (PowerShell): `Start-ScheduledTask -TaskName "Stella Radar 14h"`
Expected: sem janela visível; card no Telegram; `stella-radar.log` com `exit: 0`.

- [ ] **Step 6: Commit**

```bash
git add stella-radar.ps1 stella-run-hidden.vbs
git commit -m "feat(radar): wrapper PS, lancador c/ args e tarefas agendadas 6/14/19h"
```

> Nota: `stella-radar.ps1` e `stella-run-hidden.vbs` ficam em `D:/VortexBrain00/`, fora do
> repo `stella/`. Versioná-los: copiar para `stella/scripts/` no repo OU documentar no README.
> Decisão: adicionar cópia em `stella/scripts/windows/` e commitar lá; os arquivos vivos em
> `D:/VortexBrain00/` são a instalação.

---

## Self-Review

**1. Spec coverage:**
- 3 drops 6/14/19h, 5/3/3 → Task 9 (3 tarefas com `-N` 5/3/3). ✔
- Formato item (título, link+veículo, resumo, gancho) → Tasks 4 (curador) + 5 (card). ✔
- Seleção "mais quente, sem cota" → Task 4 (prompt sem cota por tema). ✔
- Fontes internacionais + entrega PT → Task 2 (allowlist internacional) + Task 4 (prompt em PT). ✔
- Híbrido A+B (Tavily + allowlist) → Task 1 (`include_domains`) + Task 2 (`ALLOWLIST_DOMINIOS`). ✔
- Anti-repetição → Task 3 + uso em Task 7. ✔
- Card Telegram bot único → Tasks 5 + 6. ✔
- Histórico no vault → Task 6 (`salvar_no_vault`) + Task 7 (`salvar=True`). ✔
- Robustez (degradado, sem-novidade, UTF-8, sem travessão) → Tasks 5/7 + testes. ✔
- Testes não-live + 1 live opt-in → todos os testes acima são offline (dublês); o smoke real fica no Task 8 Step 3 (manual). ✔

**2. Placeholder scan:** sem TBD/TODO; todo passo tem código real. As "Notas de implementação" do Task 7 e Task 9 são ajustes explícitos, não placeholders.

**3. Type consistency:** `Candidato`/`ItemRadar` usados de forma consistente; `buscar` tem a mesma assinatura em Task 1/2/7; `provider.complete` retorna `LLMResponse.texto`; `enviar: Callable[[str], None]`. ✔

## Notas para a divisão Claude/Codex

- **Claude (arquitetura/decisão/revisão):** Task 4 (prompt do curador e parser JSON), Task 7 (orquestração e degradação), revisão de PR.
- **Codex (volume mecânico, specs autocontidas):** Tasks 1, 2, 3, 5, 6 (funções puras com teste já especificado), Task 9 (scripts). Codex não commita: Claude/Bruno fecham os commits.
