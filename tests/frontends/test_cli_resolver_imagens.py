"""Testes do comando resolver-imagens (retry de slides foto-higgsfield)."""

from stella.adapters.higgsfield.fake import FakeHiggsField
from stella.adapters.higgsfield.mcp import HiggsFieldMCP
from stella.agents.designer.spec import DesignSpec, SlideSpec
from stella.framework.testing.fakes import FakeVault
from stella.frontends.cli import resolver_imagens_para_fila

_FILA = "C04 Claude Obsidian/Stella-publicacao/fila"
_PEND = "C04 Claude Obsidian/Stella-publicacao/pendentes"


def _montar_fila_needs_review() -> FakeVault:
    vault = FakeVault()
    spec = DesignSpec(
        formato="carrossel",
        dimensoes=[1080, 1350],
        slides=[SlideSpec(index=0, template="capa-foto-bg", conteudo={}, soul_id_prompt="Bruno")],
    )
    spec_path = f"{_PEND}/p1-spec.json"
    vault.write_binary(spec_path, spec.to_json().encode("utf-8"))
    vault.write_note(
        f"{_FILA}/2026-06-01-01.md",
        "corpo",
        {"status": "needs_review", "design_spec": spec_path, "imagens": []},
    )
    return vault


def test_resolver_baixa_status_para_pending_render() -> None:
    vault = _montar_fila_needs_review()
    higgs = HiggsFieldMCP(
        nome="higgsfield", tipo="cli", endpoint="cli://hf", client=FakeHiggsField()
    )

    resolver_imagens_para_fila(vault=vault, higgs=higgs, baixar=lambda url: b"PNG", post_id=None)

    nota = vault.read_note(f"{_FILA}/2026-06-01-01.md")
    assert nota.frontmatter["status"] == "pending_render"
    assert nota.frontmatter["imagens"] == [
        "C04 Claude Obsidian/outputs/mktmagneto-ia/imagens/2026-06-01-01/slide0.png"
    ]


def test_resolver_idempotente_nao_duplica() -> None:
    vault = _montar_fila_needs_review()
    higgs = HiggsFieldMCP(
        nome="higgsfield", tipo="cli", endpoint="cli://hf", client=FakeHiggsField()
    )

    resolver_imagens_para_fila(vault=vault, higgs=higgs, baixar=lambda url: b"PNG", post_id=None)
    # 2ª passada: já está pending_render, nada a resolver
    resolver_imagens_para_fila(vault=vault, higgs=higgs, baixar=lambda url: b"PNG", post_id=None)

    nota = vault.read_note(f"{_FILA}/2026-06-01-01.md")
    assert nota.frontmatter["imagens"] == [
        "C04 Claude Obsidian/outputs/mktmagneto-ia/imagens/2026-06-01-01/slide0.png"
    ]
