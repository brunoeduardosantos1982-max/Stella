"""Publicação do material no hub (F2.4, gate 2, ação externa).

Copia o PDF do material para o site e dispara o deploy. O commit+deploy fica numa
fronteira injetável (`deploy_fn`) para os testes não tocarem na rede; o default
`deploy_hub` espelha o fluxo manual provado (autor gmail + vercel --prod).
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

HUB_REPO = Path("D:/VortexBrain00/brunoeduardosantos-site")
_AUTOR = "Bruno Eduardo Santos <brunoeduardosantos1982@gmail.com>"


def encontrar_pdf(fab_dir: str | Path, slug: str) -> Path:
    """Acha FABRICADECONTEUDO/<KW>/<slug>.pdf. Levanta FileNotFoundError se ausente."""
    matches = sorted(Path(fab_dir).glob(f"*/{slug}.pdf"))
    if not matches:
        raise FileNotFoundError(f"PDF do material '{slug}' não encontrado em {fab_dir}")
    return matches[0]


def publicar_material(
    slug: str,
    *,
    fab_dir: str | Path,
    hub_materiais: str | Path,
    deploy_fn: Callable[[str, Path], str],
    manifesto_fn: Callable[[str, str, str], None] = lambda s, t, d: None,
    titulo: str = "",
    descricao: str = "",
) -> str:
    """Resolve o PDF (guard antes de qualquer efeito), copia pro hub e deploya.

    Se `titulo` for dado, chama `manifesto_fn(slug, titulo, descricao)` para a
    landing genérica saber o que exibir.
    """
    pdf = encontrar_pdf(fab_dir, slug)
    hub_materiais = Path(hub_materiais)
    hub_materiais.mkdir(parents=True, exist_ok=True)
    destino = hub_materiais / f"{slug}.pdf"
    shutil.copy2(pdf, destino)
    if titulo:
        manifesto_fn(slug, titulo, descricao)
    return deploy_fn(slug, destino)


def deploy_hub(slug: str, destino: Path, *, hub_repo: Path = HUB_REPO) -> str:
    """Fronteira real: git add+commit (autor gmail, pegadinha do deploy) + vercel --prod."""
    rel = f"public/materiais/{slug}.pdf"
    subprocess.run(["git", "-C", str(hub_repo), "add", rel], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(hub_repo),
            "-c",
            "user.name=Bruno Eduardo Santos",
            "-c",
            "user.email=brunoeduardosantos1982@gmail.com",
            "commit",
            "--author",
            _AUTOR,
            "-m",
            f"materiais: publica {slug}.pdf",
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        "vercel deploy --prod --yes",
        cwd=str(hub_repo),
        shell=True,
        check=True,
        capture_output=True,
    )
    return f"https://www.brunoeduardosantos.com.br/materiais/{slug}.pdf"
