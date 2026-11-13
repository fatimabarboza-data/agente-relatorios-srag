"""Ferramenta de notícias: busca notícias recentes sobre SRAG no Google Notícias (RSS).

Por que RSS do Google Notícias:
- não exige cadastro nem chave de API (qualquer avaliador consegue rodar);
- agrega veículos brasileiros e devolve título, veículo, data e link.

Guardrails aplicados aqui:
- só aceita consultas sobre o tema (consulta_permitida);
- título/veículo passam por sanitizar_texto_externo antes de chegar ao LLM;
- quantidade de resultados limitada e duplicados removidos;
- timeout curto: se a internet falhar, o relatório sai sem notícias e avisa.
"""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import feedparser
import httpx

from srag_agent.governanca.guardrails import consulta_permitida, sanitizar_texto_externo

URL_RSS = "https://news.google.com/rss/search?q={consulta}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
TIMEOUT_SEGUNDOS = 10
MAXIMO_RESULTADOS = 8


@dataclass(frozen=True)
class Noticia:
    titulo: str
    veiculo: str
    publicada_em: str
    link: str


class ConsultaForaDoTemaError(ValueError):
    """A consulta não é sobre SRAG/doenças respiratórias e foi bloqueada."""


def _data_iso(texto: str) -> str:
    try:
        return parsedate_to_datetime(texto).astimezone(UTC).date().isoformat()
    except (TypeError, ValueError):
        return ""


def interpretar_rss(conteudo_xml: str, maximo: int = MAXIMO_RESULTADOS) -> list[Noticia]:
    """Transforma o XML do RSS em uma lista limpa de notícias (sem duplicatas)."""
    feed = feedparser.parse(conteudo_xml)
    noticias: list[Noticia] = []
    titulos_vistos: set[str] = set()
    for item in feed.entries:
        veiculo = sanitizar_texto_externo(item.get("source", {}).get("title", ""))
        titulo = sanitizar_texto_externo(item.get("title", ""))
        # O Google Notícias costuma terminar o título com " - Nome do Veículo"
        if veiculo and titulo.endswith(f" - {veiculo}"):
            titulo = titulo[: -len(f" - {veiculo}")]
        chave = titulo.lower()
        if not titulo or chave in titulos_vistos:
            continue
        titulos_vistos.add(chave)
        noticias.append(Noticia(titulo, veiculo, _data_iso(item.get("published", "")), item.get("link", "")))
    noticias.sort(key=lambda noticia: noticia.publicada_em, reverse=True)
    return noticias[:maximo]


def buscar_noticias(consulta: str, maximo: int = MAXIMO_RESULTADOS) -> dict:
    """Busca notícias sobre SRAG. É esta função que vira a tool do agente."""
    if not consulta_permitida(consulta):
        raise ConsultaForaDoTemaError(f"Consulta bloqueada (fora do tema SRAG): {consulta!r}")
    url = URL_RSS.format(consulta=quote_plus(consulta))
    resposta = httpx.get(
        url,
        timeout=TIMEOUT_SEGUNDOS,
        follow_redirects=True,
        headers={"User-Agent": "srag-agent/1.0 (PoC Indicium HealthCare)"},
    )
    resposta.raise_for_status()
    noticias = interpretar_rss(resposta.text, maximo=min(maximo, MAXIMO_RESULTADOS))
    return {
        "consulta": consulta,
        "buscado_em_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "fonte": "Google Notícias (RSS)",
        "noticias": [asdict(noticia) for noticia in noticias],
    }
