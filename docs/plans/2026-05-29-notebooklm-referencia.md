---
title: "@mktmagneto.ia — 07 Plano — NotebookLM Referência (grounding)"
tipo: plano-implementacao
projeto: mktmagneto-ia
fase: 1
milestone: "AM-NLM-1 (Referência)"
status: pronto-para-execucao
criado-em: 2026-05-29
atualizado-em: 2026-05-29
tags:
  - plano-implementacao
  - projeto/mktmagneto-ia
  - notebooklm
aliases:
  - "Plano NotebookLM Referência mktmagneto"
---

# NotebookLM como Fonte de Referência (grounding) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar ao `agente_marca_mktmagneto` uma fonte de referência consultável (NotebookLM) como grounding **obrigatório**: antes de produzir, o coordenador consulta um notebook curado via `notebooklm ask` e injeta os trechos no conteúdo passado aos especialistas e ao QA; se a sessão do NotebookLM estiver caída, o agente **para e pede `notebooklm login`** (sem saída degradada).

**Architecture:** Usa a abstração de RAG que o framework já tem. Um adapter `NotebookLMRAGClient(RAGClient)` envolve o CLI `notebooklm` (subprocess, `ask --json`), registrado no `RAGRegistry` sob o nome `notebooklm`. O manifesto declara `rag: notebooklm`; o `build_agent` injeta como `self._rag`. O coordenador (`agent.py`) faz o gate de auth e o `search()` por pauta, repassando o grounding no `knowledge_pack`. **Escopo: só referência.** Geração de artefatos (`generate`) é um plano à parte (sibling).

**Tech Stack:** Python 3.14, pydantic / pydantic-settings, `subprocess`, pytest (`-m 'not live'`), ruff, mypy strict. CLI `notebooklm` (notebooklm-py 0.5.0) já instalado e autenticado.

---

## Pré-requisitos (resolver ANTES da Task 1)

1. **Isolar a feature.** O working tree de `D:\VortexBrain00\stella` está na branch `sub-projeto-d-designer-mcp-hibrido` com mudanças não commitadas (WIP do Designer). Antes de começar: finalizar/commitar (ou fazer stash) o WIP do Designer e criar uma branch limpa a partir da base de integração (master):
   ```bash
   cd /d/VortexBrain00/stella
   git status            # confirmar o que é WIP do Designer
   # (commitar ou stashar o WIP do Designer conforme o estado do sub-projeto D)
   git checkout master && git pull
   git checkout -b sub-projeto-am-notebooklm-referencia
   ```
2. **Auth viva.** `notebooklm auth check` deve sair 0. Se não, `notebooklm login`.
3. **Notebook semeado.** Existir um notebook de referência da marca com ao menos 1 fonte; anotar o id (`notebooklm list --json`). Vai em `.env` como `STELLA_NOTEBOOKLM_NOTEBOOK_ID`.

## File Structure

| Arquivo | Responsabilidade | Ação |
|---|---|---|
| `stella/stella/infra/config.py` | Config: notebook-id, binário, timeout do NotebookLM | Modificar |
| `stella/stella/adapters/rag/__init__.py` | Pacote do adapter RAG | Criar |
| `stella/stella/adapters/rag/notebooklm_client.py` | `NotebookLMRAGClient(RAGClient)` — `search()` + `auth_check()` via CLI | Criar |
| `stella/stella/framework/testing/fakes.py` | `FakeNotebookLMRAG` (dublê com auth controlável) | Modificar |
| `stella/stella/app.py` | Registrar o client no `RAGRegistry` em `build_stella` | Modificar |
| `stella/stella/agents/agente_marca_mktmagneto/manifest.yaml` | `rag: notebooklm` | Modificar |
| `stella/stella/agents/agente_marca_mktmagneto/agent.py` | Gate de auth + injeção do grounding no pipeline | Modificar |
| `stella/stella/agents/agente_marca_mktmagneto/autoqa.py` | QA da copy passa a considerar a referência | Modificar |
| `tests/infra/test_config.py` | Testa os campos novos de config | Modificar |
| `tests/adapters/rag/test_notebooklm_client.py` | Testa o adapter (subprocess mockado) | Criar |
| `tests/infra/test_build_stella_notebooklm.py` | Testa o wiring no `build_stella` | Criar |
| `tests/agents/agente_marca_mktmagneto/test_referencia_grounding.py` | Gate de auth + injeção do grounding | Criar |

> Comando de teste padrão do projeto: `pytest` (já roda `-m 'not live'` por `addopts`). Lint/типи: `ruff check .` e `mypy stella`.

---

### Task 1: Config — campos do NotebookLM

**Files:**
- Modify: `stella/stella/infra/config.py`
- Test: `tests/infra/test_config.py`

- [ ] **Step 1: Escrever o teste que falha**

Adicionar ao final de `tests/infra/test_config.py`:

```python
def test_config_notebooklm_defaults(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "fake")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(tmp_path))

    cfg = StellaConfig()

    assert cfg.notebooklm_notebook_id == ""
    assert cfg.notebooklm_bin == "notebooklm"
    assert cfg.notebooklm_timeout_s == 60


def test_config_notebooklm_override(monkeypatch, tmp_path):
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "fake")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("STELLA_NOTEBOOKLM_NOTEBOOK_ID", "nb_abc123")
    monkeypatch.setenv("STELLA_NOTEBOOKLM_TIMEOUT_S", "90")

    cfg = StellaConfig()

    assert cfg.notebooklm_notebook_id == "nb_abc123"
    assert cfg.notebooklm_timeout_s == 90
```

- [ ] **Step 2: Rodar o teste e ver falhar**

Run: `pytest tests/infra/test_config.py::test_config_notebooklm_defaults -q`
Expected: FAIL — `AttributeError: 'StellaConfig' object has no attribute 'notebooklm_notebook_id'`

- [ ] **Step 3: Implementar (campos novos)**

Em `stella/stella/infra/config.py`, depois do bloco `higgsfield_*` (final da classe `StellaConfig`):

```python
    # NotebookLM: referência RAG via CLI local (sem API key — usa storage_state.json)
    notebooklm_notebook_id: str = Field(default="")
    notebooklm_bin: str = Field(default="notebooklm")
    notebooklm_timeout_s: int = Field(default=60, gt=0)
```

- [ ] **Step 4: Rodar o teste e ver passar**

Run: `pytest tests/infra/test_config.py -q`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add stella/stella/infra/config.py tests/infra/test_config.py
git commit -m "feat(config): add NotebookLM settings (notebook id, bin, timeout)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Adapter — `auth_check()`

**Files:**
- Create: `stella/stella/adapters/rag/__init__.py` (vazio)
- Create: `stella/stella/adapters/rag/notebooklm_client.py`
- Create: `tests/adapters/rag/__init__.py` (vazio)
- Test: `tests/adapters/rag/test_notebooklm_client.py`

- [ ] **Step 1: Criar os pacotes vazios**

```bash
mkdir -p stella/stella/adapters/rag tests/adapters/rag
: > stella/stella/adapters/rag/__init__.py
: > tests/adapters/rag/__init__.py
```

- [ ] **Step 2: Escrever o teste que falha**

`tests/adapters/rag/test_notebooklm_client.py`:

```python
"""Testes do NotebookLMRAGClient — subprocess mockado (sem CLI real)."""

import subprocess
from typing import Any

from stella.adapters.rag.notebooklm_client import NotebookLMRAGClient


class _Proc:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_auth_check_true_quando_exit_0(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Proc(returncode=0))
    client = NotebookLMRAGClient(notebook_id="nb_1")
    assert client.auth_check() is True


def test_auth_check_false_quando_exit_nao_zero(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Proc(returncode=1))
    client = NotebookLMRAGClient(notebook_id="nb_1")
    assert client.auth_check() is False


def test_auth_check_false_quando_binario_ausente(monkeypatch):
    def _raise(*a: Any, **k: Any):
        raise FileNotFoundError("notebooklm not found")

    monkeypatch.setattr(subprocess, "run", _raise)
    client = NotebookLMRAGClient(notebook_id="nb_1")
    assert client.auth_check() is False
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `pytest tests/adapters/rag/test_notebooklm_client.py -q`
Expected: FAIL — `ModuleNotFoundError: stella.adapters.rag.notebooklm_client`

- [ ] **Step 4: Implementar o adapter (com `auth_check`)**

`stella/stella/adapters/rag/notebooklm_client.py`:

```python
"""NotebookLMRAGClient — adapter RAGClient sobre o CLI `notebooklm`.

Implementa `search(query, k)` via `notebooklm ask ... --json` (grounding sobre um
notebook curado) e `auth_check()` refletindo a sessão local (storage_state.json).
Não usa API key — reaproveita o login interativo do Bruno.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any

from stella.framework.rag import RAGClient


class NotebookLMError(RuntimeError):
    """Falha (não-auth) ao consultar o NotebookLM via CLI."""


@dataclass
class NotebookLMRAGClient(RAGClient):
    """Cliente RAG que consulta um notebook do NotebookLM via CLI.

    Args:
        notebook_id: id (ou prefixo) do notebook de referência da marca.
        bin: caminho/nome do executável `notebooklm` (default: resolvido na PATH).
        timeout_s: timeout (s) por chamada ao CLI.
    """

    notebook_id: str
    bin: str = "notebooklm"
    timeout_s: int = 60

    def auth_check(self) -> bool:
        """True se a sessão está válida (`notebooklm auth check` sai 0)."""
        try:
            proc = subprocess.run(
                [self.bin, "auth", "check"],
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return proc.returncode == 0
```

- [ ] **Step 5: Rodar e ver passar**

Run: `pytest tests/adapters/rag/test_notebooklm_client.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add stella/stella/adapters/rag tests/adapters/rag
git commit -m "feat(rag): NotebookLMRAGClient.auth_check via notebooklm CLI

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Adapter — `search()`

**Files:**
- Modify: `stella/stella/adapters/rag/notebooklm_client.py`
- Test: `tests/adapters/rag/test_notebooklm_client.py`

- [ ] **Step 1: Escrever os testes que falham**

Adicionar a `tests/adapters/rag/test_notebooklm_client.py`:

```python
import json

import pytest

from stella.adapters.rag.notebooklm_client import NotebookLMError


def test_search_parseia_json_em_doc(monkeypatch):
    payload = json.dumps({"answer": "Hooks de curiosidade funcionam.", "citations": [{"n": 1}]})
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Proc(returncode=0, stdout=payload))
    client = NotebookLMRAGClient(notebook_id="nb_1")

    docs = client.search("hooks que engajam")

    assert len(docs) == 1
    assert "curiosidade" in docs[0]["texto"]
    assert docs[0]["citacoes"] == [{"n": 1}]


def test_search_passa_notebook_e_json_no_comando(monkeypatch):
    chamadas = {}

    def _capture(cmd, **k):
        chamadas["cmd"] = cmd
        return _Proc(returncode=0, stdout=json.dumps({"answer": "ok"}))

    monkeypatch.setattr(subprocess, "run", _capture)
    NotebookLMRAGClient(notebook_id="nb_xyz").search("pergunta")

    assert "ask" in chamadas["cmd"]
    assert "--notebook" in chamadas["cmd"] and "nb_xyz" in chamadas["cmd"]
    assert "--json" in chamadas["cmd"]


def test_search_levanta_em_exit_nao_zero(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Proc(returncode=1, stderr="boom"))
    with pytest.raises(NotebookLMError):
        NotebookLMRAGClient(notebook_id="nb_1").search("x")


def test_search_vazio_quando_sem_resposta(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Proc(returncode=0, stdout=json.dumps({})))
    assert NotebookLMRAGClient(notebook_id="nb_1").search("x") == []
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/adapters/rag/test_notebooklm_client.py -k search -q`
Expected: FAIL — `AttributeError: 'NotebookLMRAGClient' object has no attribute 'search'`

- [ ] **Step 3: Implementar `search`**

Adicionar o método à classe `NotebookLMRAGClient` em `notebooklm_client.py`:

```python
    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Pergunta ao notebook e devolve a resposta ancorada como 1 doc.

        Formato do doc: {"texto": <resposta>, "citacoes": <lista>}.
        Levanta NotebookLMError se o CLI falhar ou a saída não for JSON.
        """
        try:
            proc = subprocess.run(
                [
                    self.bin, "ask", query,
                    "--notebook", self.notebook_id,
                    "--json",
                    "--timeout", str(self.timeout_s),
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout_s + 30,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            raise NotebookLMError(f"falha ao chamar `notebooklm ask`: {e}") from e

        if proc.returncode != 0:
            raise NotebookLMError(
                f"`notebooklm ask` saiu com {proc.returncode}: {proc.stderr.strip()}"
            )
        try:
            dados = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise NotebookLMError(f"saída de `notebooklm ask` não é JSON: {e}") from e

        # chaves defensivas — o CLI pode usar answer/text e citations/references
        texto = str(dados.get("answer") or dados.get("text") or "")
        citacoes = dados.get("citations") or dados.get("references") or []
        if not texto:
            return []
        return [{"texto": texto, "citacoes": citacoes}][:k]
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/adapters/rag/test_notebooklm_client.py -q`
Expected: PASS (todos)

- [ ] **Step 5: Verificação do schema real (uma vez, opt-in)**

> A parsing acima é defensiva quanto às chaves (`answer`/`text`, `citations`/`references`). Com a auth viva e o notebook semeado, confirmar o schema real uma vez:
> ```bash
> notebooklm ask "resuma as fontes" --notebook "$STELLA_NOTEBOOKLM_NOTEBOOK_ID" --json | head -c 400
> ```
> Se as chaves diferirem das duas tentadas, ajustar `texto`/`citacoes` no `search()` e re-rodar os testes.

- [ ] **Step 6: Commit**

```bash
git add stella/stella/adapters/rag/notebooklm_client.py tests/adapters/rag/test_notebooklm_client.py
git commit -m "feat(rag): NotebookLMRAGClient.search via notebooklm ask --json

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Fixture de teste `FakeNotebookLMRAG`

**Files:**
- Modify: `stella/stella/framework/testing/fakes.py`

> É um dublê de teste (sem teste próprio) — será exercido pelas Tasks 6–8.

- [ ] **Step 1: Adicionar a fixture**

Em `stella/stella/framework/testing/fakes.py`, logo após a classe `FakeRAG`:

```python
@dataclass
class FakeNotebookLMRAG(RAGClient):
    """RAG fake estilo NotebookLM: auth_check controlável + docs pré-definidos.

    `autenticado=False` simula sessão caída (gate de auth do agente deve parar).
    Registra as queries recebidas em `queries` para asserts.
    """

    autenticado: bool = True
    docs: list[dict[str, Any]] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)

    def auth_check(self) -> bool:
        return self.autenticado

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        self.queries.append(query)
        return list(self.docs[:k])
```

- [ ] **Step 2: Sanidade de import**

Run: `python -c "from stella.framework.testing.fakes import FakeNotebookLMRAG; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add stella/stella/framework/testing/fakes.py
git commit -m "test(fakes): add FakeNotebookLMRAG (auth-aware RAG double)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Wiring — registrar no `RAGRegistry` (`build_stella`)

**Files:**
- Modify: `stella/stella/app.py`
- Test: `tests/infra/test_build_stella_notebooklm.py` (criar)

> **Sempre registra** (mesmo com `notebook_id` vazio) para que o manifesto `rag: notebooklm` (Task 6) sempre resolva no `build_agent` — senão `RAGRegistry.get` levantaria `RAGNotFoundError` ao construir o agente.

- [ ] **Step 1: Escrever o teste que falha**

`tests/infra/test_build_stella_notebooklm.py`:

```python
"""build_stella registra o NotebookLMRAGClient no RAGRegistry."""

from stella.adapters.rag.notebooklm_client import NotebookLMRAGClient
from stella.app import build_stella
from stella.infra.config import StellaConfig


def _cfg(monkeypatch, tmp_path, notebook_id: str = "nb_test") -> StellaConfig:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("STELLA_NVIDIA_API_KEY", "fake")
    monkeypatch.setenv("STELLA_ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("STELLA_VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("STELLA_NOTEBOOKLM_NOTEBOOK_ID", notebook_id)
    return StellaConfig()


def test_build_stella_registra_notebooklm(monkeypatch, tmp_path):
    stella = build_stella(_cfg(monkeypatch, tmp_path, "nb_xyz"))
    client = stella.rag_reg.get("notebooklm")
    assert isinstance(client, NotebookLMRAGClient)
    assert client.notebook_id == "nb_xyz"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/infra/test_build_stella_notebooklm.py -q`
Expected: FAIL — `RAGNotFoundError: RAG corpus 'notebooklm' nao registrado`

- [ ] **Step 3: Implementar o registro**

Em `stella/stella/app.py`: adicionar o import no topo (junto aos demais adapters):

```python
from stella.adapters.rag.notebooklm_client import NotebookLMRAGClient
```

E logo após a linha `rag_reg = RAGRegistry()`:

```python
    # NotebookLM: referência RAG (grounding obrigatório do agente de marca).
    # Sempre registrado para o manifesto `rag: notebooklm` resolver no build_agent.
    rag_reg.register(
        "notebooklm",
        NotebookLMRAGClient(
            notebook_id=config.notebooklm_notebook_id,
            bin=config.notebooklm_bin,
            timeout_s=config.notebooklm_timeout_s,
        ),
    )
    if not config.notebooklm_notebook_id:
        _logger.warning(
            "NotebookLM: STELLA_NOTEBOOKLM_NOTEBOOK_ID vazio — o agente de marca "
            "vai falhar no gate de auth/consulta até configurar o notebook."
        )
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/infra/test_build_stella_notebooklm.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add stella/stella/app.py tests/infra/test_build_stella_notebooklm.py
git commit -m "feat(app): register NotebookLMRAGClient in RAGRegistry

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Manifesto — `rag: notebooklm`

**Files:**
- Modify: `stella/stella/agents/agente_marca_mktmagneto/manifest.yaml`
- Test: `tests/agents/agente_marca_mktmagneto/test_referencia_grounding.py` (criar)

- [ ] **Step 1: Escrever o teste que falha**

`tests/agents/agente_marca_mktmagneto/test_referencia_grounding.py`:

```python
"""Referência NotebookLM: manifesto, gate de auth e injeção de grounding."""

from pathlib import Path
from typing import Any, cast

import stella as _pkg
from stella.adapters.llm.base import LLMProvider
from stella.adapters.llm.router import LLMRouter
from stella.agents.agente_marca_mktmagneto.agent import Agent as Coordenador
from stella.framework.manifest import load_manifest
from stella.framework.testing.fakes import (
    FakeCopywriter,
    FakeDesigner,
    FakeLLM,
    FakeNotebookLMRAG,
    FakeRegistry,
    FakeVault,
)

_BASE = "C04 Claude Obsidian/projetos e specs/mktmagneto.ia/"


def test_manifest_declara_rag_notebooklm():
    manifest_path = (
        Path(_pkg.__file__).parent
        / "agents"
        / "agente_marca_mktmagneto"
        / "manifest.yaml"
    )
    manifest = load_manifest(manifest_path)
    assert manifest.capacidades_externas.rag == "notebooklm"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/agents/agente_marca_mktmagneto/test_referencia_grounding.py::test_manifest_declara_rag_notebooklm -q`
Expected: FAIL — `assert None == 'notebooklm'`

- [ ] **Step 3: Editar o manifesto**

Em `stella/stella/agents/agente_marca_mktmagneto/manifest.yaml`, na seção `capacidades_externas`, trocar:

```yaml
  rag: null
```
por:
```yaml
  rag: notebooklm
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/agents/agente_marca_mktmagneto/test_referencia_grounding.py::test_manifest_declara_rag_notebooklm -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add stella/stella/agents/agente_marca_mktmagneto/manifest.yaml tests/agents/agente_marca_mktmagneto/test_referencia_grounding.py
git commit -m "feat(agente-marca): declarar rag: notebooklm no manifesto

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Coordenador — gate de auth (obrigatório)

**Files:**
- Modify: `stella/stella/agents/agente_marca_mktmagneto/agent.py`
- Test: `tests/agents/agente_marca_mktmagneto/test_referencia_grounding.py`

- [ ] **Step 1: Escrever o teste que falha**

Adicionar a `test_referencia_grounding.py` os helpers + o teste do gate:

```python
class _FakeRouter:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def select(self, complexity: str) -> LLMProvider:
        return self._llm


def _vault() -> FakeVault:
    return FakeVault(
        {
            f"{_BASE}mktmagneto.ia — 01 Spec.md": ("# Spec", {}),
            f"{_BASE}mktmagneto.ia — 03 Briefing do Agente de Conteúdo.md": ("briefing", {}),
            f"{_BASE}mktmagneto.ia — 04 Kit de Identidade Visual.md": ("kit", {}),
        }
    )


def _coord(rag: FakeNotebookLMRAG, vault: FakeVault, coord_llm: FakeLLM) -> Coordenador:
    registry = FakeRegistry({"copywriter": FakeCopywriter(), "designer": FakeDesigner()})
    return Coordenador(
        vault=vault,
        llm=cast(LLMRouter, _FakeRouter(coord_llm)),
        mcps=[],
        rag=rag,
        registry=registry,
    )


def test_auth_caido_para_e_nao_produz(monkeypatch):
    vault = _vault()
    rag = FakeNotebookLMRAG(autenticado=False)
    coord = _coord(rag, vault, FakeLLM())

    out = coord.execute({})

    assert out.sucesso is False
    assert any("notebooklm login" in m for m in out.mensagens)
    # nenhuma nota escrita na fila
    fila = [p for p in vault._store if "Stella-publicacao/fila/" in p]
    assert fila == []
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/agents/agente_marca_mktmagneto/test_referencia_grounding.py::test_auth_caido_para_e_nao_produz -q`
Expected: FAIL — o agente roda o pipeline (sucesso True ou erro de LLM), não retorna a mensagem de login.

- [ ] **Step 3: Implementar o gate**

Em `stella/stella/agents/agente_marca_mktmagneto/agent.py`, dentro de `execute()`, **logo após** o bloco que valida `vault/llm/registry` injetados e **antes** de `# 1. Conhecimento da marca`:

```python
        # 0. Gate de auth do NotebookLM — referência é grounding OBRIGATÓRIO.
        if self._rag is not None and hasattr(self._rag, "auth_check"):
            if not self._rag.auth_check():
                return AgentOutput(
                    resultado={},
                    sucesso=False,
                    mensagens=[
                        "Senhor, NotebookLM deslogou. Rode `notebooklm login` e me chame de novo."
                    ],
                )
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/agents/agente_marca_mktmagneto/test_referencia_grounding.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add stella/stella/agents/agente_marca_mktmagneto/agent.py tests/agents/agente_marca_mktmagneto/test_referencia_grounding.py
git commit -m "feat(agente-marca): gate de auth NotebookLM para a run se sessão caída

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Coordenador — injetar o grounding no pipeline

**Files:**
- Modify: `stella/stella/agents/agente_marca_mktmagneto/agent.py`
- Test: `tests/agents/agente_marca_mktmagneto/test_referencia_grounding.py`

- [ ] **Step 1: Escrever o teste que falha**

Adicionar a `test_referencia_grounding.py`:

```python
def test_grounding_injetado_no_payload_do_copywriter(monkeypatch):
    vault = _vault()
    rag = FakeNotebookLMRAG(
        autenticado=True,
        docs=[{"texto": "Use prova concreta no gancho.", "citacoes": []}],
    )
    registry = FakeRegistry({"copywriter": FakeCopywriter(), "designer": FakeDesigner()})
    # plan com 1 pauta + QA aprovado (copy + visual)
    coord_llm = FakeLLM(
        responses=[
            'pautas:\n  - {pilar: 1, titulo: "do chat à construção"}\n',
            "veredicto: aprovado\nmotivo: ok",
            "veredicto: aprovado\nmotivo: ok",
        ]
    )
    coord = Coordenador(
        vault=vault,
        llm=cast(LLMRouter, _FakeRouter(coord_llm)),
        mcps=[],
        rag=rag,
        registry=registry,
    )

    coord.execute({})

    # a query de grounding usou o título da pauta
    assert any("do chat à construção" in q for q in rag.queries)
    # o copywriter recebeu o knowledge_pack com a chave 'referencia' preenchida
    copyw = cast(FakeCopywriter, registry.get("copywriter"))
    assert copyw.payloads, "copywriter deveria ter sido chamado"
    kp = copyw.payloads[0]["knowledge_pack"]
    assert "prova concreta" in kp.get("referencia", "")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/agents/agente_marca_mktmagneto/test_referencia_grounding.py::test_grounding_injetado_no_payload_do_copywriter -q`
Expected: FAIL — `rag.queries` vazio / `referencia` ausente no knowledge_pack.

- [ ] **Step 3: Implementar a injeção**

Em `agent.py`, dentro do laço `for i, pauta in enumerate(pautas):`, **antes** da chamada `# Copy — tentativa 1` (`copy_out = self.delegate_to("copywriter", ...)`), montar o knowledge com grounding e passar adiante:

```python
            # Grounding obrigatório por pauta: consulta o notebook de referência.
            referencia_txt = ""
            if self._rag is not None:
                docs = self._rag.search(pauta.titulo)
                referencia_txt = "\n\n".join(str(d.get("texto", "")) for d in docs)
            knowledge_pauta = {**knowledge, "referencia": referencia_txt}
```

Depois, **substituir** `knowledge` por `knowledge_pauta` nas chamadas deste post:
- nos dois `self.delegate_to("copywriter", {"knowledge_pack": knowledge, ...})` → `knowledge_pauta`;
- no `self.delegate_to("designer", {"knowledge_pack": knowledge, ...})` → `knowledge_pauta`;
- em todos os `autoqa.aprova_copy(... knowledge_pack=knowledge)` e `autoqa.feedback_copy(... knowledge_pack=knowledge)` → `knowledge_pauta`.

(O `knowledge` base, carregado por `CarregadorMarca`, continua sendo a fonte; `knowledge_pauta` só acrescenta a chave `referencia`.)

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/agents/agente_marca_mktmagneto/ -q`
Expected: PASS (incluindo os testes de integração v2 existentes — eles passam `rag=None`, então o grounding é pulado e nada quebra)

- [ ] **Step 5: Commit**

```bash
git add stella/stella/agents/agente_marca_mktmagneto/agent.py tests/agents/agente_marca_mktmagneto/test_referencia_grounding.py
git commit -m "feat(agente-marca): injeta grounding NotebookLM no knowledge_pack por pauta

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: AutoQA — considerar a referência

**Files:**
- Modify: `stella/stella/agents/agente_marca_mktmagneto/autoqa.py`
- Test: `tests/agents/agente_marca_mktmagneto/test_autoqa_v2.py`

- [ ] **Step 1: Escrever o teste que falha**

Adicionar a `tests/agents/agente_marca_mktmagneto/test_autoqa_v2.py`:

```python
def test_prompt_copy_inclui_referencia_quando_presente():
    from stella.agents.agente_marca_mktmagneto.autoqa import AutoQA
    from stella.framework.testing.fakes import FakeLLM

    qa = AutoQA(llm=FakeLLM())
    prompt = qa._montar_prompt_copy(
        copy={"legenda": "L", "hashtags": []},
        knowledge_pack={"briefing": "B", "referencia": "PRINCÍPIO: prova concreta"},
    )
    assert "prova concreta" in prompt
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/agents/agente_marca_mktmagneto/test_autoqa_v2.py::test_prompt_copy_inclui_referencia_quando_presente -q`
Expected: FAIL — `assert 'prova concreta' in prompt`

- [ ] **Step 3: Implementar**

Em `stella/stella/agents/agente_marca_mktmagneto/autoqa.py`, no método `_montar_prompt_copy`, após a montagem de `contexto` e antes do `return`, acrescentar a referência ao contexto:

```python
        referencia = knowledge_pack.get("referencia", "")
        if referencia:
            contexto += f"REFERÊNCIA (princípios/exemplos curados):\n{referencia}\n\n"
```

(`contexto` já é uma string local construída logo acima no método; basta concatenar antes do `return`.)

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/agents/agente_marca_mktmagneto/test_autoqa_v2.py -q`
Expected: PASS

- [ ] **Step 5: Suite completa + lint/tipos**

Run:
```bash
pytest -q
ruff check .
mypy stella
```
Expected: tudo verde.

- [ ] **Step 6: Commit**

```bash
git add stella/stella/agents/agente_marca_mktmagneto/autoqa.py tests/agents/agente_marca_mktmagneto/test_autoqa_v2.py
git commit -m "feat(agente-marca): AutoQA considera a referência NotebookLM na copy

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Smoke manual (opt-in, sessão real)

Com `.env` contendo `STELLA_NOTEBOOKLM_NOTEBOOK_ID` e a auth viva:

```bash
notebooklm auth check            # exit 0
python -m stella.frontends.cli conteudo mktmagneto
```
Esperado: o agente roda; se a auth estiver caída, encerra com *"NotebookLM deslogou. Rode `notebooklm login`…"*. Com auth viva, gera os rascunhos com o grounding aplicado.

## Definition of Done

- [ ] Tasks 1–9 commitadas, `pytest` / `ruff` / `mypy` verdes.
- [ ] `agente_marca_mktmagneto` consulta o notebook por pauta e injeta o grounding em copywriter/designer/AutoQA.
- [ ] Gate de auth: sessão caída → run encerra sem produzir nada, com a mensagem de login.
- [ ] Testes de integração v2 existentes continuam passando (`rag=None` → grounding pulado).
- [ ] PR pequeno (escopo só referência) no padrão "o que mudou / como testei / risco conhecido".

## Self-Review (preenchido)

- **Cobertura do spec §4.6:** 4.6.1 (adapter RAGClient) → Tasks 2,3,5; 4.6.3 (consumo obrigatório no coordenador) → Tasks 7,8,9; 4.6.5 (gate de auth para-e-re-roda) → Task 7. **Fora deste plano (sibling):** 4.6.2 manutenção/write-back do notebook, 4.6.4 estúdio de artefatos `generate` — viram o 2º plano.
- **Placeholders:** nenhum — todo passo tem código/comando reais. A única incerteza (chaves do JSON do `ask`) é tratada com parsing defensivo + passo de verificação real (Task 3, Step 5).
- **Consistência de tipos:** `RAGClient.search(query, k) -> list[dict]` e `auth_check() -> bool` usados igualmente no adapter real, no `FakeNotebookLMRAG` e no agente. `knowledge_pack["referencia"]: str` em agent.py e autoqa.py.

---

## Próximos passos (depois deste plano)

1. **2º plano (sibling):** Estúdio de artefatos NotebookLM (`generate` out-of-band + CLI `stella conteudo artefato`) — §4.6.4.
2. **Manutenção do notebook** (§4.6.2): comandos `referencia add|sync` + write-back do digest do Pesquisador.
3. **Réplicas:** mesmo adapter para `agente_marca_centroviagens`, `agente_marca_mvaambiental`, `agente_marca_americalatinaambiental` (1 notebook por marca) — ver [[2026-05-28 — Iniciar agentes de marca (Centro Viagens, MVA Ambiental, América Latina)]].
