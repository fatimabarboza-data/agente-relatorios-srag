"""ETL: lê o CSV do Open DATASUS, trata os dados e grava no banco SQLite.

Decisões principais (detalhadas no README):
- Minimização de dados (LGPD): só entram no banco as colunas necessárias
  para as métricas. Dados que identificam ou ajudam a identificar o
  paciente (data de nascimento, município, unidade de saúde, ocupação,
  campos de texto livre, número da notificação) ficam de fora.
- A idade exata vira faixa etária.
- Códigos numéricos viram rótulos legíveis ("1" -> "Sim").
- Datas impossíveis (antes dos sintomas ou depois da extração) viram nulas.
"""

import logging
import sqlite3
from pathlib import Path

import pandas as pd

from srag_agent import config

logger = logging.getLogger(__name__)

COLUNAS_ORIGEM = [
    "DT_NOTIFIC",
    "DT_SIN_PRI",
    "SG_UF_NOT",
    "NU_IDADE_N",
    "TP_IDADE",
    "UTI",
    "DT_ENTUTI",
    "EVOLUCAO",
    "DT_EVOLUCA",
    "VACINA_COV",
    "DOSE_1_COV",
    "VACINA",
    "CLASSI_FIN",
]

ROTULOS_SIM_NAO = {1: "Sim", 2: "Não", 9: "Ignorado"}
ROTULOS_EVOLUCAO = {1: "Cura", 2: "Óbito", 3: "Óbito por outras causas", 9: "Ignorado"}
ROTULOS_CLASSIFICACAO = {
    1: "SRAG por influenza",
    2: "SRAG por outro vírus respiratório",
    3: "SRAG por outro agente etiológico",
    4: "SRAG não especificado",
    5: "SRAG por covid-19",
}

FAIXAS_ETARIAS = [0, 1, 5, 12, 18, 30, 45, 60, 75, 200]
ROTULOS_FAIXAS = ["<1", "1-4", "5-11", "12-17", "18-29", "30-44", "45-59", "60-74", "75+"]


def ler_csv(caminho: Path) -> pd.DataFrame:
    """Lê apenas as colunas necessárias do CSV original."""
    logger.info("Lendo %s", caminho.name)
    return pd.read_csv(caminho, sep=";", usecols=COLUNAS_ORIGEM, low_memory=False)


def converter_datas(df: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    """Converte texto em data; valores inválidos viram nulos."""
    for coluna in colunas:
        df[coluna] = pd.to_datetime(df[coluna], errors="coerce", format="mixed")
    return df


def calcular_faixa_etaria(idade: pd.Series, tipo_idade: pd.Series) -> pd.Series:
    """Converte a idade para anos (TP_IDADE: 1=dias, 2=meses, 3=anos) e agrupa em faixas."""
    divisor = tipo_idade.map({1: 365, 2: 12, 3: 1})
    idade_em_anos = idade / divisor
    return pd.cut(idade_em_anos, bins=FAIXAS_ETARIAS, labels=ROTULOS_FAIXAS, right=False).astype("string")


def anular_datas_impossiveis(df: pd.DataFrame, coluna: str, data_extracao: pd.Timestamp) -> pd.DataFrame:
    """Datas antes dos primeiros sintomas ou depois da extração são erro de digitação."""
    invalida = (df[coluna] < df["data_sintomas"]) | (df[coluna] > data_extracao)
    if invalida.any():
        logger.info("%s: %d datas impossíveis anuladas", coluna, int(invalida.sum()))
    df.loc[invalida, coluna] = pd.NaT
    return df


def tratar(bruto: pd.DataFrame) -> pd.DataFrame:
    """Aplica seleção, renomeação, rótulos e validações."""
    df = converter_datas(bruto.copy(), ["DT_NOTIFIC", "DT_SIN_PRI", "DT_ENTUTI", "DT_EVOLUCA"])
    df = df.dropna(subset=["DT_NOTIFIC", "DT_SIN_PRI"])

    tratado = pd.DataFrame(
        {
            "data_notificacao": df["DT_NOTIFIC"],
            "data_sintomas": df["DT_SIN_PRI"],
            "uf_notificacao": df["SG_UF_NOT"].astype("string").str.strip(),
            "faixa_etaria": calcular_faixa_etaria(df["NU_IDADE_N"], df["TP_IDADE"]),
            "internado_uti": df["UTI"].map(ROTULOS_SIM_NAO),
            "data_entrada_uti": df["DT_ENTUTI"],
            "evolucao": df["EVOLUCAO"].map(ROTULOS_EVOLUCAO),
            "data_evolucao": df["DT_EVOLUCA"],
            "vacina_covid": df["VACINA_COV"].map(ROTULOS_SIM_NAO),
            # Só a existência da data da 1ª dose interessa (comprovação); a data em si não entra no banco
            "vacina_covid_comprovada": (df["VACINA_COV"].eq(1) & df["DOSE_1_COV"].notna()).map(
                {True: "Sim", False: "Não"}
            ),
            "vacina_gripe": df["VACINA"].map(ROTULOS_SIM_NAO),
            "classificacao_final": df["CLASSI_FIN"].map(ROTULOS_CLASSIFICACAO),
        }
    )

    data_extracao = tratado["data_notificacao"].max()
    for coluna in ["data_entrada_uti", "data_evolucao"]:
        tratado = anular_datas_impossiveis(tratado, coluna, data_extracao)

    # Identificador artificial: o número da notificação original não vai para o banco
    tratado.insert(0, "id_caso", range(1, len(tratado) + 1))
    return tratado


def gravar_sqlite(df: pd.DataFrame, caminho_banco: Path, tabela: str) -> None:
    """Grava a tabela tratada no SQLite (datas como texto ISO AAAA-MM-DD)."""
    caminho_banco.parent.mkdir(parents=True, exist_ok=True)
    saida = df.copy()
    for coluna in saida.select_dtypes(include="datetime").columns:
        saida[coluna] = saida[coluna].dt.strftime("%Y-%m-%d")
    with sqlite3.connect(caminho_banco) as conexao:
        saida.to_sql(tabela, conexao, if_exists="replace", index=False)
        conexao.execute(f"CREATE INDEX IF NOT EXISTS idx_notificacao ON {tabela}(data_notificacao)")
    logger.info("%d linhas gravadas em %s", len(saida), caminho_banco.name)


def executar() -> None:
    """Ponto de entrada do ETL: python -m srag_agent.dados.etl"""
    bruto = ler_csv(config.ARQUIVO_CSV)
    tratado = tratar(bruto)
    logger.info("Linhas: %d lidas, %d após tratamento", len(bruto), len(tratado))
    gravar_sqlite(tratado, config.ARQUIVO_BANCO, config.TABELA_CASOS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    executar()
