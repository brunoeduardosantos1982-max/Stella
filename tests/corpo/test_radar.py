import json
from datetime import datetime
from pathlib import Path
from typing import Any

from stella.adapters.llm.base import LLMProvider, LLMResponse, Message
from stella.corpo import radar


def _cand(url: str) -> radar.Candidato:
    return radar.Candidato(titulo="t", url=url, veiculo="v", snippet="s", data="d", tema="IA")


def test_filtrar_novos_remove_urls_ja_vistas() -> None:
    seen = [{"url": "https://x.com/velho", "enviado_em": "2026-06-20T10:00:00-03:00"}]
    cands = [_cand("https://x.com/velho"), _cand("https://x.com/novo")]
    novos = radar.filtrar_novos(cands, seen)
    assert [c.url for c in novos] == ["https://x.com/novo"]


def test_podar_seen_descarta_entradas_antigas() -> None:
    agora = datetime(2026, 6, 21, 12, 0, tzinfo=radar.FUSO)
    seen = [
        {"url": "a", "enviado_em": "2026-06-20T12:00:00-03:00"},  # 1 dia: fica
        {"url": "b", "enviado_em": "2026-06-01T12:00:00-03:00"},  # 20 dias: sai
    ]
    podado = radar.podar_seen(seen, janela_dias=7, agora=agora)
    assert [s["url"] for s in podado] == ["a"]


def test_gravar_seen_anexa_urls_com_timestamp(tmp_path: Path) -> None:
    p = tmp_path / "seen.json"
    agora = datetime(2026, 6, 21, 6, 0, tzinfo=radar.FUSO)
    radar.gravar_seen([], ["https://x.com/novo"], path=p, agora=agora)
    dados = json.loads(p.read_text(encoding="utf-8"))
    assert dados[0]["url"] == "https://x.com/novo"
    assert dados[0]["enviado_em"].startswith("2026-06-21T06:00")


def test_buscar_candidatos_agrega_temas_e_deduplica_por_url() -> None:
    chamadas: list[str] = []

    def buscar_fake(query: str, api_key: str, **kwargs: Any) -> list[dict[str, Any]]:
        chamadas.append(query)
        return [
            {
                "titulo": f"Artigo de {query}",
                "url": "https://x.com/a" if query == "marketing" else "https://x.com/b",
                "veiculo": "x.com",
                "snippet": "s",
                "data": "2026-06-21",
            }
        ]

    cands = radar.buscar_candidatos(
        temas=["marketing", "IA", "tecnologia"],
        api_key="k",
        buscar=buscar_fake,
    )

    # uma busca por tema
    assert chamadas == ["marketing", "IA", "tecnologia"]
    # url repetida (IA e tecnologia retornaram /b) deduplicada
    urls = sorted(c.url for c in cands)
    assert urls == ["https://x.com/a", "https://x.com/b"]
    assert all(isinstance(c, radar.Candidato) for c in cands)
    # o tema fica registrado
    assert {c.tema for c in cands} == {"marketing", "IA"}


def test_carregar_seen_tolera_ausente_e_json_invalido(tmp_path: Path) -> None:
    # Arquivo ausente
    p_ausente = tmp_path / "nao_existe.json"
    assert radar.carregar_seen(p_ausente) == []

    # JSON inválido
    p_invalido = tmp_path / "invalido.json"
    p_invalido.write_text("{nao json", encoding="utf-8")
    assert radar.carregar_seen(p_invalido) == []

    # JSON válido mas não é lista
    p_dict = tmp_path / "dict.json"
    p_dict.write_text("{}", encoding="utf-8")
    assert radar.carregar_seen(p_dict) == []


def test_gravar_seen_preserva_entradas_existentes(tmp_path: Path) -> None:
    p = tmp_path / "seen.json"
    agora = datetime(2026, 6, 21, 6, 0, tzinfo=radar.FUSO)
    entrada_anterior = {"url": "https://x.com/velho", "enviado_em": "2026-06-20T10:00:00-03:00"}
    radar.gravar_seen([entrada_anterior], ["https://x.com/novo"], path=p, agora=agora)
    dados = json.loads(p.read_text(encoding="utf-8"))
    assert len(dados) == 2
    urls = [d["url"] for d in dados]
    assert "https://x.com/velho" in urls
    assert "https://x.com/novo" in urls


def test_podar_seen_tolera_entrada_sem_offset() -> None:
    agora = datetime(2026, 6, 21, 12, 0, tzinfo=radar.FUSO)
    seen = [
        {"url": "naive", "enviado_em": "2026-06-20T12:00:00"},  # sem offset
        {"url": "aware", "enviado_em": "2026-06-20T12:00:00-03:00"},  # com offset
    ]
    podado = radar.podar_seen(seen, janela_dias=7, agora=agora)
    # A entrada naive deve ser descartada, apenas a aware permanece
    assert [s["url"] for s in podado] == ["aware"]


class _ProviderFake(LLMProvider):
    def __init__(self, texto: str) -> None:
        self._texto = texto
        self.prompt_recebido = ""

    def complete(self, prompt: str) -> LLMResponse:
        self.prompt_recebido = prompt
        return LLMResponse(texto=self._texto)

    def chat(self, messages: list[Message]) -> LLMResponse:  # pragma: no cover
        return LLMResponse(texto=self._texto)


def test_curar_parseia_json_e_limita_em_n() -> None:
    resposta = """```json
    [
      {"titulo": "A", "url": "https://x.com/a", "veiculo": "x.com",
       "resumo": "resumo a", "gancho": "gancho a"},
      {"titulo": "B", "url": "https://x.com/b", "veiculo": "x.com",
       "resumo": "resumo b", "gancho": "gancho b"}
    ]
    ```"""
    provider = _ProviderFake(resposta)
    cands = [_cand("https://x.com/a"), _cand("https://x.com/b"), _cand("https://x.com/c")]
    itens = radar.curar(cands, n=2, provider=provider)
    assert len(itens) == 2
    assert itens[0].titulo == "A"
    assert itens[0].gancho == "gancho a"
    assert "https://x.com/a" in provider.prompt_recebido  # candidatos vão no prompt


def test_montar_card_formata_itens_sem_travessao() -> None:
    itens = [
        radar.ItemRadar(
            titulo="IA muda SEO",
            url="https://searchengineland.com/x",
            veiculo="searchengineland.com",
            resumo="Google corta cliques.",
            gancho="Se você ainda otimiza pro Google de 2023, repense.",
        )
    ]
    agora = datetime(2026, 6, 21, 6, 0, tzinfo=radar.FUSO)
    card = radar.montar_card(itens, "06h", agora=agora)
    assert "RADAR 06h" in card
    assert "21/06" in card
    assert 'href="https://searchengineland.com/x"' in card
    assert "searchengineland.com" in card
    assert "IA muda SEO" in card
    assert "—" not in card  # sem travessão em texto público


def test_montar_card_escapa_html_dos_campos() -> None:
    itens = [
        radar.ItemRadar(
            titulo="growth < scale",
            url="https://x.com/a",
            veiculo="x.com",
            resumo="resumo normal",
            gancho="B2B & B2C juntos",
        )
    ]
    agora = datetime(2026, 6, 21, 6, 0, tzinfo=radar.FUSO)
    card = radar.montar_card(itens, "06h", agora=agora)
    # campos LLM devem ser escapados
    assert "&amp;" in card
    assert "&lt;" in card
    # estrutura HTML estatica preservada
    assert "<b>" in card
    assert "<i>" in card
    assert "<a href=" in card


def test_montar_card_vazio_avisa_sem_novidade() -> None:
    card = radar.montar_card([], "14h", agora=datetime(2026, 6, 21, 14, 0, tzinfo=radar.FUSO))
    assert "Sem novidade" in card
    assert "—" not in card


def test_enviar_telegram_usa_parse_mode_html(tmp_path: Path) -> None:
    cofre = tmp_path / "telegram.json"
    cofre.write_text(json.dumps({"bot_token": "T", "chat_id": "C"}), encoding="utf-8")
    capturado: dict[str, Any] = {}

    class _Resp:
        def raise_for_status(self) -> None:
            return None

    def post_fake(url: str, **kwargs: Any) -> "_Resp":
        capturado["url"] = url
        capturado["json"] = kwargs["json"]
        return _Resp()

    radar.enviar_telegram("oi", cofre_path=cofre, http_post=post_fake)
    assert "/botT/sendMessage" in capturado["url"]
    assert capturado["json"]["chat_id"] == "C"
    assert capturado["json"]["parse_mode"] == "HTML"


def test_salvar_no_vault_escreve_md(tmp_path: Path) -> None:
    itens = [radar.ItemRadar("T", "https://x.com/a", "x.com", "r", "g")]
    agora = datetime(2026, 6, 21, 6, 0, tzinfo=radar.FUSO)
    caminho = radar.salvar_no_vault(itens, "06h", vault_dir=tmp_path, agora=agora)
    conteudo = caminho.read_text(encoding="utf-8")
    assert "06h" in conteudo
    assert "https://x.com/a" in conteudo
    assert caminho.name == "2026-06-21.md"


def test_rodar_radar_fluxo_feliz(tmp_path: Path, monkeypatch: Any) -> None:
    enviados: list[str] = []
    seen_path = tmp_path / "seen.json"
    monkeypatch.setattr(radar, "SEEN_PATH", seen_path)

    def buscar_fake(query: str, api_key: str, **kw: Any) -> list[dict[str, Any]]:
        return [
            {
                "titulo": f"T {query}",
                "url": f"https://x.com/{query}",
                "veiculo": "x.com",
                "snippet": "s",
                "data": "2026-06-21",
            }
        ]

    provider = _ProviderFake(
        '[{"titulo":"T","url":"https://x.com/marketing","veiculo":"x.com",'
        '"resumo":"r","gancho":"g"}]'
    )
    itens = radar.rodar_radar(
        n=1,
        api_key="k",
        provider=provider,
        buscar=buscar_fake,
        enviar=enviados.append,
        salvar=False,
        agora=datetime(2026, 6, 21, 6, 0, tzinfo=radar.FUSO),
    )
    assert len(itens) == 1
    assert len(enviados) == 1 and "RADAR 06h" in enviados[0]
    assert json.loads(seen_path.read_text(encoding="utf-8"))[0]["url"] == "https://x.com/marketing"


def test_rodar_radar_degrada_quando_curador_falha(tmp_path: Path, monkeypatch: Any) -> None:
    enviados: list[str] = []
    monkeypatch.setattr(radar, "SEEN_PATH", tmp_path / "seen.json")

    def buscar_fake(query: str, api_key: str, **kw: Any) -> list[dict[str, Any]]:
        return [
            {
                "titulo": "Bruto",
                "url": "https://x.com/bruto",
                "veiculo": "x.com",
                "snippet": "s",
                "data": "d",
            }
        ]

    class _ProviderQuebra(_ProviderFake):
        def complete(self, prompt: str) -> Any:
            raise RuntimeError("LLM fora do ar")

    radar.rodar_radar(
        n=1,
        api_key="k",
        provider=_ProviderQuebra(""),
        buscar=buscar_fake,
        enviar=enviados.append,
        salvar=False,
        agora=datetime(2026, 6, 21, 14, 0, tzinfo=radar.FUSO),
    )
    assert len(enviados) == 1
    assert "https://x.com/bruto" in enviados[0]  # card degradado com links crus
    seen_path = tmp_path / "seen.json"
    assert seen_path.exists()
    dados = json.loads(seen_path.read_text(encoding="utf-8"))
    assert dados[0]["url"] == "https://x.com/bruto"
