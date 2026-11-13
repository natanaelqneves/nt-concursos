// Concursos que podem reabrir: validade terminando (data/validade/*.json).
// Tipos espelham collector/src/ntc/model/validade.py; a validação acontece no `ntc validate`.
import fs from "node:fs";
import path from "node:path";
import type { Categoria, Esfera, FonteNoticia } from "./dados";
import { hojeBRT } from "./tempo";

const DIR_DADOS = process.env.NTC_DATA_DIR ?? path.resolve(process.cwd(), "..", "data");

export interface FatoValidade {
  campo: "validade" | "homologacao" | "prorrogacao" | "cargos" | "banca" | "novo_concurso";
  texto: string;
  inicio?: string | null;
  fim?: string | null;
  fontes: string[];
}

export interface Validade {
  slug: string;
  titulo: string;
  orgao: string;
  categoria: Categoria;
  esfera: Esfera;
  uf: string;
  municipio?: string | null;
  banca?: string | null;
  resumo: string;
  cargos: string[];
  fatos: FatoValidade[];
  fontes: FonteNoticia[];
  validade_ate: string;
  apurado_em: string;
}

export const NOME_FATO_VALIDADE: Record<FatoValidade["campo"], string> = {
  validade: "Validade",
  homologacao: "Homologação",
  prorrogacao: "Prorrogação",
  cargos: "Cargos",
  banca: "Banca do último concurso",
  novo_concurso: "Novo concurso",
};

let cache: Validade[] | null = null;

export function todasValidades(): Validade[] {
  if (cache) return cache;
  const dir = path.join(DIR_DADOS, "validade");
  cache = fs.existsSync(dir)
    ? fs.readdirSync(dir).filter((f) => f.endsWith(".json")).sort()
        .map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf-8")) as Validade)
    : [];
  return cache;
}

function somarDias(iso: string, dias: number): string {
  const d = new Date(`${iso}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + dias);
  return d.toISOString().slice(0, 10);
}

/** Validades que terminam nos próximos 12 meses ou terminaram há até 6 meses (contrato, 13/11/2026),
 * da que termina primeiro para a última. */
export function validadesNaPagina(hoje = hojeBRT()): Validade[] {
  const de = somarDias(hoje, -183), ate = somarDias(hoje, 365);
  return todasValidades()
    .filter((v) => v.validade_ate >= de && v.validade_ate <= ate)
    .sort((a, b) => a.validade_ate.localeCompare(b.validade_ate));
}

export const terminou = (v: Validade, hoje = hojeBRT()) => v.validade_ate < hoje;
