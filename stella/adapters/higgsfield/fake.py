"""FakeHiggsField para testes unitários."""

from __future__ import annotations


class FakeHiggsField:
    """Implementação fake do HiggsFieldClient — sem chamadas reais."""

    def __init__(self) -> None:
        self.calls: list[dict[str, str | None]] = []

    def generate_image(self, prompt: str, soul_id: str | None = None) -> str:
        self.calls.append({"prompt": prompt, "soul_id": soul_id})
        slug = abs(hash(prompt))
        return f"https://fake.higgsfield.ai/img/{slug}.jpg"
