from stella.corpo.centralizar_conteudo import centralizar_existentes, sincronizar_fila
from stella.domain.registro_keywords import RegistroKeywords


def _reg():
    reg = RegistroKeywords()
    reg.registrar_post("VITRINE", "2026-06-24-vitrine", slug="vitrine-busca-ia")
    return reg


def test_centralizar_copia_fila_para_canonica(tmp_path):
    fab = tmp_path / "FAB"
    fila = tmp_path / "fila"
    src = fila / "2026-06-24-vitrine"
    src.mkdir(parents=True)
    (src / "legenda.txt").write_text("leg", encoding="utf-8")
    (src / "slide-00.png").write_bytes(b"x")
    migrados = centralizar_existentes(_reg(), fab, fila)
    dst = fab / "VITRINE" / "2026-06-24-vitrine"
    assert (dst / "legenda.txt").read_text(encoding="utf-8") == "leg"
    assert (dst / "slide-00.png").exists()
    assert "2026-06-24-vitrine" in migrados


def test_centralizar_idempotente(tmp_path):
    fab = tmp_path / "FAB"
    fila = tmp_path / "fila"
    src = fila / "2026-06-24-vitrine"
    src.mkdir(parents=True)
    (src / "legenda.txt").write_text("v1", encoding="utf-8")
    centralizar_existentes(_reg(), fab, fila)
    (fab / "VITRINE" / "2026-06-24-vitrine" / "legenda.txt").write_text("editado", encoding="utf-8")
    centralizar_existentes(_reg(), fab, fila)  # não sobrescreve
    assert (fab / "VITRINE" / "2026-06-24-vitrine" / "legenda.txt").read_text(
        encoding="utf-8"
    ) == "editado"


def test_sincronizar_fila_inverso(tmp_path):
    fab = tmp_path / "FAB"
    fila = tmp_path / "fila"
    canon = fab / "VITRINE" / "2026-06-24-vitrine"
    canon.mkdir(parents=True)
    (canon / "legenda.txt").write_text("leg", encoding="utf-8")
    (canon / "slide-00.png").write_bytes(b"x")
    sincronizar_fila(fab, fila, "vitrine", "2026-06-24-vitrine")
    assert (fila / "2026-06-24-vitrine" / "slide-00.png").exists()
