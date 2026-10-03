# Achados — Agente 3 (Qualidade, segurança e operação)

Referência `3a3d8bd`. Ordenados por severidade. Nenhum achado crítico.

### A3-01 — Erro de banco em consumidor bloqueia toda a outbox e nunca chega a FAILED
- Natureza: defeito demonstrado / Severidade: **alta** / Confiança: alta (reproduzido em PG; gatilho injetado)
- Esperado: `AGENT.md` (Confiabilidade): "Encaminhe falhas permanentes para fila de erro, preservando payload seguro, motivo, tentativas"; "Nunca capture uma exceção sem registrar contexto"; RNF-02; critério T17 "falhas recuperáveis".
- Observado: quando um consumidor provoca erro no `flush` (ex.: valor fora de `Numeric(14,2)`), o `except` incrementa `attempts` e chama `session.commit()` sem `rollback()`; o commit lança `PendingRollbackError` → HTTP 500. `attempts` permanece 0, o evento fica `PENDING` para sempre, `/integration/failures` fica vazio e, como os pendentes são lidos em ordem de `occurred_at`, todos os eventos seguintes deixam de ser despachados (fatura do contrato legítimo não criada após 5 despachos).
- Localização: `src/archcorp/integration/service.py:25-45`.
- Reprodução: `PYTHONPATH=src python $A/poison_exp.py` (PG descartável) → `despacho 1..5 → 500`, `[('ContractActivated.v1','PENDING',0,''), ...]`, `falhas listadas: []`.
- Impacto: um único evento incompatível paralisa F2/F3 (cobrança, workflow) sem aparecer na fila de falhas; recuperação só por intervenção manual no banco.
- Evidências: E3-17, E3-18.
- Correção proposta: processar cada evento em transação própria (`session.begin_nested()`/savepoint por consumidor ou `rollback()` no `except` seguido de recarga do evento e gravação de `attempts`/`last_error` em nova transação); registrar tipo da exceção. Aceite: teste que injeta evento com erro de banco e verifica `FAILED` após `retry_limit`, motivo não vazio e despacho normal dos eventos seguintes, em SQLite e PostgreSQL.

### A3-02 — Despachos simultâneos retornam HTTP 500 (sem bloqueio de linhas)
- Natureza: defeito demonstrado / Severidade: média / Confiança: alta (15/15 rodadas em PG)
- Esperado: RNF-02; `AGENT.md` "Consumidores devem ser idempotentes"; reprocessamento "incapaz de duplicar efeitos".
- Observado: dois `POST /api/v1/integration/outbox/dispatch` simultâneos → `[200, 500]` em todas as rodadas. Não há duplicidade de fatura/processo/inbox (as restrições `uq_invoice_contract`, `uq_process_reference`, `uq_inbox_event_consumer` seguram), mas o segundo despacho falha com `PendingRollbackError` (mesma causa raiz de A3-01) e não há `FOR UPDATE SKIP LOCKED`.
- Localização: `integration/service.py:22,37-45`.
- Reprodução: `python $A/conc_exp.py http://127.0.0.1:18082 "<dsn>" 15` com uvicorn sobre PG.
- Impacto: botão "Despachar" clicado em duas abas/usuários gera erro 500; impede escala horizontal do despachante (meta futura).
- Evidências: E3-16, E3-17.
- Correção: `SELECT ... FOR UPDATE SKIP LOCKED` (PG) na leitura dos pendentes + correção de A3-01. Aceite: teste de concorrência em PG com N despachos paralelos → todos 200, zero duplicidade.

### A3-03 — Ativação concorrente publica dois `ContractActivated.v1` para o mesmo contrato (disparável por duplo clique na interface)
- Natureza: defeito demonstrado / Severidade: média / Confiança: alta (15/15 via API; reproduzido no frontend real)
- Esperado: Fluxo mínimo 2 "Ativação do contrato cria cobrança e inicia preparação de retirada por evento, sem duplicidade"; RNF-02; AsyncAPI (um fato por ativação).
- Observado: duas ativações simultâneas com `Idempotency-Key` diferentes → `[200, 200]` e dois eventos na outbox. O frontend gera chave nova por clique (`crypto.randomUUID()`) e o botão "Ativar" não é desabilitado: o duplo clique na jornada Playwright produziu 2 eventos. Cobrança e processo não duplicaram (restrições únicas nos consumidores), mas a cópia no broker e qualquer consumidor externo recebem dois fatos de ativação.
- Localização: `contracts/service.py:62-87` (leitura do estado sem bloqueio); `web/src/App.tsx:50,99`.
- Reprodução: E3-16 cenário A; `python $A/web_journey.py ...` passo 09.
- Impacto: eventos duplicados para integrações; auditoria com duas ativações; trilha inconsistente.
- Evidências: E3-16, E3-24, E3-25.
- Correção: bloquear a linha do contrato (`with_for_update()`) ou atualização condicional `UPDATE ... WHERE status='DRAFT'` verificando `rowcount`; no frontend, desabilitar ações durante `busy` e reutilizar a chave por intenção. Aceite: teste PG com 2 ativações paralelas (chaves diferentes) → um 200 e um replay/409, exatamente 1 evento.

### A3-04 — [fundir com A2-02] Falha do broker "opcional" marca evento como FAILED após os consumidores internos já terem executado, com motivo vazio
- Natureza: defeito demonstrado / Severidade: média / Confiança: alta
- Esperado: README e `ESTADO_IMPLEMENTACAO.md` ("RabbitMQ recebe cópia opcional"); `AGENT.md` (motivo preservado; timeout; retentativa só para transitórios com backoff/jitter).
- Observado: com `RABBITMQ_URL` para porta fechada, fatura e processo são criados e commitados, mas o evento vai a `FAILED` em 3 despachos; `reason=''` em `/integration/failures`; reprocessar repete a falha. Não há backoff/jitter (A3-19) nem timeout explícito no pika (padrões da biblioteca).
- Localização: `integration/service.py:32,39,49-64`.
- Reprodução: `python $A/rabbit_exp.py sqlite:///$A/rabbit.db "amqp://guest:guest@127.0.0.1:5999/%2F"`.
- Impacto: operador vê falha permanente de evento cujo efeito de negócio já ocorreu; diagnóstico impossível pelo motivo vazio.
- Evidências: E3-20; revisão cruzada: 10,01–15,01 s por evento sem timeout explícito (padrões do pika), convergente com A2-02.
- Correção: separar estado de consumo interno e de publicação (ex.: `published_to_broker` / outbox de publicação própria), gravar `type(exc).__name__` quando `str(exc)` for vazio, definir `socket_timeout/blocked_connection_timeout`. Aceite: teste com broker indisponível → evento consumido internamente, publicação pendente com motivo não vazio.

### A3-05 — `alembic_version` e sequências ficam expostas a `anon`/`authenticated`; anon pode impedir a inicialização
- Natureza: risco (demonstrado em PG local com privilégios padrão simulados) / Severidade: média / Confiança: média (Supabase real não verificado)
- Esperado: README/ESTADO ("revoga os privilégios de anon e authenticated nas tabelas do protótipo"); T17; T20 "revisão de segredos".
- Observado: `protect_public_demo_tables` percorre só `Base.metadata.sorted_tables`; `alembic_version` fica sem RLS e com SELECT/UPDATE/DELETE para `anon`; sequências com USAGE. `SET ROLE anon; DELETE FROM alembic_version` → reinício falha (`DuplicateTable`, "Application startup failed").
- Localização: `src/archcorp/infrastructure/db.py:18-29`.
- Reprodução: E3-13/E3-14 (criar papéis, `ALTER DEFAULT PRIVILEGES ... GRANT ALL ... TO anon, authenticated`, iniciar com `PUBLIC_DEMO=true`, `SET ROLE anon; DELETE FROM alembic_version;`, reiniciar).
- Impacto: quem possuir a chave `anon` do projeto Supabase consegue derrubar a publicação (negação de serviço na próxima reinicialização/hibernação do Render Free).
- Evidências: E3-13, E3-14.
- Correção: incluir `alembic_version` e sequências no REVOKE (ou `REVOKE ALL ON ALL TABLES/SEQUENCES IN SCHEMA public FROM anon, authenticated` + `ALTER DEFAULT PRIVILEGES ... REVOKE`), ou usar schema próprio não exposto pela Data API. Aceite: teste em PG real verificando `has_table_privilege('anon', t, 'SELECT/UPDATE/DELETE') = false` para **todas** as relações do schema.

### A3-06 — Valor monetário sem limite de dígitos gera HTTP 500 em PostgreSQL
- Natureza: defeito demonstrado / Severidade: média / Confiança: alta
- Esperado: `AGENT.md` "Valide todas as entradas na fronteira da aplicação"; contrato de erro (`ESTADO_IMPLEMENTACAO.md`).
- Observado: `amount` ≥ 10^12 em rascunho/reserva → 500 (`DataError` não tratado) no PG; SQLite aceita, por isso a suíte não detecta.
- Localização: `src/archcorp/schemas.py:111`; `src/archcorp/contracts/routes.py:85`; `finance/routes.py:42`; colunas `Numeric(14,2)`.
- Reprodução: `curl -X POST /api/v1/contracts/drafts ... "amount":1000000000000000.00` → 500.
- Impacto: erro interno exposto; mesma classe de entrada pode originar eventos incompatíveis (ver A3-01).
- Evidências: E3-19.
- Correção: `Field(gt=0, max_digits=14, decimal_places=2)` (e `le=`) em todos os valores; handler para `DataError` → 422. Aceite: testes 422 para valores fora do intervalo, executados também em PG.

### A3-07 — `/metrics` público com rótulos de cardinalidade ilimitada
- Natureza: defeito demonstrado / Severidade: média / Confiança: alta
- Esperado: RNF-03/RNF-04; `AGENT.md` "Minimize os dados presentes em APIs".
- Observado: `/metrics` responde sem autenticação mesmo com `PUBLIC_DEMO=true`; o rótulo `operation` usa o caminho bruto, incluindo UUIDs de contratos e `correlationId`. 300 requisições não autenticadas com UUIDs distintos criaram 600 séries; o dicionário em memória cresce sem limite.
- Localização: `src/archcorp/observability.py:34-47`; `main.py:411-419`.
- Reprodução: E3-12.
- Impacto: crescimento de memória por requisições anônimas (degradação do Render Free); enumeração de IDs e correlações pela rota pública.
- Evidências: E3-12.
- Correção: usar o template da rota (`request.scope["route"].path`) e agrupar 404; proteger `/metrics` (papel `operations` ou token próprio) no modo público. Aceite: teste que faz N requisições com IDs distintos e verifica número constante de séries; 401 em `/metrics` no modo público.

### A3-08 — Logs JSON descartam a exceção (sem tipo nem stack)
- Natureza: defeito demonstrado / Severidade: média / Confiança: alta
- Esperado: `AGENT.md` "Nunca capture uma exceção sem registrar contexto"; RNF-04.
- Observado: `JsonFormatter` ignora `record.exc_info`; os 15 erros 500 do teste de concorrência aparecem só como "Erro não tratado"/"Falha ao despachar evento" — a causa só foi descoberta reproduzindo em processo.
- Localização: `src/archcorp/observability.py:15-25`.
- Reprodução: `grep '"level": "ERROR"' $A/logs/uvicorn_pg_conc.log`.
- Impacto: diagnóstico de falhas operacionais inviável na demo publicada.
- Evidências: E3-21, E3-17.
- Correção: incluir `exception: {type, message}` (e stack fora de produção) no JSON, sem dados sensíveis. Aceite: teste com `caplog` verificando o tipo da exceção no registro.

### A3-09 — Starlette 0.47.3 (transitiva, não pinada) com advisories conhecidos; Range afeta os arquivos estáticos servidos
- Natureza: risco / Severidade: média / Confiança: alta para a presença da versão vulnerável (pip-audit/PyPI), média para impacto
- Esperado: `AGENT.md` (segurança da demo pública); T17/T18.
- Observado: 7 advisories únicos em starlette 0.47.3 (CVE-2025-62727 Range/FileResponse, CVE-2026-48710 Host, CVE-2026-54282 path, CVE-2026-54283 form, CVE-2026-48817, CVE-2026-48818 [Windows]). A app serve `web/dist` com `StaticFiles`/`FileResponse`: 8000 intervalos de Range sem token → 7,58 s de processamento; `/health/live` concorrente subiu de 0,005 s para 0,56 s; RuntimeError no log. pytest 8.4.1 (dev) com CVE-2025-71176. npm: 0.
- Localização: `requirements.txt:1` (fastapi 0.116.1 limita starlette <0.48); `main.py:607-619`.
- Reprodução: `pip-audit -s pypi -r requirements-dev.txt`; E3-27.
- Impacto: degradação por requisições anônimas na URL pública.
- Evidências: E3-27, E3-28.
- Correção: atualizar FastAPI para versão compatível com starlette ≥1.3.1, gerar lock com hashes, adicionar `pip-audit`/`npm audit` ao CI. Aceite: pip-audit sem achados aplicáveis; suíte verde.

### A3-10 — Frontend: reenvio, perda de dados e papéis
- Natureza: defeito demonstrado / Severidade: média / Confiança: alta
- Esperado: T10 "estados e feedback de erros"; `AGENT.md` (`Idempotency-Key` em comandos repetíveis).
- Observado: (a) `Idempotency-Key` aleatória por clique e botões inline sem `disabled` → duplo clique em "Ativar" gerou 2 requisições com chaves distintas (A3-03); (b) `ActionForm` limpa o formulário antes do resultado → após "E-mail já cadastrado no CRM" os campos ficam vazios; (c) mensagens de validação do Pydantic em inglês, sem nome do campo ("String should have at least 3 characters"); (d) `refresh` com `Promise.all` em 9 coleções: com `demo-support` o painel nem abre ("Papel sem permissão") — a interface só funciona com perfil admin; (e) token inválido fica gravado em `sessionStorage`; (f) cadastro de cliente não envia `Idempotency-Key`.
- Localização: `web/src/App.tsx:27,47-69,89,97-105`.
- Reprodução: `python $A/web_journey.py http://127.0.0.1:18090 "<dsn>"`; capturas `shots/03_token_support.png`, `06_crm_duplicado.png`, `12_atendimento_erro.png`.
- Evidências: E3-24, E3-25.
- Correção: desabilitar ações durante `busy`, chave por intenção, `reset()` só em sucesso, tradução de erros 422 por campo, carregamento tolerante a 403 por coleção. Aceite: teste de navegador (Playwright) cobrindo duplo clique, erro com preservação de campos e login por papel.

### A3-11 — Acessibilidade: contraste insuficiente e landmarks ausentes
- Natureza: defeito demonstrado / Severidade: média / Confiança: alta (axe-core 4.13.0), com limitação de fonte
- Esperado: critério T18 "acessibilidade".
- Observado: `color-contrast` (serious) em todas as telas (2–14 nós: `.eyebrow`, `.label`, `.stat span`, `small`); tela de acesso sem `main` e conteúdo fora de landmarks. Aspectos positivos: `lang="pt-BR"`, inputs com `<label>` envolvente, aviso com `role="status"`, botão de fechar com `aria-label`, sem rolagem horizontal em 390 px.
- Localização: `web/src/style.css` (cores `#7791b9`, `#93a8c9` etc.); `App.tsx:89`.
- Reprodução: passo axe em `web_journey.py`.
- Evidências: E3-24.
- Correção: ajustar tokens de cor para ≥4,5:1; `<main>` na tela de acesso; `role="alert"` no erro de login. Aceite: axe sem violações serious/critical nas telas principais, executado no CI.

### A3-12 — Modo público: credencial compartilhada com todos os papéis e sem limitação de tentativas
- Natureza: risco (documentado) / Severidade: média / Confiança: alta
- Esperado: T17 "papéis"; `AGENT.md` (RBAC; OIDC é meta).
- Observado: `PUBLIC_DEMO=true` → `Principal("public-demo", TOKEN_ROLES["demo-admin"])`; quem tem a credencial reprocessa falhas, consulta trilhas e estado; validação só de comprimento ≥24 e prefixo `demo-` (sem checagem de entropia); sem rate limit; `/docs`/`/openapi.json` públicos. Documentado no README como adequado ao protótipo.
- Localização: `security.py:28-31`; `main.py:352-353`.
- Evidências: E3-11, E3-12.
- Correção: tokens públicos por papel (ex.: `DEMO_ACCESS_TOKEN_SUPPORT`) ou leitura apenas; limitação de tentativas; registrar como risco aceito em ADR. Aceite: teste 403 de papel não admin no modo público.

### A3-13 — Verificação de qualidade incompleta: suíte presa ao SQLite, RLS testado por mock, CI sem PG/desempenho/acessibilidade
- Natureza: dívida técnica / Severidade: média / Confiança: alta
- Esperado: T18 "testes de integração/contrato, acessibilidade, desempenho"; `AGENT.md` "integração para banco, broker"; ATRIBUTOS_QUALIDADE (Testabilidade).
- Observado: `conftest.py` sobrescreve `DATABASE_URL`; teste RLS usa conexão falsa; CI (`verify.yml`) roda só pytest/SQLite, build e `docker build` — sem PG, RabbitMQ, `performance_smoke.py`, testes de navegador/acessibilidade, concorrência ou auditoria de dependências. Experimento com conftest alterado: 57/57 em PG, mas os defeitos A3-01/02/03/06 só aparecem em PG/concorrência e não são cobertos. `performance_smoke.py` mede só `/health/ready` (não F1–F3).
- Localização: `tests/conftest.py:5`; `tests/test_public_database_security.py`; `.github/workflows/verify.yml`; `scripts/performance_smoke.py:19`.
- Evidências: E3-04, E3-05, E3-06, E3-23, E3-29.
- Correção: `DATABASE_URL` de teste configurável; job CI com serviço `postgres:16` (papéis anon/authenticated) e testes de concorrência; Playwright+axe; medição F1–F3. Aceite: CI verde com matriz SQLite+PG.

### A3-14 — Migração: esquema intermediário sem `alembic_version` falha em PostgreSQL
- Natureza: defeito demonstrado (caso de borda) / Severidade: baixa / Confiança: alta
- Esperado: `AGENT.md` "migrações são reproduzíveis e têm estratégia de compatibilidade"; ADR-002.
- Observado: `upgrade_to_head` só distingue "igual a head" ou "baseline"; esquema em 0002 sem carimbo → `DuplicateColumn` (PG). SQLite passa (batch recria a tabela). Os demais cenários (vazio, legado 0001 com dados, downgrade/upgrade) funcionam em SQLite e PG.
- Localização: `src/archcorp/infrastructure/migrate.py:48-54`.
- Evidências: E3-09, E3-10.
- Correção: detectar a revisão por comparação com cada revisão ou exigir carimbo manual documentado. Aceite: teste para cada revisão intermediária sem carimbo.

### A3-15 — Ausência de cabeçalhos de segurança; 405 fora do contrato de erro; fonte externa
- Natureza: risco / Severidade: baixa / Confiança: alta
- Observado: sem CSP, `X-Content-Type-Options`, `X-Frame-Options`/`frame-ancestors`, `Referrer-Policy`, HSTS (Render termina TLS, mas o app não envia HSTS); token em `sessionStorage` sem CSP; 405 retorna `application/json` em vez de `application/problem+json`; `style.css` carrega Google Fonts (dependência externa/privacidade). CORS ausente = mesma origem apenas (adequado).
- Evidências: E3-26.
- Correção: middleware de cabeçalhos; handler para 405; fontes locais. Aceite: teste verificando cabeçalhos.

### A3-16 — E-mail em log de acesso
- Natureza: risco / Severidade: baixa / Confiança: alta
- Esperado: RNF-03 / `AGENT.md` (não registrar dados pessoais).
- Observado: log de acesso do uvicorn registra `GET /api/v1/crm/customers?email=...`. Logs da aplicação não contêm token, e-mail ou corpo.
- Evidências: E3-22.
- Correção: `--no-access-log` ou filtro de query string; busca por e-mail via POST/corpo. Aceite: grep de e-mail em logs = 0.

### A3-17 — Mesma `Idempotency-Key` em paralelo retorna 409 em vez de replay; reserva sem chave duplica
- Natureza: defeito demonstrado / Severidade: baixa / Confiança: alta
- Observado: ativação/reserva com a mesma chave em paralelo → `[200,409]`/`[201,409]` (sem duplicidade, mas o cliente legítimo recebe conflito); reserva sem chave (opcional por contrato) → 2 reservas.
- Evidências: E3-16.
- Correção: capturar a violação de PK do registro de idempotência e devolver a resposta armazenada. Aceite: teste paralelo → ambos 2xx com `Idempotency-Replayed: true` no segundo.

### A3-18 — Imagem e dependências pouco reprodutíveis/endurecidas
- Natureza: dívida técnica / Severidade: baixa / Confiança: média (inspeção; build não executado localmente)
- Observado: transitivas Python não pinadas e sem hashes; imagens por tag sem digest; contêiner como root; sem `HEALTHCHECK` (o Render usa `healthCheckPath`); Node 22 local vs 24 no CI/Dockerfile e Python 3.11 vs 3.12; credenciais `guest/guest` e `archcorp/archcorp` apenas no compose local (documentado).
- Evidências: E3-28, E3-29.
- Correção: lock (`pip-compile --generate-hashes`/`uv lock`), `USER` não root, digest das imagens. Aceite: build reprodutível com lock e varredura de imagem.

### A3-19 — Divergências documentais de qualidade/segurança
- Natureza: divergência documental / Severidade: baixa / Confiança: alta
- Observado: `docs/ATRIBUTOS_QUALIDADE.md` cita "Bearer OIDC simulado" e "retentativa controlada e fila de falha" — o código usa tokens fixos (sem OIDC simulado) e a "retentativa" é a contagem de chamadas manuais ao despacho, sem backoff/jitter nem fila no broker (`AGENT.md` exige backoff exponencial com jitter). Desempenho declarado (6,36 ms; 5,74 ms) refere-se só a `/health/ready`; medição atual 11,1–13,7 ms (outro hardware), dentro da meta.
- Evidências: E3-23, E3-32.
- Correção: ajustar o texto para "tokens fixos de demonstração" e "retentativa manual limitada"; separar meta de comportamento. Aceite: documento coerente com `ESTADO_IMPLEMENTACAO.md`.

### A3-20 — T20 sem evidência de publicação
- Natureza: meta futura (não atendida) / Severidade: informativa / Confiança: alta
- Esperado: `CRONOGRAMA_EXECUCAO.md` T20 e "Regras de conclusão" (URL HTTPS, `/health/ready`, frontend, escrita/leitura após reinício, revisão de segredos).
- Observado: nenhuma URL Render/Supabase no repositório; issue #23 aberta, `status:planejado`, sem comentários; `ESTADO_IMPLEMENTACAO.md` declara não verificado. Equivalente local executado: PG + reinício + persistência + health OK (E3-15); `docker build` só no CI (run 36660119780 success).
- Evidências: E3-15, E3-29, E3-31.
- Correção: publicar e registrar evidência (URL, captura de `/health/ready`, escrita/leitura após reinício, privilégios `anon`). Aceite: critério T20 integralmente evidenciado, após corrigir A3-05 e A3-07.
