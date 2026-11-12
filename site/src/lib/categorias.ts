// Textos autorais por categoria de órgão. Genéricos de propósito: valem para qualquer concurso
// da categoria e não trazem dado que mude de um edital para outro (datas, vagas, salários).
import type { Categoria } from "./dados";

export const SOBRE_CATEGORIA: Record<Categoria, { titulo: string; paragrafos: string[] }> = {
  tribunal: {
    titulo: "O que fazem os tribunais",
    paragrafos: [
      "Os tribunais formam o Poder Judiciário. Os Tribunais de Justiça (TJs) cuidam da Justiça comum de cada estado; os Tribunais Regionais Federais (TRFs), da Justiça Federal; os Tribunais Regionais do Trabalho (TRTs) e os Tribunais Regionais Eleitorais (TREs), das justiças especializadas. Acima deles estão os tribunais superiores, como o STJ e o TST, e o Supremo Tribunal Federal.",
      "Há dois tipos bem diferentes de concurso. Para servidores (analistas e técnicos judiciários, oficiais de justiça), a seleção costuma ter provas objetivas e discursivas. Para a magistratura (juiz substituto), a Constituição exige bacharelado em Direito e três anos de atividade jurídica, e o concurso tem várias etapas, como prova oral, sindicância de vida pregressa e títulos.",
    ],
  },
  controle: {
    titulo: "O que fazem os órgãos de controle",
    paragrafos: [
      "Os tribunais de contas (TCU, na esfera federal, e TCEs ou TCMs, nos estados) fazem o controle externo: fiscalizam como o dinheiro público é usado e julgam as contas dos gestores, auxiliando o Poder Legislativo. As controladorias (CGU e as controladorias e auditorias-gerais dos estados) fazem o controle interno do Poder Executivo, com auditorias, correição e ações de transparência e combate à corrupção.",
      "Os cargos mais comuns são de auditor e analista de controle, geralmente de nível superior, com provas que cobram contabilidade, auditoria, direito administrativo e orçamento público.",
    ],
  },
  mp: {
    titulo: "O que faz o Ministério Público",
    paragrafos: [
      "Pela Constituição, o Ministério Público defende a ordem jurídica, o regime democrático e os interesses sociais e individuais indisponíveis. Na esfera federal, atua pelo Ministério Público da União (MPF, MPT, MPM e MPDFT); nos estados, pelos Ministérios Públicos estaduais.",
      "Há concursos para membros (promotores e procuradores), que exigem bacharelado em Direito e três anos de atividade jurídica, e para servidores (analistas e técnicos), com provas objetivas e, em geral, discursivas.",
    ],
  },
  defensoria: {
    titulo: "O que faz a Defensoria Pública",
    paragrafos: [
      "A Defensoria Pública presta orientação jurídica e defesa, de graça, a quem não pode pagar por um advogado. A Defensoria Pública da União atua perante a Justiça Federal e os tribunais superiores; as Defensorias estaduais, na Justiça dos estados.",
      "Os concursos são para defensor público, carreira jurídica com várias etapas, e para servidores de apoio, como analistas e técnicos.",
    ],
  },
  seguranca: {
    titulo: "O que fazem os órgãos de segurança pública",
    paragrafos: [
      "Na esfera federal estão a Polícia Federal, a Polícia Rodoviária Federal e a Polícia Penal Federal. Nos estados, a Polícia Civil investiga crimes, a Polícia Militar faz o policiamento ostensivo, a Polícia Penal atua no sistema prisional, a polícia científica faz as perícias e o Corpo de Bombeiros Militar cuida de incêndios, salvamentos e defesa civil. As polícias legislativas fazem a segurança da Câmara, do Senado e das assembleias.",
      "Além das provas escritas, esses concursos costumam ter teste de aptidão física, avaliação psicológica, exames médicos, investigação social e curso de formação. O edital de cada concurso define quais etapas existem e em que ordem.",
    ],
  },
};
