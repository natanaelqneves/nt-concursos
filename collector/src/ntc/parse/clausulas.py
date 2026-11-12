"""Localização de cláusulas de prazo (isenção, inscrição) no texto do edital.

Uma cláusula é um segmento curto de texto que contém a âncora do tipo de prazo
e ao menos uma data. Segmentos que falam de resultado, recurso etc. não são
candidatos: "resultado da isenção: 20/11/2026" não é o prazo de isenção.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from ntc.model.schema import TRECHO_MAX
from ntc.parse.datas import datas
from ntc.parse.texto import normalizar

TipoPrazo = str  # "isencao" | "inscricao"

ANCORAS: dict[TipoPrazo, re.Pattern[str]] = {
    "isencao": re.compile(r"isen[çc][ãa]o|isent[oa]s?\b", re.IGNORECASE),
    "inscricao": re.compile(r"inscri[çc](?:[ãa]o|[õo]es)", re.IGNORECASE),
}

# Termos que, no mesmo segmento, indicam outro evento do cronograma.
EXCLUSOES: dict[TipoPrazo, re.Pattern[str]] = {
    "isencao": re.compile(
        r"resultado|recurso|divulga|deferid|indeferid|homologa|publica[çc][ãa]o",
        re.IGNORECASE,
    ),
    "inscricao": re.compile(
        r"isen[çc][ãa]o|isent|resultado|recurso|divulga|homologa|deferid|indeferid|"
        r"confirma|cart[ãa]o|local de prova|pagamento|boleto|reimpress",
        re.IGNORECASE,
    ),
}

CAMPO_POR_TIPO = {"isencao": "prazos.isencao", "inscricao": "prazos.inscricao"}

# Quebra em fim de frase, ou logo após uma data quando a próxima linha de
# cronograma começa com maiúscula ("... 14/11/2026 Resultado da isenção ...").
_FRONTEIRA = re.compile(
    r"(?<=[.;])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9])"
    r"|(?<=\d{4})\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])"
    r"|(?<=\d{4}\.)\s+"
)


@dataclass(frozen=True)
class Candidato:
    tipo: TipoPrazo
    pagina: int
    trecho: str
    ancora: str
    datas: tuple[date, ...] = field(default_factory=tuple)

    @property
    def inicio(self) -> date | None:
        return self.datas[0] if len(self.datas) == 2 else None

    @property
    def fim(self) -> date | None:
        return self.datas[-1] if len(self.datas) in (1, 2) else None

    @property
    def ambiguo(self) -> bool:
        return len(self.datas) > 2


def segmentos(texto_pagina: str) -> list[str]:
    return [s.strip() for s in _FRONTEIRA.split(normalizar(texto_pagina)) if s.strip()]


def _recortar(segmento: str, ancora: re.Match[str]) -> str:
    if len(segmento) <= TRECHO_MAX:
        return segmento
    inicio = max(0, ancora.start() - 150)
    return segmento[inicio : inicio + TRECHO_MAX].strip()


def encontrar(paginas: dict[int, str], tipo: TipoPrazo) -> list[Candidato]:
    """Candidatos em todas as páginas, na ordem do documento."""
    ancora_re, exclusao_re = ANCORAS[tipo], EXCLUSOES[tipo]
    candidatos: list[Candidato] = []
    for pagina in sorted(paginas):
        for seg in segmentos(paginas[pagina]):
            m = ancora_re.search(seg)
            if not m or exclusao_re.search(seg):
                continue
            trecho = _recortar(seg, m)
            encontradas = tuple(datas(trecho))
            if not encontradas or not ancora_re.search(trecho):
                continue
            candidatos.append(Candidato(tipo, pagina, trecho, m.group(0), encontradas))
    return candidatos


def intervalos_distintos(candidatos: list[Candidato]) -> set[tuple[date | None, date | None]]:
    return {(c.inicio, c.fim) for c in candidatos if not c.ambiguo}
