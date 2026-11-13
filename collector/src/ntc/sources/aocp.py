"""Instituto AOCP (www.institutoaocp.org.br).

O site (Next.js) consome APIs JSON públicas, as mesmas usadas pela página:
  lista:    https://www.institutoaocp.org.br/api/concursos?status=SUBSCRIBE|NEW|IN_PROGRESS
  detalhe:  https://link.institutoaocp.org.br/api/concursos/<id>         (concursos "legado")
            https://www.institutoaocp.org.br/api/concursos/proseleta/<n> (plataforma nova, id "proseleta-<n>")
  página:   https://www.institutoaocp.org.br/concursos/<id>

Cada detalhe traz "publicacoes" (nome "DD/MM/AAAA - título" e URL do PDF). O edital é o
"Edital de Abertura" (preferindo a versão "retificado"); termos de retificação, comunicados,
prorrogações e afins entram como mudança (G7).

Os PDFs dos concursos "legado" ficam em arquivos-site.institutoaocp.org.br, cujo robots.txt
proíbe tudo (12/11/2026): o cliente recusa o download e o concurso fica "sem edital". Os da
plataforma nova ficam em anexos-r2.selecao.net.br, sem restrição.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import date, datetime, timedelta

from ntc.fetch.http import Cliente, ErroColeta
from ntc.sources.base import RE_MUDANCA, ConcursoFonte, DocFonte, Fonte, ano_de

SITE = "https://www.institutoaocp.org.br"
API_LEGADO = "https://link.institutoaocp.org.br/api/concursos"
# NEW: inscrição ainda não aberta; IN_PROGRESS: inscrição encerrada, mas o concurso pode já estar
# publicado e precisar de atualização (retificação). Os em andamento muito antigos são ignorados.
STATUS = ("SUBSCRIBE", "NEW", "IN_PROGRESS")
JANELA_ANDAMENTO = timedelta(days=60)

_RE_ABERTURA = re.compile(r"edital\s+(?:normativo\s+)?de\s+abertura", re.IGNORECASE)
_RE_NAO_EDITAL = re.compile(r"termo\s+de\s+retifica|anexo|errata|extrato|resultado", re.IGNORECASE)
_RE_RETIFICADO = re.compile(r"retificad[oa]", re.IGNORECASE)
_RE_DATA_NOME = re.compile(r"^\s*(\d{2})/(\d{2})/(\d{4})\s*[-–]\s*")
_INATIVOS = {"suspenso", "cancelado", "suspended", "canceled", "cancelled"}


def _data_br(bruto: str | None) -> date | None:
    """'18/11/2026 23:59:59' ou '2026-11-23 14:00:00'."""
    if not bruto:
        return None
    for fmt in ("%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(bruto.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _separar_nome(nome: str) -> tuple[date | None, str]:
    m = _RE_DATA_NOME.match(nome)
    if not m:
        return None, nome.strip()
    try:
        d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        d = None
    return d, nome[m.end():].strip()


def parse_lista(itens: list[dict], status: str, hoje: date) -> list[dict]:
    saida = []
    for c in itens:
        if status == "IN_PROGRESS":
            fim = _data_br(c.get("dataInscricao"))
            if fim is None or fim < hoje - JANELA_ANDAMENTO:
                continue
        saida.append(c)
    return saida


def url_detalhe(id_: str) -> str:
    if id_.startswith("proseleta-"):
        return f"{SITE}/api/concursos/proseleta/{id_[len('proseleta-'):]}"
    return f"{API_LEGADO}/{id_}"


def parse_detalhe(id_: str, item: dict, det: dict) -> ConcursoFonte | None:
    """None para concurso suspenso ou cancelado."""
    if str(det.get("status") or item.get("status") or "").lower() in _INATIVOS:
        return None
    nome = (det.get("nome") or item.get("nome") or id_).strip()
    tipo = det.get("tipoProcesso") or item.get("tipoProcesso") or ""
    contexto = [nome, (det.get("chamada") or item.get("chamada") or "")[:600], tipo]

    pubs = []
    for p in det.get("publicacoes") or []:
        url = p.get("url") or ""
        if not url.lower().endswith(".pdf"):
            continue
        quando, titulo = _separar_nome(p.get("nome") or "")
        pubs.append((quando, titulo, url))

    aberturas = [p for p in pubs if _RE_ABERTURA.search(p[1]) and not _RE_NAO_EDITAL.search(p[1])]
    aberturas.sort(key=lambda p: (bool(_RE_RETIFICADO.search(p[1])), p[0] or date.min), reverse=True)
    documentos: list[DocFonte] = []
    if aberturas:
        q, t, u = aberturas[0]
        documentos.append(DocFonte(u, "edital", t, q))
    usados = {aberturas[0][2]} if aberturas else set()
    mudancas = [DocFonte(u, "retificacao", t, q) for q, t, u in pubs if u not in usados and RE_MUDANCA.search(t)]
    documentos += sorted(mudancas, key=lambda d: d.publicado_em or date.min)

    ano = ano_de(item.get("numeroEdital"), det.get("edital") or item.get("edital"), item.get("dataInicioInscricao"))
    return ConcursoFonte("aocp", id_, nome, f"{SITE}/concursos/{id_}", contexto, documentos, ano)


class Aocp(Fonte):
    nome = "aocp"

    def __init__(self, so: set[str] | None = None, hoje: date | None = None):
        self.so = so
        self.hoje = hoje

    def descobrir(self, cliente: Cliente) -> Iterator[ConcursoFonte]:
        hoje = self.hoje or date.today()
        vistos: set[str] = set()
        for status in STATUS:
            itens = cliente.get(f"{SITE}/api/concursos?status={status}", usar_cache=False).json()
            for item in parse_lista(itens or [], status, hoje):
                id_ = str(item.get("id"))
                if id_ in vistos or (self.so and id_ not in self.so):
                    continue
                vistos.add(id_)
                try:
                    det = cliente.get(url_detalhe(id_), usar_cache=False).json()
                except (ErroColeta, ValueError) as erro:
                    yield ConcursoFonte("aocp", id_, item.get("nome") or id_, f"{SITE}/concursos/{id_}",
                                        [f"erro ao abrir detalhe: {erro}"])
                    continue
                if isinstance(det, list):
                    det = det[0] if det else {}
                cf = parse_detalhe(id_, item, det)
                if cf is not None:
                    yield cf
