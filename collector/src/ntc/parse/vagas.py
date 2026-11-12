"""Total de vagas imediatas declarado no edital ("destina-se ao provimento de 15 (quinze) vagas").

Só a frase de destinação do concurso conta. Vagas de cadastro reserva, de reserva para
cotas e totais por cargo em tabelas ficam de fora: se o edital não declara o total numa
frase, o campo fica `ausente` e o porte, `indefinido`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ntc.model.schema import TRECHO_MAX
from ntc.parse.clausulas import segmentos

_DESTINA = re.compile(
    r"destina(?:-se|m-se)?\s+ao\s+(?:provimento|preenchimento)\s+de\s+"
    r"(\d{1,3}(?:\.\d{3})*|\d+)\s*(?:\([^)]{2,60}\)\s*)?vagas?",
    re.IGNORECASE,
)
_EXCLUI = re.compile(r"cadastro\s+(?:de\s+)?reserva|forma[çc][ãa]o\s+de\s+cadastro", re.IGNORECASE)


@dataclass(frozen=True)
class CandidatoVagas:
    pagina: int
    trecho: str
    valor: int


def encontrar(paginas: dict[int, str]) -> list[CandidatoVagas]:
    achados = []
    for n in sorted(paginas):
        for seg in segmentos(paginas[n]):
            m = _DESTINA.search(seg)
            if not m or _EXCLUI.search(seg[m.start(): m.end() + 80]):
                continue
            trecho = seg if len(seg) <= TRECHO_MAX else seg[max(0, m.start() - 100): max(0, m.start() - 100) + TRECHO_MAX]
            achados.append(CandidatoVagas(n, trecho.strip(), int(m.group(1).replace(".", ""))))
    return achados


def principal(achados: list[CandidatoVagas]) -> CandidatoVagas | None:
    """Uma única quantidade no documento inteiro; se houver duas diferentes, nenhuma."""
    return achados[0] if achados and len({a.valor for a in achados}) == 1 else None
