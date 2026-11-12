"""Leitura e escrita determinística dos arquivos de data/.

A saída é estável (mesma entrada -> mesmos bytes) para que o `git diff` mostre
apenas mudanças reais de dados.
"""

from __future__ import annotations

import json
from pathlib import Path

from ntc.gate.evidencia import TextoDocumento
from ntc.model.decisao import Decisao
from ntc.model.schema import Concurso


def _dump(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


class JsonStore:
    def __init__(self, raiz: Path):
        self.raiz = raiz
        self.dir_concursos = raiz / "concursos"
        self.dir_documentos = raiz / "documentos"
        self.dir_revisao = raiz / "revisao"
        self.dir_execucoes = raiz / "execucoes"
        self.dir_decisoes = raiz / "decisoes"

    def decisao(self, slug: str) -> Decisao | None:
        """A decisão mais recente do editor para o concurso (o nome do arquivo ordena)."""
        pasta = self.dir_decisoes / slug
        arquivos = sorted(pasta.glob("*.json")) if pasta.exists() else []
        if not arquivos:
            return None
        d = Decisao.model_validate_json(arquivos[-1].read_text(encoding="utf-8"))
        return d if d.slug == slug else None

    def concursos(self) -> list[tuple[Path, Concurso]]:
        if not self.dir_concursos.exists():
            return []
        return [
            (p, Concurso.model_validate_json(p.read_text(encoding="utf-8")))
            for p in sorted(self.dir_concursos.glob("*.json"))
        ]

    def salvar_concurso(self, concurso: Concurso) -> Path:
        self.dir_concursos.mkdir(parents=True, exist_ok=True)
        caminho = self.dir_concursos / f"{concurso.slug}.json"
        caminho.write_text(_dump(concurso.model_dump(mode="json")), encoding="utf-8")
        return caminho

    def textos(self) -> dict[str, TextoDocumento]:
        """Textos armazenados (parciais: só páginas-âncora). `completo` é sempre False."""
        resultado: dict[str, TextoDocumento] = {}
        if not self.dir_documentos.exists():
            return resultado
        for p in sorted(self.dir_documentos.glob("*.json")):
            bruto = json.loads(p.read_text(encoding="utf-8"))
            resultado[bruto["sha256"]] = TextoDocumento(
                sha256=bruto["sha256"],
                paginas={int(k): v for k, v in bruto["paginas"].items()},
                completo=False,
                tem_texto=bruto.get("tem_texto", True),
            )
        return resultado

    def salvar_texto(self, texto: TextoDocumento, url_final: str, paginas: set[int]) -> Path:
        """Persiste apenas as páginas citadas por evidências."""
        self.dir_documentos.mkdir(parents=True, exist_ok=True)
        caminho = self.dir_documentos / f"{texto.sha256}.json"
        corpo = {
            "sha256": texto.sha256,
            "url_final": url_final,
            "tem_texto": texto.tem_texto,
            "paginas": {str(n): texto.paginas[n] for n in sorted(paginas) if n in texto.paginas},
        }
        caminho.write_text(_dump(corpo), encoding="utf-8")
        return caminho

    def salvar_revisao(self, slug: str, corpo: dict) -> Path:
        self.dir_revisao.mkdir(parents=True, exist_ok=True)
        caminho = self.dir_revisao / f"{slug}.json"
        caminho.write_text(_dump(corpo), encoding="utf-8")
        return caminho

    def remover_revisao(self, slug: str) -> None:
        (self.dir_revisao / f"{slug}.json").unlink(missing_ok=True)

    def salvar_execucao(self, dia: str, fonte: str, corpo: dict) -> Path:
        """Uma entrada por fonte e dia; a coleta seguinte da mesma fonte no mesmo dia substitui."""
        self.dir_execucoes.mkdir(parents=True, exist_ok=True)
        caminho = self.dir_execucoes / f"{dia}.json"
        atual = json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else {}
        atual[fonte] = corpo
        caminho.write_text(_dump(dict(sorted(atual.items()))), encoding="utf-8")
        return caminho
