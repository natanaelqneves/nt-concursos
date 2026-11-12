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
