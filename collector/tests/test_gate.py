from ntc.gate.evidencia import TextoDocumento
from ntc.model.schema import Concurso
from tests_helpers import regras

SHA = "a" * 64


def aplicar(gate, dados, textos):
    return gate.aplicar(Concurso.model_validate(dados), textos)


def test_exemplo_passa_inteiro(gate, novo, textos):
    r = aplicar(gate, novo(), textos)
    assert r.aprovado, r.violacoes
    assert r.concurso.prazos.isencao.status == "verificado"


def test_g1_host_fora_da_allowlist(gate, novo, textos):
    d = novo()
    d["documentos"][0]["url_final"] = "https://cursinho-qualquer.com.br/edital.pdf"
    r = aplicar(gate, d, textos)
    assert "G1" in regras(r)
    assert r.concurso.prazos.isencao.status == "revisao"


def test_g1_http_sem_tls(gate, novo, textos):
    d = novo()
    d["documentos"][0]["url_final"] = "http://exemplo.pb.gov.br/edital.pdf"
    assert "G1" in regras(aplicar(gate, d, textos))


def test_g1_dominio_parecido_nao_passa(gate, novo, textos):
    d = novo()
    d["documentos"][0]["url_final"] = "https://fakegov.br/edital.pdf"
    assert "G1" in regras(aplicar(gate, d, textos))


def test_g2_sem_texto_armazenado(gate, novo):
    assert "G2" in regras(aplicar(gate, novo(), {}))


def test_g3_trecho_inventado(gate, novo, textos):
    d = novo()
    d["evidencias"][0]["trecho"] = "A solicitação de isenção vai de 1 a 30 de novembro de 2026."
    d["prazos"]["isencao"]["inicio"] = "2026-11-01"
    d["prazos"]["isencao"]["fim"] = "2026-11-30"
    assert "G3" in regras(aplicar(gate, d, textos))


def test_g3_pagina_errada(gate, novo, textos):
    d = novo()
    d["evidencias"][0]["pagina"] = 3
    assert "G3" in regras(aplicar(gate, d, textos))


def test_g4_data_declarada_diferente_do_trecho(gate, novo, textos):
    d = novo()
    d["prazos"]["isencao"]["fim"] = "2026-11-15"
    assert "G4" in regras(aplicar(gate, d, textos))


def test_g4_trecho_de_outro_evento(gate, novo, textos):
    d = novo()
    d["evidencias"][0]["trecho"] = (
        "6.3 O resultado da análise dos pedidos de isenção será divulgado em 20/11/2026."
    )
    d["prazos"]["isencao"] = {
        "fim": "2026-11-20", "status": "verificado", "evidencia": "ev-1"
    }
    assert "G4" in regras(aplicar(gate, d, textos))


def test_g4_valor_da_taxa(gate, novo, textos):
    d = novo()
    d["taxa"]["valor"] = 120.0
    r = aplicar(gate, d, textos)
    assert "G4" in regras(r)
    assert r.concurso.taxa.status == "revisao"
    assert r.concurso.prazos.isencao.status == "verificado"  # falha é por campo


def test_g5_clausula_conflitante(gate, novo, paginas):
    paginas = dict(paginas)
    paginas[12] = "ANEXO II – CRONOGRAMA. Pedido de isenção da taxa: 10/11/2026 a 17/11/2026"
    r = aplicar(gate, novo(), {SHA: TextoDocumento(SHA, paginas, completo=True)})
    assert "G5" in regras(r)


def test_g5_so_roda_com_texto_completo(gate, novo, paginas):
    paginas = dict(paginas)
    paginas[12] = "Pedido de isenção da taxa: 10/11/2026 a 17/11/2026"
    r = aplicar(gate, novo(), {SHA: TextoDocumento(SHA, paginas, completo=False)})
    assert "G5" not in regras(r)


def test_g6_isencao_depois_das_inscricoes(gate, novo, textos):
    d = novo()
    d["prazos"]["inscricao"]["fim"] = "2026-11-12"
    d["prazos"]["inscricao"]["inicio"] = "2026-11-10"
    # o trecho não sustenta esse fim, então G4 já pega; G6 é testado com aprovação humana
    d["evidencias"][1]["aprovado_por"] = "revisor"
    d["evidencias"][1]["aprovado_em"] = "2026-11-11T20:00:00-03:00"
    r = aplicar(gate, d, textos)
    assert "G6" in regras(r)
    assert r.concurso.prazos.isencao.status == "revisao"


def test_g7_retificacao_posterior(gate, novo, textos):
    d = novo()
    sha_ret = "b" * 64
    d["documentos"].append({
        "id": "doc-2", "tipo": "retificacao",
        "url": "https://exemplo.pb.gov.br/retificacao-1.pdf",
        "url_final": "https://exemplo.pb.gov.br/retificacao-1.pdf",
        "sha256": sha_ret, "coletado_em": "2026-11-12T10:00:00-03:00", "fonte": "fgv",
    })
    textos = dict(textos)
    textos[sha_ret] = TextoDocumento(
        sha_ret, {1: "Fica prorrogado o prazo de solicitação de isenção até 21/11/2026."}
    )
    r = aplicar(gate, d, textos)
    assert ("G7", "prazos.isencao") in {(v.regra, v.campo) for v in r.violacoes}
    assert r.concurso.taxa.status == "verificado"


def test_g8_pdf_escaneado(gate, novo, paginas):
    r = aplicar(gate, novo(), {SHA: TextoDocumento(SHA, paginas, tem_texto=False)})
    assert "G8" in regras(r)


def test_aprovacao_humana_nao_dispensa_trecho_literal(gate, novo, textos):
    d = novo()
    d["evidencias"][0]["aprovado_por"] = "revisor"
    d["evidencias"][0]["aprovado_em"] = "2026-11-11T20:00:00-03:00"
    d["evidencias"][0]["trecho"] = "isenção de 1 a 30 de novembro de 2026, conforme edital."
    assert "G3" in regras(aplicar(gate, d, textos))


def test_gate_nao_altera_entrada(gate, novo):
    c = Concurso.model_validate(novo())
    gate.aplicar(c, {})
    assert c.prazos.isencao.status == "verificado"


def test_g7_retificacao_que_so_cita_a_taxa_nao_derruba(gate, novo, textos):
    d = novo()
    sha_ret = "b" * 64
    d["documentos"].append({
        **d["documentos"][0], "id": "doc-2", "tipo": "retificacao", "sha256": sha_ret,
        "coletado_em": "2026-11-12T10:00:00-03:00",
    })
    textos = dict(textos)
    textos[sha_ret] = TextoDocumento(
        sha_ret, {1: "Retificação do subitem 9.3: o conteúdo de Direito Penal passa a incluir a Lei nº 14.000. "
                     "Permanecem inalteradas as demais disposições, inclusive sobre a taxa de inscrição e a isenção."}
    )
    r = aplicar(gate, d, textos)
    assert "G7" not in regras(r)


def test_g7_retificacao_que_repete_as_mesmas_datas_nao_derruba(gate, novo, textos):
    d = novo()
    sha_ret = "b" * 64
    d["documentos"].append({
        **d["documentos"][0], "id": "doc-2", "tipo": "retificacao", "sha256": sha_ret,
        "coletado_em": "2026-11-12T10:00:00-03:00",
    })
    textos = dict(textos)
    textos[sha_ret] = TextoDocumento(
        sha_ret, {1: "6.1 A solicitação de isenção do pagamento da taxa de inscrição deverá ser feita de 10 a 14 de novembro de 2026."}
    )
    assert "G7" not in regras(aplicar(gate, d, textos))


def test_g7_errata_onde_se_le_derruba(gate, novo, textos):
    d = novo()
    sha_ret = "b" * 64
    d["documentos"].append({
        **d["documentos"][0], "id": "doc-2", "tipo": "retificacao", "sha256": sha_ret,
        "coletado_em": "2026-11-12T10:00:00-03:00",
    })
    textos = dict(textos)
    textos[sha_ret] = TextoDocumento(
        sha_ret, {1: "No subitem 5.1 (inscrições), onde se lê: 10/12/2026, leia-se: 17/12/2026."}
    )
    assert ("G7", "prazos.inscricao") in {(v.regra, v.campo) for v in aplicar(gate, d, textos).violacoes}


def test_g7_retificacao_anterior_pela_data_de_publicacao_nao_conta(gate, novo, textos):
    d = novo()
    sha_ret = "b" * 64
    d["documentos"][0]["publicado_em"] = "2026-11-12"
    d["documentos"].append({
        **d["documentos"][0], "id": "doc-2", "tipo": "retificacao", "sha256": sha_ret,
        "coletado_em": "2026-11-13T10:00:00-03:00", "publicado_em": "2026-11-12",
    })
    textos = dict(textos)
    textos[sha_ret] = TextoDocumento(sha_ret, {1: "Fica prorrogado o prazo de solicitação de isenção até 21/11/2026."})
    assert "G7" not in regras(aplicar(gate, d, textos))


def _com_etapa(novo, atividade="Aplicação das provas objetivas", datas="14/12/2026", tipo="prova_objetiva",
               fim="2026-12-14"):
    d = novo()
    d["evidencias"].append({
        "id": "ev-90", "campo": "etapas.0", "documento": "doc-1", "pagina": 1,
        "trecho": f"{atividade} — {datas}", "ancora": tipo, "metodo": "tabela:v1",
        "tabela": {"atividade": atividade, "datas": datas},
    })
    d["etapas"] = [{"tipo": tipo, "nome": atividade, "fim": fim, "status": "verificado", "evidencia": "ev-90"}]
    return d


def _textos_com(paginas, extra):
    p = dict(paginas)
    p[1] = p[1] + " " + extra
    return {SHA: TextoDocumento(SHA, p, completo=True)}


def test_etapa_conferida(gate, novo, paginas):
    t = _textos_com(paginas, "Aplicação das provas objetivas 14/12/2026")
    r = aplicar(gate, _com_etapa(novo), t)
    assert r.concurso.etapas[0].status == "verificado", r.violacoes


def test_etapa_com_data_ou_tipo_errado(gate, novo, paginas):
    t = _textos_com(paginas, "Aplicação das provas objetivas 14/12/2026")
    r = aplicar(gate, _com_etapa(novo, fim="2026-12-15"), t)
    assert r.concurso.etapas[0].status == "revisao"
    r = aplicar(gate, _com_etapa(novo, tipo="gabarito"), t)
    assert r.concurso.etapas[0].status == "revisao"
    r = aplicar(gate, _com_etapa(novo), {SHA: TextoDocumento(SHA, paginas, completo=True)})
    assert "G3" in regras(r)
