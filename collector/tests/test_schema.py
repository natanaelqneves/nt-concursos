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
