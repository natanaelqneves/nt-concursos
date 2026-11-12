// Dados institucionais exibidos em Sobre, Contato, Privacidade e Termos.
// `npm run preflight` bloqueia a publicação enquanto houver "PREENCHER".
export const SITE = {
  nome: "NT Concursos",
  url: "https://ntconcursos.com.br",
  descricao:
    "Concursos públicos com inscrições abertas e prazos de isenção da taxa, conferidos no edital oficial.",
  responsavel: "Natanael Q. Neves",
  emailContato: "contato@ntconcursos.com.br",
  cidadeUf: "João Pessoa/PB",
};

// ID de editor do AdSense (público: aparece no ads.txt de qualquer site).
// Variáveis do GitHub Actions com o mesmo nome têm prioridade, se existirem.
export const ADSENSE_PUB_ID = (process.env.ADSENSE_PUB_ID || "pub-5630145382573940").trim();
export const ADSENSE_CLIENT = import.meta.env.PUBLIC_ADSENSE_CLIENT || `ca-${ADSENSE_PUB_ID}`;
