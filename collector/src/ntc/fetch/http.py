"""Cliente HTTP do coletor.

Garantias, nesta ordem, para toda requisição:
1. a URL pedida e cada redirecionamento estão na allowlist (G1 antes de baixar);
2. o robots.txt do host permite o caminho (RFC 9309: 4xx = sem restrição, 5xx/erro = tudo proibido);
3. intervalo mínimo entre requisições ao mesmo host;
4. cache condicional (ETag / Last-Modified) para não rebaixar o que não mudou;
5. limite de tamanho e novas tentativas só para erros transitórios (rede, 429, 5xx).

Nada de mascarar IP, rodar proxies ou contornar bloqueio: se a fonte recusar, o erro sobe.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo

import requests

from ntc.fetch.allowlist import Allowlist

USER_AGENT = "ntconcursos-coletor/0.2 (+https://ntconcursos.com.br/metodologia/; contato@ntconcursos.com.br)"
BRT = ZoneInfo("America/Sao_Paulo")
MAX_REDIRECTS = 5
TRANSITORIOS = {429, 500, 502, 503, 504}


class ErroColeta(Exception):
    """Falha que impede usar a resposta. A mensagem vai para o log da execução."""


class ForaDaAllowlist(ErroColeta):
    pass


class BloqueadoPorRobots(ErroColeta):
    pass


@dataclass(frozen=True)
class Resposta:
    url: str
    url_final: str
    status: int
    conteudo: bytes
    tipo: str
    coletado_em: datetime
    de_cache: bool = False

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.conteudo).hexdigest()

    def texto(self) -> str:
        return self.conteudo.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.conteudo)


@dataclass
class Cliente:
    allowlist: Allowlist
    cache_dir: Path | None = None
    intervalo: float = 2.0
    timeout: float = 60.0
    max_bytes: int = 80 * 1024 * 1024
    tentativas: int = 3
    sessao: requests.Session = field(default_factory=requests.Session)
    relogio: Callable[[], float] = time.monotonic
    dormir: Callable[[float], None] = time.sleep
    agora: Callable[[], datetime] = lambda: datetime.now(BRT).replace(microsecond=0)
    _ultimo: dict[str, float] = field(default_factory=dict)
    _robots: dict[str, RobotFileParser | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.sessao.headers["User-Agent"] = USER_AGENT
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ---- API pública -------------------------------------------------------------

    def get(self, url: str, *, headers: dict[str, str] | None = None, usar_cache: bool = True) -> Resposta:
        return self._requisitar("GET", url, headers=headers or {}, usar_cache=usar_cache)

    def post(self, url: str, *, data: dict[str, str], headers: dict[str, str] | None = None) -> Resposta:
        return self._requisitar("POST", url, headers=headers or {}, data=data, usar_cache=False)

    # ---- internos ----------------------------------------------------------------

    def _checar(self, url: str) -> None:
        if not self.allowlist.permitido(url):
            raise ForaDaAllowlist(f"fora da allowlist: {url}")
        if not self._robots_permite(url):
            raise BloqueadoPorRobots(f"robots.txt não permite: {url}")

    def _robots_permite(self, url: str) -> bool:
        partes = urlsplit(url)
        origem = f"{partes.scheme}://{partes.netloc}"
        if origem not in self._robots:
            self._robots[origem] = self._carregar_robots(origem)
        rp = self._robots[origem]
        return True if rp is None else rp.can_fetch(USER_AGENT, url)

    def _carregar_robots(self, origem: str) -> RobotFileParser | None:
        """None = sem restrições. Erro de rede/5xx = proibido (RobotFileParser vazio com disallow_all)."""
        rp = RobotFileParser()
        try:
            self._esperar(origem)
            r = self.sessao.get(f"{origem}/robots.txt", timeout=self.timeout, allow_redirects=True)
        except requests.RequestException:
            rp.disallow_all = True
            return rp
        if 400 <= r.status_code < 500:
            return None
        if r.status_code >= 500:
            rp.disallow_all = True
            return rp
        conteudo = r.text
        if "<html" in conteudo[:500].lower():  # servidor devolve página HTML no lugar do robots
            return None
        rp.parse(conteudo.splitlines())
        return rp

    def _esperar(self, url: str) -> None:
        host = urlsplit(url).netloc
        ultimo = self._ultimo.get(host)
        if ultimo is not None:
            falta = self.intervalo - (self.relogio() - ultimo)
            if falta > 0:
                self.dormir(falta)
        self._ultimo[host] = self.relogio()

    def _chave_cache(self, url: str) -> str:
        return hashlib.sha1(url.encode()).hexdigest()

    def _ler_cache(self, url: str) -> tuple[dict, bytes] | None:
        if not self.cache_dir:
            return None
        base = self.cache_dir / self._chave_cache(url)
        meta, corpo = base.with_suffix(".json"), base.with_suffix(".bin")
        if not (meta.exists() and corpo.exists()):
            return None
        return json.loads(meta.read_text(encoding="utf-8")), corpo.read_bytes()

    def _gravar_cache(self, url: str, r: requests.Response, corpo: bytes) -> None:
        if not self.cache_dir:
            return
        etag, modificado = r.headers.get("ETag"), r.headers.get("Last-Modified")
        if not (etag or modificado):
            return
        base = self.cache_dir / self._chave_cache(url)
        base.with_suffix(".bin").write_bytes(corpo)
        meta = {"url": url, "url_final": r.url, "etag": etag, "last_modified": modificado,
                "tipo": r.headers.get("Content-Type", "")}
        base.with_suffix(".json").write_text(json.dumps(meta), encoding="utf-8")

    def _requisitar(
        self, metodo: str, url: str, *, headers: dict[str, str], usar_cache: bool, data: dict | None = None
    ) -> Resposta:
        cache = self._ler_cache(url) if (usar_cache and metodo == "GET") else None
        if cache:
            meta, _ = cache
            if meta.get("etag"):
                headers = {**headers, "If-None-Match": meta["etag"]}
            if meta.get("last_modified"):
                headers = {**headers, "If-Modified-Since": meta["last_modified"]}

        atual = url
        for _ in range(MAX_REDIRECTS + 1):
            self._checar(atual)
            r = self._com_tentativas(metodo, atual, headers, data)
            if r.is_redirect or r.status_code in (301, 302, 303, 307, 308):
                destino = r.headers.get("Location")
                r.close()
                if not destino:
                    raise ErroColeta(f"redirecionamento sem Location: {atual}")
                atual = urljoin(atual, destino)
                if r.status_code == 303:
                    metodo, data = "GET", None
                continue
            break
        else:
            raise ErroColeta(f"redirecionamentos demais a partir de {url}")

        if r.status_code == 304 and cache:
            meta, corpo = cache
            r.close()
            return Resposta(url, meta["url_final"], 200, corpo, meta.get("tipo", ""), self.agora(), True)
        corpo = self._ler_corpo(r, atual)
        if r.status_code >= 400:
            raise ErroColeta(f"HTTP {r.status_code} em {atual}")
        self._gravar_cache(url, r, corpo)
        return Resposta(url, atual, r.status_code, corpo, r.headers.get("Content-Type", ""), self.agora())

    def _com_tentativas(self, metodo: str, url: str, headers: dict, data: dict | None) -> requests.Response:
        ultimo_erro: Exception | None = None
        for n in range(1, self.tentativas + 1):
            self._esperar(url)
            try:
                r = self.sessao.request(
                    metodo, url, headers=headers, data=data, timeout=self.timeout,
                    allow_redirects=False, stream=True,
                )
            except (requests.ConnectionError, requests.Timeout) as e:
                ultimo_erro = e
            else:
                if r.status_code not in TRANSITORIOS or n == self.tentativas:
                    return r
                ultimo_erro = ErroColeta(f"HTTP {r.status_code}")
                espera = _retry_after(r.headers.get("Retry-After"))
                r.close()
                self.dormir(espera if espera is not None else 5.0 * 3 ** (n - 1))
                continue
            if n < self.tentativas:
                self.dormir(5.0 * 3 ** (n - 1))
        raise ErroColeta(f"{metodo} {url} falhou após {self.tentativas} tentativas: {ultimo_erro}")

    def _ler_corpo(self, r: requests.Response, url: str) -> bytes:
        partes, total = [], 0
        try:
            for bloco in r.iter_content(64 * 1024):
                total += len(bloco)
                if total > self.max_bytes:
                    raise ErroColeta(f"resposta maior que {self.max_bytes} bytes: {url}")
                partes.append(bloco)
        finally:
            r.close()
        return b"".join(partes)


def _retry_after(valor: str | None) -> float | None:
    if valor and valor.strip().isdigit():
        return min(float(valor), 120.0)
    return None
