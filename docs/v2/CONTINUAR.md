# NT Concursos 2.0 — continuidade

## Estado inicial (17/11/2026)
- Branch exclusiva: `develop/v2`, criada a partir de `main` no commit `e9de72d0b1c10dc11f2a3f9b2bb859488051390c`.
- Produção: **não alterar**. Aguardar aprovação do AdSense e autorização expressa posterior para qualquer deploy da V2.
- Arquitetura observada: `site/` Astro; `collector/` Python; `worker/` TypeScript; `data/`, `schema/` e GitHub Actions.
- Workflows `publish.yml` (deploy Pages com `--branch=main`), `deploy-worker.yml` (push somente main) e coleta automatizada na main.
- Confirmação do proprietário em 17/11/2026: Cloudflare faz deploy **somente da main**. A configuração externa não foi inspecionada diretamente; manter essa premissa registrada e não mudar integrações de publicação.

## Próximos passos
1. Auditar proteção da main, automações, segredos e isolamento de dados; não ler ou divulgar valores secretos. Deploy exclusivo da main informado pelo proprietário.
2. Executar baseline local: testes Python, schema, validate, build Astro; registrar comandos e resultados reais.
3. Auditar fontes, modelos, extratores, evidências, retificações e lógica de prazos.
4. Implementar incrementalmente motor de coleta V2, UI, busca, SEO, acessibilidade e testes.
5. Manter relatórios de alterações, riscos e comandos de retomada.

## Proibições
- Nenhum merge, push ou commit na main.
- Nenhuma modificação de banco, Cloudflare, DNS, AdSense ou credenciais de produção.
- Nenhuma alegação de teste executado sem evidência.
