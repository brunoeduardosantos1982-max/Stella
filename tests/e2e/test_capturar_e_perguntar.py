"""Testes E2E — chamam APIs reais (NVIDIA + Anthropic).

Opt-in: por default NÃO rodam. Para rodar:
    pytest -m live

Skip automático se chaves de API não estiverem no ambiente.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from stella.app import build_stella
from stella.infra.config import StellaConfig
from stella.usecases.capturar_ideia import EntradaCaptura
from stella.usecases.responder_projeto import EntradaPergunta

pytestmark = pytest.mark.live


def _check_env_ou_skip() -> None:
    """Tenta carregar StellaConfig (respeita o .env do projeto).

    Skip se faltarem credenciais — testes E2E só rodam se houver chaves reais.
    """
    try:
        StellaConfig()
    except ValidationError as e:
        pytest.skip(f"E2E exige .env configurado com chaves reais: {e}")


def test_e2e_captura_real(vault_tmp, monkeypatch) -> None:
    _check_env_ou_skip()
    monkeypatch.setenv("STELLA_VAULT_PATH", str(vault_tmp))
    (vault_tmp / "A00 Inbox").mkdir(exist_ok=True)

    stella = build_stella(StellaConfig())
    resultado = stella.capturar_ideia.execute(
        EntradaCaptura(
            texto="testar integração da Stella com NVIDIA NIM",
            momento=datetime.now(),
        )
    )
    nota = stella.vault.read_note(resultado.path)
    assert nota.frontmatter["tipo"] == "ideia"
    assert nota.frontmatter["title"]  # LLM real preencheu algum título


def test_e2e_qa_real(vault_tmp, monkeypatch) -> None:
    _check_env_ou_skip()
    monkeypatch.setenv("STELLA_VAULT_PATH", str(vault_tmp))
    pasta = vault_tmp / "B01 Projetos"
    pasta.mkdir(exist_ok=True)
    (pasta / "Projeto Teste.md").write_text(
        "---\ntipo: projeto\nstatus: ativo\n---\n\n# Projeto Teste\n\nÚltimo update: revisar copy.",
        encoding="utf-8",
    )

    stella = build_stella(StellaConfig())
    resultado = stella.responder_projeto.execute(
        EntradaPergunta(
            pergunta="qual o último update?",
            projeto="Projeto Teste",
        )
    )
    assert len(resultado.resposta) > 30  # resposta substantiva
    assert "B01 Projetos/Projeto Teste.md" in resultado.fontes
