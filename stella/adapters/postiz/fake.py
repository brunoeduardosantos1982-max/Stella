"""FakePostiz — dublê de teste do cliente Postiz. Sem rede."""

from __future__ import annotations

from stella.adapters.postiz.base import (
    PostizAgendamento,
    PostizError,
    PostizMidia,
    PostizResultado,
)


class FakePostiz:
    """Cliente Postiz fake — registra chamadas em memória.

    `uploads` e `agendamentos` ficam públicos para asserts nos testes.
    `falhar_em` ('upload' ou 'agendar') força um `PostizError` no método
    correspondente, para testar o tratamento de erro do agente.
    """

    def __init__(self, *, falhar_em: str | None = None) -> None:
        self.uploads: list[tuple[str, bytes]] = []
        self.agendamentos: list[PostizAgendamento] = []
        self._falhar_em = falhar_em

    def upload_imagem(self, dados: bytes, nome_arquivo: str) -> PostizMidia:
        if self._falhar_em == "upload":
            raise PostizError(f"falha simulada no upload de '{nome_arquivo}'")
        self.uploads.append((nome_arquivo, dados))
        return PostizMidia(id=f"fake-img-{len(self.uploads)}", path=f"fake://{nome_arquivo}")

    def agendar_post(self, agendamento: PostizAgendamento) -> PostizResultado:
        if self._falhar_em == "agendar":
            raise PostizError("falha simulada no agendamento")
        self.agendamentos.append(agendamento)
        return PostizResultado(post_url=f"https://postiz.fake/post/{len(self.agendamentos)}")
