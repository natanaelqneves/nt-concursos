# Runbook

## Configuração inicial (uma vez)

1. **Dados institucionais.** Edite `site/src/config.ts` e troque os três `"PREENCHER"`
   (responsável, e-mail de contato, cidade/UF). A publicação fica bloqueada até isso ser feito.
   Use um e-mail próprio do site (ex.: `contato@ntconcursos.com.br`, com roteamento de e-mail grátis da Cloudflare).
2. **Cloudflare.**
   - Crie a conta e adicione o domínio `ntconcursos.com.br`; no registrador, troque os nameservers
     pelos que a Cloudflare indicar.
   - Workers & Pages → Create → Pages → *Direct Upload* → projeto `ntconcursos`.
   - No projeto, *Custom domains* → adicione `ntconcursos.com.br` e `www.ntconcursos.com.br`.
   - Crie um API Token com o modelo *Edit Cloudflare Workers* (inclui Pages) e anote o Account ID.
3. **GitHub** (Settings → Secrets and variables → Actions):
   - Secrets: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`.
   - Variables (quando o AdSense aprovar): `ADSENSE_PUB_ID` (`pub-…`), `PUBLIC_ADSENSE_CLIENT`
     (`ca-pub-…`), `PUBLIC_ADSENSE_SLOT_TOPO`, `PUBLIC_ADSENSE_SLOT_MEIO`.
4. **Worker de disparo.**
   - GitHub → Settings → Developer settings → Fine-grained tokens: acesso só a `nt-concursos`,
     permissão *Actions: Read and write*.
   - `cd worker && npm install && npx wrangler login && npx wrangler secret put GITHUB_TOKEN && npm run deploy`
5. **INLABS** (M1): crie o cadastro gratuito em inlabs.in.gov.br; e-mail e senha vão como secrets
   `INLABS_EMAIL` e `INLABS_SENHA`.
6. **Primeira publicação:** Actions → *Publicar edição* → *Run workflow*.

## Operação diária

| Horário (BRT) | O que acontece | Sua ação |
|---|---|---|
| 04h00 | Worker dispara `publish.yml` | nenhuma |
| 04h30 | cron reserva (só publica se 04h00 falhou) | nenhuma |
| a partir de M1 | coletas criam Issues `revisao` para casos duvidosos | aprovar ou corrigir |

O GitHub manda e-mail quando um workflow falha. Se chegar:

- **`ntc validate` falhou:** um campo `verificado` não passa no gate. O log diz o arquivo, a regra e o
  campo. Corrija o dado ou rebaixe o campo para `revisao` e rode *Publicar edição* manualmente.
- **Preflight falhou:** falta configuração (passo 1 ou 3).
- **Deploy falhou:** confira o token da Cloudflare. O site continua no ar com a edição anterior.

## Plano B: banca bloqueando o GitHub Actions

Rode a coleta daquela fonte no seu PC (`ntc collect --fonte X`, a partir do M1) e faça push.
Não use proxies rotativos, VPN para mascarar IP nem serviços de resolver CAPTCHA. Se a banca
bloquear também o acesso normal, a fonte passa para revisão manual.
