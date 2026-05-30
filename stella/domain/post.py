from dataclasses import dataclass, field


@dataclass
class PostTexto:
    """Pauta + textos prontos para virar post.

    Saída normalizada da copy (legenda + hashtags + slides) que o coordenador
    monta a partir do output do especialista `copywriter` e passa adiante para
    AutoQA e EscritorFila.
    """

    pilar: int
    titulo: str
    legenda: str = ""
    hashtags: list[str] = field(default_factory=list)
    slides: list[str] = field(default_factory=list)
