"""Tema 'dicas' - fundo quente monocromatico + tipografia gigante."""

from __future__ import annotations

import html as _html

from stella.agents.designer.temas.base import FotoHeroContent

_HF = (
    "Homem careca em angulo alto sobre fundo monocromatico quente (pessego/laranja) "
    "casado com a roupa, segurando um objeto em direcao a camera, clean, "
    "ampla area lisa e vazia ao redor."
)


class DicasRecipe:
    nome = "dicas"
    usa_soul = True

    def hf_prompt(self) -> str:
        return _HF

    def html(self, c: FotoHeroContent, hero_data_uri: str) -> str:
        head = _html.escape(c.headline).replace("\n", "<br>")
        label = _html.escape(c.label_topo or "")
        sublabel = _html.escape(c.sublabel or "")
        counter = _html.escape(c.counter or "")
        return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&family=Caveat:wght@700&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}} html,body{{width:1080px;height:1350px;overflow:hidden}}
.stage{{position:relative;width:1080px;height:1350px;background:#E8915A;font-family:'Space Grotesk',sans-serif}}
.bg{{position:absolute;inset:0;width:1080px;height:1350px;object-fit:cover;object-position:center 30%}}
.mono{{position:absolute;inset:0;background:#E8915A;mix-blend-mode:color;opacity:.62}}
.shade{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(120,60,25,.25)0%,rgba(120,60,25,0)40%,rgba(90,40,15,.65)100%)}}
.counter{{position:absolute;top:58px;right:60px;font-family:'Caveat';font-weight:700;font-size:34px;color:#fff3e9}}
.kicker{{position:absolute;left:70px;bottom:300px;font-weight:700;font-size:40px;letter-spacing:.02em;color:#fff3e9;text-transform:uppercase}}
.headline{{position:absolute;left:64px;right:64px;bottom:150px;font-size:170px;font-weight:700;line-height:.82;letter-spacing:-.03em;color:#fffaf3;text-shadow:0 6px 30px rgba(80,35,10,.5)}}
.sub{{position:absolute;left:72px;bottom:78px;font-family:'Caveat';font-weight:700;font-size:54px;color:#fff3e9}}
</style></head><body><div class="stage">
<img class="bg" src="{hero_data_uri}">
<div class="mono"></div><div class="shade"></div>
<div class="counter">{counter}</div>
<div class="kicker">{label}</div>
<div class="headline">{head}</div>
<div class="sub">{sublabel}</div>
</div></body></html>"""
