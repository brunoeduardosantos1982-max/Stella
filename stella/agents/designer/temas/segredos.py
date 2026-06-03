"""Tema 'segredos' - layout claro com lista de comandos/cards."""

from __future__ import annotations

import html as _html

from stella.agents.designer.temas.base import FotoHeroContent

_HF = (
    "(sem foto) fundo claro off-white minimalista; "
    "o html gera o layout claro com icone/estrela 3D em CSS."
)


class SegredosRecipe:
    nome = "segredos"
    usa_soul = False

    def hf_prompt(self) -> str:
        return _HF

    def html(self, c: FotoHeroContent, hero_data_uri: str) -> str:
        del hero_data_uri
        notas = (c.anotacoes + ["", "", "", "", ""])[:5]
        cards = "\n".join(
            f'  <div class="card"><span class="k">&gt; {i:02d}</span>'
            f'<span class="d">{_html.escape(nota)}</span></div>'
            for i, nota in enumerate(notas, start=1)
            if nota
        )
        head = _html.escape(c.headline).replace("\n", "<br>")
        label = _html.escape(c.label_topo or "")
        sublabel = _html.escape(c.sublabel or "")
        return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}} html,body{{width:1080px;height:1350px;overflow:hidden}}
.stage{{position:relative;width:1080px;height:1350px;background:#f4f1ea;font-family:'Space Grotesk',sans-serif;padding:80px 70px}}
.eyebrow{{font-family:'JetBrains Mono';font-weight:600;font-size:24px;letter-spacing:.14em;color:#E8632A;text-transform:uppercase}}
.title{{font-size:84px;font-weight:700;line-height:.98;letter-spacing:-.02em;color:#15140f;margin-top:14px}}
.title .o{{color:#E8632A}}
.rule{{width:120px;height:8px;background:#E8632A;border-radius:4px;margin:26px 0 10px}}
.lead{{font-size:30px;color:#5a554a;line-height:1.35;max-width:760px}}
.cards{{display:flex;flex-direction:column;gap:18px;margin-top:46px}}
.card{{display:flex;align-items:baseline;gap:22px;background:#fffdf8;border:1px solid #e7e0d2;border-radius:16px;padding:24px 28px;box-shadow:0 6px 18px rgba(0,0,0,.04)}}
.card .k{{font-family:'JetBrains Mono';font-weight:600;font-size:30px;color:#E8632A;min-width:230px}}
.card .d{{font-size:27px;color:#3a362e;line-height:1.25}}
.handle{{position:absolute;bottom:54px;left:70px;font-family:'JetBrains Mono';font-size:24px;color:#9a9384}}
.handle b{{color:#E8632A;font-weight:400}}
.glow{{position:absolute;right:-120px;top:-120px;width:420px;height:420px;border-radius:50%;background:#E8632A;opacity:.10;filter:blur(120px)}}
</style></head><body><div class="stage">
<div class="glow"></div>
<div class="eyebrow">{label}</div>
<div class="title">{head}</div>
<div class="rule"></div>
<div class="lead">{sublabel}</div>
<div class="cards">
{cards}
</div>
<div class="handle">@<b>mktmagneto.ia</b></div>
</div></body></html>"""
