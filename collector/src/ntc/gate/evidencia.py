"""Gate de evidência: nenhum campo `verificado` vai ao ar sem passar por G1–G8.

O gate não corrige dados: rebaixa para `revisao` todo campo que falhe e
devolve a lista de violações, que alimenta a fila de revisão humana.

G1  host da URL final na allowlist
G2  texto do documento armazenado para o sha256 declarado
G3  trecho contido literalmente na página indicada (normalizando só espaços)
G4  cláusula: o trecho contém a âncora do campo e exatamente o(s) valor(es) declarado(s)
G5  unicidade: o documento (texto completo) não tem outra cláusula com datas diferentes
G6  plausibilidade: ano próximo ao da coleta; isenção não termina depois da inscrição
G7  retificação publicada depois do documento da evidência derruba o campo se: não tiver
    texto; trouxer cláusula do prazo com datas diferentes (ou ambígua); falar do prazo junto
    de prorrogação/reabertura/suspensão; ou for errata "onde se lê" que cite o prazo.
    Ordem por `publicado_em`; sem ela, `coletado_em`.
G8  documento sem camada de texto (PDF escaneado) não sustenta campo nenhum

Campos aprovados por humano (aprovado_por) passam apenas por G1–G3: a revisão
substitui as heurísticas, mas nunca dispensa o trecho literal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from ntc.fetch.allowlist import Allowlist
from ntc.model.schema import Campo, Concurso, Evidencia, Prazo
from ntc.parse import clausulas
from ntc.parse.texto import normalizar

TIPO_POR_CAMPO = {v: k for k, v in clausulas.CAMPO_POR_TIPO.items()}


@dataclass(frozen=True)
class TextoDocumento:
    sha256: str
    paginas: dict[int, str]
    completo: bool = False  # True apenas durante a coleta, com o PDF inteiro em mãos
    tem_texto: bool = True


@dataclass(frozen=True)
class Violacao:
    regra: str
    campo: str
    mensagem: str


@dataclass
class ResultadoGate:
    concurso: Concurso
    violacoes: list[Violacao] = field(default_factory=list)

    @property
    def aprovado(self) -> bool:
        return not self.violacoes


def _formatos_valor(valor: float | int | str) -> list[str]:
    if isinstance(valor, str):
        return [normalizar(valor)]
    if isinstance(valor, int) or float(valor).is_integer():
        n = int(valor)
        milhar = f"{n:,}".replace(",", ".")
        return [rf"\b{re.escape(str(n))}\b", rf"\b{re.escape(milhar)}\b", rf"\b{n},00\b"]
    reais = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return [re.escape(reais), re.escape(reais.replace(".", ""))]


def _valor_no_trecho(valor: float | int | str, trecho: str) -> bool:
    if isinstance(valor, str):
        return normalizar(valor).lower() in trecho.lower()
    return any(re.search(p, trecho) for p in _formatos_valor(valor))


class Gate:
    def __init__(self, allowlist: Allowlist):
        self.allowlist = allowlist

    def aplicar(self, concurso: Concurso, textos: dict[str, TextoDocumento]) -> ResultadoGate:
        resultado = ResultadoGate(concurso.model_copy(deep=True))
        c = resultado.concurso
        for caminho, campo in c.campos_com_evidencia():
            if campo.status != "verificado":
                continue
            ev = c.evidencia(campo.evidencia)  # integridade garantida pelo schema
            falhas = self._checar(c, caminho, campo, ev, textos)
            if falhas:
                campo.status = "revisao"
                resultado.violacoes.extend(falhas)
        self._checar_isencao_vs_inscricao(c, resultado)
        return resultado

    def _checar(
        self,
        c: Concurso,
        caminho: str,
        campo: Prazo | Campo,
        ev: Evidencia,
        textos: dict[str, TextoDocumento],
    ) -> list[Violacao]:
        doc = c.documento(ev.documento)

        def falha(regra: str, msg: str) -> list[Violacao]:
            return [Violacao(regra, caminho, msg)]

        if not self.allowlist.permitido(str(doc.url_final)):
            return falha("G1", f"host fora da allowlist: {doc.url_final}")
        texto = textos.get(doc.sha256)
        if texto is None:
            return falha("G2", f"texto do documento {doc.sha256[:12]} não armazenado")
        if not texto.tem_texto:
            return falha("G8", "documento sem camada de texto")
        pagina = texto.paginas.get(ev.pagina)
        trecho = normalizar(ev.trecho)
        if pagina is None or trecho not in normalizar(pagina):
            return falha("G3", f"trecho não encontrado na página {ev.pagina}")

        if ev.aprovado_por:
            return []

        if isinstance(campo, Prazo):
            tipo = TIPO_POR_CAMPO.get(caminho)
            if tipo is None:
                return falha("G4", "prazo sem tipo conhecido")
            if not clausulas.ANCORAS[tipo].search(trecho):
                return falha("G4", f"trecho sem âncora de {tipo}")
            if clausulas.EXCLUSOES[tipo].search(trecho):
                return falha("G4", "trecho descreve outro evento do cronograma")
            esperado = [d for d in (campo.inicio, campo.fim) if d is not None]
            if clausulas.datas_de_prazo(trecho) != esperado:
                return falha("G4", f"datas do trecho {clausulas.datas_de_prazo(trecho)} ≠ declaradas {esperado}")
            if texto.completo:
                distintos = clausulas.intervalos_distintos(clausulas.encontrar(texto.paginas, tipo))
                if len(distintos) > 1:
                    return falha("G5", f"{len(distintos)} cláusulas de {tipo} com datas diferentes")
            ano = doc.coletado_em.year
            if any(not (ano - 1 <= d.year <= ano + 1) for d in esperado):
                return falha("G6", "ano do prazo distante do ano da coleta")
            if self._retificado_depois(c, doc.id, tipo, campo, textos):
                return falha("G7", "retificação posterior menciona este prazo")
        elif not _valor_no_trecho(campo.valor, trecho):
            return falha("G4", f"valor {campo.valor!r} não aparece no trecho")
        return []

    @staticmethod
    def _retificado_depois(
        c: Concurso, doc_id: str, tipo: str, campo: Prazo, textos: dict[str, TextoDocumento]
    ) -> bool:
        base = c.documento(doc_id)
        for d in c.documentos:
            if d.tipo != "retificacao" or not d.posterior_a(base):
                continue
            t = textos.get(d.sha256)
            if t is None or not t.tem_texto:
                return True  # sem texto, não há como descartar o impacto
            if clausulas.altera_prazo(t.paginas, tipo, campo.inicio, campo.fim):
                return True
        return False

    @staticmethod
    def _checar_isencao_vs_inscricao(c: Concurso, resultado: ResultadoGate) -> None:
        isen, insc = c.prazos.isencao, c.prazos.inscricao
        if isen.status == insc.status == "verificado" and isen.fim > insc.fim:
            isen.status = "revisao"
            resultado.violacoes.append(
                Violacao("G6", "prazos.isencao", "isenção termina depois das inscrições")
            )


def hoje_brt() -> date:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("America/Sao_Paulo")).date()
