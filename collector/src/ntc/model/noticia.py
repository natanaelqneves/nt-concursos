"""Notícias apuradas: concursos do escopo que ainda não temos como conferir no edital.

Decisão do dono (12/11/2026): enquanto INLABS e várias bancas estão inacessíveis, o site
pode mostrar concursos apurados em fontes de imprensa, numa seção separada e rotulada.
Nada daqui entra nas listas de dados verificados.

Regras (conferidas pelo schema):
- todo fato cita fontes; precisa de 2 fontes de domínios diferentes, ou de 1 fonte oficial
  (órgão, banca ou diário oficial) que tenha sido consultada;
- o texto é escrito pelo site, com as próprias palavras; nada copiado das fontes;
- a notícia tem data de expiração (fim das inscrições) e sai do ar depois dela.
"""

from __future__ import annotations

from datetime import date
from typing import Literal
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl, AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from ntc.model.schema import FEDERAIS_COM_UF, UF, Area, Categoria, Esfera

NOTICIA_SCHEMA_VERSION = 1

CampoFato = Literal["inscricao", "isencao", "vagas", "taxa", "prova", "remuneracao", "banca", "cargos"]


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Fonte(_Base):
    id: str = Field(pattern=r"^f-\d+$")
    nome: str = Field(min_length=2, max_length=120)
    url: AnyHttpUrl
    oficial: bool = False  # site do órgão, da banca ou diário oficial
    consultado_em: date

    @property
    def dominio(self) -> str:
        host = urlsplit(str(self.url)).hostname or ""
        partes = host.removeprefix("www.").split(".")
        # "noticias.focusconcursos.com.br" e "focusconcursos.com.br" são o mesmo veículo
        return ".".join(partes[-3:]) if partes[-1] == "br" and len(partes) >= 3 else ".".join(partes[-2:])


class Fato(_Base):
    campo: CampoFato
    texto: str = Field(min_length=3, max_length=300)  # frase própria, para exibir
    inicio: date | None = None
    fim: date | None = None
    fontes: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _datas(self) -> Fato:
        if self.inicio and self.fim and self.inicio > self.fim:
            raise ValueError(f"{self.campo}: início depois do fim")
        return self


class Noticia(_Base):
    schema_version: Literal[1] = NOTICIA_SCHEMA_VERSION
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=120)
    titulo: str = Field(min_length=10, max_length=140)
    orgao: str = Field(min_length=3)
    categoria: Categoria
    esfera: Esfera
    uf: UF
    banca: str = Field(min_length=2, max_length=80)
    resumo: str = Field(min_length=80, max_length=1200)
    cargos: list[str] = Field(default_factory=list)
    areas: list[Area] = Field(default_factory=list)
    fatos: list[Fato] = Field(min_length=2)
    fontes: list[Fonte] = Field(min_length=2)
    apurado_em: AwareDatetime
    expira_em: date  # some do site depois desta data (fim das inscrições)

    @model_validator(mode="after")
    def _fontes_suficientes(self) -> Noticia:
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
                raise ValueError(
                    f"{fato.campo}: precisa de 2 fontes de veículos diferentes ou de 1 fonte oficial"
                )
        sobrando = set(por_id) - usadas
        if sobrando:
            raise ValueError(f"fontes listadas sem fato: {sorted(sobrando)}")
        insc = next((f for f in self.fatos if f.campo == "inscricao"), None)
        if insc is None or insc.fim is None:
            raise ValueError("toda notícia precisa do fim das inscrições, com fontes")
        if self.expira_em != insc.fim:
            raise ValueError("expira_em deve ser o fim das inscrições")
        if self.esfera == "federal" and self.uf != "BR" and self.categoria not in FEDERAIS_COM_UF:
            raise ValueError("órgão federal fora do Judiciário deve ter uf BR")
        if self.categoria == "outro" and "ti" not in self.areas:
            raise ValueError("categoria 'outro' só entra com cargo de TI")
        if self.esfera == "estadual" and self.uf == "BR":
            raise ValueError("órgão estadual precisa de UF")
        return self
