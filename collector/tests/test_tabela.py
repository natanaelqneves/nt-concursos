"""Cronograma em tabela: texto e células reais do edital da PC-PE 2026 (Cebraspe)."""

from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path

from ntc.coleta import _escolher
from ntc.gate.evidencia import TextoDocumento
from ntc.model.schema import Concurso
from ntc.parse import clausulas, tabela

from tests_helpers import regras

F = Path(__file__).parent / "fixtures" / "editais" / "pcpe26_cronograma.json"


def _dados():
    bruto = json.loads(F.read_text(encoding="utf-8"))
    paginas = {bruto["pagina"]: bruto["texto"]}
    linhas = [tabela.Linha(bruto["pagina"], a, d) for a, d in bruto["linhas"]]
    return paginas, linhas


def test_linha_certa_de_isencao_e_inscricao():
    paginas, linhas = _dados()
    isen = tabela.candidatos(linhas, paginas, "isencao")
    insc = tabela.candidatos(linhas, paginas, "inscricao")
    assert [(c.inicio, c.fim) for c in isen] == [(date(2026, 10, 15), date(2026, 11, 12))]
    assert [(c.inicio, c.fim) for c in insc] == [(date(2026, 10, 15), date(2026, 12, 16))]
    assert isen[0].trecho == "Período de solicitação de inscrição com isenção de taxa de inscrição — 15/10 a 12/11/2026"


def test_texto_corrido_da_mesma_pagina_nao_sustenta_nada():
    paginas, _ = _dados()
    assert clausulas.principal(clausulas.encontrar(paginas, "isencao")) is None


def test_consulta_recurso_e_pagamento_nao_viram_prazo():
    paginas, linhas = _dados()
    atividades = [c.tabela[0] for t in ("isencao", "inscricao") for c in tabela.candidatos(linhas, paginas, t)]
    assert not any(p in a.lower() for a in atividades for p in ("consulta", "recurso", "pagamento", "foto"))


def test_celula_que_nao_esta_no_texto_da_pagina_e_descartada():
    paginas, linhas = _dados()
    alterada = [tabela.Linha(l.pagina, l.atividade, "20/10 a 30/11/2026") for l in linhas]
    assert tabela.candidatos(alterada, paginas, "isencao") == []


def test_escolher_recusa_divergencia_entre_texto_e_tabela():
    paginas, linhas = _dados()
    tab = tabela.candidatos(linhas, paginas, "inscricao")
    texto = clausulas.encontrar({1: "5.1 As inscrições estarão abertas no período de 15/10/2026 a 10/12/2026."}, "inscricao")
    escolhido, motivo = _escolher(texto, tab)
    assert escolhido is None and "divergem" in motivo


def test_gate_confere_celulas_da_evidencia_de_tabela(gate, novo):
    paginas, linhas = _dados()
    c = tabela.candidatos(linhas, paginas, "isencao")[0]
    d = novo()
    sha = "c" * 64
    d["documentos"][0]["sha256"] = sha
    d["prazos"]["isencao"] = {"inicio": "2026-10-15", "fim": "2026-11-12", "status": "verificado", "evidencia": "ev-1"}
    d["prazos"]["inscricao"] = {"status": "ausente"}
    d["evidencias"][0] |= {"pagina": 92, "trecho": c.trecho, "ancora": c.ancora, "metodo": "tabela:v1",
                           "tabela": {"atividade": c.tabela[0], "datas": c.tabela[1]}}
    d["evidencias"] = [d["evidencias"][0], d["evidencias"][2], d["evidencias"][3]]
    textos = {sha: TextoDocumento(sha, paginas, completo=True)}
    from ntc.fetch.allowlist import Allowlist  # noqa: F401  (fixture gate já carrega)
    r = gate.aplicar(Concurso.model_validate(d), textos)
    assert regras(r) <= {"G3"} and not {v for v in r.violacoes if v.campo == "prazos.isencao"}

    ruim = copy.deepcopy(d)
    ruim["evidencias"][0]["tabela"]["datas"] = "27/11 a 3/12/2026"
    ruim["evidencias"][0]["trecho"] = f"{c.tabela[0]} — 27/11 a 3/12/2026"
    r2 = gate.aplicar(Concurso.model_validate(ruim), textos)
    assert any(v.regra == "G4" and v.campo == "prazos.isencao" for v in r2.violacoes)
