"""Etapas do concurso depois das inscrições, lidas no cronograma do edital (Parte 1 de "Em andamento").

Só linhas de cronograma em tabela entram (o mesmo leitor dos prazos, em parse/tabela.py): cada
linha vira (atividade, datas) e o G3 confere as duas células literalmente na página.

Cuidados, porque o texto de tabela pode desalinhar a data de uma linha com o rótulo de outra:
- a atividade precisa ter a âncora de um tipo de etapa e não pode falar de recurso, pedido,
  consulta, pagamento, local de prova etc.;
- numa página sem grade (texto do pdftotext), as etapas só valem se a mesma página traz a linha de
  inscrições com as datas já verificadas: é a prova de que a tabela daquela página está alinhada;
- o ano tem de estar perto do ano da coleta e a etapa não pode vir antes do início das inscrições.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from ntc.parse.clausulas import ANCORAS, EXCLUSOES, datas_de_prazo
from ntc.parse.tabela import Linha
from ntc.parse.texto import normalizar

# Ordem importa: o primeiro tipo que casar decide (do mais específico ao mais geral).
_TIPOS: list[tuple[str, re.Pattern[str]]] = [
    ("homologacao", re.compile(r"homologa[çc][ãa]o\s+(?:do\s+)?(?:resultado|concurso)", re.I)),
    # "resultado final na avaliação psicológica" é resultado de uma etapa, não do concurso
    ("resultado_final", re.compile(
        r"resultado\s+final(?![^.;]{0,30}?\b(?:avalia|procedimento|prova|per[íi]cia|heteroid|teste|exame|etapa|fase))",
        re.I)),
    ("resultado", re.compile(r"resultado", re.I)),
    ("gabarito", re.compile(r"gabarito", re.I)),
    ("curso_formacao", re.compile(r"curso\s+de\s+forma[çc][ãa]o", re.I)),
    ("heteroidentificacao", re.compile(r"heteroidentifica", re.I)),
    ("investigacao_social", re.compile(r"investiga[çc][ãa]o\s+social|sindic[âa]ncia\s+de\s+vida", re.I)),
    ("avaliacao_psicologica", re.compile(r"avalia[çc][ãa]o\s+psicol[óo]gica|exame\s+psicot[ée]cnico", re.I)),
    ("avaliacao_medica", re.compile(r"(?:avalia[çc][ãa]o|exame|inspe[çc][ãa]o)\s+(?:m[ée]dic|de\s+sa[úu]de)", re.I)),
    ("taf", re.compile(r"aptid[ãa]o\s+f[íi]sica|\bTAF\b|teste\s+f[íi]sico|capacidade\s+f[íi]sica", re.I)),
    ("titulos", re.compile(r"(?:avalia[çc][ãa]o|prova)\s+de\s+t[íi]tulos", re.I)),
    ("prova_pratica", re.compile(r"prova\s+pr[áa]tica", re.I)),
    ("prova_objetiva", re.compile(r"provas?\s+objetivas?", re.I)),
    ("prova_discursiva", re.compile(r"prova\s+discursiva|reda[çc][ãa]o", re.I)),
]

# Linhas que citam uma etapa mas descrevem outro evento: recurso, pedidos, consultas, envio de
# documentos, locais, convocações, pagamentos.
_OUTRO_EVENTO = re.compile(
    r"recurs|interposi|pedido|solicita|requeriment|consulta|link|envio|entrega|laudo|"
    r"atendimento|loca(?:l|is)|convoca|pagamento|boleto|isen[çc]|inscri|"
    r"padr[ãa]o\s+(?:\w+\s+)?de\s+respostas?|espelho|vista\s+d",
    re.I,
)
# "resultado preliminar/provisório" e "resultado da isenção" não são etapas do concurso.
_RESULTADO_PARCIAL = re.compile(r"preliminar|provis[óo]ri|parcial", re.I)

_AFIRMA_INSCRICAO = re.compile(r"per[íi]odo|prazo|realiza[çc][ãa]o", re.I)


@dataclass(frozen=True)
class EtapaAchada:
    tipo: str
    nome: str
    inicio: date | None
    fim: date
    pagina: int
    atividade: str
    datas: str


def classificar(atividade: str) -> str | None:
    """Tipo de etapa da atividade de uma linha de cronograma, ou None se não for etapa."""
    if _OUTRO_EVENTO.search(atividade):
        return None
    for tipo, rx in _TIPOS:
        if rx.search(atividade):
            if tipo in ("resultado", "resultado_final") and _RESULTADO_PARCIAL.search(atividade):
                return None
            return tipo
    return None


def _linha_de_inscricao(ln: Linha) -> bool:
    a = ln.atividade
    return bool(ANCORAS["inscricao"].search(a) and _AFIRMA_INSCRICAO.search(a)
                and not EXCLUSOES["inscricao"].search(a))


def encontrar(
    linhas: list[Linha], paginas_texto: dict[int, str], inscricao: tuple[date | None, date] | None, ano: int,
) -> list[EtapaAchada]:
    """Etapas do cronograma, em ordem de data. `inscricao` = (início, fim) verificados, se houver."""
    alinhadas: set[int] = set()
    if inscricao is not None:
        esperado = [d for d in inscricao if d is not None]
        for ln in linhas:
            if _linha_de_inscricao(ln) and datas_de_prazo(ln.datas) == esperado:
                alinhadas.add(ln.pagina)
    vistos: set[tuple[str, str]] = set()
    saida: list[EtapaAchada] = []
    for ln in linhas:
        if not ln.grade and ln.pagina not in alinhadas:
            continue
        tipo = classificar(ln.atividade)
        if tipo is None:
            continue
        pagina = normalizar(paginas_texto.get(ln.pagina, ""))
        if ln.atividade not in pagina or ln.datas not in pagina:
            continue
        ds = datas_de_prazo(ln.datas)
        if not 1 <= len(ds) <= 2 or (len(ds) == 2 and ds[0] > ds[1]):
            continue
        if any(not (ano - 1 <= d.year <= ano + 1) for d in ds):
            continue
        if inscricao is not None and inscricao[0] is not None and ds[-1] < inscricao[0]:
            continue
        nome = ln.atividade[:200].rstrip()
        if len(nome) < 3 or (tipo, nome) in vistos:
            continue
        vistos.add((tipo, nome))
        saida.append(EtapaAchada(tipo, nome, ds[0] if len(ds) == 2 else None, ds[-1],
                                 ln.pagina, ln.atividade, ln.datas))
    saida.sort(key=lambda e: e.fim)
    return saida


_MUDANCA = re.compile(r"onde\s+se\s+l[êe]|cronograma|adia|nova\s+data|altera", re.I)


def alterada_por(paginas: dict[int, str], tipo: str) -> bool:
    """Documento posterior que mexe nesta etapa (cita o tipo junto de alteração ou cronograma)."""
    rx = dict(_TIPOS)[tipo]
    texto = " ".join(normalizar(p) for p in paginas.values())
    return bool(rx.search(texto) and _MUDANCA.search(texto))
