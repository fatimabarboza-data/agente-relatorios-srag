"""Testes da camada de dados com uma base pequena e controlada (sem o CSV real)."""

import sqlite3
from datetime import date

import pandas as pd
import pytest

from srag_agent import config
from srag_agent.dados import etl
from srag_agent.ferramentas import metricas


def _linha(dt_notific, uti=2, evolucao=1, vacina_cov=2, dose1=None, idade=40, tipo_idade=3):
    return {
        "DT_NOTIFIC": dt_notific,
        "DT_SIN_PRI": dt_notific,
        "SG_UF_NOT": "SP",
        "NU_IDADE_N": idade,
        "TP_IDADE": tipo_idade,
        "UTI": uti,
        "DT_ENTUTI": None,
        "EVOLUCAO": evolucao,
        "DT_EVOLUCA": None,
        "VACINA_COV": vacina_cov,
        "DOSE_1_COV": dose1,
        "VACINA": 2,
        "CLASSI_FIN": 4,
    }


@pytest.fixture
def banco_teste(tmp_path):
    linhas = (
        # 2 casos na semana anterior (12 a 18/06)
        [_linha("2025-06-15"), _linha("2025-06-16")]
        # 4 casos na semana atual (19 a 25/06): 1 óbito, 2 em UTI, 1 vacinado comprovado
        + [
            _linha("2025-06-20", uti=1, evolucao=2),
            _linha("2025-06-21", uti=1),
            _linha("2025-06-22", vacina_cov=1, dose1="2023-01-01"),
            _linha("2025-06-25"),
        ]
        # dia da extração, incompleto: deve ser ignorado
        + [_linha("2025-06-26")]
    )
    tratado = etl.tratar(pd.DataFrame(linhas))
    caminho = tmp_path / "teste.db"
    etl.gravar_sqlite(tratado, caminho, config.TABELA_CASOS)
    return caminho


def test_faixa_etaria_converte_dias_e_meses_para_anos():
    idades = pd.Series([10, 6, 3, 80])
    tipos = pd.Series([1, 2, 3, 3])  # 10 dias, 6 meses, 3 anos, 80 anos
    assert etl.calcular_faixa_etaria(idades, tipos).tolist() == ["<1", "<1", "1-4", "75+"]


def test_etl_nao_grava_colunas_sensiveis(banco_teste):
    with sqlite3.connect(banco_teste) as conexao:
        colunas = [c[1] for c in conexao.execute(f"PRAGMA table_info({config.TABELA_CASOS})")]
    for proibida in ["DT_NASC", "NU_NOTIFIC", "NU_IDADE_N", "ID_MUNICIP", "NM_UN_INTE"]:
        assert proibida not in colunas


def test_data_referencia_descarta_dia_da_extracao(banco_teste):
    with metricas.conectar_somente_leitura(banco_teste) as conexao:
        assert metricas.obter_data_referencia(conexao) == date(2025, 6, 25)


def test_metricas_batem_com_a_conta_manual(banco_teste):
    resultado = {m["nome"]: m for m in metricas.calcular_metricas(banco_teste)["metricas"]}
    aumento = resultado["Taxa de aumento de casos (7 dias)"]
    assert (aumento["numerador"], aumento["denominador"], aumento["valor_percentual"]) == (4, 2, 100.0)
    mortalidade = next(m for n, m in resultado.items() if n.startswith("Taxa de mortalidade"))
    assert (mortalidade["numerador"], mortalidade["denominador"]) == (1, 6)
    uti = next(m for n, m in resultado.items() if n.startswith("Taxa de ocupação de UTI"))
    assert (uti["numerador"], uti["denominador"]) == (2, 6)
    vacina = next(m for n, m in resultado.items() if n.startswith("Taxa de vacinação"))
    assert (vacina["numerador"], vacina["denominador"]) == (1, 6)


def test_conexao_somente_leitura_bloqueia_escrita(banco_teste):
    with metricas.conectar_somente_leitura(banco_teste) as conexao, pytest.raises(sqlite3.OperationalError):
        conexao.execute(f"DELETE FROM {config.TABELA_CASOS}")
