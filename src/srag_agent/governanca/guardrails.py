"""Guardrails: regras que protegem a entrada e a saída do agente.

Entrada
- consulta_permitida: o agente só pode buscar notícias sobre o tema do relatório.
- sanitizar_texto_externo: notícias são DADO, nunca instrução. Removo HTML,
  limito o tamanho e neutralizo frases típicas de prompt injection.

Saída
- encontrar_numeros_nao_rastreaveis: todo número citado pelo LLM tem que
  existir no resultado das ferramentas (o LLM não pode "inventar" métricas).
- citacoes_invalidas: o LLM só pode citar notícias que a ferramenta trouxe.
- mascarar_dados_pessoais: remove CPF, e-mail e telefone do texto final.
"""

import html
import re
import unicodedata

TERMOS_DO_TEMA = (
    "srag",
    "síndrome respiratória",
    "sindrome respiratoria",
    "influenza",
    "gripe",
    "covid",
    "vírus sincicial",
    "virus sincicial",
    "vsr",
    "respiratóri",
    "respiratori",
    "infogripe",
    "hospitaliza",
    "internaç",
    "internac",
    "uti",
    "vacina",
)

PADROES_INJECAO = re.compile(
    r"(ignore|desconsidere|esqueça|esqueca|disregard|forget)\b.{0,40}"
    r"(instru|prompt|regra|instruction|rule|anterior|previous)"
    r"|(system prompt|you are now|voc[eê] agora [ée]|aja como|act as)",
    re.IGNORECASE,
)

LIMITE_TEXTO_EXTERNO = 400

PADRAO_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
PADRAO_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
PADRAO_TELEFONE = re.compile(r"(\(?\b\d{2}\)?\s?)?\b9?\d{4}-\d{4}\b")


def _sem_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def consulta_permitida(consulta: str) -> bool:
    """A busca de notícias precisa citar algum termo do tema (SRAG e correlatos)."""
    texto = consulta.lower()
    return 3 <= len(texto) <= 120 and any(termo in texto for termo in TERMOS_DO_TEMA)


def sanitizar_texto_externo(texto: str) -> str:
    """Limpa texto vindo da internet antes de mostrá-lo ao LLM."""
    sem_html = re.sub(r"<[^>]+>", " ", html.unescape(texto or ""))
    compacto = re.sub(r"\s+", " ", sem_html).strip()
    neutralizado = PADROES_INJECAO.sub("[trecho removido pelo guardrail]", compacto)
    return neutralizado[:LIMITE_TEXTO_EXTERNO]


def mascarar_dados_pessoais(texto: str) -> str:
    texto = PADRAO_CPF.sub("[CPF removido]", texto)
    texto = PADRAO_EMAIL.sub("[e-mail removido]", texto)
    return PADRAO_TELEFONE.sub("[telefone removido]", texto)


def _para_numero(texto: str) -> float:
    """Converte '1.234,5' ou '1234.5' ou '35,89' em float."""
    texto = texto.strip()
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", texto):
        texto = texto.replace(".", "")
    return float(texto)


def numeros_permitidos(resultado_metricas: dict) -> set[float]:
    """Todos os números que o texto pode citar: valores, numeradores, denominadores."""
    permitidos: set[float] = {7.0, 12.0, 30.0}  # janelas citadas na própria definição
    for metrica in resultado_metricas.get("metricas", []):
        for chave in ("valor_percentual", "numerador", "denominador"):
            valor = metrica.get(chave)
            if valor is not None:
                permitidos.update({float(valor), abs(float(valor))})
    return permitidos


def numeros_do_texto(texto: str) -> set[float]:
    """Números presentes num texto de fonte (ex.: título de notícia)."""
    encontrados = set()
    for bruto in re.findall(r"\d[\d.,]*\d|\d", texto):
        try:
            encontrados.add(_para_numero(bruto.rstrip(".,")))
        except ValueError:
            continue
    return encontrados


def encontrar_numeros_nao_rastreaveis(
    texto: str, resultado_metricas: dict, extras: set[float] | None = None, tolerancia: float = 0.05
) -> list[str]:
    """Lista números do texto que não batem com nenhuma saída das ferramentas.

    `extras` permite números vindos das notícias (só na seção de contexto).
    Ignora datas (25/06/2025), anos (2024, 2025) e números de 1 dígito.
    """
    permitidos = numeros_permitidos(resultado_metricas) | (extras or set())
    sem_datas = re.sub(r"\b\d{1,2}/\d{1,2}(/\d{2,4})?\b", " ", texto)
    sem_datas = re.sub(r"\[\d+\]", " ", sem_datas)  # referências às notícias, ex.: [2]
    suspeitos = []
    for bruto in re.findall(r"-?\d[\d.,]*\d|\d", sem_datas):
        bruto = bruto.rstrip(".,")
        try:
            numero = _para_numero(bruto.lstrip("-"))
        except ValueError:
            continue
        if numero < 10 and "," not in bruto and "." not in bruto:
            continue
        if 1900 <= numero <= 2100 and "," not in bruto:
            continue
        # aceita arredondamentos que o texto possa fazer (ex.: 35,89 -> 35,9 ou 36)
        if not any(abs(numero - p) <= max(tolerancia, 0.51 if numero == round(numero) else 0.051) for p in permitidos):
            suspeitos.append(bruto)
    return suspeitos


def citacoes_invalidas(indices_citados: list[int], total_noticias: int) -> list[int]:
    return [indice for indice in indices_citados if not 1 <= indice <= total_noticias]


def normalizar_para_comparacao(texto: str) -> str:
    return _sem_acentos(texto).lower()
