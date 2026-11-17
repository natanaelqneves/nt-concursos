# NT Concursos 2.0 — requisitos e aceite

## Objetivo
Portal nacional de concursos públicos com foco em confiabilidade, cobertura, clareza de inscrições e isenções, experiência móvel, acessibilidade e SEO. Preservar as regras válidas do sistema atual e refatorar somente após auditoria.

## Motor de dados (prioridade P0)
- Descoberta de fontes oficiais federais, estaduais e municipais com cobertura mensurável.
- Extração de editais, cargos, vagas, requisitos, salários, inscrições, isenções, datas, documentos e retificações.
- Evidência por campo crítico: URL, documento, trecho/página quando disponível, horário da verificação e hash/versão.
- Estados explícitos de validação; impedir publicação de campos críticos conflitantes ou sem sustentação.
- Deduplicação, idempotência, histórico, atualização e reconciliação de retificações.
- Painel de saúde de fontes, execuções e revisão humana.

## Portal (P1)
- Design original e responsivo, busca e filtros por UF, município, cargo, escolaridade, remuneração, banca, isenção e situação.
- Páginas de concursos com fontes e histórico, favoritos locais, calendário e alertas opt-in.
- SEO técnico, URLs semânticas, metadados, sitemap, indexabilidade e dados estruturados adequados.
- WCAG 2.2 AA como objetivo e Core Web Vitals medidos, não presumidos.

## Critérios de aceite
- Coleta, validação, persistência e atualização testadas com fixtures reais e casos de retificação/duplicidade.
- Nenhum concurso vencido marcado como inscrição aberta devido a data estática.
- Build, testes unitários, integração e E2E documentados com resultados verificáveis.
- Ambiente de homologação isolado e não indexável.
- Produção preservada até aprovação do AdSense, validação final e autorização expressa do proprietário.

## Diretriz arquitetural
Manter Astro e Python como baseline, sujeito à auditoria. Evitar reescrita e serviços pagos desnecessários. Preferir execução local e baixo custo operacional.

## Decisão arquitetural — PostgreSQL/Supabase (17/11/2026)
- Supabase PostgreSQL é a opção preferencial para persistência da V2, condicionada à auditoria de custos, limites e integração.
- Desenvolver e testar inicialmente em PostgreSQL local isolado; nunca conectar testes ao ambiente de produção.
- Preservar os JSONs versionados e regras de evidência existentes até migração validada, reversível e com comparação de resultados.
- Projetar tabelas de concursos, cargos, localidades, fontes, documentos, evidências, retificações, execuções e histórico; aplicar constraints, índices, idempotência e transações.
- Separar permissões: coletor escreve via credencial de serviço restrita; portal público lê apenas registros publicados e verificados; RLS para dados acessíveis por APIs do Supabase.
- Supabase Auth/Storage são possibilidades futuras, não dependências obrigatórias nem autorização para ativar serviços pagos.
- Não provisionar projeto Supabase, usar credenciais reais ou migrar dados sem confirmação do ambiente isolado.

## Decisão de infraestrutura — Supabase Pro compartilhado (17/11/2026)
- O proprietário determinou reutilizar o projeto Supabase Pro já utilizado pelo Pintar Arte, também destinado ao NT MOBILIDADE (SEMOB).
- Schema exclusivo do NT Concursos: `nt_concursos`. Schema previsto para NT MOBILIDADE: `nt_mobilidade`; o schema atual do Pintar Arte deve ser identificado e preservado sem suposições.
- Antes de qualquer DDL: obter conexão autorizada, inspecionar apenas metadados dos schemas, confirmar o projeto correto e fazer plano de migração reversível. Não criar outro projeto Supabase.
- Manter todos os objetos de NT Concursos qualificados com `nt_concursos.` e evitar alterações em `public`, `auth`, `storage` ou schemas de terceiros.
- Definir papéis de menor privilégio, RLS quando tabelas forem expostas por APIs, limites de conexão e segregação de credenciais por aplicação. Não expor service_role no frontend.
- Considerar que schemas compartilham recursos, quotas, backups e disponibilidade. Não executar migrações destrutivas ou testes de carga no banco compartilhado.
- Banco local isolado continua preferencial para testes automatizados e desenvolvimento.
