# ntconcursos — Arquitetura vencedora e plano do repositório

Versão 1.2 · 12/11/2026 (M1 e M1.1 entregues) · Mediação: Claude · Revisores: Codex, Gemini Pro

## 1. Consenso

Os três revisores escolheram, de forma independente, a família **C1/X1**: coletor Python + dados em JSON versionado no Git + site estático + GitHub Actions + Cloudflare Pages, sem servidor e sem banco em nuvem.

| Revisor | Finalista | Base |
|---|---|---|
| Claude | C1 (com elementos de G1) | menor carga operacional, R$ 0 |
| Codex | C1 | "mais proporcional ao orçamento e à capacidade de operação" |
| Gemini | X1 (com Astro no lugar do Eleventy) | DOU só como descoberta; Git como banco auditável |

**Arquitetura final:** X1/C1 com Astro, separação entre coleta e publicação (vinda de X2/G2), gate de evidência por cláusula (crítica do Codex) e fila de revisão via GitHub Issues.

## 2. Decisões de mediação (onde houve divergência)

| Tema | Posições | Decisão | Motivo |
|---|---|---|---|
| IA na extração | Codex: nenhuma. Gemini: LLM só como *fallback*, verificado por substring | **v1 sem LLM.** Se o regex falhar, o caso vai para revisão humana. O LLM sugestor fica como milestone opcional (M6), atrás do mesmo gate | O Codex mostrou que substring não prova semântica; a revisão humana resolve o caso raro sem custo variável |
| Allowlist | Gemini: 5 domínios fixos no código. Codex: validar também a URL final após redirecionamentos | **Arquivo `data/fontes.yaml` com regra por sufixo** (`gov.br`, `jus.br`, `mp.br`, `leg.br` + domínios das bancas), validando a URL **final** | Muitos editais saem em bancas menores e em domínios dos próprios órgãos |
| Plano B para bloqueio de IP | Gemini: runner self-hosted, WARP/Worker para mascarar IP, coleta local. Codex: só coleta em outra máquina; sem contornar bloqueio | **Runner self-hosted (PC do dono ou VM) com baixa frequência e respeito a robots.txt. Sem mascarar IP, sem proxies rotativos, sem CAPTCHA.** Se continuar bloqueado, a fonte passa para revisão manual | Mascarar IP para driblar um bloqueio é contornar controle de acesso da banca |
| Horário das 05h | Todos: o cron do Actions atrasa | **Coleta ao longo do dia; às 04h00 só build + deploy**, disparado por cron do Cloudflare Worker (`workflow_dispatch`), com cron do GitHub às 04h30 como reserva idempotente | O job das 04h leva poucos minutos; sobra cerca de 1 h de folga |
| DOU do dia | Codex e Gemini citam a Carta de Serviços (2022): INLABS disponibiliza os arquivos "somente a partir das 10h" | Coleta do DOU às **10h30**; a edição das 05h usa o DOU de D-1 | Fonte oficial; ainda vale testar empiricamente em M1 |
| Gerador do site | Eleventy (X1) ou Astro (C1, G1) | **Astro + Pagefind** | Proximidade com React; busca estática sem servidor |
| JSON-LD | `JobPosting` (Codex) ou `GovernmentService`/`FAQPage` (Gemini) | v1: `WebSite`, `BreadcrumbList`, `WebPage`. `JobPosting` avaliado em M5, só se a página cumprir as regras do Google | Marcação indevida traz risco de ação manual |
| PDFs | Supabase Storage / R2 | v1: **não versionar PDFs no Git**. Guardar URL, SHA-256 e o texto das páginas-âncora | O Git não serve para binários; o hash prova a identidade do documento |

## 3. Visão geral

```
            10h30 BRT                    18h00 e 02h30 BRT
        ┌───────────────┐            ┌──────────────────────┐
        │ collect-dou   │            │ collect-bancas       │
        │ (INLABS, D)   │            │ (FGV, Cebraspe, ...) │
        └──────┬────────┘            └──────────┬───────────┘
               │ descoberta + edital            │
               ▼                                ▼
        ┌──────────────────────────────────────────────┐
        │ fetch (allowlist + URL final) → pdfplumber   │
        │ → cláusulas → datas → GATE DE EVIDÊNCIA      │
        └──────┬───────────────────────────┬───────────┘
          aprovado                   dúvida/conflito
               ▼                           ▼
     data/concursos/*.json        data/revisao/*.json + GitHub Issue
               │  (commit do bot em main)
               ▼
   04h00 BRT  Worker cron → workflow_dispatch publish.yml
               │  astro build (filtra por data em America/Sao_Paulo)
               │  checks: schema, sitemap, ads.txt, links novos
               ▼
     Cloudflare Pages (ntconcursos.com.br)  ←  falhou? fica a edição de ontem + alerta
     04h30 BRT  cron reserva no GitHub (só publica se ainda não houver deploy hoje)
```

## 4. Estrutura do repositório

```
ntconcursos/
├── collector/                     # Python 3.12
│   ├── pyproject.toml
│   ├── src/ntc/
│   │   ├── cli.py                 # ntc collect --fonte X | ntc validate | ntc review
│   │   ├── config.py
│   │   ├── fetch/
│   │   │   ├── http.py            # requests, allowlist em cada salto, robots.txt, rate limit, cache ETag
│   │   │   └── allowlist.py
│   │   ├── sources/
│   │   │   ├── base.py            # interface Fonte: descobrir() / documentos()
│   │   │   ├── inlabs.py          # XML do DOU (descoberta)
│   │   │   ├── fgv.py
│   │   │   ├── cebraspe.py
│   │   │   ├── fcc.py
│   │   │   └── vunesp.py
│   │   ├── pdf/extract.py         # texto por página (pdfplumber), detecção de PDF escaneado
│   │   ├── parse/
│   │   │   ├── clausulas.py       # âncoras por tipo de prazo → janelas de texto
│   │   │   └── datas.py           # datas pt-BR (12/11/2026, 12 de novembro de 2026, intervalos)
│   │   ├── model/schema.py        # Pydantic: Concurso, Prazo, Evidencia, Documento
│   │   ├── gate/evidencia.py      # regras G1–G8 (seção 6)
│   │   ├── review/issues.py       # abre/fecha Issues da fila de revisão
│   │   └── store/json_store.py    # leitura/escrita determinística (ordenada, estável p/ diff)
│   └── tests/
│       ├── fixtures/              # textos reais de páginas de editais (não PDFs inteiros)
│       └── test_*.py
├── data/
│   ├── fontes.yaml                # allowlist e configuração por fonte
│   ├── concursos/<slug>.json
│   ├── documentos/<sha256>.json   # metadados + texto das páginas-âncora
│   ├── revisao/<id>.json
│   └── execucoes/<AAAA-MM-DD>.json
├── schema/concurso.schema.json    # gerado do Pydantic; o site valida contra ele
├── site/                          # Astro
│   ├── astro.config.mjs
│   ├── public/{ads.txt,robots.txt}
│   └── src/
│       ├── lib/dados.ts           # carrega data/, filtra abertos, ordena por fim da isenção
│       ├── components/{AdSlot,PrazoBadge,Evidencia,Consentimento,LinkAfiliado}.astro
│       ├── layouts/Base.astro
│       └── pages/
│           ├── index.astro                    # isenções abertas primeiro
│           ├── isencao-aberta.astro
│           ├── concursos/[slug].astro
│           ├── estado/[uf].astro
│           ├── banca/[banca].astro
│           ├── metodologia.astro              # como verificamos (sinal de qualidade)
│           ├── privacidade.astro, termos.astro, sobre.astro, contato.astro
│           └── sitemap.xml.ts
├── worker/                        # Cloudflare Worker: cron 07:00 UTC → workflow_dispatch
│   ├── wrangler.toml
│   └── src/index.ts
├── .github/workflows/
│   ├── ci.yml                     # testes + validação de schema em todo PR
│   ├── collect-dou.yml            # 13:30 UTC (10h30 BRT)
│   ├── collect-bancas.yml         # 21:00 e 05:30 UTC
│   └── publish.yml                # workflow_dispatch + cron reserva 07:30 UTC
└── docs/{ARQUITETURA.md,CONTRATO-DADOS.md,RUNBOOK.md}
```

## 5. Contrato de dados (`data/concursos/<slug>.json`)

```json
{
  "schema_version": 1,
  "slug": "tj-sp-2026-escrevente",
  "orgao": "Tribunal de Justiça de São Paulo",
  "banca": "vunesp",
  "uf": "SP",
  "cargos": [{"nome": "Escrevente Técnico Judiciário", "vagas": {"valor": 300, "evidencia": "ev-03"}}],
  "taxa": {"valor": 98.00, "evidencia": "ev-04"},
  "prazos": {
    "isencao":   {"inicio": "2026-11-10", "fim": "2026-11-14", "status": "verificado", "evidencia": "ev-01"},
    "inscricao": {"inicio": "2026-11-10", "fim": "2026-12-10", "status": "verificado", "evidencia": "ev-02"}
  },
  "isencao_publicos": ["CadÚnico", "doador de medula óssea"],
  "documentos": [
    {"id": "doc-1", "tipo": "edital", "url": "https://.../edital.pdf", "url_final": "https://.../edital.pdf",
     "sha256": "9f2c…", "coletado_em": "2026-11-11T18:04:12-03:00", "fonte": "vunesp"}
  ],
  "evidencias": [
    {"id": "ev-01", "campo": "prazos.isencao", "documento": "doc-1", "pagina": 7,
     "trecho": "a solicitação de isenção do pagamento da taxa de inscrição deverá ser feita de 10 a 14 de novembro de 2026",
     "ancora": "isenção", "metodo": "regex:v1", "aprovado_por": null}
  ],
  "descoberto_via": {"fonte": "inlabs", "url": "https://www.in.gov.br/...", "data_dou": "2026-11-10"},
  "conferido_em": "2026-11-11T18:04:12-03:00"
}
```

Regras do contrato:
- Todo campo factual é `{valor…, status, evidencia}`. `status ∈ {verificado, revisao, ausente}`.
- O site **só renderiza** campos `verificado`. Para `revisao` ou `ausente`, mostra "Consulte o edital" com o link oficial.
- Retificação = novo item em `documentos` do tipo `retificacao`. Os campos afetados apontam para a evidência mais recente, e o histórico fica no `git log`.
- `aprovado_por` é preenchido quando um humano aprova (PR que fecha a Issue de revisão).

## 6. Gate de evidência (nada vai ao ar sem passar)

| Regra | Verificação |
|---|---|
| G1 | O host da `url_final` (após redirecionamentos) casa com a allowlist em `fontes.yaml` |
| G2 | `sha256` calculado sobre os bytes baixados; o texto da página fica em `documentos/<sha256>.json` |
| G3 | `trecho` está contido no texto da `pagina` (normalizando apenas espaços e quebras de linha) |
| G4 | **Cláusula:** o `trecho` contém a âncora do tipo de prazo (ex.: `isen[çc][ãa]o`) **e** a(s) data(s), a no máximo N caracteres uma da outra |
| G5 | **Unicidade:** se o mesmo documento tiver mais de uma cláusula candidata com datas diferentes para o mesmo campo, vai para revisão |
| G6 | Plausibilidade: início ≤ fim; isenção dentro do ano corrente ou seguinte. Isenção terminando depois da inscrição vai para revisão (não é descartada) |
| G7 | Retificação posterior que cite a âncora do campo sem parse confiável: o campo volta para `revisao` |
| G8 | PDF sem camada de texto (escaneado): o documento inteiro vai para revisão |

## 7. Pipeline e falhas

| Horário (BRT) | Job | Em caso de falha |
|---|---|---|
| 10h30 | `collect-dou`: XML do dia → candidatos → busca o edital | Registra em `execucoes/` e avisa; nada publicado muda |
| 18h00 e 02h30 | `collect-bancas`: uma fonte por vez, isoladas | Fonte com erro mantém os dados anteriores; as demais seguem |
| 04h00 | `publish` (Worker → dispatch): build + checks + deploy | O Pages mantém o deploy anterior; alerta por e-mail |
| 04h30 | `publish` reserva (cron do GitHub) | Sai sem fazer nada se já houve deploy hoje |

O site mostra "Edição de DD/MM, publicada às HH:MM" e, em cada concurso, "conferido em …". Um deploy por dia dá ~30 por mês, muito abaixo do limite de 500 do Pages.

## 8. SEO e AdSense (checklist)

- [ ] Preservar as URLs atuais de ntconcursos.com.br (o site está em análise no AdSense); redirecionamentos 301 se alguma mudar
- [ ] `<title>`, meta description e canonical próprios por página; `lastmod` real no sitemap
- [ ] Concursos encerrados: a página permanece com o selo "Inscrições encerradas", sai da home e das listas e mantém o canonical
- [ ] Filtros combinados (estado + banca + cargo) com `noindex`; só páginas com conteúdo próprio são indexadas
- [ ] Página `/metodologia` explicando a verificação e mostrando as evidências (diferencial contra *thin content*)
- [ ] `AdSlot.astro` com `min-height` por breakpoint; Lighthouse CI no `ci.yml` com CLS < 0,05 como critério de bloqueio
- [ ] `ads.txt` com o `pub-ID` real; política de privacidade; banner de consentimento LGPD com Consent Mode v2
- [ ] Afiliados apenas via `LinkAfiliado.astro` (`rel="sponsored noopener"` + rótulo "publicidade")

## 9. Milestones

| # | Entrega | Critério de pronto |
|---|---|---|
| M0 | Esqueleto: repositório, Pydantic → JSON Schema, CI, Astro com páginas institucionais, `ads.txt` | `ci.yml` verde; site de teste no Pages |
| M1 | INLABS (descoberta federal) + Cebraspe e FGV de ponta a ponta; campos `categoria`, `esfera` e filtro de escopo (seção 11) | 1 concurso real publicado com evidência clicável; horário real do INLABS medido |
| M2 | Publicação automática (Worker + `publish.yml` + alerta) | 7 dias seguidos publicados antes das 05h00 |
| M3 | Painel admin (`admin.ntconcursos.com.br`, seção 12) + retificações | Aprovar/corrigir pela tela gera PR; CI valida e incorpora |
| M4 | FCC, Vunesp e demais bancas do escopo, por ordem de porte | Testes com fixtures reais por banca |
| M5 | SEO avançado, consentimento, afiliados, Lighthouse CI | CLS medido < 0,05; avaliação do `JobPosting` |
| M6 | Opcional: LLM sugestor atrás do gate; runner self-hosted | Só se a taxa de revisão manual passar de ~20% |

## 10. Divisão do trabalho

Decidido em 12/11/2026 para reduzir o repasse manual entre IAs: **Claude escreve o código; o Codex
revisa uma vez por milestone** (o dono cola o diff no Codex e devolve a crítica). O contrato de dados
(seção 5 e `docs/CONTRATO-DADOS.md`) só muda por PR próprio.

| Milestone | Status |
|---|---|
| M0 | esqueleto, contrato, gate G1–G8, site, CI, publicação e Worker: entregue |
| M1 | contrato v2 (PR #1) e M1 (PR #2) incorporados em 12/11/2026. FGV publica 3 concursos (TJ-PB, TJ-SC Juiz, TJ-AP Juiz). Cebraspe coleta tudo, mas publica 0: os prazos só aparecem no cronograma em tabela. INLABS em manutenção: conector testado só com XML no formato documentado; horário ainda não medido (faltam os secrets INLABS_EMAIL/INLABS_SENHA) |
| M1.1 | cronograma em tabela com evidência de célula (PRs #3 e #4), resumo do concurso, "sobre a instituição" e cargos (PR #5): entregue em 12/11/2026. Cebraspe passa a publicar (PC-PE e Polícia Penal PE no primeiro dia) |
| M2 | publicação automática: próximo |

### Decisões tomadas no M1 (12/11/2026)

- **`requests` no lugar de `httpx`**: já disponível em todo ambiente do projeto; o cliente segue
  redirecionamentos manualmente para checar a allowlist em cada salto, antes de baixar.
- **`www.in.gov.br` não é coletado**: o robots.txt do portal é `Disallow: /`. A descoberta federal
  usa só o INLABS (`inlabs.in.gov.br`, sem robots), o canal oficial de dados abertos.
- **G7 refinado**: retificação posterior só derruba o prazo se não tiver texto, trouxer outra data
  para ele, falar de prorrogação/reabertura/suspensão do prazo ou for errata "onde se lê" que o cite.
  A regra anterior (qualquer menção a "inscrição") derrubava quase toda retificação da Cebraspe.
- **Datas de normas citadas** ("Lei nº 10.567, de 7 de novembro de 1997") são ignoradas na leitura
  de prazos; antes elas criavam cláusulas falsas e mandavam o campo para revisão (G5).
- **Concurso novo só entra com prazo verificado ainda aberto**; os já publicados continuam sendo
  atualizados (inclusive rebaixados para revisão se uma retificação mudar o prazo).
- **Cronograma em tabela não sustenta prazo sozinho**: o texto extraído separa as colunas e pode
  juntar o rótulo de uma linha com a data de outra (caso real: PC-PE 2026 daria isenção de 27/11 a
  3/12, que é a consulta à situação provisória). Trechos de tabela só servem para detectar conflito.
- **Extração com `pdftotext` (Poppler)** no lugar do pdfplumber: cerca de 25 vezes mais rápida,
  com as mesmas cláusulas. Carimbos de impressão do SEI ("10/04/2026, 11:19") não contam como data.
- **Cartórios (outorga de delegações), juiz leigo, processos seletivos e exames** ficam fora do escopo.
- **Bancas inacessíveis pelo Actions (12/11/2026)**: o robots.txt da FCC proíbe `/concursos/` e todos os
  PDFs; Vunesp, Cesgranrio, IBFC, Fundatec e Consulplan respondem 403 aos servidores do GitHub. Não se
  contorna: ficam para o plano B (coleta no PC do dono, com robots respeitado) ou autorização da banca.
  Acessíveis e ainda não implementadas: Instituto AOCP, Idecan, IADES, Ibade, Selecon, Quadrix, Instituto Acesso.
- **INLABS sem previsão de volta**: a descoberta federal segue pelas bancas. A Base de Dados de
  Publicações do DOU (substituto indicado pela Imprensa Nacional) fica em www.in.gov.br, cujo robots.txt
  proíbe tudo; só será usada com autorização escrita da Imprensa Nacional.
- **Resumo por órgão** (`data/orgaos.json`) só vai ao ar com `revisado: true`; os textos por categoria são
  autorais e genéricos (sem dado que mude de edital para edital).

## 11. Escopo e prioridade (decidido em 12/11/2026; Tribunais de Contas, Defensorias, Bombeiros e Polícias Legislativas incluídos no mesmo dia)

**Escopo:** concursos de órgãos **federais e estaduais** destas áreas. Municipais ficam fora.

| Categoria | Exemplos |
|---|---|
| `tribunal` | STF, STJ, TST, TSE, STM, TRFs, TRTs, TREs, TJs, TJMs |
| `controle` | CGU, controladorias e auditorias-gerais dos estados, TCU, TCEs e TCMs estaduais |
| `mp` | MPU (MPF, MPT, MPM, MPDFT) e MPs estaduais |
| `defensoria` | DPU e Defensorias Públicas estaduais |
| `seguranca` | PF, PRF, Polícia Penal Federal, polícias civis, militares, penais e científicas, corpos de bombeiros militares, polícias legislativas (Câmara, Senado e assembleias) |

A organização é **por órgão, não por banca**: a banca é só o lugar onde o edital é publicado.
Cada concurso ganha `categoria` e `esfera` (`federal`/`estadual`); concurso fora do escopo é descartado na coleta.

**Descoberta:**
1. DOU via INLABS, para os órgãos federais.
2. Sites das bancas, que listam concursos federais e estaduais num só lugar. Os diários oficiais
   estaduais são 27 sistemas diferentes e ficam como fonte complementar futura.

**Ordem das bancas:** pelas que mais organizam concursos do escopo. Começa por Cebraspe e FGV (M1),
depois FCC e Vunesp, e então as demais, conforme o volume medido nas primeiras semanas.

**Porte:** `porte = vagas imediatas` (cadastro reserva não conta), com remuneração e esfera federal
como desempate. Uso no site:
- a lista de **isenção aberta continua ordenada pelo prazo** (perder o prazo é o problema principal),
  com selo "grande porte";
- um bloco **"Em destaque"** no topo da home mostra os maiores concursos com inscrição aberta.

## 12. Painel admin (aprovado em 12/11/2026, substitui as Issues do M3)

- Endereço `admin.ntconcursos.com.br`, protegido pelo Cloudflare Access (código por e-mail, só o
  e-mail do dono). O plano gratuito do Zero Trust cobre até 50 usuários.
- Fila de pendências com o concurso, o campo, o motivo da regra que falhou e o texto da página do edital.
- O revisor seleciona o trecho com o mouse e escolhe **aprovar**, **corrigir** ou **deixar como
  "Consulte o edital"**.
- Um Worker por trás do Access guarda o token do GitHub (nunca no navegador). Cada decisão vira um
  PR; o CI roda `ntc validate` e incorpora só se passar. Uma revisão errada é recusada e nunca
  trava a edição do dia.
- Ficam registrados quem aprovou, quando e com qual trecho (`aprovado_por`, `aprovado_em`).
