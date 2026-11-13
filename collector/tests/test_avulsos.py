"""Fonte "avulsos": edital achado fora das bancas coletadas (oficial ou cópia)."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

import pytest

from ntc import coleta
from ntc.fetch.allowlist import Allowlist
from ntc.fetch.http import BRT, BloqueadoPorRobots, Resposta
from ntc.gate.evidencia import TextoDocumento
from ntc.model.schema import Concurso
from ntc.sources.avulsos import Avulsos
from ntc.store.json_store import JsonStore

RAIZ = Path(__file__).resolve().parents[2]
AGORA = datetime(2026, 11, 13, 10, 0, tzinfo=BRT)

OFICIAL = "https://www.institutoaocp.org.br/edital.pdf"  # não está na lista: simula indisponível
COPIA = "https://arquivos.qconcursos.com/f/edital-pm-pe.pdf"
RET = "https://dhg1h5j42swfq.cloudfront.net/2026/10/15/ret.pdf"
BLOQ = "https://magistrarcursos.com.br/blog/ret.pdf"

EDITAL_TXT = {
    3: "4.1 O pedido de isenção da taxa de inscrição poderá ser feito no período de 05/10/2026 a 08/10/2026. "
       "5.1 As inscrições serão realizadas exclusivamente via internet, no período entre 9h do dia 05 de "
       "outubro de 2026 e 23h59min do dia 05 de novembro de 2026."
}
RET_TXT = {
    1: "XI - Modificar o subitem 5.1, que passa a vigorar com a seguinte redação: 5.1 As inscrições serão "
       "realizadas exclusivamente via internet, no período entre 9h do dia 05 de outubro de 2026 e 14h do "
       "dia 23 de novembro de 2026."
}


class Cliente:
    def __init__(self, arquivos: dict[str, bytes], bloqueados: set[str] = frozenset()):
        self.arquivos, self.bloqueados, self.pedidos = arquivos, bloqueados, []

    def get(self, url, **_):
        self.pedidos.append(url)
        if url in self.bloqueados:
            raise BloqueadoPorRobots(f"robots.txt não permite: {url}")
        if url not in self.arquivos:
            raise coleta.ErroColeta(f"HTTP 404 em {url}")
        return Resposta(url, url, 200, self.arquivos[url], "application/pdf", AGORA)


@pytest.fixture
def dados(tmp_path, monkeypatch) -> Path:
    shutil.copy(RAIZ / "data" / "fontes.yaml", tmp_path / "fontes.yaml")
    (tmp_path / "noticias").mkdir()
    (tmp_path / "noticias" / "pm-pe-2026.json").write_text(json.dumps({
        "slug": "pm-pe-2026",
        "fatos": [{"campo": "inscricao", "inicio": "2026-10-05", "fim": "2026-11-23"}],
    }), encoding="utf-8")
    textos = {b"%PDF-edital": EDITAL_TXT, b"%PDF-ret": RET_TXT}
    monkeypatch.setattr(coleta, "extrair",
                        lambda c: TextoDocumento(hashlib.sha256(c).hexdigest(), textos[c], completo=True))
    monkeypatch.setattr(coleta.tabela, "linhas", lambda pdf, paginas: [])
    return tmp_path


def _entrada(documentos):
    return {"concursos": [{
        "slug": "pm-pe-2026-soldado", "noticia": "pm-pe-2026", "titulo": "Polícia Militar do Estado de Pernambuco",
        "banca": "aocp", "pagina": "https://www.institutoaocp.org.br/", "cargos": ["Soldado"],
        "documentos": documentos, "pesquisa": ["teste"],
    }]}


def _rodar(dados, entrada, cliente, agora=AGORA):
    (dados / "editais-avulsos.json").write_text(json.dumps(entrada), encoding="utf-8")
    cf = next(Avulsos(dados).descobrir(cliente))
    store = JsonStore(dados)
    reg = coleta.Coletor(cliente, store, Allowlist.carregar(dados / "fontes.yaml"), agora=lambda: agora).processar(cf)
    return reg, store


EDITAL = {"tipo": "edital", "titulo": "Edital 001/2026", "publicado_em": "2026-09-29", "urls": [OFICIAL, COPIA]}
RETIF = {"tipo": "retificacao", "titulo": "Portaria 310", "publicado_em": "2026-10-15", "urls": [BLOQ, RET]}


def test_prazo_da_retificacao_em_copia(dados):
    cliente = Cliente({COPIA: b"%PDF-edital", RET: b"%PDF-ret"}, bloqueados={BLOQ})
    reg, store = _rodar(dados, _entrada([EDITAL, RETIF]), cliente)

    assert reg.situacao == "publicado", reg
    c = Concurso.model_validate_json((dados / "concursos" / "pm-pe-2026-soldado.json").read_text(encoding="utf-8"))
    assert c.banca == "aocp" and c.uf == "PE"
    assert (str(c.prazos.inscricao.fim), c.prazos.inscricao.status) == ("2026-11-23", "verificado")
    ev = c.evidencia(c.prazos.inscricao.evidencia)
    assert c.documento(ev.documento).tipo == "retificacao"
    # cada documento registra o site onde foi achado: o oficial falhou, valeu a cópia
    assert [d.fonte for d in c.documentos] == ["qconcursos", "cdn-cloudfront"]
    assert cliente.pedidos[:2] == [OFICIAL, COPIA]
    assert BLOQ in cliente.pedidos and RET in cliente.pedidos


def test_copia_desatualizada_vai_para_revisao(dados):
    """Sem a retificação, o edital diz 05/11 e a imprensa 23/11: o prazo não vai ao ar como conferido
    (em 01/11 o prazo do edital ainda estaria aberto e seria publicado com a data errada)."""
    cliente = Cliente({COPIA: b"%PDF-edital"})
    reg, _ = _rodar(dados, _entrada([EDITAL]), cliente, agora=datetime(2026, 11, 1, 10, 0, tzinfo=BRT))

    assert reg.campos["prazos.inscricao"] == "revisao"
    assert any("imprensa diz 2026-11-23" in v for v in reg.violacoes)


def test_slug_fixo_e_entradas_com_mesma_pagina(dados):
    cliente = Cliente({COPIA: b"%PDF-edital", RET: b"%PDF-ret"})
    reg, _ = _rodar(dados, _entrada([EDITAL, RETIF]), cliente)
    assert reg.slug == "pm-pe-2026-soldado"


def test_lista_real_e_valida():
    """data/editais-avulsos.json: toda URL na allowlist e cada notícia citada existe."""
    al = Allowlist.carregar(RAIZ / "data" / "fontes.yaml")
    entradas = json.loads((RAIZ / "data" / "editais-avulsos.json").read_text(encoding="utf-8"))["concursos"]
    slugs = [e["slug"] for e in entradas]
    assert len(slugs) == len(set(slugs))
    for e in entradas:
        assert e["pesquisa"], e["slug"]
        assert (RAIZ / "data" / "noticias" / f"{e['noticia']}.json").exists(), e["slug"]
        for d in e["documentos"]:
            for u in d["urls"]:
                assert al.permitido(u), u
