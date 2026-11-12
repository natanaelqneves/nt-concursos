"""Extração de datas em português de editais.

Reconhece datas numéricas (12/11/2026, 12.11.2026), por extenso
("12 de novembro de 2026") e intervalos com mês/ano compartilhados
("de 10 a 14 de novembro de 2026", "10 a 14/11/2026", "10/11 a 14/11/2026").
Datas sem ano só são aceitas quando o ano vem no outro extremo do intervalo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

MESES = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5,
    "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12,
}
_MES = "|".join(sorted(MESES, key=len, reverse=True))
_DIA = r"(\d{1,2})(?:º|°|o)?"
_SEP_INTERVALO = r"\s*(a|até|ate|e|-|–|—)\s*"

_INTERVALO_EXTENSO = re.compile(
    rf"\b{_DIA}(?:\s+de\s+({_MES}))?(?:\s+de\s+(\d{{4}}))?{_SEP_INTERVALO}"
    rf"{_DIA}\s+de\s+({_MES})(?:\s+de\s+(\d{{4}}))?\b",
    re.IGNORECASE,
)
_INTERVALO_NUMERICO = re.compile(
    rf"\b(\d{{1,2}})(?:[/.](\d{{1,2}}))?(?:[/.](\d{{4}}))?{_SEP_INTERVALO}"
    r"(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b"
)
_DATA_NUMERICA = re.compile(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b")
_DATA_EXTENSO = re.compile(rf"\b{_DIA}\s+de\s+({_MES})\s+de\s+(\d{{4}})\b", re.IGNORECASE)


@dataclass(frozen=True)
class DataEncontrada:
    data: date
    posicao: int


def _mes(nome: str) -> int:
    return MESES[nome.lower()]


def _criar(ano: int, mes: int, dia: int) -> date | None:
    try:
        return date(ano, mes, dia)
    except ValueError:
        return None


def _separador_aceito(texto: str, inicio: int, sep: str, dia_solto: bool) -> bool:
    """Evita ler "item 4 - 10/11/2026" ou "dias 10 e 14" como intervalo."""
    sep = sep.lower()
    if sep == "e":
        return texto[:inicio].rstrip().lower().endswith("entre")
    if dia_solto and sep in "-–—":
        return False
    return True


def _mascarar(texto: str, inicio: int, fim: int) -> str:
    return texto[:inicio] + " " * (fim - inicio) + texto[fim:]


def extrair_datas(texto: str) -> list[DataEncontrada]:
    """Datas na ordem em que aparecem. Datas inválidas (31/02) são descartadas."""
    achados: list[DataEncontrada] = []
    trabalho = texto

    for m in _INTERVALO_EXTENSO.finditer(trabalho):
        d1, mes1, ano1, sep, d2, mes2, ano2 = m.groups()
        if not _separador_aceito(trabalho, m.start(), sep, dia_solto=mes1 is None):
            continue
        ano_fim = ano2 or ano1
        if ano_fim is None:
            continue
        m2 = _mes(mes2)
        m1 = _mes(mes1) if mes1 else m2
        a1 = int(ano1) if ano1 else int(ano_fim)
        if not mes1 and not ano1 and int(d1) > int(d2):
            continue  # "30 a 5 de dezembro" sem mês inicial explícito é ambíguo
        if not ano1 and m1 > m2:
            a1 -= 1  # "15 de dezembro a 10 de janeiro de 2027"
        inicio = _criar(a1, m1, int(d1))
        fim = _criar(int(ano_fim), m2, int(d2))
        if inicio and fim and inicio <= fim:
            achados.append(DataEncontrada(inicio, m.start(1)))
            achados.append(DataEncontrada(fim, m.start(5)))
            trabalho = _mascarar(trabalho, m.start(), m.end())

    for m in _INTERVALO_NUMERICO.finditer(trabalho):
        d1, mes1, ano1, sep, d2, mes2, ano2 = m.groups()
        if mes1 is None and ano1 is not None:
            continue
        if not _separador_aceito(trabalho, m.start(), sep, dia_solto=mes1 is None):
            continue
        m1 = int(mes1) if mes1 else int(mes2)
        a1 = int(ano1) if ano1 else int(ano2)
        if not ano1 and m1 > int(mes2):
            a1 -= 1
        inicio = _criar(a1, m1, int(d1))
        fim = _criar(int(ano2), int(mes2), int(d2))
        if inicio and fim and inicio <= fim:
            achados.append(DataEncontrada(inicio, m.start(1)))
            achados.append(DataEncontrada(fim, m.start(5)))
            trabalho = _mascarar(trabalho, m.start(), m.end())

    for m in _DATA_NUMERICA.finditer(trabalho):
        d = _criar(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        if d:
            achados.append(DataEncontrada(d, m.start()))

    for m in _DATA_EXTENSO.finditer(trabalho):
        d = _criar(int(m.group(3)), _mes(m.group(2)), int(m.group(1)))
        if d:
            achados.append(DataEncontrada(d, m.start()))

    achados.sort(key=lambda a: a.posicao)
    return achados


def datas(texto: str) -> list[date]:
    return [a.data for a in extrair_datas(texto)]
