"""ResolvedorImagens — materializa slides foto-higgsfield de um DesignSpec.

Para cada slide com soul_id_prompt e sem foto: gera a imagem via Higgsfield,
baixa o PNG, grava no vault e seta slide.foto = path. Falha por slide vira
warning (nunca propaga) — a intenção é preservada para retry.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import httpx

from stella.adapters.higgsfield.base import HiggsFieldClient
from stella.adapters.vault.base import VaultRepository
from stella.agents.designer.spec import DesignSpec

_IMAGENS_DIR = "C04 Claude Obsidian/outputs/mktmagneto-ia/imagens"
_DOWNLOAD_TIMEOUT_S = 30


def _baixar_http(url: str) -> bytes:
    resp = httpx.get(url, timeout=_DOWNLOAD_TIMEOUT_S, follow_redirects=True)
    resp.raise_for_status()
    return bytes(resp.content)


@dataclass
class ResolvedorImagens:
    """Materializa slides foto-higgsfield in-place. Retorna lista de warnings."""

    higgs: HiggsFieldClient
    vault: VaultRepository
    baixar: Callable[[str], bytes] = field(default=_baixar_http)

    def resolver(self, spec: DesignSpec, *, post_id: str) -> list[str]:
        warnings: list[str] = []
        for slide in spec.slides:
            if not slide.soul_id_prompt or slide.foto:
                continue
            try:
                url = self.higgs.generate_image(slide.soul_id_prompt)
                dados = self.baixar(url)
                rel = f"{_IMAGENS_DIR}/{post_id}/slide{slide.index}.png"
                self.vault.write_binary(rel, dados)
                slide.foto = rel
                slide.soul_id_prompt = None
            except Exception as e:  # noqa: BLE001 — isolar falha por slide; intenção preservada
                warnings.append(f"slide {slide.index}: Higgsfield falhou — {e}")
        return warnings
