# Contrato de dados

A fonte da verdade é o modelo Pydantic em `collector/src/ntc/model/schema.py`. O arquivo
`schema/concurso.schema.json` é gerado dele (`ntc schema`) e o CI falha se estiver desatualizado.
**Mudanças no contrato exigem PR próprio**, revisado antes de qualquer código que dependa delas.

## Arquivos

| Caminho | Conteúdo |
|---|---|
| `data/fontes.yaml` | allowlist: sufixos oficiais e domínios por banca |
| `data/concursos/<slug>.json` | um concurso (o nome do arquivo deve ser igual ao `slug`) |
| `data/documentos/<sha256>.json` | texto das páginas citadas por evidências, para auditoria e revalidação |
| `data/revisao/<slug>.json` | campos em revisão, motivos e as opções lidas no edital para cada campo |
| `data/decisoes/<slug>/<AAAAMMDD-HHMMSS>.json` | decisão do editor sobre uma pendência (escolher opção, deixar sem data, descartar) |
| `data/execucoes/<AAAA-MM-DD>.json` | log das coletas do dia, uma chave por fonte, com a situação de cada concurso visto |
| `data/descobertas/<AAAA-MM-DD>.json` | editais de abertura do escopo achados no DOU (INLABS) naquele dia |

## Versão 2 (M1, 12/11/2026)

| Campo | Regra |
|---|---|
| `categoria` | `tribunal`, `controle`, `mp`, `defensoria` ou `seguranca` (obrigatório) |
| `esfera` | `federal` ou `estadual` (obrigatório). Federal fora do Judiciário usa `uf: "BR"`; TRF/TRT/TRE usam a UF da sede; estadual nunca usa `BR` |
| `vagas_imediatas` | campo factual (`valor` inteiro + `status` + `evidencia`): total de vagas imediatas declarado numa frase do edital ("destina-se ao provimento de N vagas"); cadastro reserva não conta |
| `porte` | derivado e conferido pelo schema: `grande` (≥ 100 vagas imediatas verificadas), `medio` (≥ 20), `pequeno`, `indefinido` (sem vagas verificadas) |
| `documentos[].publicado_em` | data de publicação informada pela banca; ordena edital e retificações no G7 |
| `documentos[].titulo` | rótulo do documento na página da banca |

Classificação de escopo: `collector/src/ntc/escopo.py` (regras explícitas, com testes em
`tests/test_escopo.py`). Concurso fora do escopo não gera arquivo, só uma linha no log da execução.

## Versão 2 (M1, 12/11/2026)

| Campo | Regra |
|---|---|
| `categoria` | `tribunal`, `controle`, `mp`, `defensoria` ou `seguranca` (obrigatório) |
| `esfera` | `federal` ou `estadual` (obrigatório). Federal fora do Judiciário usa `uf: "BR"`; TRF/TRT/TRE usam a UF da sede; estadual nunca usa `BR` |
| `vagas_imediatas` | campo factual (`valor` inteiro + `status` + `evidencia`): total de vagas imediatas declarado numa frase do edital ("destina-se ao provimento de N vagas"); cadastro reserva não conta |
| `porte` | derivado e conferido pelo schema: `grande` (≥ 100 vagas imediatas verificadas), `medio` (≥ 20), `pequeno`, `indefinido` (sem vagas verificadas) |
| `documentos[].publicado_em` | data de publicação informada pela banca; ordena edital e retificações no G7 |
| `documentos[].titulo` | rótulo do documento na página da banca |

Classificação de escopo: `collector/src/ntc/escopo.py` (regras explícitas, com testes em
`tests/test_escopo.py`). Concurso fora do escopo não gera arquivo, só uma linha no log da execução.

## Áreas novas (12/11/2026, compatível com a versão 2)

| Campo | Regra |
|---|---|
| `categoria` | ganha `estatal` (empresas públicas e sociedades de economia mista federais e estaduais), `conselho` (conselhos profissionais) e `outro` (demais órgãos federais e estaduais) |
| `areas` | lista de áreas dos cargos; por enquanto só `"ti"` (cargo de tecnologia da informação). Vale para qualquer categoria |
| `outro` | só existe com `areas: ["ti"]`: órgão fora das categorias entra apenas se tiver cargo de TI |
| `uf` | federais usam `BR`, exceto `tribunal`, `conselho` e (desde 13/11) `educacao`, que usam a UF da sede |

Municipais continuam fora, inclusive TI municipal e empresas municipais. O mesmo vale para `data/noticias`.

Ainda em 12/11/2026, `categoria` ganha mais quatro valores (compatível com a versão 2):

| Valor | O que cobre |
|---|---|
| `fiscal` | Receita Federal (`BR`) e secretarias estaduais de Fazenda / receitas estaduais |
| `advocacia` | AGU e PGFN (`BR`), procuradorias-gerais dos estados e do DF |
| `executivo` | só federal (`BR`): ministérios, autarquias e fundações, agências reguladoras, INSS, IBGE, Banco Central, CNU |
| `legislativo` | Câmara dos Deputados e Senado (`BR`), assembleias legislativas e Câmara Legislativa do DF |

Polícia legislativa continua em `seguranca`. Procuradorias municipais e câmaras municipais ficam fora.

Em 13/11/2026, `categoria` ganha mais três valores e `executivo` passa a aceitar a esfera estadual
(compatível com a versão 2):

| Valor | O que cobre |
|---|---|
| `executivo` | federal (`BR`) como antes e, agora, **gestão estadual**: secretarias estaduais de administração, planejamento e gestão, concursos unificados estaduais e carreiras de gestor governamental (EPPGG) |
| `educacao` | universidades e institutos federais (federal, com a UF da sede, como `tribunal` e `conselho`) e secretarias estaduais de educação |
| `saude` | só estadual: secretarias estaduais de saúde e fundações estaduais de saúde |
| `militar` | só federal (`BR`): Exército, Marinha e Aeronáutica, nas seleções de carreira (escolas de formação, quadros técnicos e de saúde) |

Ficam fora, como antes: seleções temporárias (inclusive serviço militar temporário e professor
substituto), processos seletivos simplificados, universidades estaduais e secretarias municipais.

## Evidência de tabela (12/11/2026, compatível com a versão 2)

Cronogramas em tabela (padrão da Cebraspe) são lidos célula por célula no PDF. A evidência ganha:

```json
"tabela": {"atividade": "Período de solicitação de inscrição com isenção de taxa de inscrição",
           "datas": "15/10 a 12/11/2026"},
"trecho": "Período de solicitação de inscrição com isenção de taxa de inscrição — 15/10 a 12/11/2026",
"metodo": "tabela:v1"
```

- `trecho` é sempre `atividade — datas` (o schema confere).
- G3: cada célula precisa aparecer, literalmente (normalizando espaços), no texto da página.
- G4: a âncora e as exclusões valem para a célula `atividade`; as datas declaradas saem só da célula `datas`.
- O pareamento linha a linha (qual data é de qual atividade) é feito na coleta, pela geometria da
  tabela no PDF identificado pelo `sha256`; texto corrido de cronograma continua não sustentando prazo.

## Revisão e decisões do editor (12/11/2026, compatível com a versão 2)

`data/revisao/<slug>.json` (versão 2) passa a trazer, além de `campos_em_revisao` e `motivos`:

| Campo | Regra |
|---|---|
| `schema_version` | `2` |
| `situacao` | `publicado` (já está no site, com o campo rebaixado) ou `so_revisao` (ainda não está no site) |
| `categoria`, `esfera`, `uf`, `cargos` | como no concurso, para o editor saber do que se trata |
| `opcoes` | por campo (`prazos.isencao`, `prazos.inscricao`), as leituras do edital: `id` (`o-N`), `origem` (`texto` ou `tabela`), `pagina`, `trecho`, `ancora`, `inicio`, `fim` e, na tabela, `tabela` (`atividade`, `datas`). No máximo 8 por campo |
| `mudancas` | documentos de mudança listados pela banca: `titulo`, `url`, `publicado_em` |

A coleta **não grava** revisão de concurso que não está no site e cujas opções já terminaram todas
(prazo vencido): não há o que decidir.

Decisão do editor: um arquivo novo por decisão em `data/decisoes/<slug>/`, o mais recente vale:

```json
{"schema_version": 1, "slug": "pm-al-2026", "decidido_em": "2026-11-12T19:10:00-03:00",
 "edital_sha256": "…", "acao": "decidir",
 "campos": {"prazos.inscricao": {"acao": "usar", "opcao": {"origem": "tabela", "pagina": 41,
            "trecho": "…", "inicio": "2026-11-03", "fim": "2026-12-02"}},
            "prazos.isencao": {"acao": "ausente"}}}
```

- `acao` do arquivo: `decidir` (vale `campos`) ou `descartar` (o concurso deixa de ser coletado).
- `acao` do campo: `usar` (a opção vira evidência com `aprovado_por: "editor"` e `aprovado_em` =
  `decidido_em`) ou `ausente` (o campo fica sem data e sai da revisão).
- A decisão só vale enquanto o edital for o mesmo (`edital_sha256`), a opção ainda aparecer igual
  (mesma página e trecho) na leitura do edital e nenhuma retificação tiver sido publicada depois de
  `decidido_em`. Se qualquer uma falhar, o campo volta para a revisão com o motivo.
- A aprovação continua sujeita a G1–G3: uma decisão não publica nada que não esteja literalmente no edital.
- A página `/admin/` do site (fora do sitemap, `noindex`) lista as revisões e gera o arquivo de decisão
  como um "novo arquivo" no GitHub; o editor confirma o commit lá. Nenhuma chave fica no site.

## Regras do concurso

- Todo campo factual (`prazos.*`, `taxa`, `cargos.N.vagas`, `cargos.N.remuneracao`) tem `status`
  (`verificado`, `revisao` ou `ausente`) e `evidencia` (id).
- `verificado` exige evidência; prazo verificado exige `fim`; `inicio ≤ fim`.
- Toda evidência aponta para um documento existente, e o `campo` da evidência precisa ser
  exatamente o caminho do campo que a referencia.
- Campos desconhecidos são recusados (`extra="forbid"`): nada entra no JSON sem estar no contrato.
- Retificação é um novo `documento` com `tipo: "retificacao"`; nada é apagado, e o histórico fica no Git.
- O site só exibe campos `verificado`. Os demais aparecem como "Consulte o edital".

## Gate de evidência

Implementado em `collector/src/ntc/gate/evidencia.py`. Roda na coleta (com o PDF inteiro) e de novo
no CI e em toda publicação (com as páginas guardadas em `data/documentos/`). Campo que falha
é rebaixado para `revisao`; na publicação, qualquer falha em campo `verificado` bloqueia o deploy.

| Regra | O que exige |
|---|---|
| G1 | host da URL final (após redirecionamentos), sobre HTTPS, na allowlist |
| G2 | texto do documento guardado para o `sha256` declarado |
| G3 | `trecho` contido literalmente na `pagina` (normalizando só espaços) |
| G4 | trecho com a âncora do campo, sem termos de outro evento, e com exatamente as datas/valor declarados (datas de normas citadas, como "Lei nº 10.567, de 7 de novembro de 1997", são ignoradas) |
| G5 | uma só cláusula de datas para o campo no documento inteiro (só na coleta); "até 18/11" é compatível com "de 20/10 a 18/11" |
| G6 | ano próximo ao da coleta; isenção não termina depois das inscrições |
| G7 | documento de mudança publicado depois (retificação, comunicado, prorrogação) derruba o prazo se não tiver texto, se trouxer cláusula do prazo com outras datas (ou ambígua), se falar do prazo junto de prorrogação/reabertura/suspensão, ou se for errata "onde se lê" que o cite. Citar só "taxa de inscrição" sem data não derruba |
| G8 | PDF sem camada de texto não sustenta campo nenhum |

Aprovação humana (`aprovado_por` + `aprovado_em`) dispensa G4–G7, nunca G1–G3.

## O que fica guardado em `data/documentos/`

- Do edital: só as páginas citadas por evidências.
- Dos documentos de mudança: as páginas que o G7 lê (citam isenção/inscrição ou trazem "onde se lê"),
  e um registro mesmo quando nenhuma página cita prazo, para o `ntc validate` saber que o texto existiu.

## Notícias apuradas (`data/noticias/<slug>.json`, desde 12/11/2026)

Arquivo separado do contrato do concurso, com schema próprio (`schema/noticia.schema.json`,
gerado de `collector/src/ntc/model/noticia.py`). Serve para concursos do escopo que o coletor
ainda não consegue conferir no edital (banca bloqueada, INLABS fora do ar).

| Regra | Conferida por |
|---|---|
| Cada fato cita fontes: 2 de veículos diferentes (subdomínios do mesmo site contam como um) ou 1 oficial consultada | schema |
| Toda fonte listada sustenta algum fato | schema |
| `expira_em` = fim das inscrições; a página sai das listas depois dessa data e ganha `noindex` | schema e site |
| Texto próprio (`resumo`, `fatos[].texto`), nada copiado das fontes | revisão |
| Órgão que já tem concurso verificado aberto: a notícia some das listas do site e o `ntc validate` avisa | site e validate |

## Editais avulsos e cópias (13/11/2026, compatível com a versão 2)

Concursos que a imprensa noticia e cujo edital não está numa fonte que o coletor alcança
(banca sem coletor, PDF bloqueado por robots.txt) entram pela fonte `avulsos`.

| Item | Regra |
|---|---|
| `data/editais-avulsos.json` | lista mantida à mão: `slug` (fixo), `noticia` (slug em `data/noticias/` que o concurso substitui), `titulo`, `banca`, `uf` (opcional, corrige o classificador), `pagina`, `cargos`, `contexto`, `documentos[]` (`tipo`, `titulo`, `publicado_em`, `urls` em ordem de preferência: oficial primeiro, cópias depois) e `pesquisa[]` (onde se procurou o edital; aparece no fim da página) |
| `data/fontes.yaml`, `papel: copia` | sites de concursos que publicam cópias de editais. Entram na allowlist, mas só são usados pela fonte `avulsos` |
| `documentos[].fonte` | nas bancas, o nome da banca (como antes). Nos avulsos, a entrada de `fontes.yaml` que cobre o host da URL final (ex.: `qconcursos`) ou `oficial` quando só um sufixo oficial cobre (ex.: `trf3.jus.br`) |
| `banca` | nos avulsos, a banca real informada na lista (ex.: `idecan`, `fcc`, `vunesp`) |
| Prazo nos avulsos | pode ter evidência numa retificação (prorrogação); o G7 olha só as retificações posteriores à evidência. Se a data do documento diferir da publicada pela imprensa na notícia ligada, o prazo vai para `revisao` |
| Site | documento com `fonte` de `papel: copia` é exibido como "cópia publicada por …"; a notícia ligada sai do ar quando o concurso conferido está aberto |
