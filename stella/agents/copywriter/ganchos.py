"""GanchoCatalog - swipe-file de padroes de gancho (formulas, nao texto copiado)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

_VAULT_PATH = (
    "D:/VortexBrain00/bssurf00/C04 Claude Obsidian/Comandos e Diretrizes/swipe-ganchos.json"
)


@dataclass
class GanchoCatalog:
    path: str = _VAULT_PATH

    def _carregar(self) -> list[dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return []
        padroes = data.get("padroes", []) if isinstance(data, dict) else []
        return [p for p in padroes if isinstance(p, dict)]

    def listar(self) -> list[dict[str, Any]]:
        return self._carregar()

    def get(self, gid: str) -> dict[str, Any] | None:
        for padrao in self._carregar():
            if padrao.get("id") == gid:
                return padrao
        return None
