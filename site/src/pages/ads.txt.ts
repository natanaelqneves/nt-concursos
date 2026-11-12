import type { APIRoute } from "astro";

// ADSENSE_PUB_ID = "pub-XXXXXXXXXXXXXXXX" (variável do GitHub Actions). Sem ela, o arquivo
// sai só com um comentário; o preflight impede publicar em produção nesse estado.
export const GET: APIRoute = () => {
  const pub = process.env.ADSENSE_PUB_ID?.trim();
  const linha = pub
    ? `google.com, ${pub}, DIRECT, f08c47fec0942fa0\n`
    : "# ads.txt: ADSENSE_PUB_ID não configurado\n";
  return new Response(linha, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
};
