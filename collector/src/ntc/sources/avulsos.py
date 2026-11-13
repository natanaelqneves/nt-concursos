"""Editais achados fora das bancas que coletamos ("avulsos").

Lista mantida à mão em data/editais-avulsos.json, para concursos que a imprensa noticia e cujo
edital não está numa fonte que o coletor alcança (banca sem coletor, PDF bloqueado por robots.txt).
Cada documento traz uma ou mais URLs, em ordem de preferência: primeiro a oficial (órgão, banca,
diário), depois cópias publicadas por sites de concursos. O pipeline é o mesmo das bancas
(cláusulas, gate G1–G8), com duas proteções a mais:

- as datas do edital são comparadas com as que a imprensa publicou (data/noticias/<noticia>.json);
  se divergirem, o prazo vai para revisão em vez de ir ao ar;
- o prazo pode ser lido na retificação mais recente que o traga (prorrogação), já que a cópia
  do edital de abertura costuma estar desatualizada.

A página do concurso diz de onde veio cada documento e onde a pesquisa foi feita (campo
"pesquisa" do arquivo, que o site lê).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import date
from pathlib import Path

from ntc.fetch.http import Cliente
from ntc.sources.base import ConcursoFonte, DocFonte, Fonte, ano_de

ARQUIVO = "editais-avulsos.json"


def _data(v: str | None) -> date | None:
    return date.fromisoformat(v) if v else None


def esperado_da_noticia(pasta_dados: Path, slug_noticia: str | None) -> dict[str, tuple[date | None, date]]:
    if not slug_noticia:
        return {}
    caminho = pasta_dados / "noticias" / f"{slug_noticia}.json"
    if not caminho.exists():
        return {}
    n = json.loads(caminho.read_text(encoding="utf-8"))
    saida = {}
    for fato in n.get("fatos", []):
        if fato.get("campo") in ("inscricao", "isencao") and fato.get("fim"):
            saida[fato["campo"]] = (_data(fato.get("inicio")), _data(fato["fim"]))
    return saida


def esperado_da_entrada(e: dict) -> dict[str, tuple[date | None, date]]:
    """Sem notícia publicada: datas que a imprensa deu, anotadas na própria entrada
    ("imprensa": {"inscricao": {"inicio", "fim"}, "fontes": [urls de 2 veículos]})."""
    imp = e.get("imprensa") or {}
    return {
        tipo: (_data(v.get("inicio")), _data(v["fim"]))
        for tipo, v in imp.items() if tipo in ("inscricao", "isencao") and v.get("fim")
    }


class Avulsos(Fonte):
    nome = "avulsos"

    def __init__(self, pasta_dados: Path, so: set[str] | None = None):
        self.pasta, self.so = pasta_dados, so

    def entradas(self) -> list[dict]:
        caminho = self.pasta / ARQUIVO
        if not caminho.exists():
            return []
        return json.loads(caminho.read_text(encoding="utf-8"))["concursos"]

    def descobrir(self, cliente: Cliente) -> Iterator[ConcursoFonte]:
        for e in self.entradas():
            if self.so and e["slug"] not in self.so:
                continue
            docs = [
                DocFonte(url=d["urls"][0], tipo=d["tipo"], titulo=d["titulo"],
                         publicado_em=_data(d.get("publicado_em")), alternativas=tuple(d["urls"][1:]))
                for d in e["documentos"]
            ]
            yield ConcursoFonte(
                fonte=self.nome, id=e["slug"], titulo=e["titulo"], url=e["pagina"],
                contexto=e.get("contexto", []), documentos=docs, ano=ano_de(e["slug"]),
                cargos=e.get("cargos", []), banca=e["banca"], slug=e["slug"], uf=e.get("uf"),
                esperado=esperado_da_noticia(self.pasta, e.get("noticia")) or esperado_da_entrada(e),
                prazo_na_retificacao=True,
            )
