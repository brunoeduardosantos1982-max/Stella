from typer.testing import CliRunner

from stella.adapters.higgsfield.fake import FakeHiggsField
from stella.frontends.cli import app

runner = CliRunner()


def test_gerar_imagem_usa_higgsfield_injetavel(monkeypatch) -> None:
    monkeypatch.setenv("STELLA_HIGGSFIELD_SOUL_ID", "")
    fake = FakeHiggsField()
    monkeypatch.setattr("stella.frontends.cli._build_higgsfield_client", lambda **_: fake)

    result = runner.invoke(app, ["gerar-imagem", "Bruno em fundo neon"])

    assert result.exit_code == 0
    assert fake.calls == [{"prompt": "Bruno em fundo neon", "soul_id": None}]
    assert "https://fake.higgsfield.ai/img/" in result.stdout


def test_gerar_imagem_usa_soul_id_do_config_por_padrao(monkeypatch) -> None:
    monkeypatch.setenv("STELLA_HIGGSFIELD_SOUL_ID", "soul-do-bruno")
    fake = FakeHiggsField()
    monkeypatch.setattr("stella.frontends.cli._build_higgsfield_client", lambda **_: fake)

    result = runner.invoke(app, ["gerar-imagem", "retrato"])

    assert result.exit_code == 0
    assert fake.calls == [{"prompt": "retrato", "soul_id": "soul-do-bruno"}]


def test_flag_soul_id_tem_prioridade_sobre_config(monkeypatch) -> None:
    monkeypatch.setenv("STELLA_HIGGSFIELD_SOUL_ID", "soul-do-config")
    fake = FakeHiggsField()
    monkeypatch.setattr("stella.frontends.cli._build_higgsfield_client", lambda **_: fake)

    result = runner.invoke(app, ["gerar-imagem", "retrato", "--soul-id", "soul-explicito"])

    assert result.exit_code == 0
    assert fake.calls == [{"prompt": "retrato", "soul_id": "soul-explicito"}]


def test_gerar_imagem_repassa_aspect_ratio_para_factory(monkeypatch) -> None:
    capturado: dict[str, object] = {}

    def _factory(**kwargs):
        capturado.update(kwargs)
        return FakeHiggsField()

    monkeypatch.setattr("stella.frontends.cli._build_higgsfield_client", _factory)

    result = runner.invoke(app, ["gerar-imagem", "cena vertical", "--aspect-ratio", "9:16"])

    assert result.exit_code == 0
    assert capturado["aspect_ratio"] == "9:16"
