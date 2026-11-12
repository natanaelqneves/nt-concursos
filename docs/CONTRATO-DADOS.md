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
| `data/revisao/<id>.json` | casos pendentes de revisão humana (M3) |
| `data/execucoes/<AAAA-MM-DD>.json` | log das coletas do dia (M1) |

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
| G4 | trecho com a âncora do campo, sem termos de outro evento, e com exatamente as datas/valor declarados |
| G5 | uma só cláusula de datas para o campo no documento inteiro (só na coleta) |
| G6 | ano próximo ao da coleta; isenção não termina depois das inscrições |
| G7 | retificação posterior que mencione o prazo derruba a evidência anterior |
| G8 | PDF sem camada de texto não sustenta campo nenhum |

Aprovação humana (`aprovado_por` + `aprovado_em`) dispensa G4–G7, nunca G1–G3.
