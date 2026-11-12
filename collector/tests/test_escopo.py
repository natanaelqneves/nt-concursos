"""Filtro de escopo com títulos reais das listas da FGV e da Cebraspe (12/11/2026)."""

import pytest

from ntc.escopo import classificar

DENTRO = [
    # (textos, categoria, esfera, uf, sigla)
    (["Concurso Público para Tribunal de Justiça do Estado da Paraíba"], "tribunal", "estadual", "PB", "tj-pb"),
    (["Concurso Público para o Tribunal de Justiça do Estado de Santa Catarina - Juiz Substituto (2026)"],
     "tribunal", "estadual", "SC", "tj-sc"),
    (["XVI Concurso Público para provimento de cargos de Juiz Federal Substituto da 5ª Região"],
     "tribunal", "federal", "PE", "trf5"),
    (["Concurso Público para o Tribunal Regional Federal da 6ª Região - TRF6"], "tribunal", "federal", "MG", "trf6"),
    (["Concurso Público para o Tribunal de Justiça do Distrito Federal e dos Territórios (TJDFT)"],
     "tribunal", "federal", "DF", "tjdft"),
    (["Concurso Público para a Polícia Civil do Estado do Paraná"], "seguranca", "estadual", "PR", "pc-pr"),
    (["Concurso Público para a Defensoria Pública do Estado do Rio de Janeiro"], "defensoria", "estadual", "RJ", "dpe-rj"),
    (["Concurso Público para a Defensoria Pública de Mato Grosso do Sul"], "defensoria", "estadual", "MS", "dpe-ms"),
    (["XXXIX Concurso para Ingresso na Classe Inicial da Carreira do Ministério Público do Estado do Rio de Janeiro"],
     "mp", "estadual", "RJ", "mp-rj"),
    (["Concurso Público para o Tribunal de Contas do Estado de Santa Catarina"], "controle", "estadual", "SC", "tce-sc"),
    (["Concurso Público para a Controladoria-Geral do Estado de Santa Catarina"], "controle", "estadual", "SC", "cge-sc"),
    (["Concurso Público para a Controladoria Geral da União"], "controle", "federal", "BR", "cgu"),
    (["Concurso Público para o Tribunal de Contas da União"], "controle", "federal", "BR", "tcu"),
    (["Concurso Público para o Corpo de Bombeiros Militar do Estado do Amazonas"], "seguranca", "estadual", "AM", "cbm-am"),
    (["Concurso Público para a Polícia Militar do Estado de São Paulo"], "seguranca", "estadual", "SP", "pm-sp"),
    # Cebraspe (nome abreviado + nome completo + cargos)
    (["PC PE 26", "PC PE 26", "Cargo 1: Agente de Polícia"], "seguranca", "estadual", "PE", "pc-pe"),
    (["SEAP PE 26", "SEAP PE 26", "CARGO DE POLICIAL PENAL DO ESTADO"], "seguranca", "estadual", "PE", "policia-penal-pe"),
    (["CÂMARA DOS DEPUTADOS 26 PLF", "CÂMARA DOS DEPUTADOS 26 POLICIAL LEGISLATIVO FEDERAL"],
     "seguranca", "federal", "BR", "camara-dos-deputados"),
    (["CBM AL 26", "Corpo de Bombeiros Militar do Estado de Alagoas"], "seguranca", "estadual", "AL", "cbm-al"),
    (["CGU 26 AFFC", "CGU 26 AFFC"], "controle", "federal", "BR", "cgu"),
    (["CGE AL 26"], "controle", "estadual", "AL", "cge-al"),
    (["TC DF 26 ANALISTA"], "controle", "estadual", "DF", "tcdf"),
    (["TCE AC 26"], "controle", "estadual", "AC", "tce-ac"),
    (["TCU 25 AUFC"], "controle", "federal", "BR", "tcu"),
    (["PF 25"], "seguranca", "federal", "BR", "pf"),
    (["PM DF 25 CFO"], "seguranca", "estadual", "DF", "pm-df"),
    (["PERICIA OFICIAL MA 26"], "seguranca", "estadual", "MA", "pci-ma"),
    (["PC DF 26 DELEGADO"], "seguranca", "estadual", "DF", "pc-df"),
]

FORA = [
    ["Concurso Público para a Prefeitura de Macaé"],
    ["Concurso Público para Conselho Regional de Psicologia da 5ª Região – CRP/05"],
    ["Concurso Público para Indústrias Nucleares do Brasil S.A. - INB"],
    ["Exame Nacional da Magistratura - ENAM (2026.2)"],
    ["Concurso Público de Provas e Títulos para Outorga de Delegações de Notas e de Registro do Estado do RS"],
    ["Processo Seletivo para Juiz Leigo do Tribunal de Justiça"],
    ["Concurso Público para a Procuradoria-Geral do Estado do Acre"],
    ["Concurso Público para a Assembleia Legislativa do Estado do Rio de Janeiro (ALERJ)"],
    ["CÂMARA DOS DEPUTADOS 26 ANALISTA", "CÂMARA DOS DEPUTADOS 26 ANALISTA"],
    ["Concurso Público para a Controladoria Geral do Município do Rio de Janeiro"],
    ["TJ CE 25 NOTÁRIOS"],
    ["SEAP MA 26 ESPECIALISTA E ASSISTENTE", "SEAP MA 26", "Especialista Penitenciário"],
    ["SEFAZ AL 26"],
    ["PREF PORTO ALEGRE RS 26"],
    ["Concurso Público para a Prefeitura Municipal do Salvador 2026 - Guarda Municipal"],
]


@pytest.mark.parametrize("textos,categoria,esfera,uf,sigla", DENTRO)
def test_dentro_do_escopo(textos, categoria, esfera, uf, sigla):
    r = classificar(*textos)
    assert r is not None, textos
    assert (r.categoria, r.esfera, r.uf, r.sigla) == (categoria, esfera, uf, sigla)


@pytest.mark.parametrize("textos", FORA)
def test_fora_do_escopo(textos):
    assert classificar(*textos) is None


def test_nome_do_orgao():
    r = classificar("Concurso Público para Tribunal de Justiça do Estado da Paraíba")
    assert r.orgao == "Tribunal de Justiça do Estado da Paraíba"
    assert classificar("PC PE 26").orgao == "Polícia Civil do Estado de Pernambuco"
