"""Testes do fluxo do agente com um LLM falso e roteirizado (sem internet e sem chave de API).

Verificam as regras de governança: ferramentas obrigatórias, bloqueios,
validação do texto, correção e queda para o texto padrão.
"""

import pytest
from langchain_core.messages import AIMessage

from srag_agent.agente import grafo as modulo_grafo
from srag_agent.agente.grafo import AgenteSRAG, ComentarioRelatorio
from srag_agent.governanca.auditoria import TrilhaAuditoria

METRICAS_FALSAS = {
    "data_referencia": "2025-06-25",
    "metricas": [
        {
            "nome": "Taxa de aumento de casos (7 dias)",
            "valor_percentual": -35.89,
            "numerador": 6698,
            "denominador": 10448,
            "periodo": "19/06/2025 a 25/06/2025",
            "definicao": "d",
        },
        {
            "nome": "Taxa de aumento de casos (30 dias)",
            "valor_percentual": 0.36,
            "numerador": 46845,
            "denominador": 46678,
            "periodo": "p",
            "definicao": "d",
        },
        {
            "nome": "Taxa de mortalidade (letalidade hospitalar por SRAG)",
            "valor_percentual": 8.48,
            "numerador": 2029,
            "denominador": 23927,
            "periodo": "p",
            "definicao": "d",
        },
        {
            "nome": "Taxa de ocupação de UTI (proxy)",
            "valor_percentual": 26.95,
            "numerador": 10673,
            "denominador": 39608,
            "periodo": "p",
            "definicao": "d",
        },
        {
            "nome": "Taxa de vacinação contra covid-19 (proxy)",
            "valor_percentual": 46.25,
            "numerador": 21399,
            "denominador": 46264,
            "periodo": "p",
            "definicao": "d",
        },
    ],
}
NOTICIAS_FALSAS = {
    "consulta": "x",
    "buscado_em_utc": "2026-11-13T10:00:00+00:00",
    "fonte": "teste",
    "noticias": [
        {
            "titulo": "InfoGripe aponta 18 estados em alerta",
            "veiculo": "Fiocruz",
            "publicada_em": "2026-11-12",
            "link": "https://exemplo.org",
        }
    ],
}


def _comentario(resumo: str) -> ComentarioRelatorio:
    return ComentarioRelatorio(
        resumo_executivo=resumo,
        comentarios_metricas=[{"metrica": "Taxa de mortalidade", "comentario": "Letalidade de 8,48%."}],
        contexto_noticias="O boletim cita 18 estados em alerta [1].",
        noticias_citadas=[1],
        pontos_de_atencao=["Atraso de notificação nos últimos dias."],
    )


class LLMRoteirizado:
    """Imita um chat model: devolve respostas pré-definidas, na ordem."""

    def __init__(self, respostas_orquestrador: list[AIMessage], respostas_redator: list[ComentarioRelatorio]):
        self.respostas_orquestrador = list(respostas_orquestrador)
        self.respostas_redator = list(respostas_redator)

    def bind_tools(self, _ferramentas):
        return self

    def with_structured_output(self, _esquema, **_opcoes):
        llm = self

        class _Redator:
            def invoke(self, _mensagens):
                return {"raw": AIMessage(""), "parsed": llm.respostas_redator.pop(0), "parsing_error": None}

        return _Redator()

    def invoke(self, _mensagens):
        resposta = self.respostas_orquestrador.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


def _chamada(nome: str, args: dict | None = None, id_: str = "1") -> dict:
    return {"name": nome, "args": args or {}, "id": id_, "type": "tool_call"}


@pytest.fixture(autouse=True)
def ferramentas_falsas(monkeypatch, tmp_path):
    monkeypatch.setattr(modulo_grafo, "calcular_metricas", lambda: METRICAS_FALSAS)
    monkeypatch.setattr(modulo_grafo, "gerar_graficos", lambda: {"grafico_diario": "d.png", "grafico_mensal": "m.png"})
    monkeypatch.setattr(modulo_grafo, "buscar_noticias", lambda consulta: {**NOTICIAS_FALSAS, "consulta": consulta})
    monkeypatch.setattr(modulo_grafo, "montar_relatorio", lambda estado, trilha, cfg: {"html": "r.html"})


def _executar(llm, tmp_path):
    trilha = TrilhaAuditoria(pasta=tmp_path)
    estado = AgenteSRAG(llm, trilha, {"provedor": "teste", "modelo": "roteirizado"}).executar()
    return estado, trilha


def test_fluxo_feliz_llm_escolhe_ferramentas_e_texto_e_aprovado(tmp_path):
    llm = LLMRoteirizado(
        [
            AIMessage(
                "",
                tool_calls=[
                    _chamada("consultar_metricas", id_="a"),
                    _chamada("gerar_graficos_relatorio", id_="b"),
                    _chamada("buscar_noticias_srag", {"consulta": "SRAG boletim"}, id_="c"),
                ],
            ),
            AIMessage("CONCLUIDO"),
        ],
        [_comentario("Queda de 35,9% na semana; letalidade de 8,48%.")],
    )
    estado, trilha = _executar(llm, tmp_path)
    assert estado["origem_texto"] == "llm"
    assert [e["nome"] for e in trilha.eventos_do_tipo("ferramenta")] == [
        "consultar_metricas",
        "gerar_graficos",
        "buscar_noticias",
    ]
    assert trilha.eventos_do_tipo("guardrail") == []
    assert trilha.arquivo.exists()


def test_sistema_executa_ferramentas_obrigatorias_que_o_llm_esqueceu(tmp_path):
    llm = LLMRoteirizado([AIMessage("CONCLUIDO")], [_comentario("Letalidade de 8,48%.")])
    estado, trilha = _executar(llm, tmp_path)
    assert estado["origem_texto"] == "llm"
    regras = [e["regra"] for e in trilha.eventos_do_tipo("guardrail")]
    assert regras.count("insumo_obrigatorio") == 3


def test_numero_inventado_gera_correcao_e_segunda_versao_e_aceita(tmp_path):
    llm = LLMRoteirizado(
        [AIMessage("CONCLUIDO")], [_comentario("Letalidade subiu para 12,7%."), _comentario("Letalidade de 8,48%.")]
    )
    estado, trilha = _executar(llm, tmp_path)
    assert estado["origem_texto"] == "llm"
    assert estado["tentativas_redacao"] == 2
    assert any("12,7" in e["detalhe"] for e in trilha.eventos_do_tipo("guardrail") if e["regra"] == "validacao_saida")


def test_llm_reprovado_em_todas_as_tentativas_cai_no_texto_padrao(tmp_path):
    invalido = _comentario("Houve 99.999 casos.")
    llm = LLMRoteirizado([AIMessage("CONCLUIDO")], [invalido, invalido, invalido])
    estado, trilha = _executar(llm, tmp_path)
    assert estado["origem_texto"] == "padrao"
    assert any(e["regra"] == "fallback_texto_padrao" for e in trilha.eventos_do_tipo("guardrail"))


def test_ferramenta_desconhecida_e_busca_fora_do_tema_sao_bloqueadas(tmp_path, monkeypatch):
    from srag_agent.ferramentas import noticias

    def busca_com_guardrail(consulta):
        if not modulo_grafo.guardrails.consulta_permitida(consulta):
            raise noticias.ConsultaForaDoTemaError(consulta)
        return NOTICIAS_FALSAS

    monkeypatch.setattr(modulo_grafo, "buscar_noticias", busca_com_guardrail)
    llm = LLMRoteirizado(
        [
            AIMessage(
                "",
                tool_calls=[
                    _chamada("apagar_banco", id_="x"),
                    _chamada("buscar_noticias_srag", {"consulta": "preço do bitcoin"}, id_="y"),
                ],
            ),
            AIMessage("CONCLUIDO"),
        ],
        [_comentario("Letalidade de 8,48%.")],
    )
    estado, trilha = _executar(llm, tmp_path)
    regras = {e["regra"] for e in trilha.eventos_do_tipo("guardrail")}
    assert {"ferramenta_nao_permitida", "consulta_fora_do_tema"} <= regras


def test_modo_sem_llm_gera_relatorio_com_texto_padrao(tmp_path):
    estado, trilha = _executar(None, tmp_path)
    assert estado["origem_texto"] == "padrao"
    assert estado["relatorio"] == {"html": "r.html"}


def test_falha_do_provedor_no_orquestrador_nao_derruba_o_relatorio(tmp_path):
    llm = LLMRoteirizado([ConnectionError("provedor fora do ar")], [_comentario("Letalidade de 8,48%.")])
    estado, trilha = _executar(llm, tmp_path)
    assert estado["origem_texto"] == "llm"
    assert trilha.eventos_do_tipo("erro_llm")[0]["etapa"] == "orquestrador"
