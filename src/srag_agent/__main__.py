"""Gera o relatório de SRAG.

Uso:
    python -m srag_agent              # com LLM (lê a chave do .env)
    python -m srag_agent --sem-llm    # sem LLM: texto padrão, útil para testar o pipeline
"""

import argparse
import logging

from dotenv import load_dotenv

from srag_agent import config
from srag_agent.agente.grafo import AgenteSRAG
from srag_agent.agente.llm import LLMNaoConfiguradoError, criar_llm, descrever_configuracao
from srag_agent.dados import etl
from srag_agent.governanca.auditoria import TrilhaAuditoria

logger = logging.getLogger("srag_agent")


def main() -> None:
    parser = argparse.ArgumentParser(description="Relatório automatizado de SRAG com agente de IA")
    parser.add_argument("--sem-llm", action="store_true", help="roda sem LLM (texto padrão)")
    parser.add_argument("--recarregar-dados", action="store_true", help="refaz o ETL a partir do CSV")
    argumentos = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv(config.RAIZ_PROJETO / ".env")

    if argumentos.recarregar_dados or not config.ARQUIVO_BANCO.exists():
        etl.executar()

    llm, configuracao_llm = None, {}
    if not argumentos.sem_llm:
        try:
            llm, configuracao_llm = criar_llm(), descrever_configuracao()
        except LLMNaoConfiguradoError as erro:
            logger.warning("%s. Seguindo sem LLM (texto padrão).", erro)

    trilha = TrilhaAuditoria()
    estado = AgenteSRAG(llm, trilha, configuracao_llm).executar()
    logger.info("Relatório: %s", estado["relatorio"]["html"])
    logger.info("Trilha de auditoria: %s", trilha.arquivo)


if __name__ == "__main__":
    main()
