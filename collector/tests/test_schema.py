import pytest
from pydantic import ValidationError

from ntc.model.schema import Concurso


def test_exemplo_valido(novo):
    Concurso.model_validate(novo())


def test_verificado_sem_evidencia(novo):
    d = novo()
    d["prazos"]["isencao"]["evidencia"] = None
    with pytest.raises(ValidationError, match="sem evidência"):
        Concurso.model_validate(d)


def test_evidencia_inexistente(novo):
    d = novo()
    d["prazos"]["isencao"]["evidencia"] = "ev-99"
    with pytest.raises(ValidationError, match="inexistente"):
        Concurso.model_validate(d)


def test_evidencia_de_outro_campo(novo):
    d = novo()
    d["prazos"]["isencao"]["evidencia"] = "ev-2"
    with pytest.raises(ValidationError, match="outro campo"):
        Concurso.model_validate(d)


def test_documento_inexistente(novo):
    d = novo()
    d["evidencias"][0]["documento"] = "doc-9"
    with pytest.raises(ValidationError, match="documento inexistente"):
        Concurso.model_validate(d)


def test_inicio_depois_do_fim(novo):
    d = novo()
    d["prazos"]["isencao"]["inicio"] = "2026-11-20"
    with pytest.raises(ValidationError, match="posterior"):
        Concurso.model_validate(d)


def test_campo_desconhecido_e_recusado(novo):
    d = novo()
    d["palpite"] = "algo"
    with pytest.raises(ValidationError):
        Concurso.model_validate(d)


def test_revisao_sem_evidencia_e_aceito(novo):
    d = novo()
    d["prazos"]["isencao"] = {"status": "revisao"}
    Concurso.model_validate(d)


def test_porte_coerente_com_vagas(novo):
    d = novo()
    d["vagas_imediatas"] = {"valor": 150, "status": "verificado", "evidencia": "ev-3"}
    d["evidencias"][2]["campo"] = "vagas_imediatas"
    d["cargos"][0]["vagas"] = None
    d["porte"] = "grande"
    Concurso.model_validate(d)
    d["porte"] = "medio"
    with pytest.raises(ValidationError, match="porte"):
        Concurso.model_validate(d)


def test_porte_indefinido_sem_vagas_verificadas(novo):
    d = novo()
    d["vagas_imediatas"] = {"status": "revisao"}
    d["porte"] = "grande"
    with pytest.raises(ValidationError, match="porte"):
        Concurso.model_validate(d)


def test_federal_fora_do_judiciario_usa_br(novo):
    d = novo()
    d["categoria"], d["esfera"], d["uf"] = "seguranca", "federal", "DF"
    with pytest.raises(ValidationError, match="uf BR"):
        Concurso.model_validate(d)
    d["uf"] = "BR"
    Concurso.model_validate(d)


def test_estadual_nao_usa_br(novo):
    d = novo()
    d["uf"] = "BR"
    with pytest.raises(ValidationError, match="UF"):
        Concurso.model_validate(d)


def test_categoria_obrigatoria(novo):
    d = novo()
    del d["categoria"]
    with pytest.raises(ValidationError):
        Concurso.model_validate(d)


def test_evidencia_de_tabela_exige_trecho_composto(novo):
    d = novo()
    linha = {"atividade": "Período de solicitação de inscrições", "datas": "10/11 a 10/12/2026"}
    d["evidencias"][1]["tabela"] = linha
    d["evidencias"][1]["trecho"] = "Período de solicitação de inscrições — 10/11 a 10/12/2026"
    Concurso.model_validate(d)
    d["evidencias"][1]["trecho"] = "Período de solicitação de inscrições: 10/11 a 10/12/2026"
    with pytest.raises(ValidationError, match="atividade — datas"):
        Concurso.model_validate(d)


def test_categoria_outro_exige_area_ti(novo):
    d = novo()
    d["categoria"] = "outro"
    with pytest.raises(ValidationError, match="TI"):
        Concurso.model_validate(d)
    d["areas"] = ["ti"]
    Concurso.model_validate(d)


def test_conselho_federal_pode_ter_uf_da_sede(novo):
    d = novo()
    d["categoria"], d["esfera"], d["uf"] = "conselho", "federal", "SP"
    Concurso.model_validate(d)
    d["categoria"] = "estatal"
    with pytest.raises(ValidationError, match="uf BR"):
        Concurso.model_validate(d)


def test_esfera_municipal(concurso_dict):
    import pytest
    from ntc.model.schema import Concurso

    d = dict(concurso_dict, esfera="municipal", categoria="guarda", municipio="João Pessoa", uf="PB")
    Concurso.model_validate(d)
    with pytest.raises(ValueError):
        Concurso.model_validate(dict(d, municipio=None))
    with pytest.raises(ValueError):
        Concurso.model_validate(dict(d, categoria="tribunal"))
    with pytest.raises(ValueError):
        Concurso.model_validate(dict(d, esfera="estadual", municipio=None))  # guarda é só municipal
    Concurso.model_validate(dict(d, esfera="estadual", categoria="transito", municipio=None))


def test_validade_regras():
    import pytest
    from ntc.model.validade import Validade

    base = {
        "slug": "gcm-recife-2022", "titulo": "Guarda Civil do Recife: validade termina em março",
        "orgao": "Guarda Civil Municipal do Recife", "categoria": "guarda", "esfera": "municipal",
        "uf": "PE", "municipio": "Recife", "resumo": "x" * 90,
        "fatos": [{"campo": "validade", "texto": "Validade até 10/3/2027", "fim": "2027-03-10", "fontes": ["f-1"]}],
        "fontes": [{"id": "f-1", "nome": "Diário Oficial do Recife", "url": "https://www.recife.pe.gov.br/x",
                    "oficial": True, "consultado_em": "2026-11-13"}],
        "validade_ate": "2027-03-10", "apurado_em": "2026-11-13T15:00:00-03:00",
    }
    Validade.model_validate(base)
    with pytest.raises(ValueError):
        Validade.model_validate(dict(base, validade_ate="2027-03-11"))
    with pytest.raises(ValueError):  # uma só fonte não oficial
        Validade.model_validate(dict(base, fontes=[dict(base["fontes"][0], oficial=False)]))


def _etapa(**kw):
    base = {"tipo": "prova_objetiva", "nome": "Aplicação das provas objetivas", "fim": "2026-12-14",
            "status": "revisao"}
    return {**base, **kw}


def test_etapas_regras(novo):
    d = novo()
    d["etapas"] = [_etapa(), _etapa(tipo="gabarito", nome="Gabarito preliminar", fim="2026-12-15")]
    Concurso.model_validate(d)
    d["etapas"] = [_etapa(), _etapa()]
    with pytest.raises(ValidationError, match="repetidas"):
        Concurso.model_validate(d)
    d["etapas"] = [_etapa(fim="2027-01-10"), _etapa(tipo="gabarito", nome="Gabarito", fim="2026-12-15")]
    with pytest.raises(ValidationError, match="ordem"):
        Concurso.model_validate(d)
    d["etapas"] = [_etapa(status="verificado", fim=None, evidencia="ev-1")]
    with pytest.raises(ValidationError, match="sem data"):
        Concurso.model_validate(d)
    d["etapas"] = [_etapa(status="verificado")]
    with pytest.raises(ValidationError, match="sem evidência"):
        Concurso.model_validate(d)


def test_etapa_verificada_exige_evidencia_do_proprio_caminho(novo):
    d = novo()
    ev = dict(d["evidencias"][0], id="ev-90", campo="etapas.0")
    d["evidencias"].append(ev)
    d["etapas"] = [_etapa(status="verificado", evidencia="ev-90")]
    Concurso.model_validate(d)
    d["etapas"][0]["evidencia"] = d["evidencias"][0]["id"]
    with pytest.raises(ValidationError, match="outro campo"):
        Concurso.model_validate(d)
