"""Tema 'ferramentas' - foto espontanea estilo celular + selo de nicho."""

from __future__ import annotations

import html as _html

from stella.agents.designer.temas.base import FotoHeroContent

_HF = (
    "Foto espontanea estilo celular do homem careca ao ar livre/urbano, luz natural, casual, "
    "espaco na base p/ headline branca + selo de nicho."
)


class FerramentasRecipe:
    nome = "ferramentas"
    usa_soul = True

    def hf_prompt(self) -> str:
        return _HF

    def html(self, c: FotoHeroContent, hero_data_uri: str) -> str:
        head = _html.escape(c.headline).replace("\n", "<br>")
        label = _html.escape(c.label_topo or "")
        sublabel = _html.escape(c.sublabel or "")
        counter = _html.escape(c.counter or "")
        return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@700;900&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}} html,body{{width:1080px;height:1350px;overflow:hidden}}
.stage{{position:relative;width:1080px;height:1350px;background:#0d0d0f;font-family:'Archivo',sans-serif}}
.bg{{position:absolute;inset:0;width:1080px;height:1350px;object-fit:cover;object-position:center 30%}}
.shade{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(13,13,15,.25)0%,rgba(13,13,15,0)42%,rgba(13,13,15,.9)100%)}}
.appicon{{position:absolute;top:300px;right:60px;width:120px;height:120px;border-radius:28px;background:#E8632A;display:flex;align-items:center;justify-content:center;box-shadow:0 14px 40px rgba(0,0,0,.45)}}
.appicon svg{{width:74px;height:74px}}
.counter{{position:absolute;top:54px;right:60px;font-family:'JetBrains Mono';font-size:22px;color:#e8e8e8;letter-spacing:.1em;text-shadow:0 2px 8px #000}}
.kicker{{position:absolute;left:64px;bottom:340px;font-family:'JetBrains Mono';font-weight:700;font-size:30px;letter-spacing:.06em;color:#fff;text-transform:uppercase;text-shadow:0 2px 10px #000}}
.headline{{position:absolute;left:60px;right:60px;bottom:190px;font-size:118px;font-weight:900;line-height:.9;letter-spacing:-.02em;color:#fff;text-transform:uppercase;text-shadow:0 4px 26px rgba(0,0,0,.6)}}
.pill{{position:absolute;left:64px;bottom:96px;background:#E8632A;color:#0d0d0f;font-weight:900;font-size:30px;padding:14px 30px;border-radius:40px;text-transform:uppercase;letter-spacing:.02em}}
</style></head><body><div class="stage">
<img class="bg" src="{hero_data_uri}">
<div class="shade"></div>
<div class="counter">{counter}</div>
<div class="appicon"><svg viewBox="0 0 24 24" fill="#fff"><path d="M12 2l1.6 6.1L19 4.9l-3.2 5.1 6.2.3-5.7 2.6 4.2 4.6-5.6-2.1L12 22l-1.1-6.5-5.6 2.1 4.2-4.6L3.8 10.3l6.2-.3L6.8 4.9 12.4 8.1z"/></svg></div>
<div class="kicker">{label}</div>
<div class="headline">{head}</div>
<div class="pill">{sublabel}</div>
</div></body></html>"""
