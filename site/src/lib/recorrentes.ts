// Concursos que se repetem de tempos em tempos (começando pelos bancos públicos). Conteúdo
// editorial, apurado em reportagens e no histórico dos editais, com as fontes listadas em cada
// página. Não entra nas listas verificadas: quando houver edital aberto, a página aponta para o
// concurso conferido (ou para a apuração na imprensa) pelo nome do órgão.
import type { Categoria, Concurso, Noticia } from "./dados";
import { encerrado, noticiasAtivas, todos } from "./dados";
import { hojeBRT } from "./tempo";

export interface Recorrente {
  slug: string;
  nome: string;
  categoria: Categoria;
  esfera: "federal" | "estadual";
  uf: string; // BR para os nacionais
  /** Expressão (sem acento, minúsculas) que reconhece o órgão no nome ou no slug de um concurso. */
  reconhece: string;
  sobre: string[];
  cargos: { nome: string; escolaridade: string; nota?: string }[];
  historico: { ano: string; texto: string }[];
  situacao: string;
  fontes: { nome: string; url: string }[];
  conferido_em: string; // AAAA-MM-DD
}

export const RECORRENTES: Recorrente[] = [
  {
    slug: "banco-do-brasil",
    nome: "Banco do Brasil",
    categoria: "estatal",
    esfera: "federal",
    uf: "BR",
    reconhece: "banco do brasil|^bb-",
    sobre: [
      "O Banco do Brasil é uma sociedade de economia mista controlada pela União e uma das maiores instituições financeiras do país, com agências em todos os estados. Os empregados são contratados pela CLT, por concurso público.",
      "A porta de entrada é o cargo de escriturário, de nível médio, com lotação definida por região (as vagas são distribuídas por macrorregiões e polos). Nos editais recentes o cargo teve dois perfis: agente comercial, para o atendimento nas agências, e agente de tecnologia, para as áreas de sistemas.",
    ],
    cargos: [{ nome: "Escriturário (agente comercial e agente de tecnologia)", escolaridade: "nível médio" }],
    historico: [
      { ano: "2021", texto: "Edital para escriturário organizado pela Fundação Cesgranrio, com 4.480 vagas." },
      { ano: "2022", texto: "Novo edital da Fundação Cesgranrio para escriturário, com 6.000 vagas (4.000 imediatas e 2.000 em cadastro de reserva), para os perfis agente comercial e agente de tecnologia. A validade terminou em julho de 2025." },
    ],
    situacao: "Sem edital aberto. A imprensa especializada informa que um novo concurso para escriturário está em estudo e que a contratação da banca estava em análise no início de 2026.",
    fontes: [
      { nome: "Estratégia Concursos – panorama do concurso BB", url: "https://www.estrategiaconcursos.com.br/blog/?p=31422" },
      { nome: "Direção Concursos – última prova de escriturário", url: "https://www.direcaoconcursos.com.br/noticias/concurso-banco-do-brasil-prova-escriturario/" },
      { nome: "Diário do Pará – fim da validade do último edital", url: "https://diariodopara.com.br/concursos-e-empregos/alerta-para-concurseiros-fim-do-edital-do-bb-acelera-publicacao-de-novo-concurso/" },
    ],
    conferido_em: "2026-11-13",
  },
  {
    slug: "caixa",
    nome: "Caixa Econômica Federal",
    categoria: "estatal",
    esfera: "federal",
    uf: "BR",
    reconhece: "caixa economica|^caixa-|^cef-",
    sobre: [
      "A Caixa é uma empresa pública federal: além de banco comercial, opera programas sociais e de habitação do governo, como o FGTS, o Bolsa Família e o financiamento habitacional. Os empregados são contratados pela CLT.",
      "O cargo mais procurado é o de técnico bancário, de nível médio, que nos últimos editais teve duas áreas: a comercial, de atendimento nas agências, e a de tecnologia da informação. Concursos de nível superior, como engenharia, arquitetura e medicina do trabalho, acontecem em editais separados.",
    ],
    cargos: [
      { nome: "Técnico Bancário Novo", escolaridade: "nível médio" },
      { nome: "Técnico Bancário Novo – Tecnologia da Informação", escolaridade: "nível médio" },
      { nome: "Cargos de nível superior (engenharia, arquitetura, medicina do trabalho)", escolaridade: "nível superior", nota: "em editais próprios" },
    ],
    historico: [
      { ano: "2014", texto: "Concurso para técnico bancário organizado pelo Cespe (hoje Cebraspe), só com cadastro de reserva." },
      { ano: "2021", texto: "Edital da Fundação Cesgranrio para técnico bancário, com cerca de mil vagas." },
      { ano: "2024", texto: "Edital da Fundação Cesgranrio com 4.050 vagas: 4.000 para técnico bancário (comercial e TI) e 50 de nível superior. A validade foi prorrogada até agosto de 2026." },
      { ano: "2025", texto: "Edital de nível superior (arquiteto, engenheiro e médico do trabalho), também pela Cesgranrio, homologado em 2026." },
    ],
    situacao: "Sem edital aberto para técnico bancário. Segundo a imprensa, um novo concurso para o cargo está em estudo, e a Caixa mantém contrato com a Fundação Cesgranrio até 2028.",
    fontes: [
      { nome: "Folha Dirigida (Qconcursos) – o que estudar para o próximo edital", url: "https://folha.qconcursos.com/n/concurso-caixa-o-que-estudar" },
      { nome: "Direção Concursos – validade prorrogada", url: "https://www.direcaoconcursos.com.br/noticias/concurso-caixa-validade-prorrogada-nivel-medio" },
      { nome: "Gran Cursos – edital Caixa", url: "https://blog.grancursosonline.com.br/edital-caixa/" },
    ],
    conferido_em: "2026-11-13",
  },
  {
    slug: "banco-do-nordeste",
    nome: "Banco do Nordeste (BNB)",
    categoria: "estatal",
    esfera: "federal",
    uf: "BR",
    reconhece: "banco do nordeste|^bnb-",
    sobre: [
      "O Banco do Nordeste é um banco de desenvolvimento regional controlado pela União, com atuação nos nove estados do Nordeste e no norte de Minas Gerais e do Espírito Santo. É o principal operador do crédito do Fundo Constitucional do Nordeste (FNE).",
      "O cargo mais frequente nos editais é o de analista bancário 1, de nível médio. O banco também faz concursos para especialista técnico, de nível superior, principalmente na área de tecnologia da informação.",
    ],
    cargos: [
      { nome: "Analista Bancário 1", escolaridade: "nível médio" },
      { nome: "Especialista Técnico (analista de sistemas)", escolaridade: "nível superior" },
    ],
    historico: [
      { ano: "2018", texto: "Edital para analista bancário e especialista técnico (analista de sistemas), com 700 vagas, quase todas em cadastro de reserva." },
      { ano: "2022", texto: "Concurso voltado à área de tecnologia da informação." },
      { ano: "2024", texto: "Edital da Fundação Cesgranrio para analista bancário 1, com 710 vagas (410 imediatas e 300 em cadastro de reserva) e remuneração inicial de R$ 3.788,16." },
    ],
    situacao: "Sem edital aberto. O banco chamou todos os aprovados do último concurso e, segundo a imprensa, estuda uma nova seleção e já consultou bancas em 2026.",
    fontes: [
      { nome: "Folha Dirigida (Qconcursos) – BNB prospecta bancas", url: "https://folha.qconcursos.com/n/concurso-bnb-2026-estudos-e-prospeccao-bancas" },
      { nome: "Gran Cursos – cargos dos últimos editais do BNB", url: "https://blog.grancursosonline.com.br/?p=79879182" },
      { nome: "Focus Concursos – último concurso BNB", url: "https://noticias.focusconcursos.com.br/noticias/novo-edital-do-bnb-pode-sair-em-2027-com-previsao-de-400-vagas" },
    ],
    conferido_em: "2026-11-13",
  },
  {
    slug: "banco-da-amazonia",
    nome: "Banco da Amazônia (Basa)",
    categoria: "estatal",
    esfera: "federal",
    uf: "BR",
    reconhece: "banco da amazonia|^basa-",
    sobre: [
      "O Banco da Amazônia é um banco de desenvolvimento controlado pela União, com agências nos estados da Amazônia Legal. É o principal operador do Fundo Constitucional do Norte (FNO).",
      "Os editais costumam ter dois cargos: técnico bancário, de nível médio, e técnico científico, de nível superior, quase sempre na área de tecnologia da informação.",
    ],
    cargos: [
      { nome: "Técnico Bancário", escolaridade: "nível médio" },
      { nome: "Técnico Científico (tecnologia da informação)", escolaridade: "nível superior" },
    ],
    historico: [
      { ano: "2018", texto: "Concurso para técnico bancário e técnico científico, com 46 vagas imediatas e cadastro de reserva." },
      { ano: "2021–2022", texto: "Editais da Fundação Cesgranrio para técnico científico (TI) e para técnico bancário e técnico científico." },
      { ano: "2024", texto: "Edital da Fundação Cesgranrio com 50 vagas imediatas e 400 em cadastro de reserva (técnico bancário e técnico científico – TI). A validade foi prorrogada até janeiro de 2027." },
    ],
    situacao: "Sem edital aberto. O concurso de 2024 continua válido até janeiro de 2027, e ainda pode haver convocações.",
    fontes: [
      { nome: "Estratégia Concursos – concurso Basa", url: "https://www.estrategiaconcursos.com.br/blog/concurso-basa/" },
      { nome: "Estratégia Concursos – edital Basa 2024", url: "https://www.estrategiaconcursos.com.br/blog/concurso-basa-edital-2024/amp/" },
      { nome: "Gran Cursos – histórico do concurso Basa", url: "https://blog.grancursosonline.com.br/?p=79343172" },
    ],
    conferido_em: "2026-11-13",
  },
  {
    slug: "bndes",
    nome: "BNDES",
    categoria: "estatal",
    esfera: "federal",
    uf: "BR",
    reconhece: "bndes|banco nacional de desenvolvimento",
    sobre: [
      "O Banco Nacional de Desenvolvimento Econômico e Social é uma empresa pública federal que financia investimentos de longo prazo em infraestrutura, indústria e inovação. Fica no Rio de Janeiro, com escritórios em outras capitais.",
      "Os concursos são raros e muito disputados. Têm cargos de nível médio (técnico administrativo) e de nível superior, em várias formações: administração, análise de sistemas, contabilidade, direito, economia, engenharia e outras.",
    ],
    cargos: [
      { nome: "Técnico administrativo", escolaridade: "nível médio" },
      { nome: "Analista / profissional básico, por formação", escolaridade: "nível superior" },
    ],
    historico: [
      { ano: "2012", texto: "Concurso da Fundação Cesgranrio só com cadastro de reserva, para técnico e profissional básico, com cerca de 138 mil inscritos." },
      { ano: "2024", texto: "Novo edital da Fundação Cesgranrio, publicado em julho de 2024, com vagas de níveis médio e superior." },
    ],
    situacao: "Sem edital aberto. Entre os dois últimos concursos passaram 12 anos.",
    fontes: [
      { nome: "Folha Dirigida (Qconcursos) – edital BNDES 2024", url: "https://folha.qconcursos.com/n/concurso-bndes" },
      { nome: "Estratégia Concursos – último concurso do BNDES", url: "https://www.estrategiaconcursos.com.br/blog/como-foi-ultimo-concurso-bndes-detalhes/amp/" },
    ],
    conferido_em: "2026-11-13",
  },
  {
    slug: "banrisul",
    nome: "Banrisul",
    categoria: "estatal",
    esfera: "estadual",
    uf: "RS",
    reconhece: "banrisul|banco do estado do rio grande do sul",
    sobre: [
      "O Banco do Estado do Rio Grande do Sul é uma sociedade de economia mista controlada pelo governo gaúcho, com centenas de agências no estado e algumas em outras capitais.",
      "O cargo de entrada é o de escriturário, de nível médio. O banco também faz concursos para técnico em tecnologia da informação, de nível superior, em editais separados.",
    ],
    cargos: [
      { nome: "Escriturário", escolaridade: "nível médio" },
      { nome: "Técnico em Tecnologia da Informação", escolaridade: "nível superior" },
    ],
    historico: [
      { ano: "2018", texto: "Edital para escriturário organizado pela FCC, com 200 vagas." },
      { ano: "2022", texto: "Edital para técnico em TI organizado pelo Cebraspe, com 274 vagas, e edital para escriturário organizado pela Fundação Cesgranrio, com 824 vagas imediatas. A validade do concurso de escriturário foi prorrogada até março de 2027." },
      { ano: "2025", texto: "Novo edital do Cebraspe para técnico em TI, com 100 vagas." },
    ],
    situacao: "Sem edital aberto. O concurso de escriturário de 2022 segue válido até março de 2027.",
    fontes: [
      { nome: "Direção Concursos – Banrisul prorrogado até 2027", url: "https://www.direcaoconcursos.com.br/noticias/concurso-banrisul-prorrogado-ate-2027" },
      { nome: "Gran Cursos – concurso Banrisul", url: "https://blog.grancursosonline.com.br/concurso-banrisul/" },
      { nome: "JC Concursos – Banrisul 2022", url: "https://jcconcursos.com.br/concurso/concurso-banrisul-77842" },
    ],
    conferido_em: "2026-11-13",
  },
  {
    slug: "brb",
    nome: "BRB – Banco de Brasília",
    categoria: "estatal",
    esfera: "estadual",
    uf: "DF",
    reconhece: "banco de brasilia|^brb-",
    sobre: [
      "O Banco de Brasília é uma sociedade de economia mista controlada pelo Governo do Distrito Federal. Os empregados são contratados pela CLT, por concurso público.",
      "O cargo de entrada é o de escriturário, de nível médio. O banco também faz concursos para analista de tecnologia da informação e outros cargos de nível superior.",
    ],
    cargos: [
      { nome: "Escriturário", escolaridade: "nível médio" },
      { nome: "Analista de Tecnologia da Informação", escolaridade: "nível superior" },
    ],
    historico: [
      { ano: "2019", texto: "Editais do Iades para escriturário, analista de TI, advogado e outros cargos." },
      { ano: "2022", texto: "Edital do Iades para escriturário, com 500 vagas (300 imediatas e 200 em cadastro de reserva). A validade foi prorrogada e segue até 2027." },
      { ano: "2024", texto: "Edital do Iades para analista de tecnologia da informação." },
    ],
    situacao: "Sem edital aberto. O banco continua chamando aprovados do concurso de escriturário de 2022.",
    fontes: [
      { nome: "Direção Concursos – validade prorrogada", url: "https://www.direcaoconcursos.com.br/noticias/concurso-brb-escriturario-validade-prorrogada" },
      { nome: "Folha Dirigida (Qconcursos) – convocações do edital de 2022", url: "https://folha.qconcursos.com/n/concurso-brb-convocacao-escriturarios-2022" },
      { nome: "Estratégia Concursos – concurso BRB", url: "https://www.estrategiaconcursos.com.br/blog/concurso-brb/" },
    ],
    conferido_em: "2026-11-13",
  },
  {
    slug: "banpara",
    nome: "Banpará",
    categoria: "estatal",
    esfera: "estadual",
    uf: "PA",
    reconhece: "banpara|banco do estado do para",
    sobre: [
      "O Banco do Estado do Pará é uma sociedade de economia mista controlada pelo governo paraense, com agências em todo o estado.",
      "O cargo mais oferecido é o de técnico bancário, de nível médio, com vagas distribuídas por polos regionais. Os editais também trazem poucas vagas de nível superior, como engenharia, contabilidade e tecnologia da informação.",
    ],
    cargos: [
      { nome: "Técnico Bancário", escolaridade: "nível médio" },
      { nome: "Cargos de nível superior (engenharia, contabilidade, TI e outros)", escolaridade: "nível superior" },
    ],
    historico: [
      { ano: "2018", texto: "Edital da Fadesp com 126 vagas imediatas e cadastro de reserva, para cargos de níveis médio e superior." },
      { ano: "2024", texto: "Edital publicado em novembro de 2024, com 37 vagas imediatas e cadastro de reserva. O resultado foi homologado e o concurso vale até 2027." },
    ],
    situacao: "Sem edital aberto. O banco convocou mais aprovados do concurso de 2024 em 2026.",
    fontes: [
      { nome: "Folha Dirigida (Qconcursos) – convocações de 2026", url: "https://folha.qconcursos.com/n/concurso-banpara-2026-tera-novos-aprovados-em-marco" },
      { nome: "Estratégia Concursos – concurso Banpará", url: "https://www.estrategiaconcursos.com.br/blog/concurso-banpara/amp/" },
      { nome: "Direção Concursos – edital de 2018", url: "https://direcaoconcursos.com.br/noticias/concurso-banpara-comissao-acompanhamento" },
    ],
    conferido_em: "2026-11-13",
  },
];

const semAcento = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** Concurso conferido ou notícia ativa do mesmo órgão, para avisar que há edital aberto. */
export function abertoAgora(r: Recorrente, hoje = hojeBRT()): { concursos: Concurso[]; noticias: Noticia[] } {
  const re = new RegExp(r.reconhece);
  const casa = (x: { orgao: string; slug: string }) => re.test(semAcento(x.orgao)) || re.test(x.slug);
  return {
    concursos: todos().filter((c) => !encerrado(c, hoje) && casa(c)),
    noticias: noticiasAtivas(hoje).filter(casa),
  };
}
