"""Filtro de escopo: decide se um concurso é de um órgão coberto pelo site.

Escopo (docs/ARQUITETURA.md, seção 11): órgãos federais e estaduais das categorias
tribunal, controle, mp, defensoria, seguranca, fiscal, advocacia, executivo (só federal),
legislativo, estatal e conselho; outros órgãos só com cargo de TI. Municipais, outorgas de
cartório, exames e processos seletivos ficam fora.

A classificação usa só texto que a fonte publica sobre o concurso (título, nome
abreviado da banca, cargos, hierarquia do DOU). Regras explícitas e testadas, sem
heurística estatística: o que não casa com nenhuma regra fica fora do escopo e vai
para o log da execução, onde pode ser conferido.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace

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
    areas: tuple[str, ...] = ()  # ("ti",) quando há cargo de tecnologia da informação


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
    curtos_lista = [x for x in partes if len(x) <= 200]
    curtos = sem_acento(" | ".join(curtos_lista))
    if _FORA.search(curtos):
        return None
    if _MUNICIPAL.search(curtos) and not re.search(r"tribunal de contas dos municipios", curtos):
        return None
    areas = ("ti",) if tem_ti(*partes) else ()

    r = _nucleo(partes, t)
    if r is None:
        r = _publico(partes, curtos_lista)
    if r is None:
        r = _conselho(partes) or _estatal(partes, t)
    if r is None and tem_ti(*curtos_lista):
        # Demais órgãos federais/estaduais só entram com cargo de TI nomeado (título ou cargo).
        r = _outro(partes)
    if r is None:
        return None
    return replace(r, areas=areas)


def _nucleo(partes: list[str], t: str) -> Classificacao | None:
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
    # Câmara, Senado e assembleias só entram pelo concurso de polícia legislativa
    # (ou, como "outro", se tiverem cargo de TI).
    if re.search(r"camara dos deputados|senado federal|assembleia legislativa|camara legislativa", t):
        if not _POLICIA_LEGISLATIVA.search(t):
            return None
    return r


# ---------------------------------------------------------------- fiscal, advocacia, executivo, legislativo

# Assembleias por sigla (Cebraspe/FGV usam "ALEAM 25", "alerj2025", "ALEPE")
_SIGLAS_ALE = {
    "aleac": "AC", "aleal": "AL", "alea": "AL", "aleap": "AP", "aleam": "AM", "alba": "BA", "alece": "CE",
    "cldf": "DF", "ales": "ES", "alego": "GO", "alema": "MA", "almt": "MT", "alems": "MS", "almg": "MG",
    "alepa": "PA", "alpb": "PB", "alep": "PR", "alepe": "PE", "alepi": "PI", "alerj": "RJ", "alrn": "RN",
    "alrs": "RS", "alero": "RO", "alerr": "RR", "alesc": "SC", "alesp": "SP", "alese": "SE", "aleto": "TO",
}

# Executivo federal: nome por extenso (em textos curtos) -> (órgão, sigla do slug)
_EXECUTIVO_NOMES = {
    r"instituto nacional do seguro social": ("Instituto Nacional do Seguro Social (INSS)", "inss"),
    r"instituto brasileiro de geografia e estatistica": ("Instituto Brasileiro de Geografia e Estatística (IBGE)", "ibge"),
    r"concurso (?:publico )?nacional unificado": ("Concurso Público Nacional Unificado (CNU)", "cnu"),
    r"banco central do brasil": ("Banco Central do Brasil", "bacen"),
    r"agencia brasileira de inteligencia": ("Agência Brasileira de Inteligência (Abin)", "abin"),
    r"conselho administrativo de defesa economica": ("Conselho Administrativo de Defesa Econômica (Cade)", "cade"),
    r"comissao de valores mobiliarios": ("Comissão de Valores Mobiliários (CVM)", "cvm"),
    r"superintendencia de seguros privados": ("Superintendência de Seguros Privados (Susep)", "susep"),
    r"instituto brasileiro do meio ambiente": ("Ibama", "ibama"),
    r"instituto chico mendes": ("ICMBio", "icmbio"),
    r"instituto nacional de colonizacao e reforma agraria": ("Incra", "incra"),
    r"instituto nacional da propriedade industrial": ("INPI", "inpi"),
    r"departamento nacional de infraestrutura de transportes": ("DNIT", "dnit"),
    r"ministerio das relacoes exteriores": ("Ministério das Relações Exteriores", "mre"),
    r"arquivo nacional": ("Arquivo Nacional", "arquivo-nacional"),
    r"instituto do patrimonio historico e artistico nacional": ("Iphan", "iphan"),
    r"instituto de pesquisa economica aplicada": ("Ipea", "ipea"),
}
# Siglas que só valem como primeira palavra do título ("ANTAQ 25 CF", "IBGE 26")
_EXECUTIVO_SIGLAS = {
    "inss": "Instituto Nacional do Seguro Social (INSS)", "ibge": "Instituto Brasileiro de Geografia e Estatística (IBGE)",
    "cnu": "Concurso Público Nacional Unificado (CNU)", "cpnu": "Concurso Público Nacional Unificado (CNU)",
    "bacen": "Banco Central do Brasil", "bcb": "Banco Central do Brasil", "abin": "Agência Brasileira de Inteligência (Abin)",
    "cade": "Conselho Administrativo de Defesa Econômica (Cade)", "cvm": "Comissão de Valores Mobiliários (CVM)",
    "susep": "Superintendência de Seguros Privados (Susep)", "previc": "Superintendência Nacional de Previdência Complementar (Previc)",
    "ibama": "Ibama", "icmbio": "ICMBio", "incra": "Incra", "inep": "Inep", "capes": "Capes", "cnpq": "CNPq",
    "funai": "Funai", "inpi": "INPI", "inmetro": "Inmetro", "dnit": "DNIT", "funasa": "Funasa", "iphan": "Iphan",
    "ipea": "Ipea", "enap": "Enap", "mre": "Ministério das Relações Exteriores", "mgi": "Ministério da Gestão e da Inovação",
    "antaq": "Agência Nacional de Transportes Aquaviários (Antaq)", "antt": "Agência Nacional de Transportes Terrestres (ANTT)",
    "anac": "Agência Nacional de Aviação Civil (Anac)", "aneel": "Agência Nacional de Energia Elétrica (Aneel)",
    "anatel": "Agência Nacional de Telecomunicações (Anatel)", "anvisa": "Agência Nacional de Vigilância Sanitária (Anvisa)",
    "ans": "Agência Nacional de Saúde Suplementar (ANS)", "ana": "Agência Nacional de Águas (ANA)",
    "anp": "Agência Nacional do Petróleo (ANP)", "ancine": "Agência Nacional do Cinema (Ancine)",
    "anm": "Agência Nacional de Mineração (ANM)",
}
_SEFAZ_SIGLA = re.compile(r"^(sefaz|sefa|sef|sefin|sefe)([a-z]{2})?\d*$")


def _primeiro_token(titulo: str) -> list[str]:
    return re.sub(r"[^a-z0-9 ]", " ", sem_acento(titulo)).split()


def _publico(partes: list[str], curtos_lista: list[str]) -> Classificacao | None:
    """Fiscal, advocacia pública, executivo federal e legislativo (federal e estadual)."""
    # Só título e segundo texto (nome completo na Cebraspe, hierarquia no DOU, id na FGV):
    # descrições e cargos citam ministérios e secretarias sem ser deles o concurso.
    for orig in (x for x in partes[:2] if len(x) <= 200):
        r = _publico_por_nome(sem_acento(orig), orig)
        if r is not None:
            return r
    return _publico_por_sigla(partes[0])


def _publico_por_nome(t: str, orig: str) -> Classificacao | None:
    # Fiscal
    if re.search(r"receita federal|auditor[- ]fiscal da receita federal", t):
        return _c("fiscal", "federal", "BR", "Receita Federal do Brasil", "receita-federal")
    m = re.search(r"secretaria (?:de estado )?(?:da |de )?(?:fazenda|economia e fazenda|fazenda e planejamento)|"
                  r"receita estadual|auditor[- ]fiscal da receita estadual", t)
    if m:
        uf = uf_por_nome(t, m.start())
        if uf:
            return _c("fiscal", "estadual", uf, f"Secretaria da Fazenda {_no_estado(uf)}", f"sefaz-{uf.lower()}")
    # Advocacia pública
    if re.search(r"advocacia[- ]geral da uniao", t):
        return _c("advocacia", "federal", "BR", "Advocacia-Geral da União (AGU)", "agu")
    if re.search(r"procuradoria[- ]geral da fazenda nacional", t):
        return _c("advocacia", "federal", "BR", "Procuradoria-Geral da Fazenda Nacional (PGFN)", "pgfn")
    if re.search(r"procuradoria[- ]geral do distrito federal", t):
        return _c("advocacia", "estadual", "DF", "Procuradoria-Geral do Distrito Federal", "pgdf")
    m = re.search(r"procuradoria[- ]geral do estado", t)
    if m:
        uf = uf_por_nome(t, m.start())
        if uf:
            return _c("advocacia", "estadual", uf, f"Procuradoria-Geral {_no_estado(uf)}", f"pge-{uf.lower()}")
    # Legislativo (polícia legislativa já saiu como segurança no núcleo)
    if re.search(r"camara dos deputados", t):
        return _c("legislativo", "federal", "BR", "Câmara dos Deputados", "camara-dos-deputados")
    if re.search(r"senado federal", t):
        return _c("legislativo", "federal", "BR", "Senado Federal", "senado")
    if re.search(r"camara legislativa do distrito federal", t):
        return _c("legislativo", "estadual", "DF", "Câmara Legislativa do Distrito Federal", "cldf")
    m = re.search(r"assembleia legislativa", t)
    if m:
        uf = uf_por_nome(t, m.end())
        if uf:
            return _c("legislativo", "estadual", uf, f"Assembleia Legislativa {_no_estado(uf)}", f"ale-{uf.lower()}")
    # Executivo federal
    for padrao, (orgao, sigla) in _EXECUTIVO_NOMES.items():
        if re.search(padrao, t):
            return _c("executivo", "federal", "BR", orgao, sigla)
    m = re.search(r"\bministerio d[aoe]s? ([a-z ]+?)(?:\s*[-–(|/,]|$| e do | 20\d\d)", t)
    if m and not m.group(1).startswith("publico"):
        nome = orig[m.start():m.end(1)] if len(orig) == len(t) else "Ministério d" + t[m.start() + 12:m.end(1)]
        nome = "Ministério" + nome[len("ministerio"):]
        palavras = [w for w in m.group(1).split() if w not in {"da", "de", "do", "das", "dos", "e", "em"}]
        return _c("executivo", "federal", "BR", nome, slug_simples("ministerio " + " ".join(palavras[:2])))
    m = re.search(r"agencia nacional d[aeo]s? ([a-z ]+?)(?:\s*[-–(|/,]|$| 20\d\d)", t)
    if m:
        nome = orig[m.start():m.end(1)] if len(orig) == len(t) else f"Agência Nacional de {m.group(1)}"
        return _c("executivo", "federal", "BR", "Agência" + nome[len("agencia"):], slug_simples("agencia " + " ".join(m.group(1).split()[:2])))
    return None


def _publico_por_sigla(titulo: str) -> Classificacao | None:
    tokens = _primeiro_token(titulo)
    if not tokens:
        return None
    a = tokens[0]
    prox = tokens[1] if len(tokens) > 1 else ""
    if a in {"rfb", "receita"} and (a == "rfb" or prox == "federal"):
        return _c("fiscal", "federal", "BR", "Receita Federal do Brasil", "receita-federal")
    m = _SEFAZ_SIGLA.match(a)
    if m:
        uf = (m.group(2) or (prox if prox in _UFS else "")).upper()
        if uf in ESTADOS:
            return _c("fiscal", "estadual", uf, f"Secretaria da Fazenda {_no_estado(uf)}", f"sefaz-{uf.lower()}")
    if a == "agu":
        return _c("advocacia", "federal", "BR", "Advocacia-Geral da União (AGU)", "agu")
    if a == "pgfn":
        return _c("advocacia", "federal", "BR", "Procuradoria-Geral da Fazenda Nacional (PGFN)", "pgfn")
    if a == "pgdf":
        return _c("advocacia", "estadual", "DF", "Procuradoria-Geral do Distrito Federal", "pgdf")
    m = re.match(r"^pge([a-z]{2})?\d*$", a)
    if m:
        uf = (m.group(1) or (prox if prox in _UFS else "")).upper()
        if uf in ESTADOS:
            return _c("advocacia", "estadual", uf, f"Procuradoria-Geral {_no_estado(uf)}", f"pge-{uf.lower()}")
    if a == "cd" or (a == "camara" and prox == "dos"):
        return _c("legislativo", "federal", "BR", "Câmara dos Deputados", "camara-dos-deputados")
    if a == "senado":
        return _c("legislativo", "federal", "BR", "Senado Federal", "senado")
    m = re.match(r"^([a-z]{3,5}?)\d*$", a)
    base = m.group(1) if m else a
    for sigla in sorted(_SIGLAS_ALE, key=len, reverse=True):
        if a == sigla or re.fullmatch(rf"{sigla}\d+", a):
            uf = _SIGLAS_ALE[sigla]
            orgao = "Câmara Legislativa do Distrito Federal" if uf == "DF" else f"Assembleia Legislativa {_no_estado(uf)}"
            return _c("legislativo", "estadual", uf, orgao, "cldf" if uf == "DF" else f"ale-{uf.lower()}")
    if base in _EXECUTIVO_SIGLAS or a in _EXECUTIVO_SIGLAS:
        chave = a if a in _EXECUTIVO_SIGLAS else base
        # Siglas curtas ("ANA", "ANS", "MRE") só com ano/número logo depois: "Ana Maria" não é agência.
        if len(chave) <= 3 and a == chave and prox and not prox.isdigit():
            return None
        return _c("executivo", "federal", "BR", _EXECUTIVO_SIGLAS[chave], chave)
    return None


# ---------------------------------------------------------------- tecnologia da informação

_TI = re.compile(
    r"tecnologia da informacao|\bti\b|analista de sistemas?|analise de sistemas|desenvolvimento de sistemas|"
    r"desenvolvedor|programador|engenh(?:aria|eiro) de (?:software|computacao|dados)|ciencia de dados|"
    r"cientista de dados|banco de dados|seguranca da informacao|ciberseguranca|seguranca cibernetica|"
    r"infraestrutura de ti|redes de computadores|suporte (?:tecnico|em tecnologia)|informatica|"
    r"ciencia da computacao|tecnologia e informacoes|processamento de dados"
)
_NAO_TI = re.compile(r"nocoes de informatica|informatica basica|conhecimentos de informatica")
_DOCENCIA = re.compile(r"professor|docente|magisterio")


def tem_ti(*textos: str | None) -> bool:
    """Algum texto nomeia cargo/especialidade de TI? ("noções de informática" não conta)."""
    for x in textos:
        if not x:
            continue
        limpo = _NAO_TI.sub(" ", sem_acento(x))
        if _DOCENCIA.search(limpo):
            continue  # "professor de informática" é cargo de magistério, não de TI
        if _TI.search(limpo):
            return True
    return False


# ---------------------------------------------------------------- conselhos profissionais

_CONSELHO = re.compile(r"conselho (regional|federal) d[eoa]s? ([a-z ]+?)(?: d[aeo]s? (\d{1,2})a? regiao|\s*[-–(|/,]|$| do estado| de | da | do )")


def _conselho(partes: list[str]) -> Classificacao | None:
    for texto in partes:
        t = sem_acento(texto)
        m = re.search(r"conselho (regional|federal) d[eoa]s? ", t)
        if not m:
            continue
        inicio = texto[m.start():]
        nome = re.split(r"\s+[-–(|]\s*|\s*[–(|]", inicio, maxsplit=1)[0].strip(" .")
        if m.group(1) == "federal":
            return _c("conselho", "federal", "BR", nome, slug_simples(nome))
        uf = uf_por_nome(t, m.end())
        return _c("conselho", "federal", uf or "BR", nome, slug_simples(nome))
    # Siglas usuais (CRM-SP, CREA PR, CRP/05...)
    for texto in partes:
        t = sem_acento(texto)
        m = re.match(r"\s*(cr[a-z]{1,4}|cf[a-z]{1,4})[\s/-]+([a-z]{2}|\d{1,2})\b", t)
        if m and m.group(1).upper() in _SIGLAS_CONSELHO:
            sufixo = m.group(2)
            uf = sufixo.upper() if sufixo.upper() in ESTADOS else "BR"
            nome = f"{_SIGLAS_CONSELHO[m.group(1).upper()]}" + (f" ({sufixo.upper()})" if uf != "BR" else f" da {int(sufixo)}ª Região" if sufixo.isdigit() else "")
            return _c("conselho", "federal", uf, nome, slugify_simples(f"{m.group(1)} {sufixo}"))
    return None


_SIGLAS_CONSELHO = {
    "CRM": "Conselho Regional de Medicina", "CREA": "Conselho Regional de Engenharia e Agronomia",
    "CRP": "Conselho Regional de Psicologia", "CRC": "Conselho Regional de Contabilidade",
    "COREN": "Conselho Regional de Enfermagem", "CRO": "Conselho Regional de Odontologia",
    "CRF": "Conselho Regional de Farmácia", "CREFITO": "Conselho Regional de Fisioterapia e Terapia Ocupacional",
    "CRMV": "Conselho Regional de Medicina Veterinária", "CRA": "Conselho Regional de Administração",
    "CRN": "Conselho Regional de Nutricionistas", "CRESS": "Conselho Regional de Serviço Social",
    "CRB": "Conselho Regional de Biblioteconomia", "CRQ": "Conselho Regional de Química",
    "CRECI": "Conselho Regional de Corretores de Imóveis", "CREF": "Conselho Regional de Educação Física",
    "CRBM": "Conselho Regional de Biomedicina", "CRFA": "Conselho Regional de Fonoaudiologia",
    "CAU": "Conselho de Arquitetura e Urbanismo", "CORE": "Conselho Regional dos Representantes Comerciais",
}


# ---------------------------------------------------------------- empresas públicas

# Federais: nome (sem acento, minúsculo) -> (nome oficial, sigla do slug)
_ESTATAIS_FEDERAIS = {
    r"petrobras|petroleo brasileiro": ("Petrobras", "petrobras"),
    r"transpetro": ("Transpetro", "transpetro"),
    r"banco do brasil\b": ("Banco do Brasil", "bb"),
    r"caixa economica federal": ("Caixa Econômica Federal", "caixa"),
    r"correios|empresa brasileira de correios": ("Correios", "correios"),
    r"\bbndes\b|banco nacional de desenvolvimento": ("BNDES", "bndes"),
    r"banco do nordeste": ("Banco do Nordeste", "bnb"),
    r"banco da amazonia": ("Banco da Amazônia", "basa"),
    r"\bserpro\b|servico federal de processamento": ("Serpro", "serpro"),
    r"\bdataprev\b|tecnologia e informacoes da previdencia": ("Dataprev", "dataprev"),
    r"\bembrapa\b|empresa brasileira de pesquisa agropecuaria": ("Embrapa", "embrapa"),
    r"\bebserh\b|empresa brasileira de servicos hospitalares": ("Ebserh", "ebserh"),
    r"casa da moeda": ("Casa da Moeda do Brasil", "casa-da-moeda"),
    r"\bconab\b|companhia nacional de abastecimento": ("Conab", "conab"),
    r"hemobras": ("Hemobrás", "hemobras"),
    r"telebras": ("Telebras", "telebras"),
    r"infraero": ("Infraero", "infraero"),
    r"nav brasil": ("NAV Brasil", "nav-brasil"),
    r"\bamazul\b|amazonia azul tecnologias": ("Amazul", "amazul"),
    r"\bcprm\b|servico geologico do brasil|companhia de pesquisa de recursos minerais": ("Serviço Geológico do Brasil (CPRM)", "sgb-cprm"),
    r"codevasf": ("Codevasf", "codevasf"),
    r"\bfinep\b": ("Finep", "finep"),
    r"empresa de pesquisa energetica": ("Empresa de Pesquisa Energética", "epe"),
    r"\binb\b|industrias nucleares do brasil": ("Indústrias Nucleares do Brasil", "inb"),
    r"\bnuclep\b": ("Nuclep", "nuclep"),
    r"eletronuclear": ("Eletronuclear", "eletronuclear"),
    r"\bemgepron\b": ("Emgepron", "emgepron"),
    r"\bimbel\b|industria de material belico": ("Imbel", "imbel"),
    r"\bebc\b|empresa brasil de comunicacao": ("EBC", "ebc"),
    r"\bcbtu\b|companhia brasileira de trens urbanos": ("CBTU", "cbtu"),
    r"trensurb": ("Trensurb", "trensurb"),
    r"grupo hospitalar conceicao": ("Grupo Hospitalar Conceição", "ghc"),
    r"hospital de clinicas de porto alegre": ("Hospital de Clínicas de Porto Alegre", "hcpa"),
    r"companhia docas": ("Companhia Docas", "docas"),
    r"infra s\.?a|valec": ("Infra S.A.", "infra-sa"),
}

# Estaduais conhecidas por sigla: sigla -> (UF, nome)
_ESTATAIS_ESTADUAIS = {
    "CAESB": ("DF", "Companhia de Saneamento Ambiental do Distrito Federal (Caesb)"),
    "CAGECE": ("CE", "Companhia de Água e Esgoto do Ceará (Cagece)"),
    "COMPESA": ("PE", "Companhia Pernambucana de Saneamento (Compesa)"),
    "EMBASA": ("BA", "Empresa Baiana de Águas e Saneamento (Embasa)"),
    "COPASA": ("MG", "Companhia de Saneamento de Minas Gerais (Copasa)"),
    "CEDAE": ("RJ", "Companhia Estadual de Águas e Esgotos do Rio de Janeiro (Cedae)"),
    "SANEPAR": ("PR", "Companhia de Saneamento do Paraná (Sanepar)"),
    "CASAN": ("SC", "Companhia Catarinense de Águas e Saneamento (Casan)"),
    "CAGEPA": ("PB", "Companhia de Água e Esgotos da Paraíba (Cagepa)"),
    "CASAL": ("AL", "Companhia de Saneamento de Alagoas (Casal)"),
    "CAERN": ("RN", "Companhia de Águas e Esgotos do Rio Grande do Norte (Caern)"),
    "CAEMA": ("MA", "Companhia de Saneamento Ambiental do Maranhão (Caema)"),
    "COSANPA": ("PA", "Companhia de Saneamento do Pará (Cosanpa)"),
    "SANEAGO": ("GO", "Saneamento de Goiás (Saneago)"),
    "SANESUL": ("MS", "Empresa de Saneamento de Mato Grosso do Sul (Sanesul)"),
    "DESO": ("SE", "Companhia de Saneamento de Sergipe (Deso)"),
    "CEMIG": ("MG", "Companhia Energética de Minas Gerais (Cemig)"),
    "COPEL": ("PR", "Companhia Paranaense de Energia (Copel)"),
    "CELESC": ("SC", "Centrais Elétricas de Santa Catarina (Celesc)"),
    "BANRISUL": ("RS", "Banco do Estado do Rio Grande do Sul (Banrisul)"),
    "BRB": ("DF", "Banco de Brasília (BRB)"),
    "BANESTES": ("ES", "Banco do Estado do Espírito Santo (Banestes)"),
    "BANPARA": ("PA", "Banco do Estado do Pará (Banpará)"),
    "BANESE": ("SE", "Banco do Estado de Sergipe (Banese)"),
    "PRODEMGE": ("MG", "Companhia de Tecnologia da Informação de Minas Gerais (Prodemge)"),
    "PRODESP": ("SP", "Companhia de Processamento de Dados do Estado de São Paulo (Prodesp)"),
    "CELEPAR": ("PR", "Companhia de Tecnologia da Informação e Comunicação do Paraná (Celepar)"),
    "PROCERGS": ("RS", "Companhia de Processamento de Dados do Rio Grande do Sul (Procergs)"),
    "METRO SP": ("SP", "Companhia do Metropolitano de São Paulo (Metrô)"),
    "CPTM": ("SP", "Companhia Paulista de Trens Metropolitanos (CPTM)"),
    "METRO DF": ("DF", "Companhia do Metropolitano do Distrito Federal (Metrô-DF)"),
    "EMATER": ("", "Empresa de Assistência Técnica e Extensão Rural"),
}
_EMPRESA_GENERICA = re.compile(r"\b(companhia|empresa|banco|centrais eletricas|sociedade de economia mista)\b|\bs\.?\s?a\.?(?:\s|$|[-–)])")


def _estatal(partes: list[str], t: str) -> Classificacao | None:
    for texto in partes:
        tt = sem_acento(texto)
        for padrao, (nome, sigla) in _ESTATAIS_FEDERAIS.items():
            if re.search(padrao, tt):
                return _c("estatal", "federal", "BR", nome, sigla)
    for texto in partes:
        tokens = re.sub(r"[^A-Z0-9 ]", " ", sem_acento(texto).upper()).split()
        for chave, (uf, nome) in _ESTATAIS_ESTADUAIS.items():
            k = chave.split()
            if tokens[: len(k)] == k:
                uf = uf or (tokens[len(k)] if len(tokens) > len(k) and tokens[len(k)] in ESTADOS else "")
                if uf:
                    return _c("estatal", "estadual", uf, nome if "(" in nome else f"{nome} {_no_estado(uf)}",
                              slug_simples(f"{chave} {uf if chave in ('EMATER',) else ''}"))
    for texto in partes:
        tt = sem_acento(texto)
        m = _EMPRESA_GENERICA.search(tt)
        if m:
            uf = uf_por_nome(tt, 0)
            if uf:
                nome = _nome_do_titulo(texto)
                return _c("estatal", "estadual", uf, nome, slug_simples(_sigla_do_titulo(texto) or nome))
    return None


# ---------------------------------------------------------------- demais órgãos (só com TI)

_FEDERAL_GENERICO = re.compile(
    r"\bfederal\b|\bnacional\b|da uniao|ministerio|brasileir|instituto federal|universidade federal|camara dos deputados|senado federal|"
    r"^\s*(antaq|antt|anac|aneel|anatel|anvisa|ans|ana|anp|ancine|anm|inss|ibge|ibama|icmbio|incra|inep|"
    r"capes|cnpq|mre|mpo|mgi|funai|funpresp|abin|cade|cvm|susep|previc|bacen|banco central|receita federal)\b"
)


def _outro(partes: list[str]) -> Classificacao | None:
    titulo = partes[0]
    t = sem_acento(" | ".join(x for x in partes if len(x) <= 200))
    nome = _nome_do_titulo(titulo)
    if _FEDERAL_GENERICO.search(t):
        return _c("outro", "federal", "BR", nome, slug_simples(_sigla_do_titulo(titulo) or nome))
    uf = uf_por_nome(t, 0)
    if uf is None:
        tokens = re.sub(r"[^a-z0-9 ]", " ", sem_acento(titulo)).split()
        uf = next((x.upper() for x in tokens[1:4] if x in _UFS), None)
    if uf:
        return _c("outro", "estadual", uf, nome, slug_simples(_sigla_do_titulo(titulo) or nome))
    return None


def _nome_do_titulo(titulo: str) -> str:
    """'Concurso Público para a Secretaria X – SIGLA' -> 'Secretaria X'; 'SEFAZ AL 26' -> 'SEFAZ AL'."""
    t = re.sub(r"^\s*(concurso p[úu]blico|processo seletivo)[^a-zà-ú]*(?:para|do|da|de)\s+(?:o|a|os|as)?\s*", "",
               titulo, flags=re.IGNORECASE)
    t = re.split(r"\s+[-–]\s+|\s*\(", t, maxsplit=1)[0]
    t = re.sub(r"\s+\d{2,4}\b.*$", "", t).strip(" .,")
    t = t or titulo.strip()
    palavras = t.split()
    if sum(len(p) >= 4 and p.isupper() for p in palavras) >= 2:  # "CÂMARA DOS DEPUTADOS"
        t = " ".join(p.lower() if p.lower() in {"de", "da", "do", "das", "dos", "e"} else p.capitalize() for p in palavras)
    return t


def _sigla_do_titulo(titulo: str) -> str | None:
    m = re.search(r"[-–(]\s*([A-Z][A-Za-z]{1,9}(?:[/ -][A-Z]{2})?)\s*\)?\s*$", titulo)
    return m.group(1) if m else None


def slug_simples(texto: str) -> str:
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", sem_acento(texto))).strip("-")[:60]


slugify_simples = slug_simples
