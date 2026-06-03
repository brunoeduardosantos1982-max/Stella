"""Tema 'impactante' - retrato dramatico + headline de choque."""

from __future__ import annotations

import html as _html

from stella.agents.designer.temas.base import FotoHeroContent

_HF = (
    "Homem careca com expressao de CHOQUE/surpresa (maos no rosto) em sala de servidores "
    "com fundo de circuito, luz fria dramatica, alto contraste, ampla area inferior preta lisa e vazia."
)


class ImpactanteRecipe:
    nome = "impactante"
    usa_soul = True

    def hf_prompt(self) -> str:
        return _HF

    def html(self, c: FotoHeroContent, hero_data_uri: str) -> str:
        head = _html.escape(c.headline).replace("\n", "<br>")
        sublabel = _html.escape(c.sublabel or "")
        counter = _html.escape(c.counter or "")
        return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@800;900&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}} html,body{{width:1080px;height:1350px;overflow:hidden}}
.stage{{position:relative;width:1080px;height:1350px;background:#000;font-family:'Archivo',sans-serif;display:flex;flex-direction:column}}
.top{{position:relative;height:760px;overflow:hidden}}
.bg{{position:absolute;inset:0;width:1080px;height:760px;object-fit:cover;object-position:center 30%}}
.topfade{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.45)0%,rgba(0,0,0,0)35%,rgba(0,0,0,.95)100%)}}
.brandmark{{position:absolute;left:50%;bottom:14px;transform:translateX(-50%);font-family:'JetBrains Mono';font-weight:700;font-size:30px;color:#fff;letter-spacing:.02em;text-shadow:0 2px 12px #000}}
.brandmark i{{color:#22D3EE;font-style:normal}}
.counter{{position:absolute;top:48px;right:56px;font-family:'JetBrains Mono';font-size:22px;color:#cfe9f2;letter-spacing:.1em}}
.bottom{{flex:1;background:#000;padding:50px 60px 0}}
.hl-block{{font-size:86px;font-weight:900;line-height:.98;letter-spacing:-.02em;text-transform:uppercase;color:#F4F4F6}}
.hl-block br + *{{color:#22D3EE}}
.sub{{margin-top:26px;font-family:'JetBrains Mono';font-weight:500;font-size:30px;color:#9fb6bf}}
.handle{{position:absolute;bottom:56px;left:60px;font-family:'JetBrains Mono';font-size:24px;color:#7fbdd0}}
</style></head><body><div class="stage">
<div class="top">
  <img class="bg" src="{hero_data_uri}">
  <div class="topfade"></div>
  <div class="counter">{counter}</div>
  <div class="brandmark">&#9670; <i>mktmagneto</i>.ia</div>
</div>
<div class="bottom">
  <div class="hl-block">{head}</div>
  <div class="sub">&gt; {sublabel}</div>
</div>
<div class="handle">@mktmagneto.ia</div>
</div></body></html>"""
