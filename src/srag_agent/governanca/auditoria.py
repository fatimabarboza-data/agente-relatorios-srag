"""Trilha de auditoria: registra cada passo e cada decisão do agente.

Cada execução ganha um id único e um arquivo JSONL em logs/ (uma linha
por evento). Assim é possível responder, depois do fato:
- quais ferramentas o agente chamou, com quais argumentos e em que ordem;
- o que cada ferramenta devolveu (resumo) e quanto tempo levou;
- qual modelo e qual versão de prompt geraram o texto;
- quais guardrails dispararam e o que foi feito a respeito.

Nada de dado individual de paciente passa por aqui: só agregados.
"""

import hashlib
import json
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from srag_agent import config

LIMITE_CARACTERES_RESUMO = 2000


def _resumir(valor: Any) -> Any:
    """Evita logs gigantes: textos longos são cortados, mas com hash do conteúdo completo."""
    texto = json.dumps(valor, ensure_ascii=False, default=str)
    if len(texto) <= LIMITE_CARACTERES_RESUMO:
        return valor
    return {
        "resumo": texto[:LIMITE_CARACTERES_RESUMO] + "...",
        "sha256_conteudo_completo": hashlib.sha256(texto.encode()).hexdigest(),
    }


def hash_texto(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]


class TrilhaAuditoria:
    """Grava eventos de uma execução em logs/execucao_<data>_<id>.jsonl."""

    def __init__(self, pasta: Path = config.PASTA_LOGS) -> None:
        self.id_execucao = uuid.uuid4().hex[:12]
        pasta.mkdir(parents=True, exist_ok=True)
        carimbo = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        self.arquivo = pasta / f"execucao_{carimbo}_{self.id_execucao}.jsonl"
        self.eventos: list[dict] = []

    def registrar(self, tipo: str, **dados: Any) -> None:
        evento = {
            "momento_utc": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "id_execucao": self.id_execucao,
            "sequencia": len(self.eventos) + 1,
            "tipo": tipo,
            **{chave: _resumir(valor) for chave, valor in dados.items()},
        }
        self.eventos.append(evento)
        # Caminhos relativos ao projeto: o log não expõe a estrutura de pastas da máquina
        linha = json.dumps(evento, ensure_ascii=False, default=str).replace(str(config.RAIZ_PROJETO) + "/", "")
        with self.arquivo.open("a", encoding="utf-8") as saida:
            saida.write(linha + "\n")

    @contextmanager
    def cronometrar(self, tipo: str, **dados: Any):
        """Registra a duração e o sucesso/erro de um bloco (ex.: chamada de ferramenta)."""
        inicio = time.perf_counter()
        resultado: dict[str, Any] = {}
        try:
            yield resultado
        except Exception as erro:
            self.registrar(
                tipo, status="erro", erro=repr(erro), duracao_ms=round((time.perf_counter() - inicio) * 1000), **dados
            )
            raise
        self.registrar(tipo, status="ok", duracao_ms=round((time.perf_counter() - inicio) * 1000), **dados, **resultado)

    def eventos_do_tipo(self, tipo: str) -> list[dict]:
        return [evento for evento in self.eventos if evento["tipo"] == tipo]
