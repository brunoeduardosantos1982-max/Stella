"""DesignSpec — schema do pacote de design gerado pelo DesignSpecGenerator."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from typing import Literal

DesignStatus = Literal["pending_render", "needs_review", "rendering", "rendered", "error"]
DesignFormato = Literal["post-unico", "carrossel", "stories", "video", "landing-page"]


@dataclass
class SlideSpec:
    index: int
    template: str
    conteudo: dict[str, str]
    foto: str | None = None
    soul_id_prompt: str | None = None
    referencias_usadas: list[str] = field(default_factory=list)


@dataclass
class DesignSpec:
    formato: DesignFormato
    dimensoes: list[int]
    slides: list[SlideSpec] = field(default_factory=list)
    landing_page_html: str | None = None
    video_clarificacao: str | None = None
    status: DesignStatus = "pending_render"

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, text: str) -> DesignSpec:
        data = json.loads(text)
        slides_raw = data.pop("slides", [])
        slides = [SlideSpec(**s) for s in slides_raw]
        valid = {f.name for f in fields(cls)}
        return cls(slides=slides, **{k: v for k, v in data.items() if k in valid})
