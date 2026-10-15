# Execuções — Agente 3 (Qualidade, segurança e operação)

Referência: `3a3d8bd` (cópia isolada `$SP/iso`, manifesto conferido **antes** e **depois** das execuções: `sha256sum -c ../manifest_3a3d8bd.sha256 --quiet` → OK nas duas vezes). Repositório real não foi alterado (`git status --short` vazio).

`$SP` = `/tmp/claude-0/-home-user-projetoAplicado7/ec00d59b-c354-5d1f-b4d6-080b88ac1d06/scratchpad`; `$A` = `$SP/agente3`. Logs completos em `$A/logs/`.

## Ambiente

- SO: Linux 6.18 (contêiner), 4 vCPU Intel Xeon @ 2.10GHz, usuário root.
- Python 3.11.15 (`$A/venv`) e Python 3.12.3 (`$A/venv312`), ambos com `requirements-dev.txt`. Versões resolvidas idênticas nos dois (freeze em `logs/freeze_311.txt`, `logs/freeze_312.txt`): fastapi 0.116.1, **starlette 0.47.3 (transitiva)**, SQLAlchemy 2.0.43, alembic 1.20.0, psycopg 3.2.9, pydantic 2.13.5, uvicorn 0.35.0, pika 1.3.2, anyio 4.15.1, pytest 8.4.1.
- Node 22.22.0 / npm 10.9.4 (CI e Dockerfile usam Node 24 — divergência registrada).
- PostgreSQL 16.14 descartável: `initdb --username=pgadmin --auth=trust` executado como usuário `postgres` (via `runuser`); porta 55432, somente 127.0.0.1. **Desvio:** o diretório de dados foi movido para `/tmp/a3pg` porque o ambiente restaurou a permissão 700 de `/tmp/claude-0` (impede acesso do usuário `postgres`) e o caminho do socket Unix excedia 107 bytes (`logs/pg_initdb.log`, `$A/pg_LOCALIZACAO.txt`).
- Variáveis herdadas: `env | grep -i -E 'database|rabbit|token'` (valores mascarados) → apenas `MAX_THINKING_TOKENS`, `GH_TOKEN`, `GITHUB_TOKEN`, `CLOUDSDK_AUTH_ACCESS_TOKEN`, `CLAUDE_SESSION_INGRESS_TOKEN_FILE`, `CLAUDE_CODE_MESSAGING_TOKEN`. Nenhuma `DATABASE_URL`, `RABBITMQ_URL`, `PUBLIC_DEMO` ou `DEMO_ACCESS_TOKEN` herdada; mesmo assim todas as execuções usaram `env -u DATABASE_URL -u RABBITMQ_URL -u DEMO_ACCESS_TOKEN -u PUBLIC_DEMO`.
- RabbitMQ: não instalado (apenas `librabbitmq4`, biblioteca cliente C); porta 5672 fechada.
- Docker: cliente presente, daemon ausente (`/var/run/docker.sock` inexistente) → `docker build`/`compose` **não executados**.
- `DEMO_ACCESS_TOKEN` dos testes de modo público: gerado com `secrets.token_urlsafe(32)` e guardado em `$A/.demo_token_local` (permissão 600); não aparece em nenhum log (verificado por grep).

## Banco descartável da suíte

`tests/conftest.py:4-5` **sobrescreve incondicionalmente** `DATABASE_URL` com `sqlite:///./tmp/test-archcorp.db` (relativo ao cwd). Para que o arquivo ficasse em `$A/`, criei o link simbólico `$SP/iso/tmp -> $A/tmp`. Resultado: banco em `$A/tmp/test-archcorp.db`. Consequência: a suíte não pode ser apontada para PostgreSQL por variável de ambiente (ver A3-17).

## Tabela de execuções

| # | Início (UTC) | Comando (cwd `$SP/iso`, `PYTHONPATH=src`) | Ambiente relevante | Resultado | Duração |
|---|---|---|---|---|---|
| X1 | 2026-10-01T20:38:48Z | `env -u DATABASE_URL ... $A/venv/bin/python -m pytest -q tests -p no:cacheprovider -rA` | Py 3.11.15, SQLite `$A/tmp/test-archcorp.db` | **57 coletados, 57 aprovados**, 1 aviso (DeprecationWarning anyio BlockingPortal) — `logs/pytest_py311.log` | 10,8 s (pytest 9,03 s) |
| X2 | 2026-10-01T20:39:05Z | idem com `$A/venv312/bin/python` | Py 3.12.3, SQLite | **57/57 aprovados**, 1 aviso — `logs/pytest_py312.log` | 11,2 s (9,45 s) |
| X3 | 2026-10-01T20:39:29Z | `python tools/export_openapi.py --check` | `DATABASE_URL=sqlite:///$A/openapi-check.db` | rc=0 (flag existe, `tools/export_openapi.py:22`); comparação byte a byte do `render()` com o arquivo salvo: **idêntico** (SHA-256 `2a038eea…04b2` = manifesto); `openapi-spec-validator` OK | <5 s |
| X4 | 2026-10-01T20:39:41Z | `cd web && npm ci && npm run build` | Node 22.22.0 | `npm ci` rc=0 (21 pacotes, "found 0 vulnerabilities"); build rc=0 (tsc + vite 7.3.6; JS 240,52 kB) — `logs/npm_ci.log`, `logs/npm_build.log` | 5 s |
| X5 | — | `npm run test:browser` | — | **Não aplicável a este estado**: `web/package.json` em 3a3d8bd só tem `dev` e `build` | — |
| X6 | 2026-10-01T20:42:09Z | `python $A/mig_exp.py sqlite:///$A/mig_sqlite.db sqlite` | SQLite | vazio→head OK, 0 divergências; downgrade base→upgrade OK; legado 0001 com dados→head: dados e unicidades preservados; legado sem `alembic_version`→OK; `--sql` offline rc=255 (batch SQLite exige conexão) — `logs/migracoes_sqlite.log` | ~6 s |
| X7 | 2026-10-01T20:42:~15Z | `python $A/mig_exp.py postgresql+psycopg://pgadmin@127.0.0.1:55432/migexp postgresql` | PG 16.14 | igual ao SQLite, **exceto** caso 5 (esquema 0002 sem `alembic_version`) → `DuplicateColumn` na inicialização; `--sql` rc=0 (238 linhas) — `logs/migracoes_pg.log` | ~8 s |
| X8 | 2026-10-01T20:43Z | uvicorn em PG `rlsdb` com `PUBLIC_DEMO=true`; papéis `anon`/`authenticated` criados e `ALTER DEFAULT PRIVILEGES ... GRANT ALL ... TO anon, authenticated` (simulação dos padrões do Supabase) | PG | token curto e token `demo-…` → inicialização recusada (rc=3); `demo-admin` → 401; sem token → 401; token público → 200 (inclusive rota só-admin); `/metrics`, `/docs`, `/openapi.json` → 200 sem token; RLS ativa e privilégios revogados nas 16 tabelas do modelo; **`alembic_version` sem RLS e com SELECT/UPDATE/DELETE para `anon`**; sequências com USAGE para `anon` — `logs/uvicorn_pg_public*.log` | — |
| X9 | 2026-10-01T20:44Z | reinício do uvicorn (PG) e leitura do cliente criado antes | PG `rlsdb` | persistência após reinício **OK** (local); após `SET ROLE anon; DELETE FROM alembic_version` + reinício → **inicialização falha** (`DuplicateTable`) — `logs/uvicorn_pg_after_anon_delete.log` | — |
| X10 | 2026-10-01T20:45:08Z | `python $A/conc_exp.py http://127.0.0.1:18082 "<dsn concdb>" 15` (uvicorn 1 processo, threadpool) | PG `concdb` | 15/15 rodadas: ativação concorrente com chaves diferentes → [200,200] e **2 `ContractActivated.v1`**; mesma chave → [200,409]; reserva mesma chave → [201,409], 1 reserva; reserva sem chave → 2 reservas; **2 despachos simultâneos → [200,500]**; faturas/processos/inbox duplicados = 0 — `logs/concorrencia_pg_1worker.log` | ~40 s |
| X11 | 2026-10-01T20:46Z | `python $A/conc_inproc.py` (dois `dispatch_pending` em threads) | PG `conc2` | um despacho OK, outro `sqlalchemy.exc.PendingRollbackError` (falta `rollback()` no `except`) | — |
| X12 | 2026-10-01T20:46Z | `python $A/poison_exp.py` (evento com valor fora de Numeric(14,2) inserido na outbox + evento legítimo) | PG `conc2` | 5 despachos → **5×HTTP 500**; ambos eventos `PENDING`, `attempts=0`; `/integration/failures` vazio; fatura do contrato legítimo não criada — `logs/evento_venenoso_pg.log` | — |
| X13 | 2026-10-01T20:47Z | probes de validação via curl (uvicorn em PG) | PG | `amount=1e15` em rascunho → **500**; `1e20` → 500; reserva `1e16` → 500; `Idempotency-Key` 101 chars → 422; `X-Correlation-ID` inválido → 400; nome 151 → 422; e-mail inválido → 422 — `logs/uvicorn_pg_valid.log` | — |
| X14 | 2026-10-01T20:46:~50Z | `python $A/rabbit_exp.py sqlite:///$A/rabbit.db amqp://guest:guest@127.0.0.1:5999/%2F` e com host `192.0.2.1` | SQLite, `RABBITMQ_URL` para porta fechada / host TEST-NET | consumidores internos **executam** (1 fatura, 1 processo) mas evento fica `PENDING`→`FAILED` após 3 despachos; `reason` **vazio**; reprocessar repete a falha; falha rápida (0,05 s) nos dois casos (rede do contêiner recusa; timeout de host silencioso não medido) — `logs/rabbit_*.log` | — |
| X15 | 2026-10-01T20:47:28Z | `python scripts/performance_smoke.py` ×3 (Py 3.11), ×1 (Py 3.12), ×1 (PG) | `DATABASE_URL` explícito em `$A/` | p95 = **11,10 / 11,17 / 11,57 ms** (3.11), 13,32 ms (3.12), 13,70 ms (PG); todos PASS (<500 ms) — `logs/performance_smoke.log` | ~4 s cada |
| X16 | 2026-10-01T20:48:04Z | `python $A/perf_flows.py` (complementar, 100 iterações por fluxo) | SQLite e PG | SQLite: F1 p95 39,5 ms, F2 42,9 ms, F3 38,7 ms; PG: 43,7 / 50,7 / 45,3 ms — `logs/perf_flows.log` | ~10 s |
| X17 | 2026-10-01T20:48:48Z | suíte em PG (experimento): cópia `$A/iso_pg` com `conftest.py` alterado para ler `AUDIT_TEST_DATABASE_URL` | PG `testsuite` | **57/57 aprovados** — `logs/pytest_postgresql_experimento.log` | 24 s |
| X18 | 2026-10-01T20:50:31Z | `python $A/web_journey.py http://127.0.0.1:18090 "<dsn webdb>"` (Playwright 1.56.0 Python, Chromium 141 de `/opt/pw-browsers`, sem `playwright install`; axe-core 4.13.0 local via npm) | uvicorn em PG servindo `web/dist` | jornada completa OK (gate → token errado → token support → admin → cliente → duplicado → reserva → contrato → ativar → despachar → fatura → processo → chamado inválido → móvel); **duplo clique em "Ativar" gerou 2 `ContractActivated.v1`**; axe: `color-contrast` (serious) em todas as telas — `logs/web_journey.log`, `shots/01..13*.png` | ~20 s |
| X19 | 2026-10-01T20:51:21Z | curl de cabeçalhos/CORS e 300 GETs sem token com UUIDs distintos; `/metrics` sem token | SQLite, `PUBLIC_DEMO=true` | sem cabeçalhos de segurança; sem CORS (bloqueio padrão); `/metrics` cresceu para **612 linhas** (600 de caminhos 401) — `logs/cabecalhos_cors.log`, `logs/metrics_publico.txt` | — |
| X20 | 2026-10-01T20:52:18Z | OSV.dev `querybatch` | proxy | **falhou**: `Tunnel connection failed: 403 Forbidden` — `logs/osv_resultado.txt` | — |
| X21 | 2026-10-01T20:52:39Z | `pip-audit 2.10.1 -s pypi -r requirements-dev.txt` | PyPI (permitido pelo proxy) | 14 entradas / 7 advisories únicos em **starlette 0.47.3** e 1 em pytest 8.4.1 — `logs/pip_audit_pypi.log`, detalhes da API JSON do PyPI em `logs/pypi_vuln_detalhes.txt` (2026-10-01T20:53Z) | ~20 s |
| X22 | 2026-10-01T20:53:04Z | `npm audit --json` | registry.npmjs.org | 0 vulnerabilidades (`logs/npm_audit.json`) | — |
| X23 | 2026-10-01T20:53Z | Range com 10/1000/4000/8000 intervalos em `/assets/*.js` | SQLite | 0,04 / 0,73 / 3,68 / **7,58 s**; `/health/live` concorrente 0,56 s (vs 0,005 s); `RuntimeError: Response content longer than Content-Length` no log — `logs/range_header_starlette.log` | — |
| X24 | 2026-10-01 | GitHub MCP `actions_list` | API GitHub | run 36660119780 (push `main`, `3a3d8bd`) **success**, inclusive "Build deployable Docker image"; run 36662056291 (PR #29, `b58c933`) success; `actions/*@v7` resolvidas e executadas | — |
| X25 | 2026-10-01 | `docker info` | — | daemon indisponível → build/compose não executados | — |

## Limitações

- OSV.dev e GitHub Advisory via HTTP bloqueados pelo proxy (403); usei pip-audit com fonte PyPI e a API JSON do PyPI (que agrega GHSA/PYSEC). Não consultei NVD.
- Concorrência medida com um processo uvicorn (threadpool); `--workers` não foi testado. A injeção do "evento venenoso" (X12) é artificial (inserção direta na outbox), mas a mesma causa raiz aparece sem injeção em X10 (500 em despacho concorrente).
- Supabase real não acessado: privilégios padrão de `anon`/`authenticated` foram **simulados** com `ALTER DEFAULT PRIVILEGES`.
- Timeout do pika para host que descarta pacotes não foi observável (rede do contêiner recusa imediatamente).
- Docker/Compose, Render, Supabase, HTTPS público: não executados/não verificáveis neste ambiente.
- A cópia isolada recebeu arquivos novos (não constantes do manifesto): `tmp` (symlink), `web/node_modules`, `web/dist`, `web/tsconfig.tsbuildinfo`, `__pycache__`. Nenhum arquivo do manifesto mudou.
