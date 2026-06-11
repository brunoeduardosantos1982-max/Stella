from pathlib import Path

from stella.corpo import gravador
from stella.framework.testing.fakes import FakeLLM


def test_salvar_no_vault_escreve_nota_com_frontmatter(tmp_path: Path) -> None:
    nota = gravador.salvar_no_vault(
        "cliente especial",
        "[00:00] transcricao completa",
        "Resumo da reuniao",
        tmp_path,
    )

    assert nota.parent == tmp_path / "C04 Claude Obsidian" / "reunioes"
    assert nota.name.endswith("-cliente-especial.md")
    conteudo = nota.read_text(encoding="utf-8")
    assert "tipo: reuniao" in conteudo
    assert "origem: gravador" in conteudo
    assert "criado-em:" in conteudo
    assert "## Resumo" in conteudo
    assert "Resumo da reuniao" in conteudo
    assert "## Transcrição completa" in conteudo
    assert "[00:00] transcricao completa" in conteudo


def test_processar_pasta_ignora_feito_e_cria_marker(monkeypatch, tmp_path: Path) -> None:
    pasta = tmp_path / "gravacoes"
    pasta.mkdir()
    novo = pasta / "nova.mp3"
    novo.write_bytes(b"audio")
    antigo = pasta / "antiga.wav"
    antigo.write_bytes(b"audio")
    antigo.with_name("antiga.wav.feito").touch()

    chamados: list[str] = []

    monkeypatch.setattr(gravador, "transcrever", lambda caminho: f"transcrito {caminho.name}")
    monkeypatch.setattr(gravador, "resumir", lambda transcricao, llm: f"resumo {transcricao}")
    monkeypatch.setattr(
        gravador,
        "avisar_telegram",
        lambda resumo, nota_path, cofre_path: chamados.append(nota_path.name),
    )

    total = gravador.processar_pasta(pasta, tmp_path / "vault", tmp_path / "cofre.json", FakeLLM())

    assert total == 1
    assert novo.with_name("nova.mp3.feito").exists()
    assert chamados and chamados[0].endswith("-nova.md")
    assert not antigo.with_name("antiga.wav.feito.feito").exists()


def test_resumir_monta_prompt_e_retorna_texto_do_llm() -> None:
    llm = FakeLLM(["Resumo final"])

    resumo = gravador.resumir("[00:00] cliente falou algo importante", llm)

    assert resumo == "Resumo final"
    assert llm.calls
    prompt = llm.calls[0]
    assert "Resumo executivo" in prompt
    assert "Decisoes tomadas" in prompt
    assert "Acoes combinadas" in prompt
    assert "Citacoes literais" in prompt
    assert "[00:00] cliente falou algo importante" in prompt
