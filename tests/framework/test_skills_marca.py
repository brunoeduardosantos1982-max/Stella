"""Testa que as 7 skills do Agente de Marca foram criadas e são descobertas."""

from pydantic import SecretStr

from stella.framework.resources.skills_registry import SkillsRegistry
from stella.infra.config import StellaConfig


def test_sete_skills_descobertas(tmp_path):
    config = StellaConfig(
        nvidia_api_key=SecretStr("fake"),
        anthropic_api_key=SecretStr("fake"),
        vault_path=tmp_path,
    )
    reg = SkillsRegistry(config.skills_dir)
    ids = {s.id for s in reg.list_all()}
    esperadas = {
        "copywriting-engajamento-ptbr",
        "carrossel-instagram-ia",
        "estrategia-hashtags",
        "design-tipografico-dark",
        "planejamento-editorial",
        "pesquisa-tendencias-web",
        "revisao-padroes-marca",
    }
    assert esperadas.issubset(ids), f"faltando: {esperadas - ids}"
