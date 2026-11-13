// Leitura de data/concursos no build. Tipos espelham collector/src/ntc/model/schema.py;
// a validação de verdade acontece no `ntc validate`, que roda antes de todo build.
import fs from "node:fs";
import path from "node:path";
import { hojeBRT } from "./tempo";
import { substituicoes } from "./origem";

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
  publicado_em?: string | null;
  titulo?: string | null;
}

export type Categoria = "tribunal" | "controle" | "mp" | "defensoria" | "seguranca" | "estatal" | "conselho" | "fiscal" | "advocacia" | "executivo" | "legislativo" | "educacao" | "saude" | "militar" | "guarda" | "transito" | "vigilancia" | "prefeitura" | "outro";
export type Esfera = "federal" | "estadual" | "municipal";
export type Porte = "grande" | "medio" | "pequeno" | "indefinido";

export const NOME_CATEGORIA: Record<Categoria, string> = {
  tribunal: "Tribunais",
  controle: "Controle e contas",
  mp: "Ministério Público",
  defensoria: "Defensoria Pública",
  seguranca: "Segurança pública",
  estatal: "Empresas públicas",
  conselho: "Conselhos profissionais",
  fiscal: "Fiscal e Receita",
  advocacia: "Advocacia pública",
  executivo: "Executivo e gestão",
  legislativo: "Legislativo",
  educacao: "Educação",
  saude: "Saúde",
  militar: "Forças Armadas",
  guarda: "Guardas municipais",
  transito: "Trânsito",
  vigilancia: "Vigilância",
  prefeitura: "Prefeituras das capitais",
  outro: "Outros órgãos",
};

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
  tabela?: { atividade: string; datas: string } | null;
}

export type TipoEtapa =
  | "prova_objetiva" | "prova_discursiva" | "prova_pratica" | "taf" | "avaliacao_psicologica"
  | "avaliacao_medica" | "investigacao_social" | "titulos" | "heteroidentificacao" | "curso_formacao"
  | "gabarito" | "resultado" | "resultado_final" | "homologacao" | "outra";

export interface Etapa {
  tipo: TipoEtapa;
  nome: string;
  inicio?: string | null;
  fim?: string | null;
  status: Status;
  evidencia?: string | null;
}

export interface Concurso {
  schema_version: 2;
  slug: string;
  orgao: string;
  categoria: Categoria;
  esfera: Esfera;
  banca: string;
  uf: string;
  municipio?: string | null;
  cargos: { nome: string; vagas?: Campo | null; remuneracao?: Campo | null }[];
  vagas_imediatas?: Campo | null;
  porte: Porte;
  areas?: "ti"[];
  taxa?: Campo | null;
  prazos: { isencao: Prazo; inscricao: Prazo };
  etapas?: Etapa[];
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

export const verificado = (p?: Prazo | Campo | Etapa | null): boolean => p?.status === "verificado";

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

// "Em andamento" (Parte 1): inscrições encerradas há até ~6 meses e etapas conferidas no cronograma.
export const JANELA_ANDAMENTO_DIAS = 183;

export const NOME_ETAPA: Record<TipoEtapa, string> = {
  prova_objetiva: "Prova objetiva", prova_discursiva: "Prova discursiva", prova_pratica: "Prova prática",
  taf: "Teste de aptidão física", avaliacao_psicologica: "Avaliação psicológica", avaliacao_medica: "Avaliação médica",
  investigacao_social: "Investigação social", titulos: "Avaliação de títulos", heteroidentificacao: "Heteroidentificação",
  curso_formacao: "Curso de formação", gabarito: "Gabarito", resultado: "Resultado", resultado_final: "Resultado final",
  homologacao: "Homologação", outra: "Etapa",
};

export function etapasVerificadas(c: Concurso): Etapa[] {
  return (c.etapas ?? []).filter((e) => verificado(e) && !!e.fim);
}

function menosDias(dia: string, n: number): string {
  const d = new Date(`${dia}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() - n);
  return d.toISOString().slice(0, 10);
}

export function emAndamento(c: Concurso, hoje = hojeBRT()): boolean {
  return encerrado(c, hoje) && etapasVerificadas(c).length > 0
    && (c.prazos.inscricao.fim ?? "") >= menosDias(hoje, JANELA_ANDAMENTO_DIAS);
}

export function proximaEtapa(c: Concurso, hoje = hojeBRT()): Etapa | undefined {
  return etapasVerificadas(c).find((e) => (e.fim ?? "") >= hoje);
}

/** Em andamento, com a próxima etapa mais perto primeiro; os sem etapa futura vão ao fim. */
export function concursosEmAndamento(hoje = hojeBRT()): Concurso[] {
  return todos().filter((c) => emAndamento(c, hoje))
    .sort(porFim((c) => proximaEtapa(c, hoje)?.fim));
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

/** Maiores concursos com inscrição aberta: porte (vagas imediatas), depois esfera federal. */
export function emDestaque(limite = 4, hoje = hojeBRT()): Concurso[] {
  const vagas = (c: Concurso) => (verificado(c.vagas_imediatas) ? Number(c.vagas_imediatas!.valor) : 0);
  return todos()
    .filter((c) => inscricaoAberta(c, hoje) && c.porte === "grande")
    .sort((a, b) => vagas(b) - vagas(a) || Number(b.esfera === "federal") - Number(a.esfera === "federal"))
    .slice(0, limite);
}

export function local(c: Concurso): string {
  return c.uf === "BR" ? "Nacional" : c.uf;
}

/** "Federal", "Estadual" ou "Municipal · João Pessoa". */
export function textoEsfera(x: { esfera: Esfera; municipio?: string | null }): string {
  if (x.esfera === "municipal") return `Municipal · ${x.municipio ?? ""}`;
  return x.esfera === "federal" ? "Federal" : "Estadual";
}

export function evidenciaDe(c: Concurso, campo?: Prazo | Campo | Etapa | null) {
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

export interface Orgao {
  resumo: string;
  site?: string;
  revisado: boolean;
}

let orgaos: Record<string, Orgao> | null = null;

/** Resumo do órgão, só se alguém o revisou (`revisado: true` em data/orgaos.json). */
export function orgaoRevisado(nome: string): Orgao | null {
  if (!orgaos) {
    const arq = path.join(DIR_DADOS, "orgaos.json");
    orgaos = fs.existsSync(arq) ? JSON.parse(fs.readFileSync(arq, "utf-8")) : {};
  }
  const o = orgaos![nome];
  return o && o.revisado === true && typeof o.resumo === "string" ? o : null;
}

// ---- Notícias apuradas em fontes de imprensa (seção separada, nunca misturada às listas verificadas)

export interface FonteNoticia {
  id: string;
  nome: string;
  url: string;
  oficial: boolean;
  consultado_em: string;
}

export interface FatoNoticia {
  campo: "inscricao" | "isencao" | "vagas" | "taxa" | "prova" | "remuneracao" | "banca" | "cargos"
    | "gabarito" | "resultado" | "homologacao" | "etapa";
  texto: string;
  inicio?: string | null;
  fim?: string | null;
  fontes: string[];
}

export interface Noticia {
  slug: string;
  titulo: string;
  orgao: string;
  categoria: Categoria;
  esfera: Esfera;
  uf: string;
  municipio?: string | null;
  banca: string;
  resumo: string;
  cargos: string[];
  areas?: "ti"[];
  fatos: FatoNoticia[];
  fontes: FonteNoticia[];
  apurado_em: string;
  expira_em: string;
}

export const NOME_FATO: Record<FatoNoticia["campo"], string> = {
  inscricao: "Inscrições",
  isencao: "Isenção da taxa",
  vagas: "Vagas",
  taxa: "Taxa",
  prova: "Provas",
  remuneracao: "Remuneração",
  banca: "Banca",
  cargos: "Cargos",
};

let cacheNoticias: Noticia[] | null = null;

export function todasNoticias(): Noticia[] {
  if (cacheNoticias) return cacheNoticias;
  const dir = path.join(DIR_DADOS, "noticias");
  cacheNoticias = fs.existsSync(dir)
    ? fs.readdirSync(dir).filter((f) => f.endsWith(".json")).sort()
        .map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf-8")) as Noticia)
    : [];
  return cacheNoticias;
}

/** Concurso conferido que substitui a notícia (pela lista de editais avulsos), se houver. */
export function substitutoDe(n: Noticia): Concurso | undefined {
  const slug = substituicoes().get(n.slug);
  return slug ? todos().find((c) => c.slug === slug) : undefined;
}

/** Notícias com inscrição ainda não encerrada, de órgãos que não têm concurso verificado aberto
 * (pelo nome do órgão ou pela lista de editais avulsos, que liga a notícia ao concurso conferido). */
export function noticiasAtivas(hoje = hojeBRT()): Noticia[] {
  const abertos = todos().filter((c) => !encerrado(c, hoje));
  const verificados = new Set(abertos.map((c) => c.orgao));
  const slugsAbertos = new Set(abertos.map((c) => c.slug));
  const subst = substituicoes();
  return todasNoticias()
    .filter((n) => n.expira_em >= hoje && !verificados.has(n.orgao) && !slugsAbertos.has(subst.get(n.slug) ?? ""))
    .sort((a, b) => a.expira_em.localeCompare(b.expira_em));
}

export function fatoInscricao(n: Noticia): FatoNoticia | undefined {
  return n.fatos.find((f) => f.campo === "inscricao");
}

export const temTI = (x: { areas?: string[] }) => (x.areas ?? []).includes("ti");

/** Concursos verificados abertos e notícias ativas com cargo de TI. */
export function abertosTI(hoje = hojeBRT()): { concursos: Concurso[]; noticias: Noticia[] } {
  return {
    concursos: todos().filter((c) => temTI(c) && !encerrado(c, hoje)),
    noticias: noticiasAtivas(hoje).filter(temTI),
  };
}
