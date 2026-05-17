from pathlib import Path

from stella.framework.manifest import load_manifest

_MANIFEST_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "stella"
    / "agents"
    / "coord_ecommerce_aspargus"
    / "manifest.yaml"
)


def test_aspargus_manifest_carrega() -> None:
    """O manifest do Aspargus deve ser parseavel pelo framework."""
    m = load_manifest(_MANIFEST_PATH)
    assert m.nome == "coord_ecommerce_aspargus"


def test_aspargus_manifest_e_http_e_aponta_para_endpoint() -> None:
    m = load_manifest(_MANIFEST_PATH)
    assert m.execucao == "http"
    assert m.endpoint == "http://localhost:8000"


def test_aspargus_manifest_e_coordenador_de_ecommerce() -> None:
    m = load_manifest(_MANIFEST_PATH)
    assert m.tipo == "coordenador"
    assert m.setor == "ecommerce"
