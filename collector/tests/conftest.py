from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from ntc.fetch.allowlist import Allowlist
from ntc.gate.evidencia import Gate, TextoDocumento

FIXTURES = Path(__file__).parent / "fixtures"
RAIZ = Path(__file__).resolve().parents[2]
SHA = "a" * 64


@pytest.fixture
def allowlist() -> Allowlist:
    return Allowlist.carregar(RAIZ / "data" / "fontes.yaml")


@pytest.fixture
def gate(allowlist: Allowlist) -> Gate:
    return Gate(allowlist)


@pytest.fixture
def paginas() -> dict[int, str]:
    bruto = json.loads((FIXTURES / "edital_exemplo.json").read_text(encoding="utf-8"))
    return {int(k): v for k, v in bruto["paginas"].items()}


@pytest.fixture
def textos(paginas: dict[int, str]) -> dict[str, TextoDocumento]:
    return {SHA: TextoDocumento(SHA, paginas, completo=True)}


@pytest.fixture
def concurso_dict() -> dict:
    return json.loads((FIXTURES / "concurso_exemplo.json").read_text(encoding="utf-8"))


@pytest.fixture
def novo(concurso_dict: dict):
    """Fábrica: devolve uma cópia profunda do concurso de exemplo para alterar."""
    return lambda: copy.deepcopy(concurso_dict)
