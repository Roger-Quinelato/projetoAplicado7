# Evidências, execuções e limitações

Este índice reúne as evidências do pacote. Os registros completos de cada frente estão em `evidencias/`:

- `agente1/`: requisitos e entregas, evidências E1-01..E1-36.
- `agente2/`: arquitetura e comportamento, evidências E2-01..E2-24, scripts `exp/eNN_*.py` com as saídas `.out` e `mapa_arquitetural.md`.
- `agente3/`: qualidade, segurança e operação, evidências E3-01..E3-32, `execucoes.md` (X1–X25), `scripts/`, `logs/` e `shots/`.
- `BRIEFING.md`: critérios comuns distribuídos aos agentes.
- `manifest_3a3d8bd.sha256`: hashes da cópia isolada.

## Isolamento

- **Cópia auditável:** a cópia descartável foi criada com `git archive 3a3d8bd` e tem 110 arquivos, sem contar `.claude/`. O manifesto SHA-256 está em `evidencias/manifest_3a3d8bd.sha256`.
- **O que ficou fora da cópia:** `.env`, bancos existentes, `node_modules`, caches e worktrees.
- **Conferência do manifesto:** antes e depois das execuções (`sha256sum -c --quiet` → OK). As execuções acrescentaram à cópia `web/node_modules`, `web/dist`, `__pycache__` e o link `tmp`, mas nenhum arquivo do manifesto mudou.
- **Variáveis de ambiente:** nenhuma `DATABASE_URL`, `RABBITMQ_URL`, `PUBLIC_DEMO` ou `DEMO_ACCESS_TOKEN` foi herdada. Mesmo assim, toda execução usou `env -u` para essas quatro variáveis.
- **Bancos usados:** só bancos descartáveis, SQLite na pasta de trabalho e PostgreSQL 16.14 local na porta 55432, apenas em 127.0.0.1.
- **Token de demonstração pública:** foi gerado localmente com `secrets.token_urlsafe(32)` e não está neste pacote nem em nenhum log.
- **Entregáveis finais:** os arquivos `output/*.docx` e `output/*.pptx` não foram regenerados. Foram inspecionados e renderizados a partir de cópias, e os SHA-256 dos originais não mudaram.

## Execuções

Fonte: `evidencias/agente3/execucoes.md`. As versões estão em `logs/freeze_311.txt` e `logs/freeze_312.txt`.

| # | Comando | Ambiente | Resultado | Log |
|---|---|---|---|---|
| X1 | `python -m pytest -q tests -p no:cacheprovider` | Py 3.11.15, SQLite | 57/57 | `logs/pytest_py311.log` |
| X2 | idem | Py 3.12.3, SQLite | 57/57 | `logs/pytest_py312.log` |
| X17 | idem, com `conftest` alterado (experimento) | Py 3.11, PG 16.14 | 57/57 | `logs/pytest_postgresql_experimento.log` |
| X3 | `python tools/export_openapi.py --check` | Py 3.11 | rc=0, saída byte-idêntica, spec válida | `logs/export_openapi_check.log` |
| X4 | `npm ci && npm run build` | Node 22.22.0 (o CI usa 24) | OK, 0 vulnerabilidades | `logs/npm_ci.log`, `logs/npm_build.log` |
| X5 | `npm run test:browser` | — | **Não aplicável**: o script não existe em `3a3d8bd` | — |
| X15 | `scripts/performance_smoke.py` | SQLite e PG | p95 de 11,1–13,7 ms; mede só `/health/ready` (prontidão), não F1–F3 | `logs/performance_smoke.log` |
| X16 | `perf_flows.py` (complementar) | SQLite e PG | p95 de F1–F3 entre 38,7 e 50,7 ms | `logs/perf_flows.log` |
| X6/X7 | `mig_exp.py` | SQLite e PG | Banco vazio, legado 0001 com dados e downgrade/upgrade OK; caso 5 falha em PG | `logs/migracoes_*.log` |
| X8/X9 | modo público + RLS + reinício | PG com `anon`/`authenticated` simulados | segredo OK; `alembic_version` exposta; persistência após reinício OK | `logs/uvicorn_pg_public*.log` |
| X10/X11 | `conc_exp.py`, `conc_inproc.py` | PG, 1 processo uvicorn | 2 eventos de ativação; despacho `[200,500]`; 0 duplicidades de efeito | `logs/concorrencia_pg_1worker.log` |
| X12 | `poison_exp.py` | PG | 5 despachos com 500; outbox bloqueada | `logs/evento_venenoso_pg.log` |
| X13 | validações por curl | PG | `amount=1e15` → 500 | `logs/uvicorn_pg_valid.log` |
| X14 | `rabbit_exp.py`, `rabbit_timing.py` | SQLite, broker indisponível | FAILED com motivo vazio; 10,01 s (host sem resposta) e 15,01 s (TCP sem AMQP) por evento | `logs/rabbit_*.log` |
| X18 | `web_journey.py` (Playwright 1.56, Chromium 141, axe-core 4.13) | uvicorn + PG servindo `web/dist` | jornada F1–F3 OK; duplo clique gera 2 eventos; contraste *serious* | `logs/web_journey.log`, `shots/` |
| X19 | cabeçalhos e `/metrics` | SQLite, `PUBLIC_DEMO=true` | sem cabeçalhos de segurança; 600 séries após 300 requisições anônimas | `logs/cabecalhos_cors.log`, `logs/metrics_publico.txt` |
| X21/X22 | `pip-audit -s pypi`, `npm audit` | PyPI, npm | starlette 0.47.3: 7 advisories; pytest 8.4.1: 1; npm: 0 | `logs/pip_audit_pypi.log`, `logs/npm_audit.json` |
| X23 | cabeçalho Range com 8000 intervalos | SQLite | 7,58 s; `/health/live` de 0,005 s para 0,56 s | `logs/range_header_starlette.log` |
| — | Experimentos da frente 2 (`exp/e04`–`e13`) | Py 3.11, SQLite | F1–F3, falhas injetadas, concorrência com barreira, contratos | `evidencias/agente2/exp/*.out` |
| — | Revisão cruzada: `ordem_exp.py`, `pagamento_exp.py`, `rx/x1_meio_centavo.py` | PG e SQLite | AUD-04 e AUD-09 confirmados | `logs/ordem_customer_updated_pg.log`, `logs/pagamento_fracao_pg.log`, `agente1/rx/x1.out` |
| X25 | `docker info` | — | daemon indisponível; build e Compose **não executados** | — |

## Referências externas consultadas (somente leitura)

| Fonte | Data/hora (UTC) | Conteúdo | Evidência |
|---|---|---|---|
| GitHub (MCP): issues, PRs, Actions, marcos | 01/10/2026 20:37–20:44 | 22 issues; PR #28 mesclado em 30/09 02:29Z; PR #29 em rascunho; run 36660119780 (`3a3d8bd`) success; run 36662056291 (PR #29) success; 0 deployments | E1-28, E1-30, E1-33, X24 |
| Jira ARCH7 (Atlassian Rovo) | 01/10/2026 20:37–20:44; reconsulta na onda 2 | 22 itens; ARCH7-1..5 "Concluído" sem resolução | E1-29, E1-31; `agente2/revisao_cruzada.md` |
| Trello | 01/10/2026 | 22 cartões com link para o Jira; T01–T05 em "Concluído" | E1-32 |
| Notion e Google Drive | 01/10/2026 | nenhuma página ou arquivo do projeto localizado; enunciado "Localiza" não encontrado | E1-03, E1-15, E1-34 |
| PyPI JSON API (agrega GHSA/PYSEC) | 01/10/2026 20:53 | advisories da starlette 0.47.3 e do pytest 8.4.1 | `logs/pypi_vuln_detalhes.txt` |
| OSV.dev | 01/10/2026 20:52 | **falhou** (proxy 403) | `logs/osv_resultado.txt` |

## Limitações de verificação

| ID | Limitação | Efeito nas conclusões |
|---|---|---|
| L-01 | `execucao-tarefas-pendentes`/`3fdb533` não publicada | Progresso posterior a `3a3d8bd` não auditado (AUD-50) |
| L-02 | Enunciado "Localiza" não localizado | Comparação feita só com o `Guia.pdf` |
| L-03 | Docker sem daemon | Imagem e Compose comprovados só pelo CI; `HEALTHCHECK` e usuário da imagem avaliados por inspeção |
| L-04 | RabbitMQ ausente | Broker simulado com porta fechada e host sem resposta; o descarte da cópia é inferido por inspeção (confiança média) |
| L-05 | Render e Supabase não acessados | T20 sem evidência; RLS avaliado com privilégios Supabase **simulados** em PG local |
| L-06 | Notion, Drive e GitHub Project não alcançados (GraphQL indisponível) | Partes de T21 "não verificadas"; a ausência não prova inexistência |
| L-07 | Changelog do Jira não consultado | Causa da transição de T01–T05 (manual ou fechamento de sprint) indeterminada |
| L-08 | OSV.dev e GitHub Advisory bloqueados pelo proxy | Vulnerabilidades obtidas pelo PyPI (pip-audit e API JSON); NVD não consultado |
| L-09 | Concorrência com 1 processo uvicorn; SQLite com barreira forçada | Cenários com `--workers` não testados |
| L-10 | Falhas de consumidor injetadas em memória ou na tabela | Bloqueio permanente de AUD-01 reproduzido só com injeção; o 500 transitório ocorre sem injeção |
| L-11 | Google Fonts bloqueadas | axe avaliou o contraste com a fonte de fallback |
| L-12 | Paginação medida no LibreOffice 24.2 | O Word pode paginar de forma diferente |
| L-13 | Python 3.11 e Node 22 locais (o CI usa 3.12 e 24) | A suíte também rodou em Python 3.12.3; o build web não foi repetido em Node 24 |
| L-14 | Diagrama Mermaid não validado em renderizador externo | Sintaxe conferida manualmente |
