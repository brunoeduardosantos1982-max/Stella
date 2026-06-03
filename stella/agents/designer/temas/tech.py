"""Tema 'tech' - servidor futurista + paineis holograficos."""

from __future__ import annotations

import html as _html

from stella.agents.designer.temas.base import FotoHeroContent

_HF = (
    "Retrato do homem careca de camisa escura em sala de servidores/centro de dados futurista, "
    "paineis holograficos azuis abstratos ao redor, luz ciano, "
    "atmosfera imersiva premium, foto editorial, ampla area lisa e vazia na base."
)


class TechRecipe:
    nome = "tech"
    usa_soul = True

    def hf_prompt(self) -> str:
        return _HF

    def html(self, c: FotoHeroContent, hero_data_uri: str) -> str:
        notas = (c.anotacoes + ["", "", ""])[:3]
        head = _html.escape(c.headline).replace("\n", "<br>")
        sublabel = _html.escape(c.sublabel or "")
        counter = _html.escape(c.counter or "")
        return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}} html,body{{width:1080px;height:1350px;overflow:hidden}}
.stage{{position:relative;width:1080px;height:1350px;background:#0a0f1a;font-family:'Space Grotesk',sans-serif}}
.bg{{position:absolute;inset:0;width:1080px;height:1350px;object-fit:cover;object-position:center 35%;opacity:.82}}
.tint{{position:absolute;inset:0;background:radial-gradient(120% 80% at 50% 18%, rgba(34,211,238,.18), rgba(10,15,26,0) 55%),linear-gradient(180deg, rgba(10,15,26,.55) 0%, rgba(10,15,26,0) 30%, rgba(10,15,26,.2) 55%, rgba(10,15,26,.92) 86%)}}
.brand{{position:absolute;top:54px;left:50%;transform:translateX(-50%);font-family:'JetBrains Mono';font-weight:700;font-size:30px;color:#eaf6ff;letter-spacing:.02em}}
.brand i{{color:#22D3EE;font-style:normal}}
.counter{{position:absolute;top:56px;right:60px;font-family:'JetBrains Mono';font-size:22px;color:#7fbdd0;letter-spacing:.1em}}
/* paineis holograficos */
.ui{{position:absolute;border:1px solid rgba(34,211,238,.45);border-radius:14px;background:rgba(8,20,32,.55);
    padding:18px 22px;backdrop-filter:blur(2px);box-shadow:0 0 30px rgba(34,211,238,.12) inset}}
.ui .lbl{{font-family:'JetBrains Mono';font-size:18px;letter-spacing:.12em;color:#22D3EE;text-transform:uppercase}}
.ui .val{{font-family:'Space Grotesk';font-weight:600;font-size:26px;color:#eaf6ff;margin-top:8px;line-height:1.15}}
.ui.a{{top:300px;left:50px;width:300px}} .ui.b{{top:300px;right:50px;width:300px;text-align:right}}
.ui.c{{top:520px;left:50px;width:270px}}
/* headline base */
.headline{{position:absolute;left:60px;right:60px;bottom:230px;font-size:104px;font-weight:700;line-height:.96;
    letter-spacing:-.02em;text-transform:uppercase;color:#F4F4F6;text-shadow:0 4px 30px rgba(0,0,0,.5)}}
.headline .hl{{color:#22D3EE}}
.sub{{position:absolute;left:62px;right:62px;bottom:150px;font-family:'JetBrains Mono';font-size:30px;color:#bcd9e3}}
.handle{{position:absolute;bottom:60px;left:62px;font-family:'JetBrains Mono';font-size:24px;color:#7fbdd0}}
.handle b{{color:#22D3EE;font-weight:400}}
</style></head><body><div class="stage">
<img class="bg" src="{hero_data_uri}">
<div class="tint"></div>
<div class="brand">&#9670; <i>mktmagneto</i>.ia</div>
<div class="counter">{counter}</div>
<div class="ui a"><div class="lbl">// agente</div><div class="val">{_html.escape(notas[0])}</div></div>
<div class="ui b"><div class="lbl">resposta</div><div class="val">{_html.escape(notas[1])}</div></div>
<div class="ui c"><div class="lbl">// status</div><div class="val">{_html.escape(notas[2])}</div></div>
<div class="headline">{head}</div>
<div class="sub">&gt; {sublabel}</div>
<div class="handle">@<b>mktmagneto.ia</b></div>
</div></body></html>"""
