// Navegação por estado e por área: só agrupa o que já está nas listas (concursos conferidos no
// edital e notícias apuradas), sem dado novo.
import type { Categoria, Concurso, Noticia } from "./dados";
import { NOME_CATEGORIA, encerrado, noticiasAtivas, todos } from "./dados";
import { hojeBRT } from "./tempo";

export const ESTADOS: Record<string, { nome: string; prep: "do" | "da" | "de" }> = {
  AC: { nome: "Acre", prep: "do" },
  AL: { nome: "Alagoas", prep: "de" },
  AP: { nome: "Amapá", prep: "do" },
  AM: { nome: "Amazonas", prep: "do" },
  BA: { nome: "Bahia", prep: "da" },
  CE: { nome: "Ceará", prep: "do" },
  DF: { nome: "Distrito Federal", prep: "do" },
  ES: { nome: "Espírito Santo", prep: "do" },
  GO: { nome: "Goiás", prep: "de" },
  MA: { nome: "Maranhão", prep: "do" },
  MT: { nome: "Mato Grosso", prep: "de" },
  MS: { nome: "Mato Grosso do Sul", prep: "de" },
  MG: { nome: "Minas Gerais", prep: "de" },
  PA: { nome: "Pará", prep: "do" },
  PB: { nome: "Paraíba", prep: "da" },
  PR: { nome: "Paraná", prep: "do" },
  PE: { nome: "Pernambuco", prep: "de" },
  PI: { nome: "Piauí", prep: "do" },
  RJ: { nome: "Rio de Janeiro", prep: "do" },
  RN: { nome: "Rio Grande do Norte", prep: "do" },
  RS: { nome: "Rio Grande do Sul", prep: "do" },
  RO: { nome: "Rondônia", prep: "de" },
  RR: { nome: "Roraima", prep: "de" },
  SC: { nome: "Santa Catarina", prep: "de" },
  SP: { nome: "São Paulo", prep: "de" },
  SE: { nome: "Sergipe", prep: "de" },
  TO: { nome: "Tocantins", prep: "do" },
};

/** Endereço da página do estado: /estados/pb/; os concursos nacionais (uf BR) ficam em /estados/nacional/. */
export const urlEstado = (uf: string) => `/estados/${uf === "BR" ? "nacional" : uf.toLowerCase()}/`;
export const urlArea = (c: Categoria) => `/areas/${c}/`;

export interface Grupo {
  concursos: Concurso[];
  noticias: Noticia[];
}

const conferidos = (hoje: string) => todos().filter((c) => !encerrado(c, hoje));

export function porUf(uf: string, hoje = hojeBRT()): Grupo {
  return {
    concursos: conferidos(hoje).filter((c) => c.uf === uf),
    noticias: noticiasAtivas(hoje).filter((n) => n.uf === uf),
  };
}

export function porCategoria(cat: Categoria, hoje = hojeBRT()): Grupo {
  return {
    concursos: conferidos(hoje).filter((c) => c.categoria === cat),
    noticias: noticiasAtivas(hoje).filter((n) => n.categoria === cat),
  };
}

export const total = (g: Grupo) => g.concursos.length + g.noticias.length;

/** Áreas na ordem do menu ("outro" por último). */
export const AREAS = (Object.keys(NOME_CATEGORIA) as Categoria[]).sort((a, b) =>
  a === "outro" ? 1 : b === "outro" ? -1 : NOME_CATEGORIA[a].localeCompare(NOME_CATEGORIA[b], "pt-BR"),
);
