// Bloqueia a publicação em produção enquanto faltar configuração obrigatória.
// Roda no publish.yml antes do build; falha com a lista do que falta.
import fs from "node:fs";

const problemas = [];

const config = fs.readFileSync(new URL("../src/config.ts", import.meta.url), "utf-8");
if (config.includes('"PREENCHER"')) {
  problemas.push("site/src/config.ts ainda tem campos \"PREENCHER\" (responsável, e-mail, cidade)");
}

const pub = process.env.ADSENSE_PUB_ID ?? "";
const client = process.env.PUBLIC_ADSENSE_CLIENT ?? "";
if (pub && !/^pub-\d{16}$/.test(pub)) problemas.push(`ADSENSE_PUB_ID inválido: ${pub}`);
if (client && !/^ca-pub-\d{16}$/.test(client)) problemas.push(`PUBLIC_ADSENSE_CLIENT inválido: ${client}`);
if (pub && client && client !== `ca-${pub}`) problemas.push("PUBLIC_ADSENSE_CLIENT e ADSENSE_PUB_ID são de contas diferentes");

if (problemas.length) {
  console.error("Preflight falhou:\n- " + problemas.join("\n- "));
  process.exit(1);
}
console.log("Preflight ok" + (pub ? "" : " (AdSense ainda não configurado: site sai sem anúncios)"));
