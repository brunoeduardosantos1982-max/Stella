"""Gerador da config do ManyChat por keyword (F2.3).

A partir de uma entrada do registro (keyword, slug, material, posts), monta o texto
padrão: gatilho de comentário -> DM1 (confirmação "EU QUERO") -> DM2 (botão pro PDF).
Sem travessão. O cérebro pode refinar os textos depois; isto é o baseline válido.
"""

from __future__ import annotations

from pathlib import Path

from stella.domain.registro_keywords import EntradaKeyword

_BASE_URL = "https://brunoeduardosantos.com.br/materiais"


def montar_manychat(entrada: EntradaKeyword) -> str:
    kw = entrada.keyword
    posts = ", ".join(entrada.posts) if entrada.posts else "(nenhum ainda)"
    url = f"{_BASE_URL}/{entrada.slug}.pdf" if entrada.slug else "(sem material definido)"
    material = entrada.material or "o material que você pediu"
    return (
        f"MANYCHAT | KEYWORD: {kw}\n"
        f"Posts que usam: {posts}\n"
        f"Material entregue: {url}\n\n"
        f"GATILHO: comentário com a palavra {kw} nos posts (Instagram > User comments).\n\n"
        "DM 1 (confirmação, abre a janela de 24h):\n"
        f"Oi! Vi que você quer {material} 🙌\n"
        "Responde EU QUERO que eu mando agora.\n"
        "(gatilho de resposta esperado: EU QUERO)\n\n"
        "DM 2 (entrega):\n"
        f"Tá aqui 👇 {material}.\n"
        f'[BOTÃO tipo URL] Texto: "Baixar" -> {url}\n\n'
        '(opcional) Auto-reply no comentário: "Acabei de te mandar no direct 📩"\n'
    )


def escrever_manychat(entrada: EntradaKeyword, dest_dir: str | Path) -> Path:
    """Escreve manychat-<kw>.txt (em minúsculas) na pasta da keyword. Escrita atômica."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    destino = dest_dir / f"manychat-{entrada.keyword.lower()}.txt"
    tmp = destino.with_name(destino.name + ".tmp")
    tmp.write_text(montar_manychat(entrada), encoding="utf-8")
    tmp.replace(destino)
    return destino
