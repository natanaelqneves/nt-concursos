"""INLABS / Imprensa Nacional: descoberta federal pelo XML da seção 3 do DOU.

Acesso documentado pela Imprensa Nacional (github.com/Imprensa-Nacional/inlabs):
  POST https://inlabs.in.gov.br/logar.php  (email, password)  -> cookie inlabs_session_cookie
  GET  https://inlabs.in.gov.br/index.php?p=AAAA-MM-DD&dl=AAAA-MM-DD-DO3.zip  (header origem)
O ZIP traz um XML por matéria: <article artType=... artCategory=... pubDate=... numberPage=...
pdfPage=...><body><Identifica/><Texto/></body></article>.

O INLABS só descobre: devolve editais de abertura de concurso de órgãos federais no
escopo. Os documentos que sustentam as datas vêm da banca (ou do próprio órgão).
As credenciais vêm de INLABS_EMAIL e INLABS_SENHA (secrets do Actions).
"""

from __future__ import annotations

import io
import re
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime

from lxml import etree, html

from ntc.escopo import classificar
from ntc.fetch.http import Cliente, ErroColeta
from ntc.sources.base import ConcursoFonte, Fonte

LOGIN = "https://inlabs.in.gov.br/logar.php"
DOWNLOAD = "https://inlabs.in.gov.br/index.php?p={d}&dl={d}-{secao}.zip"
ORIGEM = "736372697074"  # cabeçalho exigido pelo INLABS nos downloads automatizados
SECOES = ("DO3", "DO3E")

_RE_CONCURSO = re.compile(r"concurso\s+p[úu]blico", re.IGNORECASE)
_RE_ABERTURA = re.compile(
    r"abertura|torna\s+p[úu]blica\s+a\s+realiza[çc][ãa]o|abertas\s+as\s+inscri[çc][õo]es|"
    r"realiza[çc][ãa]o\s+de\s+concurso",
    re.IGNORECASE,
)
_RE_FORA = re.compile(r"homologa|resultado|convoca|prorroga[çc][ãa]o\s+da\s+validade|retifica", re.IGNORECASE)


@dataclass(frozen=True)
class Materia:
    id: str
    secao: str
    tipo: str
    categoria: str
    data: date | None
    pagina: str
    url_pdf: str
    identifica: str
    texto: str


class SemCredenciais(ErroColeta):
    pass


class Indisponivel(ErroColeta):
    """O arquivo do dia ainda não existe (404) ou o INLABS está em manutenção."""


def _texto_html(fragmento: str) -> str:
    if not fragmento.strip():
        return ""
    return html.fromstring(f"<div>{fragmento}</div>").text_content()


def parse_xml(conteudo: bytes) -> Materia | None:
    raiz = etree.fromstring(conteudo, etree.XMLParser(recover=True, huge_tree=True))
    if raiz is None:
        return None
    art = raiz if raiz.tag == "article" else raiz.find(".//article")
    if art is None:
        return None
    corpo = art.find("body")

    def campo(nome: str) -> str:
        el = corpo.find(nome) if corpo is not None else None
        return (el.text or "") if el is not None else ""

    bruto = art.get("pubDate", "")
    try:
        data = datetime.strptime(bruto, "%d/%m/%Y").date()
    except ValueError:
        data = None
    return Materia(
        id=art.get("idMateria") or art.get("id", ""),
        secao=art.get("pubName", ""),
        tipo=art.get("artType", ""),
        categoria=art.get("artCategory", ""),
        data=data,
        pagina=art.get("numberPage", ""),
        url_pdf=art.get("pdfPage", ""),
        identifica=_texto_html(campo("Identifica")).strip(),
        texto=_texto_html(campo("Texto")),
    )


def materias_do_zip(conteudo: bytes) -> Iterator[Materia]:
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        for nome in sorted(z.namelist()):
            if nome.lower().endswith(".xml"):
                m = parse_xml(z.read(nome))
                if m is not None:
                    yield m


def eh_abertura_de_concurso(m: Materia) -> bool:
    if "edital" not in m.tipo.lower():
        return False
    inicio = f"{m.identifica} {m.texto[:1500]}"
    return bool(_RE_CONCURSO.search(inicio) and _RE_ABERTURA.search(inicio) and not _RE_FORA.search(m.identifica))


def candidato(m: Materia) -> ConcursoFonte:
    url = m.url_pdf.replace("http://", "https://", 1) if m.url_pdf else "https://www.in.gov.br/servicos/diario-oficial-da-uniao"
    return ConcursoFonte(
        fonte="inlabs", id=m.id, titulo=m.identifica or m.tipo, url=url,
        contexto=[m.categoria.replace("/", " / "), m.texto[:600]], ano=m.data.year if m.data else None,
        data_dou=m.data,
    )


class Inlabs(Fonte):
    nome = "inlabs"

    def __init__(self, email: str | None, senha: str | None, data_dou: date):
        self.email, self.senha, self.data_dou = email, senha, data_dou

    def login(self, cliente: Cliente) -> None:
        if not (self.email and self.senha):
            raise SemCredenciais("defina INLABS_EMAIL e INLABS_SENHA")
        r = cliente.post(LOGIN, data={"email": self.email, "password": self.senha},
                         headers={"Content-Type": "application/x-www-form-urlencoded"})
        if "manuten" in r.texto().lower():
            raise Indisponivel("INLABS em manutenção")
        if not cliente.sessao.cookies.get("inlabs_session_cookie"):
            raise ErroColeta("login no INLABS sem cookie de sessão: confira as credenciais")

    def baixar(self, cliente: Cliente, secao: str) -> bytes:
        url = DOWNLOAD.format(d=self.data_dou.isoformat(), secao=secao)
        try:
            r = cliente.get(url, headers={"origem": ORIGEM}, usar_cache=False)
        except ErroColeta as e:
            if "HTTP 404" in str(e):
                raise Indisponivel(f"{secao} de {self.data_dou} ainda não publicado") from e
            raise
        if not r.conteudo.startswith(b"PK"):
            raise Indisponivel(f"{secao} de {self.data_dou}: resposta não é ZIP")
        return r.conteudo

    def descobrir(self, cliente: Cliente) -> Iterator[ConcursoFonte]:
        self.login(cliente)
        for secao in SECOES:
            try:
                conteudo = self.baixar(cliente, secao)
            except Indisponivel:
                if secao == "DO3":
                    raise
                continue  # edição extra só existe em alguns dias
            for m in materias_do_zip(conteudo):
                if eh_abertura_de_concurso(m):
                    yield candidato(m)


def no_escopo(c: ConcursoFonte):
    return classificar(c.titulo, *c.contexto)
