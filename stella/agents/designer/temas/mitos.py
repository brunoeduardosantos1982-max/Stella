"""Tema 'mitos' - flat-lay top-down + tipografia laranja gigante."""

from __future__ import annotations

import html as _html
from importlib import resources

from stella.agents.designer.temas.base import FotoHeroContent

_HF = (
    "Fotografia vista DE CIMA (top-down, bird eye view) de um homem COMPLETAMENTE CARECA "
    "cabeca raspada, barba curta, vestido com camisa escura, em pe no centro olhando para cima "
    "para a camera, sobre piso de concreto industrial; objetos tech ao redor em flat-lay "
    "(laptop, smartphone, fones, caneca, caderno); iluminacao cinematografica, tons quentes, "
    "muito espaco vazio no centro-inferior; foto editorial premium"
)


def _svg(nome: str, fill: str) -> str:
    try:
        raw = (resources.files("stella.agents.designer.temas.assets") / f"{nome}.svg").read_text(
            encoding="utf-8"
        )
    except (FileNotFoundError, ModuleNotFoundError):
        return ""
    return raw.replace("<svg ", f'<svg fill="{fill}" width="60" height="60" ')


class MitosRecipe:
    nome = "mitos"
    usa_soul = True

    def hf_prompt(self) -> str:
        return _HF

    def html(self, c: FotoHeroContent, hero_data_uri: str) -> str:
        notas = (c.anotacoes + ["", ""])[:2]
        logos_html = "".join(
            _svg("claude", "#E8632A") if n == "claude" else _svg("openai", "#FFFFFF")
            for n in c.logos
        )
        head = _html.escape(c.headline).replace("\n", "<br>")
        label = _html.escape(c.label_topo or "").replace("\n", "<br>")
        return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Caveat:wght@700&family=Archivo:wght@700;900&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}} html,body{{width:1080px;height:1350px;overflow:hidden}}
.stage{{position:relative;width:1080px;height:1350px;background:#0d0d0f;font-family:'Archivo',sans-serif}}
.bg{{position:absolute;inset:0;width:1080px;height:1350px;object-fit:cover;object-position:center 42%}}
.shade{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(13,13,15,.62)0%,rgba(13,13,15,.12)20%,rgba(13,13,15,0)46%,rgba(13,13,15,.55)80%,rgba(13,13,15,.9)100%)}}
.toplabel{{position:absolute;top:52px;left:60px;font-weight:900;font-size:34px;color:#F4F4F6;text-transform:uppercase;line-height:1}}
.brand{{position:absolute;top:56px;right:62px;font-family:'JetBrains Mono';font-weight:700;font-size:28px;color:#F4F4F6}}
.brand i{{color:#E8632A;font-style:normal}}
.counter{{position:absolute;top:100px;right:62px;font-family:'JetBrains Mono';font-size:22px;color:#cdcdcd;letter-spacing:.1em}}
.logos{{position:absolute;top:150px;left:50%;transform:translateX(-50%);display:flex;align-items:center;gap:24px;padding:16px 30px;background:rgba(13,13,15,.5);border:1px solid rgba(255,255,255,.14);border-radius:60px}}
.logos svg{{width:60px;height:60px;display:block}}
.logos .plus{{font-weight:800;font-size:32px;color:#b8b8b8}}
.note{{position:absolute;font-family:'Caveat',cursive;font-weight:700;color:#f4f4f6;font-size:46px;line-height:1;text-shadow:0 2px 10px rgba(0,0,0,.6)}}
.note.l{{left:34px;top:262px;transform:rotate(-8deg)}} .note.r{{right:30px;top:300px;transform:rotate(7deg);text-align:right}}
.headline{{position:absolute;left:50%;transform:translateX(-50%);bottom:236px;width:100%;text-align:center;font-family:'Anton';color:#E8632A;font-size:172px;line-height:.86;text-transform:uppercase;text-shadow:0 6px 34px rgba(0,0,0,.55)}}
.sub{{position:absolute;left:50%;transform:translateX(-50%);bottom:150px;text-align:center;font-weight:900;font-size:32px;color:#0d0d0f;background:#E8632A;padding:12px 28px;text-transform:uppercase}}
.handle{{position:absolute;bottom:58px;left:50%;transform:translateX(-50%);font-family:'JetBrains Mono';font-size:24px;color:#d2d2d2}}
</style></head><body><div class="stage">
<img class="bg" src="{hero_data_uri}"><div class="shade"></div>
<div class="toplabel">{label}</div>
<div class="brand">&#10022; <i>mktmagneto</i>.ia</div>
<div class="counter">{_html.escape(c.counter or "")}</div>
<div class="logos">{logos_html}<span class="plus">+</span></div>
<div class="note l">{_html.escape(notas[0])}</div>
<div class="note r">{_html.escape(notas[1])}</div>
<div class="headline">{head}</div>
<div class="sub">{_html.escape(c.sublabel or "")}</div>
<div class="handle">@mktmagneto.ia</div>
</div></body></html>"""
