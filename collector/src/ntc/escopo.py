"""Filtro de escopo: decide se um concurso é de um órgão coberto pelo site.

Escopo (docs/ARQUITETURA.md, seção 11): órgãos federais e estaduais das categorias
tribunal, controle, mp, defensoria e seguranca. Municipais, conselhos profissionais,
estatais, outorgas de cartório, exames e processos seletivos ficam fora.

A classificação usa só texto que a fonte publica sobre o concurso (título, nome
abreviado da banca, cargos, hierarquia do DOU). Regras explícitas e testadas, sem
heurística estatística: o que não casa com nenhuma regra fica fora do escopo e vai
para o log da execução, onde pode ser conferido.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# (nome, preposição) — "Tribunal de Justiça do Estado da Paraíba"
ESTADOS: dict[str, tuple[str, str]] = {
    "AC": ("Acre", "do"), "AL": ("Alagoas", "de"), "AP": ("Amapá", "do"),
    "AM": ("Amazonas", "do"), "BA": ("Bahia", "da"), "CE": ("Ceará", "do"),
    "DF": ("Distrito Federal", "do"), "ES": ("Espírito Santo", "do"), "GO": ("Goiás", "de"),
    "MA": ("Maranhão", "do"), "MT": ("Mato Grosso", "de"), "MS": ("Mato Grosso do Sul", "de"),
    "MG": ("Minas Gerais", "de"), "PA": ("Pará", "do"), "PB": ("Paraíba", "da"),
    "PR": ("Paraná", "do"), "PE": ("Pernambuco", "de"), "PI": ("Piauí", "do"),
    "RJ": ("Rio de Janeiro", "do"), "RN": ("Rio Grande do Norte", "do"),
    "RS": ("Rio Grande do Sul", "do"), "RO": ("Rondônia", "de"), "RR": ("Roraima", "de"),
    "SC": ("Santa Catarina", "de"), "SP": ("São Paulo", "de"), "SE": ("Sergipe", "de"),
    "TO": ("Tocantins", "do"),
}

# Sedes dos tribunais regionais federais (a UF do contrato é a da sede)
SEDE_TRF = {1: "DF", 2: "RJ", 3: "SP", 4: "RS", 5: "PE", 6: "MG"}
SEDE_TRT = {
    1: "RJ", 2: "SP", 3: "MG", 4: "RS", 5: "BA", 6: "PE", 7: "CE", 8: "PA", 9: "PR", 10: "DF",
    11: "AM", 12: "SC", 13: "PB", 14: "RO", 15: "SP", 16: "MA", 17: "ES", 18: "GO", 19: "AL",
    20: "SE", 21: "RN", 22: "PI", 23: "MT", 24: "MS",
}


@dataclass(frozen=True)
class Classificacao:
    categoria: str
    esfera: str
    uf: str
    orgao: str
    sigla: str  # base do slug, já em minúsculas e com hífens


def sem_acento(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _no_estado(uf: str) -> str:
    nome, prep = ESTADOS[uf]
    return "do Distrito Federal" if uf == "DF" else f"do Estado {prep} {nome}"


# Ordem: nomes mais longos primeiro ("Mato Grosso do Sul" antes de "Mato Grosso").
_ESTADO_RE = re.compile(
    r"\b(?:estado\s+)?d[aoe]\s+("
    + "|".join(sorted((re.escape(sem_acento(n)) for n, _ in ESTADOS.values()), key=len, reverse=True))
    + r")\b"
)
_UF_POR_NOME = {sem_acento(n): uf for uf, (n, _) in ESTADOS.items()}


def uf_por_nome(t: str, depois_de: int = 0) -> str | None:
    m = _ESTADO_RE.search(t, depois_de)
    return _UF_POR_NOME[m.group(1)] if m else None


_FORA = re.compile(
    r"notaria|notarial|notarios|outorga de delega|cartorio|registro de imoveis|"
    r"\bexame\b|vestibular|residencia|juiz leigo|conciliador|estagi|"
    r"processo seletivo|selecao simplificada|temporari"
)
_MUNICIPAL = re.compile(r"prefeitura|camara municipal|\bmunicipal\b|do municipio|guarda municipal")
_POLICIA_LEGISLATIVA = re.compile(r"policia legislativa|policial legislativo|\bplf\b")
_POLICIA_PENAL = re.compile(r"policia penal|policial penal|policiais penais")


def _c(categoria: str, esfera: str, uf: str, orgao: str, sigla: str) -> Classificacao:
    return Classificacao(categoria, esfera, uf, orgao, sigla)


def _estadual(categoria: str, prefixo: str, sigla: str, t: str, pos: int) -> Classificacao | None:
    uf = uf_por_nome(t, pos)
    if uf is None:
        return None
    return _c(categoria, "estadual", uf, f"{prefixo} {_no_estado(uf)}", f"{sigla}-{uf.lower()}")


def _por_nome(t: str) -> Classificacao | None:
    """Regras sobre nomes por extenso (FGV, DOU, nome completo da Cebraspe)."""
    federais = [
        (r"supremo tribunal federal", "tribunal", "Supremo Tribunal Federal", "stf"),
        (r"superior tribunal de justica", "tribunal", "Superior Tribunal de Justiça", "stj"),
        (r"superior tribunal militar", "tribunal", "Superior Tribunal Militar", "stm"),
        (r"tribunal superior do trabalho", "tribunal", "Tribunal Superior do Trabalho", "tst"),
        (r"tribunal superior eleitoral", "tribunal", "Tribunal Superior Eleitoral", "tse"),
        (r"conselho superior da justica do trabalho", "tribunal",
         "Conselho Superior da Justiça do Trabalho", "csjt"),
        (r"conselho da justica federal", "tribunal", "Conselho da Justiça Federal", "cjf"),
        (r"conselho nacional de justica", "tribunal", "Conselho Nacional de Justiça", "cnj"),
        (r"tribunal de contas da uniao", "controle", "Tribunal de Contas da União", "tcu"),
        (r"controladoria[- ]geral da uniao", "controle", "Controladoria-Geral da União", "cgu"),
        (r"ministerio publico do distrito federal e territorios", "mp",
         "Ministério Público do Distrito Federal e Territórios", "mpdft"),
        (r"ministerio publico do trabalho", "mp", "Ministério Público do Trabalho", "mpt"),
        (r"ministerio publico militar", "mp", "Ministério Público Militar", "mpm"),
        (r"ministerio publico federal", "mp", "Ministério Público Federal", "mpf"),
        (r"ministerio publico da uniao", "mp", "Ministério Público da União", "mpu"),
        (r"defensoria publica da uniao", "defensoria", "Defensoria Pública da União", "dpu"),
        (r"policia rodoviaria federal", "seguranca", "Polícia Rodoviária Federal", "prf"),
        (r"policia penal federal|secretaria nacional de politicas penais", "seguranca",
         "Polícia Penal Federal", "ppf"),
        (r"policia federal", "seguranca", "Polícia Federal", "pf"),
    ]
    for padrao, categoria, orgao, sigla in federais:
        if re.search(padrao, t):
            return _c(categoria, "federal", "BR", orgao, sigla)

    m = re.search(r"tribunal regional federal da (\d)|juiz federal substituto da (\d)", t)
    if m:
        n = int(m.group(1) or m.group(2))
        if n in SEDE_TRF:
            return _c("tribunal", "federal", SEDE_TRF[n], f"Tribunal Regional Federal da {n}ª Região", f"trf{n}")
    m = re.search(r"tribunal regional do trabalho da (\d{1,2})", t)
    if m and int(m.group(1)) in SEDE_TRT:
        n = int(m.group(1))
        return _c("tribunal", "federal", SEDE_TRT[n], f"Tribunal Regional do Trabalho da {n}ª Região", f"trt{n}")
    m = re.search(r"tribunal regional eleitoral", t)
    if m:
        uf = uf_por_nome(t, m.end())
        if uf:
            nome, prep = ESTADOS[uf]
            return _c("tribunal", "federal", uf, f"Tribunal Regional Eleitoral {prep} {nome}", f"tre-{uf.lower()}")

    if re.search(r"tribunal de justica do distrito federal", t):
        return _c("tribunal", "federal", "DF", "Tribunal de Justiça do Distrito Federal e dos Territórios", "tjdft")
    m = re.search(r"tribunal de justica militar", t)
    if m:
        return _estadual("tribunal", "Tribunal de Justiça Militar", "tjm", t, m.end())
    m = re.search(r"tribunal de justica", t)
    if m:
        return _estadual("tribunal", "Tribunal de Justiça", "tj", t, m.end())

    m = re.search(r"tribunal de contas dos municipios", t)
    if m:
        return _estadual("controle", "Tribunal de Contas dos Municípios", "tcm", t, m.end())
    if re.search(r"tribunal de contas do municipio", t):
        return None
    if re.search(r"tribunal de contas do distrito federal", t):
        return _c("controle", "estadual", "DF", "Tribunal de Contas do Distrito Federal", "tcdf")
    m = re.search(r"tribunal de contas", t)
    if m:
        return _estadual("controle", "Tribunal de Contas", "tce", t, m.end())
    if re.search(r"controladoria[- ]geral do municipio", t):
        return None
    m = re.search(r"controladoria[- ]geral|auditoria[- ]geral do estado", t)
    if m:
        return _estadual("controle", "Controladoria-Geral", "cge", t, m.end())

    m = re.search(r"ministerio publico de contas", t)
    if m:
        return _estadual("mp", "Ministério Público de Contas", "mpc", t, m.end())
    m = re.search(r"ministerio publico", t)
    if m:
        return _estadual("mp", "Ministério Público", "mp", t, m.end())
    m = re.search(r"defensoria publica", t)
    if m:
        return _estadual("defensoria", "Defensoria Pública", "dpe", t, m.end())

    m = re.search(r"policia civil", t)
    if m:
        return _estadual("seguranca", "Polícia Civil", "pc", t, m.end())
    m = re.search(r"policia militar", t)
    if m:
        return _estadual("seguranca", "Polícia Militar", "pm", t, m.end())
    m = re.search(r"corpo de bombeiros|bombeiros militar", t)
    if m:
        return _estadual("seguranca", "Corpo de Bombeiros Militar", "cbm", t, m.end())
    m = re.search(
        r"policia cientifica|pericia oficial|policia tecnico[- ]cientifica|instituto geral de pericias", t
    )
    if m:
        return _estadual("seguranca", "Polícia Científica", "pci", t, m.end())
    if _POLICIA_PENAL.search(t):
        return _estadual("seguranca", "Polícia Penal", "policia-penal", t, 0)

    if _POLICIA_LEGISLATIVA.search(t):
        if re.search(r"camara dos deputados", t):
            return _c("seguranca", "federal", "BR", "Câmara dos Deputados (Polícia Legislativa)", "camara-dos-deputados")
        if re.search(r"senado federal", t):
            return _c("seguranca", "federal", "BR", "Senado Federal (Polícia Legislativa)", "senado")
        m = re.search(r"assembleia legislativa|camara legislativa", t)
        if m:
            uf = uf_por_nome(t, m.end())
            if uf:
                orgao = "Câmara Legislativa do Distrito Federal" if uf == "DF" else f"Assembleia Legislativa {_no_estado(uf)}"
                return _c("seguranca", "estadual", uf, f"{orgao} (Polícia Legislativa)", f"ale-{uf.lower()}")
    return None


# Siglas usadas pela Cebraspe no nome abreviado ("PC PE 26", "TCE AC 26", "CGU 26 AFFC")
_SIGLAS_ESTADUAIS = {
    "tj": ("tribunal", "Tribunal de Justiça", "tj"),
    "tjm": ("tribunal", "Tribunal de Justiça Militar", "tjm"),
    "tce": ("controle", "Tribunal de Contas", "tce"),
    "tcm": ("controle", "Tribunal de Contas dos Municípios", "tcm"),
    "cge": ("controle", "Controladoria-Geral", "cge"),
    "mp": ("mp", "Ministério Público", "mp"),
    "mpe": ("mp", "Ministério Público", "mp"),
    "mpc": ("mp", "Ministério Público de Contas", "mpc"),
    "dpe": ("defensoria", "Defensoria Pública", "dpe"),
    "dp": ("defensoria", "Defensoria Pública", "dpe"),
    "pc": ("seguranca", "Polícia Civil", "pc"),
    "pm": ("seguranca", "Polícia Militar", "pm"),
    "cbm": ("seguranca", "Corpo de Bombeiros Militar", "cbm"),
    "pp": ("seguranca", "Polícia Penal", "policia-penal"),
    "ppe": ("seguranca", "Polícia Penal", "policia-penal"),
    "pci": ("seguranca", "Polícia Científica", "pci"),
    "politec": ("seguranca", "Polícia Científica", "pci"),
    "igp": ("seguranca", "Polícia Científica", "pci"),
    "pericia oficial": ("seguranca", "Polícia Científica", "pci"),
}
_SIGLAS_FEDERAIS = {
    "stf": ("tribunal", "Supremo Tribunal Federal"),
    "stj": ("tribunal", "Superior Tribunal de Justiça"),
    "stm": ("tribunal", "Superior Tribunal Militar"),
    "tst": ("tribunal", "Tribunal Superior do Trabalho"),
    "tse": ("tribunal", "Tribunal Superior Eleitoral"),
    "tcu": ("controle", "Tribunal de Contas da União"),
    "cgu": ("controle", "Controladoria-Geral da União"),
    "mpu": ("mp", "Ministério Público da União"),
    "mpf": ("mp", "Ministério Público Federal"),
    "mpt": ("mp", "Ministério Público do Trabalho"),
    "mpm": ("mp", "Ministério Público Militar"),
    "mpdft": ("mp", "Ministério Público do Distrito Federal e Territórios"),
    "dpu": ("defensoria", "Defensoria Pública da União"),
    "pf": ("seguranca", "Polícia Federal"),
    "prf": ("seguranca", "Polícia Rodoviária Federal"),
    "ppf": ("seguranca", "Polícia Penal Federal"),
}
_UFS = {uf.lower() for uf in ESTADOS}


def _por_sigla(abreviado: str, contexto: str) -> Classificacao | None:
    t = re.sub(r"[^a-z0-9 ]", " ", sem_acento(abreviado))
    tokens = t.split()
    if not tokens:
        return None
    # "TC DF" é o Tribunal de Contas do DF
    if tokens[:2] == ["tc", "df"]:
        return _c("controle", "estadual", "DF", "Tribunal de Contas do Distrito Federal", "tcdf")
    m = re.match(r"(trf|trt)\s*(\d{1,2})\b", t)
    if m:
        n = int(m.group(2))
        sedes = SEDE_TRF if m.group(1) == "trf" else SEDE_TRT
        if n in sedes:
            nome = "Federal" if m.group(1) == "trf" else "do Trabalho"
            return _c("tribunal", "federal", sedes[n], f"Tribunal Regional {nome} da {n}ª Região", f"{m.group(1)}{n}")
    if tokens[0] == "tre" and len(tokens) > 1 and tokens[1] in _UFS:
        uf = tokens[1].upper()
        nome, prep = ESTADOS[uf]
        return _c("tribunal", "federal", uf, f"Tribunal Regional Eleitoral {prep} {nome}", f"tre-{uf.lower()}")
    if tokens[0] in _SIGLAS_FEDERAIS:
        categoria, orgao = _SIGLAS_FEDERAIS[tokens[0]]
        return _c(categoria, "federal", "BR", orgao, tokens[0])
    for chave in sorted(_SIGLAS_ESTADUAIS, key=len, reverse=True):
        partes = chave.split()
        if tokens[: len(partes)] == partes and len(tokens) > len(partes) and tokens[len(partes)] in _UFS:
            categoria, prefixo, sigla = _SIGLAS_ESTADUAIS[chave]
            uf = tokens[len(partes)].upper()
            return _c(categoria, "estadual", uf, f"{prefixo} {_no_estado(uf)}", f"{sigla}-{uf.lower()}")
    # Secretarias de administração penitenciária: só com cargo de policial penal
    if tokens[0] in {"seap", "sejus", "sejusp", "seape", "sap", "seres", "sejuc"} and len(tokens) > 1:
        if tokens[1] in _UFS and _POLICIA_PENAL.search(contexto):
            uf = tokens[1].upper()
            return _c("seguranca", "estadual", uf, f"Polícia Penal {_no_estado(uf)}", f"policia-penal-{uf.lower()}")
    return None


def classificar(*textos: str | None) -> Classificacao | None:
    """Classifica um concurso a partir dos textos da fonte. O primeiro texto é o título
    (ou nome abreviado); os demais (cargos, nome completo, hierarquia) dão contexto."""
    partes = [x for x in textos if x]
    if not partes:
        return None
    t = sem_acento(" | ".join(partes))
    # Exclusões só em textos curtos (título, nome completo, cargos): o corpo de um edital
    # fala de "exame médico" ou "município" sem que o concurso seja exame ou municipal.
    curtos = sem_acento(" | ".join(x for x in partes if len(x) <= 200))
    if _FORA.search(curtos):
        return None
    if _MUNICIPAL.search(curtos) and not re.search(r"tribunal de contas dos municipios", curtos):
        return None
    for texto in partes:
        r = _por_nome(sem_acento(texto))
        if r is not None:
            return _confirmar(r, t)
    for texto in partes:
        r = _por_sigla(texto, t)
        if r is not None:
            return _confirmar(r, t)
    return None


def _confirmar(r: Classificacao, t: str) -> Classificacao | None:
    # Câmara, Senado e assembleias só entram pelo concurso de polícia legislativa.
    if re.search(r"camara dos deputados|senado federal|assembleia legislativa|camara legislativa", t):
        if not _POLICIA_LEGISLATIVA.search(t):
            return None
    return r
