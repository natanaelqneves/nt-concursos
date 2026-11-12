def regras(resultado) -> set[str]:
    return {v.regra for v in resultado.violacoes}
