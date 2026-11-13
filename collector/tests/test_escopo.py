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
    ["Exame Nacional da Magistratura - ENAM (2026.2)"],
    ["Concurso Público de Provas e Títulos para Outorga de Delegações de Notas e de Registro do Estado do RS"],
    ["Processo Seletivo para Juiz Leigo do Tribunal de Justiça"],
    ["Concurso Público para a Controladoria Geral do Município do Rio de Janeiro"],
    ["TJ CE 25 NOTÁRIOS"],
    ["SEAP MA 26 ESPECIALISTA E ASSISTENTE", "SEAP MA 26", "Especialista Penitenciário"],
    ["Concurso Público para a Prefeitura de Macaé", "Cargo: Analista de Tecnologia da Informação"],
    ["Processo Seletivo Simplificado para a Secretaria da Educação do Estado de São Paulo - Ensino Médio Técnico"],
    # educação, saúde e gestão: municipais, temporários, penitenciária e assistência social ficam fora
    ["Concurso Público para a Secretaria Municipal de Educação do Município de São Lourenço da Mata"],
    ["Concurso Público para a Secretaria de Administração Penitenciária e Ressocialização do Estado da Bahia - SEAP-BA"],
    ["Concurso Público para a Secretaria de Estado da Assistência Social, Inclusão e Cidadania do Estado do Sergipe"],
    ["Secretaria de Saúde de São Paulo"],
    ["Serviço Militar Voluntário - Exército Brasileiro"],
    ["Processo Seletivo Simplificado para Professor Substituto da Universidade Federal do Pará"],
    ["IME Brasil"],
    ["UDESC 26"],
    ["PREF PORTO ALEGRE RS 26"],
    ["PREF PORTO VELHO 26 PROCURADOR"],
    ["Concurso Público para a Procuradoria-Geral do Município do Rio de Janeiro"],
    ["CAMARA MUNICIPAL BOAVISTA 25"],
    ["Ana Maria 26"],
    ["ARSAL 26"],
    ["DETRAN AL 26"],
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


NOVAS = [
    # (textos, categoria, esfera, uf, sigla, ti) — títulos reais da FGV e da Cebraspe (12/11/2026)
    (["Concurso Público para Indústrias Nucleares do Brasil S.A. - INB"], "estatal", "federal", "BR", "inb", False),
    (["Concurso Público para a Empresa de Tecnologia e Informações da Previdência - DATAPREV"],
     "estatal", "federal", "BR", "dataprev", True),
    (["Concurso Público para a NAV Brasil Serviços de Navegação Aérea S.A."], "estatal", "federal", "BR", "nav-brasil", False),
    (["Concurso Público para a Empresa Brasileira de Serviços Hospitalares - EBSERH - Área Médica"],
     "estatal", "federal", "BR", "ebserh", False),
    (["Concurso Público para a Companhia de Pesquisa de Recursos Minerais - CPRM"], "estatal", "federal", "BR", "sgb-cprm", False),
    (["CAESB 24"], "estatal", "estadual", "DF", "caesb", False),
    (["Concurso Público para Conselho Regional de Psicologia da 5ª Região – CRP/05"],
     "conselho", "federal", "BR", "conselho-regional-de-psicologia-da-5a-regiao", False),
    (["Concurso Público para o Conselho Regional de Medicina do Estado de São Paulo (CREMESP)"],
     "conselho", "federal", "SP", "conselho-regional-de-medicina-do-estado-de-sao-paulo", False),
    (["SEFAZ AL 26", "SEFAZ AL 26", "Cargo 4: Analista de Tecnologia da Informação"], "fiscal", "estadual", "AL", "sefaz-al", True),
    (["CÂMARA DOS DEPUTADOS 26 ANALISTA", "CÂMARA DOS DEPUTADOS 26 ANALISTA",
      "Analista Legislativo – Atribuição: Informática Legislativa"], "legislativo", "federal", "BR", "camara-dos-deputados", True),
    (["Concurso Público para Secretaria de Planejamento e Gestão do Estado do Rio de Janeiro – SEPLAG/RJ",
      "Analista de Planejamento e Orçamento – Tecnologia da Informação"], "executivo", "estadual", "RJ", "seplag-rj", True),
    # TI marcada também nas categorias de sempre
    (["TRF 3 26", "Analista Judiciário – Apoio Especializado – Análise de Sistemas de Informação"],
     "tribunal", "federal", "SP", "trf3", True),
]


@pytest.mark.parametrize("textos,categoria,esfera,uf,sigla,ti", NOVAS)
def test_estatais_conselhos_e_ti(textos, categoria, esfera, uf, sigla, ti):
    r = classificar(*textos)
    assert r is not None, textos
    assert (r.categoria, r.esfera, r.uf, r.sigla, "ti" in r.areas) == (categoria, esfera, uf, sigla, ti)


PUBLICO = [
    # (textos, categoria, esfera, uf, sigla) — títulos reais vistos na coleta de 12/11/2026
    (["SEFAZ AL 26"], "fiscal", "estadual", "AL", "sefaz-al"),
    (["SEFAZ AL 26", "SEFAZ AL 26", "Cargo 1: Auditor Fiscal da Receita Estadual"], "fiscal", "estadual", "AL", "sefaz-al"),
    (["SEFAZ RJ 25 AUDITOR"], "fiscal", "estadual", "RJ", "sefaz-rj"),
    (["Concurso Público Receita Federal do Brasil 2026"], "fiscal", "federal", "BR", "receita-federal"),
    (["Concurso Público para a Secretaria de Estado da Fazenda de Santa Catarina"], "fiscal", "estadual", "SC", "sefaz-sc"),
    (["PGE AL 26"], "advocacia", "estadual", "AL", "pge-al"),
    (["pgeac", "pgeac"], "advocacia", "estadual", "AC", "pge-ac"),
    (["Concurso Público para a Procuradoria-Geral do Estado do Acre"], "advocacia", "estadual", "AC", "pge-ac"),
    (["AGU 26"], "advocacia", "federal", "BR", "agu"),
    (["CÂMARA DOS DEPUTADOS 26 ANALISTA", "CÂMARA DOS DEPUTADOS 26 ANALISTA"], "legislativo", "federal", "BR", "camara-dos-deputados"),
    (["Concurso Público para a Assembleia Legislativa do Estado do Rio de Janeiro (ALERJ)"], "legislativo", "estadual", "RJ", "ale-rj"),
    (["alero25", "alero25"], "legislativo", "estadual", "RO", "ale-ro"),
    (["ALEPE 26 ANALISTA"], "legislativo", "estadual", "PE", "ale-pe"),
    (["ANTAQ 25 CF"], "executivo", "federal", "BR", "antaq"),
    (["IBGE 26"], "executivo", "federal", "BR", "ibge"),
    (["MRE 23"], "executivo", "federal", "BR", "mre"),
    (["Concurso Público para o Ministério da Gestão e da Inovação em Serviços Públicos"], "executivo", "federal", "BR",
     "ministerio-gestao-inovacao"),
    (["INB 26", "Indústrias Nucleares do Brasil", "empresa vinculada ao Ministério de Minas e Energia"], "estatal", "federal", "BR", "inb"),
    # polícia legislativa continua em segurança
    (["CD 26 PL", "CÂMARA DOS DEPUTADOS 26 POLICIAL LEGISLATIVO FEDERAL"], "seguranca", "federal", "BR", "camara-dos-deputados"),
]


@pytest.mark.parametrize("textos,categoria,esfera,uf,sigla", PUBLICO)
def test_fiscal_advocacia_executivo_legislativo(textos, categoria, esfera, uf, sigla):
    r = classificar(*textos)
    assert r is not None, textos
    assert (r.categoria, r.esfera, r.uf, r.sigla) == (categoria, esfera, uf, sigla)


SETORIAL = [
    # (textos, categoria, esfera, uf, sigla) — títulos reais da coleta de 12/11/2026 + casos-limite
    (["IFPA - INSTITUTO FEDERAL DE EDUCAÇÃO, CIÊNCIA E TECNOLOGIA DO PARÁ"], "educacao", "federal", "PA", "ifpa"),
    (["UFRN 26"], "educacao", "federal", "RN", "ufrn"),
    (["Universidade Federal de Pelotas - concurso técnico-administrativo"], "educacao", "federal", "BR",
     "universidade-federal-de-pelotas"),
    (["SEDUC AL 26"], "educacao", "estadual", "AL", "seduc-al"),
    (["SEDUC PI 25 PROFESSOR", "SEDUC PI 25", "Professor de Informática"], "educacao", "estadual", "PI", "seduc-pi"),
    (["Concurso Público para a Secretaria de Estado de Educação do Mato Grosso"], "educacao", "estadual", "MT", "seduc-mt"),
    (["Concurso Público para o Magistério Público da Secretaria de Estado da Educação, do Esporte e do Lazer (SEEC), "
      "do Rio Grande do Norte"], "educacao", "estadual", "RN", "seduc-rn"),
    (["SESAU AL 26"], "saude", "estadual", "AL", "ses-al"),
    (["SES DF 26"], "saude", "estadual", "DF", "ses-df"),
    (["Concurso Público para a Secretaria de Estado de Saúde do Tocantins e a Secretaria de Estado da Administração"],
     "saude", "estadual", "TO", "ses-to"),
    (["SECRETARIA DE ESTADO DA ADMINISTRAÇÃO DO ESTADO DO AMAPÁ - AP"], "executivo", "estadual", "AP", "gestao-ap"),
    (["Concurso Público para Secretaria de Planejamento e Gestão do Estado do Rio de Janeiro – SEPLAG/RJ"],
     "executivo", "estadual", "RJ", "seplag-rj"),
    (["Concurso Público para o Cargo Especialista em Políticas Públicas e Gestão Governamental - SEAD/SE"],
     "executivo", "estadual", "SE", "eppgg-se"),
    (["Concurso Público Unificado do Estado de Pernambuco - CPU-PE"], "executivo", "estadual", "PE", "cpu-pe"),
    (["CNU 2026"], "executivo", "federal", "BR", "cnu"),
    (["Concurso de Admissão à Escola de Sargentos das Armas 2026"], "militar", "federal", "BR", "essa"),
    (["ESSA 26"], "militar", "federal", "BR", "essa"),
    (["EEAR 2027"], "militar", "federal", "BR", "eear"),
    (["SEPLAG AL 26 ESPECIALISTA"], "executivo", "estadual", "AL", "seplag-al"),
    # o que já era de outra categoria continua lá
    (["HU BRASIL - EMPRESA BRASILEIRA DE SERVIÇOS HOSPITALARES"], "estatal", "federal", "BR", "ebserh"),
    (["Superior Tribunal Militar"], "tribunal", "federal", "BR", "stm"),
    (["PM PE 26"], "seguranca", "estadual", "PE", "pm-pe"),
]


@pytest.mark.parametrize("textos,categoria,esfera,uf,sigla", SETORIAL)
def test_educacao_saude_militar_gestao(textos, categoria, esfera, uf, sigla):
    r = classificar(*textos)
    assert r is not None, textos
    assert (r.categoria, r.esfera, r.uf, r.sigla) == (categoria, esfera, uf, sigla)


def test_nomes_com_acento():
    assert classificar("IFPA - INSTITUTO FEDERAL DE EDUCAÇÃO, CIÊNCIA E TECNOLOGIA DO PARÁ").orgao == "Instituto Federal do Pará"
    assert (classificar("SECRETARIA DE ESTADO DA ADMINISTRAÇÃO DO ESTADO DO AMAPÁ - AP").orgao
            == "Secretaria de Estado da Administração do Estado do Amapá")
