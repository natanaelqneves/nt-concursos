from datetime import date

from ntc.parse import etapas
from ntc.parse.tabela import Linha


def test_classificar():
    assert etapas.classificar("Aplicação das provas objetivas e discursivas") == "prova_objetiva"
    assert etapas.classificar("Divulgação do gabarito oficial preliminar das provas objetivas") == "gabarito"
    assert etapas.classificar("Resultado final no concurso") == "resultado_final"
    assert etapas.classificar("Homologação do resultado final do concurso") == "homologacao"
    assert etapas.classificar("Teste de Aptidão Física (TAF)") == "taf"
    # outros eventos e resultados parciais não são etapas
    assert etapas.classificar("Prazo para interposição de recurso contra o gabarito") is None
    assert etapas.classificar("Resultado preliminar da prova objetiva") is None
    assert etapas.classificar("Consulta aos locais de prova") is None
    assert etapas.classificar("Divulgação do padrão preliminar de respostas da prova discursiva") is None
    assert etapas.classificar(
        "Divulgação do edital de resultado final na avaliação biopsicossocial e no procedimento de heteroidentificação"
    ) == "resultado"
    assert etapas.classificar("Período de inscrições") is None


PAGINA = (
    "Cronograma previsto Período de inscrições 10/10/2026 a 30/10/2026 "
    "Aplicação das provas objetivas 14/12/2026 "
    "Divulgação do gabarito oficial preliminar 16/12/2026 "
    "Prazo para recurso contra o gabarito 17/12/2026 e 18/12/2026 "
    "Resultado final 20/02/2027"
)
INSC = (date(2026, 10, 10), date(2026, 10, 30))


def _linhas(grade=True):
    return [
        Linha(3, "Período de inscrições", "10/10/2026 a 30/10/2026", grade),
        Linha(3, "Aplicação das provas objetivas", "14/12/2026", grade),
        Linha(3, "Divulgação do gabarito oficial preliminar", "16/12/2026", grade),
        Linha(3, "Prazo para recurso contra o gabarito", "17/12/2026 e 18/12/2026", grade),
        Linha(3, "Resultado final", "20/02/2027", grade),
    ]


def test_encontrar_em_ordem():
    achadas = etapas.encontrar(_linhas(), {3: PAGINA}, INSC, 2026)
    assert [(e.tipo, e.fim) for e in achadas] == [
        ("prova_objetiva", date(2026, 12, 14)),
        ("gabarito", date(2026, 12, 16)),
        ("resultado_final", date(2027, 2, 20)),
    ]


def test_sem_grade_exige_linha_de_inscricao_conferida():
    assert etapas.encontrar(_linhas(grade=False), {3: PAGINA}, INSC, 2026)
    # inscrição da tabela diferente da verificada: tabela possivelmente desalinhada
    assert etapas.encontrar(_linhas(grade=False), {3: PAGINA}, (date(2026, 10, 1), date(2026, 10, 30)), 2026) == []


def test_celula_ausente_da_pagina_e_ano_distante():
    linhas = [Linha(3, "Aplicação das provas objetivas", "14/12/2026")]
    assert etapas.encontrar(linhas, {3: "outra coisa"}, INSC, 2026) == []
    linhas = [Linha(3, "Aplicação das provas objetivas", "14/12/2029")]
    assert etapas.encontrar(linhas, {3: "Aplicação das provas objetivas 14/12/2029"}, INSC, 2026) == []


def test_alterada_por():
    assert etapas.alterada_por({1: "Onde se lê: aplicação das provas objetivas em 14/12"}, "prova_objetiva")
    assert not etapas.alterada_por({1: "Retifica o anexo de vagas"}, "prova_objetiva")
