"""Ferramenta de gráficos: casos diários (30 dias) e mensais (12 meses).

Escolhas de visualização (explicadas no README):
- Diário: colunas claras com os casos do dia + linha da média móvel de 7 dias.
  Notificação tem forte efeito de fim de semana e feriado; a média móvel
  mostra a tendência real sem esconder o dado bruto. Um eixo só.
- Mensal: colunas com o total do mês. Meses parciais (início/fim do arquivo)
  ganham textura e o rótulo "parcial"; meses fora do arquivo aparecem como
  contorno vazio, para nunca parecer que houve "zero casos".
- Grade horizontal fina e discreta, números no padrão brasileiro e fonte
  dos dados no rodapé.
"""

from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # gera imagens sem abrir janela
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

from srag_agent import config
from srag_agent.ferramentas.metricas import conectar_somente_leitura, obter_data_referencia

AZUL = "#2a78d6"
AZUL_CLARO = "#b9d3f2"
TEXTO = "#0b0b0b"
TEXTO_SECUNDARIO = "#52514e"
GRADE = "#e4e3df"
FUNDO = "#fcfcfb"
FONTE_DADOS = "Fonte: Open DATASUS - SRAG Hospitalizado (SIVEP-Gripe), arquivo de 26/06/2025. Data de notificação."

FERIADOS_NACIONAIS_2025 = {date(2025, 6, 19): "Corpus Christi"}
MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def _formatar_milhar(valor: float, _posicao=None) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def _estilo_base(ax) -> None:
    ax.set_facecolor(FUNDO)
    ax.figure.set_facecolor(FUNDO)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(TEXTO_SECUNDARIO)
    ax.grid(axis="y", color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=TEXTO_SECUNDARIO, length=0, labelsize=9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_formatar_milhar))


def _titulo(fig, titulo: str, subtitulo: str) -> None:
    fig.text(0.01, 0.97, titulo, fontsize=13, fontweight="bold", color=TEXTO, va="top")
    fig.text(0.01, 0.905, subtitulo, fontsize=9.5, color=TEXTO_SECUNDARIO, va="top")
    fig.text(0.01, 0.01, FONTE_DADOS, fontsize=7.5, color=TEXTO_SECUNDARIO)


def buscar_casos_diarios(conexao, inicio: date, fim: date) -> pd.Series:
    sql = f"""
        SELECT data_notificacao AS dia, COUNT(*) AS casos
        FROM {config.TABELA_CASOS}
        WHERE data_notificacao BETWEEN ? AND ?
        GROUP BY data_notificacao
    """
    df = pd.read_sql(sql, conexao, params=(inicio.isoformat(), fim.isoformat()), parse_dates=["dia"])
    todos_os_dias = pd.date_range(inicio, fim, freq="D")
    return df.set_index("dia")["casos"].reindex(todos_os_dias, fill_value=0)


def buscar_casos_mensais(conexao, referencia: date) -> pd.DataFrame:
    """Últimos 12 meses até a referência, com a situação de cobertura de cada mês."""
    meses = pd.period_range(end=pd.Period(referencia, "M"), periods=12, freq="M")
    sql = f"""
        SELECT substr(data_notificacao, 1, 7) AS mes, COUNT(*) AS casos,
               MIN(data_notificacao) AS primeiro_dia, MAX(data_notificacao) AS ultimo_dia
        FROM {config.TABELA_CASOS}
        WHERE data_notificacao BETWEEN ? AND ?
        GROUP BY mes
    """
    inicio = meses[0].start_time.date().isoformat()
    encontrados = pd.read_sql(sql, conexao, params=(inicio, referencia.isoformat())).set_index("mes")
    resultado = pd.DataFrame(index=[str(m) for m in meses]).join(encontrados)
    resultado["casos"] = resultado["casos"].fillna(0).astype(int)

    def situacao(linha) -> str:
        if pd.isna(linha["primeiro_dia"]):
            return "sem_dados"
        periodo = pd.Period(linha.name, "M")
        cobre_inicio = linha["primeiro_dia"] == periodo.start_time.date().isoformat()
        cobre_fim = linha["ultimo_dia"] == periodo.end_time.date().isoformat()
        return "completo" if cobre_inicio and cobre_fim else "parcial"

    resultado["situacao"] = resultado.apply(situacao, axis=1)
    return resultado


def gerar_grafico_diario(conexao, referencia: date, pasta: Path) -> Path:
    inicio = referencia - timedelta(days=config.JANELA_LONGA_DIAS - 1)
    # 6 dias extras antes da janela para a média móvel já começar completa
    serie_estendida = buscar_casos_diarios(conexao, inicio - timedelta(days=6), referencia)
    media_movel = serie_estendida.rolling(7).mean().loc[pd.Timestamp(inicio) :]
    serie = serie_estendida.loc[pd.Timestamp(inicio) :]

    fig, ax = plt.subplots(figsize=(11, 4.8))
    fig.subplots_adjust(top=0.80, bottom=0.14, left=0.06, right=0.90)
    _estilo_base(ax)
    ax.bar(serie.index, serie.values, width=0.7, color=AZUL_CLARO, label="Casos notificados no dia")
    ax.plot(media_movel.index, media_movel.values, color=AZUL, linewidth=2.2, label="Média móvel de 7 dias")

    ultimo_dia, ultimo_valor = media_movel.index[-1], media_movel.iloc[-1]
    ax.annotate(
        f"{_formatar_milhar(ultimo_valor)}/dia",
        (ultimo_dia, ultimo_valor),
        xytext=(8, 0),
        textcoords="offset points",
        va="center",
        fontsize=9,
        fontweight="bold",
        color=TEXTO,
    )

    for dia, nome in FERIADOS_NACIONAIS_2025.items():
        if inicio <= dia <= referencia:
            valor = serie.loc[pd.Timestamp(dia)]
            ax.annotate(
                f"Feriado\n({nome})",
                (pd.Timestamp(dia), valor),
                xytext=(0, 22),
                textcoords="offset points",
                ha="center",
                fontsize=8,
                color=TEXTO_SECUNDARIO,
                arrowprops={"arrowstyle": "-", "color": TEXTO_SECUNDARIO, "linewidth": 0.8},
            )

    ax.xaxis.set_major_locator(matplotlib.dates.WeekdayLocator(byweekday=0))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d/%m\n(seg)"))
    ax.set_xlim(pd.Timestamp(inicio) - pd.Timedelta(days=0.8), pd.Timestamp(referencia) + pd.Timedelta(days=0.8))
    ax.legend(
        loc="upper right", bbox_to_anchor=(1.0, 1.13), ncol=2, frameon=False, fontsize=9, labelcolor=TEXTO_SECUNDARIO
    )
    _titulo(
        fig,
        "Casos diários de SRAG - últimos 30 dias",
        f"{inicio:%d/%m/%Y} a {referencia:%d/%m/%Y}. Quedas nos fins de semana e feriados refletem a rotina "
        "de notificação, não menos doença.",
    )

    caminho = pasta / "casos_diarios_30d.png"
    fig.savefig(caminho, dpi=200, facecolor=FUNDO)
    plt.close(fig)
    return caminho


def gerar_grafico_mensal(conexao, referencia: date, pasta: Path) -> Path:
    dados = buscar_casos_mensais(conexao, referencia)
    rotulos = [f"{MESES_PT[pd.Period(m, 'M').month - 1]}\n{pd.Period(m, 'M').year}" for m in dados.index]
    posicoes = range(len(dados))
    topo = dados["casos"].max()

    fig, ax = plt.subplots(figsize=(11, 4.8))
    fig.subplots_adjust(top=0.80, bottom=0.16, left=0.06, right=0.98)
    _estilo_base(ax)

    for posicao, (_, linha) in zip(posicoes, dados.iterrows(), strict=True):
        if linha["situacao"] == "sem_dados":
            ax.bar(posicao, topo * 0.06, width=0.6, color="none", edgecolor=GRADE, linewidth=1, linestyle="-")
            ax.text(
                posicao, topo * 0.08, "fora do\narquivo", ha="center", va="bottom", fontsize=7.5, color=TEXTO_SECUNDARIO
            )
            continue
        parcial = linha["situacao"] == "parcial"
        ax.bar(
            posicao,
            linha["casos"],
            width=0.6,
            color=AZUL_CLARO if parcial else AZUL,
            hatch="////" if parcial else None,
            edgecolor=AZUL if parcial else AZUL,
            linewidth=0,
        )
        texto = _formatar_milhar(linha["casos"]) + ("\n(parcial)" if parcial else "")
        ax.text(
            posicao,
            linha["casos"] + topo * 0.015,
            texto,
            ha="center",
            va="bottom",
            fontsize=8.5,
            color=TEXTO,
            fontweight="bold" if not parcial else "normal",
        )

    ax.set_xticks(list(posicoes), rotulos)
    ax.set_ylim(0, topo * 1.18)
    primeiro = dados[dados["situacao"] != "sem_dados"]["primeiro_dia"].min()
    _titulo(
        fig,
        "Casos mensais de SRAG - últimos 12 meses",
        f"O arquivo cobre de {pd.Timestamp(primeiro):%d/%m/%Y} a {referencia:%d/%m/%Y}; "
        "meses anteriores não fazem parte da base disponibilizada. Hachurado = mês incompleto.",
    )

    caminho = pasta / "casos_mensais_12m.png"
    fig.savefig(caminho, dpi=200, facecolor=FUNDO)
    plt.close(fig)
    return caminho


def gerar_graficos(caminho_banco: Path = config.ARQUIVO_BANCO, pasta: Path = config.PASTA_SAIDAS) -> dict:
    """Gera os dois gráficos do relatório. É esta função que vira a tool do agente."""
    pasta.mkdir(parents=True, exist_ok=True)
    with closing(conectar_somente_leitura(caminho_banco)) as conexao:
        referencia = obter_data_referencia(conexao)
        diario = gerar_grafico_diario(conexao, referencia, pasta)
        mensal = gerar_grafico_mensal(conexao, referencia, pasta)
    return {"grafico_diario": str(diario), "grafico_mensal": str(mensal)}


if __name__ == "__main__":
    print(gerar_graficos())
