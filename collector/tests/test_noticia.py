"""Notícias apuradas em fontes de imprensa: regras de fonte do schema."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ntc.model.noticia import Noticia

DADOS = Path(__file__).resolve().parents[2] / "data" / "noticias"


@pytest.fixture
def base() -> dict:
    return json.loads((DADOS / "pm-sp-2026-aluno-soldado.json").read_text(encoding="utf-8"))


def test_noticias_do_repositorio_sao_validas():
    arquivos = sorted(DADOS.glob("*.json"))
    assert arquivos
    for a in arquivos:
        n = Noticia.model_validate_json(a.read_text(encoding="utf-8"))
        assert n.slug == a.stem


def test_mesmo_orgao_com_grafia_diferente_e_duplicata():
    from ntc.cli import chave_duplicata_noticia

    a = Noticia.model_validate_json((DADOS / "prefeitura-parari-2026.json").read_text(encoding="utf-8"))
    b = a.model_copy(update={"municipio": "Parári", "orgao": "Prefeitura Municipal de Parári"})
    assert chave_duplicata_noticia(a) == chave_duplicata_noticia(b)


def test_fato_com_uma_fonte_nao_oficial_e_aceito(base):
    d = copy.deepcopy(base)
    d["fatos"][2]["fontes"] = ["f-1"]
    Noticia.model_validate(d)


def test_fato_sem_fonte_e_recusado(base):
    d = copy.deepcopy(base)
    d["fatos"][2]["fontes"] = []
    with pytest.raises(ValidationError):
        Noticia.model_validate(d)


def test_uma_fonte_oficial_basta(base):
    d = copy.deepcopy(base)
    d["fontes"][0]["oficial"] = True
    d["fatos"][2]["fontes"] = ["f-1"]
    Noticia.model_validate(d)


def test_expira_no_fim_das_inscricoes(base):
    d = copy.deepcopy(base)
    d["expira_em"] = "2026-12-31"
    with pytest.raises(ValidationError, match="expira_em"):
        Noticia.model_validate(d)


def test_fonte_sem_uso_e_recusada(base):
    d = copy.deepcopy(base)
    d["fontes"].append({**d["fontes"][0], "id": "f-9"})
    with pytest.raises(ValidationError, match="sem fato"):
        Noticia.model_validate(d)
