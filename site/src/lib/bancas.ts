// Site oficial da banca, usado no botão "Ir ao site da banca" quando não há edital oficial
// para mostrar. Os domínios são os de data/fontes.yaml (fonte papel: banca). Bancas fora
// desta lista não ganham botão, para não apontar para um site que não conferimos.
const DOMINIO_BANCA: Record<string, string> = {
  fgv: "conhecimento.fgv.br",
  cebraspe: "cebraspe.org.br",
  aocp: "institutoaocp.org.br",
  fcc: "concursosfcc.com.br",
  vunesp: "vunesp.com.br",
  idecan: "idecan.org.br",
  comperve: "comperve.ufrn.br",
  access: "access.org.br",
  selecon: "selecon.org.br",
  ibade: "ibade.org.br",
};

// Nome livre (como aparece na notícia ou no concurso) -> chave de DOMINIO_BANCA.
const APELIDOS: [RegExp, string][] = [
  [/fgv/i, "fgv"],
  [/cebraspe/i, "cebraspe"],
  [/aocp/i, "aocp"],
  [/carlos chagas|\bfcc\b/i, "fcc"],
  [/vunesp/i, "vunesp"],
  [/idecan/i, "idecan"],
  [/comperve/i, "comperve"],
  [/instituto access/i, "access"],
  [/selecon/i, "selecon"],
  [/ibade/i, "ibade"],
];

/** URL do site oficial da banca, ou undefined se a banca não estiver mapeada. */
export function siteBanca(banca: string): string | undefined {
  const hit = APELIDOS.find(([re]) => re.test(banca));
  return hit ? `https://${DOMINIO_BANCA[hit[1]]}/` : undefined;
}
