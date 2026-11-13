"""Concursos que podem reabrir: validade terminando (data/validade/<slug>.json).

Decisão do dono (13/11/2026): página própria, "Podem reabrir", separada das inscrições abertas.
Mostra concursos do escopo cuja validade termina em breve (ou terminou há pouco) e que, por isso,
costumam ganhar edital novo. Não é previsão de concurso: o site informa a data em que a validade
acaba, com as fontes, e nunca mostra isso como inscrição aberta.

Regras (conferidas pelo schema), as mesmas das notícias apuradas:
- todo fato cita fontes; 2 de veículos diferentes ou 1 fonte oficial (órgão, banca, diário oficial);
- o fato "validade" é obrigatório, com a data final (`fim`), e `validade_ate` é igual a ela;
- texto próprio, nada copiado das fontes.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from ntc.model.noticia import Fonte
from ntc.model.schema import UF, Area, Categoria, Esfera, checar_esfera

VALIDADE_SCHEMA_VERSION = 1

CampoValidade = Literal["validade", "homologacao", "prorrogacao", "cargos", "banca", "novo_concurso"]


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class FatoValidade(_Base):
    campo: CampoValidade
    texto: str = Field(min_length=3, max_length=300)
    inicio: date | None = None
    fim: date | None = None
    fontes: list[str] = Field(min_length=1)


class Validade(_Base):
    schema_version: Literal[1] = VALIDADE_SCHEMA_VERSION
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=120)
    titulo: str = Field(min_length=10, max_length=140)
    orgao: str = Field(min_length=3)
    categoria: Categoria
    esfera: Esfera
    uf: UF
    municipio: str | None = Field(default=None, min_length=2, max_length=80)
    banca: str | None = Field(default=None, max_length=80)  # banca do último concurso
    resumo: str = Field(min_length=80, max_length=1200)
    cargos: list[str] = Field(default_factory=list)
    areas: list[Area] = Field(default_factory=list)
    fatos: list[FatoValidade] = Field(min_length=1)
    fontes: list[Fonte] = Field(min_length=1)
    validade_ate: date
    apurado_em: AwareDatetime

    @model_validator(mode="after")
    def _regras(self) -> Validade:
        por_id = {f.id: f for f in self.fontes}
        if len(por_id) != len(self.fontes):
            raise ValueError("ids de fonte repetidos")
        usadas: set[str] = set()
        for fato in self.fatos:
            faltando = [i for i in fato.fontes if i not in por_id]
            if faltando:
                raise ValueError(f"{fato.campo}: fonte inexistente {faltando}")
            fontes = [por_id[i] for i in fato.fontes]
            usadas |= set(fato.fontes)
            if not any(f.oficial for f in fontes) and len({f.dominio for f in fontes}) < 2:
                raise ValueError(f"{fato.campo}: precisa de 2 fontes de veículos diferentes ou de 1 fonte oficial")
        sobrando = set(por_id) - usadas
        if sobrando:
            raise ValueError(f"fontes listadas sem fato: {sorted(sobrando)}")
        val = next((f for f in self.fatos if f.campo == "validade"), None)
        if val is None or val.fim is None:
            raise ValueError("falta o fato 'validade' com a data final")
        if self.validade_ate != val.fim:
            raise ValueError("validade_ate deve ser a data final do fato 'validade'")
        checar_esfera(self.categoria, self.esfera, self.uf, self.municipio)
        if self.categoria == "outro" and "ti" not in self.areas:
            raise ValueError("categoria 'outro' só entra com cargo de TI")
        return self
