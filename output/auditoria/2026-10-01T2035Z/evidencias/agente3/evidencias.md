# Evidências — Agente 3 (Qualidade, segurança e operação)

Referência auditada: `3a3d8bd`, cópia isolada `$SP/iso` (manifesto OK antes e depois). Detalhes de comando/ambiente em `execucoes.md`; logs em `$A/logs/`.

### E3-01 — Integridade da cópia isolada
- Tipo: comando
- Fonte/local: `cd $SP/iso && sha256sum -c ../manifest_3a3d8bd.sha256 --quiet`, 2026-10-01T20:36Z e ~20:54Z
- Resultado observado: `MANIFEST_OK` e `MANIFEST_OK_POS_EXECUCAO` (110 arquivos)
- Limitações: arquivos novos (node_modules, dist, tmp, __pycache__) não são cobertos pelo manifesto.

### E3-02 — Suíte backend Python 3.11
- Tipo: comando
- Fonte/local: `logs/pytest_py311.log`, 2026-10-01T20:38:48Z
- Comando: `env -u DATABASE_URL -u RABBITMQ_URL -u DEMO_ACCESS_TOKEN -u PUBLIC_DEMO PYTHONPATH=src python -m pytest -q tests -p no:cacheprovider -rA`
- Resultado observado: `57 passed, 1 warning in 9.03s` (11 test_contracts, 9 test_contracts_and_architecture, 14 test_crm, 3 test_extended_modules, 9 test_flows, 10 test_foundation, 1 test_public_database_security). Aviso: `DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated`.
- Comparação documental: `docs/EVIDENCIAS_VALIDACAO.md` registra 13 (13 e 14/09), 18 (27/09) e 57 (29/09). O valor vigente (57) **confere**; "13 testes" é histórico.
- Limitações: SQLite apenas (forçado por `tests/conftest.py:5`).

### E3-03 — Suíte backend Python 3.12 (paridade com CI)
- Tipo: comando — `logs/pytest_py312.log`, 2026-10-01T20:39:05Z, Python 3.12.3
- Resultado: `57 passed, 1 warning in 9.45s`.

### E3-04 — Suíte em PostgreSQL (experimento, cópia alterada)
- Tipo: comando — `logs/pytest_postgresql_experimento.log`, 2026-10-01T20:48:48Z
- Comando: cópia `$A/iso_pg` com `conftest.py` lendo `AUDIT_TEST_DATABASE_URL`; PG 16.14 descartável.
- Resultado: `57 passed, 1 warning in 20.74s`.
- Limitações: exige alterar o conftest (fora do repositório); o teste RLS continua sendo mock.

### E3-05 — conftest força SQLite
- Tipo: inspeção de código — `tests/conftest.py:4-6`
- Resultado: `os.environ["DATABASE_URL"] = "sqlite:///./tmp/test-archcorp.db"` (sobrescreve qualquer valor) e `os.environ.pop("RABBITMQ_URL", None)`.

### E3-06 — Teste de RLS é simulado
- Tipo: inspeção de código — `tests/test_public_database_security.py:8-27`
- Resultado: `Connection` falsa e `engine` substituído por `SimpleNamespace(dialect=postgresql.dialect())`; verifica apenas as strings SQL geradas.

### E3-07 — Contrato OpenAPI sincronizado
- Tipo: comando — `logs/export_openapi_check.log`, 2026-10-01T20:39:29Z
- Comando: `PYTHONPATH=src python tools/export_openapi.py --check` (flag existe em `tools/export_openapi.py:22`)
- Resultado: rc=0; `render()` byte-idêntico ao arquivo (SHA-256 `2a038eeaba5f…2d04b2`, igual ao manifesto); `openapi-spec-validator OK`.
- Limitações: CI não executa `--check` explicitamente, mas `tests/test_contracts_and_architecture.py:40` compara o YAML salvo com `app.openapi()`.

### E3-08 — Build do frontend
- Tipo: comando — `logs/npm_ci.log`, `logs/npm_build.log`, 2026-10-01T20:39:41Z, Node 22.22.0
- Resultado: `npm ci` "added 21 packages ... found 0 vulnerabilities"; `tsc -b && vite build` OK (`dist/assets/index-CgpmyOVc.js 240.52 kB`).
- Limitações: CI/Dockerfile usam Node 24; `test:browser` inexistente em `web/package.json`.

### E3-09 — Migrações SQLite
- Tipo: comando — `logs/migracoes_sqlite.log`, 2026-10-01T20:42:09Z (`$A/mig_exp.py`)
- Resultado: vazio→`0003_contract_closing`, 0 divergências; `downgrade base` remove todas as tabelas e novo upgrade OK; legado 0001 com cliente/contrato/idempotência → head preservou dados (`active=1`, `ends_on=None`, `request_hash=None`), unicidades `email` e `uq_contract_business_key` presentes e efetivas (`IntegrityError` na duplicata); legado sem `alembic_version` → OK; `alembic upgrade head --sql` rc=255 ("batch mode with dialect sqlite requires a live database connection").

### E3-10 — Migrações PostgreSQL
- Tipo: comando — `logs/migracoes_pg.log`, PG 16.14
- Resultado: casos 1–4 e 6 iguais ao SQLite (offline SQL rc=0, 238 linhas). Caso 5 (esquema em 0002 sem `alembic_version`): `FALHA na inicialização: ProgrammingError: (psycopg.errors.DuplicateColumn) column "active" of relation "crm_customers" already exists`.
- Limitações: o caso 5 é de borda (banco criado por `create_all` entre 0002 e 0003).

### E3-11 — Modo público: segredo e autenticação
- Tipo: comando + inspeção — `src/archcorp/main.py:352-353`, `src/archcorp/security.py:28-31`; logs `uvicorn_pg_tokencurto.log`, `uvicorn_pg_tokendemo.log`, `uvicorn_pg_public.log`
- Resultado: `DEMO_ACCESS_TOKEN=curto` e `demo-xxxx…` (≥24) → `RuntimeError: PUBLIC_DEMO exige DEMO_ACCESS_TOKEN aleatório com pelo menos 24 caracteres` (rc=3). Com token aleatório: `demo-admin` 401, sem token 401, token público 200, `/api/v1/demo/state` (só admin) 200. Comparação com `secrets.compare_digest`. Modo local: `credentials.credentials not in TOKEN_ROLES` (comparação de dicionário, tokens fixos e públicos no README).
- Observação: o token público recebe `TOKEN_ROLES["demo-admin"]` (todos os papéis). Sem verificação de entropia além de comprimento/prefixo; sem limitação de tentativas.

### E3-12 — Endpoints operacionais sem autenticação
- Tipo: comando — `logs/uvicorn_pg_public.log`, `logs/metrics_publico.txt`
- Resultado (PUBLIC_DEMO=true): `/metrics` 200, `/docs` 200, `/openapi.json` 200 sem token; `/api/v1/operations/*` e `/api/v1/integration/failures` exigem `operations`/`admin` (`main.py:530,584`) → 401 sem token. Após 300 GETs sem token a `/api/v1/operations/<uuid aleatório>`, `/metrics` passou a ter 612 linhas, 600 com o caminho bruto (`observability.py:37-39` usa `request.url.path` como rótulo).

### E3-13 — RLS/REVOKE em PostgreSQL com padrões do Supabase simulados
- Tipo: comando — PG `rlsdb`; `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES/SEQUENCES TO anon, authenticated` antes da inicialização
- Resultado: 16 tabelas do modelo com `relrowsecurity=t` e sem privilégios para `anon`/`authenticated` (`SET ROLE anon; SELECT ... crm_customers` → `permission denied`). **`alembic_version|f|f|t|t|t`** (sem RLS; anon SELECT/UPDATE; authenticated INSERT); `SET ROLE anon; UPDATE alembic_version ...` → `UPDATE 1`; sequências `integration_audit_id_seq`, `integration_inbox_id_seq`, `integration_legacy_ids_id_seq` com USAGE para anon. Causa: `db.py:25` itera somente `Base.metadata.sorted_tables`.
- Limitações: Supabase real não verificado; papéis e privilégios padrão simulados.

### E3-14 — Indisponibilidade causada por papel anon
- Tipo: comando — `logs/uvicorn_pg_after_anon_delete.log`
- Resultado: `SET ROLE anon; DELETE FROM alembic_version;` → `DELETE 1`; reinício → `DuplicateTable: relation ...` / `Application startup failed. Exiting.` Restaurado com `INSERT INTO alembic_version VALUES ('0003_contract_closing')` → inicia.

### E3-15 — Persistência após reinício (PostgreSQL local)
- Tipo: comando — `logs/uvicorn_pg_public_restart.log`
- Resultado: cliente sintético criado antes do reinício retornado por `GET /api/v1/crm/customers?email=...` depois do reinício (200). `GET /health/ready` → `{"status":"UP","database":"UP"}`.
- Limitações: local, HTTP, sem Render/Supabase; não satisfaz o critério de T20.

### E3-16 — Concorrência real em PostgreSQL (API)
- Tipo: comando — `logs/concorrencia_pg_1worker.log`, 2026-10-01T20:45:08Z, 15 rodadas, barreira de 2 threads
- Resultado literal:
  - `15x A_ativacao_chaves_diferentes codes=[200, 200] eventos=2`
  - `15x B_ativacao_mesma_chave codes=[200, 409] eventos=1`
  - `15x C_reserva_mesma_chave codes=[201, 409] reservas=1`
  - `15x D_reserva_sem_chave codes=[201, 201] reservas=2`
  - `15x E_despacho_paralelo codes=[200, 500]`
  - `contratos_ativos=30 faturas=30 faturas_duplicadas=0 processos_duplicados=0 inbox_duplicado=0`; `contratos_com_>1_ContractActivated=15`.
- Limitações: 1 processo uvicorn; não testado com `--workers`.

### E3-17 — Causa do 500 no despacho concorrente
- Tipo: comando + inspeção — `$A/conc_inproc.py`; `src/archcorp/integration/service.py:25-45`
- Resultado: `('exc', 'sqlalchemy.exc.PendingRollbackError', "This Session's transaction has been rolled back due to a previous exception during flush...")`. O `except Exception` incrementa `attempts` e chama `session.commit()` (linha 45) sem `session.rollback()`; não há `SELECT ... FOR UPDATE SKIP LOCKED` na leitura dos pendentes (linha 22).

### E3-18 — Evento "venenoso" bloqueia a outbox
- Tipo: comando — `logs/evento_venenoso_pg.log`
- Resultado: `despacho 1..5 → 500`; `[('ContractActivated.v1', 'PENDING', 0, ''), ('ContractActivated.v1', 'PENDING', 0, '')]`; `fatura do contrato legítimo: 0`; `falhas listadas: []`.
- Limitações: gatilho injetado diretamente na tabela (valor `1e20` em `billing.amount`).

### E3-19 — Valor monetário sem limite → 500 em PostgreSQL
- Tipo: comando + inspeção — `logs/uvicorn_pg_valid.log`; `src/archcorp/schemas.py:111` (`amount: Decimal = Field(gt=0, decimal_places=2)`), `contracts/routes.py:85`; colunas `Numeric(14,2)` (`0001_baseline.py`)
- Resultado: `draft amount=999999999999.99 -> 201`, `1000000000000000.00 -> 500`, `1e20 -> 500`, `reserva amount=1e16 -> 500`.

### E3-20 — Broker indisponível
- Tipo: comando — `logs/rabbit_porta_fechada.log`, `logs/rabbit_blackhole.log`
- Resultado: `despacho 1: processed 0, failed 1 ... evento=('PENDING', 1, '') faturas=1 processos=1` … `despacho 3: ('FAILED', 3, '')`; `falhas: [('ContractActivated.v1', 3, '')]`; reprocessamento → `failed 1` novamente. Causa: `_publish_broker` (`integration/service.py:32,49-64`) roda dentro do mesmo `try` dos consumidores; `str(exc)` do pika vazio → `last_error=''`.
- Limitações: 192.0.2.1 é recusado pela rede em 0,05 s. **Atualização (onda 2):** `$A/rabbit_timing.py` mediu 10,01 s/evento com 10.255.255.1 (`socket_timeout` padrão do pika) e 15,01 s/evento com TCP aceito sem handshake (`stack_timeout` padrão); ver `logs/rabbit_tempo_por_evento.log` e `revisao_cruzada.md`.

### E3-21 — Logs JSON descartam exceção
- Tipo: inspeção + comando — `src/archcorp/observability.py:15-25`; `logs/uvicorn_pg_conc.log`
- Resultado: `JsonFormatter.format` não inclui `record.exc_info`; 15 linhas `"level": "ERROR" ... "message": "Erro não tratado"` sem tipo nem stack (`Traceback` = 0 no log).

### E3-22 — PII em log de acesso
- Tipo: comando — `logs/uvicorn_pg_public_restart.log`
- Resultado: `"GET /api/v1/crm/customers?email=<email>@example.com HTTP/1.1" 200 OK` (log de acesso do uvicorn). Nenhum token ou `Bearer` em logs (grep = 0).

### E3-23 — Desempenho
- Tipo: comando + inspeção — `scripts/performance_smoke.py:5,13-25`; `logs/performance_smoke.log`, `logs/perf_flows.log`
- Resultado: p95 11,10/11,17/11,57 ms (3.11), 13,32 ms (3.12), 13,70 ms (PG) — PASS. Script mede apenas `GET /health/ready` via `TestClient` (sem rede); faz `drop_all/create_all` no banco configurado. Complementar F1/F2/F3 (100 iterações): SQLite 39,5/42,9/38,7 ms; PG 43,7/50,7/45,3 ms.
- Comparação: documento declara p95 6,36 ms (13/09, Windows, Py 3.12.14) e 5,74 ms (29/09). Valores atuais maiores (hardware diferente), mas dentro da meta de RNF-07.

### E3-24 — Jornada real no frontend (Playwright + axe)
- Tipo: comando — `logs/web_journey.log`, `shots/01_gate.png` … `shots/13_mobile.png`, 2026-10-01T20:50:31Z
- Resultado literal (trechos): `02 token errado -> aviso='Falha ao carregar: Token ausente ou inválido'`; `02b token inválido persistido em sessionStorage=True`; `03 token demo-support -> aviso='Falha ao carregar: Papel sem permissão para esta operação'; gate=True`; `06 e-mail duplicado -> aviso='Não foi possível concluir: E-mail já cadastrado no CRM'; campo nome preservado após erro=''`; `07 reserva (duplo clique no submit) -> reservas no banco=1`; `09 ativar (duplo clique) -> ... eventos ContractActivated=2`; `11 financeiro -> faturas do contrato no banco=1`; `12 workflow -> processos do contrato=1`; `13 chamado com descrição curta -> 'Não foi possível concluir: String should have at least 3 characters'`; `14 viewport 390px -> scrollWidth/innerWidth=[390, 390]`. Requisições: duas `POST .../activate` com chaves diferentes (`341d4391`, `4b076cd4`).
- axe-core 4.13.0: gate → `color-contrast (serious) nós=2`, `landmark-one-main`, `region`; painel 8 nós, CRM 14, financeiro 10, atendimento 9 nós `color-contrast`.
- Limitações: fontes Google bloqueadas pelo proxy (`ERR_CERT_AUTHORITY_INVALID`) — contraste avaliado com fonte de fallback; sem leitor de tela real.

### E3-25 — Frontend: chave de idempotência e reset do formulário
- Tipo: inspeção de código — `web/src/App.tsx:27,50,93-105`
- Resultado: `ActionForm` chama `void onSubmit(...)` e `e.currentTarget.reset()` imediatamente (linha 27); `'Idempotency-Key': crypto.randomUUID()` por requisição (linha 50); botões inline ("Gerar contrato", "Ativar", "Encerrar", "Resolver", "Concluir") e submits de formulário não usam `disabled={busy}` (apenas "Atualizar" e "Despachar eventos pendentes" da visão geral); `refresh` usa `Promise.all` sobre 9 coleções (linha 64) — qualquer 403 impede o painel.

### E3-26 — Cabeçalhos de segurança e CORS
- Tipo: comando — `logs/cabecalhos_cors.log`
- Resultado: respostas só com `server`, `content-type`, `x-correlation-id`; sem CSP, `X-Content-Type-Options`, `X-Frame-Options`, HSTS; sem `Access-Control-*` (nenhum `CORSMiddleware` — origem cruzada bloqueada por padrão). 405 com `content-type: application/json` (não problem+json). `style.css:1` importa Google Fonts.

### E3-27 — Vulnerabilidades de dependências
- Tipo: consulta externa — pip-audit 2.10.1 `-s pypi` (2026-10-01T20:52:39Z) e `https://pypi.org/pypi/<pkg>/<ver>/json` (2026-10-01T20:53Z); `npm audit` (20:53:04Z); OSV.dev bloqueado (403 no túnel).
- Resultado: starlette 0.47.3 (transitiva de fastapi 0.116.1): GHSA-7f5h-v6xp-fcq8/CVE-2025-62727 (Range em FileResponse, corrigido 0.49.1), GHSA-86qp-5c8j-p5mr/CVE-2026-48710 (Host, 1.0.1), GHSA-jp82-jpqv-5vv3/CVE-2026-54282 (path, 1.3.0), GHSA-82w8-qh3p-5jfq/CVE-2026-54283 (form limits, 1.3.1), GHSA-x746-7m8f-x49c/CVE-2026-48817 (HTTPEndpoint, 1.1.0), GHSA-wqp7-x3pw-xc5r/CVE-2026-48818 (StaticFiles Windows, 1.1.0). pytest 8.4.1: GHSA-6w46-j5rx-g56g/CVE-2025-71176 (dev). npm: 0.
- Medição de aplicabilidade (CVE-2025-62727): 8000 intervalos → 7,58 s; `/health/live` concorrente 0,56 s; `RuntimeError: Response content longer than Content-Length`.

### E3-28 — Reprodutibilidade de dependências e imagem
- Tipo: inspeção — `requirements.txt`, `requirements-dev.txt`, `web/package.json`, `web/package-lock.json`, `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `render.yaml`
- Resultado: dependências diretas Python pinadas (`==`), transitivas **não** pinadas (sem lock/hashes; ex. starlette, pydantic, anyio resolvidos no momento da instalação); npm com `package-lock.json` e `npm ci`. Dockerfile: `node:24-alpine` e `python:3.12-slim` por tag (sem digest), sem `USER` (executa como root), sem `HEALTHCHECK`; copia só `requirements.txt`, `src`, `web/dist` (`.env` não é copiado, embora ausente do `.dockerignore`). Compose: `archcorp/archcorp` e `guest/guest` (demonstração local, documentado no README). `render.yaml`: `PUBLIC_DEMO=true`, `DATABASE_URL` e `DEMO_ACCESS_TOKEN` com `sync: false`, `healthCheckPath: /health/ready`.

### E3-29 — CI
- Tipo: inspeção + consulta externa — `.github/workflows/verify.yml`; GitHub MCP `actions_list` (2026-10-01)
- Resultado: run 36660119780 (push main, `3a3d8bd`) conclusion `success`, passos incluem pytest, npm ci/build e `docker build` (13 s); run 36662056291 (PR #29) `success`. `actions/checkout@v7`, `setup-python@v7`, `setup-node@v7` executaram. CI **não** roda: PostgreSQL, RabbitMQ, `performance_smoke.py`, `export_openapi.py --check` explícito, testes de navegador/acessibilidade, auditoria de dependências, teste do contêiner em execução.

### E3-30 — Segredos no histórico
- Tipo: comando (somente leitura no repositório real) — `git log -p --all | grep -iE '(password|secret|token|apikey|api_key|passwd)\s*[:=]'` e padrões de chaves conhecidas (ghp_, github_pat_, AKIA, xox, BEGIN PRIVATE, JWT, sk-, ATATT)
- Resultado: nenhum segredo real; ocorrências = leituras de variáveis de ambiente (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) em arquivos de skills de `.claude/` e `POSTGRES_PASSWORD: archcorp` em `docker-compose.yml` (credencial de demonstração local). Padrões de chaves: 0. `.env` e `.envrc` no `.gitignore` (linhas 151-152).

### E3-31 — Evidência de hospedagem (T20)
- Tipo: inspeção documental + consulta externa — grep `onrender.com|supabase.co` no repositório (0 ocorrências); `docs/ESTADO_IMPLEMENTACAO.md` ("execução no Render/Supabase não foi verificada"); issue GitHub #23 "[T20][S12/Q6] Publicar app/API em Render Free com Supabase Free" — `open`, `status:planejado`, 0 comentários (consulta 2026-10-01).
- Resultado: nenhuma URL pública, HTTPS, health remoto ou persistência remota documentados.

### E3-32 — Retentativa sem backoff
- Tipo: inspeção de código — `integration/service.py:37-43`
- Resultado: `attempts += 1` a cada chamada manual de despacho; nenhum atraso exponencial, jitter ou agendamento; `retry_limit=3` (`config.py:9`). `AGENT.md` exige "atraso exponencial e jitter".
