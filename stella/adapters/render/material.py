"""Material rico (lead-magnet) em PDF, identidade Field Manual escuro (F2.2).

Renderiza um HTML para PDF via Chrome `--print-to-pdf` e valida a qualidade:
fontes embutidas e a REGRA DE LAYOUT (nº de <section class="page"> == nº de páginas
do PDF; senão, alguma seção estourou e o espaçamento quebra).
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from stella.adapters.render.carrossel import detectar_chrome

_SECAO_RE = re.compile(r'<section class="page">')
_PAGINA_RE = re.compile(r"/Type\s*/Page[^s]")
_FONTES = ("Grotesk", "Fraunces", "JetBrains")


def contar_secoes(html: str) -> int:
    """Quantas <section class="page"> (páginas físicas pretendidas) o HTML declara."""
    return len(_SECAO_RE.findall(html))


def contar_paginas_pdf(pdf_bytes: bytes) -> int:
    """Quantas páginas o PDF tem (/Type /Page folha; ignora /Type /Pages árvore)."""
    texto = pdf_bytes.decode("latin-1", errors="ignore")
    return len(_PAGINA_RE.findall(texto))


def fontes_embutidas(pdf_bytes: bytes) -> bool:
    """True se as fontes da identidade aparecem embutidas (sinal de que a CSS carregou)."""
    texto = pdf_bytes.decode("latin-1", errors="ignore")
    return any(f in texto for f in _FONTES)


def validar_layout(html: str, n_paginas: int) -> None:
    """Levanta ValueError se o nº de seções não bater com o nº de páginas do PDF."""
    secoes = contar_secoes(html)
    if secoes != n_paginas:
        raise ValueError(
            f"material estourou: {secoes} seção(ões) no HTML, {n_paginas} página(s) no PDF. "
            'Redivida em uma <section class="page"> por página (máx. ~3 cards por seção).'
        )


def renderizar_pdf(
    html_file: str | Path, pdf_out: str | Path, *, chrome: str | None = None
) -> bytes:
    """Renderiza o HTML para PDF (headers off) e devolve os bytes do PDF gerado."""
    chrome_bin = detectar_chrome(chrome)
    html_file = Path(html_file)
    pdf_out = Path(pdf_out)
    pdf_out.parent.mkdir(parents=True, exist_ok=True)
    url = "file:///" + str(html_file.resolve()).replace("\\", "/")
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [
                chrome_bin,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--allow-file-access-from-files",
                "--no-pdf-header-footer",
                "--virtual-time-budget=20000",
                "--run-all-compositor-stages-before-draw",
                f"--user-data-dir={tmp}",
                f"--print-to-pdf={pdf_out}",
                url,
            ],
            capture_output=True,
            timeout=120,
        )
    if not pdf_out.exists():
        raise RuntimeError(f"Chrome não gerou o PDF: {pdf_out}")
    return pdf_out.read_bytes()
