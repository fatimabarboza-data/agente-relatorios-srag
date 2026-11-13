"""Montagem determinística do relatório (HTML para leitura/impressão e Markdown).

O LLM não monta o relatório: ele só fornece os comentários (já validados).
Tabela de métricas, gráficos, lista de notícias e a seção de governança
são preenchidos aqui, direto das saídas das ferramentas e da trilha de auditoria.
O layout fica em templates/ (Jinja2), separado da lógica.
"""

import base64
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape

from srag_agent import config
from srag_agent.governanca.guardrails import mascarar_dados_pessoais

PASTA_TEMPLATES = Path(__file__).parent / "templates"
FUSO_HORARIO = ZoneInfo("America/Sao_Paulo")

AVISO = (
    "Relatório gerado automaticamente por um agente de IA como prova de conceito. "
    "Não substitui boletins oficiais nem avaliação de profissionais de saúde, "
    "e não contém orientação médica individual."
)

LIMITACOES = [
    "O arquivo disponibilizado cobre de 29/12/2024 a 26/06/2025; o gráfico de 12 meses mostra "
    "os meses anteriores como fora do arquivo.",
    "Ocupação de UTI é aproximada pela proporção de internados que foram para UTI: a base não "
    "informa a quantidade de leitos disponíveis.",
    "Vacinação é aproximada pela proporção de casos internados com vacina contra covid-19 "
    "comprovada (data da 1ª dose registrada); não é a cobertura vacinal da população.",
    "Mortalidade é a letalidade hospitalar: óbitos por SRAG entre casos já encerrados. Casos "
    "ainda em aberto ficam fora do cálculo.",
    "Os últimos dias recebem notificações com atraso; quedas recentes tendem a ser revistas para cima.",
]


# ---------- formatação ----------


def formatar_percentual(valor: float | None, sinal: bool = False) -> str:
    if valor is None:
        return "n/d"
    texto = f"{abs(valor):,.1f}".replace(",", "X").replace(".", ",").replace("X", ".") + "%"
    if sinal:
        return ("+" if valor > 0 else "−" if valor < 0 else "") + texto
    return texto


def formatar_inteiro(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


def data_br(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%d/%m/%Y") if iso else ""


def _metrica(metricas: dict, inicio_nome: str) -> dict:
    return next(m for m in metricas["metricas"] if m["nome"].startswith(inicio_nome))


def _e_aumento(metrica: dict) -> bool:
    return metrica["nome"].startswith("Taxa de aumento")


# ---------- texto padrão (sem LLM ou quando o LLM é reprovado) ----------


def texto_padrao(metricas: dict, noticias: list[dict]) -> dict:
    aumento7 = _metrica(metricas, "Taxa de aumento de casos (7")
    aumento30 = _metrica(metricas, "Taxa de aumento de casos (30")
    mortalidade = _metrica(metricas, "Taxa de mortalidade")
    uti = _metrica(metricas, "Taxa de ocupação de UTI")
    vacina = _metrica(metricas, "Taxa de vacinação")
    return {
        "resumo_executivo": (
            f"Até {data_br(metricas['data_referencia'])}, os casos notificados nos últimos 7 dias variaram "
            f"{formatar_percentual(aumento7['valor_percentual'], sinal=True)} em relação à semana anterior e "
            f"{formatar_percentual(aumento30['valor_percentual'], sinal=True)} na comparação de 30 dias. "
            f"A letalidade hospitalar foi de {formatar_percentual(mortalidade['valor_percentual'])}, "
            f"{formatar_percentual(uti['valor_percentual'])} dos internados com informação foram para UTI e "
            f"{formatar_percentual(vacina['valor_percentual'])} tinham vacina contra covid-19 comprovada."
        ),
        "comentarios_metricas": [
            {"metrica": m["nome"], "comentario": f"Definição: {m['definicao']}. Período: {m['periodo']}."}
            for m in metricas["metricas"]
        ],
        "contexto_noticias": (
            "Texto padrão gerado sem LLM: as notícias abaixo foram coletadas automaticamente e não foram interpretadas."
            if noticias
            else "Nenhuma notícia pôde ser coletada nesta execução."
        ),
        "noticias_citadas": [],
        "pontos_de_atencao": [
            "Quedas nos dias mais recentes podem refletir atraso de notificação, fins de semana e feriados.",
            "UTI e vacinação são aproximações; consulte as definições antes de comparar com outras fontes.",
        ],
    }


# ---------- montagem ----------


def _ambiente(autoescape: bool) -> Environment:
    ambiente = Environment(
        loader=FileSystemLoader(PASTA_TEMPLATES),
        autoescape=select_autoescape(["html", "j2"]) if autoescape else False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    ambiente.filters.update(seguro=mascarar_dados_pessoais, inteiro=formatar_inteiro, data_br=data_br)
    return ambiente


def _imagem_base64(caminho: str) -> str:
    return "data:image/png;base64," + base64.b64encode(Path(caminho).read_bytes()).decode()


def _cartoes(metricas: dict) -> list[dict]:
    aumento7 = _metrica(metricas, "Taxa de aumento de casos (7")
    aumento30 = _metrica(metricas, "Taxa de aumento de casos (30")
    mortalidade = _metrica(metricas, "Taxa de mortalidade")
    uti = _metrica(metricas, "Taxa de ocupação de UTI")
    vacina = _metrica(metricas, "Taxa de vacinação")

    def proporcao(m: dict, unidade: str) -> str:
        return f"{formatar_inteiro(m['numerador'])} / {formatar_inteiro(m['denominador'])} {unidade}"

    return [
        {
            "titulo": "Aumento de casos (7 dias vs. 7 anteriores)",
            "valor": formatar_percentual(aumento7["valor_percentual"], sinal=True),
            "detalhe": proporcao(aumento7, "casos").replace(" / ", " vs. "),
            "nota": f"Em 30 dias: {formatar_percentual(aumento30['valor_percentual'], sinal=True)}",
        },
        {
            "titulo": "Mortalidade (letalidade hospitalar)",
            "valor": formatar_percentual(mortalidade["valor_percentual"]),
            "detalhe": proporcao(mortalidade, "casos encerrados"),
            "nota": "Últimos 30 dias",
        },
        {
            "titulo": "Internados que foram para UTI*",
            "valor": formatar_percentual(uti["valor_percentual"]),
            "detalhe": proporcao(uti, "casos"),
            "nota": "Últimos 30 dias",
        },
        {
            "titulo": "Casos com vacina covid comprovada*",
            "valor": formatar_percentual(vacina["valor_percentual"]),
            "detalhe": proporcao(vacina, "casos"),
            "nota": "Últimos 30 dias",
        },
    ]


def _contexto(estado: dict, trilha, configuracao_llm: dict, gerado_em: str) -> dict:
    metricas = estado["metricas"]
    inicio = trilha.eventos_do_tipo("inicio_execucao")
    return {
        "referencia": data_br(metricas["data_referencia"]),
        "gerado_em": gerado_em,
        "id_execucao": trilha.id_execucao,
        "aviso": AVISO,
        "comentario": estado["comentario"],
        "cartoes": _cartoes(metricas),
        "metricas": [
            {**m, "valor_formatado": formatar_percentual(m["valor_percentual"], sinal=_e_aumento(m))}
            for m in metricas["metricas"]
        ],
        "noticias": estado.get("noticias", []),
        "buscas": estado.get("buscas_noticias", []),
        "limitacoes": LIMITACOES,
        "governanca": {
            "origem": (
                "Comentários escritos pelo LLM e aprovados pelos guardrails."
                if estado.get("origem_texto") == "llm"
                else "Comentários em texto padrão determinístico (sem LLM ou LLM reprovado)."
            ),
            "modelo": (
                f"{configuracao_llm['provedor']} / {configuracao_llm['modelo']}"
                if configuracao_llm
                else "não utilizado"
            ),
            "versao_prompts": inicio[0].get("versao_prompts", "") if inicio else "",
            "ferramentas": [e["nome"] for e in trilha.eventos_do_tipo("ferramenta")],
            "eventos_guardrail": len(trilha.eventos_do_tipo("guardrail")),
            "arquivo_log": trilha.arquivo.name,
        },
    }


def montar_relatorio(estado: dict, trilha, configuracao_llm: dict, pasta: Path = config.PASTA_SAIDAS) -> dict:
    pasta.mkdir(parents=True, exist_ok=True)
    gerado_em = datetime.now(FUSO_HORARIO).strftime("%d/%m/%Y %H:%M")
    contexto = _contexto(estado, trilha, configuracao_llm, gerado_em)

    html = (
        _ambiente(autoescape=True)
        .get_template("relatorio.html.j2")
        .render(
            **contexto,
            grafico_diario=_imagem_base64(estado["graficos"]["grafico_diario"]),
            grafico_mensal=_imagem_base64(estado["graficos"]["grafico_mensal"]),
        )
    )
    markdown = _ambiente(autoescape=False).get_template("relatorio.md.j2").render(**contexto)

    caminho_html, caminho_md = pasta / "relatorio_srag.html", pasta / "relatorio_srag.md"
    caminho_html.write_text(html, encoding="utf-8")
    caminho_md.write_text(markdown, encoding="utf-8")
    return {"html": str(caminho_html), "markdown": str(caminho_md)}
