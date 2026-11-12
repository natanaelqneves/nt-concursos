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

// Preenchidos via variáveis de ambiente no build (GitHub Actions → vars).
export const ADSENSE_CLIENT = import.meta.env.PUBLIC_ADSENSE_CLIENT ?? ""; // ca-pub-XXXXXXXXXXXXXXXX
