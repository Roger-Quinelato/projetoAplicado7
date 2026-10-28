# Evidências — F-QUA (Testes, qualidade, operação e interface)

Auditoria de 18/10/2026. Referência `main` = `44b8325`. Cópia de execução `iso-qua` (SQLite dentro da cópia; porta 18103). Python do `venv-auditoria` 3.12.10; Node v24.21.0; npm 11.19.0.
Horários em UTC. A suíte começou em 2026-10-18T20:27Z; o restante foi executado em 2026-10-19 (relógio do sistema). Logs em `logs/`, scripts em `scripts/`, registro de comandos em `scripts/comandos_executados.txt`. Tokens locais de demonstração aparecem redigidos como `<TOKEN_...>`.

### E-QUA-01 — Origem do import da cópia isolada e integridade do venv
- Tipo: comando + inspeção de código
- Fonte/local: `logs/coverage_report_src.txt`; listagem de `venv-auditoria\Lib\site-packages` (sem `*.pth` e sem `archcorp` instalado), 2026-10-18 ~20:33Z
- Comando e ambiente: `PY -m coverage report -m --include="src/*"` a partir de ISO; Python 3.12.10
- Resultado observado: todos os arquivos aparecem como `src\archcorp\...`, relativos a ISO. O pacote foi importado da cópia isolada, não do worktree.
- Limitações: prova indireta (pelo caminho registrado na cobertura). Não houve `import archcorp` isolado.

### E-QUA-02 — Suíte completa, rodada 1 (com cobertura de ramos)
- Tipo: comando
- Fonte/local: `logs/pytest_rodada1_cobertura.log`; ISO; início 2026-10-18T20:27Z
- Comando e ambiente: `PY -m coverage run --branch -m pytest -q -p no:cacheprovider -rs -o pythonpath=src tests`
- Resultado observado: `213 passed, 10 skipped, 1 warning in 387.28s (0:06:27)`. A progressão de pontos (32%, 64%, 96%, 100%) fecha em 223 itens = 213 + 10. Aviso: `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead`.
- Limitações: o arquivo tem 1,6 KB porque é a saída `-q` (pontos mais resumo). Não é parcial: o resumo final está presente. O tempo inclui a instrumentação de cobertura.

### E-QUA-03 — Suíte completa, rodada 2 (repetição sem cobertura)
- Tipo: comando
- Fonte/local: `logs/pytest_rodada2.log`; ISO; executada depois da rodada 1
- Comando e ambiente: `PY -m pytest -q -p no:cacheprovider -rs --durations=25 -o pythonpath=src tests`
- Resultado observado: `213 passed, 10 skipped, 1 warning in 224.40s (0:03:44)`. Mesmas contagens da rodada 1. Maiores durações: `test_envelopes_publicados_validam_contra_asyncapi` 44,65 s (call) e 9,68 s (setup); `test_migracao_0004_preserva_faturas_antigas` 25,78 s.
- Limitações: duas rodadas, no mesmo SQLite. Não prova ausência de instabilidade; não cobre PostgreSQL. A diferença de tempo para a rodada 1 é atribuída à instrumentação do coverage (não medida isoladamente).

### E-QUA-04 — Motivos dos skips (local) e inferência para a CI
- Tipo: comando + log da CI
- Fonte/local: `logs/pytest_rodada2.log` (linhas SKIPPED); `gh run view 39063148796 --repo Roger-Quinelato/projetoAplicado7 --job 117485116770 --log` (run de 2026-10-17 19:37Z)
- Comando e ambiente: `gh run view ... --log | grep -E "SKIPPED|passed|warning"`
- Resultado observado (local, SQLite): `test_migration_convergence.py:39` ×3 e `:57` ×1: "TEST_DATABASE_URL PostgreSQL não configurada"; `test_postgresql_concurrency.py` (4 itens): "Exige PostgreSQL real"; `test_rabbitmq_real.py` (2 itens): "Exige RabbitMQ real (TEST_RABBITMQ_URL)". Total 10.
- Resultado observado (CI, job `postgresql`): `221 passed, 2 skipped, 1 warning in 43.83s`. O comando do workflow não usa `-rs`, então os 2 skips não aparecem no log.
- Limitações: a identificação dos 2 skips do job PostgreSQL como os testes de RabbitMQ é inferência aritmética (213 + 8 = 221; 10 − 8 = 2), declarada como premissa.

### E-QUA-05 — Cobertura de linhas e ramos de `src/`
- Tipo: comando
- Fonte/local: `logs/coverage_src.json`, `logs/resumo_cobertura.txt`, `logs/coverage_report_src.txt` (rodada 1)
- Comando e ambiente: `PY -m coverage json --include="src/*" -o logs/coverage_src.json`; `PY -I scripts/resumo_cobertura.py logs/coverage_src.json`
- Resultado observado: 2754 instruções, 2612 executadas (linhas 94,8%); 727 ramos, 633 executados (87,1%); combinada 93,2%. Por pacote (linhas / ramos): contracts 97,9% / 91,7%; crm 99,4% / 96,0%; finance 98,6% / 97,1%; integration 94,6% / 89,6%; support 98,7% / 96,0%; raiz de archcorp 95,4% / 88,2%; infrastructure 80,4% / 67,6%; workflow 81,9% / 60,0%. Abaixo de 80% de linhas: `workflow/routes.py` 67,4%; `migrations/versions/0001_baseline.py` 54,3%; `0003_contract_closing.py` 72,2%; `migrations/env.py` 79%.
- Limitações: cobertura mede execução, não qualidade de asserção. Medida só em SQLite: ramos exercitados apenas em PostgreSQL (ex.: `integration/service.py:33`, caminho skip-locked) não aparecem aqui.

### E-QUA-06 — Análise estática das funções de teste (sem executar)
- Tipo: inspeção de código (ferramenta própria, AST)
- Fonte/local: `scripts/analise_testes.py` sobre `ISO\tests`; `logs/analise_testes.txt`
- Comando e ambiente: `PY -I scripts/analise_testes.py ISO\tests`
- Resultado observado: 157 funções `test_*` no nível de módulo (parametrizações expandem para 223 itens). Sem asserção: 0. Somente status HTTP: 7 (matrizes de autorização: `test_contracts.py:136,144`; `test_extended_modules.py:72`; `test_finance.py:343,350`; `test_flows.py:100`; `test_security_hardening.py:26`). Tautológicas: 0. Asserção fraca: 0. Atribuição direta a `settings`: 2 funções (`test_extended_modules.py:74,79`; `test_flows.py:83,91`), ambas com `try/finally`. Concorrência com threads: 4, todas em `test_postgresql_concurrency.py` (só executam em PostgreSQL).
- Limitações: heurística AST. Helpers `assert_*` (ex.: `assert_problem`) contam como asserção; conferido à mão em `test_finance.py:321`. Não avalia se o conteúdo da asserção é suficiente.

### E-QUA-07 — Frontend: instalação, testes e build
- Tipo: comando
- Fonte/local: `logs/npm_ci.log`, `logs/npm_test.log`, `logs/npm_build.log`, `logs/npm_test_cobertura_frontend.txt`; ISO\web
- Comando e ambiente: `npm ci`; `npm test` (`node --test "tests/**/*.test.ts"`); `npm run build` (`tsc -b && vite build`); `node --experimental-test-coverage --test "tests/**/*.test.ts"`; Node 24.21.0
- Resultado observado: `npm ci` — `added 21 packages, and audited 22 packages in 29s`. `npm test` — 4 testes passaram, todos de `describeIssue`. Build — `✓ built in 5.04s` (JS 287,07 kB). Cobertura (Node): `api.ts` 60,56% de linhas e 62,50% de ramos; nenhum `.tsx` é carregado pelos testes.
- Limitações: `npm audit` não executado aqui (é da F-CFG). Sem navegador. Avisos `install-scripts` (postinstall do esbuild) registrados, não avaliados.

### E-QUA-08 — Contraste WCAG calculado a partir do CSS
- Tipo: comando (script próprio) + inspeção de código
- Fonte/local: `web/src/style.css` (tokens em `:root`, linhas 3-23; regras em 37, 65, 89, 108, 111, 124); `scripts/contraste_wcag.py` → `logs/contraste_wcag.md`
- Comando e ambiente: `PY -I scripts/contraste_wcag.py`
- Resultado observado: 46 pares avaliados; 5 abaixo do mínimo. Texto do rodapé (`footer`, `#66768a` sobre `#f4f7fb`, 11 px): 4,32:1 (mínimo 4,5:1). Bordas de campo (`--line-strong` `#cfdae6` sobre branco): 1,42:1 (mínimo 3:1). Borda do botão secundário: 1,42:1. Fundos de botão inline `#e9f6f1` (1,11:1) e `#f1f4f8` (1,10:1) sobre o cartão. Demais pares passam, inclusive texto principal `#182943` (13,60:1), texto de cartão `#41566e` (7,55:1) e eyebrow `#5f7290` (4,55:1, no limite).
- Limitações: razão pela fórmula WCAG 2.1 sobre as cores declaradas. Sem renderização, sem axe, sem fonte real (Google Fonts indisponível no ambiente). Premissa: fundos de botão com rótulo textual não são exigidos pelo 1.4.11.

### E-QUA-09 — Experimento do formatter JSON diante de exceções
- Tipo: comando
- Fonte/local: `src/archcorp/observability.py:15-27`; `src/archcorp/main.py:102-104`; `src/archcorp/integration/service.py:86-88, 105-106`; `scripts/experimento_formatter_excecao.py` → `logs/experimento_formatter_excecao.txt`
- Comando e ambiente: `PY -I scripts/experimento_formatter_excecao.py ISO\src`
- Resultado observado: caso A (`logger.exception` do middleware): `record.exc_info preenchido: True`; a saída tem `"level": "ERROR", "module": "archcorp", "operation": "/api/v1/sintetico", "result": "failure", "message": "Erro n..."`, e não tem `ValueError`, `Traceback` nem chave `exception`. Caso B (despacho, `errorType` explícito): a saída tem `"errorType": "RuntimeError"` e não tem pilha.
- Limitações: logger isolado com o formatter de produção. `correlationId` aparece como `unknown` porque o experimento não passa pelo middleware. A codificação do console alterou acentos no arquivo.

### E-QUA-10 — Cegueira do teste de RLS
- Tipo: comando + inspeção de código
- Fonte/local: `tests/test_public_database_security.py:8-27`; `src/archcorp/infrastructure/db.py:42-50` (laço em `:49`); `scripts/teste_cegueira_rls.py` → `logs/teste_cegueira_rls.txt`
- Comando e ambiente: `PY -I scripts/teste_cegueira_rls.py ISO\src`
- Resultado observado: 51 instruções emitidas (17 `ENABLE ROW LEVEL SECURITY` e 34 `REVOKE`). `alembic_version coberta por algum REVOKE: False`. `sequencias citadas em alguma instrucao: False`.
- Limitações: sem PostgreSQL e sem papéis `anon`/`authenticated` reais. A verificação real (`has_table_privilege`) não foi executada; é a E-06 da frente F-SEG.

### E-QUA-11 — Teste de contrato de eventos sem `FormatChecker`
- Tipo: comando
- Fonte/local: `tests/test_contracts_and_architecture.py:21-23` (validador), `:174-180` (exemplos), `:183-204` (envelopes; asserção só de `occurredAt.endswith("Z")` em `:201`); `docs/events/asyncapi.yaml` (ISO); `scripts/teste_cegueira_formato.py` → `logs/teste_cegueira_formato.txt`
- Comando e ambiente: `PY -I scripts/teste_cegueira_formato.py ISO`
- Resultado observado: `occurredAt = '2026-10-01T10:00:00'` — sem `format_checker` (como no teste): 0 erros; com `FormatChecker`: `is not a 'date-time'`. `occurredAt = 'nao-e-uma-data'` — 0 erros sem checker; 1 com checker.
- Limitações: testado com `ContractActivated.v1` e com `occurredAt`. A mesma construção vale para `dueAt` (não executado separadamente).

### E-QUA-12 — Lint com ruff (regras padrão)
- Tipo: comando
- Fonte/local: `logs/ruff_estatisticas.txt`, `logs/ruff_concise.txt`; ruff 0.6.9 em ISO
- Comando e ambiente: `PY -m ruff check src tests scripts tools --output-format concise`
- Resultado observado: "Found 12 errors. [*] 2 fixable with the --fix option." E402 ×10: `src\archcorp\schemas.py:30-34` (shim de reexportação) e `tests\conftest.py:8-13` (variável de ambiente antes do import, de propósito). F401 ×2: `tests\conftest.py:10` (`sqlalchemy.text`) e `tools\build_report.py:4` (`WD_SECTION`).
- Limitações: regras padrão. Não há configuração de ruff no repositório (premissa).

### E-QUA-13 — Tipos com mypy
- Tipo: comando
- Fonte/local: `logs/mypy_src.txt`; mypy 1.11.2; ISO
- Comando e ambiente: `PY -m mypy src --ignore-missing-imports` (levou mais de 120 s; concluído em segundo plano)
- Resultado observado: "Found 72 errors in 14 files (checked 55 source files)". Por código: arg-type 23, dict-item 17, list-item 14, return-value 8, union-attr 4, operator 2, index 2, method-assign 1, assignment 1. Triagem: `support/domain.py:93,114` são falsos positivos (`as_utc` é anotada `datetime | None`, e as chamadas passam datetime: `service.py:68`, `:225`, `:284`). Sinal real: `workflow/routes.py:138-147` (ver QUA-17). `errors.py:136-139` e `:176` são usos de tipos de handler e de atribuição de `app.openapi`.
- Limitações: sem `--strict`. Sinal, não achado por si; cada item foi triado por código.

### E-QUA-14 — Jobs da CI (`verify.yml`) e log do job `postgresql`
- Tipo: inspeção de código + log da CI
- Fonte/local: `.github/workflows/verify.yml:12-34` (postgresql), `:35-53` (rabbitmq), `:54-84` (application); `gh run view 39063148796 --repo Roger-Quinelato/projetoAplicado7 --job 117485116770 --log`
- Comando e ambiente: `gh` somente leitura
- Resultado observado (log): `221 passed, 2 skipped, 1 warning in 43.83s`; o aviso é o mesmo `StarletteDeprecationWarning` do local. Configuração: `postgresql` roda `tests` inteiro com `TEST_DATABASE_URL`; `rabbitmq` roda 2 arquivos (`test_rabbitmq_real.py` e `test_reliability_regressions.py`); `application` roda `tests` inteiro em SQLite, `pip_audit` em `requirements.txt`, `npm audit`, `npm test`, `npm run build` e `docker build`. Não há ruff, mypy, cobertura mínima, medição F1–F3, axe/Playwright nem e2e. O job PostgreSQL não usa `-rs`.
- Limitações: PostgreSQL e RabbitMQ não foram executados localmente; os números são evidência de terceiros (CI do próprio SHA).

### E-QUA-15 — Estado do PR #54 (e2e Playwright)
- Tipo: consulta externa (somente leitura)
- Fonte/local: `gh pr view 54 --repo Roger-Quinelato/projetoAplicado7 --json number,state,isDraft,title,headRefName,updatedAt` (consulta de 2026-10-19)
- Resultado observado: `{"headRefName":"feat/e2e-playwright","isDraft":true,"number":54,"state":"OPEN","title":"Roteiros Playwright da interface e perfil Playwright MCP","updatedAt":"2026-10-17T20:46:38Z"}`
- Limitações: somente metadados; o conteúdo do PR não foi lido.

### E-QUA-16 — E-14: latência de rotas de negócio por HTTP (SQLite, uvicorn na 18103)
- Tipo: comando
- Fonte/local: `logs/e14_carga_sintetica.txt`, `logs/e14_medicoes.txt`, `logs/uvicorn_e14.log`; uvicorn com `--app-dir ISO\src archcorp.main:app`, iniciado às 2026-10-19T08:08Z
- Comando e ambiente: `PY -I scripts/seed_sintetico.py --base-url http://127.0.0.1:18103 --token <TOKEN_ADMIN_LOCAL>`; `PY -I scripts/medir_rotas_e14.py http://127.0.0.1:18103 <TOKEN_ADMIN_LOCAL> 200`. Windows, i5-8250U, 8 processadores lógicos, cliente httpx no mesmo host.
- Resultado observado: N=200 por rota, nenhuma resposta não-2xx. Leituras, p95: customers 24,33 ms; reservas 10,16 ms; faturas 11,13 ms; tickets 11,72 ms; processos 10,95 ms. Escritas, p95: F1-A customers 28,39 ms; F1-B drafts 45,17 ms; F2-A activate 37,19 ms; F2-B dispatch 43,55 ms; F3-A tickets 40,14 ms; F3-B dispatch 45,10 ms. Fluxos (soma por iteração), p95: F1 81,34 ms; F2 81,01 ms; F3 86,63 ms. Referência `/health/ready`: p95 5,43 ms. Maior p95 de rota de negócio: 45,17 ms, abaixo de 500 ms.
- Limitações: SQLite; PostgreSQL não medido (não equivale). Os máximos por rota (E-QUA-17) não entram no p95 e são tratados à parte.

### E-QUA-17 — E-14: cauda de latência
- Tipo: comando
- Fonte/local: `logs/e14_medicoes.txt` (máximos por rota); `logs/e14_cauda_latencia.txt` (300 leituras e 300 criações sequenciais, mesmo servidor)
- Comando e ambiente: `PY -I scripts/cauda_latencia_e14.py http://127.0.0.1:18103 <TOKEN_ADMIN_LOCAL> 300`
- Resultado observado: máximos de 7,0 s a 21,8 s nas somas de fluxo em E-14. Experimento de cauda: `ESCRITA customers #265 19273 ms em t=16.1s`; `#264 1522 ms em t=14.6s`; `#189 319 ms`; `#197 343 ms`; `#266 350 ms em t=35.4s`; leituras `#0 839 ms` e `#167 315 ms`. Mediana 16,7 ms; p99 314,5 ms; 600 respostas 200/201.
- Limitações: causa não determinada. Hipóteses: espera por lock do SQLite e interferência do sistema de arquivos/antivírus no Windows. O servidor não grava duração por requisição, então o pico não pode ser relacionado a um evento interno.

### E-QUA-18 — Observabilidade do servidor de E-14: `/metrics` e log
- Tipo: comando
- Fonte/local: `logs/e14_metrics.txt`, `logs/uvicorn_e14.log`
- Comando e ambiente: `curl /metrics` sem token e com token de operações; contagem de `ERROR`, `Traceback` e `module` no log
- Resultado observado: sem token, 401. Com token: `archcorp_requests_total` (14 séries), `archcorp_request_latency_seconds_sum` (14 séries, somente soma), `archcorp_events_published_total`. Sem `archcorp_events_failed_total` (nenhuma falha ocorreu). Log: 0 linhas `ERROR`, 0 `Traceback`; `"module": "archcorp"` em 2412 linhas e `"module": "alembic.runtime.migration"` em 8 (migração na inicialização).
- Limitações: amostra sem falhas e sem broker. Não há métrica de retentativa no código (grep em `src`: o único registro é um log `"result": "retry"` em `contracts/adapters.py:52`).

### E-QUA-19 — Inspeção da interface (AUD-26 e AUD-27)
- Tipo: inspeção de código
- Fonte/local: `web/src/ui.tsx:64-67` (componente `Id`), `:77-97` (`useResource`), `:163-184` (`useIdempotencyKeys`), `:187-198` (`FeedbackBanner`), `:242-253` (`Field`), `:283-298` (`ActionForm`); `web/src/App.tsx:47-63` (`verify`), `:95` (link de pular), `:109-129` (`<main>`), `:128` (rodapé), `:142` (`<main>` da tela de acesso), `:155` (`role="alert"`); `web/src/api.ts:191-234` (`describeIssue`), `:311` (`createCustomer`); `web/src/contexts/*.tsx` (`disabled={busy}`, p.ex. `Contracts.tsx:117,139`); `web/src/style.css:3-23, 65, 89, 108, 137`
- Comando e ambiente: leitura direta; sem execução de navegador
- Resultado observado: chave de idempotência por intenção, reaproveitada só com corpo idêntico (`ui.tsx:163-184`); formulário limpo só após sucesso (`ui.tsx:292`); token persistido só após validação (`App.tsx:60`); erros de validação traduzidos (`api.ts:208-234`); cada recurso com estado próprio e falha isolada (`ui.tsx:77-97`); botões de comando com `disabled={busy}`; `aria-live`, `role="status"` e `role="alert"` nos avisos; `label` ligado a cada campo; link de pular conteúdo; `prefers-reduced-motion`. Pendências: cadastro de cliente sem chave (`api.ts:311`; `Crm.tsx:42`); rodapé dentro de `<main>` (`App.tsx:128`); `aria-label` em `<code>` (`ui.tsx:66`).
- Limitações: sem navegador. Duplo clique real, zoom de 200%, leitor de tela e axe não executados. Avaliação de código, não de renderização.

### E-QUA-20 — Testes de linha de base (AUD-36) lidos
- Tipo: inspeção de código
- Fonte/local: `tests/test_postgresql_concurrency.py` (4 testes, `:34`, `:55`, `:93`, `:123`); `tests/test_rabbitmq_real.py` (2); `tests/test_reliability_regressions.py` (13); `tests/test_f1_cliente_reserva_contrato.py:293-313` (RF-06); `tests/conftest.py:5`
- Comando e ambiente: leitura direta; `grep` por ativação concorrente e por valores grandes
- Resultado observado: PostgreSQL tem concorrência real com barreiras e threads, incluindo o despacho com `SKIP LOCKED` (`:93`). Não há teste de ativação concorrente em lugar nenhum (grep de `activate` nos arquivos de concorrência: nenhum). Não há teste com `amount` ≥ 10^12 em contratos. RF-06 é testado por HTTP (`/api/v1/operations/{correlation_id}`). `conftest.py:5` honra `TEST_DATABASE_URL`. `test_public_database_security.py` segue com conexão falsa.
- Limitações: leitura, não execução em PostgreSQL.

### E-QUA-21 — Ativação concorrente: API em SQLite e causa in-process
- Tipo: comando
- Fonte/local: `logs/ativacao_concorrente_sqlite.txt` (uvicorn na 18103, SQLite da cópia); `logs/ativacao_concorrente_causa.txt` (TestClient in-process sobre ISO\src); `logs/uvicorn_qua13.log` (15 linhas "Erro não tratado"); `src/archcorp/contracts/service.py:81-95` (leitura de `contract.status`, verificação e atribuição em `:95`)
- Comando e ambiente: `PY -I scripts/ativacao_concorrente_api.py http://127.0.0.1:18103 <TOKEN_ADMIN_LOCAL> 15`; `PY -I scripts/ativacao_concorrente_causa.py ISO\src 10`
- Resultado observado: API, 15 rodadas: `(200, 500) eventos=1: 15`; nenhuma rodada com mais de um evento. In-process, 10 rodadas: `codigos HTTP por rodada: {(200, 500): 10}`; `10x OperationalError: (sqlite3.OperationalError) database is locked [SQL: UPDATE contracts_contracts SET status=? ...]`.
- Limitações: SQLite (bloqueio de escrita). No PostgreSQL, o 01/10 registrou `[200,200]` e 2 `ContractActivated.v1` em 15/15 rodadas (`evidencias/agente3/logs/concorrencia_pg_1worker.log`, E3-16). Esse PostgreSQL não foi reexecutado. O script de API serve também a um servidor PostgreSQL dedicado, sem alteração.

### E-QUA-22 — Exceção do baseline v1 sem ADR
- Tipo: inspeção de código/documento
- Fonte/local: `tests/fixtures/api_v1_baseline.json:5670-5677` (`approved_security`, `_motivo`: "Correção de segurança (#40)…"); `docs/adr/*.md` (ADR-001 a ADR-006); `docs/adr/ADR-005-fronteiras-http-e-integracao-publica.md:37-40`
- Comando e ambiente: `grep -rln '/metrics' docs/adr` (0 resultados); `grep -c 'ADR' tests/fixtures/api_v1_baseline.json` (1, a chave `approved_ADR003`)
- Resultado observado: a exceção de segurança de `GET /metrics` tem apenas o motivo textual. ADR-005 cita apenas as duas exceções de ADR-003.
- Limitações: avalia só a rastreabilidade, não a decisão (regra do briefing).

### E-QUA-23 — Lacunas pontuais de teste (rotas e ramos)
- Tipo: comando (grep) + cobertura
- Fonte/local: `tests/*.py` (grep por `workflow/tasks`, `/health`, `.patch(`); `logs/coverage_report_src.txt`
- Comando e ambiente: `grep -n -E "workflow/tasks|/health|\.patch\(" *.py` em `ISO\tests`
- Resultado observado: nenhum `POST` ou `PATCH` em `/api/v1/workflow/tasks`; o único acesso é um GET em `test_extended_modules.py:66`. `/health/ready` não aparece em nenhum teste; `/health/live` só em `test_finance.py:396`. Linhas não executadas: `main.py:70` (guarda do token público), `:126-130` (ready com 503), `:163-175` (estáticos e SPA); `workflow/routes.py:101-104, 119-128, 134-149`; `0001_baseline.py:225-279` (downgrade); `0003_contract_closing.py:29-34` (downgrade).
- Limitações: grep textual; cobertura de SQLite.

### E-QUA-24 — Idempotência no cadastro de cliente
- Tipo: inspeção de código
- Fonte/local: `src/archcorp/crm/routes.py:128-143` (`POST /customers`, sem leitura de `Idempotency-Key`); `web/src/api.ts:311`; `web/src/contexts/Crm.tsx:42`; `tests/test_foundation.py:51-60` (repetição por e-mail → 409)
- Comando e ambiente: leitura direta e `grep -rn "Idempotency" src/archcorp/crm` (sem resultados)
- Resultado observado: a rota não recebe a chave; a UI não a envia; repetir o mesmo e-mail devolve 409 `CONFLICT`, sem devolver o `customerId` do cadastro original.
- Limitações: repetição com chave não foi executada (a rota não aceita a chave).

### E-QUA-25 — Metas declaradas de observabilidade e idempotência
- Tipo: inspeção de documento de critério (`AGENTS.md`, usado como critério de código, não avaliado em redação)
- Fonte/local: `AGENTS.md:3` (tracing distribuído, OIDC, fila de erro e escala horizontal são metas); seção "Observabilidade" (métricas mínimas; traces atravessando API, adaptadores e consumidores); seção "Confiabilidade" (Idempotency-Key em comandos repetíveis)
- Comando e ambiente: `grep -rn -i "opentelemetry\|tracing\|start_span\|traceparent" src` (0 resultados)
- Resultado observado: tracing está declarado como meta e não há instrumentação no código. A correlação existe por `X-Correlation-ID` e `correlationId` nos logs e em `/api/v1/operations/{id}`.
- Limitações: nenhuma avaliação de redação.

### E-QUA-26 — Redação e segredos nos registros desta frente
- Tipo: comando (grep)
- Fonte/local: `logs/*.txt` e `logs/*.log` da frente
- Comando e ambiente: `grep -o -E '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}'`; `grep -l 'demo-'`; `grep -c 'Bearer'`
- Resultado observado: nenhum e-mail encontrado (uvicorn_e14.log e saídas de E-14); nenhum `demo-` nos logs; nenhum `Bearer` nos logs nem em `e14_metrics.txt`. Os tokens de demonstração aparecem só em `scripts/comandos_executados.txt`, redigidos como `<TOKEN_...>`.
- Limitações: verificação por padrão textual. Os tokens locais são públicos (README e código); não foram tratados como segredos.

### E-QUA-27 — Itens não executados e motivo
- Tipo: registro
- Fonte/local: este pacote; `scripts/comandos_executados.txt`
- Resultado observado: não executados, com motivo: (a) suíte em PostgreSQL e job RabbitMQ localmente, sem PostgreSQL/RabbitMQ locais (evidência da CI, E-QUA-14); (b) E-14 em PostgreSQL, idem; (c) teste real de RLS com `anon`/`authenticated`, idem (E-06 da F-SEG); (d) ativação concorrente em PostgreSQL, idem (script pronto: `scripts/ativacao_concorrente_api.py`); (e) jornada de navegador, duplo clique real, axe, leitor de tela e zoom de 200%, por não haver navegador (instrução do usuário); (f) `npm audit`/`pip-audit` e análise de dependências, fora da F-QUA (F-CFG); (g) Docker, imagem e `docker build`, proibidos nesta auditoria.
- Limitações: não se aplica a este registro.
