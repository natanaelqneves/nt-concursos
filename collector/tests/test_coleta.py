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


def test_cebraspe_pelo_cronograma_em_tabela(dados, monkeypatch):
    """PC-PE 2026: os prazos só existem no Anexo I (tabela)."""
    from ntc.parse import tabela
    from ntc.sources import cebraspe

    bruto = json.loads((F / "editais" / "pcpe26_cronograma.json").read_text(encoding="utf-8"))
    det = json.loads((F / "cebraspe" / "PC_PE_26.json").read_text(encoding="utf-8"))
    cf = cebraspe.parse_evento(det)
    cf.documentos = [cf.edital]  # retificações ficam para o teste de G7
    monkeypatch.setattr(coleta, "extrair", lambda b: TextoDocumento(
        __import__("hashlib").sha256(b).hexdigest(), {92: bruto["texto"]}, completo=True))
    monkeypatch.setattr(tabela, "linhas", lambda pdf, pags: [tabela.Linha(92, a, d) for a, d in bruto["linhas"]])
    reg = coleta.Coletor(ClienteFalso({cf.edital.url: b"%PDF-pcpe"}), JsonStore(dados),
                         Allowlist.carregar(dados / "fontes.yaml"), agora=lambda: AGORA).processar(cf)
    assert reg.situacao == "publicado", reg
    c = json.loads((dados / "concursos" / f"{reg.slug}.json").read_text(encoding="utf-8"))
    assert reg.slug == "pc-pe-2026"
    assert (c["prazos"]["isencao"]["inicio"], c["prazos"]["isencao"]["fim"]) == ("2026-10-15", "2026-11-12")
    assert c["prazos"]["inscricao"]["fim"] == "2026-12-16"
    assert c["evidencias"][0]["metodo"] == "tabela:v1"
    assert main(["validate", "--data", str(dados)]) == 0


# ---- revisão com opções e decisões do editor ----------------------------------------------

CONFLITO = "As inscrições serão recebidas no período de 01/12/2026 a 10/12/2026, exclusivamente pela internet."


def _coletar(dados, cf=None):
    cliente = ClienteFalso({EDITAL: b"%PDF-edital"})
    return coleta.Coletor(cliente, JsonStore(dados), Allowlist.carregar(dados / "fontes.yaml"),
                          agora=lambda: AGORA).processar(cf or _cf())


def _decidir(dados, corpo: dict, nome="20261112-190000"):
    pasta = dados / "decisoes" / corpo["slug"]
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / f"{nome}.json").write_text(json.dumps(corpo), encoding="utf-8")


def test_revisao_traz_opcoes_e_decisao_publica_com_aprovacao(dados, extrair_falso, paginas_tjpb):
    extrair_falso[b"%PDF-edital"] = paginas_tjpb | {50: CONFLITO}
    reg = _coletar(dados)
    assert reg.campos.get("prazos.inscricao") == "revisao", reg
    rev = json.loads((dados / "revisao" / "tj-pb-2026.json").read_text(encoding="utf-8"))
    assert rev["schema_version"] == 2 and rev["campos_em_revisao"] == ["prazos.inscricao"]
    opcoes = rev["opcoes"]["prazos.inscricao"]
    fins = {o["fim"] for o in opcoes}
    assert {"2026-11-18", "2026-12-10"} <= fins
    certa = next(o for o in opcoes if o["fim"] == "2026-11-18")

    _decidir(dados, {"schema_version": 1, "slug": "tj-pb-2026", "decidido_em": "2026-11-12T19:00:00-03:00",
                     "edital_sha256": rev["edital_sha256"], "acao": "decidir",
                     "campos": {"prazos.inscricao": {"acao": "usar", "opcao": {
                         k: certa[k] for k in ("origem", "pagina", "trecho", "inicio", "fim")}}}})
    reg = _coletar(dados)
    assert reg.campos["prazos.inscricao"] == "verificado", reg
    c = json.loads((dados / "concursos" / "tj-pb-2026.json").read_text(encoding="utf-8"))
    ev = next(e for e in c["evidencias"] if e["id"] == c["prazos"]["inscricao"]["evidencia"])
    assert ev["aprovado_por"] == "editor" and c["prazos"]["inscricao"]["fim"] == "2026-11-18"
    assert not (dados / "revisao" / "tj-pb-2026.json").exists()
    assert main(["validate", "--data", str(dados)]) == 0


def test_decisao_com_outro_edital_nao_vale(dados, extrair_falso, paginas_tjpb):
    extrair_falso[b"%PDF-edital"] = paginas_tjpb | {50: CONFLITO}
    _coletar(dados)
    _decidir(dados, {"schema_version": 1, "slug": "tj-pb-2026", "decidido_em": "2026-11-12T19:00:00-03:00",
                     "edital_sha256": "0" * 64, "acao": "decidir",
                     "campos": {"prazos.inscricao": {"acao": "ausente"}}})
    reg = _coletar(dados)
    assert reg.campos["prazos.inscricao"] == "revisao"
    assert any("edital mudou" in v for v in reg.violacoes)


def test_decisao_ausente_e_descartar(dados, extrair_falso, paginas_tjpb):
    extrair_falso[b"%PDF-edital"] = paginas_tjpb | {50: CONFLITO}
    _coletar(dados)
    rev = json.loads((dados / "revisao" / "tj-pb-2026.json").read_text(encoding="utf-8"))
    _decidir(dados, {"schema_version": 1, "slug": "tj-pb-2026", "decidido_em": "2026-11-12T19:00:00-03:00",
                     "edital_sha256": rev["edital_sha256"], "acao": "decidir",
                     "campos": {"prazos.inscricao": {"acao": "ausente"}}})
    reg = _coletar(dados)
    assert "prazos.inscricao" not in reg.campos or reg.campos["prazos.inscricao"] == "ausente"
    assert not (dados / "revisao" / "tj-pb-2026.json").exists()
    _decidir(dados, {"schema_version": 1, "slug": "tj-pb-2026", "decidido_em": "2026-11-12T19:30:00-03:00",
                     "acao": "descartar"}, nome="20261112-193000")
    assert _coletar(dados).situacao == "descartado"
