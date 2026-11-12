from datetime import date

from ntc.parse.clausulas import encontrar, intervalos_distintos, segmentos


def test_isencao_ignora_resultado(paginas):
    cands = encontrar(paginas, "isencao")
    assert len(cands) == 1
    c = cands[0]
    assert c.pagina == 7
    assert (c.inicio, c.fim) == (date(2026, 11, 10), date(2026, 11, 14))
    assert "resultado" not in c.trecho.lower()


def test_inscricao_nao_confunde_com_isencao(paginas):
    cands = encontrar(paginas, "inscricao")
    assert intervalos_distintos(cands) == {(date(2026, 11, 10), date(2026, 12, 10))}


def test_cronograma_em_tabela_vira_linhas():
    texto = (
        "Solicitação de isenção 10/11/2026 a 14/11/2026 "
        "Resultado da isenção 20/11/2026 "
        "Inscrições 10/11/2026 a 10/12/2026"
    )
    segs = segmentos(texto)
    assert len(segs) == 3
    assert encontrar({1: texto}, "isencao")[0].fim == date(2026, 11, 14)


def test_duas_clausulas_conflitantes_sao_detectadas():
    paginas = {
        2: "A solicitação de isenção poderá ser feita de 10 a 14 de novembro de 2026.",
        9: "Cronograma. Pedido de isenção da taxa: 10/11/2026 a 17/11/2026",
    }
    assert len(intervalos_distintos(encontrar(paginas, "isencao"))) == 2


def test_trecho_longo_e_recortado():
    texto = "x" * 900 + " pedido de isenção até 14/11/2026 " + "y" * 900
    c = encontrar({1: texto}, "isencao")[0]
    assert len(c.trecho) <= 500
    assert c.fim == date(2026, 11, 14)
