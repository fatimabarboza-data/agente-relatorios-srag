"""Testes da montagem do relatório: segurança do HTML e formatação brasileira."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from srag_agent.agente import relatorio
from srag_agent.governanca.auditoria import TrilhaAuditoria
from tests.test_agente import METRICAS_FALSAS


def _imagem(caminho: Path) -> str:
    fig, _ = plt.subplots(figsize=(1, 1))
    fig.savefig(caminho)
    plt.close(fig)
    return str(caminho)


def _estado(tmp_path: Path, comentario: dict, noticias: list[dict]) -> dict:
    return {
        "metricas": METRICAS_FALSAS,
        "graficos": {"grafico_diario": _imagem(tmp_path / "d.png"), "grafico_mensal": _imagem(tmp_path / "m.png")},
        "noticias": noticias,
        "buscas_noticias": [{"consulta": "SRAG", "status": "ok"}],
        "comentario": comentario,
        "origem_texto": "llm",
    }


def test_formatacao_brasileira():
    assert relatorio.formatar_percentual(-35.89, sinal=True) == "−35,9%"
    assert relatorio.formatar_percentual(0.36, sinal=True) == "+0,4%"
    assert relatorio.formatar_inteiro(46845) == "46.845"
    assert relatorio.data_br("2025-06-25") == "25/06/2025"


def test_html_escapa_conteudo_externo_e_mascara_dados_pessoais(tmp_path):
    comentario = relatorio.texto_padrao(METRICAS_FALSAS, [])
    comentario["resumo_executivo"] += " Contato do paciente: 123.456.789-09."
    noticia_maliciosa = {
        "indice": 1,
        "titulo": "<script>alert('x')</script> SRAG",
        "veiculo": "Site",
        "publicada_em": "2026-11-12",
        "link": "https://exemplo.org",
    }
    trilha = TrilhaAuditoria(pasta=tmp_path)
    caminhos = relatorio.montar_relatorio(_estado(tmp_path, comentario, [noticia_maliciosa]), trilha, {}, tmp_path)

    html = Path(caminhos["html"]).read_text(encoding="utf-8")
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
    assert "123.456.789-09" not in html and "[CPF removido]" in html
    assert "−35,9%" in html
    assert Path(caminhos["markdown"]).exists()
