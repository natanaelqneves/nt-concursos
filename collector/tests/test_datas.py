from datetime import date

import pytest

from ntc.parse.datas import datas

D = date


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("até 14/11/2026", [D(2026, 11, 14)]),
        ("até 14.11.2026", [D(2026, 11, 14)]),
        ("em 5 de março de 2027", [D(2027, 3, 5)]),
        ("no dia 1º de dezembro de 2026", [D(2026, 12, 1)]),
        ("de 10 a 14 de novembro de 2026", [D(2026, 11, 10), D(2026, 11, 14)]),
        ("de 30 de novembro a 5 de dezembro de 2026", [D(2026, 11, 30), D(2026, 12, 5)]),
        ("de 15 de dezembro a 10 de janeiro de 2027", [D(2026, 12, 15), D(2027, 1, 10)]),
        ("de 10 a 14/11/2026", [D(2026, 11, 10), D(2026, 11, 14)]),
        ("de 10/11 a 14/11/2026", [D(2026, 11, 10), D(2026, 11, 14)]),
        ("de 10/11/2026 a 14/11/2026", [D(2026, 11, 10), D(2026, 11, 14)]),
        ("de 10/11/2026 até 14/11/2026", [D(2026, 11, 10), D(2026, 11, 14)]),
        ("entre 10 e 14 de novembro de 2026", [D(2026, 11, 10), D(2026, 11, 14)]),
        (
            "das 10h do dia 10/11/2026 às 23h59min do dia 14/11/2026",
            [D(2026, 11, 10), D(2026, 11, 14)],
        ),
    ],
)
def test_reconhece(texto, esperado):
    assert datas(texto) == esperado


@pytest.mark.parametrize(
    "texto",
    [
        "Edital nº 1/2026",
        "31/02/2026",
        "de 10 a 14 de novembro",  # sem ano em nenhum extremo
        "Lei nº 8.112, de 1990",
    ],
)
def test_ignora(texto):
    assert datas(texto) == []


def test_item_com_traco_nao_vira_intervalo():
    assert datas("item 4 - 10/11/2026") == [D(2026, 11, 10)]


def test_dias_e_sem_entre_nao_vira_intervalo():
    assert datas("nos dias 10 e 14/11/2026") == [D(2026, 11, 14)]


def test_ordem_de_aparicao():
    texto = "provas em 20/12/2026; inscrições de 10/11/2026 a 30/11/2026"
    assert datas(texto) == [D(2026, 12, 20), D(2026, 11, 10), D(2026, 11, 30)]
