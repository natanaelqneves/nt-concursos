"""Cebraspe (www.cebraspe.org.br/concursos).

O site é uma aplicação React que consome uma API JSON pública, a mesma usada pela página:
  lista:   https://apis.cebraspe.org.br/cebraspe/eventos/tipo/concursos/   (grupos por fase)
  detalhe: https://apis.cebraspe.org.br/cebraspe/eventos/<eventoURL>
  arquivo: https://cdn.cebraspe.org.br/concursos/<eventoURL>/arquivos/<nomeArquivo>
           (ou https://cdn.cebraspe.org.br/<nomeArquivo> quando isGuid)

O edital vigente é o "Edital nº 1 - Abertura", preferindo a versão "Atualizado conforme
retificações". Retificações, reaberturas, prorrogações e comunicados entram como mudança (G7).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import datetime

from ntc.fetch.http import Cliente, ErroColeta
from ntc.sources.base import RE_MUDANCA, ConcursoFonte, DocFonte, Fonte, ano_de

API = "https://apis.cebraspe.org.br/cebraspe/eventos"
CDN = "https://cdn.cebraspe.org.br/"
PAGINA = "https://www.cebraspe.org.br/concursos/"

_RE_ABERTURA = re.compile(r"edital\s+n[º°o.]*\s*0*1\b.*abertura", re.IGNORECASE)
_RE_ATUALIZADO = re.compile(r"atualizado", re.IGNORECASE)


def _url_arquivo(evento: str, arq: dict) -> str:
    if arq.get("isGuid"):
        return f"{CDN}{arq['nomeArquivo']}"
    return f"{CDN}concursos/{evento}/arquivos/{arq['nomeArquivo']}"


def _data(arq: dict):
    bruto = arq.get("dataArquivoObj") or ""
    try:
        return datetime.fromisoformat(bruto).date()
    except ValueError:
        return None


def parse_lista(dados: list[dict]) -> list[dict]:
    """Eventos fora da fase "Encerrados"."""
    return [e for grupo in dados if grupo.get("faseEvento") != "Encerrados" for e in grupo.get("eventos") or []]


def parse_evento(det: dict) -> ConcursoFonte:
    evento = det["eventoURL"]
    abreviado = det.get("eventoNomeAbreviado") or evento
    contexto = [det.get("eventoNomeCompleto") or ""] + [c.get("area", "") for c in det.get("eventoCargos") or []]
    pdfs = [a for a in det.get("arquivosEdital") or [] if a.get("tipoExtensaoArquivo") == "_.pdf"]

    aberturas = [a for a in pdfs if _RE_ABERTURA.search(a.get("descricaoArquivo", ""))]
    aberturas.sort(key=lambda a: (bool(_RE_ATUALIZADO.search(a["descricaoArquivo"])), a.get("dataArquivoObj", "")),
                   reverse=True)
    documentos: list[DocFonte] = []
    if aberturas:
        a = aberturas[0]
        documentos.append(DocFonte(_url_arquivo(evento, a), "edital", a["descricaoArquivo"], _data(a)))
    escolhidos = {id(a) for a in aberturas}
    mudancas = [
        DocFonte(_url_arquivo(evento, a), "retificacao", a["descricaoArquivo"], _data(a))
        for a in pdfs
        if id(a) not in escolhidos and RE_MUDANCA.search(a.get("descricaoArquivo", ""))
    ]
    documentos += sorted(mudancas, key=lambda d: d.publicado_em or datetime.min.date())
    ano = det.get("eventoAno") or ano_de(abreviado, evento)
    return ConcursoFonte("cebraspe", evento, abreviado, f"{PAGINA}{evento}", contexto, documentos, ano)


class Cebraspe(Fonte):
    nome = "cebraspe"

    def __init__(self, so: set[str] | None = None):
        self.so = so

    def descobrir(self, cliente: Cliente) -> Iterator[ConcursoFonte]:
        lista = cliente.get(f"{API}/tipo/concursos/", usar_cache=False).json()
        for e in parse_lista(lista):
            evento = e.get("eventoURL")
            if not evento or (self.so and evento not in self.so):
                continue
            try:
                det = cliente.get(f"{API}/{evento}", usar_cache=False).json()
            except (ErroColeta, ValueError) as erro:
                yield ConcursoFonte("cebraspe", evento, e.get("eventoNomeAbreviado") or evento,
                                    f"{PAGINA}{evento}", [f"erro ao abrir detalhe: {erro}"])
                continue
            yield parse_evento(det)
