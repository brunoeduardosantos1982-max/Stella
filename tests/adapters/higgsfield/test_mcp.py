"""Testes do HiggsFieldMCP."""

from stella.adapters.higgsfield.fake import FakeHiggsField
from stella.adapters.higgsfield.mcp import HiggsFieldMCP


def test_mcp_tem_category_image() -> None:
    mcp = HiggsFieldMCP(nome="higgsfield", tipo="cli", endpoint="cli://hf")
    assert mcp.category == "image"


def test_mcp_injeta_soul_id_padrao() -> None:
    fake = FakeHiggsField()
    mcp = HiggsFieldMCP(
        nome="higgsfield", tipo="cli", endpoint="cli://hf", client=fake, soul_id="soul-bruno"
    )
    mcp.generate_image("cena")
    assert fake.calls[0]["soul_id"] == "soul-bruno"


def test_mcp_soul_id_explicito_sobrescreve() -> None:
    fake = FakeHiggsField()
    mcp = HiggsFieldMCP(
        nome="higgsfield", tipo="cli", endpoint="cli://hf", client=fake, soul_id="soul-bruno"
    )
    mcp.generate_image("cena", soul_id="outro")
    assert fake.calls[0]["soul_id"] == "outro"
