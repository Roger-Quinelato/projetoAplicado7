# Evidências — F-SEG (Segurança e privacidade)

Referência: `main` = `44b8325`. Cópia de execução: `C:\Users\roger\.claude\jobs\f5019419\tmp\iso-seg` (porta 18101; SQLite dentro da cópia; Python `venv-auditoria`). Os horários são UTC da execução de 19/10/2026 (ou o registrado no próprio arquivo). Logs e saídas brutas estão em `logs/`; scripts em `scripts/`. Nenhum valor de credencial foi copiado para estes registros: onde há token ou segredo, aparece `<REDACTED>`.

Execução de referência: servidor `uvicorn archcorp.main:app` em `127.0.0.1:18101`, modo local e depois modo público (token aleatório gerado a cada subida, gravado só em `tmp/` da cópia). Ambos foram encerrados e a porta foi confirmada fechada.

---

### E-SEG-01 — Integridade da cópia isolada
- Tipo: comando
- Fonte/local: `evidencias/manifest_44b8325.sha256` (292 arquivos) contra `iso-seg`; execução em 2026-10-18T20:28:44Z
- Comando e ambiente: `tr -d '\r' < manifest | sha256sum -c --quiet` (Git Bash), na cópia
- Resultado observado: `MANIFEST_OK`
- Limitações: o manifesto não cobre `tmp/`, `web/node_modules` e `web/dist`, gerados pela frente. A cópia não foi alterada além disso.

### E-SEG-02 — Log da CI, job `postgresql` (id 117485116770)
- Tipo: log da CI
- Fonte/local: `logs/ci_job_postgresql_117485116770.log`, run `39063148796` (push de `44b8325`, 17/10/2026 19:35 UTC)
- Comando e ambiente: `gh run view --repo Roger-Quinelato/projetoAplicado7 --job 117485116770 --log`
- Resultado observado: `221 passed, 2 skipped, 1 warning in 43.83s`. Os dois skips são de `tests/test_rabbitmq_real.py` (linhas 36 e 47): `pytestmark = skipif(not RABBITMQ_URL)` (linha 14), e o job não define `TEST_RABBITMQ_URL` (`verify.yml`, linhas 25-26).
- Limitações: o job roda sem `-rs`, então os motivos dos skips vêm do código e da conta de skips (ver E-SEG-03).

### E-SEG-03 — Log da CI, job `application` (id 117485116908)
- Tipo: log da CI
- Fonte/local: `logs/ci_job_application_117485116908.log`
- Resultado observado: `213 passed, 10 skipped, 1 warning in 22.40s`; `No known vulnerabilities found` (pip-audit de `requirements.txt`); `found 0 vulnerabilities` (npm audit de `web/`). Os 10 skips são 4 de `test_postgresql_concurrency.py` (`skipif` de dialeto, linha 17), 4 de `test_migration_convergence.py` (sem `TEST_DATABASE_URL`, linhas 22-24) e 2 de `test_rabbitmq_real.py`. Essa soma (4+4+2) fecha com o total de 223 testes do job `postgresql`.
- Limitações: `docker build` do mesmo job não foi reproduzido (Docker proibido nesta frente).

### E-SEG-04 — Autenticação, papéis e guardas de inicialização (inspeção)
- Tipo: inspeção de código
- Fonte/local: `src/archcorp/security.py:11-18` (TOKEN_ROLES), `:27-35` (`current_principal`); `src/archcorp/config.py:21-22` (`public_demo`, `demo_access_token`); `src/archcorp/main.py:69-72` (guardas do lifespan)
- Resultado observado: no modo público, `compare_digest` (`security.py:30`) compara com `DEMO_ACCESS_TOKEN` e qualquer token válido recebe `TOKEN_ROLES["demo-admin"]` (`security.py:32`). No modo local, a comparação é `credentials.credentials not in TOKEN_ROLES` (`security.py:33`), isto é, pertinência em dicionário, não comparação em tempo constante. A guarda `main.py:69-70` exige ≥24 caracteres e rejeita prefixo `demo-`; não há teste de entropia. `config.py:21`: `public_demo: bool = False` (o padrão é o modo local com tokens fixos).
- Limitações: os tokens locais são públicos (README e código); a comparação não constante não tem o que proteger neles.

### E-SEG-05 — Frontend construído na cópia
- Tipo: comando
- Fonte/local: `logs/npm_ci_seg.log`, `logs/npm_build_seg.log`
- Comando e ambiente: `npm --prefix iso-seg/web ci --no-audit --no-fund`; `npm --prefix iso-seg/web run build` (Node v24.21.0, npm 11.19.0)
- Resultado observado: ambos com rc=0; `web/dist/assets/index-*.js` (287,07 kB) e `index-*.css` gerados (`built in 1.84s`). Aviso do npm sobre script de instalação do esbuild (não bloqueante).
- Limitações: nenhuma.

### E-SEG-06 — Inventário das 53 operações e estrutura de rotas
- Tipo: comando (diagnóstico somente leitura)
- Fonte/local: `scripts/seg_diagnostico_rotas.py`
- Resultado observado: no FastAPI 0.143.2, as rotas de `include_router` ficam dentro de objetos `_IncludedRouter`, com as rotas em `original_router.routes` e caminhos completos (ex.: `/api/v1/integration/outbox/dispatch`). Enumerando `app.routes` diretamente, a matriz encontraria 4 operações; com a correção, encontra 53 (`/health/live`, `/health/ready`, `/metrics`, `/api/v1/demo/state` no `main.py`, mais 49 dos seis routers). Os 53 batem com o briefing.
- Limitações: `_IncludedRouter` é detalhe de implementação do FastAPI 0.143; a matriz usa esse atributo e falha se houver dependência de inclusão (`include_context.dependencies`), o que não ocorre no projeto.

### E-SEG-07 — Matriz de autorização E-09, modo local
- Tipo: comando (TestClient; SQLite da cópia)
- Fonte/local: `scripts/seg_autorizacao_matriz.py local`; `logs/e09_matriz_local.tsv`, `logs/e09_matriz_local.json`, `logs/e09_matriz_local_stdout.log`
- Comando e ambiente: `python seg_autorizacao_matriz.py local`, `PUBLIC_DEMO` ausente, banco `tmp/matriz_local.db`
- Resultado observado: 53 operações; 51 com `require_roles`; 2 sem (`GET /health/live`, `GET /health/ready`, públicas por desenho). Para cada uma das 51: sem token → 401; papel errado → 403; papel certo → não 401/403; `demo-admin` → não 401/403. Divergências: 0. Respostas 5xx: 0. Conjuntos de papéis distintos: 13 (ex.: `GET /api/v1/crm/customers` aceita `admin, commercial, contracts, support`; `GET /api/v1/support/tickets` aceita `admin, operations, support`).
- Limitações: payloads `{}` e IDs inexistentes; as chamadas autorizadas param na validação ou em 404, sem gravação. Cobre autorização por papel; não cobre autorização por objeto (não existe no projeto).

### E-SEG-08 — Matriz E-09, modo público
- Tipo: comando (TestClient; SQLite da cópia)
- Fonte/local: `scripts/seg_autorizacao_matriz.py publico`; `logs/e09_matriz_publico.tsv`, `logs/e09_matriz_publico.json`
- Resultado observado: 53 operações; 51 protegidas; divergências 0; 5xx 0. Com `DEMO_ACCESS_TOKEN` aleatório: sem token → 401; `demo-support` e `demo-admin` (tokens locais) → 401; token público → não 401/403 em todas as 51. Ou seja, um único token dá todos os papéis.
- Limitações: o token é gerado em tempo de execução e não é gravado.

### E-SEG-09 — Cabeçalhos de segurança, CORS e OPTIONS (uvicorn local, porta 18101)
- Tipo: consulta HTTP (`scripts/seg_sondas_http.py local`; saída em `logs/sondas_local.json`)
- Resultado observado: em `/` e em `/health/live` estão ausentes `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`/`frame-ancestors`, `Referrer-Policy`, `Strict-Transport-Security` e `Permissions-Policy`. O cabeçalho `server: uvicorn` está presente. Preflight `OPTIONS /api/v1/crm/customers` com `Origin` externo → 405, sem `Access-Control-Allow-Origin`. `GET /health/live` com `Origin` externo → 200 sem `Access-Control-Allow-Origin` (o projeto não tem CORS; origem cruzada não consegue ler respostas, o que é o comportamento esperado para a demo).
- Limitações: HSTS é responsabilidade do edge (Render) e não foi verificado; não há como medir o edge localmente.

### E-SEG-10 — Range em arquivos estáticos (E-10; CVE-2025-62727 em AUD-25)
- Tipo: consulta HTTP
- Fonte/local: `logs/sondas_local.json` (campos `range_simples`, `range_multiplos`)
- Resultado observado: `Range: bytes=0-9` → 206 (`content-range: bytes 0-9/287067`). Múltiplos intervalos: 100 → 206 (1 byte no corpo, 1,04 s no total); 1000 → 200 com o arquivo inteiro (1,06 s; cabeçalho de 4.005 bytes); 3000 → 200 com o arquivo inteiro (0,78 s; cabeçalho de 12.005 bytes).
- Limitações: a medição de 7,58 s com 8.000 intervalos (01/10, starlette 0.47.3) não foi reproduzida porque o uvicorn/h11 limita o bloco de cabeçalhos (16 KB); 3.000 intervalos (12 KB) foi o máximo aceito. A versão atual (starlette 1.8.0) está acima da correção do advisory (0.49.1).

### E-SEG-11 — Travessia de caminho e fallback da SPA
- Tipo: consulta HTTP com bytes brutos (sem normalização do cliente)
- Fonte/local: `logs/sondas_local.json` (campo `travessia`)
- Resultado observado: `/assets/../../src/archcorp/config.py` → 404 (corpo de 22 bytes); `/assets/%2e%2e/%2e%2e/src/...` → 404; `/assets/..%2f..%2fsrc%2f...` → 404; `/../src/archcorp/config.py` → 200 com o `index.html` do fallback (484 bytes). Em nenhum caso o conteúdo de `config.py` apareceu.
- Limitações: nenhuma.

### E-SEG-12 — Formatos de erro (uvicorn local e TestClient)
- Tipo: consulta HTTP
- Fonte/local: `logs/sondas_local.json` (`erro_401`, `erro_403`, `erro_404_api`, `erro_400_correlacao`, `erro_405`)
- Resultado observado: 401, 403, 404 (rota `/api/v1/...` inexistente) e 400 (`X-Correlation-ID` que não é UUID) respondem `application/problem+json` com as chaves `type, title, status, detail, instance, code, correlationId`. **405 responde `application/json` com `{"detail": ...}`** (`erro_405`: `content-type: application/json`, chaves `['detail']`, `allow: GET`). Confirmado também no TestClient (`scripts/seg_checagens_inprocesso.py`, `405_metodo`).
- Limitações: o 404 de rota inexistente fora de `/api/` depende do fallback da SPA; sem `web/dist`, a resposta seria o 404 padrão do Starlette (não verificado).

### E-SEG-13 — Erros em processo: 409, 422 sem eco e 500 sem traceback
- Tipo: comando (TestClient; SQLite da cópia; `scripts/seg_checagens_inprocesso.py`)
- Fonte/local: `logs/checagens_inprocesso.json`
- Resultado observado: 409 (e-mail duplicado) → problem+json, sem traceback. 422 com marcador em `email` e `token` → problem+json, `errors` sem eco (`ecoa_entrada: false`). Sonda de erro não tratado (`RuntimeError` injetada só na memória do processo) → 500 `problem+json`, sem traceback, e a mensagem original não aparece na resposta (`mensagem_original_ecoada: false`).
- Limitações: a rota de sonda existe apenas no processo de teste; não foi gravada na cópia nem no repositório.

### E-SEG-14 — Limites de entrada (matriz em processo)
- Tipo: comando (TestClient; SQLite)
- Fonte/local: `logs/checagens_inprocesso.json` (campos `reserva_amount_*`, `draft_billing_amount_1e20`, `nome_*`, `email_invalido`, `paginacao_*`, `idempotency_key_101`, `chamado_*`, `pagamento_*`)
- Resultado observado: `amount=0` → 422. **`amount=1e20` → 201 em reserva (`reserva_amount_1e20`) e em rascunho (`draft_billing_amount_1e20`)**, porque `contracts/schemas.py:12` e `contracts/routes.py:90` declaram `Decimal` sem `max_digits` (no PostgreSQL, a mesma entrada gera 500, conforme AUD-35 em 01/10). Nome de 1 e de 151 caracteres → 422; 150 → 201. E-mail `x@` → 422. `limit=201` e `offset=-1` → 422. `Idempotency-Key` de 101 caracteres → 422. Descrição de 2.001 caracteres → 422. `serviceCode` de 5.000 caracteres em chamado → 422 sem campo `errors` (regra de negócio, pela elegibilidade; o schema `support/schemas.py:27` não tem limite de tamanho). Pagamento com `amount=1e15` → 422 (`max_digits=14`) e `0.001` → 422.
- Limitações: o efeito em PostgreSQL não foi reproduzido aqui (pertence à F-DAD, AUD-35).

### E-SEG-15 — Heurística de dados sensíveis (`_SENSITIVE_PATTERNS`)
- Tipo: comando + inspeção
- Fonte/local: `src/archcorp/support/domain.py:119-130`; `logs/checagens_inprocesso.json` (campo `heuristica_contains_sensitive_data`)
- Resultado observado: 12 casos; 11 corretos. Falha: `Ligar para (31) 99999-9999` → `False` (falso negativo: o padrão de telefone aceita espaços e traços, mas não parênteses). Verdadeiros: CPF com pontos, CPF sem separadores, CNPJ, cartão com espaços, DDI com espaços, placa Mercosul e antiga, e-mail. Falsos positivos: nenhum entre os casos legítimos.
- Uso: `grep` em `src/` e `tests/` mostra `contains_sensitive_data` apenas em `support/domain.py` e em `tests/test_t15_atendimento.py:190,195`. **Não há chamada no fluxo de abertura** (`support/service.py:54-83`, `support/routes.py` `open_ticket`).
- Limitações: a heurística é regex e não substitui minimização (a própria `archcorp-seguranca` §1 diz isso).

### E-SEG-16 — Chamado com dado sensível (uvicorn local)
- Tipo: consulta HTTP (`scripts/seg_sondas_http.py local`, bloco `chamado_dado_sensivel`)
- Resultado observado: criação de contrato e ativação → 200; `POST /api/v1/support/tickets` com descrição contendo CPF (`000.000.000-00`), cartão de teste (<REDACTED-PAN>), telefone (`+55 31 99999-9999`), placa (`ABC1D23`) e e-mail sintético → **201**. `GET /api/v1/support/tickets/{id}` com `demo-support` → 200, e `description` devolvida **igual** à enviada (`descricao_gravada_e_devolvida_igual: true`).
- Limitações: os valores são sintéticos ou de teste público; nenhum dado real foi usado.

### E-SEG-17 — Corpo grande e ordem entre corpo e autenticação
- Tipo: consulta HTTP + comando (TestClient)
- Fontes: `logs/sondas_local.json` (`corpo_20mb`); `scripts/seg_preautenticacao.py`, `logs/preautenticacao_resultado.json`
- Resultado observado: corpo JSON de 20 MB (`name` de 20 MB) com token admin → 422 em 1,16 s (`application/problem+json`); não há limite de tamanho na aplicação (nenhum middleware ou configuração em `main.py:80-86`, `Dockerfile:15`, `render.yaml`). **Sem token:** JSON inválido (`{`) → 422 `VALIDATION_ERROR`; JSON válido `{}` → 401; corpo não JSON sem token → 422. Ou seja, o corpo é lido e validado antes da dependência de autenticação, e um cliente anônimo recebe os nomes dos campos (`loc`) do schema.
- Limitações: o tempo de leitura do corpo sem token não foi medido separadamente; a conclusão de ordem vem do status de resposta.

### E-SEG-18 — Métricas: exposição e cardinalidade (AUD-24)
- Tipo: consulta HTTP
- Fonte/local: `logs/sondas_local.json` (`metrics_sem_token`, `metrics_cardinalidade`); `src/archcorp/main.py:133-137`; `src/archcorp/observability.py:44-52`
- Resultado observado: `GET /metrics` sem token → 401; com `demo-operations` → 200. Após 300 requisições a `/api/v1/crm/customers/{uuid}` com UUIDs distintos (todas 404), o número de séries `archcorp_requests_total{` passou de **15 para 15**.
- Limitações: nenhuma.

### E-SEG-19 — Logs do servidor local (E-11; demos F1–F3 e sondas)
- Tipo: log (`logs/uvicorn_local_18101.stdout.log` = acesso; `logs/uvicorn_local_18101.stderr.log` = aplicação em JSON)
- Comando: `scripts/demo_f1.py`, `demo_f2.py`, `demo_f3.py` da cópia contra `http://127.0.0.1:18101` (F1 repetido com `--timeout 120`, ver nota)
- Resultados dos demos: F1 **20/20**; F2 **14/14**; F3 **15/15**. Nota: a primeira execução do F1 deu `ReadTimeout` (10 s do cliente do demo) no passo 1 (criação de cliente), e a repetição com timeout de 120 s passou. Latência intermitente do ambiente Windows, sem diagnóstico conclusivo.
- Grep nos logs (só contagens): `demo-*` (tokens) = **0** (acesso e aplicação); `Bearer`/`Authorization` = **0**; `Traceback` = **0**; `Erro não tratado` = 0 (local); descrição sensível de chamado = **0**; e-mail codificado `%40` no log de acesso = **2** (`GET /api/v1/crm/customers?email=...`, AUD-47); chaves de query registradas: `contractId`, `customerId`, `email`, `serviceCode`.
- Limitações: o log de acesso do uvicorn é o que o Dockerfile produz (`Dockerfile:15`, sem `--no-access-log`).

### E-SEG-20 — Demos F1–F3 em modo público e token ausente dos logs
- Tipo: log e comando (token passado por variável de ambiente, sem gravação)
- Fonte/local: `logs/demo_f1_publico.log`, `logs/demo_f2_publico.log`, `logs/demo_f3_publico.log`; logs do servidor público
- Resultado observado: F1 **19/19**, F2 **13/13**, F3 **14/14** (sem checagem de 403, como o próprio demo prevê no modo público). Ocorrências do token público nos logs do servidor = **0**; nos logs dos demos = **0**. Erros não tratados no modo público = 1 (a sonda de cabeçalho não ASCII, E-SEG-21), sem traceback.
- Limitações: nenhuma.

### E-SEG-21 — Modo público: documentação, token único, força bruta e cabeçalho não ASCII
- Tipo: consulta HTTP (`logs/sondas_publico.json`; servidor em modo público)
- Resultado observado: `/docs`, `/redoc` e `/openapi.json` → 200 sem token. `/api/v1/demo/state`: sem token → 401; `demo-admin` (local) → 401; token público → 200. **Força bruta:** 300 tentativas com tokens aleatórios → 300×401, nenhum bloqueio, nenhum 429 (latência do cliente de 172 s; o servidor respondeu rápido em `curl`); token válido em seguida → 200. **Cabeçalho `Authorization` com bytes não ASCII** (`Bearer` + UTF-8 `ção`) → **500** `application/problem+json` (`urn:archcorp:problem:internal-error`, "Erro interno inesperado"), e o log registra "Erro não tratado" sem traceback. Com cabeçalho ASCII errado → 401. `/metrics` sem token → 401; com token público → 200.
- Limitações: a força bruta foi medida com 300 tentativas; o efeito de um volume maior não foi testado.

### E-SEG-22 — Relações do banco após migrações × laço de proteção (E-06, parte executada em SQLite)
- Tipo: comando (`scripts/seg_estrutura_banco_sqlite.py`; `logs/estrutura_sqlite_seg.log`)
- Resultado observado: 18 tabelas no banco após `upgrade_to_head`; `Base.metadata.sorted_tables` tem 17. **Relações fora do laço de `protect_public_demo_tables`: `['alembic_version']`.** O código percorre apenas `sorted_tables` (`src/archcorp/infrastructure/db.py:49`), e no lifespan a proteção roda depois da migração (`main.py:73-75`).
- Limitações: SQLite não tem papéis `anon`/`authenticated` nem sequências; o efeito de privilégio fica para E-SEG-23.

### E-SEG-23 — E-06 em PostgreSQL com papéis simulados (NÃO EXECUTADO)
- Tipo: script pronto (não executado)
- Fonte/local: `scripts/seg_e06_rls_postgres.py`; compilado com `compile()` sem execução (`sintaxe: OK`)
- Motivo de não execução: PostgreSQL local indisponível e Docker proibido nesta frente. O script exige um banco PostgreSQL descartável (`SEG_PG_URL`, com papel dono e `CREATEROLE`), cria `anon` e `authenticated`, define `ALTER DEFAULT PRIVILEGES` como o Supabase faz, sobe o lifespan com `PUBLIC_DEMO=true` e lista RLS e privilégios de todas as relações de `public` (tabelas e sequências), com testes negativos em `SET ROLE anon`.
- Limitações: o resultado depende de executar o script em PostgreSQL real; enquanto isso, AUD-23 segue com confiança média.

### E-SEG-24 — Teste de RLS existente (inspeção)
- Tipo: inspeção de código
- Fonte/local: `tests/test_public_database_security.py:8-27`
- Resultado observado: **dublê.** A `Connection` é uma classe falsa que devolve `["anon", "authenticated"]` (linhas 11-13); o `engine` é substituído por `SimpleNamespace(dialect=postgresql.dialect())` (linha 18). O teste só verifica se as strings `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` e `REVOKE ALL PRIVILEGES ON TABLE ... FROM anon` estão na lista de comandos, para `sorted_tables` (linhas 23-27).
- Limitações: o teste não conecta a PostgreSQL e não detectaria a lacuna de `alembic_version` (ele nem a enumera).

### E-SEG-25 — Dependências: pip-audit e npm audit
- Tipo: consulta externa (PyPI JSON e registro npm, via `pip-audit` e `npm audit`)
- Fontes: `logs/pip_audit_requirements_seg.log`, `logs/pip_audit_dev_seg.log`, `logs/npm_audit_seg.log`
- Comando e ambiente: `python -m pip_audit -r iso-seg/requirements.txt`; idem para `requirements-dev.txt`; `npm --prefix iso-seg/web audit --audit-level=moderate`
- Resultado observado: runtime (`requirements.txt`, com `fastapi==0.143.2` e `starlette==1.8.0` na linha 2) → **`No known vulnerabilities found`**, igual à CI de 17/10. Dev (`requirements-dev.txt`, linha 2: `pytest==8.4.1`) → **`Found 2 known vulnerabilities in 1 package`**: `pytest 8.4.1`, `PYSEC-2026-1845` (corrigido em 9.0.3). npm → **`found 0 vulnerabilities`**, igual à CI.
- Limitações: a consulta depende do índice público no momento da execução; `pip-audit` não audita o que está fora de `requirements*.txt`.

### E-SEG-26 — SAST: bandit em `src/`
- Tipo: comando
- Fonte/local: `logs/bandit_src_seg.json`; `logs/bandit_stderr_seg.log`
- Comando: `python -m bandit -r iso-seg/src -f json -o ... -q` (bandit 1.7.10, perfil padrão)
- Resultado observado: 56 arquivos, 4.366 linhas de código; **0 achados** (alta, média e baixa severidade), 0 erros, 0 `nosec`.
- Limitações: o perfil padrão do bandit não cobre regras de lógica de negócio nem de autorização; a análise de autorização está em E-SEG-07 e E-SEG-08.

### E-SEG-27 — Semgrep: NÃO EXECUTADO
- Tipo: registro
- Motivo: o coordenador proibiu instalar pacotes no `venv-auditoria` (compartilhado com as outras frentes), e não há ferramenta isolada autorizada para isso. O `semgrep` não está instalado (`Scripts/` do venv só tem `bandit`, `detect-secrets` e `pip-audit`).
- Limitações: nenhum SAST além do bandit foi executado nesta frente.

### E-SEG-28 — Segredos na árvore (detect-secrets)
- Tipo: comando (`scripts/seg_segredos_arvore.py`; saída bruta com hashes apagada após o processamento)
- Fonte/local: `logs/detect_secrets_arvore_redigido.json`; triagem em `logs/triagem_segredos_mascarado.txt`
- Comando: `detect-secrets scan --all-files --exclude-files` (cwd = cópia; exclusões de `node_modules`, `dist`, `__pycache__`, `.pytest_cache` e `tmp`)
- Resultado observado: 24 achados em 13 arquivos. Triagem por máscara (valores sempre `<REDACTED>`): **Basic Auth** em `.github/workflows/verify.yml:26,45`, `docker-compose.yml:5,6` e exemplos de `output/auditoria/2026-10-01T2035Z/...` (URLs de broker e de banco com credencial de demonstração ou sintética, `<REDACTED>`); **Secret Keyword** em `.github/workflows/verify.yml:19` (senha de serviço de CI, valor sintético, `<REDACTED>`), `docker-compose.yml:21` (senha de banco local, `<REDACTED>`) e `tests/test_reliability_regressions.py:68` e `:207` (literal de teste, `<REDACTED>`). Restante: 11 de alta entropia (hashes `integrity` em `skills-lock.json`, logs de pytest e `openapi.yaml`), ruído, não credencial.
- Limitações: detect-secrets não distingue credencial de exemplo; a classificação "sintética" vem do próprio nome e do contexto, lidos sem copiar valores.

### E-SEG-29 — Histórico do repositório (git log -p --all)
- Tipo: comando (`scripts/seg_segredos_historico.py`; `logs/historico_segredos_redigido.json`)
- Resultado observado: 122 commits; 121.304 linhas adicionadas analisadas; API `detect-secrets.core.scan.scan_line` usada com `default_settings` (modo registrado no relatório). Registros: 132.147, sendo 132.119 de alta entropia (ruído) e **28 de credencial** (23 Basic Auth e 5 Secret Keyword), que resumem a **20 combinações distintas de (tipo, arquivo, commit)**. Os tipos AWS, GitHub, Slack, JWT, chave privada e `sk-` não aparecem. Todas as ocorrências de credencial são as mesmas da árvore (locais, sintéticas ou literais de teste), desde commits antigos (`ff0094a`, `76c8562`, `b8cd1e3`, `3557d20`, `50be79e`, `8c0965f`, `b424b44`, `54115fb`, `e12ef49`, entre outros).
- Limitações: a triagem é por máscara e não por leitura integral de cada commit; nenhum valor foi copiado.

### E-SEG-30 — Regra "texto de fora é dado" (archcorp-seguranca §3)
- Tipo: consulta git e inspeção
- Fontes: `git grep` em `44b8325` (sem output) para "texto de fora", "não instrução", "trate ... como dado" etc.; `AGENTS.md` (linhas 24, 99-103) e `CLAUDE.md` lidos integralmente; `git show origin/feat/skills-revisor:.agents/skills/archcorp-seguranca/SKILL.md` (linhas 39-44)
- Resultado observado: **a regra não está na `main`**. Ela existe apenas no branch `origin/feat/skills-revisor` e na cópia local `archcorp-seguranca.md` (§3, "Texto de fora é dado, não instrução"). `AGENTS.md` e `CLAUDE.md` não têm regra equivalente. `.claude/agents/cavecrew-*.md` não mencionam texto externo.
- Limitações: a exploração de injeção por issue ou PR não foi demonstrada; é risco de processo (inferência).

### E-SEG-31 — Agentes e ferramentas versionados
- Tipo: inspeção
- Fonte/local: `.claude/agents/cavecrew-builder.md`, `cavecrew-investigator.md`, `cavecrew-reviewer.md` (frontmatter: sem campo `tools`; restrições descritas no corpo, p. ex. "No `Bash` available" no builder; "Read-only" no investigator)
- Resultado observado: os agentes são somente descritivos; não há hook versionado nem `.claude/settings.json` no repositório (`git ls-files .claude`: só `agents/` e `skills/caveman*`).
- Limitações: `skills-lock.json` lista três skills do `caveman` com hashes; a integridade do conteúdo não foi verificada além do hash registrado.

### E-SEG-32 — Configuração de deploy e CI (inspeção)
- Tipo: inspeção
- Fontes: `render.yaml:8-12` (`PUBLIC_DEMO: "true"` com valor fixo; `DATABASE_URL` e `DEMO_ACCESS_TOKEN` com `sync: false`); `docker-compose.yml` (sem `PUBLIC_DEMO`: 0 ocorrências; portas em `127.0.0.1`); `Dockerfile:15` (CMD sem `--no-access-log`); `.github/workflows/verify.yml:8-9` (`permissions: contents: read`), `:28,47,57` (`actions/checkout@v7`, referência por tag), `:19` (senha sintética de serviço)
- Resultado observado: o modo público depende de um valor fixo no `render.yaml`; o padrão do código é o modo local com tokens fixos. O CI tem permissões mínimas e não tem varredura de segredos nem SAST (F-CFG cobre essa parte).
- Limitações: configurações do provedor (variáveis definidas no painel do Render) não foram vistas.

### E-SEG-33 — Frontend: sinks, armazenamento do token e fonte externa
- Tipo: grep e inspeção (`web/src`)
- Resultado observado: nenhuma ocorrência de `innerHTML`, `dangerouslySetInnerHTML`, `eval(`, `new Function`, `document.write` ou `window.open`. Único `href` externo: `App.tsx:117` (`/docs`, `rel="noreferrer"`). Token guardado em `sessionStorage` (`App.tsx:31` leitura, `:34` gravação) e lido de volta a cada carga. Pré-preenchimento de `demo-admin` só em `import.meta.env.DEV` (`App.tsx:135`). A tela de acesso pede a credencial ao responsável (`App.tsx:146`), o que confirma a distribuição do token a visitantes. `web/src/style.css:1` carrega `@import url('https://fonts.googleapis.com/...')`.
- Limitações: a análise é estática; não há navegador nesta frente (contraste e leitores de tela são de F-QUA).

### E-SEG-34 — Aceite formal do token público
- Tipo: consulta
- Fonte/local: `grep -i "PUBLIC_DEMO|demo pública|DEMO_ACCESS_TOKEN|token público" docs/adr/`
- Resultado observado: nenhum ADR menciona o modo público ou o token público. O risco aceito de P-15 (01/10) ainda não foi registrado em ADR.
- Limitações: a documentação não foi avaliada pelo conteúdo (fora de escopo); o achado é só a ausência de decisão formal.

### E-SEG-35 — Testes de segurança existentes na cópia
- Tipo: comando
- Fonte/local: `logs/pytest_seguranca_seg.log` (e `.err.log`)
- Comando: `python -m pytest -q -p no:cacheprovider -rs tests/test_security_hardening.py tests/test_public_database_security.py tests/test_t15_atendimento.py` (cwd = cópia; `PYTHONPATH=src`)
- Resultado observado: **52 passed, 1 warning** em 38,25 s (SQLite). Cobrem: métricas com cardinalidade limitada e 401/403 em `/metrics`; 422 sem eco; escape de rótulo; SQL de RLS (dublê); regras de chamado, prazo e detecção heurística de dado sensível (só a função, não a API).
- Limitações: nenhum teste exercita o fluxo de abertura de chamado com dado sensível pela API (ver E-SEG-16), nem limite de corpo, nem cabeçalhos HTTP, nem 405 em `problem+json`.

### E-SEG-36 — Listagens: limites no código
- Tipo: inspeção de código
- Fontes: `src/archcorp/crm/service.py:127-129` (`ContactService.list`, `.limit(MAX_PAGE_SIZE)`, `MAX_PAGE_SIZE = 200` em `:14`); `src/archcorp/crm/service.py:175-177` (`OpportunityService.list`, mesmo limite); `src/archcorp/finance/service.py:209-213` (`list_invoices`, `.limit(200)`); `src/archcorp/crm/service.py:66-79` (`CustomerService.list`, `min(limit, MAX_PAGE_SIZE)` e `offset`); **`src/archcorp/integration/routes.py:42-44` (`list_failures`: `session.scalars(select(OutboxEvent).where(OutboxEvent.status == "FAILED")).all()`, sem limite)**
- Resultado observado: todas as listas têm teto de 200, exceto `GET /api/v1/integration/failures`. Contatos e oportunidades não têm `offset`, mas têm teto.
- Limitações: não medido com volume; a lista de falhas cresce com o número de eventos que atingiram o limite de tentativas.

### E-SEG-37 — Autorização por papel versus contexto de dados (inspeção + matriz)
- Tipo: inspeção + E-SEG-07
- Fontes: `src/archcorp/crm/routes.py:22` (`CUSTOMER_READERS = require_roles("commercial", "contracts", "support", "admin")`), `:145-157` (`list_customers` retorna `email`, `eligible`, `consentService` e `legacyId` de todos os clientes, até 200 por página com `offset`); `src/archcorp/support/routes.py:24` (`TICKET_READERS` com `operations`, que lê a descrição dos chamados em `support/routes.py:140-142`)
- Resultado observado: o papel `support` lê cadastro completo de clientes (incluindo e-mail) e o papel `operations` lê descrições de chamados, sem vínculo ao chamado ou ao contrato. A matriz confirma `GET /api/v1/crm/customers` → 200 para `demo-commercial` e 403 para `demo-finance`.
- Limitações: o projeto não tem autorização por objeto (não está no contrato); é uma decisão de desenho a registrar em ADR.

---

### Não executado e por quê (resumo)
- E-SEG-23 (E-06 em PostgreSQL): sem PostgreSQL local e sem Docker. Script pronto e compilado.
- E-SEG-27 (Semgrep): instalação vetada no `venv-auditoria` compartilhado.
- HSTS e TLS no edge do Render, e as configurações do painel do provedor: não verificáveis localmente.
- Imagem Docker e `docker build`: proibidos nesta frente (F-CFG estático; CI de 17/10 como declaração de evidência).
- Supabase real: não verificado; os papéis `anon` e `authenticated` foram simulados no script de E-SEG-23.
