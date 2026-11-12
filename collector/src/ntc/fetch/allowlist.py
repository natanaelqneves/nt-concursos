"""Allowlist de domínios oficiais, carregada de data/fontes.yaml.

A comparação é sempre feita sobre o host da URL *final* (após redirecionamentos).
Um domínio `d` aceita `d` e qualquer subdomínio `*.d`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import yaml


@dataclass(frozen=True)
class Allowlist:
    sufixos_oficiais: tuple[str, ...]
    dominios_por_fonte: dict[str, tuple[str, ...]]

    @classmethod
    def carregar(cls, caminho: Path) -> Allowlist:
        bruto = yaml.safe_load(caminho.read_text(encoding="utf-8"))
        fontes = {
            nome: tuple(d.lower() for d in cfg.get("dominios", []))
            for nome, cfg in (bruto.get("fontes") or {}).items()
        }
        sufixos = tuple(s.lower().lstrip(".") for s in bruto.get("sufixos_oficiais", []))
        return cls(sufixos_oficiais=sufixos, dominios_por_fonte=fontes)

    def _todos(self) -> tuple[str, ...]:
        extras = tuple(d for ds in self.dominios_por_fonte.values() for d in ds)
        return self.sufixos_oficiais + extras

    def permitido(self, url: str) -> bool:
        partes = urlsplit(url)
        if partes.scheme != "https":
            return False
        host = (partes.hostname or "").lower().rstrip(".")
        return any(host == d or host.endswith("." + d) for d in self._todos())
