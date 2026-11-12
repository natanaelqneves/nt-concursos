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
