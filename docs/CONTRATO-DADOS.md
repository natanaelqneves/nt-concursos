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
| `data/revisao/<slug>.json` | campos em revisão e motivos (regra do gate, cláusulas conflitantes) |
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
| `uf` | federais usam `BR`, exceto `tribunal` e `conselho`, que usam a UF da sede regional |

Municipais continuam fora, inclusive TI municipal e empresas municipais. O mesmo vale para `data/noticias`.

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
