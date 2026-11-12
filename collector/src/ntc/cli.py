"""Linha de comando do coletor.

    ntc collect --fonte fgv|cebraspe|inlabs [--so ID ...] [--data-dou AAAA-MM-DD]
                                 coleta uma fonte, grava data/ e o log em data/execucoes/
    ntc validate [--data DIR]    valida schema, integridade e gate de todos os concursos
    ntc schema [--check]         gera (ou confere) schema/concurso.schema.json

Códigos de saída do collect: 0 ok (mesmo com erro em concursos isolados), 1 a fonte falhou,
3 fonte indisponível no momento (ex.: DOU do dia ainda não saiu, INLABS em manutenção).
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


def cmd_collect(args: argparse.Namespace) -> int:
    import os
    from datetime import date, datetime

    from ntc.coleta import Coletor, Registro, resumo
    from ntc.fetch.http import BRT, Cliente, ErroColeta
    from ntc.sources.cebraspe import Cebraspe
    from ntc.sources.fgv import FGV
    from ntc.sources.inlabs import Inlabs, Indisponivel, SemCredenciais, no_escopo

    data = Path(args.data)
    allowlist = Allowlist.carregar(data / "fontes.yaml")
    cliente = Cliente(allowlist, cache_dir=Path(args.cache) if args.cache else None, intervalo=args.intervalo)
    store = JsonStore(data)
    inicio = datetime.now(BRT).replace(microsecond=0)
    so = set(args.so) if args.so else None
    registros: list[Registro] = []
    erro_fonte: str | None = None
    codigo = 0

    if args.fonte == "inlabs":
        data_dou = date.fromisoformat(args.data_dou) if args.data_dou else inicio.date()
        fonte = Inlabs(os.environ.get("INLABS_EMAIL"), os.environ.get("INLABS_SENHA"), data_dou)
        descobertas = []
        try:
            for cf in fonte.descobrir(cliente):
                cls = no_escopo(cf)
                reg = Registro(cf.fonte, cf.id, cf.titulo, "descoberto" if cls else "fora_do_escopo",
                               f"{cls.categoria}/{cls.esfera}/{cls.uf}" if cls else "")
                registros.append(reg)
                if cls:
                    descobertas.append({"id": cf.id, "titulo": cf.titulo, "orgao": cls.orgao,
                                        "categoria": cls.categoria, "esfera": cls.esfera, "uf": cls.uf,
                                        "url": cf.url, "data_dou": data_dou.isoformat()})
        except (SemCredenciais, Indisponivel) as e:
            erro_fonte, codigo = f"{type(e).__name__}: {e}", 3
        except ErroColeta as e:
            erro_fonte, codigo = f"{type(e).__name__}: {e}", 1
        if descobertas:
            destino = data / "descobertas" / f"{data_dou.isoformat()}.json"
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(json.dumps(descobertas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        fonte = {"fgv": FGV, "cebraspe": Cebraspe}[args.fonte](so)
        coletor = Coletor(cliente, store, allowlist)
        try:
            import time

            for cf in fonte.descobrir(cliente):
                t0 = time.monotonic()
                reg = coletor.processar(cf)
                registros.append(reg)
                print(f"{time.monotonic() - t0:6.1f}s {reg.situacao:14} {cf.fonte}:{cf.id} {reg.slug or ''} "
                      f"{reg.campos or ''} {reg.detalhe[:200]}", flush=True)
        except ErroColeta as e:
            erro_fonte, codigo = f"{type(e).__name__}: {e}", 1

    corpo = {"inicio": inicio.isoformat(), "fim": datetime.now(BRT).replace(microsecond=0).isoformat(),
             "erro_fonte": erro_fonte, **resumo(registros)}
    store.salvar_execucao(inicio.date().isoformat(), args.fonte, corpo)
    print(json.dumps({"fonte": args.fonte, "erro_fonte": erro_fonte, "contagem": corpo["contagem"]}, ensure_ascii=False))
    if erro_fonte:
        print(f"fonte {args.fonte}: {erro_fonte}", file=sys.stderr)
    return codigo


def cmd_inlabs_horario(args: argparse.Namespace) -> int:
    """Uma sondagem: o ZIP da seção 3 de hoje já está no INLABS? Imprime uma linha JSON."""
    import os
    from datetime import date, datetime

    from ntc.fetch.http import BRT, Cliente, ErroColeta
    from ntc.sources.inlabs import Inlabs, Indisponivel, SemCredenciais

    agora = datetime.now(BRT).replace(microsecond=0)
    data_dou = date.fromisoformat(args.data_dou) if args.data_dou else agora.date()
    cliente = Cliente(Allowlist.carregar(Path(args.data) / "fontes.yaml"), intervalo=1.0, tentativas=1)
    fonte = Inlabs(os.environ.get("INLABS_EMAIL"), os.environ.get("INLABS_SENHA"), data_dou)
    linha = {"verificado_em": agora.isoformat(), "data_dou": data_dou.isoformat(), "secao": "DO3"}
    try:
        fonte.login(cliente)
        linha |= {"status": "disponivel", "bytes": len(fonte.baixar(cliente, "DO3"))}
    except SemCredenciais:
        linha["status"] = "sem_credenciais"
    except Indisponivel as e:
        linha |= {"status": "manutencao" if "manuten" in str(e) else "ausente", "detalhe": str(e)}
    except ErroColeta as e:
        linha |= {"status": "erro", "detalhe": str(e)[:300]}
    print(json.dumps(linha, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ntc")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="valida data/ inteiro")
    p_val.add_argument("--data", default=str(RAIZ / "data"))
    p_val.set_defaults(func=cmd_validate)

    p_col = sub.add_parser("collect", help="coleta uma fonte")
    p_col.add_argument("--fonte", required=True, choices=["fgv", "cebraspe", "inlabs"])
    p_col.add_argument("--so", nargs="*", help="só estes ids da fonte (ex.: tjpb26, PC_PE_26)")
    p_col.add_argument("--data", default=str(RAIZ / "data"))
    p_col.add_argument("--cache", default=None, help="diretório de cache HTTP (ETag)")
    p_col.add_argument("--intervalo", type=float, default=2.0, help="segundos entre requisições ao mesmo host")
    p_col.add_argument("--data-dou", default=None, help="inlabs: data da edição (padrão: hoje em BRT)")
    p_col.set_defaults(func=cmd_collect)

    p_hor = sub.add_parser("inlabs-horario", help="sonda se o DO3 do dia já saiu no INLABS")
    p_hor.add_argument("--data", default=str(RAIZ / "data"))
    p_hor.add_argument("--data-dou", default=None)
    p_hor.set_defaults(func=cmd_inlabs_horario)

    p_sch = sub.add_parser("schema", help="gera o JSON Schema do contrato")
    p_sch.add_argument("--check", action="store_true")
    p_sch.set_defaults(func=cmd_schema)

    args = parser.parse_args(argv)
    return args.func(args)
