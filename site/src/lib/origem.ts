// De onde veio cada documento e onde a pesquisa foi feita (fim da página do concurso).
// Os nomes das cópias espelham as entradas com `papel: copia` em data/fontes.yaml.
import fs from "node:fs";
import path from "node:path";
import type { Concurso, Documento } from "./dados";

const DIR_DADOS = process.env.NTC_DATA_DIR ?? path.resolve(process.cwd(), "..", "data");

export const COPIAS: Record<string, string> = {
  qconcursos: "Qconcursos",
  direcao: "Direção Concursos",
  jcconcursos: "JC Concursos",
  novaconcursos: "Nova Concursos",
  editorasolucao: "Editora Solução",
  magistrar: "Magistrar Cursos",
  acheconcursos: "Ache Concursos",
  "cdn-cloudfront": "um portal de concursos (CDN)",
};

const BANCAS: Record<string, string> = {
  fgv: "FGV Conhecimento",
  cebraspe: "Cebraspe",
  aocp: "Instituto AOCP",
  fcc: "Fundação Carlos Chagas",
  vunesp: "Vunesp",
  idecan: "Idecan",
  comperve: "Comperve/UFRN",
  access: "Instituto Access",
  inlabs: "Imprensa Nacional (Diário Oficial da União)",
};

export const ehCopia = (d: Documento) => d.fonte in COPIAS;
export const host = (d: Documento) => new URL(d.url_final).hostname.replace(/^www\./, "");

/** "site oficial (trf3.jus.br)" ou "cópia publicada por Qconcursos (arquivos.qconcursos.com)". */
export function origemDoc(d: Documento): string {
  if (ehCopia(d)) return `cópia publicada por ${COPIAS[d.fonte]} (${host(d)})`;
  const nome = BANCAS[d.fonte];
  return nome ? `site oficial da banca ${nome} (${host(d)})` : `site oficial (${host(d)})`;
}

export interface Avulso {
  slug: string;
  noticia?: string;
  pesquisa: string[];
}

let cache: Avulso[] | null = null;
export function avulsos(): Avulso[] {
  if (cache) return cache;
  const arq = path.join(DIR_DADOS, "editais-avulsos.json");
  cache = fs.existsSync(arq) ? (JSON.parse(fs.readFileSync(arq, "utf-8")).concursos as Avulso[]) : [];
  return cache;
}

export const avulsoDe = (c: Concurso) => avulsos().find((a) => a.slug === c.slug);

/** Notícia da imprensa -> concurso conferido que a substitui. */
export function substituicoes(): Map<string, string> {
  return new Map(avulsos().filter((a) => a.noticia).map((a) => [a.noticia!, a.slug]));
}
