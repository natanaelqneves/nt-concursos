"""Parsers das fontes com páginas e respostas reais (coletadas em 12/11/2026)."""

from __future__ import annotations

import io
import json
import zipfile
from datetime import date
from pathlib import Path

from ntc.escopo import classificar
from ntc.sources import cebraspe, fgv, inlabs

F = Path(__file__).parent / "fixtures"


def test_fgv_lista_so_em_andamento():
    itens = fgv.parse_lista((F / "fgv" / "lista_p1.html").read_text(encoding="utf-8"))
    urls = [u for _, u in itens]
    assert "https://conhecimento.fgv.br/concursos/pcpr26" in urls
    assert "https://conhecimento.fgv.br/concursos/tjscservidor26" in urls
    # "realizados" ficam de fora
    assert "https://conhecimento.fgv.br/concursos/rfb22" not in urls
    assert len(itens) == 15


def test_fgv_concurso_edital_consolidado_e_retificacoes():
    cf = fgv.parse_concurso((F / "fgv" / "tjpb26.html").read_text(encoding="utf-8"),
                            "https://conhecimento.fgv.br/concursos/tjpb26")
    assert cf.titulo == "Concurso Público para Tribunal de Justiça do Estado da Paraíba"
    assert cf.ano == 2026
    ed = cf.edital
    assert ed.url.endswith("edital-retificado-tjpb_11.11.pdf")
    assert ed.publicado_em == date(2026, 11, 12)  # "Edital (retificado em 12/11/2026)"
    ret = [d for d in cf.documentos if d.tipo == "retificacao"]
    assert [d.publicado_em for d in ret] == [date(2026, 10, 26), date(2026, 10, 30), date(2026, 11, 12)]
    # resultados de isenção não são documentos de mudança
    assert not any("resultado" in d.titulo.lower() for d in cf.documentos)


def test_fgv_titulo_com_qualificador():
    cf = fgv.parse_concurso((F / "fgv" / "tjscjuiz26.html").read_text(encoding="utf-8"),
                            "https://conhecimento.fgv.br/concursos/tjscjuiz26")
    assert cf.id == "tjscjuiz26"
    assert cf.edital.url.endswith("edital-n-33-2026-edital-de-abertura-retificado.pdf")
    assert classificar(cf.titulo, *cf.contexto).sigla == "tj-sc"


def test_cebraspe_lista_ignora_encerrados():
    eventos = cebraspe.parse_lista(json.loads((F / "cebraspe" / "lista.json").read_text(encoding="utf-8")))
    nomes = {e["eventoURL"] for e in eventos}
    assert {"PC_PE_26", "SEAP_PE_26", "CD_26_PL", "CBM_AL_26"} <= nomes
    assert len(eventos) == 73


def test_cebraspe_evento_prefere_edital_atualizado():
    det = json.loads((F / "cebraspe" / "PC_PE_26.json").read_text(encoding="utf-8"))
    cf = cebraspe.parse_evento(det)
    assert cf.edital.titulo == "Edital nº 1 - Abertura - Atualizado conforme retificações"
    assert cf.edital.url.startswith("https://cdn.cebraspe.org.br/concursos/PC_PE_26/arquivos/")
    assert cf.edital.url.endswith(".pdf")
    ret = [d for d in cf.documentos if d.tipo == "retificacao"]
    assert {d.publicado_em for d in ret} >= {date(2026, 10, 21), date(2026, 11, 11)}
    assert classificar(cf.titulo, *cf.contexto).sigla == "pc-pe"


def test_cebraspe_polícia_penal_pelo_cargo():
    det = json.loads((F / "cebraspe" / "SEAP_PE_26.json").read_text(encoding="utf-8"))
    cf = cebraspe.parse_evento(det)
    c = classificar(cf.titulo, *cf.contexto)
    assert (c.categoria, c.uf, c.sigla) == ("seguranca", "PE", "policia-penal-pe")
    assert cf.edital is not None and cf.edital.titulo == "Edital nº 1 - Abertura"


def test_cebraspe_reabertura_e_cronograma_sao_mudanca():
    det = json.loads((F / "cebraspe" / "CBM_AL_26.json").read_text(encoding="utf-8"))
    cf = cebraspe.parse_evento(det)
    titulos = " | ".join(d.titulo for d in cf.documentos if d.tipo == "retificacao")
    assert "Reabertura das Inscrições" in titulos
    assert "alteração do cronograma" in titulos
    assert "Relação final" not in titulos


# INLABS: o serviço estava em manutenção em 12/11/2026. O XML abaixo segue a estrutura
# documentada pela Imprensa Nacional; trocar por um arquivo real assim que o serviço voltar.
XML_ABERTURA = """<xml><article id="1" idMateria="99001" pubName="DO3" artType="Edital" pubDate="12/11/2026"
artCategory="Ministério da Justiça e Segurança Pública/Polícia Rodoviária Federal/Diretoria de Gestão de Pessoas"
numberPage="88" pdfPage="http://pesquisa.in.gov.br/imprensa/jsp/visualiza/index.jsp?data=12/11/2026&amp;jornal=530&amp;pagina=88">
<body><Identifica><![CDATA[EDITAL Nº 1 - PRF, DE 11 DE NOVEMBRO DE 2026]]></Identifica>
<Texto><![CDATA[<p>CONCURSO PÚBLICO PARA PROVIMENTO DE VAGAS NO CARGO DE POLICIAL RODOVIÁRIO FEDERAL</p>
<p>O DIRETOR-GERAL torna pública a realização de concurso público...</p>]]></Texto></body></article></xml>"""
XML_HOMOLOGACAO = XML_ABERTURA.replace('idMateria="99001"', 'idMateria="99002"').replace(
    "EDITAL Nº 1 - PRF", "EDITAL Nº 9 - PRF - HOMOLOGAÇÃO DO RESULTADO FINAL")


def test_inlabs_descobre_abertura_federal():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("a.xml", XML_ABERTURA)
        z.writestr("b.xml", XML_HOMOLOGACAO)
    materias = list(inlabs.materias_do_zip(buf.getvalue()))
    assert len(materias) == 2
    aberturas = [m for m in materias if inlabs.eh_abertura_de_concurso(m)]
    assert [m.id for m in aberturas] == ["99001"]
    cf = inlabs.candidato(aberturas[0])
    assert cf.url.startswith("https://pesquisa.in.gov.br/")
    assert cf.data_dou == date(2026, 11, 12)
    cls = inlabs.no_escopo(cf)
    assert (cls.sigla, cls.esfera, cls.uf) == ("prf", "federal", "BR")


def test_fgv_edital_avulso_nao_substitui_o_de_abertura():
    cf = fgv.parse_concurso((F / "fgv" / "tjscservidor26.html").read_text(encoding="utf-8"),
                            "https://conhecimento.fgv.br/concursos/tjscservidor26")
    assert "Cumprimento de decisão" not in cf.edital.titulo
    avulso = [d for d in cf.documentos if "Cumprimento de decisão" in d.titulo]
    assert avulso and avulso[0].tipo == "retificacao"
    assert cf.ano == 2026
