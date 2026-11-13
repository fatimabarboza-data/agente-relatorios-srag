"""Agente orquestrador (LangGraph).

Fluxo:

    START -> orquestrador <-> executar_ferramentas      (LLM decide quais ferramentas usar)
                  |
                  v
           garantir_insumos      (guardrail: métricas e gráficos são obrigatórios)
                  |
                  v
               redigir  <-+      (LLM escreve; guardrails validam; até 2 correções)
                  |-------+
                  v
           montar_relatorio -> END   (montagem determinística do HTML/Markdown)

Princípio: o LLM decide e escreve, mas NÃO calcula. Números, gráficos e a
tabela de métricas vêm sempre das ferramentas; o texto do LLM só entra no
relatório se passar pelos guardrails.
"""

import json
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from srag_agent.agente import prompts
from srag_agent.agente.relatorio import montar_relatorio, texto_padrao
from srag_agent.ferramentas.graficos import gerar_graficos
from srag_agent.ferramentas.metricas import calcular_metricas
from srag_agent.ferramentas.noticias import ConsultaForaDoTemaError, buscar_noticias
from srag_agent.governanca import guardrails
from srag_agent.governanca.auditoria import TrilhaAuditoria, hash_texto

MAXIMO_RODADAS_ORQUESTRADOR = 6
MAXIMO_BUSCAS_NOTICIAS = 3
MAXIMO_NOTICIAS_NO_RELATORIO = 12
MAXIMO_TENTATIVAS_REDACAO = 3  # 1 tentativa + 2 correções
CONSULTA_PADRAO_NOTICIAS = "SRAG casos Brasil"


# ---------- Ferramentas expostas ao LLM (só a assinatura; a execução é controlada abaixo) ----------


@tool
def consultar_metricas() -> str:
    """Calcula as métricas oficiais do relatório (aumento de casos, mortalidade, UTI, vacinação)."""
    return ""


@tool
def gerar_graficos_relatorio() -> str:
    """Gera os gráficos de casos diários (30 dias) e mensais (12 meses)."""
    return ""


@tool
def buscar_noticias_srag(consulta: str) -> str:
    """Busca notícias recentes sobre SRAG no Brasil. `consulta`: termos curtos em português."""
    return ""


FERRAMENTAS = [consultar_metricas, gerar_graficos_relatorio, buscar_noticias_srag]
NOMES_PERMITIDOS = {ferramenta.name for ferramenta in FERRAMENTAS}


def _modelo_da_resposta(mensagem) -> str | None:
    """Nome do modelo que de fato respondeu (o OpenRouter pode escolher entre vários)."""
    metadados = getattr(mensagem, "response_metadata", None) or {}
    return metadados.get("model_name") or metadados.get("model")


# ---------- Saída estruturada do redator ----------


class ComentarioMetrica(BaseModel):
    metrica: str = Field(description="Nome da métrica comentada, igual ao de <metricas>")
    comentario: str = Field(description="2 a 3 frases interpretando a métrica")


class ComentarioRelatorio(BaseModel):
    resumo_executivo: str = Field(description="3 a 5 frases com a leitura geral do cenário")
    comentarios_metricas: list[ComentarioMetrica]
    contexto_noticias: str = Field(description="Como as notícias ajudam a explicar o cenário, citando [n]")
    noticias_citadas: list[int] = Field(description="Números das notícias citadas")
    pontos_de_atencao: list[str] = Field(description="2 a 4 pontos de atenção para a vigilância")


# ---------- Estado ----------


class Estado(TypedDict, total=False):
    mensagens: Annotated[list, add_messages]
    rodadas: int
    metricas: dict
    graficos: dict
    noticias: list[dict]
    buscas_noticias: list[dict]
    comentario: dict
    origem_texto: Literal["llm", "padrao"]
    tentativas_redacao: int
    violacoes: list[str]
    relatorio: dict


class AgenteSRAG:
    def __init__(self, llm: BaseChatModel | None, trilha: TrilhaAuditoria, configuracao_llm: dict | None = None):
        self.llm = llm
        self.trilha = trilha
        self.configuracao_llm = configuracao_llm or {}
        self.grafo = self._construir_grafo()

    # ----- execução das ferramentas (com auditoria e guardrails) -----

    def _executar_metricas(self, estado: Estado) -> dict:
        with self.trilha.cronometrar("ferramenta", nome="consultar_metricas") as registro:
            resultado = calcular_metricas()
            registro["saida"] = resultado
        return {"metricas": resultado}

    def _executar_graficos(self, estado: Estado) -> dict:
        with self.trilha.cronometrar("ferramenta", nome="gerar_graficos") as registro:
            resultado = gerar_graficos()
            registro["saida"] = resultado
        return {"graficos": resultado}

    def _executar_busca(self, estado: Estado, consulta: str) -> dict:
        buscas = list(estado.get("buscas_noticias", []))
        noticias = list(estado.get("noticias", []))
        if len(buscas) >= MAXIMO_BUSCAS_NOTICIAS:
            self.trilha.registrar("guardrail", regra="limite_buscas", consulta=consulta, acao="busca ignorada")
            return {"buscas_noticias": buscas + [{"consulta": consulta, "status": "bloqueada: limite de buscas"}]}
        try:
            with self.trilha.cronometrar("ferramenta", nome="buscar_noticias", consulta=consulta) as registro:
                resultado = buscar_noticias(consulta)
                registro["quantidade"] = len(resultado["noticias"])
        except ConsultaForaDoTemaError as erro:
            self.trilha.registrar("guardrail", regra="consulta_fora_do_tema", consulta=consulta, acao=str(erro))
            return {"buscas_noticias": buscas + [{"consulta": consulta, "status": "bloqueada: fora do tema"}]}
        except Exception as erro:  # rede fora do ar não pode derrubar o relatório
            return {"buscas_noticias": buscas + [{"consulta": consulta, "status": f"falhou: {type(erro).__name__}"}]}

        titulos = {noticia["titulo"].lower() for noticia in noticias}
        for noticia in resultado["noticias"]:
            if len(noticias) >= MAXIMO_NOTICIAS_NO_RELATORIO:
                break
            if noticia["titulo"].lower() not in titulos:
                titulos.add(noticia["titulo"].lower())
                noticias.append({**noticia, "indice": len(noticias) + 1})
        busca = {
            "consulta": consulta,
            "status": "ok",
            "quantidade": len(resultado["noticias"]),
            "buscado_em_utc": resultado["buscado_em_utc"],
        }
        return {"buscas_noticias": buscas + [busca], "noticias": noticias}

    # ----- nós do grafo -----

    def no_orquestrador(self, estado: Estado) -> dict:
        mensagens = estado.get("mensagens") or [
            SystemMessage(prompts.ORQUESTRADOR),
            HumanMessage("Reúna os insumos para o relatório de SRAG."),
        ]
        try:
            resposta = self.llm.bind_tools(FERRAMENTAS).invoke(mensagens)
        except Exception as erro:  # falha do provedor: o sistema segue com os insumos obrigatórios
            causa = repr(erro.__cause__) if erro.__cause__ else None
            self.trilha.registrar("erro_llm", etapa="orquestrador", erro=repr(erro), causa=causa)
            resposta = AIMessage("CONCLUIDO")
        chamadas = [{"ferramenta": c["name"], "argumentos": c["args"]} for c in resposta.tool_calls]
        self.trilha.registrar(
            "decisao_llm",
            etapa="orquestrador",
            rodada=estado.get("rodadas", 0) + 1,
            modelo_que_respondeu=_modelo_da_resposta(resposta),
            chamadas_de_ferramenta=chamadas,
            texto=resposta.content,
        )
        novas = [] if estado.get("mensagens") else mensagens
        return {"mensagens": novas + [resposta], "rodadas": estado.get("rodadas", 0) + 1}

    def no_executar_ferramentas(self, estado: Estado) -> dict:
        ultima: AIMessage = estado["mensagens"][-1]
        atualizacao: dict[str, Any] = {}
        respostas = []
        for chamada in ultima.tool_calls:
            estado_atual = {**estado, **atualizacao}
            nome = chamada["name"]
            if nome not in NOMES_PERMITIDOS:
                self.trilha.registrar("guardrail", regra="ferramenta_nao_permitida", ferramenta=nome)
                conteudo = "Ferramenta não permitida."
            elif nome == "consultar_metricas":
                atualizacao.update(self._executar_metricas(estado_atual))
                conteudo = json.dumps(atualizacao["metricas"], ensure_ascii=False)
            elif nome == "gerar_graficos_relatorio":
                atualizacao.update(self._executar_graficos(estado_atual))
                conteudo = "Gráficos gerados."
            else:
                consulta = str(chamada["args"].get("consulta", ""))
                atualizacao.update(self._executar_busca(estado_atual, consulta))
                ultima_busca = atualizacao["buscas_noticias"][-1]
                conteudo = json.dumps(ultima_busca, ensure_ascii=False)
            respostas.append(ToolMessage(content=conteudo, tool_call_id=chamada["id"], name=nome))
        return {**atualizacao, "mensagens": respostas}

    def no_garantir_insumos(self, estado: Estado) -> dict:
        """Guardrail determinístico: o relatório nunca sai sem métricas e gráficos."""
        atualizacao: dict[str, Any] = {}
        if "metricas" not in estado:
            self.trilha.registrar("guardrail", regra="insumo_obrigatorio", acao="sistema executou consultar_metricas")
            atualizacao.update(self._executar_metricas(estado))
        if "graficos" not in estado:
            self.trilha.registrar("guardrail", regra="insumo_obrigatorio", acao="sistema executou gerar_graficos")
            atualizacao.update(self._executar_graficos(estado))
        if not any(busca["status"] == "ok" for busca in estado.get("buscas_noticias", [])):
            self.trilha.registrar(
                "guardrail",
                regra="insumo_obrigatorio",
                acao=f"sistema buscou notícias com a consulta padrão {CONSULTA_PADRAO_NOTICIAS!r}",
            )
            atualizacao.update(self._executar_busca(estado, CONSULTA_PADRAO_NOTICIAS))
        return atualizacao

    def _validar(self, comentario: ComentarioRelatorio, estado: Estado) -> list[str]:
        metricas, noticias = estado["metricas"], estado.get("noticias", [])
        violacoes = []
        textos_metricas = [
            comentario.resumo_executivo,
            *comentario.pontos_de_atencao,
            *(item.comentario for item in comentario.comentarios_metricas),
        ]
        for numero in guardrails.encontrar_numeros_nao_rastreaveis(" ".join(textos_metricas), metricas):
            violacoes.append(f"Número '{numero}' não existe em <metricas>.")
        numeros_noticias = guardrails.numeros_do_texto(" ".join(n["titulo"] for n in noticias))
        for numero in guardrails.encontrar_numeros_nao_rastreaveis(
            comentario.contexto_noticias, metricas, extras=numeros_noticias
        ):
            violacoes.append(f"Número '{numero}' no contexto não vem das métricas nem das notícias.")
        for indice in guardrails.citacoes_invalidas(comentario.noticias_citadas, len(noticias)):
            violacoes.append(f"Notícia [{indice}] citada mas não existe na lista.")
        return violacoes

    def no_redigir(self, estado: Estado) -> dict:
        tentativas = estado.get("tentativas_redacao", 0) + 1
        if self.llm is None:
            self.trilha.registrar("decisao_sistema", etapa="redigir", acao="texto padrão (modo sem LLM)")
            return {
                "comentario": texto_padrao(estado["metricas"], estado.get("noticias", [])),
                "origem_texto": "padrao",
                "tentativas_redacao": tentativas,
            }

        noticias_formatadas = (
            "\n".join(
                f"[{n['indice']}] {n['titulo']} ({n['veiculo']}, {n['publicada_em']})"
                for n in estado.get("noticias", [])
            )
            or "(nenhuma notícia disponível)"
        )
        buscadas_em = next(
            (b.get("buscado_em_utc") for b in estado.get("buscas_noticias", []) if b.get("buscado_em_utc")),
            "indisponível",
        )
        correcao = (
            prompts.CORRECAO.format(motivos="\n".join(f"- {v}" for v in estado["violacoes"]))
            if estado.get("violacoes")
            else ""
        )
        sistema = prompts.REDATOR.format(data_referencia=estado["metricas"]["data_referencia"])
        entrada = prompts.REDATOR_ENTRADA.format(
            metricas=json.dumps(estado["metricas"], ensure_ascii=False, indent=2),
            noticias=noticias_formatadas,
            buscadas_em=buscadas_em,
            correcao=correcao,
        )

        try:
            resultado = self.llm.with_structured_output(
                ComentarioRelatorio, method="function_calling", include_raw=True
            ).invoke([SystemMessage(sistema), HumanMessage(entrada)])
            comentario = resultado["parsed"]
            if comentario is None:
                raise ValueError(f"Saída fora do formato esperado: {resultado.get('parsing_error')!r}")
        except Exception as erro:
            causa = repr(erro.__cause__) if erro.__cause__ else None
            self.trilha.registrar("erro_llm", etapa="redigir", tentativa=tentativas, erro=repr(erro), causa=causa)
            return {"violacoes": [f"Falha na chamada ao LLM: {type(erro).__name__}"], "tentativas_redacao": tentativas}

        violacoes = self._validar(comentario, estado)
        self.trilha.registrar(
            "decisao_llm",
            etapa="redigir",
            tentativa=tentativas,
            modelo_que_respondeu=_modelo_da_resposta(resultado.get("raw")),
            hash_prompt_sistema=hash_texto(sistema),
            hash_entrada=hash_texto(entrada),
            aprovado=not violacoes,
            violacoes=violacoes,
        )
        if violacoes:
            for violacao in violacoes:
                self.trilha.registrar("guardrail", regra="validacao_saida", tentativa=tentativas, detalhe=violacao)
            return {"violacoes": violacoes, "tentativas_redacao": tentativas}
        return {
            "comentario": comentario.model_dump(),
            "origem_texto": "llm",
            "violacoes": [],
            "tentativas_redacao": tentativas,
        }

    def no_texto_padrao(self, estado: Estado) -> dict:
        """Se o LLM não passar nos guardrails após as correções, usa texto determinístico."""
        self.trilha.registrar(
            "guardrail",
            regra="fallback_texto_padrao",
            acao="texto do LLM descartado após tentativas esgotadas",
            ultimas_violacoes=estado.get("violacoes", []),
        )
        return {"comentario": texto_padrao(estado["metricas"], estado.get("noticias", [])), "origem_texto": "padrao"}

    def no_montar_relatorio(self, estado: Estado) -> dict:
        with self.trilha.cronometrar("montagem_relatorio") as registro:
            caminhos = montar_relatorio(estado, self.trilha, self.configuracao_llm)
            registro["arquivos"] = caminhos
        return {"relatorio": caminhos}

    # ----- roteamento -----

    def _depois_orquestrador(self, estado: Estado) -> str:
        ultima = estado["mensagens"][-1]
        if getattr(ultima, "tool_calls", None) and estado.get("rodadas", 0) < MAXIMO_RODADAS_ORQUESTRADOR:
            return "executar_ferramentas"
        if getattr(ultima, "tool_calls", None):
            self.trilha.registrar("guardrail", regra="limite_rodadas", acao="orquestração encerrada")
        return "garantir_insumos"

    def _depois_redigir(self, estado: Estado) -> str:
        if "comentario" in estado and not estado.get("violacoes"):
            return "montar_relatorio"
        if estado.get("tentativas_redacao", 0) >= MAXIMO_TENTATIVAS_REDACAO:
            return "texto_padrao"
        return "redigir"

    def _construir_grafo(self):
        grafo = StateGraph(Estado)
        grafo.add_node("garantir_insumos", self.no_garantir_insumos)
        grafo.add_node("redigir", self.no_redigir)
        grafo.add_node("texto_padrao", self.no_texto_padrao)
        grafo.add_node("montar_relatorio", self.no_montar_relatorio)
        if self.llm is not None:
            grafo.add_node("orquestrador", self.no_orquestrador)
            grafo.add_node("executar_ferramentas", self.no_executar_ferramentas)
            grafo.add_edge(START, "orquestrador")
            grafo.add_conditional_edges(
                "orquestrador", self._depois_orquestrador, ["executar_ferramentas", "garantir_insumos"]
            )
            grafo.add_edge("executar_ferramentas", "orquestrador")
        else:
            grafo.add_edge(START, "garantir_insumos")
        grafo.add_edge("garantir_insumos", "redigir")
        grafo.add_conditional_edges("redigir", self._depois_redigir, ["redigir", "texto_padrao", "montar_relatorio"])
        grafo.add_edge("texto_padrao", "montar_relatorio")
        grafo.add_edge("montar_relatorio", END)
        return grafo.compile()

    def executar(self) -> Estado:
        self.trilha.registrar(
            "inicio_execucao", llm=self.configuracao_llm or "sem LLM", versao_prompts=prompts.VERSAO_PROMPTS
        )
        estado_final = self.grafo.invoke({}, {"recursion_limit": 40})
        self.trilha.registrar(
            "fim_execucao", origem_texto=estado_final.get("origem_texto"), arquivos=estado_final.get("relatorio")
        )
        return estado_final
