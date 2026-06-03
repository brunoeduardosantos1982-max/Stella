"""Tema 'autoridade' - retrato quente e sofisticado."""

from __future__ import annotations

import html as _html

from stella.agents.designer.temas.base import FotoHeroContent

_HF = (
    "Retrato lateral cinematografico do homem careca, ambiente sofisticado "
    "(biblioteca/escritorio escuro), luz quente premium, profundidade, ampla area lisa e vazia na base."
)


class AutoridadeRecipe:
    nome = "autoridade"
    usa_soul = True

    def hf_prompt(self) -> str:
        return _HF

    def html(self, c: FotoHeroContent, hero_data_uri: str) -> str:
        head = _html.escape(c.headline).replace("\n", "<br>")
        label = _html.escape(c.label_topo or "")
        counter = _html.escape(c.counter or "")
        return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}} html,body{{width:1080px;height:1350px;overflow:hidden}}
.stage{{position:relative;width:1080px;height:1350px;background:#140d07;font-family:'Space Grotesk',sans-serif}}
.bg{{position:absolute;inset:0;width:1080px;height:1350px;object-fit:cover;object-position:65% 35%}}
.warm{{position:absolute;inset:0;background:radial-gradient(80% 60% at 22% 30%, rgba(232,150,60,.30), rgba(20,13,7,0) 60%),linear-gradient(180deg, rgba(20,13,7,.5) 0%, rgba(20,13,7,0) 35%, rgba(20,13,7,.55) 62%, rgba(20,13,7,.95) 88%)}}
.burst{{position:absolute;top:200px;left:90px;width:360px;height:360px;border-radius:50%;
  background:repeating-conic-gradient(from 0deg,#E8A24a 0 5deg,transparent 5deg 15deg);opacity:.55;
  -webkit-mask:radial-gradient(circle,#000 26%,transparent 70%);filter:blur(.4px)}}
.eyebrow{{position:absolute;top:62px;left:64px;font-family:'JetBrains Mono';font-size:24px;letter-spacing:.14em;color:#E8A24a;text-transform:uppercase}}
.counter{{position:absolute;top:62px;right:60px;font-family:'JetBrains Mono';font-size:22px;color:#c9a786;letter-spacing:.1em}}
.headline{{position:absolute;left:64px;right:64px;bottom:190px;font-size:96px;font-weight:700;line-height:1.0;letter-spacing:-.02em;color:#F6EFE6;text-shadow:0 4px 30px rgba(0,0,0,.55)}}
.headline .y{{color:#F4C24a}}
.handle{{position:absolute;bottom:60px;left:64px;font-family:'JetBrains Mono';font-size:24px;color:#c9a786}}
.handle b{{color:#F4C24a;font-weight:400}}
</style></head><body><div class="stage">
<img class="bg" src="{hero_data_uri}">
<div class="warm"></div><div class="burst"></div>
<div class="eyebrow">{label}</div>
<div class="counter">{counter}</div>
<div class="headline">{head}</div>
<div class="handle">@<b>mktmagneto.ia</b></div>
</div></body></html>"""
