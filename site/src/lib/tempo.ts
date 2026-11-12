const FUSO = "America/Sao_Paulo";

/** Data de hoje em Brasília, no formato AAAA-MM-DD (o mesmo dos JSON). */
export function hojeBRT(agora: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: FUSO }).format(agora);
}

export function agoraBRT(agora: Date = new Date()): string {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: FUSO,
    dateStyle: "short",
    timeStyle: "short",
  }).format(agora);
}

/** "2026-11-14" -> "14/11/2026" sem passar por Date (evita deslocamento de fuso). */
export function formatarData(iso: string): string {
  const [a, m, d] = iso.split("-");
  return `${d}/${m}/${a}`;
}

export function formatarDataHora(isoComFuso: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: FUSO,
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(isoComFuso));
}

/** Dias corridos de `de` até `ate` (ambos AAAA-MM-DD). */
export function diasEntre(de: string, ate: string): number {
  const utc = (s: string) => {
    const [a, m, d] = s.split("-").map(Number);
    return Date.UTC(a, m - 1, d);
  };
  return Math.round((utc(ate) - utc(de)) / 86_400_000);
}
