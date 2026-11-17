# Auditoria inicial — etapa 0 (parcial)

Data: 17/11/2026. Escopo: inspeção remota da estrutura e workflows, **sem execução de testes**.

## Confirmado
- Repositório: `natanaelqneves/nt-concursos`; branch padrão `main` (sem proteção na consulta).
- `site/`: projeto Astro (`astro.config.mjs`, `package.json`).
- `collector/`: Python (`pyproject.toml`, `src/`, `tests/`).
- `worker/`: TypeScript (`package.json`, `wrangler.toml`).
- `.github/workflows/ci.yml`: testes do coletor e build do site; push restrito à main e pull_request.
- `.github/workflows/publish.yml`: execução agendada/manual, validação e deploy Cloudflare Pages explicitamente com `--branch=main`.
- `.github/workflows/deploy-worker.yml`: push na main para mudanças em worker ou execução manual.
- `.github/workflows/collect-dou.yml`: coleta agendada com escrita de dados e commit na main.
- `.github/workflows/collect-bancas.yml`: coleta agendada de fontes.

## Não verificado
- Configurações externas de Cloudflare Pages, preview deployments e integração GitHub.
- Banco de dados, credenciais, variáveis e permissões externas.
- Cobertura, qualidade e precisão real do coletor.
- Testes locais, builds, métricas SEO/Lighthouse e segurança.

## Riscos e ações
1. **Alta:** main sem proteção. Configurar proteção somente com autorização e após avaliação das automações que escrevem nela.
2. **Alta:** eventual preview automático do Cloudflare em push de branch. Confirmar antes de push adicional de código.
3. **Alta:** coletor existente faz commits na main; garantir que desenvolvimento V2 não compartilhe recursos de escrita.
4. **Média:** publicação com datas relativas pode ficar desatualizada; auditar cálculos e timezone.

## Próxima evidência exigida
Resultados reais dos testes, inspeção dos modelos e regras de coleta, confirmação de isolamento Cloudflare e plano de implementação por componentes.
