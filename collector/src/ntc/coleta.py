"""Pipeline de coleta: fonte -> escopo -> documentos -> cláusulas -> gate -> data/.

Para cada concurso descoberto:
1. filtro de escopo (ntc.escopo); fora do escopo só vai para o log;
2. baixa o edital vigente e os documentos de mudança publicados a partir dele;
3. extrai prazos (isenção, inscrição) e vagas imediatas por cláusula;
4. aplica o gate com o texto completo (G1–G8, inclusive G5); o que falha vira `revisao`;
5. grava o concurso se houver ao menos um prazo verificado (ou se ele já estava publicado,
   para rebaixar campos que deixaram de passar), as páginas citadas e a fila de revisão.

Uma falha num concurso não interrompe os demais: vira registro de erro na execução.
"""

from __future__ import annotations

import re
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Callable

from ntc.escopo import Classificacao, classificar, sem_acento
from ntc.fetch.allowlist import Allowlist
from ntc.fetch.http import BRT, Cliente, ErroColeta
from ntc.gate.evidencia import Gate, TextoDocumento
from ntc.model.schema import (
    Campo,
    Cargo,
    Concurso,
    Descoberta,
    Documento,
    Evidencia,
    LinhaTabela,
    Prazo,
    Prazos,
    classificar_porte,
)
from ntc.parse import clausulas, tabela, vagas
from ntc.pdf.extract import NaoEhPdf, extrair
from ntc.sources.base import ConcursoFonte, DocFonte
from ntc.store.json_store import JsonStore

METODO = "regex:v1"
MAX_MUDANCAS = 15
_ONDE_SE_LE = re.compile(r"onde\s+se\s+l[êe]", re.IGNORECASE)


@dataclass
class Registro:
    fonte: str
    id: str
    titulo: str
    situacao: str  # fora_do_escopo | sem_edital | erro | publicado | so_revisao | encerrado | descoberto
    detalhe: str = ""
    slug: str | None = None
    campos: dict[str, str] = field(default_factory=dict)
    violacoes: list[str] = field(default_factory=list)


def _compativeis(a: tuple, b: tuple) -> bool:
    return a[1] == b[1] and (a[0] is None or b[0] is None or a[0] == b[0])


def _escolher(texto: list, tab: list):
    """Cláusula em texto corrido e linha de cronograma precisam concordar.
    Devolve (candidato, None), (None, motivo) para revisão ou (None, None) se não há nada."""
    principal = clausulas.principal(texto)
    ints_texto = clausulas.intervalos_distintos(texto)
    ints_tab = {(c.inicio, c.fim) for c in tab}
    if principal is not None:
        alvo = (principal.inicio, principal.fim)
        if any(not _compativeis(alvo, i) for i in ints_tab):
            return None, "cláusula do edital e cronograma em tabela divergem"
        return principal, None
    if len(ints_tab) == 1:
        alvo = next(iter(ints_tab))
        if all(_compativeis(alvo, i) for i in ints_texto):
            return tab[0], None
        return None, "cronograma em tabela diverge do texto corrido"
    if len(ints_tab) > 1:
        return None, f"{len(ints_tab)} linhas de cronograma com datas diferentes"
    if texto:
        return None, f"{len(ints_texto)} cláusulas diferentes" if ints_texto else "só há cláusulas de cronograma em texto corrido"
    return None, None


def slugificar(texto: str) -> str:
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", sem_acento(texto))).strip("-")


def sufixo_do_slug(cf: ConcursoFonte, cls: Classificacao) -> str:
    """Qualificador estável que separa concursos do mesmo órgão e ano (juiz x servidor)."""
    if cf.fonte == "cebraspe":
        ignorar = set(cls.sigla.split("-")) | {cls.uf.lower(), "26", "25", "24", "27"}
        ignorar |= set(slugificar(cls.orgao).split("-"))
        tokens = [t for t in slugificar(cf.id).split("-") if t not in ignorar and not t.isdigit()]
        return "-".join(tokens)
    if cf.fonte == "fgv" and " - " in cf.titulo:
        resto = cf.titulo.rsplit(" - ", 1)[1]
        resto = re.sub(r"\(\s*\d{4}(?:\.\d)?\s*\)", "", resto)
        s = slugificar(resto)
        return "" if s in {"", cls.sigla, cls.sigla.replace("-", "")} else s
    return ""


class Coletor:
    def __init__(
        self,
        cliente: Cliente,
        store: JsonStore,
        allowlist: Allowlist,
        agora: Callable[[], datetime] = lambda: datetime.now(BRT).replace(microsecond=0),
    ):
        self.cliente, self.store, self.gate, self.agora = cliente, store, Gate(allowlist), agora
        self._existentes = {
            str(c.descoberto_via.url): (p, c) for p, c in store.concursos() if c.descoberto_via is not None
        }
        self._slugs = {c.slug for _, c in store.concursos()}

    # ---- entrada ------------------------------------------------------------------

    def processar(self, cf: ConcursoFonte) -> Registro:
        reg = Registro(cf.fonte, cf.id, cf.titulo, "erro")
        try:
            cls = classificar(cf.titulo, *cf.contexto)
            if cls is None:
                reg.situacao = "fora_do_escopo"
                return reg
            reg.detalhe = f"{cls.categoria}/{cls.esfera}/{cls.uf}"
            if cf.edital is None:
                reg.situacao = "sem_edital"
                return reg
            return self._processar(cf, cls, reg)
        except Exception as e:  # um concurso nunca derruba a execução
            reg.situacao = "erro"
            reg.detalhe = f"{type(e).__name__}: {e}"
            if not isinstance(e, ErroColeta | NaoEhPdf):
                reg.detalhe += "\n" + traceback.format_exc(limit=3)
            return reg

    # ---- etapas -------------------------------------------------------------------

    def _baixar(self, doc: DocFonte, doc_id: str) -> tuple[Documento, TextoDocumento | None, bytes]:
        r = self.cliente.get(doc.url)
        try:
            texto = extrair(r.conteudo)
        except NaoEhPdf:
            texto = None
        documento = Documento(
            id=doc_id, tipo=doc.tipo, url=doc.url, url_final=r.url_final, sha256=r.sha256,
            coletado_em=r.coletado_em, fonte=self._fonte_atual, publicado_em=doc.publicado_em,
            titulo=doc.titulo[:300] or None,
        )
        return documento, texto, r.conteudo

    def _processar(self, cf: ConcursoFonte, cls: Classificacao, reg: Registro) -> Registro:
        self._fonte_atual = cf.fonte
        edital_fonte = cf.edital
        doc_edital, txt_edital, pdf_edital = self._baixar(edital_fonte, "doc-1")
        if txt_edital is None:
            raise NaoEhPdf(f"edital não é PDF: {doc_edital.url_final}")
        documentos, textos = [doc_edital], {doc_edital.sha256: txt_edital}

        evidencias: list[Evidencia] = []
        prazos = Prazos()
        try:
            linhas_tabela = tabela.linhas(pdf_edital, txt_edital.paginas)
        except Exception as e:  # tabela ilegível não derruba o concurso: só não há candidato de tabela
            linhas_tabela = []
            reg.violacoes.append(f"cronograma em tabela ilegível: {type(e).__name__}")
        for tipo, campo in clausulas.CAMPO_POR_TIPO.items():
            cands = clausulas.encontrar(txt_edital.paginas, tipo)
            tab = [c for c in tabela.candidatos(linhas_tabela, txt_edital.paginas, tipo) if not c.ambiguo]
            escolhido, motivo = _escolher(cands, tab)
            if escolhido is not None:
                linha = LinhaTabela(atividade=escolhido.tabela[0], datas=escolhido.tabela[1]) if escolhido.tabela else None
                ev = Evidencia(id=f"ev-{len(evidencias) + 1}", campo=campo, documento="doc-1",
                               pagina=escolhido.pagina, trecho=escolhido.trecho, ancora=escolhido.ancora,
                               metodo="tabela:v1" if linha else METODO, tabela=linha)
                evidencias.append(ev)
                setattr(prazos, tipo, Prazo(inicio=escolhido.inicio, fim=escolhido.fim, status="verificado",
                                            evidencia=ev.id))
            elif motivo:
                setattr(prazos, tipo, Prazo(status="revisao"))
                reg.violacoes.append(f"{campo}: {motivo}")

        vagas_campo = None
        achados = vagas.encontrar(txt_edital.paginas)
        v = vagas.principal(achados)
        if v is not None:
            ev = Evidencia(id=f"ev-{len(evidencias) + 1}", campo="vagas_imediatas", documento="doc-1",
                           pagina=v.pagina, trecho=v.trecho, ancora="vagas", metodo=METODO)
            evidencias.append(ev)
            vagas_campo = Campo(valor=v.valor, status="verificado", evidencia=ev.id)
        elif achados:
            vagas_campo = Campo(status="revisao")

        existente = self._existentes.get(cf.url)
        hoje = self.agora().date()
        abertos = [p for p in (prazos.isencao, prazos.inscricao) if p.status == "verificado" and p.fim and p.fim >= hoje]
        verif = [p for p in (prazos.isencao, prazos.inscricao) if p.status == "verificado"]
        if not existente and verif and not abertos:
            # Concurso novo sem nenhum prazo verificado ainda aberto: o site é sobre prazos abertos.
            reg.situacao = "encerrado"
            return reg
        if not existente and all(p.status != "verificado" for p in (prazos.isencao, prazos.inscricao)):
            mudancas_necessarias = False  # nada a proteger: o G7 não tem o que rebaixar
        else:
            mudancas_necessarias = True
        mudancas = [] if not mudancas_necessarias else [
            d for d in cf.documentos
            if d.tipo == "retificacao"
            and (d.publicado_em is None or edital_fonte.publicado_em is None or d.publicado_em >= edital_fonte.publicado_em)
        ][-MAX_MUDANCAS:]
        for i, d in enumerate(mudancas, start=2):
            try:
                doc, txt, _ = self._baixar(d, f"doc-{i}")
            except ErroColeta as e:
                # sem o documento não dá para descartar impacto: G7 rebaixa o que ele poderia afetar
                reg.violacoes.append(f"documento de mudança indisponível: {d.url} ({e})")
                doc = Documento(id=f"doc-{i}", tipo="retificacao", url=d.url, url_final=d.url, sha256="0" * 64,
                                coletado_em=self.agora(), fonte=cf.fonte, publicado_em=d.publicado_em,
                                titulo=d.titulo[:300] or None)
                txt = None
            documentos.append(doc)
            if txt is not None:
                textos[doc.sha256] = txt
            elif doc.sha256 != "0" * 64:
                textos[doc.sha256] = TextoDocumento(doc.sha256, {}, completo=True, tem_texto=False)

        slug = existente[1].slug if existente else self._novo_slug(cf, cls)
        concurso = Concurso(
            slug=slug, orgao=cls.orgao, categoria=cls.categoria, esfera=cls.esfera, banca=cf.fonte, uf=cls.uf,
            cargos=[Cargo(nome=n) for n in cf.cargos if len(n) >= 2],
            vagas_imediatas=vagas_campo, porte=classificar_porte(vagas_campo), prazos=prazos,
            documentos=documentos, evidencias=evidencias,
            descoberto_via=Descoberta(fonte=cf.fonte, url=cf.url, data_dou=cf.data_dou),
            conferido_em=self.agora(),
        )

        # Gate com texto completo (G5 incluso) e, de novo, só com as páginas que serão guardadas:
        # o que vai para data/ precisa passar no `ntc validate` exatamente como passou aqui.
        resultado = self.gate.aplicar(concurso, textos)
        guardados = self._paginas_guardadas(resultado.concurso, textos)
        resultado2 = self.gate.aplicar(resultado.concurso, guardados)
        final = resultado2.concurso
        final.porte = classificar_porte(final.vagas_imediatas)
        Concurso.model_validate(final.model_dump())
        reg.violacoes += [f"{v.regra} {v.campo}: {v.mensagem}" for v in resultado.violacoes + resultado2.violacoes]

        reg.slug = slug
        reg.campos = {caminho: c.status for caminho, c in final.campos_com_evidencia()}
        verificados = [p for p in (final.prazos.isencao, final.prazos.inscricao) if p.status == "verificado"]
        # Novo concurso entra só com prazo verificado ainda aberto; um já publicado é sempre
        # regravado (para rebaixar campos que deixaram de passar no gate).
        if existente or any(p.fim and p.fim >= hoje for p in verificados):
            self.store.salvar_concurso(final)
            for doc in final.documentos:
                t = guardados.get(doc.sha256)
                if t is not None:  # mesmo sem páginas: registra que o texto existe e não cita prazo
                    self.store.salvar_texto(t, str(doc.url_final), set(t.paginas))
            reg.situacao = "publicado"
        else:
            reg.situacao = "so_revisao"
        pendentes = {k: s for k, s in reg.campos.items() if s == "revisao"}
        if pendentes or reg.violacoes:
            self.store.salvar_revisao(slug, {
                "slug": slug, "orgao": final.orgao, "fonte": cf.fonte, "url": cf.url,
                "edital": str(doc_edital.url_final), "campos_em_revisao": sorted(pendentes),
                "motivos": reg.violacoes, "registrado_em": self.agora().isoformat(),
            })
        else:
            self.store.remover_revisao(slug)
        self._slugs.add(slug)
        return reg

    def _novo_slug(self, cf: ConcursoFonte, cls: Classificacao) -> str:
        ano = cf.ano or self.agora().year
        base = slugificar(f"{cls.sigla} {ano} {sufixo_do_slug(cf, cls)}")[:100].strip("-")
        slug, n = base, 2
        while slug in self._slugs:
            slug, n = f"{base}-{cf.fonte}" if n == 2 else f"{base}-{n}", n + 1
        return slug

    @staticmethod
    def _paginas_guardadas(c: Concurso, textos: dict[str, TextoDocumento]) -> dict[str, TextoDocumento]:
        """O que vai para data/documentos: páginas citadas por evidências e, nos documentos de
        mudança, as páginas que o G7 lê (âncora de prazo ou errata "onde se lê")."""
        saida: dict[str, TextoDocumento] = {}
        citadas: dict[str, set[int]] = {}
        for ev in c.evidencias:
            citadas.setdefault(c.documento(ev.documento).sha256, set()).add(ev.pagina)
        for doc in c.documentos:
            t = textos.get(doc.sha256)
            if t is None:
                continue
            if doc.tipo == "retificacao":
                paginas = {
                    n for n, p in t.paginas.items()
                    if any(a.search(p) for a in clausulas.ANCORAS.values()) or _ONDE_SE_LE.search(p)
                }
            else:
                paginas = citadas.get(doc.sha256, set())
            saida[doc.sha256] = TextoDocumento(
                t.sha256, {n: t.paginas[n] for n in sorted(paginas)}, completo=False, tem_texto=t.tem_texto
            )
        return saida


def resumo(registros: list[Registro]) -> dict:
    contagem: dict[str, int] = {}
    for r in registros:
        contagem[r.situacao] = contagem.get(r.situacao, 0) + 1
    return {"contagem": contagem, "registros": [asdict(r) for r in registros]}
