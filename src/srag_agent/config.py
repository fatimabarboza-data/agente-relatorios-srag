"""Configurações centrais do projeto (caminhos e parâmetros).

Tudo que pode mudar entre ambientes fica aqui ou no arquivo .env,
nunca espalhado pelo código.
"""

from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parents[2]

PASTA_DADOS_BRUTOS = RAIZ_PROJETO / "data" / "raw"
PASTA_DADOS_TRATADOS = RAIZ_PROJETO / "data" / "processed"
PASTA_SAIDAS = RAIZ_PROJETO / "outputs"
PASTA_LOGS = RAIZ_PROJETO / "logs"

# CSV original compactado (19 MB): o pandas lê direto do .zip
ARQUIVO_CSV = PASTA_DADOS_BRUTOS / "INFLUD25_DATASUS-Versao26-06-2025.zip"
ARQUIVO_BANCO = PASTA_DADOS_TRATADOS / "srag.db"
TABELA_CASOS = "casos_srag"

# Janelas usadas nas métricas (em dias)
JANELA_CURTA_DIAS = 7
JANELA_LONGA_DIAS = 30
