// Leitura de data/concursos no build. Tipos espelham collector/src/ntc/model/schema.py;
// a validação de verdade acontece no `ntc validate`, que roda antes de todo build.
import fs from "node:fs";
import path from "node:path";
import { hojeBRT } from "./tempo";

export type Status = "verificado" | "revisao" | "ausente";

export interface Prazo {
  inicio?: string | null;
  fim?: string | null;
  status: Status;
  evidencia?: string | null;
}

export interface Campo {
  valor?: number | string | null;
  status: Status;
  evidencia?: string | null;
}

export interface Documento {
  id: string;
  tipo: "edital" | "retificacao" | "aviso" | "dou";
  url: string;
  url_final: string;
  sha256: string;
  coletado_em: string;
  fonte: string;
}

export interface Evidencia {
  id: string;
  campo: string;
  documento: string;
  pagina: number;
  trecho: string;
  ancora: string;
  metodo: string;
  aprovado_por?: string | null;
  aprovado_em?: string | null;
}

export interface Concurso {
  schema_version: 1;
  slug: string;
  orgao: string;
  banca: string;
  uf: string;
  cargos: { nome: string; vagas?: Campo | null; remuneracao?: Campo | null }[];
  taxa?: Campo | null;
  prazos: { isencao: Prazo; inscricao: Prazo };
  isencao_publicos: string[];
  documentos: Documento[];
  evidencias: Evidencia[];
  conferido_em: string;
}

const DIR_DADOS = process.env.NTC_DATA_DIR ?? path.resolve(process.cwd(), "..", "data");

let cache: Concurso[] | null = null;

export function todos(): Concurso[] {
  if (cache) return cache;
  const dir = path.join(DIR_DADOS, "concursos");
  const arquivos = fs.existsSync(dir) ? fs.readdirSync(dir).filter((f) => f.endsWith(".json")) : [];
  cache = arquivos
    .sort()
    .map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf-8")) as Concurso);
  return cache;
}

export const verificado = (p?: Prazo | Campo | null): boolean => p?.status === "verificado";

function dentro(p: Prazo, hoje: string): boolean {
  if (!verificado(p) || !p.fim) return false;
  return (!p.inicio || p.inicio <= hoje) && hoje <= p.fim;
}

export const isencaoAberta = (c: Concurso, hoje = hojeBRT()) => dentro(c.prazos.isencao, hoje);
export const inscricaoAberta = (c: Concurso, hoje = hojeBRT()) => dentro(c.prazos.inscricao, hoje);

export function encerrado(c: Concurso, hoje = hojeBRT()): boolean {
  const fim = c.prazos.inscricao.fim;
  return verificado(c.prazos.inscricao) && !!fim && fim < hoje;
}

const porFim = (sel: (c: Concurso) => string | null | undefined) => (a: Concurso, b: Concurso) =>
  (sel(a) ?? "9999").localeCompare(sel(b) ?? "9999");

export function comIsencaoAberta(hoje = hojeBRT()): Concurso[] {
  return todos()
    .filter((c) => isencaoAberta(c, hoje))
    .sort(porFim((c) => c.prazos.isencao.fim));
}

export function inscricoesAbertasSemIsencao(hoje = hojeBRT()): Concurso[] {
  return todos()
    .filter((c) => inscricaoAberta(c, hoje) && !isencaoAberta(c, hoje))
    .sort(porFim((c) => c.prazos.inscricao.fim));
}

export function evidenciaDe(c: Concurso, campo?: Prazo | Campo | null) {
  if (!campo?.evidencia) return null;
  const ev = c.evidencias.find((e) => e.id === campo.evidencia);
  const doc = ev ? c.documentos.find((d) => d.id === ev.documento) : undefined;
  return ev && doc ? { ev, doc } : null;
}

export function titulo(c: Concurso): string {
  const cargos = c.cargos.map((x) => x.nome);
  const resumo = cargos.length > 2 ? `${cargos.slice(0, 2).join(", ")} e outros` : cargos.join(" e ");
  return resumo ? `${c.orgao} – ${resumo}` : c.orgao;
}
