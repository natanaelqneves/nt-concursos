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
