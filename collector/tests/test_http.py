"""Cliente HTTP: allowlist em cada salto, robots.txt, cache condicional e novas tentativas.
Usa um adaptador falso do requests: nenhum teste acessa a rede."""

from __future__ import annotations

import io

import pytest
import requests
from requests.adapters import BaseAdapter
from requests.structures import CaseInsensitiveDict

from ntc.fetch.http import BloqueadoPorRobots, Cliente, ErroColeta, ForaDaAllowlist


class Falso(BaseAdapter):
    def __init__(self, rotas: dict):
        super().__init__()
        self.rotas, self.chamadas = rotas, []

    def send(self, req, **kw):
        self.chamadas.append((req.method, req.url, dict(req.headers)))
        rota = self.rotas.get(req.url, (404, {}, b""))
        if callable(rota):
            rota = rota(req)
        status, headers, corpo = rota
        r = requests.Response()
        r.status_code, r.url, r.request = status, req.url, req
        r.headers = CaseInsensitiveDict(headers)
        r.raw = io.BytesIO(corpo)
        return r

    def close(self):
        pass


def cliente(allowlist, rotas, tmp_path=None, **kw) -> tuple[Cliente, Falso]:
    falso = Falso(rotas)
    s = requests.Session()
    s.mount("https://", falso)
    s.mount("http://", falso)
    c = Cliente(allowlist, cache_dir=tmp_path, sessao=s, dormir=lambda _: None, **kw)
    return c, falso


def test_bloqueia_host_fora_da_allowlist(allowlist):
    c, falso = cliente(allowlist, {})
    with pytest.raises(ForaDaAllowlist):
        c.get("https://exemplo.com/edital.pdf")
    assert falso.chamadas == []


def test_bloqueia_redirecionamento_para_fora(allowlist):
    c, falso = cliente(allowlist, {
        "https://conhecimento.fgv.br/robots.txt": (404, {}, b""),
        "https://conhecimento.fgv.br/a.pdf": (302, {"Location": "https://espelho.example.com/a.pdf"}, b""),
    })
    with pytest.raises(ForaDaAllowlist):
        c.get("https://conhecimento.fgv.br/a.pdf")
    assert all("example.com" not in u for _, u, _ in falso.chamadas)


def test_segue_redirecionamento_permitido_e_guarda_url_final(allowlist):
    c, _ = cliente(allowlist, {
        "https://conhecimento.fgv.br/robots.txt": (404, {}, b""),
        "https://cdn.cebraspe.org.br/robots.txt": (404, {}, b""),
        "https://conhecimento.fgv.br/a.pdf": (301, {"Location": "https://cdn.cebraspe.org.br/b.pdf"}, b""),
        "https://cdn.cebraspe.org.br/b.pdf": (200, {}, b"%PDF-1.7 ok"),
    })
    r = c.get("https://conhecimento.fgv.br/a.pdf")
    assert r.url_final == "https://cdn.cebraspe.org.br/b.pdf"
    assert r.conteudo == b"%PDF-1.7 ok"


def test_respeita_robots(allowlist):
    robots = b"User-agent: *\nDisallow: /\n"
    c, falso = cliente(allowlist, {"https://www.in.gov.br/robots.txt": (200, {}, robots)})
    with pytest.raises(BloqueadoPorRobots):
        c.get("https://www.in.gov.br/leiturajornal?data=12-11-2026&secao=do3")
    assert [u for _, u, _ in falso.chamadas] == ["https://www.in.gov.br/robots.txt"]


def test_robots_com_erro_de_servidor_proibe(allowlist):
    c, _ = cliente(allowlist, {"https://conhecimento.fgv.br/robots.txt": (503, {}, b"")})
    with pytest.raises(BloqueadoPorRobots):
        c.get("https://conhecimento.fgv.br/concursos")


def test_cache_condicional(allowlist, tmp_path):
    def pdf(req):
        if req.headers.get("If-None-Match") == '"v1"':
            return (304, {}, b"")
        return (200, {"ETag": '"v1"'}, b"%PDF conteudo")

    rotas = {"https://conhecimento.fgv.br/robots.txt": (404, {}, b""), "https://conhecimento.fgv.br/e.pdf": pdf}
    c, falso = cliente(allowlist, rotas, tmp_path)
    primeiro = c.get("https://conhecimento.fgv.br/e.pdf")
    c2, _ = cliente(allowlist, rotas, tmp_path)
    segundo = c2.get("https://conhecimento.fgv.br/e.pdf")
    assert not primeiro.de_cache and segundo.de_cache
    assert segundo.conteudo == primeiro.conteudo and segundo.sha256 == primeiro.sha256


def test_tenta_de_novo_em_erro_transitorio(allowlist):
    respostas = iter([(503, {}, b""), (200, {}, b"ok")])
    c, _ = cliente(allowlist, {
        "https://conhecimento.fgv.br/robots.txt": (404, {}, b""),
        "https://conhecimento.fgv.br/x": lambda req: next(respostas),
    })
    assert c.get("https://conhecimento.fgv.br/x").conteudo == b"ok"


def test_404_vira_erro(allowlist):
    c, _ = cliente(allowlist, {"https://conhecimento.fgv.br/robots.txt": (404, {}, b"")})
    with pytest.raises(ErroColeta, match="HTTP 404"):
        c.get("https://conhecimento.fgv.br/nao-existe.pdf")


def test_intervalo_entre_requisicoes_ao_mesmo_host(allowlist):
    esperas = []
    falso = Falso({"https://conhecimento.fgv.br/robots.txt": (404, {}, b""),
                   "https://conhecimento.fgv.br/a": (200, {}, b"a"), "https://conhecimento.fgv.br/b": (200, {}, b"b")})
    s = requests.Session()
    s.mount("https://", falso)
    c = Cliente(allowlist, sessao=s, intervalo=2.0, relogio=lambda: 100.0, dormir=esperas.append)
    c.get("https://conhecimento.fgv.br/a")
    c.get("https://conhecimento.fgv.br/b")
    assert esperas and all(e == pytest.approx(2.0) for e in esperas)
