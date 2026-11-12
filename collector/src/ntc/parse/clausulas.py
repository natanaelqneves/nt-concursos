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


_DATA_EXTENSO = r"\d{1,2}(?:º|°)?\s+de\s+[a-zç]+\s+de\s+\d{4}|\d{1,2}/\d{1,2}/\d{4}"
# Datas de normas citadas ("Lei nº 10.567, de 07 de novembro de 1997") não são prazos.
_CITACAO = re.compile(
    rf"(?:\b(?:lei|decreto(?:-lei)?|portaria|resolu[çc][ãa]o|instru[çc][ãa]o\s+normativa|"
    rf"medida\s+provis[óo]ria|emenda\s+constitucional|edital)\b(?:(?!inscri|isen|per[íi]odo|prazo)[^.;:]){{0,40}}?"
    rf"|\b\d{{1,3}}(?:\.\d{{3}})+(?:/\d{{2,4}})?,?\s+)"
    rf"de\s+(?:{_DATA_EXTENSO})",
    re.IGNORECASE,
)


def datas_de_prazo(texto: str) -> list[date]:
    """Datas do texto, ignorando as que datam normas citadas."""
    return datas(_CITACAO.sub(lambda m: " " * len(m.group(0)), texto))


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
            encontradas = tuple(datas_de_prazo(trecho))
            if not encontradas or not ancora_re.search(trecho):
                continue
            candidatos.append(Candidato(tipo, pagina, trecho, m.group(0), encontradas))
    return candidatos


_DEFINE_PRAZO = re.compile(
    r"estar[ãa]o\s+abertas|ser[ãa]o\s+(?:realizadas|recebidas|efetuadas)|poder[áa]\s+ser\s+(?:solicitad|requerid|feit)|"
    r"dever[áa]\s+ser\s+(?:solicitad|requerid|feit)|per[íi]odo\s+(?:de|das|entre)\s+(?:\d|inscri|solicita)",
    re.IGNORECASE,
)


def intervalos_distintos(candidatos: list[Candidato]) -> set[tuple[date | None, date | None]]:
    """Intervalos diferentes entre si. "até 18/11" é compatível com "20/10 a 18/11"
    (mesmo fim, início omitido) e não conta como cláusula conflitante."""
    brutos = {(c.inicio, c.fim) for c in candidatos if not c.ambiguo}
    completos = {i for i in brutos if i[0] is not None}
    return completos | {i for i in brutos if i[0] is None and not any(c[1] == i[1] for c in completos)}


def principal(candidatos: list[Candidato]) -> Candidato | None:
    """A cláusula que sustenta o campo: só existe se não houver conflito (G5).
    Prefere a que traz início e fim; entre essas, a primeira do documento."""
    if len(intervalos_distintos(candidatos)) != 1:
        return None
    validos = [c for c in candidatos if not c.ambiguo]

    def nota(c: Candidato) -> tuple[int, int, int]:
        # 1) traz início e fim; 2) é a cláusula que define o prazo; 3) a âncora vem no começo
        posicao = ANCORAS[c.tipo].search(c.trecho).start()
        return (c.inicio is not None, bool(_DEFINE_PRAZO.search(c.trecho)), posicao < 120)

    melhor = max(nota(c) for c in validos)
    return next(c for c in validos if nota(c) == melhor)


_MUDANCA_PRAZO = re.compile(
    r"prorroga|reabert|reabr|adiad|adiament|suspens|nova\s+data|novo\s+per[íi]odo|novo\s+prazo",
    re.IGNORECASE,
)
_ONDE_SE_LE = re.compile(r"onde\s+se\s+l[êe]", re.IGNORECASE)


def altera_prazo(paginas: dict[int, str], tipo: TipoPrazo, inicio: date | None, fim: date | None) -> bool:
    """Um documento posterior (retificação, comunicado) muda o prazo declarado?

    Sim se: alguma cláusula do prazo traz datas diferentes ou é ambígua; algum trecho
    fala do prazo junto de prorrogação/reabertura/suspensão; ou é errata "onde se lê"
    que menciona o prazo. Mencionar o prazo sem data (ex.: "taxa de inscrição") não muda nada.
    """
    ancora = ANCORAS[tipo]
    if not any(ancora.search(p) for p in paginas.values()):
        return False
    if any(_ONDE_SE_LE.search(p) for p in paginas.values()):
        return True
    for pagina in paginas.values():
        for seg in segmentos(pagina):
            if ancora.search(seg) and _MUDANCA_PRAZO.search(seg):
                return True
    for cand in encontrar(paginas, tipo):
        if cand.ambiguo or cand.fim != fim or (cand.inicio is not None and cand.inicio != inicio):
            return True
    return False
