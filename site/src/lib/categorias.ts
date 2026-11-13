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
  estatal: {
    titulo: "O que são as empresas públicas",
    paragrafos: [
      "Empresas públicas e sociedades de economia mista são empresas controladas pela União ou por um estado, como bancos públicos, empresas de tecnologia do governo, companhias de saneamento e de energia. Elas contratam por concurso, mas os empregados são regidos pela CLT, e não pelo regime estatutário dos servidores.",
      "Por isso, a estabilidade é diferente da de um servidor público, e benefícios como plano de saúde e previdência complementar variam de empresa para empresa. O edital informa salário, jornada e benefícios de cada emprego.",
    ],
  },
  conselho: {
    titulo: "O que são os conselhos profissionais",
    paragrafos: [
      "Os conselhos profissionais, como os de medicina, engenharia, contabilidade e enfermagem, fiscalizam o exercício das profissões regulamentadas. Têm um conselho federal e conselhos regionais, em geral com sede num estado ou numa região que reúne alguns estados.",
      "Para contratar, os conselhos precisam fazer concurso público. Os cargos mais comuns são de fiscal, agente administrativo, analista e advogado, e os empregados costumam ser contratados pela CLT.",
    ],
  },
  fiscal: {
    titulo: "O que fazem os órgãos fazendários",
    paragrafos: [
      "A Receita Federal, na União, e as secretarias de Fazenda (ou receitas estaduais), nos estados, cobram e fiscalizam os tributos: na esfera federal, impostos como o de renda e o IPI; nos estados, principalmente o ICMS e o IPVA. Também cuidam da arrecadação, do controle aduaneiro e, nos estados, de parte da gestão financeira.",
      "Os cargos mais disputados são de auditor fiscal, de nível superior, com provas longas que cobram direito tributário, contabilidade, auditoria, direito constitucional e administrativo e, em muitos editais, tecnologia da informação e legislação tributária do próprio estado. Há também cargos de analista e técnico fazendário.",
    ],
  },
  advocacia: {
    titulo: "O que faz a advocacia pública",
    paragrafos: [
      "A advocacia pública defende a União, os estados e o Distrito Federal na Justiça e dá consultoria jurídica à administração. Na União, a Advocacia-Geral da União (AGU) reúne carreiras como advogado da União e procurador federal, e a Procuradoria-Geral da Fazenda Nacional (PGFN) cuida da cobrança da dívida ativa federal. Nos estados, esse papel é das procuradorias-gerais (PGEs).",
      "O cargo de procurador exige bacharelado em Direito e, em geral, inscrição na OAB; o concurso costuma ter provas objetivas, discursivas e orais, além de títulos. As procuradorias também fazem concursos para cargos de apoio, como analista e técnico.",
    ],
  },
  executivo: {
    titulo: "O que é o executivo e a gestão pública",
    paragrafos: [
      "No governo federal, o Executivo reúne os ministérios, autarquias e fundações como o INSS e o IBGE, o Banco Central e as agências reguladoras, que fiscalizam setores como energia, telecomunicações, transportes e saúde suplementar. Desde 2024, parte desses órgãos seleciona servidores pelo Concurso Público Nacional Unificado (CNU).",
      "Nos estados, acompanhamos os concursos da área de gestão: secretarias de administração, planejamento e gestão, concursos unificados que reúnem vários órgãos do governo estadual e carreiras de gestor governamental, como especialista em políticas públicas e gestão governamental. Os cargos vão de técnico, de nível médio, a analista e especialista, de nível superior, e cada edital traz as áreas de formação aceitas e o conteúdo das provas.",
    ],
  },
  legislativo: {
    titulo: "O que faz o Poder Legislativo",
    paragrafos: [
      "O Legislativo faz as leis e fiscaliza o Executivo. Na União, é formado pela Câmara dos Deputados e pelo Senado Federal; nos estados, pelas assembleias legislativas; no Distrito Federal, pela Câmara Legislativa.",
      "Os concursos são para analistas e técnicos legislativos, consultores legislativos e de orçamento e, em algumas casas, policiais legislativos (que aparecem aqui em segurança pública). Os salários costumam estar entre os mais altos do serviço público, e as provas cobram o regimento interno da casa, além das matérias da especialidade.",
    ],
  },
  educacao: {
    titulo: "Concursos da educação pública",
    paragrafos: [
      "Na esfera federal, acompanhamos as universidades e os institutos federais de educação, ciência e tecnologia. Eles fazem concursos para professores (magistério superior e ensino básico, técnico e tecnológico) e para técnicos-administrativos em educação, cargos de nível médio e superior que trabalham na gestão, nos laboratórios, nas bibliotecas e no atendimento.",
      "Nos estados, acompanhamos as secretarias de educação, que contratam professores da rede estadual e profissionais de apoio. Seleções temporárias, como as de professor substituto ou contratado, ficam de fora: aqui entram só concursos para cargos efetivos.",
    ],
  },
  saude: {
    titulo: "Concursos da saúde pública estadual",
    paragrafos: [
      "As secretarias estaduais de saúde e as fundações estaduais de saúde administram hospitais, hemocentros, laboratórios e a gestão do SUS em cada estado. Os concursos costumam ter muitos cargos ao mesmo tempo: médicos de várias especialidades, enfermeiros, técnicos de enfermagem, farmacêuticos, fisioterapeutas, psicólogos, assistentes sociais e cargos administrativos.",
      "Muitos cargos exigem registro no conselho profissional e, às vezes, residência ou especialização, e o concurso pode ter prova de títulos. Seleções temporárias e processos seletivos simplificados ficam de fora.",
    ],
  },
  militar: {
    titulo: "Concursos das Forças Armadas",
    paragrafos: [
      "Exército, Marinha e Aeronáutica selecionam pessoal por concursos de admissão às suas escolas de formação, como a Escola de Sargentos das Armas, a Escola Preparatória de Cadetes do Exército, a Escola Naval, o Colégio Naval, a Escola de Especialistas de Aeronáutica e a Academia da Força Aérea, e por concursos para quadros técnicos, de saúde e de engenharia.",
      "Os requisitos de idade, altura, estado civil e escolaridade variam muito de uma seleção para outra, e quase todas têm exames de saúde, teste físico e avaliação psicológica além das provas. O serviço militar temporário e voluntário fica de fora: aqui entram só as seleções de carreira.",
    ],
  },
  outro: {
    titulo: "Por que este concurso aparece aqui",
    paragrafos: [
      "Além das categorias que acompanhamos sempre, acompanhamos concursos de outros órgãos federais e estaduais quando eles têm vagas na área de tecnologia da informação.",
      "Cargos de TI aparecem com nomes diferentes de um órgão para outro: analista de tecnologia da informação, analista de sistemas, especialista em infraestrutura, técnico de informática. O edital traz os requisitos de formação e o conteúdo da prova de cada um.",
    ],
  },
};
