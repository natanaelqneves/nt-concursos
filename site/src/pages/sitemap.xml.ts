import type { APIRoute } from "astro";
import { SITE } from "../config";
import { substitutoDe, todasNoticias, todos } from "../lib/dados";
import { validadesNaPagina } from "../lib/validade";
import { hojeBRT } from "../lib/tempo";
import { AREAS, ESTADOS, porCategoria, porUf, total, urlArea, urlEstado } from "../lib/navegacao";
import { RECORRENTES } from "../lib/recorrentes";

const FIXAS = ["/", "/isencao-aberta/", "/podem-reabrir/", "/como-pedir-isencao/", "/noticias/", "/ti/", "/metodologia/", "/sobre/", "/contato/", "/privacidade/", "/termos/"];

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");

export const GET: APIRoute = () => {
  const urls = [
    ...FIXAS.map((p) => ({ loc: new URL(p, SITE.url).href, lastmod: null as string | null })),
    ...["/estados/", "/areas/", "/recorrentes/"].map((p) => ({ loc: new URL(p, SITE.url).href, lastmod: null as string | null })),
    // páginas de estado vazias ficam com noindex e fora do sitemap
    ...["BR", ...Object.keys(ESTADOS)].filter((uf) => total(porUf(uf)) > 0)
      .map((uf) => ({ loc: new URL(urlEstado(uf), SITE.url).href, lastmod: null as string | null })),
    // áreas sem concurso, recorrente nem validade ficam com noindex e fora do sitemap
    ...AREAS.filter((c) => total(porCategoria(c)) > 0 || RECORRENTES.some((r) => r.categoria === c)
      || validadesNaPagina().some((v) => v.categoria === c)).map((c) => ({ loc: new URL(urlArea(c), SITE.url).href, lastmod: null as string | null })),
    ...RECORRENTES.map((r) => ({ loc: new URL(`/recorrentes/${r.slug}/`, SITE.url).href, lastmod: r.conferido_em })),
    ...todos().map((c) => ({
      loc: new URL(`/concursos/${c.slug}/`, SITE.url).href,
      lastmod: c.conferido_em.slice(0, 10), // data real da última conferência
    })),
    ...validadesNaPagina().map((v) => ({ loc: new URL(`/podem-reabrir/${v.slug}/`, SITE.url).href, lastmod: v.apurado_em.slice(0, 10) })),
    // notícia já conferida no edital aponta (canonical) para o concurso e sai do sitemap
    ...todasNoticias().filter((n) => n.expira_em >= hojeBRT() && !substitutoDe(n)).map((n) => ({
      loc: new URL(`/noticias/${n.slug}/`, SITE.url).href,
      lastmod: n.apurado_em.slice(0, 10),
    })),
  ];
  const corpo = urls
    .map((u) => `  <url><loc>${esc(u.loc)}</loc>${u.lastmod ? `<lastmod>${u.lastmod}</lastmod>` : ""}</url>`)
    .join("\n");
  const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${corpo}\n</urlset>\n`;
  return new Response(xml, { headers: { "Content-Type": "application/xml; charset=utf-8" } });
};
