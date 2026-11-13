// Navegação por estado e por área: só agrupa o que já está nas listas (concursos conferidos no
// edital e notícias apuradas), sem dado novo.
import type { Categoria, Concurso, Noticia } from "./dados";
import { NOME_CATEGORIA, encerrado, noticiasAtivas, todos } from "./dados";
import { hojeBRT } from "./tempo";
import { validadesNaPagina } from "./validade";

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

// ---- Próximos prazos (linha do tempo da página inicial) e índice da busca rápida

import type { FatoNoticia } from "./dados";
import { fatoInscricao, isencaoAberta, inscricaoAberta, titulo, verificado } from "./dados";
import { RECORRENTES } from "./recorrentes";

export interface Prazo {
  data: string; // AAAA-MM-DD
  evento: string;
  nome: string;
  url: string;
  isencao: boolean;
  imprensa: boolean;
}

/** Datas que importam nos próximos `dias` dias: fim da isenção, fim e início das inscrições. */
export function proximosPrazos(dias = 21, hoje = hojeBRT()): Prazo[] {
  const limite = new Date(`${hoje}T12:00:00Z`);
  limite.setUTCDate(limite.getUTCDate() + dias);
  const ate = limite.toISOString().slice(0, 10);
  const dentro = (d?: string | null) => !!d && d >= hoje && d <= ate;
  const out: Prazo[] = [];
  for (const c of todos()) {
    const url = `/concursos/${c.slug}/`;
    const nome = c.orgao;
    const { isencao, inscricao } = c.prazos;
    if (verificado(isencao) && dentro(isencao.fim) && isencaoAberta(c, hoje))
      out.push({ data: isencao.fim!, evento: "Fim do pedido de isenção", nome, url, isencao: true, imprensa: false });
    if (verificado(inscricao) && dentro(inscricao.inicio) && inscricao.inicio! > hoje)
      out.push({ data: inscricao.inicio!, evento: "Início das inscrições", nome, url, isencao: false, imprensa: false });
    if (verificado(inscricao) && dentro(inscricao.fim) && (inscricaoAberta(c, hoje) || (inscricao.inicio ?? "") > hoje))
      out.push({ data: inscricao.fim!, evento: "Fim das inscrições", nome, url, isencao: false, imprensa: false });
  }
  for (const n of noticiasAtivas(hoje)) {
    const url = `/noticias/${n.slug}/`;
    const isen = n.fatos.find((f: FatoNoticia) => f.campo === "isencao");
    if (isen?.fim && dentro(isen.fim))
      out.push({ data: isen.fim, evento: "Fim do pedido de isenção", nome: n.orgao, url, isencao: true, imprensa: true });
    const insc = fatoInscricao(n);
    if (insc?.fim && dentro(insc.fim))
      out.push({ data: insc.fim, evento: "Fim das inscrições", nome: n.orgao, url, isencao: false, imprensa: true });
  }
  return out.sort((a, b) => a.data.localeCompare(b.data) || Number(b.isencao) - Number(a.isencao));
}

export interface ItemBusca {
  t: string; // título
  d: string; // descrição curta
  u: string; // endereço
  k: string; // termos extras (sem acento)
}

const semAcento = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** Índice pequeno, embutido na página: concursos, apuração, bancos recorrentes, estados e áreas. */
export function indiceBusca(hoje = hojeBRT()): ItemBusca[] {
  const itens: ItemBusca[] = [];
  for (const c of todos().filter((c) => !encerrado(c, hoje))) {
    const uf = c.uf === "BR" ? "nacional" : `${c.uf} ${ESTADOS[c.uf]?.nome ?? ""}`;
    itens.push({
      t: titulo(c), u: `/concursos/${c.slug}/`,
      d: `Conferido no edital · ${NOME_CATEGORIA[c.categoria]} · ${c.uf === "BR" ? "Nacional" : c.uf} · ${c.banca.toUpperCase()}`,
      k: semAcento(`${c.banca} ${uf} ${NOME_CATEGORIA[c.categoria]} ${c.cargos.map((x) => x.nome).join(" ")}`),
    });
  }
  for (const n of noticiasAtivas(hoje)) {
    const uf = n.uf === "BR" ? "nacional" : `${n.uf} ${ESTADOS[n.uf]?.nome ?? ""}`;
    itens.push({
      t: n.titulo, u: `/noticias/${n.slug}/`,
      d: `Apuração na imprensa · ${NOME_CATEGORIA[n.categoria]} · ${n.uf === "BR" ? "Nacional" : n.uf} · ${n.banca}`,
      k: semAcento(`${n.orgao} ${n.banca} ${uf} ${NOME_CATEGORIA[n.categoria]} ${n.cargos.join(" ")}`),
    });
  }
  for (const v of validadesNaPagina(hoje))
    itens.push({ t: `${v.orgao}: validade até ${v.validade_ate.split("-").reverse().join("/")}`, u: `/podem-reabrir/${v.slug}/`,
      d: "Podem reabrir", k: semAcento(`${v.orgao} ${v.municipio ?? ""} ${v.uf} ${ESTADOS[v.uf]?.nome ?? ""} ${v.cargos.join(" ")} validade reabrir`) });
  for (const r of RECORRENTES)
    itens.push({ t: `Concurso ${r.nome}`, u: `/recorrentes/${r.slug}/`, d: "Concursos que se repetem", k: semAcento(`banco ${r.cargos.map((c) => c.nome).join(" ")}`) });
  for (const [uf, e] of Object.entries(ESTADOS))
    itens.push({ t: `Concursos ${e.prep} ${e.nome}`, u: urlEstado(uf), d: "Por estado", k: semAcento(`${uf} ${e.nome}`) });
  for (const c of AREAS)
    itens.push({ t: NOME_CATEGORIA[c], u: urlArea(c), d: "Por área", k: c });
  return itens;
}
