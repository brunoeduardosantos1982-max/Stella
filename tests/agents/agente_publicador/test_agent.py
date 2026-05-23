from datetime import datetime

import pytest

from stella.adapters.postiz.fake import FakePostiz
from stella.agents.agente_publicador.agent import Agent, _para_utc_iso
from stella.framework.testing.fakes import FakeVault

_MARCAS = "C04 Claude Obsidian/Stella-publicacao/marcas.md"
_FILA = "C04 Claude Obsidian/Stella-publicacao/fila"


def _vault(posts: dict[str, tuple[str, dict[str, object]]] | None = None) -> FakeVault:
    """FakeVault com marcas.md válido + posts opcionais na fila."""
    notes: dict[str, tuple[str, dict[str, object]]] = {
        _MARCAS: ("", {"marcas": {"mktmagneto": {"instagram": "canal-ig-1"}}}),
    }
    if posts:
        notes.update(posts)
    return FakeVault(notes=notes)  # type: ignore[arg-type]


def _post(status: str = "aprovado", **extra: object) -> tuple[str, dict[str, object]]:
    fm: dict[str, object] = {
        "marca": "mktmagneto",
        "plataformas": ["instagram"],
        "agendar-para": "2026-05-25 09:00",
        "status": status,
    }
    fm.update(extra)
    return ("Legenda do post", fm)


# --- helper de fuso ---------------------------------------------------------


def test_para_utc_iso_converte_brasilia_para_utc() -> None:
    assert _para_utc_iso("2026-05-25 09:00") == "2026-05-25T12:00:00.000Z"


def test_para_utc_iso_aceita_datetime_naive() -> None:
    assert _para_utc_iso(datetime(2026, 5, 25, 9, 0)) == "2026-05-25T12:00:00.000Z"


def test_para_utc_iso_string_invalida_levanta() -> None:
    with pytest.raises(ValueError):
        _para_utc_iso("25/05/2026")


def test_execute_modo_invalido_devolve_falha() -> None:
    saida = Agent().execute({"modo": "turbo"})
    assert saida.sucesso is False
    assert "inválido" in saida.mensagens[0]


# --- publicação -------------------------------------------------------------


def test_execute_publica_post_aprovado_em_semi_auto() -> None:
    vault = _vault({f"{_FILA}/post1.md": _post()})
    postiz = FakePostiz()
    saida = Agent(vault=vault, postiz_client=postiz).execute({"modo": "semi-auto"})

    assert saida.sucesso is True
    assert saida.resultado["publicados"] == [f"{_FILA}/post1.md"]
    assert len(postiz.agendamentos) == 1
    ag = postiz.agendamentos[0]
    assert ag.canal_id == "canal-ig-1"
    assert ag.conteudo == "Legenda do post"
    assert ag.data_utc == "2026-05-25T12:00:00.000Z"

    nota = vault.read_note(f"{_FILA}/post1.md")
    assert nota.frontmatter["status"] == "agendado"
    assert nota.frontmatter["post-url"]


def test_execute_publica_post_com_imagem() -> None:
    vault = _vault({f"{_FILA}/post1.md": _post(imagem="foto.png")})
    vault.write_binary(f"{_FILA}/foto.png", b"PNGDATA")
    postiz = FakePostiz()
    Agent(vault=vault, postiz_client=postiz).execute({"modo": "semi-auto"})

    assert postiz.uploads == [("foto.png", b"PNGDATA")]
    assert len(postiz.agendamentos[0].midias) == 1


def test_execute_semi_auto_ignora_rascunho() -> None:
    vault = _vault({f"{_FILA}/post1.md": _post(status="rascunho")})
    postiz = FakePostiz()
    saida = Agent(vault=vault, postiz_client=postiz).execute({"modo": "semi-auto"})

    assert saida.resultado["ignorados"] == 1
    assert postiz.agendamentos == []


def test_execute_auto_publica_rascunho() -> None:
    vault = _vault({f"{_FILA}/post1.md": _post(status="rascunho")})
    postiz = FakePostiz()
    saida = Agent(vault=vault, postiz_client=postiz).execute({"modo": "auto"})

    assert saida.resultado["publicados"] == [f"{_FILA}/post1.md"]
    assert len(postiz.agendamentos) == 1


def test_execute_erro_em_um_post_nao_derruba_outros() -> None:
    vault = _vault(
        {
            f"{_FILA}/bom.md": _post(),
            f"{_FILA}/ruim.md": _post(marca="inexistente"),
        }
    )
    postiz = FakePostiz()
    saida = Agent(vault=vault, postiz_client=postiz).execute({"modo": "semi-auto"})

    assert saida.sucesso is False
    assert saida.resultado["publicados"] == [f"{_FILA}/bom.md"]
    assert len(saida.resultado["erros"]) == 1
    assert vault.read_note(f"{_FILA}/bom.md").frontmatter["status"] == "agendado"
    nota_ruim = vault.read_note(f"{_FILA}/ruim.md")
    assert nota_ruim.frontmatter["status"] == "erro"
    assert nota_ruim.frontmatter["erro"]


def test_execute_post_sem_agendar_para_vira_erro() -> None:
    post_sem_data = (
        "Legenda",
        {"marca": "mktmagneto", "plataformas": ["instagram"], "status": "aprovado"},
    )
    vault = _vault({f"{_FILA}/post1.md": post_sem_data})
    saida = Agent(vault=vault, postiz_client=FakePostiz()).execute({"modo": "semi-auto"})

    assert saida.sucesso is False
    assert vault.read_note(f"{_FILA}/post1.md").frontmatter["status"] == "erro"


def test_execute_sem_marcas_md_devolve_falha() -> None:
    agente = Agent(vault=FakeVault(), postiz_client=FakePostiz())
    saida = agente.execute({"modo": "semi-auto"})
    assert saida.sucesso is False
    assert "marcas" in saida.mensagens[0].lower()


def test_execute_sem_token_e_sem_client_devolve_falha() -> None:
    saida = Agent(vault=_vault()).execute({"modo": "semi-auto"})
    assert saida.sucesso is False
    assert "token" in saida.mensagens[0].lower()
