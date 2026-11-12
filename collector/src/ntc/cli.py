"""Linha de comando do coletor.

    ntc validate [--data DIR]    valida schema, integridade e gate de todos os concursos
    ntc schema [--check]         gera (ou confere) schema/concurso.schema.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from ntc.fetch.allowlist import Allowlist
from ntc.gate.evidencia import Gate
from ntc.model.schema import Concurso
from ntc.store.json_store import JsonStore

RAIZ = Path(__file__).resolve().parents[3]
SCHEMA_PATH = RAIZ / "schema" / "concurso.schema.json"


def _schema_json() -> str:
    return json.dumps(Concurso.model_json_schema(), ensure_ascii=False, indent=2) + "\n"


def cmd_schema(args: argparse.Namespace) -> int:
    atual = _schema_json()
    if args.check:
        if not SCHEMA_PATH.exists() or SCHEMA_PATH.read_text(encoding="utf-8") != atual:
            print("schema/concurso.schema.json desatualizado: rode `ntc schema`", file=sys.stderr)
            return 1
        print("schema em dia")
        return 0
    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_PATH.write_text(atual, encoding="utf-8")
    print(f"gravado {SCHEMA_PATH.relative_to(RAIZ)}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    data = Path(args.data)
    store = JsonStore(data)
    gate = Gate(Allowlist.carregar(data / "fontes.yaml"))
    textos = store.textos()
    erros = 0
    arquivos = sorted((data / "concursos").glob("*.json")) if (data / "concursos").exists() else []
    for caminho in arquivos:
        try:
            concurso = Concurso.model_validate_json(caminho.read_text(encoding="utf-8"))
        except ValidationError as e:
            erros += 1
            print(f"ERRO {caminho.name}: schema\n{e}", file=sys.stderr)
            continue
        if caminho.stem != concurso.slug:
            erros += 1
            print(f"ERRO {caminho.name}: nome do arquivo difere do slug", file=sys.stderr)
        for v in gate.aplicar(concurso, textos).violacoes:
            erros += 1
            print(f"ERRO {caminho.name}: {v.regra} {v.campo}: {v.mensagem}", file=sys.stderr)
    print(f"{len(arquivos)} concurso(s) verificados, {erros} erro(s)")
    return 1 if erros else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ntc")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="valida data/ inteiro")
    p_val.add_argument("--data", default=str(RAIZ / "data"))
    p_val.set_defaults(func=cmd_validate)

    p_sch = sub.add_parser("schema", help="gera o JSON Schema do contrato")
    p_sch.add_argument("--check", action="store_true")
    p_sch.set_defaults(func=cmd_schema)

    args = parser.parse_args(argv)
    return args.func(args)
