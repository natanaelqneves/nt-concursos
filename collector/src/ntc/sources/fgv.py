"""FGV Conhecimento (conhecimento.fgv.br/concursos).

Lista: bloco "em andamento" (view concursos_em_andamento), paginado por ?page=N; o mesmo
parâmetro pagina também o bloco "realizados", que é ignorado.
Concurso: título no <h1>; "Arquivos do concurso" é uma lista de pares (data, rótulo + link).
O edital vigente é o item cujo rótulo começa com "Edital" (a FGV republica a versão
consolidada como "Edital (retificado em DD/MM/AAAA)"); retificações e comunicados entram
como documentos de mudança (G7).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ntc.escopo import classificar
from ntc.fetch.http import Cliente
from ntc.sources.base import RE_MUDANCA, ConcursoFonte, DocFonte, Fonte, ano_de

BASE = "https://conhecimento.fgv.br"
LISTA = f"{BASE}/concursos"
MAX_PAGINAS = 20

_RE_EDITAL = re.compile(r"^\s*edital\b(?!\s+de\s+convoca)", re.IGNORECASE)
# Rótulo do edital de abertura: "Edital", "Edital (retificado em ...)", "Edital de abertura",
# "Edital nº 1/2026". "Edital N. 36/2026 - Cumprimento de decisão" é edital avulso, não o de abertura.
_RE_ABERTURA = re.compile(
    r"^\s*edital\s*(?:$|\(|de\s+abertura|n[º°o.]*\s*0*1\s*/|.*abertura)", re.IGNORECASE
)
_RE_RETIFICADO_EM = re.compile(r"retificad[oa]\s+em\s+(\d{2}/\d{2}/\d{4})", re.IGNORECASE)


def _data(texto: str) -> date | None:
    m = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", texto)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%d/%m/%Y").date()
    except ValueError:
        return None


def parse_lista(html: str) -> list[tuple[str, str]]:
    """(título, url) do bloco "em andamento" de uma página da lista."""
    s = BeautifulSoup(html, "lxml")
    bloco = s.select_one(".view-id-concursos_em_andamento")
    if bloco is None:
        return []
    itens = []
    for a in bloco.select(".views-row a[href]"):
        href = a["href"]
        if href.startswith("/concursos/") and href.count("/") == 2:
            itens.append((a.get_text(" ", strip=True), urljoin(BASE, href)))
    return itens


def parse_concurso(html: str, url: str) -> ConcursoFonte:
    s = BeautifulSoup(html, "lxml")
    h1 = s.find("h1")
    titulo = h1.get_text(" ", strip=True) if h1 else ""
    corpo = s.select_one(".field--name-body")
    contexto = [corpo.get_text(" ", strip=True)[:1500]] if corpo else []
    id_fonte = url.rstrip("/").rsplit("/", 1)[-1]

    editais: list[DocFonte] = []
    mudancas: list[DocFonte] = []
    for item in s.select(".field--name-field-concurso-arquivos .paragraph--type--texto-data"):
        texto = item.get_text(" | ", strip=True)
        publicado = _data(texto)
        for a in item.find_all("a", href=True):
            href = urljoin(BASE, a["href"])
            if not href.lower().endswith(".pdf"):
                continue
            rotulo = a.get_text(" ", strip=True) or texto
            if _RE_EDITAL.search(rotulo):
                m = _RE_RETIFICADO_EM.search(rotulo)
                quando = _data(m.group(1)) if m else publicado
                editais.append(DocFonte(href, "edital", rotulo, quando))
            elif RE_MUDANCA.search(rotulo):
                mudancas.append(DocFonte(href, "retificacao", rotulo, publicado))

    # Edital vigente: entre os rótulos de abertura, o publicado (ou retificado) mais recentemente;
    # sem rótulo de abertura, o primeiro edital publicado. Os demais editais viram documentos de mudança.
    abertura = sorted((d for d in editais if _RE_ABERTURA.search(d.titulo)),
                      key=lambda d: d.publicado_em or date.min, reverse=True)
    if abertura:
        principal = abertura[0]
    elif editais:
        principal = min(editais, key=lambda d: d.publicado_em or date.max)
    else:
        principal = None
    avulsos = [DocFonte(d.url, "retificacao", d.titulo, d.publicado_em) for d in editais
               if principal and d is not principal and d not in abertura]
    documentos = ([principal] if principal else []) + sorted(mudancas + avulsos, key=lambda d: d.publicado_em or date.min)
    m = re.search(r"(\d{4}|\d{2})$", id_fonte)
    ano_id = (int(m.group(1)) if len(m.group(1)) == 4 else 2000 + int(m.group(1))) if m else None
    if ano_id is not None and not 2015 <= ano_id <= 2035:
        ano_id = None
    ano = ano_id or ano_de(titulo) or (principal.publicado_em.year if principal and principal.publicado_em else None)
    return ConcursoFonte("fgv", id_fonte, titulo, url, [id_fonte] + contexto, documentos, ano)


class FGV(Fonte):
    nome = "fgv"

    def __init__(self, so: set[str] | None = None):
        self.so = so

    def descobrir(self, cliente: Cliente) -> Iterator[ConcursoFonte]:
        vistos: set[str] = set()
        for pagina in range(MAX_PAGINAS):
            r = cliente.get(f"{LISTA}?page={pagina}" if pagina else LISTA, usar_cache=False)
            itens = [(t, u) for t, u in parse_lista(r.texto()) if u not in vistos]
            if not itens:
                break
            for titulo, url in itens:
                vistos.add(url)
                id_fonte = url.rsplit("/", 1)[-1]
                if self.so and id_fonte not in self.so:
                    continue
                # Filtro barato pelo título antes de abrir a página do concurso.
                if not self.so and classificar(titulo) is None:
                    yield ConcursoFonte("fgv", id_fonte, titulo, url)
                    continue
                det = cliente.get(url, usar_cache=False)
                yield parse_concurso(det.texto(), url)
