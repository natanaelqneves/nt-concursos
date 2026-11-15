"""Querido Diário (Open Knowledge Brasil): API pública dos diários oficiais municipais.

Papel no site: só DESCOBERTA. O diário diz que um município abriu concurso; os prazos continuam
vindo do edital, pelo gate de evidência. A API pede uso moderado (referência: 60 requisições por
minuto); aqui vai 1 requisição a cada 2 segundos.

Por enquanto só a sonda (`ntc qd-sonda`): mede a cobertura na Paraíba e mostra o que a busca
devolve, sem gravar nada em data/.
"""

from __future__ import annotations

from datetime import date, timedelta
from urllib.parse import urlencode

from ntc.fetch.http import Cliente

API = "https://api.queridodiario.ok.org.br"
BUSCA = '"concurso público" edital'


def cidades(cliente: Cliente, **params: str) -> list[dict]:
    r = cliente.get(f"{API}/cities?{urlencode(params)}", usar_cache=False).json()
    return r.get("cities", r) if isinstance(r, dict) else r


def diarios(cliente: Cliente, *, desde: date, territorios: list[str] | None = None, tamanho: int = 50,
            busca: str = BUSCA) -> dict:
    params: list[tuple[str, str]] = [
        ("querystring", busca), ("published_since", desde.isoformat()), ("size", str(tamanho)),
        ("excerpt_size", "300"), ("number_of_excerpts", "1"), ("sort_by", "descending_date"),
    ]
    params += [("territory_ids", t) for t in territorios or []]
    return cliente.get(f"{API}/gazettes?{urlencode(params)}", usar_cache=False).json()


def sonda(cliente: Cliente, dias: int = 30) -> dict:
    """Cobertura na Paraíba e amostra da busca. Cada parte falha sozinha, com o erro no resultado."""
    from ntc.municipios import PARAIBA

    saida: dict = {}
    try:
        todas = cidades(cliente, levels="3")
        if not todas:
            todas = cidades(cliente, city_name="a")
        saida["cidades_total"] = len(todas)
        saida["cidades_campos"] = sorted(todas[0]) if todas else []
        pb = [c for c in todas if c.get("state_code") == "PB"]
        saida["pb_cobertos"] = sorted(c.get("territory_name", "?") for c in pb)
        saida["pb_fora_da_lista_do_site"] = sorted(set(saida["pb_cobertos"]) - set(PARAIBA))
        saida["pb_ids"] = {c.get("territory_name"): c.get("territory_id") for c in pb}
    except Exception as e:  # sonda: mostra o erro e segue
        saida["cidades_erro"] = f"{type(e).__name__}: {e}"[:300]
    desde = date.today() - timedelta(days=dias)
    for nome, ids in (("brasil", None), ("pb", list((saida.get("pb_ids") or {}).values()) or ["2507507", "2504009"])):
        try:
            r = diarios(cliente, desde=desde, territorios=ids)
            gz = r.get("gazettes", [])
            saida[f"busca_{nome}"] = {
                "total": r.get("total_gazettes"), "campos": sorted(gz[0]) if gz else [],
                "amostra": [
                    {"cidade": g.get("territory_name"), "uf": g.get("state_code"), "data": g.get("date"),
                     "url": g.get("url"), "trecho": " ".join((g.get("excerpts") or [""])[0].split())[:260]}
                    for g in gz[:40]
                ],
            }
        except Exception as e:
            saida[f"busca_{nome}_erro"] = f"{type(e).__name__}: {e}"[:300]
    return saida
