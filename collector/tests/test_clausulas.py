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


def test_ate_mesma_data_e_compativel_com_intervalo():
    from ntc.parse.clausulas import encontrar, intervalos_distintos, principal

    paginas = {
        3: "4.1 As inscrições para o Concurso Público estarão abertas no período das 16h do dia 20 de outubro de 2026 até às 16h do dia 18 de novembro de 2026.",
        10: "6.6.1 O candidato que declarar indevidamente ser pessoa com deficiência no requerimento de inscrição poderá corrigir a opção até 18 de novembro de 2026.",
    }
    cands = encontrar(paginas, "inscricao")
    assert len(cands) == 2
    assert len(intervalos_distintos(cands)) == 1
    p = principal(cands)
    assert p is not None and p.pagina == 3


def test_fim_diferente_continua_conflito():
    from ntc.parse.clausulas import encontrar, principal

    paginas = {
        3: "4.1 As inscrições estarão abertas de 20 de outubro de 2026 a 18 de novembro de 2026.",
        4: "4.9 O período de inscrição poderá ser feito até 25 de novembro de 2026.",
    }
    assert principal(encontrar(paginas, "inscricao")) is None


def test_datas_de_normas_citadas_nao_sao_prazo():
    from ntc.parse.clausulas import datas_de_prazo, encontrar, principal

    # Trechos reais do edital do TJSC (Juiz Substituto 2026), páginas 17 a 19
    paginas = {
        17: "10.2 A isenção mencionada no subitem 10.1 poderá ser solicitada no período das 16h do dia 19 de outubro de 2026 às 16h do dia 21 de outubro de 2026, horário oficial de Brasília/DF.",
        18: "10.567 de 07 de novembro de 1997, para obter a isenção deverão fazer o upload da imagem dos documentos originais comprobatórios.",
        19: "Os candidatos amparados pela Lei nº 11.289, de 27 de dezembro de 1999, para obter a isenção deverão fazer o upload da imagem dos documentos.",
    }
    assert datas_de_prazo(paginas[19]) == []
    p = principal(encontrar(paginas, "isencao"))
    assert p is not None and p.pagina == 17
