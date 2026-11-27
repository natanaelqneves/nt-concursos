"""Decisão do editor sobre uma pendência de revisão (docs/CONTRATO-DADOS.md).

Um arquivo por decisão em data/decisoes/<slug>/<AAAAMMDD-HHMMSS>.json; o mais recente vale.
Ou um lote em data/decisoes/lotes/<AAAAMMDD-HHMMSS>.json, com várias decisões de slugs diferentes.
A página /admin/ do site gera o arquivo; a coleta seguinte aplica.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

DECISAO_SCHEMA_VERSION = 1
APROVADO_POR = "editor"
CAMPOS_DECIDIVEIS = ("prazos.isencao", "prazos.inscricao")


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OpcaoEscolhida(_Base):
    origem: Literal["texto", "tabela"]
    pagina: int = Field(ge=1)
    trecho: str = Field(min_length=15)
    inicio: date | None = None
    fim: date


class DecisaoCampo(_Base):
    acao: Literal["usar", "ausente"]
    opcao: OpcaoEscolhida | None = None

    @model_validator(mode="after")
    def _coerente(self) -> DecisaoCampo:
        if (self.acao == "usar") != (self.opcao is not None):
            raise ValueError("'usar' exige opcao; 'ausente' não leva opcao")
        return self


class Decisao(_Base):
    schema_version: Literal[1] = DECISAO_SCHEMA_VERSION
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    decidido_em: AwareDatetime
    edital_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    acao: Literal["decidir", "descartar"]
    campos: dict[str, DecisaoCampo] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _coerente(self) -> Decisao:
        for k in self.campos:
            if k not in CAMPOS_DECIDIVEIS:
                raise ValueError(f"campo não decidível: {k}")
        if self.acao == "decidir" and not self.campos:
            raise ValueError("decisão sem campos")
        if self.acao == "decidir" and not self.edital_sha256:
            raise ValueError("decisão de campos precisa do edital_sha256")
        return self


class Lote(_Base):
    """Várias decisões num arquivo só (data/decisoes/lotes/), para o editor confirmar de uma vez."""

    schema_version: Literal[1] = DECISAO_SCHEMA_VERSION
    decisoes: list[Decisao] = Field(min_length=1)

    @model_validator(mode="after")
    def _slugs_unicos(self) -> Lote:
        slugs = [d.slug for d in self.decisoes]
        if len(set(slugs)) != len(slugs):
            raise ValueError("slug repetido no lote")
        return self
