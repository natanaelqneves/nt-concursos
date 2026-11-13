"""Contrato de dados de um concurso (data/concursos/<slug>.json).

Todo campo factual carrega `status` e o id da evidência que o sustenta. O site
renderiza apenas campos com status `verificado`; a integridade referencial
(campo -> evidência -> documento) é garantida aqui, antes de qualquer gravação.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, model_validator

SCHEMA_VERSION = 2

Status = Literal["verificado", "revisao", "ausente"]
TipoDocumento = Literal["edital", "retificacao", "aviso", "dou"]
UF = Literal[
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO", "BR",
]

Categoria = Literal[
    "tribunal", "controle", "mp", "defensoria", "seguranca",
    "estatal",   # empresas públicas e sociedades de economia mista federais e estaduais
    "conselho",  # conselhos profissionais (autarquias federais, com sede regional)
    "fiscal",       # Receita Federal e secretarias estaduais de Fazenda (auditoria fiscal)
    "advocacia",    # advocacia pública: AGU, PGFN, procuradorias-gerais dos estados e do DF
    "executivo",    # executivo federal (ministérios, autarquias, agências, INSS, IBGE, CNU) e gestão estadual
                    # (secretarias de administração/planejamento, concursos unificados estaduais, EPPGG)
    "legislativo",  # Câmara dos Deputados, Senado Federal e assembleias legislativas
    "educacao",     # universidades e institutos federais (UF da sede) e secretarias estaduais de educação
    "saude",        # secretarias estaduais de saúde e fundações estaduais de saúde
    "militar",      # Forças Armadas: Exército, Marinha e Aeronáutica (carreira, não temporários)
    "guarda",       # guardas municipais (capitais e cidades grandes)
    "transito",     # Detrans estaduais e órgãos municipais de trânsito (capitais e cidades grandes)
    "vigilancia",   # vigilância sanitária/epidemiológica, agente de endemias e vigilante (estadual ou municipal)
    "prefeitura",   # demais concursos das prefeituras das capitais
    "outro",     # demais órgãos federais/estaduais: só entram com cargo de TI (areas contém "ti")
]
Area = Literal["ti"]
# Categorias federais que podem ter UF própria (sede regional); as demais federais usam BR.
FEDERAIS_COM_UF = {"tribunal", "conselho", "educacao"}
Esfera = Literal["federal", "estadual", "municipal"]
# Na esfera municipal (13/11/2026) entram as capitais (prefeitura e câmara) e, nas capitais e
# cidades grandes, guarda municipal, trânsito e vigilância.
CATEGORIAS_MUNICIPAIS = {"guarda", "transito", "vigilancia", "prefeitura", "legislativo"}
SO_MUNICIPAIS = {"guarda", "prefeitura"}
SEM_FEDERAL = {"transito", "vigilancia"}


def checar_esfera(categoria: str, esfera: str, uf: str, municipio: str | None) -> None:
    """Regras de esfera, categoria, UF e município comuns a concursos, notícias e validades."""
    if esfera == "federal" and uf != "BR" and categoria not in FEDERAIS_COM_UF:
        # TRF/TRT/TRE, conselhos regionais, universidades e institutos federais têm UF da sede;
        # os demais órgãos federais são BR.
        raise ValueError("órgão federal fora do Judiciário deve ter uf BR")
    if categoria == "militar" and esfera != "federal":
        raise ValueError("categoria 'militar' cobre só as Forças Armadas (federal)")
    if categoria == "saude" and esfera != "estadual":
        raise ValueError("categoria 'saude' cobre só as secretarias e fundações estaduais de saúde")
    if esfera in ("estadual", "municipal") and uf == "BR":
        raise ValueError("órgão estadual ou municipal precisa de UF")
    if esfera == "municipal":
        if not municipio:
            raise ValueError("órgão municipal precisa de município")
        if categoria not in CATEGORIAS_MUNICIPAIS:
            raise ValueError(f"categoria {categoria!r} não existe na esfera municipal")
    elif municipio:
        raise ValueError("município só se aplica à esfera municipal")
    if categoria in SO_MUNICIPAIS and esfera != "municipal":
        raise ValueError(f"categoria {categoria!r} é só municipal")
    if categoria in SEM_FEDERAL and esfera == "federal":
        raise ValueError(f"categoria {categoria!r} é estadual ou municipal")
Porte = Literal["grande", "medio", "pequeno", "indefinido"]

TRECHO_MAX = 500

# porte = vagas imediatas verificadas (cadastro reserva não conta)
PORTE_GRANDE = 100
PORTE_MEDIO = 20


def classificar_porte(vagas_imediatas: Campo | None) -> str:
    if vagas_imediatas is None or vagas_imediatas.status != "verificado":
        return "indefinido"
    n = int(vagas_imediatas.valor)
    if n >= PORTE_GRANDE:
        return "grande"
    return "medio" if n >= PORTE_MEDIO else "pequeno"


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class Documento(_Base):
    id: str = Field(pattern=r"^doc-\d+$")
    tipo: TipoDocumento
    url: HttpUrl
    url_final: HttpUrl
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    coletado_em: AwareDatetime
    fonte: str = Field(min_length=2)
    # Data em que a banca/órgão publicou o documento. Ordena edital e retificações (G7);
    # sem ela, vale `coletado_em`.
    publicado_em: date | None = None
    titulo: str | None = Field(default=None, max_length=300)

    def posterior_a(self, outro: Documento) -> bool:
        """Ordem de publicação; se algum dos dois não tiver `publicado_em`, usa `coletado_em`."""
        if self.publicado_em and outro.publicado_em:
            return self.publicado_em > outro.publicado_em
        return self.coletado_em > outro.coletado_em


SEPARADOR_TABELA = " — "


class LinhaTabela(_Base):
    """Linha de uma tabela do documento (ex.: cronograma), lida célula por célula no PDF.
    Cada célula precisa aparecer, literalmente, no texto da página (G3)."""

    atividade: str = Field(min_length=5, max_length=290)
    datas: str = Field(min_length=4, max_length=200)


class Evidencia(_Base):
    id: str = Field(pattern=r"^ev-\d+$")
    campo: str = Field(min_length=3)
    documento: str
    pagina: int = Field(ge=1)
    trecho: str = Field(min_length=15, max_length=TRECHO_MAX)
    ancora: str = Field(min_length=3)
    metodo: str = Field(min_length=3)
    aprovado_por: str | None = None
    aprovado_em: AwareDatetime | None = None
    # Presente quando a evidência é uma linha de tabela; o trecho é "atividade — datas".
    tabela: LinhaTabela | None = None

    @model_validator(mode="after")
    def _aprovacao_completa(self) -> Evidencia:
        if (self.aprovado_por is None) != (self.aprovado_em is None):
            raise ValueError("aprovado_por e aprovado_em devem vir juntos")
        if self.tabela is not None and self.trecho != f"{self.tabela.atividade}{SEPARADOR_TABELA}{self.tabela.datas}":
            raise ValueError("trecho de evidência de tabela deve ser 'atividade — datas'")
        return self


class _ComEvidencia(_Base):
    status: Status = "ausente"
    evidencia: str | None = None

    @model_validator(mode="after")
    def _verificado_exige_evidencia(self):
        if self.status == "verificado" and not self.evidencia:
            raise ValueError("campo verificado sem evidência")
        return self


class Prazo(_ComEvidencia):
    inicio: date | None = None
    fim: date | None = None

    @model_validator(mode="after")
    def _coerente(self) -> Prazo:
        if self.status == "verificado" and self.fim is None:
            raise ValueError("prazo verificado sem data de fim")
        if self.inicio and self.fim and self.inicio > self.fim:
            raise ValueError("início do prazo posterior ao fim")
        return self


class Campo(_ComEvidencia):
    valor: float | int | str | None = None

    @model_validator(mode="after")
    def _valor_presente(self) -> Campo:
        if self.status == "verificado" and self.valor is None:
            raise ValueError("campo verificado sem valor")
        return self


class Cargo(_Base):
    nome: str = Field(min_length=2)
    vagas: Campo | None = None
    remuneracao: Campo | None = None


# Etapas depois das inscrições (13/11/2026): o concurso não some do site quando as inscrições
# fecham; passa para "em andamento" e mostra as etapas do cronograma, cada uma com evidência.
TipoEtapa = Literal[
    "prova_objetiva", "prova_discursiva", "prova_pratica", "taf", "avaliacao_psicologica",
    "avaliacao_medica", "investigacao_social", "titulos", "heteroidentificacao", "curso_formacao",
    "gabarito", "resultado", "resultado_final", "homologacao", "outra",
]


class Etapa(_ComEvidencia):
    tipo: TipoEtapa
    nome: str = Field(min_length=3, max_length=200)  # como o cronograma chama a etapa
    inicio: date | None = None
    fim: date | None = None  # data da etapa (ou fim do período)

    @model_validator(mode="after")
    def _coerente(self) -> Etapa:
        if self.status == "verificado" and self.fim is None:
            raise ValueError("etapa verificada sem data")
        if self.inicio and self.fim and self.inicio > self.fim:
            raise ValueError("início da etapa posterior ao fim")
        return self


class Prazos(_Base):
    isencao: Prazo = Field(default_factory=Prazo)
    inscricao: Prazo = Field(default_factory=Prazo)


class Descoberta(_Base):
    fonte: str
    url: HttpUrl
    data_dou: date | None = None


class Concurso(_Base):
    schema_version: Literal[2] = SCHEMA_VERSION
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=120)
    orgao: str = Field(min_length=3)
    categoria: Categoria
    esfera: Esfera
    banca: str = Field(min_length=2)
    uf: UF
    municipio: str | None = Field(default=None, min_length=2, max_length=80)  # só na esfera municipal
    cargos: list[Cargo] = Field(default_factory=list)
    vagas_imediatas: Campo | None = None
    porte: Porte = "indefinido"
    areas: list[Area] = Field(default_factory=list)  # áreas dos cargos (ex.: "ti")
    taxa: Campo | None = None
    prazos: Prazos = Field(default_factory=Prazos)
    etapas: list[Etapa] = Field(default_factory=list)  # em ordem de data
    isencao_publicos: list[str] = Field(default_factory=list)
    documentos: list[Documento] = Field(min_length=1)
    evidencias: list[Evidencia] = Field(default_factory=list)
    descoberto_via: Descoberta | None = None
    conferido_em: AwareDatetime

    def campos_com_evidencia(self) -> list[tuple[str, _ComEvidencia]]:
        """Pares (caminho do campo, objeto) para todos os campos factuais."""
        pares: list[tuple[str, _ComEvidencia]] = [
            ("prazos.isencao", self.prazos.isencao),
            ("prazos.inscricao", self.prazos.inscricao),
        ]
        if self.vagas_imediatas is not None:
            pares.append(("vagas_imediatas", self.vagas_imediatas))
        if self.taxa is not None:
            pares.append(("taxa", self.taxa))
        for i, etapa in enumerate(self.etapas):
            pares.append((f"etapas.{i}", etapa))
        for i, cargo in enumerate(self.cargos):
            if cargo.vagas is not None:
                pares.append((f"cargos.{i}.vagas", cargo.vagas))
            if cargo.remuneracao is not None:
                pares.append((f"cargos.{i}.remuneracao", cargo.remuneracao))
        return pares

    def evidencia(self, ev_id: str) -> Evidencia:
        return next(e for e in self.evidencias if e.id == ev_id)

    def documento(self, doc_id: str) -> Documento:
        return next(d for d in self.documentos if d.id == doc_id)

    @model_validator(mode="after")
    def _integridade(self) -> Concurso:
        doc_ids = [d.id for d in self.documentos]
        ev_ids = [e.id for e in self.evidencias]
        if len(set(doc_ids)) != len(doc_ids):
            raise ValueError("ids de documento repetidos")
        if len(set(ev_ids)) != len(ev_ids):
            raise ValueError("ids de evidência repetidos")
        for ev in self.evidencias:
            if ev.documento not in doc_ids:
                raise ValueError(f"{ev.id} aponta para documento inexistente {ev.documento}")
        checar_esfera(self.categoria, self.esfera, self.uf, self.municipio)
        if self.categoria == "outro" and "ti" not in self.areas:
            raise ValueError("categoria 'outro' só entra com cargo de TI (areas: ['ti'])")
        if len(set(self.areas)) != len(self.areas):
            raise ValueError("areas repetidas")
        chaves = [(e.tipo, e.nome) for e in self.etapas]
        if len(set(chaves)) != len(chaves):
            raise ValueError("etapas repetidas")
        datas = [e.fim for e in self.etapas if e.fim is not None]
        if datas != sorted(datas):
            raise ValueError("etapas fora da ordem de data")
        if self.vagas_imediatas is not None and self.vagas_imediatas.valor is not None:
            if not isinstance(self.vagas_imediatas.valor, int) or self.vagas_imediatas.valor < 0:
                raise ValueError("vagas_imediatas deve ser inteiro não negativo")
        if self.porte != classificar_porte(self.vagas_imediatas):
            raise ValueError(f"porte {self.porte!r} incoerente com vagas_imediatas")
        for caminho, campo in self.campos_com_evidencia():
            if campo.evidencia is None:
                continue
            if campo.evidencia not in ev_ids:
                raise ValueError(f"{caminho} aponta para evidência inexistente {campo.evidencia}")
            if self.evidencia(campo.evidencia).campo != caminho:
                raise ValueError(f"{campo.evidencia} pertence a outro campo, não a {caminho}")
        return self
