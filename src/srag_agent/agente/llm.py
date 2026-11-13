"""Criação do LLM a partir do .env, sem amarrar o projeto a um fornecedor.

Variáveis:
- LLM_PROVEDOR: "google" (padrão) ou "openai"
- LLM_MODELO: ex. "gemini-flash-latest" (padrão) ou "gpt-4o-mini"
- GOOGLE_API_KEY / OPENAI_API_KEY: a chave do provedor escolhido

Temperatura baixa: o relatório é técnico, queremos respostas estáveis.
"""

import os

from langchain_core.language_models import BaseChatModel

MODELO_PADRAO = {"google": "gemini-flash-latest", "openai": "gpt-4o-mini"}
TEMPERATURA = 0.2


class LLMNaoConfiguradoError(RuntimeError):
    """Não há chave de API: o relatório roda no modo sem LLM (texto padrão)."""


def descrever_configuracao() -> dict:
    provedor = os.getenv("LLM_PROVEDOR", "google").lower()
    return {
        "provedor": provedor,
        "modelo": os.getenv("LLM_MODELO", MODELO_PADRAO.get(provedor, "")),
        "temperatura": TEMPERATURA,
    }


def criar_llm() -> BaseChatModel:
    configuracao = descrever_configuracao()
    provedor, modelo = configuracao["provedor"], configuracao["modelo"]
    if provedor == "google":
        if not os.getenv("GOOGLE_API_KEY"):
            raise LLMNaoConfiguradoError("Defina GOOGLE_API_KEY no arquivo .env")
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=modelo, temperature=TEMPERATURA, max_retries=2)
    if provedor == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise LLMNaoConfiguradoError("Defina OPENAI_API_KEY no arquivo .env")
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=modelo, temperature=TEMPERATURA, max_retries=2)
    raise LLMNaoConfiguradoError(f"LLM_PROVEDOR desconhecido: {provedor!r} (use 'google' ou 'openai')")
