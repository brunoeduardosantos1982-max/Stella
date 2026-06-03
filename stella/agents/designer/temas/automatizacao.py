"""Tema 'automatizacao' - starburst claro + promessa no topo."""

from __future__ import annotations

import html as _html

from stella.agents.designer.temas.base import FotoHeroContent

_HF = (
    "Homem careca apontando para cima com as duas maos, fundo claro quente com grande forma "
    "radial de raios de luz partindo do centro atras, expressao confiante, "
    "metade superior com fundo claro liso e vazio."
)


class AutomatizacaoRecipe:
    nome = "automatizacao"
    usa_soul = True

    def hf_prompt(self) -> str:
        return _HF

    def html(self, c: FotoHeroContent, hero_data_uri: str) -> str:
        head = _html.escape(c.headline).replace("\n", "<br>")
        sublabel = _html.escape(c.sublabel or "")
        counter = _html.escape(c.counter or "")
        return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@800;900&family=Caveat:wght@700&family=JetBrains+Mono:wght@600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}} html,body{{width:1080px;height:1350px;overflow:hidden}}
.stage{{position:relative;width:1080px;height:1350px;background:#f4f1ea;font-family:'Archivo',sans-serif;display:flex;flex-direction:column}}
.top{{position:relative;height:560px;padding:70px 64px 0;text-align:center}}
.headline{{font-size:74px;font-weight:900;line-height:1.0;letter-spacing:-.02em;color:#15140f;text-transform:uppercase}}
.headline .s{{font-family:'Caveat';font-weight:700;font-size:120px;color:#E8632A;text-transform:none;display:block;line-height:.8;margin:6px 0}}
.chip{{display:inline-block;margin-top:18px;background:#15140f;color:#fff;font-family:'JetBrains Mono';font-weight:600;font-size:30px;padding:12px 28px;border-radius:10px}}
.bottom{{position:relative;flex:1;overflow:hidden}}
.burst{{position:absolute;left:50%;top:-40px;transform:translateX(-50%);width:560px;height:560px;border-radius:50%;
  background:repeating-conic-gradient(from 0deg,#E8915A 0 5deg,transparent 5deg 15deg);opacity:.5;
  -webkit-mask:radial-gradient(circle,#000 24%,transparent 68%)}}
.bg{{position:absolute;left:50%;bottom:0;transform:translateX(-50%);width:1080px;height:760px;object-fit:cover;object-position:center 18%}}
.handle{{position:absolute;bottom:40px;left:50%;transform:translateX(-50%);font-family:'JetBrains Mono';font-size:24px;color:#fff;text-shadow:0 2px 8px #000;z-index:3}}
.counter{{position:absolute;top:44px;right:56px;font-family:'JetBrains Mono';font-size:22px;color:#9a9384;letter-spacing:.1em;z-index:3}}
</style></head><body><div class="stage">
<div class="counter">{counter}</div>
<div class="top">
  <div class="headline">{head}</div>
  <div class="chip">{sublabel}</div>
</div>
<div class="bottom">
  <div class="burst"></div>
  <img class="bg" src="{hero_data_uri}">
  <div class="handle">@mktmagneto.ia</div>
</div>
</div></body></html>"""
