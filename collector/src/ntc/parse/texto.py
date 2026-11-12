"""Normalização de texto usada igualmente pela extração e pelo gate.

Só espaços em branco são normalizados: o trecho guardado como evidência precisa
continuar sendo uma cópia literal do edital.
"""

import re

_ESPACOS = re.compile(r"\s+")


def normalizar(texto: str) -> str:
    return _ESPACOS.sub(" ", texto.replace(" ", " ")).strip()
