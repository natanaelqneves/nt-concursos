import pytest


@pytest.mark.parametrize(
    "url",
    [
        "https://www.in.gov.br/web/dou",
        "https://exemplo.pb.gov.br/edital.pdf",
        "https://www.tjsp.jus.br/concursos",
        "https://conhecimento.fgv.br/concursos/x",
        "https://cdn.cebraspe.org.br/concursos/x.pdf",
    ],
)
def test_aceita(allowlist, url):
    assert allowlist.permitido(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://www.in.gov.br/web/dou",
        "https://gov.br.golpe.com/edital.pdf",
        "https://fakegov.br/edital.pdf",
        "https://fgv.br.exemplo.com/edital.pdf",
        "https://blogdeconcursos.com.br/edital.pdf",
    ],
)
def test_recusa(allowlist, url):
    assert not allowlist.permitido(url)
