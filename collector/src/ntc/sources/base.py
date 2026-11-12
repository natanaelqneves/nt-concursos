"""Interface comum das fontes.

Uma fonte só *descobre*: lista concursos e os documentos oficiais de cada um, com o
texto que ela mesma publica (título, cargos). Baixar PDFs, extrair cláusulas e aplicar
o gate é trabalho do pipeline (ntc.coleta), igual para todas as fontes.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date

from ntc.fetch.http import Cliente

# Documentos que podem mudar datas já publicadas (G7)
RE_MUDANCA = re.compile(
    r"retifica|errata|prorroga|reabertura|reabre|suspens|adiament|altera[çc][ãa]o|cronograma|"
    r"comunicado|aviso",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DocFonte:
    url: str
    tipo: str  # "edital" | "retificacao"
    titulo: str
    publicado_em: date | None = None


@dataclass
class ConcursoFonte:
    fonte: str
    id: str
    titulo: str
    url: str  # página do concurso na banca (ou matéria no DOU)
    contexto: list[str] = field(default_factory=list)  # cargos, nome completo etc.
    documentos: list[DocFonte] = field(default_factory=list)
    ano: int | None = None
    data_dou: date | None = None
    cargos: list[str] = field(default_factory=list)  # nomes como a banca publica

    @property
    def edital(self) -> DocFonte | None:
        return next((d for d in self.documentos if d.tipo == "edital"), None)


class Fonte(ABC):
    nome: str

    @abstractmethod
    def descobrir(self, cliente: Cliente) -> Iterator[ConcursoFonte]:
        """Concursos ativos na fonte (sem filtro de escopo: o pipeline filtra e registra)."""


def ano_de(*textos: str | None) -> int | None:
    for t in textos:
        if not t:
            continue
        m = re.search(r"\b(20[2-4]\d)\b", t)
        if m:
            return int(m.group(1))
        m = re.search(r"(?:^|[ _])(2[4-9])(?:[ _]|$)", t)
        if m:
            return 2000 + int(m.group(1))
    return None


_MINUSCULAS = {"de", "da", "do", "das", "dos", "e", "em", "a", "o", "para", "com", "na", "no", "ao", "à"}


def nome_de_cargo(bruto: str) -> str:
    """'CARGO 2: SOLDADO – QUALIFICAÇÃO: QPBM/1' -> 'Soldado – Qualificação: QPBM/1'."""
    t = re.sub(r"^\s*cargo\s*(?:de\s+)?(?:\d+\s*)?[:–-]?\s*", "", bruto.strip(), flags=re.IGNORECASE)
    t = re.sub(r"\s*[–-]\s*c[óo]digo\s*:.*$", "", t, flags=re.IGNORECASE)  # código interno da banca
    t = re.sub(r"\s+", " ", t).strip(" .;")
    letras = [c for c in t if c.isalpha()]
    if letras and sum(c.isupper() for c in letras) / len(letras) > 0.8:
        palavras = []
        for i, p in enumerate(t.split(" ")):
            if re.fullmatch(r"\([A-Z]{2,8}\)", p) or (re.fullmatch(r"[A-Z0-9/().-]{2,8}", p) and any(ch.isdigit() for ch in p)) \
                    or p in {"TI", "QPBM", "QOBM", "QOPM"}:
                palavras.append(p)
            elif i > 0 and p.lower() in _MINUSCULAS:
                palavras.append(p.lower())
            else:
                palavras.append(p[:1].upper() + p[1:].lower())
        t = " ".join(palavras)
    return t
