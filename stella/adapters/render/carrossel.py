"""Motor de carrossel @brunoe.santos, modo Autoridade "Field Manual escuro" (F2.1).

Porte do motor standalone (FABRICADECONTEUDO/motor/gerar_carrossel.py) para dentro
do repo. Os builders de HTML (capa/conteudo/cta) são puros e testáveis; a
renderização PNG é um wrapper fino sobre o Chrome headless (1080x1350).
"""

from __future__ import annotations

import html as _html
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

HEAD = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=JetBrains+Mono:wght@500;700&family=Fraunces:ital,opsz,wght@1,9..144,500;1,9..144,600&display=swap" rel="stylesheet">
<style>
:root{--bg:#0d0d0f;--ink:#f4f4f6;--muted:#9a9aa2;--meta:#6a6a72;--cyan:#22d3ee;--line:#26262d}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1350px}
body{background:radial-gradient(circle at 88% -6%,rgba(34,211,238,.13),transparent 32rem),
 linear-gradient(var(--line) 1px,transparent 1px) 0 0/100% 54px,
 linear-gradient(90deg,var(--line) 1px,transparent 1px) 0 0/54px 100%,var(--bg);
 background-blend-mode:normal,soft-light,soft-light,normal;color:var(--ink);
 font-family:'Space Grotesk',sans-serif;padding:78px 82px;display:flex;flex-direction:column}
.hdr{display:flex;justify-content:space-between;align-items:center;font-family:'JetBrains Mono',monospace;
 font-size:21px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.hdr .me{display:flex;align-items:center;gap:.7rem;color:var(--ink)}
.dot{width:11px;height:11px;border-radius:999px;background:var(--cyan);box-shadow:0 0 18px rgba(34,211,238,.85)}
.hdr .ct{color:var(--cyan)}
.rule{height:1px;background:var(--line);margin:26px 0 0}
.kick{font-family:'JetBrains Mono',monospace;font-size:22px;letter-spacing:.16em;text-transform:uppercase;color:var(--cyan)}
.selo{align-self:flex-start;width:fit-content;font-family:'JetBrains Mono',monospace;font-size:21px;letter-spacing:.16em;
 text-transform:uppercase;color:var(--cyan);border:1px solid rgba(34,211,238,.45);border-radius:999px;padding:10px 20px}
.box{background:var(--cyan);color:#071013;font-style:italic;padding:0 .16em;border-radius:10px}
.serif{font-family:'Fraunces',serif;font-style:italic;font-weight:600;color:var(--cyan)}
.spacer{flex:1}
.ftr{display:flex;justify-content:space-between;align-items:flex-end;gap:30px}
.ftr .h{display:flex;align-items:center;gap:.6rem;font-weight:700;font-size:30px}
.ftr .c{font-family:'JetBrains Mono',monospace;font-size:20px;color:var(--meta);text-align:right;max-width:430px;line-height:1.4}
.cp-title{margin-top:22px;font-weight:700;font-size:118px;line-height:.98;letter-spacing:-.01em;text-transform:uppercase}
.cp-serif{display:block;margin-top:14px;text-transform:none;font-size:88px;line-height:1.02}
.cp-sub{margin-top:50px;font-family:'JetBrains Mono',monospace;font-size:26px;color:var(--muted)}
.cp-sub b{color:var(--ink);font-weight:700}
.ct-title{margin-top:24px;font-weight:700;font-size:74px;line-height:1.02;letter-spacing:-.01em}
.ct-title .serif{font-size:1em}
.steps{margin-top:50px;display:flex;flex-direction:column;gap:34px}
.step{display:flex;gap:30px;align-items:flex-start}
.num{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:42px;line-height:1;color:var(--cyan);flex:none;width:88px;height:88px;border-radius:999px;background:rgba(34,211,238,.12);border:1px solid rgba(34,211,238,.5);display:flex;align-items:center;justify-content:center}
.st-h{font-weight:700;font-size:38px;line-height:1.1}
.st-b{margin-top:8px;font-size:27px;line-height:1.4;color:var(--muted)}
.mid{flex:1;display:flex;flex-direction:column;justify-content:center}
.cta-big{margin-top:18px;font-weight:700;font-size:104px;line-height:.98;letter-spacing:-.01em;text-transform:uppercase}
.cta-big .serif{display:block;text-transform:none;font-size:60px;margin-top:10px}
.icons{display:flex;align-items:center;gap:34px;margin-top:56px}
.icons svg{width:54px;height:54px;stroke:var(--muted);fill:none;stroke-width:2.2}
.icons .save{stroke:var(--cyan);fill:rgba(34,211,238,.12)}
.savetag{font-family:'JetBrains Mono',monospace;font-size:24px;color:var(--cyan);letter-spacing:.08em}
.comenta{margin-top:34px;font-size:30px;color:var(--ink)}
.comenta b{color:var(--cyan)}
</style></head><body>"""

FOOT = "</body></html>"
TAGLINE = "marketing com IA · da estratégia à solução implantada"
ICONS = (
    '<svg viewBox="0 0 24 24"><path d="M12 21s-7-4.35-9.5-8.5C1 9 3 5.5 6.5 5.5 8.5 5.5 10 7 12 9c2-2 3.5-3.5 5.5-3.5C21 5.5 23 9 21.5 12.5 19 16.65 12 21 12 21z"/></svg>'
    '<svg viewBox="0 0 24 24"><path d="M21 11.5a8.5 8.5 0 0 1-12.3 7.6L3 21l1.9-5.7A8.5 8.5 0 1 1 21 11.5z"/></svg>'
    '<svg class="save" viewBox="0 0 24 24"><path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z"/></svg>'
    '<svg viewBox="0 0 24 24"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>'
)

_CHROME_CANDIDATOS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)


def _hdr(cat: str, i: int, n: int) -> str:
    return (
        f'<div class="hdr"><span class="me"><span class="dot"></span>@brunoe.santos</span>'
        f'<span><span class="ct">{_html.escape(cat)}</span> &nbsp;·&nbsp; {i:02d} / {n:02d}</span></div>'
        f'<div class="rule"></div>'
    )


def _ftr(tagline: bool = True) -> str:
    c = f'<span class="c">{TAGLINE}</span>' if tagline else '<span class="c"></span>'
    return (
        f'<div class="ftr"><span class="h"><span class="dot"></span>@brunoe.santos</span>{c}</div>'
    )


def _capa(d: dict[str, Any], i: int, n: int, cat: str) -> str:
    serif = f'<span class="cp-serif serif">{d["serif"]}</span>' if d.get("serif") else ""
    sub = f'<p class="cp-sub">{d["sub"]}</p>' if d.get("sub") else ""
    return (
        HEAD
        + _hdr(cat, i, n)
        + f'<div class="kick" style="margin-top:96px">{_html.escape(d.get("kick", "field note"))}</div>'
        + f'<h1 class="cp-title fit">{d["titulo"]}</h1>{serif}{sub}'
        + '<div class="spacer"></div>'
        + _ftr(False)
        + FOOT
    )


def _conteudo(d: dict[str, Any], i: int, n: int, cat: str) -> str:
    selo = (
        f'<span class="selo" style="margin-top:60px">{_html.escape(d.get("selo", "passo a passo"))}</span>'
        if d.get("selo")
        else ""
    )
    steps = "".join(
        f'<div class="step"><div class="num">{p[0]}</div><div>'
        f'<div class="st-h">{p[1]}</div><div class="st-b">{p[2]}</div></div></div>'
        for p in d["passos"]
    )
    return (
        HEAD
        + _hdr(cat, i, n)
        + selo
        + f'<h2 class="ct-title fit">{d["titulo"]}</h2>'
        + f'<div class="steps">{steps}</div>'
        + '<div class="spacer"></div>'
        + _ftr(False)
        + FOOT
    )


def _cta(d: dict[str, Any], i: int, n: int, cat: str) -> str:
    serif = f'<span class="serif">{d["serif"]}</span>' if d.get("serif") else ""
    comenta = f'<p class="comenta">{d["comenta"]}</p>' if d.get("comenta") else ""
    return (
        HEAD
        + _hdr(cat, i, n)
        + f'<div class="mid"><span class="kick">{_html.escape(d.get("kick", "guarda pra depois"))}</span>'
        + f'<h2 class="cta-big fit">{d["titulo"]}{serif}</h2>'
        + f'<div class="icons">{ICONS}<span class="savetag">salva ↑</span></div>{comenta}</div>'
        + _ftr(True)
        + FOOT
    )


_BUILDERS = {"capa": _capa, "conteudo": _conteudo, "cta": _cta}


def montar_slide_html(slide: dict[str, Any], indice: int, total: int, categoria: str) -> str:
    """Monta o HTML de um slide. Levanta ValueError se o tipo for desconhecido."""
    tipo = slide.get("tipo")
    builder = _BUILDERS.get(str(tipo))
    if builder is None:
        raise ValueError(f"tipo de slide desconhecido: {tipo!r}")
    return builder(slide, indice, total, categoria)


def montar_slides_html(post: dict[str, Any]) -> list[str]:
    """Monta um HTML por slide do post (na ordem)."""
    slides = post["slides"]
    total = len(slides)
    categoria = post.get("categoria", "IA & MARKETING")
    return [montar_slide_html(s, i, total, categoria) for i, s in enumerate(slides, start=1)]


def detectar_chrome(chrome: str | None = None) -> str:
    """Devolve o caminho do Chrome/Edge. Usa o argumento, senão tenta os candidatos."""
    if chrome:
        return chrome
    for cand in _CHROME_CANDIDATOS:
        if os.path.exists(cand):
            return cand
    raise RuntimeError("Chrome/Edge não encontrado; passe o caminho via --chrome.")


def _render_png(html_str: str, out: str, chrome: str) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        page = os.path.join(tmp, "p.html")
        with open(page, "w", encoding="utf-8") as f:
            f.write(html_str)
        prof = os.path.join(tmp, "prof")
        subprocess.run(
            [
                chrome,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--hide-scrollbars",
                "--allow-file-access-from-files",
                "--force-device-scale-factor=1",
                f"--user-data-dir={prof}",
                "--window-size=1080,1350",
                "--virtual-time-budget=20000",
                f"--screenshot={out}",
                "file://" + page.replace("\\", "/"),
            ],
            capture_output=True,
            timeout=90,
        )
    return os.path.exists(out)


def renderizar_post(
    post: dict[str, Any], outdir: str | Path, *, chrome: str | None = None
) -> list[tuple[Path, bool]]:
    """Renderiza todos os slides do post em PNG slide-NN.png em outdir."""
    chrome_bin = detectar_chrome(chrome)
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    htmls = montar_slides_html(post)
    feitos: list[tuple[Path, bool]] = []
    for i, html_str in enumerate(htmls):
        out = outdir / f"slide-{i:02d}.png"
        ok = _render_png(html_str, str(out.resolve()), chrome_bin)
        feitos.append((out, ok))
    return feitos
