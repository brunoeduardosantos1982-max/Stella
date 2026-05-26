"""Testes do adapter Higgsfield."""

from stella.adapters.higgsfield.fake import FakeHiggsField


def test_fake_retorna_url_deterministica() -> None:
    fake = FakeHiggsField()
    url = fake.generate_image("Bruno em escritório tech")
    assert url.startswith("https://fake.higgsfield.ai/")
    assert url.endswith(".jpg")


def test_fake_registra_calls() -> None:
    fake = FakeHiggsField()
    fake.generate_image("cena 1")
    fake.generate_image("cena 2", soul_id="soul-abc")
    assert len(fake.calls) == 2
    assert fake.calls[0]["prompt"] == "cena 1"
    assert fake.calls[1]["soul_id"] == "soul-abc"


def test_fake_url_diferente_para_prompts_diferentes() -> None:
    fake = FakeHiggsField()
    url1 = fake.generate_image("cena A")
    url2 = fake.generate_image("cena B")
    assert url1 != url2
