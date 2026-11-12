"""Cronograma em tabela, lido célula por célula (padrão dos editais da Cebraspe).

O texto corrido de uma tabela separa as colunas e pode juntar o rótulo de uma linha com
a data de outra. Aqui a tabela é lida pela geometria do PDF (pdfplumber), só nas páginas
cujo texto traz um cabeçalho de cronograma, e cada linha vira (atividade, datas).

Uma linha só vira candidata a prazo se:
- a atividade tem a âncora do prazo e um verbo/rótulo de definição ("Período de solicitação...");
- a atividade não fala de outro evento (resultado, consulta, recurso, pagamento, foto...);
- as duas células aparecem, literalmente, no texto da página (é o que o G3 confere depois).
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

import pdfplumber

from ntc.model.schema import SEPARADOR_TABELA
from ntc.parse.clausulas import ANCORAS, EXCLUSOES, TABELA_CABECALHO, Candidato, TipoPrazo, datas_de_prazo
from ntc.parse.texto import normalizar

_DEFINE = re.compile(r"per[íi]odo|prazo\s+(?:para|de)\s+(?:solicita|inscri)|solicita[çc][ãa]o", re.IGNORECASE)
_OUTRO_EVENTO = re.compile(
    r"consulta|situa[çc][ãa]o|rela[çc][ãa]o|link|foto|envio\s+de\s+laudo|atendimento|local|aplica[çc][ãa]o",
    re.IGNORECASE,
)
_ATE_ULTIMA_DATA = re.compile(r"^.*\d{4}")


@dataclass(frozen=True)
class Linha:
    pagina: int
    atividade: str
    datas: str


def linhas(pdf: bytes, paginas_texto: dict[int, str]) -> list[Linha]:
    alvo = [n for n, t in paginas_texto.items() if TABELA_CABECALHO.search(normalizar(t))]
    if not alvo:
        return []
    saida: list[Linha] = []
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        for n in alvo:
            if n > len(doc.pages):
                continue
            pagina = doc.pages[n - 1]
            for tabela in pagina.extract_tables():
                for linha in tabela:
                    celulas = [normalizar(c) for c in linha if c and normalizar(c)]
                    if len(celulas) < 2:
                        continue
                    m = _ATE_ULTIMA_DATA.match(celulas[-1])
                    if not m:
                        continue
                    saida.append(Linha(n, celulas[0], m.group(0).strip()))
            pagina.flush_cache()
    return saida


def candidatos(linhas_: list[Linha], paginas_texto: dict[int, str], tipo: TipoPrazo) -> list[Candidato]:
    ancora = ANCORAS[tipo]
    achados = []
    for ln in linhas_:
        m = ancora.search(ln.atividade)
        if not m or not _DEFINE.search(ln.atividade):
            continue
        if EXCLUSOES[tipo].search(ln.atividade) or _OUTRO_EVENTO.search(ln.atividade):
            continue
        pagina = normalizar(paginas_texto.get(ln.pagina, ""))
        if ln.atividade not in pagina or ln.datas not in pagina:
            continue  # sem as células literais na página, o G3 não teria como conferir
        d = tuple(datas_de_prazo(ln.datas))
        if not d:
            continue
        trecho = f"{ln.atividade}{SEPARADOR_TABELA}{ln.datas}"
        achados.append(Candidato(tipo, ln.pagina, trecho, m.group(0), d, False, (ln.atividade, ln.datas)))
    return achados
