"""Criação do LLM a partir do .env, sem amarrar o projeto a um fornecedor.

Variáveis:
- LLM_PROVEDOR: "groq", "google" ou "openai". Se não for informado, usa o
  primeiro provedor que tiver chave configurada (nessa ordem).
- LLM_MODELO: opcional; cada provedor tem um modelo padrão.
- GROQ_API_KEY / GOOGLE_API_KEY / OPENAI_API_KEY: a chave do provedor escolhido.

Temperatura baixa: o relatório é técnico, queremos respostas estáveis.
"""

import os

from langchain_core.language_models import BaseChatModel

MODELO_PADRAO = {
    "groq": "openai/gpt-oss-120b",
    "google": "gemini-flash-latest",
    "openai": "gpt-4o-mini",
}
VARIAVEL_CHAVE = {"groq": "GROQ_API_KEY", "google": "GOOGLE_API_KEY", "openai": "OPENAI_API_KEY"}
URL_GROQ = "https://api.groq.com/openai/v1"
TEMPERATURA = 0.2


class LLMNaoConfiguradoError(RuntimeError):
    """Não há chave de API: o relatório roda no modo sem LLM (texto padrão)."""


def _provedor_escolhido() -> str:
    escolhido = os.getenv("LLM_PROVEDOR", "").strip().lower()
    if escolhido:
        return escolhido
    return next((provedor for provedor, chave in VARIAVEL_CHAVE.items() if os.getenv(chave)), "groq")


def descrever_configuracao() -> dict:
    provedor = _provedor_escolhido()
    return {
        "provedor": provedor,
        "modelo": os.getenv("LLM_MODELO") or MODELO_PADRAO.get(provedor, ""),
        "temperatura": TEMPERATURA,
    }


def criar_llm() -> BaseChatModel:
    configuracao = descrever_configuracao()
    provedor, modelo = configuracao["provedor"], configuracao["modelo"]
    if provedor not in VARIAVEL_CHAVE:
        raise LLMNaoConfiguradoError(f"LLM_PROVEDOR desconhecido: {provedor!r} (use groq, google ou openai)")
    chave = os.getenv(VARIAVEL_CHAVE[provedor])
    if not chave:
        raise LLMNaoConfiguradoError(f"Defina {VARIAVEL_CHAVE[provedor]} no arquivo .env")

    if provedor == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=modelo, temperature=TEMPERATURA, max_retries=2)

    from langchain_openai import ChatOpenAI

    # O Groq usa a mesma API da OpenAI, só muda o endereço
    base_url = URL_GROQ if provedor == "groq" else None
    return ChatOpenAI(model=modelo, temperature=TEMPERATURA, max_retries=2, api_key=chave, base_url=base_url)
