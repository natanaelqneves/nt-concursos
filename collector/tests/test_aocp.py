"""Instituto AOCP: respostas reais da API pública (12/11/2026)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ntc.escopo import classificar
from ntc.sources import aocp

FIX = Path(__file__).parent / "fixtures" / "aocp"
HOJE = date(2026, 11, 12)


def _j(nome):
    return json.loads((FIX / nome).read_text(encoding="utf-8"))


def _item(lista, id_):
    return next(c for c in lista if str(c["id"]) == id_)


def test_lista_abertas_e_andamento_recente():
    abertas = aocp.parse_lista(_j("lista_abertas.json"), "SUBSCRIBE", HOJE)
    assert {"proseleta-3", "714", "715"} <= {str(c["id"]) for c in abertas}
    andamento = {str(c["id"]) for c in aocp.parse_lista(_j("lista_andamento.json"), "IN_PROGRESS", HOJE)}
    assert "720" in andamento  # inscrição até 06/11/2026
    assert "26" not in andamento and "672" not in andamento  # MPBA 2014, PPMG 2025


def test_detalhe_proseleta_pmsc():
    lista = _j("lista_abertas.json")
    cf = aocp.parse_detalhe("proseleta-3", _item(lista, "proseleta-3"), _j("detalhe_proseleta_3.json")[0])
    assert cf.url == "https://www.institutoaocp.org.br/concursos/proseleta-3"
    assert cf.edital.titulo.startswith("Edital de Abertura nº 002/CCP/2026")
    assert cf.edital.publicado_em == date(2026, 10, 19)
    assert cf.edital.url.startswith("https://anexos-r2.selecao.net.br/")
    mud = [d.titulo for d in cf.documentos if d.tipo == "retificacao"]
    assert any("Primeiro Termo de Retificação" in t for t in mud) and any("Segundo Termo" in t for t in mud)
    assert cf.ano == 2026
    r = classificar(cf.titulo, *cf.contexto)
    assert (r.categoria, r.esfera, r.uf) == ("seguranca", "estadual", "SC")


def test_detalhe_legado_pmpe():
    lista = _j("lista_abertas.json")
    cf = aocp.parse_detalhe("714", _item(lista, "714"), _j("detalhe_714.json")[0])
    assert cf.edital.titulo == "Concurso Público 001/2026 - Edital de Abertura"
    assert cf.edital.publicado_em == date(2026, 9, 30)
    assert any("Ampliação do Prazo" in d.titulo for d in cf.documentos if d.tipo == "retificacao")
    r = classificar(cf.titulo, *cf.contexto)
    assert (r.categoria, r.uf) == ("seguranca", "PE")


def test_suspenso_fica_de_fora():
    lista = _j("lista_abertas.json")
    assert aocp.parse_detalhe("701", _item(lista, "701"), _j("detalhe_701.json")[0]) is None


def test_processo_seletivo_fora_do_escopo():
    lista = _j("lista_abertas.json")
    hu = _item(lista, "727")
    cf = aocp.parse_detalhe("727", hu, {"publicacoes": []})
    assert classificar(cf.titulo, *cf.contexto) is None
