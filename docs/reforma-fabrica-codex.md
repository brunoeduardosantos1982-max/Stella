# Reforma da Fábrica — Frente B (spec autocontida para Codex)

Contexto: reforma da fábrica de conteúdo (@brunoe.santos). A Frente A (QA de material rico) já está feita pelo Claude na branch `feat/reforma-fabrica-materiais`. Esta spec é a **Frente B**: centralizar o conteúdo por keyword e dar à Stella o pacote por keyword (listar → escolher → enviar via Telegram).

**Regras do projeto (obrigatórias):**
- TDD: teste falha primeiro, depois código. `uv run pytest`, `uv run ruff check`, `uv run ruff format`, `uv run mypy` limpos.
- Type hints estritos. Clean Architecture: `domain/` não importa `adapters/` nem `corpo/`. Adapters injetáveis (testes mockam, sem rede).
- Escrita atômica (`.tmp` + `replace`) onde houver risco de corrupção. Sem travessão (—) em texto público.
- **Codex NÃO commita.** Deixe a árvore verde; o Claude revisa e commita.

**Interfaces existentes que você vai consumir (não mude):**
- `stella/domain/registro_keywords.py`: `RegistroKeywords.carregar(path) -> RegistroKeywords`, `.buscar(keyword) -> EntradaKeyword | None`, `.keywords() -> list[EntradaKeyword]`, `.registrar_post(keyword, post_id, *, slug="", material="")`, `.definir_material(keyword, *, slug, material="")`. `EntradaKeyword(keyword, slug, material, posts: list[str])`. `normalizar_keyword(kw) -> str` (sem acento, MAIÚSCULA).
- `stella/corpo/daemon_telegram.py`: `load_secrets(cofre_path=COFRE_TELEGRAM) -> TelegramSecrets(bot_token, chat_id)`.
- `stella/frontends/cli.py`: helpers `_fab_dir() -> Path` (= `StellaConfig().vault_path / "C04 Claude Obsidian/outputs/FABRICADECONTEUDO"`), `_registro_path() -> Path`, e a constante `_FILA_DIR = "C04 Claude Obsidian/Stella-publicacao/fila"`. Import `from stella.config import StellaConfig` já é usado no arquivo.

Estrutura canônica alvo: `FABRICADECONTEUDO/<KEYWORD_NORM>/<post-id>/{legenda.txt, slide-NN.png}` (a copy/slides do post, hoje gravados na fila). PDF do material: `FABRICADECONTEUDO/<KEYWORD_NORM>/<slug>.pdf`.

---

## Task A — Domínio `pacote_conteudo`

**Arquivos:** criar `stella/domain/pacote_conteudo.py`; teste `tests/domain/test_pacote_conteudo.py`.

**Produz:**
- `@dataclass(frozen=True) PostInfo(post_id: str, data: str, titulo: str)`
- `@dataclass(frozen=True) Pacote(keyword: str, post_id: str, legenda: Path | None, slides: list[Path], material_pdf: Path | None, manychat: Path | None)`
- `listar_posts(registro, keyword, fab_root) -> list[PostInfo]`
- `resolver_pacote(registro, keyword, post_id, fab_root) -> Pacote`

**Teste (escreva primeiro, veja falhar):**

```python
# tests/domain/test_pacote_conteudo.py
from pathlib import Path
from stella.domain.registro_keywords import RegistroKeywords
from stella.domain.pacote_conteudo import listar_posts, resolver_pacote, PostInfo

def _registro():
    reg = RegistroKeywords()
    reg.definir_material("VITRINE", slug="vitrine-busca-ia", material="o guia")
    reg.registrar_post("VITRINE", "2026-06-24-vitrine")
    return reg

def test_listar_posts_extrai_data(tmp_path):
    posts = listar_posts(_registro(), "vitrine", tmp_path)
    assert posts == [PostInfo(post_id="2026-06-24-vitrine", data="2026-06-24", titulo="")]

def test_listar_posts_keyword_inexistente(tmp_path):
    assert listar_posts(_registro(), "NADA", tmp_path) == []

def test_resolver_pacote_monta_paths(tmp_path):
    kw = tmp_path / "VITRINE"; post = kw / "2026-06-24-vitrine"; post.mkdir(parents=True)
    (post / "legenda.txt").write_text("x", encoding="utf-8")
    (post / "slide-00.png").write_bytes(b"x"); (post / "slide-01.png").write_bytes(b"x")
    (kw / "vitrine-busca-ia.pdf").write_bytes(b"%PDF")
    pac = resolver_pacote(_registro(), "vitrine", "2026-06-24-vitrine", tmp_path)
    assert pac.legenda == post / "legenda.txt"
    assert pac.slides == [post / "slide-00.png", post / "slide-01.png"]
    assert pac.material_pdf == kw / "vitrine-busca-ia.pdf"

def test_resolver_pacote_ausentes_viram_none(tmp_path):
    pac = resolver_pacote(_registro(), "vitrine", "2026-06-24-vitrine", tmp_path)
    assert pac.legenda is None and pac.slides == [] and pac.material_pdf is None
```

**Implementação:**

```python
# stella/domain/pacote_conteudo.py
from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path
from stella.domain.registro_keywords import RegistroKeywords, normalizar_keyword

_DATA_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")

@dataclass(frozen=True)
class PostInfo:
    post_id: str
    data: str
    titulo: str

@dataclass(frozen=True)
class Pacote:
    keyword: str
    post_id: str
    legenda: Path | None
    slides: list[Path]
    material_pdf: Path | None
    manychat: Path | None

def listar_posts(registro: RegistroKeywords, keyword: str, fab_root: Path) -> list[PostInfo]:
    entrada = registro.buscar(keyword)
    if entrada is None:
        return []
    infos: list[PostInfo] = []
    for post_id in entrada.posts:
        m = _DATA_RE.match(post_id)
        infos.append(PostInfo(post_id=post_id, data=m.group(1) if m else "", titulo=""))
    return infos

def resolver_pacote(registro: RegistroKeywords, keyword: str, post_id: str, fab_root: Path) -> Pacote:
    entrada = registro.buscar(keyword)
    norm = normalizar_keyword(keyword)
    kw_dir = fab_root / norm
    post_dir = kw_dir / post_id
    legenda = post_dir / "legenda.txt"
    slides = sorted(post_dir.glob("slide-*.png")) if post_dir.exists() else []
    pdf = (kw_dir / f"{entrada.slug}.pdf") if entrada and entrada.slug else None
    manychat = next(iter(kw_dir.glob("manychat-*.txt")), None) if kw_dir.exists() else None
    return Pacote(
        keyword=norm, post_id=post_id,
        legenda=legenda if legenda.exists() else None,
        slides=list(slides),
        material_pdf=pdf if (pdf and pdf.exists()) else None,
        manychat=manychat,
    )
```

Verifique: `uv run pytest tests/domain/test_pacote_conteudo.py -v` (PASS), ruff+mypy limpos.

---

## Task B — Adapter Telegram para arquivos

**Arquivos:** criar `stella/adapters/telegram/__init__.py` (vazio) e `stella/adapters/telegram/arquivos.py`; teste `tests/adapters/telegram/test_arquivos.py`.

**Produz:** `enviar_documento(token, chat_id, caminho, *, legenda=None, http_post=httpx.post) -> None` e `enviar_foto(...)` (mesma assinatura). `http_post` injetável.

**Teste:**

```python
# tests/adapters/telegram/test_arquivos.py
from stella.adapters.telegram.arquivos import enviar_documento, enviar_foto

class _Resp:
    def raise_for_status(self): pass

def test_enviar_documento_chama_sendDocument(tmp_path):
    f = tmp_path / "a.pdf"; f.write_bytes(b"%PDF")
    chamadas = []
    def fake_post(url, **kw): chamadas.append((url, kw)); return _Resp()
    enviar_documento("TOK", "42", f, legenda="oi", http_post=fake_post)
    url, kw = chamadas[0]
    assert url.endswith("/sendDocument")
    assert kw["data"] == {"chat_id": "42", "caption": "oi"}
    assert "document" in kw["files"]

def test_enviar_foto_chama_sendPhoto(tmp_path):
    f = tmp_path / "s.png"; f.write_bytes(b"x")
    chamadas = []
    def fake_post(url, **kw): chamadas.append(url); return _Resp()
    enviar_foto("TOK", "42", f, http_post=fake_post)
    assert chamadas[0].endswith("/sendPhoto")
```

**Implementação:**

```python
# stella/adapters/telegram/arquivos.py
from __future__ import annotations
from collections.abc import Callable
from pathlib import Path
import httpx

def _url(token: str, metodo: str) -> str:
    return f"https://api.telegram.org/bot{token}/{metodo}"

def _enviar(metodo: str, campo: str, token: str, chat_id: str, caminho: Path,
            legenda: str | None, http_post: Callable) -> None:
    data = {"chat_id": chat_id}
    if legenda:
        data["caption"] = legenda
    with caminho.open("rb") as fh:
        resp = http_post(_url(token, metodo), data=data,
                         files={campo: (caminho.name, fh)}, timeout=120)
    resp.raise_for_status()

def enviar_documento(token: str, chat_id: str, caminho: Path, *,
                     legenda: str | None = None, http_post: Callable = httpx.post) -> None:
    _enviar("sendDocument", "document", token, chat_id, caminho, legenda, http_post)

def enviar_foto(token: str, chat_id: str, caminho: Path, *,
                legenda: str | None = None, http_post: Callable = httpx.post) -> None:
    _enviar("sendPhoto", "photo", token, chat_id, caminho, legenda, http_post)
```

Verifique: `uv run pytest tests/adapters/telegram/test_arquivos.py -v` (PASS), ruff+mypy limpos.

---

## Task C — Centralização (migração retroativa + espelho da fila)

**Arquivos:** criar `stella/corpo/centralizar_conteudo.py`; teste `tests/corpo/test_centralizar_conteudo.py`.

**Produz:**
- `centralizar_existentes(registro, fab_root, fila_root) -> list[str]` (fila/<post>/ → fab/<NORM>/<post>/, todas as keywords; idempotente)
- `sincronizar_fila(fab_root, fila_root, keyword, post_id) -> str` (sentido inverso, para publicar)

**Teste:**

```python
# tests/corpo/test_centralizar_conteudo.py
from stella.domain.registro_keywords import RegistroKeywords
from stella.corpo.centralizar_conteudo import centralizar_existentes, sincronizar_fila

def _reg():
    reg = RegistroKeywords()
    reg.registrar_post("VITRINE", "2026-06-24-vitrine", slug="vitrine-busca-ia")
    return reg

def test_centralizar_copia_fila_para_canonica(tmp_path):
    fab = tmp_path / "FAB"; fila = tmp_path / "fila"
    src = fila / "2026-06-24-vitrine"; src.mkdir(parents=True)
    (src / "legenda.txt").write_text("leg", encoding="utf-8"); (src / "slide-00.png").write_bytes(b"x")
    migrados = centralizar_existentes(_reg(), fab, fila)
    dst = fab / "VITRINE" / "2026-06-24-vitrine"
    assert (dst / "legenda.txt").read_text(encoding="utf-8") == "leg"
    assert (dst / "slide-00.png").exists()
    assert "2026-06-24-vitrine" in migrados

def test_centralizar_idempotente(tmp_path):
    fab = tmp_path / "FAB"; fila = tmp_path / "fila"
    src = fila / "2026-06-24-vitrine"; src.mkdir(parents=True)
    (src / "legenda.txt").write_text("v1", encoding="utf-8")
    centralizar_existentes(_reg(), fab, fila)
    (fab / "VITRINE" / "2026-06-24-vitrine" / "legenda.txt").write_text("editado", encoding="utf-8")
    centralizar_existentes(_reg(), fab, fila)
    assert (fab / "VITRINE" / "2026-06-24-vitrine" / "legenda.txt").read_text(encoding="utf-8") == "editado"

def test_sincronizar_fila_inverso(tmp_path):
    fab = tmp_path / "FAB"; fila = tmp_path / "fila"
    canon = fab / "VITRINE" / "2026-06-24-vitrine"; canon.mkdir(parents=True)
    (canon / "legenda.txt").write_text("leg", encoding="utf-8"); (canon / "slide-00.png").write_bytes(b"x")
    sincronizar_fila(fab, fila, "vitrine", "2026-06-24-vitrine")
    assert (fila / "2026-06-24-vitrine" / "slide-00.png").exists()
```

**Implementação:**

```python
# stella/corpo/centralizar_conteudo.py
from __future__ import annotations
import shutil
from pathlib import Path
from stella.domain.registro_keywords import RegistroKeywords, normalizar_keyword

_NOMES = ("legenda.txt",)

def _copiar_assets(src_dir: Path, dst_dir: Path) -> bool:
    if not src_dir.exists():
        return False
    dst_dir.mkdir(parents=True, exist_ok=True)
    fontes = [src_dir / n for n in _NOMES] + sorted(src_dir.glob("slide-*.png"))
    entrou = False
    for src in fontes:
        if not src.exists():
            continue
        dst = dst_dir / src.name
        if dst.exists():
            continue
        tmp = dst.with_name(dst.name + ".tmp")
        shutil.copyfile(src, tmp)
        tmp.replace(dst)
        entrou = True
    return entrou

def centralizar_existentes(registro: RegistroKeywords, fab_root: Path, fila_root: Path) -> list[str]:
    migrados: list[str] = []
    for entrada in registro.keywords():
        norm = normalizar_keyword(entrada.keyword)
        for post_id in entrada.posts:
            if _copiar_assets(fila_root / post_id, fab_root / norm / post_id):
                migrados.append(post_id)
    return migrados

def sincronizar_fila(fab_root: Path, fila_root: Path, keyword: str, post_id: str) -> str:
    norm = normalizar_keyword(keyword)
    dst = fila_root / post_id
    _copiar_assets(fab_root / norm / post_id, dst)
    return str(dst)
```

Verifique: `uv run pytest tests/corpo/test_centralizar_conteudo.py -v` (PASS), ruff+mypy limpos.

---

## Task D — Comandos CLI

**Arquivos:** anexar 4 comandos ao fim de `stella/frontends/cli.py`; teste `tests/frontends/test_cli_conteudo.py`.

Consome Tasks A/B/C. Comandos: `conteudo-listar`, `conteudo-enviar`, `conteudo-centralizar`, `conteudo-sync-fila`.

**Teste:**

```python
# tests/frontends/test_cli_conteudo.py
from typer.testing import CliRunner
from stella.frontends.cli import app
from stella.domain.registro_keywords import RegistroKeywords

runner = CliRunner()

def test_conteudo_listar_imprime_posts(monkeypatch, tmp_path):
    reg = RegistroKeywords(); reg.registrar_post("VITRINE", "2026-06-24-vitrine", slug="s")
    reg_path = tmp_path / "registro-keywords.json"; reg.salvar(reg_path)
    monkeypatch.setattr("stella.frontends.cli._registro_path", lambda: reg_path)
    monkeypatch.setattr("stella.frontends.cli._fab_dir", lambda: tmp_path)
    res = runner.invoke(app, ["conteudo-listar", "VITRINE"])
    assert res.exit_code == 0
    assert "2026-06-24-vitrine" in res.stdout
```

**Implementação (anexar ao cli.py):**

```python
@app.command("conteudo-listar")
def conteudo_listar(keyword: str = typer.Argument(..., help="Keyword (ex.: VITRINE)")) -> None:
    """Lista os posts de uma keyword (para o Bruno escolher qual enviar)."""
    from stella.domain.pacote_conteudo import listar_posts
    from stella.domain.registro_keywords import RegistroKeywords
    reg = RegistroKeywords.carregar(_registro_path())
    posts = listar_posts(reg, keyword, _fab_dir())
    if not posts:
        typer.echo(f"Senhor, não há posts para '{keyword}'."); raise typer.Exit(code=1)
    for p in posts:
        typer.echo(f"{p.post_id}\t{p.data}")

@app.command("conteudo-enviar")
def conteudo_enviar(
    keyword: str = typer.Argument(...),
    post_id: str = typer.Argument(...),
    telegram: bool = typer.Option(False, "--telegram", help="Envia ao Telegram do Bruno"),
) -> None:
    """Monta o pacote do post (slides+legenda+PDF) e imprime os paths ou envia ao Telegram."""
    from stella.domain.pacote_conteudo import resolver_pacote
    from stella.domain.registro_keywords import RegistroKeywords
    reg = RegistroKeywords.carregar(_registro_path())
    pac = resolver_pacote(reg, keyword, post_id, _fab_dir())
    if telegram:
        from stella.adapters.telegram.arquivos import enviar_documento, enviar_foto
        from stella.corpo.daemon_telegram import load_secrets
        s = load_secrets()
        for png in pac.slides:
            enviar_foto(s.bot_token, s.chat_id, png)
        if pac.legenda:
            enviar_documento(s.bot_token, s.chat_id, pac.legenda, legenda="Legenda do post")
        if pac.material_pdf:
            enviar_documento(s.bot_token, s.chat_id, pac.material_pdf, legenda="Material rico")
        typer.echo("Senhor, pacote enviado ao Telegram.")
        return
    for caminho in [*pac.slides, pac.legenda, pac.material_pdf]:
        if caminho:
            typer.echo(str(caminho))

@app.command("conteudo-centralizar")
def conteudo_centralizar() -> None:
    """Migra (uma vez) a copy+slides existentes da fila para a pasta canônica da keyword."""
    from stella.config import StellaConfig
    from stella.corpo.centralizar_conteudo import centralizar_existentes
    from stella.domain.registro_keywords import RegistroKeywords
    reg = RegistroKeywords.carregar(_registro_path())
    fila = StellaConfig().vault_path / _FILA_DIR
    migrados = centralizar_existentes(reg, _fab_dir(), fila)
    typer.echo(f"OK: {len(migrados)} post(s) centralizado(s).")

@app.command("conteudo-sync-fila")
def conteudo_sync_fila(keyword: str = typer.Argument(...), post_id: str = typer.Argument(...)) -> None:
    """Espelha a pasta canônica do post para a fila do Postiz (publicação)."""
    from stella.config import StellaConfig
    from stella.corpo.centralizar_conteudo import sincronizar_fila
    fila = StellaConfig().vault_path / _FILA_DIR
    destino = sincronizar_fila(_fab_dir(), fila, keyword, post_id)
    typer.echo(f"OK: espelhado em {destino}")
```

Verifique: `uv run pytest tests/frontends/test_cli_conteudo.py -v` (PASS); `uv run stella --help` lista os 4 comandos; suíte completa sem regressão; ruff+mypy limpos.

---

## Definição de pronto (Frente B)
- 4 módulos/tasks acima verdes, cada um com teste.
- `uv run pytest` todo verde; ruff + format + mypy limpos. Nenhuma regressão.
- Árvore pronta (NÃO commitar). Avise o Claude para revisar e commitar na branch `feat/reforma-fabrica-materiais`.
- O Claude faz à parte: a atualização das personas (render canônico + ferramenta de recuperar conteúdo) e a execução da migração/smoke.
