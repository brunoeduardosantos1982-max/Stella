"""Tema 'conceito' - cena cinematografica surreal com luz vertical."""

from __future__ import annotations

import html as _html

from stella.agents.designer.temas.base import FotoHeroContent

_HF = (
    "Cena conceitual cinematografica dramatica do homem careca em pose inusitada, luz laranja "
    "vertical em fundo escuro, atmosfera surreal premium, muito espaco negativo liso ao redor."
)


class ConceitoRecipe:
    nome = "conceito"
    usa_soul = True

    def hf_prompt(self) -> str:
        return _HF

    def html(self, c: FotoHeroContent, hero_data_uri: str) -> str:
        head = _html.escape(c.headline).replace("\n", "<br>")
        sublabel = _html.escape(c.sublabel or "")
        counter = _html.escape(c.counter or "")
        return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@800;900&family=Playfair+Display:ital,wght@1,700&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}} html,body{{width:1080px;height:1350px;overflow:hidden}}
.stage{{position:relative;width:1080px;height:1350px;background:#0a0805;font-family:'Archivo',sans-serif}}
.bg{{position:absolute;inset:0;width:1080px;height:1350px;object-fit:cover;object-position:center 32%}}
.beam{{position:absolute;inset:0;background:linear-gradient(90deg,rgba(10,8,5,.92)0%,rgba(10,8,5,.35)28%,rgba(232,99,42,.18)50%,rgba(10,8,5,.4)72%,rgba(10,8,5,.92)100%),linear-gradient(180deg,rgba(10,8,5,.5)0%,rgba(10,8,5,0)35%,rgba(10,8,5,.96)82%)}}
.counter{{position:absolute;top:54px;right:58px;font-family:'JetBrains Mono';font-size:22px;color:#e8d9cf;letter-spacing:.1em}}
.headline{{position:absolute;left:60px;right:60px;bottom:250px;font-size:108px;font-weight:900;line-height:.92;letter-spacing:-.02em;color:#F6F2EE;text-transform:uppercase;text-shadow:0 4px 30px rgba(0,0,0,.6)}}
.headline .it{{font-family:'Playfair Display',serif;font-style:italic;font-weight:700;text-transform:none;color:#E8915A}}
.chip{{position:absolute;left:62px;bottom:170px;background:#e23b2e;color:#fff;font-weight:900;font-size:30px;padding:12px 26px;border-radius:8px;text-transform:uppercase;letter-spacing:.03em}}
.handle{{position:absolute;bottom:70px;left:62px;font-family:'JetBrains Mono';font-size:24px;color:#c9b6a8}}
</style></head><body><div class="stage">
<img class="bg" src="{hero_data_uri}">
<div class="beam"></div>
<div class="counter">{counter}</div>
<div class="headline">{head}</div>
<div class="chip">{sublabel}</div>
<div class="handle">@mktmagneto.ia</div>
</div></body></html>"""
