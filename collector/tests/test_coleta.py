"""Pipeline de ponta a ponta com o texto real do edital do TJPB (FGV, 12/11/2026).

O PDF não é versionado: a extração é substituída pelas páginas reais guardadas em
fixtures/editais/tjpb26_ancoras.json (todas as páginas do edital que citam isenção ou
inscrição). O resto do caminho é o de produção: escopo, cláusulas, gate duplo e gravação.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

import pytest

from ntc import coleta
from ntc.cli import main
from ntc.fetch.allowlist import Allowlist
from ntc.fetch.http import BRT, Resposta
from ntc.gate.evidencia import TextoDocumento
from ntc.sources import fgv
from ntc.store.json_store import JsonStore

F = Path(__file__).parent / "fixtures"
RAIZ = Path(__file__).resolve().parents[2]
EDITAL = "https://conhecimento.fgv.br/sites/default/files/concursos/edital-retificado-tjpb_11.11.pdf"
AGORA = datetime(2026, 11, 12, 13, 0, tzinfo=BRT)


class ClienteFalso:
    def __init__(self, arquivos: dict[str, bytes]):
        self.arquivos = arquivos

    def get(self, url, **_):
        if url not in self.arquivos:
            raise coleta.ErroColeta(f"HTTP 404 em {url}")
        return Resposta(url, url, 200, self.arquivos[url], "application/pdf", AGORA)


@pytest.fixture
def dados(tmp_path) -> Path:
    shutil.copy(RAIZ / "data" / "fontes.yaml", tmp_path / "fontes.yaml")
    return tmp_path


@pytest.fixture
def paginas_tjpb() -> dict[int, str]:
    bruto = json.loads((F / "editais" / "tjpb26_ancoras.json").read_text(encoding="utf-8"))
    return {int(k): v for k, v in bruto["paginas"].items()}


@pytest.fixture
def extrair_falso(monkeypatch, paginas_tjpb):
    """Bytes "%PDF-edital" viram o texto real do edital; "%PDF-ret-..." viram o texto indicado."""
    textos = {b"%PDF-edital": paginas_tjpb}

    def extrair(conteudo: bytes):
        import hashlib

        sha = hashlib.sha256(conteudo).hexdigest()
        return TextoDocumento(sha, textos[conteudo], completo=True)

    monkeypatch.setattr(coleta, "extrair", extrair)
    return textos


def _cf():
    return fgv.parse_concurso((F / "fgv" / "tjpb26.html").read_text(encoding="utf-8"),
                              "https://conhecimento.fgv.br/concursos/tjpb26")


def test_tjpb_publicado_com_evidencias(dados, extrair_falso):
    ret3 = "https://conhecimento.fgv.br/sites/default/files/concursos/06.11-extrato-3a-retificacao-do-edital-tjpb.pdf"
    extrair_falso[b"%PDF-ret3"] = {1: "Extrato da 3ª retificação: altera o subitem 12.4 (conteúdo programático)."}
    cliente = ClienteFalso({EDITAL: b"%PDF-edital", ret3: b"%PDF-ret3"})
    store = JsonStore(dados)
    reg = coleta.Coletor(cliente, store, Allowlist.carregar(dados / "fontes.yaml"), agora=lambda: AGORA).processar(_cf())

    assert reg.situacao == "publicado", reg
    assert reg.slug == "tj-pb-2026"
    c = json.loads((dados / "concursos" / "tj-pb-2026.json").read_text(encoding="utf-8"))
    assert (c["categoria"], c["esfera"], c["uf"], c["banca"]) == ("tribunal", "estadual", "PB", "fgv")
    assert c["prazos"]["isencao"] | {} == {"inicio": "2026-10-20", "fim": "2026-10-27", "status": "verificado",
                                           "evidencia": "ev-1"}
    assert c["prazos"]["inscricao"]["fim"] == "2026-11-18"
    assert c["porte"] == "indefinido"  # o edital do TJPB traz as vagas em tabela
    ev = c["evidencias"][0]
    assert ev["pagina"] == 6 and "20 de outubro de 2026" in ev["trecho"]
    # Só páginas citadas do edital são guardadas
    doc = json.loads((dados / "documentos" / f"{c['documentos'][0]['sha256']}.json").read_text(encoding="utf-8"))
    assert set(doc["paginas"]) == {"3", "6"}
    # E o resultado passa no validate, como no CI e na publicação
    assert main(["validate", "--data", str(dados)]) == 0
    assert not (dados / "revisao" / "tj-pb-2026.json").exists()


def test_retificacao_que_prorroga_derruba_inscricao(dados, extrair_falso):
    cf = _cf()
    nova = fgv.DocFonte("https://conhecimento.fgv.br/sites/default/files/concursos/4a-retificacao.pdf",
                        "retificacao", "4ª Retificação", datetime(2026, 11, 13).date())
    cf.documentos.append(nova)
    extrair_falso[b"%PDF-ret4"] = {1: "Fica prorrogado o período de inscrições até 25 de novembro de 2026."}
    cliente = ClienteFalso({EDITAL: b"%PDF-edital", nova.url: b"%PDF-ret4"})
    reg = coleta.Coletor(cliente, JsonStore(dados), Allowlist.carregar(dados / "fontes.yaml"),
                         agora=lambda: AGORA).processar(cf)
    assert reg.campos["prazos.inscricao"] == "revisao"
    assert reg.campos["prazos.isencao"] == "verificado"
    assert any(v.startswith("G7 prazos.inscricao") for v in reg.violacoes)
    revisao = json.loads((dados / "revisao" / "tj-pb-2026.json").read_text(encoding="utf-8"))
    assert revisao["campos_em_revisao"] == ["prazos.inscricao"]
    assert main(["validate", "--data", str(dados)]) == 0


def test_fora_do_escopo_nao_baixa_nada(dados):
    cf = fgv.ConcursoFonte("fgv", "prefeiturademacae26", "Concurso Público para a Prefeitura de Macaé",
                           "https://conhecimento.fgv.br/concursos/prefeiturademacae26")
    reg = coleta.Coletor(ClienteFalso({}), JsonStore(dados), Allowlist.carregar(dados / "fontes.yaml")).processar(cf)
    assert reg.situacao == "fora_do_escopo"
    assert not (dados / "concursos").exists()


def test_slug_estavel_entre_coletas(dados, extrair_falso):
    cliente = ClienteFalso({EDITAL: b"%PDF-edital"})
    al = Allowlist.carregar(dados / "fontes.yaml")
    r1 = coleta.Coletor(cliente, JsonStore(dados), al, agora=lambda: AGORA).processar(_cf())
    r2 = coleta.Coletor(cliente, JsonStore(dados), al, agora=lambda: AGORA).processar(_cf())
    assert r1.slug == r2.slug == "tj-pb-2026"
    assert len(list((dados / "concursos").glob("*.json"))) == 1


def test_concurso_novo_ja_encerrado_nao_entra(dados, extrair_falso):
    depois = datetime(2026, 12, 1, 9, 0, tzinfo=BRT)
    cliente = ClienteFalso({EDITAL: b"%PDF-edital"})
    reg = coleta.Coletor(cliente, JsonStore(dados), Allowlist.carregar(dados / "fontes.yaml"),
                         agora=lambda: depois).processar(_cf())
    assert reg.situacao == "encerrado"
    assert not (dados / "concursos").exists()
