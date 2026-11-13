"""Ferramenta de métricas: consulta o banco com SQL FIXO e somente leitura.

Guardrail importante: o LLM nunca escreve SQL e nunca calcula números.
Ele só pode pedir "calcule as métricas" e recebe o resultado pronto,
com numerador, denominador e a definição de cada taxa (transparência).
"""

import sqlite3
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path

from srag_agent import config


@dataclass(frozen=True)
class Metrica:
    nome: str
    valor_percentual: float | None
    numerador: int
    denominador: int
    periodo: str
    definicao: str


def conectar_somente_leitura(caminho_banco: Path = config.ARQUIVO_BANCO) -> sqlite3.Connection:
    """Abre o SQLite em modo read-only: nenhuma consulta consegue alterar os dados."""
    return sqlite3.connect(f"file:{caminho_banco}?mode=ro", uri=True)


def _consultar_um_valor(conexao: sqlite3.Connection, sql: str, parametros: tuple = ()) -> int:
    return conexao.execute(sql, parametros).fetchone()[0] or 0


def obter_data_referencia(conexao: sqlite3.Connection) -> date:
    """Último dia COMPLETO da base.

    O último dia do arquivo é o dia da extração e chega incompleto
    (poucos registros), por isso é descartado.
    """
    ultima = _consultar_um_valor(conexao, f"SELECT MAX(data_notificacao) FROM {config.TABELA_CASOS}")
    return date.fromisoformat(ultima) - timedelta(days=1)


def _contar_casos(conexao: sqlite3.Connection, inicio: date, fim: date) -> int:
    sql = f"SELECT COUNT(*) FROM {config.TABELA_CASOS} WHERE data_notificacao BETWEEN ? AND ?"
    return _consultar_um_valor(conexao, sql, (inicio.isoformat(), fim.isoformat()))


def _br(dia: date) -> str:
    return dia.strftime("%d/%m/%Y")


def _percentual(numerador: int, denominador: int) -> float | None:
    return round(numerador / denominador * 100, 2) if denominador else None


def _proporcao(
    conexao: sqlite3.Connection,
    coluna: str,
    valores_numerador: tuple[str, ...],
    valores_denominador: tuple[str, ...],
    inicio: date,
    fim: date,
) -> tuple[int, int]:
    """Conta casos do período cuja coluna está no numerador e no denominador.

    O nome da coluna vem sempre do próprio código (nunca do LLM), então
    não há risco de SQL injection.
    """
    marcas_num = ",".join("?" * len(valores_numerador))
    marcas_den = ",".join("?" * len(valores_denominador))
    sql = f"""
        SELECT
            SUM(CASE WHEN {coluna} IN ({marcas_num}) THEN 1 ELSE 0 END),
            SUM(CASE WHEN {coluna} IN ({marcas_den}) THEN 1 ELSE 0 END)
        FROM {config.TABELA_CASOS}
        WHERE data_notificacao BETWEEN ? AND ?
    """
    parametros = (*valores_numerador, *valores_denominador, inicio.isoformat(), fim.isoformat())
    numerador, denominador = conexao.execute(sql, parametros).fetchone()
    return numerador or 0, denominador or 0


def calcular_taxa_aumento(conexao: sqlite3.Connection, referencia: date, dias: int) -> Metrica:
    inicio_atual = referencia - timedelta(days=dias - 1)
    fim_anterior = inicio_atual - timedelta(days=1)
    inicio_anterior = fim_anterior - timedelta(days=dias - 1)
    atual = _contar_casos(conexao, inicio_atual, referencia)
    anterior = _contar_casos(conexao, inicio_anterior, fim_anterior)
    variacao = round((atual / anterior - 1) * 100, 2) if anterior else None
    return Metrica(
        nome=f"Taxa de aumento de casos ({dias} dias)",
        valor_percentual=variacao,
        numerador=atual,
        denominador=anterior,
        periodo=f"{_br(inicio_atual)} a {_br(referencia)} vs {_br(inicio_anterior)} a {_br(fim_anterior)}",
        definicao=f"(casos notificados nos últimos {dias} dias / casos dos {dias} dias anteriores) - 1",
    )


def calcular_taxa_mortalidade(conexao: sqlite3.Connection, inicio: date, fim: date) -> Metrica:
    obitos, encerrados = _proporcao(
        conexao, "evolucao", ("Óbito",), ("Cura", "Óbito", "Óbito por outras causas"), inicio, fim
    )
    return Metrica(
        nome="Taxa de mortalidade (letalidade hospitalar por SRAG)",
        valor_percentual=_percentual(obitos, encerrados),
        numerador=obitos,
        denominador=encerrados,
        periodo=f"{_br(inicio)} a {_br(fim)}",
        definicao="óbitos por SRAG / casos com evolução conhecida (cura ou óbito)",
    )


def calcular_taxa_uti(conexao: sqlite3.Connection, inicio: date, fim: date) -> Metrica:
    em_uti, informados = _proporcao(conexao, "internado_uti", ("Sim",), ("Sim", "Não"), inicio, fim)
    return Metrica(
        nome="Taxa de ocupação de UTI (proxy: % de internados que foram para UTI)",
        valor_percentual=_percentual(em_uti, informados),
        numerador=em_uti,
        denominador=informados,
        periodo=f"{_br(inicio)} a {_br(fim)}",
        definicao="casos internados em UTI / casos com a informação de UTI preenchida (Sim ou Não)",
    )


def calcular_taxa_vacinacao(conexao: sqlite3.Connection, inicio: date, fim: date) -> Metrica:
    sql = f"""
        SELECT
            SUM(CASE WHEN vacina_covid_comprovada = 'Sim' THEN 1 ELSE 0 END),
            SUM(CASE WHEN vacina_covid IN ('Sim', 'Não') THEN 1 ELSE 0 END)
        FROM {config.TABELA_CASOS}
        WHERE data_notificacao BETWEEN ? AND ?
    """
    vacinados, informados = conexao.execute(sql, (inicio.isoformat(), fim.isoformat())).fetchone()
    vacinados, informados = vacinados or 0, informados or 0
    return Metrica(
        nome="Taxa de vacinação contra covid-19 (proxy: % dos casos com vacina comprovada)",
        valor_percentual=_percentual(vacinados, informados),
        numerador=vacinados,
        denominador=informados,
        periodo=f"{_br(inicio)} a {_br(fim)}",
        definicao="casos com vacina covid 'Sim' E data da 1ª dose registrada / casos com Sim ou Não informado",
    )


def calcular_metricas(caminho_banco: Path = config.ARQUIVO_BANCO) -> dict:
    """Calcula as 4 métricas do relatório. É esta função que vira a tool do agente."""
    with closing(conectar_somente_leitura(caminho_banco)) as conexao:
        referencia = obter_data_referencia(conexao)
        inicio_30d = referencia - timedelta(days=config.JANELA_LONGA_DIAS - 1)
        metricas = [
            calcular_taxa_aumento(conexao, referencia, config.JANELA_CURTA_DIAS),
            calcular_taxa_aumento(conexao, referencia, config.JANELA_LONGA_DIAS),
            calcular_taxa_mortalidade(conexao, inicio_30d, referencia),
            calcular_taxa_uti(conexao, inicio_30d, referencia),
            calcular_taxa_vacinacao(conexao, inicio_30d, referencia),
        ]
    return {"data_referencia": referencia.isoformat(), "metricas": [asdict(m) for m in metricas]}


if __name__ == "__main__":
    import json

    print(json.dumps(calcular_metricas(), ensure_ascii=False, indent=2))
