import type { APIRoute } from "astro";
import { SITE } from "../config";
import { todasNoticias, todos } from "../lib/dados";
import { hojeBRT } from "../lib/tempo";

const FIXAS = ["/", "/isencao-aberta/", "/como-pedir-isencao/", "/noticias/", "/ti/", "/metodologia/", "/sobre/", "/contato/", "/privacidade/", "/termos/"];

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");

export const GET: APIRoute = () => {
  const urls = [
    ...FIXAS.map((p) => ({ loc: new URL(p, SITE.url).href, lastmod: null as string | null })),
    ...todos().map((c) => ({
      loc: new URL(`/concursos/${c.slug}/`, SITE.url).href,
      lastmod: c.conferido_em.slice(0, 10), // data real da última conferência
    })),
    ...todasNoticias().filter((n) => n.expira_em >= hojeBRT()).map((n) => ({
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
