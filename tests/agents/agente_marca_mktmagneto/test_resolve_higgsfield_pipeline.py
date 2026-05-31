"""Pipeline: o agente resolve slides foto-higgsfield entre design e fila.

Valida o trecho de resolução de forma isolada (sem montar o agente inteiro).
A integração ponta-a-ponta do agente já é coberta por test_integration_v2.py.
"""

from stella.adapters.higgsfield.fake import FakeHiggsField
from stella.adapters.higgsfield.mcp import HiggsFieldMCP
from stella.adapters.higgsfield.resolvedor import ResolvedorImagens
from stella.agents.designer.spec import DesignSpec, SlideSpec
from stella.framework.testing.fakes import FakeVault


def _resolver_inline(vault, higgs_mcp, spec_path, post_id, baixar=lambda url: b"PNG"):
    spec = DesignSpec.from_json(vault.read_binary(spec_path).decode("utf-8"))
    warnings = ResolvedorImagens(higgs=higgs_mcp, vault=vault, baixar=baixar).resolver(
        spec, post_id=post_id
    )
    vault.write_binary(spec_path, spec.to_json().encode("utf-8"))
    return warnings, [s.foto for s in spec.slides if s.foto]


def test_pipeline_resolve_e_reescreve_spec() -> None:
    vault = FakeVault()
    spec = DesignSpec(
        formato="carrossel",
        dimensoes=[1080, 1350],
        slides=[SlideSpec(index=0, template="capa-foto-bg", conteudo={}, soul_id_prompt="Bruno")],
    )
    spec_path = "C04 Claude Obsidian/Stella-publicacao/pendentes/x-spec.json"
    vault.write_binary(spec_path, spec.to_json().encode("utf-8"))

    mcp = HiggsFieldMCP(nome="higgsfield", tipo="cli", endpoint="cli://hf", client=FakeHiggsField())
    warnings, imagens = _resolver_inline(vault, mcp, spec_path, "2026-06-01-01")

    assert warnings == []
    rel = "C04 Claude Obsidian/outputs/mktmagneto-ia/imagens/2026-06-01-01/slide0.png"
    assert imagens == [rel]
    spec2 = DesignSpec.from_json(vault.read_binary(spec_path).decode("utf-8"))
    assert spec2.slides[0].foto == rel
    assert spec2.slides[0].soul_id_prompt is None
