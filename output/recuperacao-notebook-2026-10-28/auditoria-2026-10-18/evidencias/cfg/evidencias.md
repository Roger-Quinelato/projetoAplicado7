# F-CFG · Evidências (configuração, ambiente, cadeia de suprimentos e agentes)

Referência: `main` = `44b83254b43bfcc043766d69b9fb6b8970330cbf`. Execução na cópia `iso-cfg` (porta 18104, SQLite dentro da cópia, Python 3.12.10 do `venv-auditoria`). Sem Docker, sem PostgreSQL e sem RabbitMQ locais. Os horários são UTC e os de execução são aproximados quando marcados com "aprox.". Logs brutos em `logs/`; scripts em `scripts/`.

---

### E-CFG-01 — Integridade da cópia isolada contra o manifesto
- Tipo: comando
- Fonte/local: `scripts/verificar_iso.py`; `logs/verificar_iso.txt`; manifesto `evidencias/manifest_44b8325.sha256`; 2026-10-19 ~11:00 UTC
- Comando e ambiente: `PY -I verificar_iso.py <ISO> <manifesto>`
- Resultado observado: manifesto com 292 arquivos; ausentes 0; divergentes 0. Nove "extras" são arquivos de `.claude/`, que o manifesto exclui por desenho.
- Limitações: o manifesto cobre o código congelado, não a pasta `.claude/` nem `output/`.

### E-CFG-02 — Ambiente de execução
- Tipo: comando
- Fonte/local: `logs/ambiente.txt`, `logs/fuso_host.txt`; 2026-10-19 11:30:46 UTC
- Comando e ambiente: `python -I -c "import sys; print(sys.version)"`, `node -v`, `npm -v`, `git --version`
- Resultado observado: Python 3.12.10 (venv-auditoria); Node v24.21.0; npm 11.19.0; git 2.55.0. Fuso do host: horário de Brasília (`timezone` = 10800 s); `localtime` 08:08 e `gmtime` 11:08 no mesmo instante.
- Limitações: a versão local de Node é a mesma da CI e do Dockerfile (24), mas a execução foi só neste Windows.

### E-CFG-03 — Governança de refs (coleta anterior, reaproveitada)
- Tipo: comando (git, somente leitura)
- Fonte/local: `scripts/refs_governanca.py`; `logs/refs_governanca.txt`; `logs/gh_pr_list.json`; coleta de 18/10/2026 ~20:30 UTC (execução anterior, reaproveitada conforme instrução do coordenador)
- Comando e ambiente: `PY -I refs_governanca.py <WT> <gh_pr_list.json>`
- Resultado observado: 30 branches remotas com commits fora da `main` por ancestralidade (`origin/main..ref` > 0 e `ref` não ancestral). A ancestralidade superestima o conteúdo não integrado, porque há squash-merge. Branches locais sem nenhuma remota contendo o SHA: `feat/fluxo-coordenado` (20 commits). Worktrees: 8, uma delas travada por sessão.
- Limitações: `git cherry` é limite superior. A coleta foi feita antes de 19/10; o estado remoto pode ter mudado (conferido em E-CFG-24 para as refs citadas).

### E-CFG-04 — Verificações de S-01, S-02 e S-03
- Tipo: comando (git, somente leitura)
- Fonte/local: `scripts/verificar_s01_s02.py`; `logs/s01_s02_verificacoes.txt`; 2026-10-19 ~11:25 UTC (aprox.)
- Comando e ambiente: `PY -I verificar_s01_s02.py <WT> <LOGS>`, com `git -C <WT>`
- Resultado observado:
  - S-01: `merge-base --is-ancestor` de 4a557da, 6ad9733, 893e98f, c79cfa1 e 45694c7 contra `origin/main` retorna exit 1 para os cinco (PRs #45–#49 não chegaram à `main`).
  - `origin/main` tem apenas `docs/agentes/LEVANTAMENTO_SKILLS.md` e `.claude/skills/caveman*` e `cavecrew`. `origin/feat/skills-revisor` tem 10 `SKILL.md` `archcorp-*` em `.agents/skills`, 4 em `.claude/skills`, `tools/perfil_skills.py`, `docs/agentes/IMPLEMENTADOR.md` e `REVISOR.md`.
  - `origin/feat/perfil-mcp:.github/workflows/verify.yml` contém `perfil_skills.py --check`; a `main` não contém.
  - S-02: `git check-ignore --no-index .claude/worktrees/x/y.txt` retorna exit 1 (não ignorado). `.claude/settings.local.json` é ignorado apenas pela configuração global do usuário.
  - S-03: `git ls-files *.pdf` retorna só `Guia.pdf`. `AGENTS.md:39` cita "Projeto Aplicado – Localiza_ Arquitetura de Sistemas Corporativos.pdf", que não está versionado.
- Limitações: a verificação de S-03 é de existência de arquivo; o conteúdo do enunciado não está no repositório e não foi avaliado.

### E-CFG-05 — Experimentos de configuração: importação e valores de faixa (A01–A11)
- Tipo: comando (execução da aplicação, SQLite na cópia)
- Fonte/local: `scripts/exp_config.py`; `logs/exp_config.txt` e `logs/exp_config.json`; `src/archcorp/config.py`; 2026-10-19 ~11:03–11:07 UTC
- Comando e ambiente: `PY -I exp_config.py <ISO> <LOGS>`; cada caso em subprocesso `python -I`, cwd na cópia; banco SQLite em `ISO\tmp\exp_config`
- Resultado observado:
  - A01/A02: `RETRY_LIMIT=0` e `-1` aceitos (`retry_limit` 0 e -1).
  - A03: `RETRY_LIMIT=abc` recusado com `ValidationError` (tipo validado).
  - A04: `CRM_READER_MAX_ATTEMPTS=0` recusado na importação com `ValueError: max_attempts deve ser pelo menos 1`.
  - A05: `CRM_READER_TIMEOUT_SECONDS=-1` aceito; 1 chamada ao CRM, nenhuma espera, erro `prazo de -1s esgotado`. Controle A06 (padrão): 3 chamadas, 2 esperas.
  - A07: `CRM_READER_BASE_DELAY_SECONDS=-1` aceito; na execução sobe `ValueError: sleep length must be non-negative`, que não é `CustomerReaderUnavailableError`.
  - A08/A09: `DATABASE_URL` sem esquema ou vazia recusada na importação (`ArgumentError`).
  - A10: `DATABASE_URL` PostgreSQL inacessível recusada na inicialização (`OperationalError`, tempo limite de conexão).
  - A11: diretório SQLite inexistente recusado na inicialização (`OperationalError`).
- Limitações: PostgreSQL inacessível foi simulado por porta fechada; a conexão real não foi testada.

### E-CFG-06 — Guardas de inicialização do modo público e padrões (B01–B09)
- Tipo: comando (execução da aplicação com `TestClient`, que executa o lifespan)
- Fonte/local: `scripts/exp_config.py`; `logs/exp_config.txt`; `src/archcorp/main.py:69-75`; `src/archcorp/infrastructure/db.py:42-44`; 2026-10-19 ~11:03–11:07 UTC
- Comando e ambiente: mesmo script de E-CFG-05; tokens sintéticos (valores não registrados, só comprimento)
- Resultado observado:
  - B01 (sem token), B02 (10 caracteres), B03 (prefixo `demo-`), B06 (`FINANCE_ALLOW_FUTURE_AS_OF` com `PUBLIC_DEMO`): recusados na inicialização com `RuntimeError`.
  - B04 (prefixo `Demo-` com maiúscula, 35 caracteres): aceito. O token funciona (`/api/v1/demo/state` retorna 200) e `demo-admin` retorna 401.
  - B05 (24 caracteres repetidos): aceito.
  - B07 (modo público, token válido, SQLite): inicia; o espião de `protect_public_demo_tables` registra 0 chamadas ao banco (dialeto `sqlite`).
  - B08 (modo local com `FINANCE_ALLOW_FUTURE_AS_OF`): inicia.
  - B09 (padrões, sem variáveis de demo): inicia; sem credencial retorna 401; `demo-admin` retorna 200.
- Limitações: a proteção RLS em PostgreSQL não foi testada aqui (sem PostgreSQL local). A verificação da RLS é de F-SEG.

### E-CFG-07 — Execução com valores em tempo de execução (C01–C11)
- Tipo: comando (execução de `EventDispatcher` e do leitor, sem broker real)
- Fonte/local: `scripts/exp_config.py`; `logs/exp_config.txt`; `src/archcorp/integration/service.py:91-145`; `src/archcorp/contracts/adapters.py:37-60`; 2026-10-19 ~11:03–11:07 UTC
- Comando e ambiente: mesmo script; broker apontado para `127.0.0.1:1` (porta fechada, ninguém escuta)
- Resultado observado:
  - C01 (timeouts padrão): `AMQPConnectionError` com mensagem vazia, em 2,14 s.
  - C02 (`RABBITMQ_SOCKET_TIMEOUT_SECONDS=-1`): `ValueError: socket_timeout must be > 0`, em 0,09 s.
  - C03 (`RABBITMQ_BLOCKED_TIMEOUT_SECONDS=-1`): `ValueError: blocked_connection_timeout must be >= 0`.
  - C04 (`RABBITMQ_HEARTBEAT_SECONDS=-1`): `ValueError: heartbeat must >= 0`.
  - C05/C06 (`RETRY_LIMIT=0` e `-1`): após a primeira falha o status é `FAILED`.
  - C07 (padrão): após a primeira e a segunda falhas, `PENDING` (3 tentativas).
  - C08: `settings.retry_limit = 'abc'` aceito; no uso, `TypeError: '>=' not supported between instances of 'int' and 'str'`.
  - C09/C10/C11: `.env` com `RETRY_LIMIT=7` é lido só quando o cwd contém o `.env` (7); variável de ambiente sobrepõe o `.env` (9); a partir do cwd da cópia, sem `.env`, vale o padrão (3).
- Limitações: `RABBITMQ_QUEUE_MAX_LENGTH=-1` não foi exercitado, porque exige broker real; efeito previsto por inspeção (`queue_declare` com argumento negativo), confiança baixa.

### E-CFG-08 — Servidor real uvicorn na porta 18104
- Tipo: comando (servidor iniciado e encerrado pela própria frente)
- Fonte/local: `scripts/exp_uvicorn.py`; `logs/uvicorn_18104.json`; `logs/uvicorn_18104_*.txt`; 2026-10-19 ~11:09 UTC (aprox.)
- Comando e ambiente: `PY -I exp_uvicorn.py <ISO> <LOGS>`; `python -I -m uvicorn archcorp.main:app --app-dir <ISO>\src --host 127.0.0.1 --port 18104`; cada cenário é encerrado com `terminate()` antes do próximo; porta liberada ao fim (`porta_liberada`: true nos três).
- Resultado observado:
  - `dev_padrao`: sobe em 19,8 s; `/health/live` 200; `/health/ready` 200; `/api/v1/demo/state` sem credencial 401 e com `demo-admin` 200; `/metrics` com `demo-admin` 200; `/openapi.json` 200; `/docs` 200.
  - `publico_token_curto`: não sobe; log `RuntimeError: PUBLIC_DEMO exige DEMO_ACCESS_TOKEN ...` seguido de `Application startup failed. Exiting.`; código 3.
  - `publico_token_valido` (SQLite): sobe em 8,6 s; `/health/live` e `/health/ready` 200; sem credencial 401; token configurado 200; `demo-admin` 401; `/openapi.json` 200 sem credencial.
- Limitações: código de saída 1 nos cenários que subiram vem do `terminate()` no Windows e não indica erro de aplicação (os logs não mostram traceback). Não foi testado PostgreSQL.

### E-CFG-09 — Fuso do host e rótulo "Z" nos logs
- Tipo: comando e inspeção de código
- Fonte/local: `logs/fuso_host.txt`; `src/archcorp/observability.py:16-19`; saídas de `logs/exp_config.txt` (stderr com timestamps); 2026-10-19
- Comando e ambiente: `python -I -c "import time; ..."` (tzname, timezone, localtime, gmtime)
- Resultado observado: `localtime` 2026-10-19T08:08:19 e `gmtime` 2026-10-19T11:08:19 no mesmo instante. O formatador grava `...%SZ` com `formatTime`, que usa `time.localtime` por padrão. As linhas de log de E-CFG-05 trazem `2026-10-19T08:03:01Z`, horário local, quando a hora UTC era 11:03.
- Limitações: confirmado neste host (UTC-3). Em host em UTC (ex.: Render) o rótulo fica correto.

### E-CFG-10 — Dockerfile (análise estática) e o que não foi verificado
- Tipo: inspeção de código (parse por script)
- Fonte/local: `Dockerfile:1-15`; `logs/analise_estatica.txt` (seção Dockerfile)
- Comando e ambiente: `PY -I analise_estatica.py <WT> <ISO>`; sem Docker
- Resultado observado: `FROM node:24-alpine` (linha 1) e `FROM python:3.12-slim` (linha 8), ambos sem digest; `USER` ausente; `HEALTHCHECK` ausente; `EXPOSE` ausente; `pip install --no-cache-dir -r requirements.txt` (linha 11) sem `--require-hashes`; `CMD ["sh", "-c", "uvicorn ... ${PORT:-8000}"]` (linha 15) em forma de shell. `COPY web/ ./` (linha 5, estágio frontend) copia o diretório inteiro. Imports `import.meta.env` no `web/`: só `DEV` (`web/src/App.tsx:135`); nenhuma variável `VITE_*` é embutida. Log da CI (job application) mostra o build da imagem `archcorp-demo` concluído (digests resolvidos pelo BuildKit, não fixados no arquivo).
- Não verificado (sem Docker, decisão do usuário): PID 1 e propagação de sinais pelo `sh -c` (confiança baixa); usuário efetivo do contêiner em execução; tamanho e camadas da imagem; `docker build` local. A evidência de que a imagem constrói vem só da CI (run 39063148796, job application).
- Limitações: a declaração do usuário de que a stack Docker funcionou em 17/10 é declaração, não evidência.

### E-CFG-11 — docker-compose.yml (análise estática)
- Tipo: inspeção de código (parse YAML por script)
- Fonte/local: `docker-compose.yml:1-40`; `logs/analise_estatica.txt` (seção docker-compose)
- Comando e ambiente: `yaml.safe_load` no script de E-CFG-10
- Resultado observado:
  - api: chaves `build`, `depends_on`, `environment`, `ports`. Sem `restart`, sem `healthcheck`, sem limites de recurso. Porta `127.0.0.1:8000:8000`. `depends_on` com `service_healthy` em postgres e rabbitmq. `DATABASE_URL` e `RABBITMQ_URL` com credencial embutida (valores não registrados).
  - postgres: `healthcheck` (pg_isready), sem `restart`, porta `127.0.0.1:5432`, senha igual ao nome de usuário (valor não registrado).
  - rabbitmq: `healthcheck`, sem `restart`, porta `127.0.0.1:15672` (painel). A porta AMQP 5672 não é publicada. Não define `RABBITMQ_DEFAULT_USER`/`PASS`, então usa o usuário padrão.
  - volume nomeado `archcorp-data`.
- Limitações: a validação de sintaxe com `docker compose config` não foi feita (sem Docker).

### E-CFG-12 — Consulta externa: usuário guest do RabbitMQ
- Tipo: consulta externa
- Fonte/local: https://www.rabbitmq.com/docs/access-control (documentação oficial); consulta feita em 19/10/2026, entre 11:20 e 11:30 UTC (horário de sessão, aproximado)
- Comando e ambiente: WebFetch com pedido de citação literal sobre o usuário `guest`
- Resultado observado: seção "guest user can only connect from localhost": "By default, the guest user is prohibited from connecting from remote hosts" e "can only connect over a loopback interface (localhost)". Recusa registrada no log: "PLAIN login refused: user 'guest' can only connect via localhost". A página não menciona Docker nem contêineres.
- Limitações: a aplicação dessa regra ao Compose (conexão do contêiner `api` ao host `rabbitmq`) é inferência, não verificada sem Docker. Ver CFG-05.

### E-CFG-13 — render.yaml e checklist de deploy aplicado
- Tipo: inspeção de código e consulta de checklist (`engineering:deploy-checklist`)
- Fonte/local: `render.yaml:1-13`; `logs/analise_estatica.txt` (seção render.yaml); `src/archcorp/main.py:67-75`
- Comando e ambiente: parse YAML; leitura do checklist
- Resultado observado: plano `free`, runtime `docker`, `healthCheckPath: /health/ready`, `PUBLIC_DEMO` fixo em `true`, `DATABASE_URL` e `DEMO_ACCESS_TOKEN` com `sync: false`. Não declara `autoDeploy`, `region`, `disk` ou `numInstances`. Não define `RABBITMQ_URL` (broker desativado no Render). Aplicação do checklist:
  - Pré-deploy: testes passando na CI, comprovado para 44b8325 (run 39063148796, três jobs `success`). Código revisado e aprovado: não verificável (PRs mesclados sem `reviewDecision`; `git shortlog` em `origin/main` mostra 21 commits de um nome, 12 de uma variante desse nome e 2 atribuídos a "Claude"). Sem bugs críticos conhecidos: não verificado nesta frente (achados de F-DAD). Migrações testadas: parcial (convergência de migrações no job postgresql; SQLite por F-DAD). Flags configuradas: parcial (`PUBLIC_DEMO` declarado; `FINANCE_ALLOW_FUTURE_AS_OF` ausente, usa o padrão `False`). Rollback documentado: não verificável no repositório (sem artefato de rollback em `render.yaml` ou na CI). Equipe de plantão avisada: não aplicável (projeto acadêmico).
  - Deploy: staging: não atendido (serviço único, sem ambiente de staging declarado). Smoke tests: parcial (`scripts/demo_f1..f3.py` existem, não estão no pipeline e não rodaram contra URL pública). Canário: não aplicável (instância única). Monitoramento de erro e latência por 15 min: não atendido (sem alerta versionado). Fluxos-chave: parcial (mesmo caso dos smoke tests).
  - Pós-deploy: métricas nominais: não atendido. Changelog e stakeholders: fora do escopo (documentação). Tickets: fora do escopo (Jira e GitHub).
  - Gatilhos de rollback: não definidos em artefato versionado.
- Limitações: o painel do Render não foi acessado; nenhuma URL pública foi encontrada no repositório (ver E-CFG-23 e E-CFG-24).

### E-CFG-14 — verify.yml (análise estática) e execuções do workflow
- Tipo: inspeção de código e consulta ao GitHub (somente leitura)
- Fonte/local: `.github/workflows/verify.yml:1-83`; `logs/analise_estatica.txt` (seção verify.yml); `logs/github_leitura.txt` (`gh run list`); 2026-10-19 ~11:20 UTC
- Comando e ambiente: parse YAML; `gh run list --workflow verify.yml --limit 30` (GET)
- Resultado observado:
  - Gatilhos: `push` em `main` e `sobe-artefatos-cenario-4` (linha 5); `pull_request` sem filtro. `permissions: contents: read` no topo (linhas 8–9). Sem `concurrency`. Sem `timeout-minutes` em nenhum dos três jobs. Sem cache de pip. `pip install` repetido em três jobs.
  - Actions: 7 de 7 referenciadas por tag (`checkout@v7`, `setup-python@v7`, `setup-node@v7`).
  - Ferramentas ausentes do arquivo: ruff, mypy, bandit, semgrep, detect-secrets, gitleaks, trivy, codeql e dependabot (todas `False`).
  - Execuções das 30 mais recentes: `main` (push, 10) e 14 ramos de PR (20 execuções). Nenhuma para `sobe-artefatos-cenario-4`.
- Limitações: a lista tem só as 30 execuções mais recentes; o efeito do gatilho antigo pode existir em execuções mais antigas.

### E-CFG-15 — Logs da CI do SHA auditado (jobs postgresql, application e rabbitmq)
- Tipo: log da CI
- Fonte/local: run `39063148796` (workflow Verify, push de `44b8325`, 2026-10-17T19:35:51Z, conclusão `success`); jobs `117485116770` (postgresql), `117485116908` (application), `117485117016` (rabbitmq); `logs/ci_job_*.txt`
- Comando e ambiente: `gh run view --repo Roger-Quinelato/projetoAplicado7 --job <id> --log` (GET), salvo por `scripts/github_leitura.py`
- Resultado observado:
  - application: `No known vulnerabilities found` (pip-audit de requirements.txt); `213 passed, 10 skipped, 1 warning in 22.40s`; `found 0 vulnerabilities` (npm audit); build da imagem `archcorp-demo` concluído (`naming to docker.io/library/archcorp-demo done`).
  - rabbitmq: `20 passed, 1 warning in 0.99s` (`logs/ci_job_rabbitmq.txt`, linha 497). postgresql: `221 passed, 2 skipped, 1 warning in 43.83s` (`logs/ci_job_postgresql.txt`, linha 525). application: `213 passed, 10 skipped, 1 warning in 22.40s` (`logs/ci_job_application.txt`, linha 423). Os três jobs têm conclusão `success`.
  - O job rabbitmq roda só `tests/test_rabbitmq_real.py` e `tests/test_reliability_regressions.py` (`verify.yml:53`), e usa `localhost` (`verify.yml:45`).
- Redação: uma linha do job postgresql continha a credencial sintética de CI (`synthetic-ci-only`); foi substituída por `<REDACTED>` em `logs/ci_job_postgresql.txt` (`scripts/redigir_logs.py`). Os valores não aparecem nos registros.
- Limitações: o log é da execução de 17/10, não de nova execução.

### E-CFG-16 — Dependências: pins, fechamento transitivo e tamanho do conjunto
- Tipo: comando (leitura de metadados instalados no venv, sem instalar nada)
- Fonte/local: `scripts/analise_dependencias.py`; `logs/dependencias_fechamento.txt`; `requirements.txt:1-12`; `requirements-dev.txt:1-7`; 2026-10-19 ~11:12 UTC (aprox.)
- Comando e ambiente: `PY -I analise_dependencias.py <WT>`
- Resultado observado: 10 pins diretos, todos instalados nas versões exigidas (`igual=True`). Fechamento de execução: 22 transitivos sem pin nem hash neste Windows (inclui `colorama`, `tzdata` e `watchfiles`; a CI Linux pode incluir `uvloop` e excluir outros). Pacotes só de desenvolvimento: 44.
- Limitações: o fechamento foi avaliado com os marcadores de Windows. Não substitui a resolução limpa da CI.

### E-CFG-17 — pip-audit e pip list --outdated
- Tipo: comando (leitura de índice, sem instalar)
- Fonte/local: `logs/pip_audit_requirements.json`; `logs/pip_outdated.json`; 2026-10-19 ~11:12 UTC
- Comando e ambiente: `PY -I -m pip_audit -r requirements.txt -f json -o <LOGS>\...`; `PY -I -m pip list --outdated --format=json`
- Resultado observado: pip-audit sem vulnerabilidades para os 10 pins e transitivos (`vulns: []`), exit 0. Diretas atrás da última versão no índice: fastapi 0.143.2 → 0.147.0; starlette 1.8.0 → 1.9.0; uvicorn 0.35.0 → 0.54.0; sqlalchemy 2.0.43 → 2.1.5; psycopg 3.2.9 → 3.3.6; pika 1.3.2 → 1.4.4; pydantic-settings 2.10.1 → 2.16.0; email-validator 2.2.0 → 2.3.0; pydantic 2.13.5 → 2.14.1 (pin intencional, `requirements.txt:6-7`). alembic em dia.
- Limitações: pip-audit usa o índice na hora da execução. O resultado para AUD-25 (starlette) é da F-SEG.

### E-CFG-18 — npm ci, npm audit e npm outdated (web/)
- Tipo: comando (npm dentro da cópia)
- Fonte/local: `logs/npm_ci.txt`; `logs/npm_audit.json`; `logs/npm_outdated.json`; `ISO\web`; 2026-10-19 ~11:13 UTC
- Comando e ambiente: `npm ci --no-audit --no-fund`; `npm audit --json`; `npm outdated --json`
- Resultado observado: `npm ci` exit 0, com aviso de que o npm 11 não executou o `postinstall` do esbuild (sem efeito observado). `npm audit`: 0 vulnerabilidades em 71 dependências. `npm outdated` (exit 1, esperado com desatualizados): react 19.3.0 (wanted 19.3.1); vite 7.3.7 (latest 8.3.4); typescript 5.9.3 (latest 7.0.2).
- Limitações: a execução dos testes e do build do `web/` é da F-QUA.

### E-CFG-19 — Teste de OpenAPI para o pin do pydantic (recorte)
- Tipo: comando (pytest, subconjunto)
- Fonte/local: `logs/pytest_openapi_recorte.txt`; `requirements.txt:6-8` (comentário do pin); 2026-10-19 ~11:25 UTC (aprox.)
- Comando e ambiente: `$env:PYTHONPATH = "<ISO>\src"; PY -m pytest -q tests -k openapi -p no:cacheprovider` (a partir da cópia)
- Resultado observado: `3 passed, 220 deselected, 1 warning in 6.83s`. O teste que sustenta o pin de pydantic (`test_openapi_salvo_corresponde_a_aplicacao_e_documenta_exemplos`) passa com 2.13.5.
- Limitações: recorte de 3 testes. A suíte completa é da F-QUA.

### E-CFG-20 — Ignores, ausência de .env e de .env.example
- Tipo: comando (git ls-files, leitura de `.gitignore` e `.dockerignore`)
- Fonte/local: `.dockerignore:1-12`; `.gitignore:59, 151-152, 221-228`; `logs/analise_estatica.txt` (seção ignores); `logs/s01_s02_verificacoes.txt`
- Comando e ambiente: `git ls-files`; parse dos arquivos de ignore
- Resultado observado: `.dockerignore` exclui `.git`, `.venv`, `tmp`, `output`, `web/node_modules`, `web/dist`, `*.db` e `*.pyc`, mas não `.env`. `.gitignore` exclui `.env` (151), `.envrc` (152), `*.log` (59), `tmp/` (221) e `.codex-finalizer/`, `.codex-remote-attachments/` (222, 228). Não há entrada para `.claude/` nem `.claude/worktrees/`. `git ls-files` não tem nenhum `.env*` nem `*.example`.
- Limitações: `*.log` (linha 59) faz com que novos logs de auditoria não sejam versionados sem `git add -f`. Os logs desta frente foram gravados como `.txt` e `.json` por isso (premissa P-05 do resumo).

### E-CFG-21 — Configuração do web/
- Tipo: inspeção de código
- Fonte/local: `web/package.json:1-21`; `web/tsconfig.json:1-20`; `web/vite.config.ts:1-5`; `web/src/App.tsx:135`; `logs/analise_estatica.txt` (seção web/)
- Comando e ambiente: parse JSON; leitura
- Resultado observado: `package.json` com `private: true` e scripts `dev`, `build` (`tsc -b && vite build`) e `test` (`node --test "tests/**/*.test.ts"`); sem `engines` e sem `packageManager`. `tsconfig` com `strict`, `noUnusedLocals`, `noUnusedParameters`; `include: ["src"]`, portanto `web/tests/api.test.ts` fica fora de `tsc -b`. `vite.config.ts` com proxy `/api` e `/health` fixo em `127.0.0.1:8000`, sem `server.host`.
- Limitações: a versão exigida pelo teste (suporte a TypeScript no `node --test`) não foi verificada em outras versões de Node.

### E-CFG-22 — Alembic (configuração)
- Tipo: inspeção de código
- Fonte/local: `alembic.ini:1-7`; `src/archcorp/infrastructure/migrations/env.py:21-35`; `logs/analise_estatica.txt` (seção Alembic)
- Comando e ambiente: leitura
- Resultado observado: `alembic.ini` não tem `sqlalchemy.url`; `env.py` usa `settings.database_url` como fallback (linha 24). Não há credencial no arquivo. A migração automática na inicialização está em `main.py:73-75` e roda depois das guardas (ordem correta).
- Limitações: o conteúdo das migrações é da F-DAD.

### E-CFG-23 — Configurações do GitHub (somente leitura)
- Tipo: consulta ao GitHub (GET)
- Fonte/local: `logs/github_leitura.txt`; `scripts/github_leitura.py`; 2026-10-19T11:20:33Z
- Comando e ambiente: `gh api repos/Roger-Quinelato/projetoAplicado7/...` com GET; sem escrita
- Resultado observado:
  - Repositório: `visibility: public`; `default_branch: main`; `allow_forking: true`; `delete_branch_on_merge: false`.
  - Segurança: secret scanning `enabled`; push protection `enabled`; security updates do Dependabot `disabled`; secret scanning de padrões não provedores `disabled`.
  - `branches/main`: `protected: false`. `branches/main/protection`: 404 "Branch not protected". `rulesets`: lista vazia.
  - `vulnerability-alerts`: 404 "Vulnerability alerts are disabled". Dependabot alerts: 403 com a mensagem de desabilitado. `code-scanning`: 404 "no analysis found". Alertas de secret scanning abertos: 0.
  - Actions: `enabled`, `allowed_actions: all`, `sha_pinning_required: false`. Permissão padrão do `GITHUB_TOKEN`: `read`; aprovação de PR pelo workflow: não permitida.
  - Deployments: 0.
  - Issue #23 (T20): `open`, 0 comentários, rótulos `status:planejado`, `semana:S12`.
  - Run 39063148796: `success`, evento `push`, SHA `44b8325`. Jobs: postgresql, application e rabbitmq, todos `success`. Check runs do SHA: os três `success`. Status combinado: `pending` com 0 contextos (sem status externo).
  - PRs mescladas recentes: `reviewDecision` vazio em todas (#39–#53).
- Limitações: o token do `gh` tem escopo `repo`; alguns endpoints de segurança pedem escopo de administrador, e as respostas 403/404 foram registradas como "desabilitado" ou "não verificável" conforme a mensagem da API. O resultado de Dependabot foi lido pela mensagem de erro.

### E-CFG-24 — Governança de refs: AUD-50, branch sem remota e commit direto em main
- Tipo: comando (git, somente leitura) e consulta ao GitHub
- Fonte/local: `scripts/governanca_detalhes.py`; `logs/governanca_detalhes.txt`; 2026-10-19 ~11:25 UTC (aprox.)
- Comando e ambiente: `PY -I governanca_detalhes.py <WT> <LOGS>`, com `git -C <WT>`
- Resultado observado:
  - `ls-remote origin execucao-tarefas-pendentes`: ausente. `cat-file -t 3fdb533`: falha (exit 128). `3fdb533` não está no reflog de nenhuma ref. Nenhuma ref com "pendentes" no clone.
  - Branches locais sem upstream e sem remota contendo o SHA: `feat/fluxo-coordenado` (6901e02, 20 commits fora da `main`, em worktree `q01-workflow-dueat`). As demais locais sem upstream estão contidas em remotas.
  - Divergência local × remoto: só o remoto está à frente (sem commits locais não publicados) nas branches com upstream.
  - Commit `eaad233` ("Atualizar o nome AGENT.md", 2026-10-16) está em `main` com um pai (`3557d20`) e sem número de PR no assunto. Nenhum PR tem esse commit como merge.
  - Arquivos `docs/*_SYNC.json` e `JIRA_*.json` versionados: nenhum.
  - Domínios de hospedagem: `onrender.com` não aparece em código ou configuração. `supabase.co`: aparece só em `README.md`, e o host do link é `https://supabase.com` (genérico, não é URL de projeto). Texto do README não avaliado.
- Limitações: para `feat/fluxo-coordenado`, a ausência de remota é verificada neste clone. Outros clones da máquina podem ter a mesma branch.

### E-CFG-25 — Scripts de publicação em GitHub e Jira (leitura estática)
- Tipo: inspeção de código
- Fonte/local: `tools/publish_github_issues.py:20, 26-44, 87-88, 95-99, 151`; `tools/publish_jira_backlog.py:16, 49-56, 62, 74-78, 86-87, 92`
- Comando e ambiente: leitura. Nenhum script foi executado (escrevem em serviços externos, fora do escopo)
- Resultado observado: `publish_github_issues.py` chama a CLI `gh` por `subprocess` com lista de argumentos (credencial do `gh`, fora do repositório); cria issues, labels e milestones e faz PATCH de issues; grava `docs/GITHUB_ISSUES_SYNC.json` (coberto por `docs/*_SYNC.json`). Os corpos das issues apontam para a branch `sobe-artefatos-cenario-4` e para o PR #2 (linhas 87–88). `publish_jira_backlog.py` chama a CLI `twg` (credencial fora do repositório), tem site fixo (linha 16), cria workitems, links e transições, e usa id de transição fixo `"11"` (linha 87). Grava `docs/JIRA_SYNC.json`, `JIRA_LINKS.json` e `JIRA_STATUS.json`, todos ignorados. Nenhum literal de segredo nos scripts.
- Limitações: a leitura não cobre as configurações de `gh` e `twg` na máquina do autor.

### E-CFG-26 — Versionamento de .claude/ e skills-lock.json
- Tipo: inspeção de arquivo
- Fonte/local: `.claude/agents/cavecrew-*.md`; `.claude/skills/{cavecrew,caveman,caveman-commit}/`; `skills-lock.json:1-23`
- Comando e ambiente: leitura; `sha256sum` dos três `SKILL.md`
- Resultado observado: versionados em `main`: três agentes `cavecrew-*` (investigator e reviewer com `model: haiku`; builder sem modelo) e três skills `cavecrew`, `caveman` e `caveman-commit`. `skills-lock.json` lista as mesmas três skills com `computedHash`. Os SHA-256 dos `SKILL.md` não batem com os `computedHash` (`4444f8…` contra `32d532…` no cavecrew). O formato do `computedHash` não está documentado no repositório, então a conferência não é possível. Não há `.claude/settings.json` versionado (políticas de permissão e hooks não estão no repositório).
- Limitações: o conteúdo dos arquivos de agentes não foi avaliado como redação, por decisão do briefing.

### E-CFG-27 — Reprodutor do Compose (roteiro pronto, não executado)
- Tipo: comando (preparado; não executado)
- Fonte/local: `scripts/reproduzir_compose_broker_guest.py`
- Comando e ambiente: não executado. Exige Docker, e a decisão 2 do briefing proíbe Docker nesta auditoria
- Resultado observado: não há resultado. O roteiro sobe postgres, rabbitmq e api num projeto Compose próprio, tenta a conexão AMQP de dentro do contêiner `api` com a mesma URL, lê o log do rabbitmq, consulta o painel no host e remove os volumes. Critério: `ACCESS_REFUSED`/`ProbableAuthenticationError` confirma CFG-05; conexão bem-sucedida a refuta.
- Limitações: o roteiro depende de Docker numa máquina fora desta auditoria.

### E-CFG-28 — Redação de credenciais nas saídas brutas
- Tipo: comando
- Fonte/local: `scripts/redigir_logs.py`; `logs/*.txt` e `logs/*.json`
- Comando e ambiente: `PY -I redigir_logs.py <LOGS>`, executado duas vezes
- Resultado observado: 1 substituição na primeira execução (`synthetic-ci-only` em `ci_job_postgresql.txt`); 0 na segunda. Os experimentos já gravam URLs com `<REDACTED>` (`scripts/exp_config.py`, função `redigir`) e tokens só pelo comprimento.
- Limitações: a redação cobre as credenciais conhecidas desta frente (de desenvolvimento e de CI). Não é varredura de segredos; essa é da F-SEG.
