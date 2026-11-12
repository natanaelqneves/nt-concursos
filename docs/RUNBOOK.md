# Runbook

## Configuração inicial (uma vez)

1. **Dados institucionais.** Edite `site/src/config.ts` e troque os três `"PREENCHER"`
   (responsável, e-mail de contato, cidade/UF). A publicação fica bloqueada até isso ser feito.
   Use um e-mail próprio do site (ex.: `contato@ntconcursos.com.br`, com roteamento de e-mail grátis da Cloudflare).
2. **Cloudflare.**
   - O domínio `ntconcursos.com.br` precisa estar na conta com status *Active*.
   - My Profile → API Tokens → Create Token → *Custom token* com as permissões
     **Account → Cloudflare Pages → Edit** e **Account → Workers Scripts → Edit**, restrito à sua conta.
   - Anote o **Account ID** (página inicial da conta ou Workers & Pages → barra lateral).
   - Não crie o projeto do Pages manualmente: o `publish.yml` cria o projeto `ntconcursos` na primeira execução.
     **Não conecte o repositório pela integração Git da Cloudflare**: ela publicaria sem passar pelo gate.
3. **GitHub** (Settings → Secrets and variables → Actions):
   - Secrets: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `DISPATCH_TOKEN`
     (token fine-grained do GitHub com acesso só a `nt-concursos` e *Actions: Read and write*).
   - Variables (quando o AdSense aprovar): `ADSENSE_PUB_ID` (`pub-…`), `PUBLIC_ADSENSE_CLIENT`
     (`ca-pub-…`), `PUBLIC_ADSENSE_SLOT_TOPO`, `PUBLIC_ADSENSE_SLOT_MEIO`.
4. **Primeiro deploy e domínio.**
   - Actions → *Publicar edição* → *Run workflow*. Isso cria o projeto e publica.
   - Workers & Pages → `ntconcursos` → *Custom domains* → `ntconcursos.com.br` e `www.ntconcursos.com.br`.
   - Actions → *Publicar Worker de disparo* → *Run workflow*.
5. **INLABS** (M1): crie o cadastro gratuito em inlabs.in.gov.br; e-mail e senha vão como secrets
   `INLABS_EMAIL` e `INLABS_SENHA`.

## Operação diária

| Horário (BRT) | O que acontece | Sua ação |
|---|---|---|
| 04h00 | Worker dispara `publish.yml` | nenhuma |
| 04h30 | cron reserva (só publica se 04h00 falhou) | nenhuma |
| a partir de M1 | coletas mandam casos duvidosos para o painel admin (M3) | aprovar ou corrigir |

O GitHub manda e-mail quando um workflow falha. Se chegar:

- **`ntc validate` falhou:** um campo `verificado` não passa no gate. O log diz o arquivo, a regra e o
  campo. Corrija o dado ou rebaixe o campo para `revisao` e rode *Publicar edição* manualmente.
- **Preflight falhou:** falta configuração (passo 1 ou 3).
- **Deploy falhou:** confira o token da Cloudflare. O site continua no ar com a edição anterior.

## Plano B: banca bloqueando o GitHub Actions

Rode a coleta daquela fonte no seu PC (`ntc collect --fonte X`, a partir do M1) e faça push.
Não use proxies rotativos, VPN para mascarar IP nem serviços de resolver CAPTCHA. Se a banca
bloquear também o acesso normal, a fonte passa para revisão manual.
