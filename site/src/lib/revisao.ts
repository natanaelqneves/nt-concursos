// Pendências de revisão (data/revisao) e decisões do editor (data/decisoes), lidas no build
// para a página /admin/. Formato em docs/CONTRATO-DADOS.md ("Revisão e decisões do editor").
import fs from "node:fs";
import path from "node:path";

const DIR_DADOS = process.env.NTC_DATA_DIR ?? path.resolve(process.cwd(), "..", "data");

export const REPO = "natanaelqneves/nt-concursos";

export interface Opcao {
  id: string;
  origem: "texto" | "tabela";
  pagina: number;
  trecho: string;
  ancora: string;
  inicio: string | null;
  fim: string;
  tabela?: { atividade: string; datas: string };
}

export interface Revisao {
  schema_version?: number;
  slug: string;
  orgao: string;
  situacao?: string;
  categoria?: string;
  esfera?: string;
  uf?: string;
  cargos?: string[];
  fonte: string;
  url: string;
  edital: string;
  edital_sha256?: string;
  campos_em_revisao: string[];
  motivos: string[];
  opcoes?: Record<string, Opcao[]>;
  mudancas?: { titulo: string; url: string; publicado_em: string | null }[];
  registrado_em: string;
}

export interface DecisaoResumo {
  arquivo: string;
  decidido_em: string;
  acao: string;
}

export const NOME_CAMPO: Record<string, string> = {
  "prazos.isencao": "Prazo de isenção da taxa",
  "prazos.inscricao": "Prazo de inscrição",
  vagas_imediatas: "Vagas imediatas",
};

export function todasRevisoes(): Revisao[] {
  const dir = path.join(DIR_DADOS, "revisao");
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf-8")) as Revisao)
    .sort((a, b) => Number(b.situacao === "publicado") - Number(a.situacao === "publicado") || a.slug.localeCompare(b.slug));
}

/** Última decisão já gravada para o concurso, se houver (a coleta seguinte é que aplica). */
export function ultimaDecisao(slug: string): DecisaoResumo | null {
  const dir = path.join(DIR_DADOS, "decisoes", slug);
  if (!fs.existsSync(dir)) return null;
  const arquivos = fs.readdirSync(dir).filter((f) => f.endsWith(".json")).sort();
  if (!arquivos.length) return null;
  const arquivo = arquivos[arquivos.length - 1];
  try {
    const d = JSON.parse(fs.readFileSync(path.join(dir, arquivo), "utf-8"));
    return { arquivo, decidido_em: d.decidido_em, acao: d.acao };
  } catch {
    return { arquivo, decidido_em: "", acao: "inválida" };
  }
}

export function dataBR(iso: string | null | undefined): string {
  if (!iso) return "";
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

export function intervalo(o: Opcao): string {
  return o.inicio ? `${dataBR(o.inicio)} a ${dataBR(o.fim)}` : `até ${dataBR(o.fim)}`;
}
