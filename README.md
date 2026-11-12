# nt-concursos

Código do [ntconcursos.com.br](https://ntconcursos.com.br): concursos públicos com inscrições
abertas, com destaque para os prazos de **isenção da taxa**. Toda data publicada tem URL oficial,
página e trecho literal do edital, e passa por um gate automático de evidência antes de ir ao ar.

```
collector/   coletor e verificador em Python (modelo, parser de datas, gate G1–G8, CLI `ntc`)
data/        banco de dados do site: JSON versionado no Git (a trilha de auditoria é o git log)
schema/      JSON Schema gerado do modelo Pydantic
site/        site estático em Astro, publicado no Cloudflare Pages
worker/      Cloudflare Worker que dispara a edição diária às 04h00 BRT
docs/        arquitetura, contrato de dados e runbook de operação
```

## Rodar localmente

```bash
# coletor
cd collector
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
ntc validate          # valida data/ inteiro contra o schema e o gate
ntc schema --check    # confere se schema/concurso.schema.json está em dia

# site
cd ../site
npm install
npm run dev           # http://localhost:4321
```

## Documentação

- [docs/ARQUITETURA.md](docs/ARQUITETURA.md): decisões, pipeline, milestones
- [docs/CONTRATO-DADOS.md](docs/CONTRATO-DADOS.md): formato dos JSON e regras do gate
- [docs/RUNBOOK.md](docs/RUNBOOK.md): configuração inicial, operação diária e o que fazer quando algo falha
