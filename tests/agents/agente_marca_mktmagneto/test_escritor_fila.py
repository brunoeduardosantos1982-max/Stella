"""Testes do EscritorFila com nova assinatura (design_spec_path)."""

from datetime import datetime, timedelta, timezone

from stella.agents.agente_marca_mktmagneto.escritor_fila import EscritorFila
from stella.agents.agente_marca_mktmagneto.redator import PostTexto
from stella.agents.designer.spec import DesignSpec
from stella.framework.testing.fakes import FakeVault

_BRT = timezone(timedelta(hours=-3))


def _post() -> PostTexto:
    return PostTexto(
        pilar=1, titulo="Título", legenda="Legenda do post", hashtags=["#ia"], slides=["S1"]
    )


def test_escrever_cria_nota_com_status_pending_render() -> None:
    vault = FakeVault()
    escritor = EscritorFila(vault=vault)
    path = escritor.escrever(
        _post(),
        post_id="2026-05-25-01",
        design_spec_path="C04 Claude Obsidian/Stella-publicacao/pendentes/spec.json",
        agendar_para=datetime(2026, 5, 27, 9, 0, tzinfo=_BRT),
    )
    nota = vault.read_note(path)
    assert nota.frontmatter["status"] == "pending_render"
    assert (
        nota.frontmatter["design_spec"]
        == "C04 Claude Obsidian/Stella-publicacao/pendentes/spec.json"
    )
    assert nota.frontmatter["imagens"] == []
    assert "Legenda do post" in nota.content


def test_escrever_nao_grava_png() -> None:
    vault = FakeVault()
    escritor = EscritorFila(vault=vault)
    escritor.escrever(
        _post(),
        post_id="2026-05-25-01",
        design_spec_path="spec.json",
        agendar_para=datetime(2026, 5, 27, 9, 0, tzinfo=_BRT),
    )
    assert len(vault._binarios) == 0


def test_escrever_com_qa_warning_marca_needs_review_na_nota() -> None:
    # O status needs_review e os avisos vivem na nota da fila (fonte única).
    # O EscritorFila NÃO muta o spec em pendentes/ (domínio do designer).
    vault = FakeVault()
    vault.write_binary(
        "spec.json",
        DesignSpec(formato="carrossel", dimensoes=[1080, 1350]).to_json().encode("utf-8"),
    )
    escritor = EscritorFila(vault=vault)
    path = escritor.escrever(
        _post(),
        post_id="2026-05-25-01",
        design_spec_path="spec.json",
        agendar_para=datetime(2026, 5, 27, 9, 0, tzinfo=_BRT),
        status="needs_review",
        qa_warnings=["copy QA aviso: hook fraco"],
    )
    nota = vault.read_note(path)
    assert nota.frontmatter["status"] == "needs_review"
    assert nota.frontmatter["qa_warnings"] == ["copy QA aviso: hook fraco"]
    # spec permanece intocado (status default), não foi reescrito.
    spec = DesignSpec.from_json(vault.read_binary("spec.json").decode("utf-8"))
    assert spec.status != "needs_review"


def test_needs_review_nao_invade_pendentes_em_vault_escopado() -> None:
    # Regressão: o coordenador constrói o EscritorFila com o vault DELE, que
    # tem escopo fila/** mas NÃO pendentes/**. Marcar needs_review não pode
    # tentar ler/escrever o spec em pendentes/ — isso quebrava 2 de 3 posts.
    coord_scope = [
        "C04 Claude Obsidian/Stella-publicacao/fila/**",
        "C04 Claude Obsidian/outputs/mktmagneto-ia/**",
    ]
    vault = FakeVault().scoped(coord_scope)
    escritor = EscritorFila(vault=vault)
    spec_path = "C04 Claude Obsidian/Stella-publicacao/pendentes/20260529-x-spec.json"
    path = escritor.escrever(
        _post(),
        post_id="2026-05-29-02",
        design_spec_path=spec_path,
        agendar_para=datetime(2026, 5, 29, 9, 0, tzinfo=_BRT),
        status="needs_review",
        qa_warnings=["visual QA aviso: contraste"],
    )
    nota = vault.read_note(path)
    assert nota.frontmatter["status"] == "needs_review"
    assert nota.frontmatter["design_spec"] == spec_path
