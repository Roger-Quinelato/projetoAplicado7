# Achados — F-QUA (Testes, qualidade, operação e interface)

Referência `main` = `44b8325`. Contagens: média 10 · baixa 9 · informativa 1 · alta 0 · crítica 0. Confiança alta em 16, média em 4.
Caminhos relativos à raiz do repositório. Scripts e logs em `scripts/` e `logs/`.

### QUA-01 — O formatter JSON descarta o tipo e a pilha da exceção no caminho do middleware
- Natureza / Severidade / Confiança: defeito demonstrado / média / alta (executado agora)
- Esperado (fonte): AGENTS.md, Confiabilidade ("Nunca capture uma exceção sem registrar contexto") e Observabilidade (logs com resultado e contexto do erro); critério de AUD-32 (01/10).
- Observado: `JsonFormatter.format` monta o JSON sem `record.exc_info`. Com `logger.exception` no middleware, a saída não tem tipo, pilha nem chave `exception`. O tipo só aparece no despacho, porque o chamador passa `errorType` explicitamente. O campo `module` é sempre `"archcorp"` (nome do logger), não o módulo de origem.
- Localização: `src/archcorp/observability.py:15-27`; `src/archcorp/main.py:102-104` (`logger.exception`); `src/archcorp/integration/service.py:86-88, 105-106` (`errorType`).
- Reprodução: `PY -I scripts/experimento_formatter_excecao.py ISO\src` → `logs/experimento_formatter_excecao.txt` (caso A: tipo False, Traceback False; caso B: errorType True).
- Impacto: os 500 de causa desconhecida (QUA-13, E-14) não puderam ser diagnosticados pelos logs; a causa só foi obtida reexecutando in-process.
- Evidências: E-QUA-09, E-QUA-18, E-QUA-21.
- Linha de base: AUD-32 (aberto; reconciliado em `linha_de_base.md`).
- Correção proposta e critério de aceite: incluir `exception: {type, message}` no JSON quando `record.exc_info` existir (pilha só fora de produção, mensagem sem dados de entrada). Trocar `module` por `record.name` do módulo de origem (`getLogger(__name__)`). Aceite: teste com `caplog` em que o registro do middleware contém `ValueError`, e nenhum conteúdo de entrada sintético aparece na saída.
- Skill ou fluxo sugerido para a correção: `tdd` (teste antes da correção, como exige AGENTS.md), depois `surgical-patch`.

### QUA-02 — Métricas mínimas e campos de log exigidos pelo AGENTS.md estão incompletos
- Natureza / Severidade / Confiança: dívida técnica / média / alta (executado: `/metrics` em E-14)
- Esperado (fonte): AGENTS.md, Observabilidade: "taxa e latência por operação, erros, retentativas, tamanho/idade da fila e mensagens não processadas"; logs com módulo.
- Observado: após cerca de 2.400 requisições, `/metrics` expõe 3 famílias: `archcorp_requests_total` (por operação e status), `archcorp_request_latency_seconds_sum` (só soma, sem contagem nem histograma, portanto sem p95) e `archcorp_events_published_total`. Não há contador de retentativas: o CRM reader só registra log `"result": "retry"`. Não há idade da fila; `broker_queue_messages` só é gravado no envio ao broker. `events_failed_total` só existe após a primeira falha. O campo `module` é fixo.
- Localização: `src/archcorp/observability.py:55-70` (middleware e `render_metrics`); `src/archcorp/contracts/adapters.py:51-52` (retentativa só em log); `src/archcorp/integration/service.py:130` (`broker_queue_messages`).
- Reprodução: `curl -H "Authorization: Bearer <TOKEN_OPERACOES_LOCAL>" .../metrics` → `logs/e14_metrics.txt`; grep de famílias.
- Impacto: a operação não vê retentativas nem backlog de fila; latência por operação só como média; diagnóstico de lentidão depende de medição externa.
- Evidências: E-QUA-18, E-QUA-09.
- Linha de base: novo (relaciona-se a AUD-36 e ao item P-14 do plano de 01/10).
- Correção proposta e critério de aceite: adicionar `archcorp_retries_total{operation}`, um gauge da idade do evento PENDING mais antigo, histograma de latência com buckets e o campo `module` pelo nome do módulo. Aceite: `/metrics` contém as quatro famílias, verificado por teste; teste de retentativa incrementa o contador.
- Skill ou fluxo sugerido para a correção: `tdd`; critérios de `AGENTS.md` (Observabilidade).

### QUA-03 — O teste de RLS não consegue detectar a exposição de `alembic_version` e das sequências
- Natureza / Severidade / Confiança: defeito de teste (lacuna) / média / alta (executado: 17 relações, sem `alembic_version`)
- Esperado (fonte): AGENTS.md, Segurança (minimizar exposição); critério de AUD-23 (01/10 A3-05): `has_table_privilege('anon', t, …)` falso para todas as relações do schema, e não só para o metadata.
- Observado: `protect_public_demo_tables` percorre só `Base.metadata.sorted_tables` e não trata sequências. O teste compara o mesmo conjunto, com conexão falsa (`SimpleNamespace`). Com o mesmo construtor, a execução emite 51 instruções (17 RLS e 34 REVOKE), sem nenhuma para `alembic_version` e sem nenhuma para sequências. O teste portanto não pode falhar pelas exposições que o 01/10 mostrou em PostgreSQL com padrões do Supabase simulados.
- Localização: `tests/test_public_database_security.py:8-27`; `src/archcorp/infrastructure/db.py:42-50` (laço em `:49`).
- Reprodução: `PY -I scripts/teste_cegueira_rls.py ISO\src` → `logs/teste_cegueira_rls.txt`.
- Impacto: a suíte fica verde mesmo com a exposição de AUD-23, que é o controle de segurança da demonstração pública. A verificação real depende de PostgreSQL e não foi executada aqui.
- Evidências: E-QUA-10, E-QUA-20.
- Linha de base: AUD-23 (aberto; frente F-SEG/F-DAD) e AUD-36 ("RLS por mock"; aberto).
- Correção proposta e critério de aceite: teste de integração em PostgreSQL que consulte `pg_class` do schema inteiro com `has_table_privilege` e `has_sequence_privilege` para `anon` e `authenticated`; o código passa a revogar `alembic_version` e as sequências. Aceite: o teste falha se a revogação de `alembic_version` for removida.
- Skill ou fluxo sugerido para a correção: `archcorp-seguranca` (§1 e §4) para o código e `tdd` para o teste; a verificação real é E-06 da F-SEG.

### QUA-04 — Os testes de contrato de eventos não validam formato (`date-time`, `uuid`)
- Natureza / Severidade / Confiança: defeito de teste (lacuna) / média / alta (executado)
- Esperado (fonte): AGENTS.md, Contratos ("datas e horas em ISO 8601 UTC"); critério de Q-05 e de P-10 (01/10): exemplos e envelopes validados contra o schema com `FormatChecker`.
- Observado: `asyncapi_validator` cria `Draft202012Validator` sem `format_checker`. Um `occurredAt` sem fuso (`2026-10-01T10:00:00`) passa sem erro; com `FormatChecker` falha ("is not a 'date-time'"). O mesmo vale para `dueAt`, que não tem asserção própria no teste (AUD-41). Só `occurredAt` tem asserção (`endswith("Z")`, linha 201), e só nos envelopes publicados.
- Localização: `tests/test_contracts_and_architecture.py:21-23` (validador), `:174-180` (exemplos), `:183-204` (envelopes).
- Reprodução: `PY -I scripts/teste_cegueira_formato.py ISO` → `logs/teste_cegueira_formato.txt`.
- Impacto: exemplos e envelopes com data sem fuso passam pela suíte; a detecção fica por conta da verificação E-03 da F-DAD, que não faz parte desta frente.
- Evidências: E-QUA-11.
- Linha de base: Q-05 (exemplos inválidos) e AUD-41 (`dueAt` sem Z), relacionados a AUD-20 e AUD-21 do 01/10 (reconciliação com a F-DAD).
- Correção proposta e critério de aceite: `format_checker=FormatChecker()` no validador e na validação dos exemplos do OpenAPI; asserção de `Z` em `dueAt`. Aceite: o teste falha com `2026-10-01T10:00:00` em `occurredAt` ou em `dueAt`.
- Skill ou fluxo sugerido para a correção: `archcorp-contratos-e-migracoes`; `tdd`.

### QUA-05 — As rotas de tarefas do Workflow não têm nenhum teste
- Natureza / Severidade / Confiança: defeito de teste (lacuna) / média / alta (cobertura e grep)
- Esperado (fonte): AGENTS.md, Testes obrigatórios ("para cada mudança de comportamento, testes de integração"); AUD-30 (T16: máquina de estados de tarefa).
- Observado: `POST /api/v1/workflow/tasks` (`create_task`, linhas 116-128) e `PATCH /api/v1/workflow/tasks/{id}` (`change_task`, linhas 131-149) não são chamados em nenhum teste. Só há um GET de tarefas (`test_extended_modules.py:66`). A rota de PATCH grava `item.state = body.state` sem validar transição: `DONE` para `OPEN` é aceito, e a conclusão do processo depende de todas as tarefas estarem `DONE`.
- Localização: `src/archcorp/workflow/routes.py:116-149`; ausência em `tests/`.
- Reprodução: `logs/coverage_report_src.txt` (`workflow/routes.py` 67,4%; ramos do pacote 60,0%) e grep em E-QUA-23.
- Impacto: transições inválidas e a regra de conclusão de processo por tarefas não são verificadas; a conclusão de processo que o plano considera implementada não tem teste de rota.
- Evidências: E-QUA-05, E-QUA-23.
- Linha de base: AUD-30 (aberto; F-ARQ/F-MOD); a lacuna de teste é nova.
- Correção proposta e critério de aceite: testes de criação (201; 404 e 409 em processo encerrado) e de transição (inválida → 409 `INVALID_STATE`; conclusão de todas as tarefas → processo `COMPLETED`). Aceite: `routes.py` acima de 90% de linhas.
- Skill ou fluxo sugerido para a correção: `tdd`; para a máquina de estados, `archcorp-fronteiras-e-dominio`.

### QUA-06 — A guarda de token do modo público não tem teste
- Natureza / Severidade / Confiança: defeito de teste (lacuna) / média / alta (cobertura e leitura do teste)
- Esperado (fonte): AGENTS.md, Segurança ("configure DEMO_ACCESS_TOKEN … somente no ambiente seguro do provedor"); plano de 01/10, P-15; briefing da F-CFG, item 2 (guardas de inicialização).
- Observado: `main.py:69-70` lança `RuntimeError` quando `PUBLIC_DEMO=true` e o token está ausente, é curto (menor que 24) ou começa com `demo-`. Nenhum teste executa essa linha (`main.py:70` aparece como não executada). O único teste de modo público (`test_finance.py:385-391`) usa um token válido e cobre apenas a guarda de `FINANCE_ALLOW_FUTURE_AS_OF` (linhas 71-72). Remover a guarda não quebra nenhum teste.
- Localização: `src/archcorp/main.py:69-70`; `tests/test_finance.py:385-391`.
- Reprodução: `logs/coverage_report_src.txt` (`main.py` 83%, linhas ausentes 70, 126-130, 163-175); leitura de `test_finance.py`.
- Impacto: uma regressão que permita o modo público com credencial fraca passaria pela suíte; a proteção depende de inspeção. A F-CFG executa a validação por experimento.
- Evidências: E-QUA-23, E-QUA-25.
- Linha de base: novo para o registro; relaciona-se a AUD-34 (credencial pública, aberto).
- Correção proposta e critério de aceite: teste parametrizado com token ausente, curto e `demo-*`, esperando `RuntimeError`, e um caso com token válido. Aceite: o teste falha se a guarda for removida (verificado por mutação manual, a registrar).
- Skill ou fluxo sugerido para a correção: `tdd`; coordenar com `archcorp-seguranca`.

### QUA-07 — `/health/live` e `/health/ready` não têm teste próprio, e o ramo 503 de `/health/ready` não é executado
- Natureza / Severidade / Confiança: lacuna de teste / baixa / alta
- Esperado (fonte): AGENTS.md, Observabilidade ("health checks separados para processo vivo e dependências prontas"); `render.yaml` usa `/health/ready` como `healthCheckPath`.
- Observado: `/health/live` só aparece como GET de smoke em `test_finance.py:396` (status 200). `/health/ready` não é chamado em nenhum teste, e o ramo de falha (503) de `main.py:126-130` não é executado.
- Localização: `src/archcorp/main.py:112-130`; `tests/test_finance.py:396`.
- Reprodução: grep em E-QUA-23; `logs/coverage_report_src.txt`.
- Impacto: o endpoint que o Render usa para decidir a saúde do serviço não tem teste do caminho de falha.
- Evidências: E-QUA-23, E-QUA-18.
- Linha de base: S-09 do plano de 01/10 (sinal "health sem teste próprio").
- Correção proposta e critério de aceite: testes de `/health/live` (200) e de `/health/ready` (200 com SQLite; 503 com um engine que falha). Aceite: os dois ramos de `ready` cobertos.
- Skill ou fluxo sugerido para a correção: `tdd`.

### QUA-08 — Contraste abaixo do mínimo no rodapé e nas bordas de campo
- Natureza / Severidade / Confiança: defeito / média / média (razão calculada pelo CSS; não renderizada; sem axe)
- Esperado (fonte): WCAG 2.1 AA, 1.4.3 (texto de 4,5:1 ou mais) e 1.4.11 (limite de componente de 3:1 ou mais), conforme o checklist de `design:accessibility-review`; critério de acessibilidade de T18.
- Observado: 5 de 46 pares estão abaixo do mínimo. O texto do rodapé (`footer`, `#66768a` sobre `#f4f7fb`, 11 px) tem 4,32:1. As bordas dos campos (`--line-strong` `#cfdae6` sobre branco) têm 1,42:1, e são o único contorno que identifica o controle. A borda do botão secundário tem 1,42:1. Os fundos de botão inline (1,10 a 1,11:1) têm rótulo textual e não são exigidos (premissa).
- Localização: `web/src/style.css:65` (rodapé), `:9` (token `--line-strong`), `:89` (campos), `:108` (botão secundário); `web/src/App.tsx:128` (rodapé dentro de `<main>`).
- Reprodução: `PY -I scripts/contraste_wcag.py` → `logs/contraste_wcag.md`.
- Impacto: pessoas com baixa visão podem não localizar os campos; o rodapé não atinge o AA.
- Evidências: E-QUA-08, E-QUA-19.
- Linha de base: AUD-27 (parcial; reconciliado em `linha_de_base.md`).
- Correção proposta e critério de aceite: escurecer o texto do rodapé e a borda dos campos até uma razão calculada pelo script (texto ≥ 4,5:1; contorno do campo ≥ 3:1). Aceite: `contraste_wcag.py` sem pares abaixo do mínimo para texto e para contorno de campo.
- Skill ou fluxo sugerido para a correção: `design:accessibility-review`; `surgical-patch` (tokens em `:root`).

### QUA-09 — `aria-label` em `<code>` contraria a nomeação de acessibilidade
- Natureza / Severidade / Confiança: defeito / baixa / média (premissa: ARIA 1.2, não reconsultada online)
- Esperado (fonte): ARIA 1.2, lista de papéis em que nomear é proibido (inclui `code`); WCAG 4.1.2 (nome, papel e valor).
- Observado: o componente `Id` renderiza `<code title={value} aria-label="Identificador …">`. Pela especificação, o `aria-label` não é aplicável ao papel `code`, e leitores de tela podem ignorá-lo.
- Localização: `web/src/ui.tsx:64-67` (linha 66).
- Reprodução: inspeção. Axe não executado (sem navegador).
- Impacto: identificadores nas tabelas são lidos sem o rótulo "Identificador"; impacto pequeno.
- Evidências: E-QUA-19.
- Linha de base: AUD-27 (parcial).
- Correção proposta e critério de aceite: remover o `aria-label` do `<code>` e manter o texto visível e o `title`. Aceite: axe sem `aria-prohibited-attr` em uma execução de navegador no CI (quando houver).
- Skill ou fluxo sugerido para a correção: `design:accessibility-review`; `surgical-patch`.

### QUA-10 — A interface não tem teste de comportamento nem verificação de acessibilidade na CI
- Natureza / Severidade / Confiança: lacuna de teste / média / alta
- Esperado (fonte): AGENTS.md, Testes ("testes proporcionais ao risco"); T10 (estados e erros) e T18 (acessibilidade); plano de 01/10, P-18 (Playwright e axe no CI).
- Observado: `web/tests/api.test.ts` tem 4 testes, todos de `describeIssue`. A cobertura medida pelo Node é de 60,6% das linhas, mas só de `api.ts`; os `.tsx` (contextos e componentes) não são carregados (0%). Não há teste de duplo clique, de preservação do formulário após erro, de estados de carregamento e erro, nem axe na CI. O PR #54 (Playwright) está aberto como rascunho desde 2026-10-17 20:46Z.
- Localização: `web/tests/api.test.ts`; `.github/workflows/verify.yml:67-81` (job `application`: `npm test` e `npm run build`, sem e2e nem axe).
- Reprodução: `node --experimental-test-coverage --test "tests/**/*.test.ts"` → `logs/npm_test_cobertura_frontend.txt`; `gh pr view 54` (E-QUA-15).
- Impacto: as regressões de AUD-26 (duplo clique, reset de formulário, chave por clique) podem voltar sem que a CI falhe.
- Evidências: E-QUA-07, E-QUA-15, E-QUA-19.
- Linha de base: AUD-26 (parcial), AUD-27 (parcial) e AUD-36 (acessibilidade e interface sem teste).
- Correção proposta e critério de aceite: testes de `ActionForm` e de `useIdempotencyKeys` (duplo envio gera uma requisição; erro preserva os campos) e axe no CI para as telas principais. Aceite: os testes passam no CI e falhariam nas versões anteriores descritas em AUD-26.
- Skill ou fluxo sugerido para a correção: `tdd`; reaproveitar o PR #54 após revisão, com `surgical-patch` para o que faltar.

### QUA-11 — A CI não tem gate de desempenho F1–F3, de cobertura, de lint nem de tipos
- Natureza / Severidade / Confiança: lacuna (dívida) / média / alta
- Esperado (fonte): AGENTS.md, Testes obrigatórios; RNF-07 (p95); plano de 01/10, P-17 e P-19 (medição de F1–F3 e CI com PostgreSQL).
- Observado: `scripts/performance_smoke.py` mede só `GET /health/ready` por TestClient (p95 de 5 ms aqui) e não roda na CI. O `verify.yml` não tem ruff, mypy, cobertura mínima nem medição de F1–F3. O job `postgresql` roda sem `-rs`, então os motivos de skip não aparecem no log. O job `rabbitmq` roda 2 arquivos (20 testes). Em E-14 (HTTP local), o p95 das rotas de negócio ficou entre 10 e 45 ms, mas isso não é gate.
- Localização: `.github/workflows/verify.yml:12-84`; `scripts/performance_smoke.py:5, 13-25`.
- Reprodução: leitura do YAML e do script; `gh run view ... --log` (E-QUA-14).
- Impacto: regressões de desempenho F1–F3 e de qualidade estática não bloqueiam a integração.
- Evidências: E-QUA-14, E-QUA-16, E-QUA-13.
- Linha de base: AUD-36 (parcial; desempenho F1–F3 e P-19).
- Correção proposta e critério de aceite: passo de medição F1–F3 com limite de p95 (500 ms, como o projeto declara) e, em seguida, ruff e cobertura mínima como gates (ruff começa com as regras atuais); `-rs` no job PostgreSQL. Aceite: o CI falha se o p95 de F1–F3 passar do limite em SQLite de CI.
- Skill ou fluxo sugerido para a correção: `surgical-patch` (YAML e script) e revisão com `code-review`.

### QUA-12 — Cauda de latência de até 19 s em escritas no SQLite local (causa não determinada)
- Natureza / Severidade / Confiança: risco / baixa / média (causa não determinada; ambiente Windows, SQLite)
- Esperado (fonte): RNF-07 (p95 abaixo de 500 ms), atendido em E-14 (p95 máximo de 45,17 ms); a cauda não é coberta pela meta.
- Observado: em E-14 (200 por rota), os máximos foram de 7,0 s a 21,8 s nas somas de fluxo, todos em escritas, e 1,6 s em leitura; nenhuma resposta de erro. No experimento de cauda (300 + 300), 7 requisições passaram de 300 ms, agrupadas entre t=10 s e t=16 s, incluindo uma criação de cliente de 19,3 s. Mediana de 16,7 ms e p99 de 314,5 ms.
- Localização: `src/archcorp/infrastructure/db.py:16` (engine SQLite, `pool_pre_ping=True`); `src/archcorp/contracts/service.py:81-95` (ativação, escrita após leitura). A origem não foi determinada.
- Reprodução: `PY -I scripts/medir_rotas_e14.py ...` e `PY -I scripts/cauda_latencia_e14.py ...` (E-QUA-16 e E-QUA-17).
- Impacto: numa demonstração ao vivo, uma requisição pode parecer travada por cerca de 20 s. A transposição para PostgreSQL não é possível sem medição.
- Evidências: E-QUA-16, E-QUA-17.
- Linha de base: novo (aspecto de desempenho de AUD-36).
- Correção proposta e critério de aceite: repetir a medição com PostgreSQL (mesmo script, `DATABASE_URL` dedicado) e registrar p50, p95 e p99; investigar a causa (tempo de espera de lock e I/O no Windows). Aceite: causa identificada ou risco aceito por escrito.
- Skill ou fluxo sugerido para a correção: `investigate-first` (hipóteses ranqueadas por evidência); medição com o script de E-14.

### QUA-13 — Ativação concorrente: sem teste, com 500 reproduzido no SQLite e dois eventos no PostgreSQL
- Natureza / Severidade / Confiança: defeito demonstrado (SQLite agora; PostgreSQL pelo 01/10) e lacuna de teste / média / alta
- Esperado (fonte): Fluxo mínimo 2 de AGENTS.md ("ativação do contrato cria cobrança … sem duplicidade"); RNF-02; AGENTS.md, Confiabilidade ("consumidores devem ser idempotentes").
- Observado: em 15 de 15 rodadas com duas ativações simultâneas (chaves diferentes), o SQLite devolve `[200, 500]` e um único evento. A causa, em 10 de 10 execuções in-process, é `sqlite3.OperationalError: database is locked` no `UPDATE contracts_contracts SET status=?`. O código lê o status, verifica a transição e grava sem escrita condicional (`contracts/service.py:88-95`). No PostgreSQL, o 01/10 registrou `[200,200]` e 2 `ContractActivated.v1` em 15 de 15 rodadas (E3-16). Nenhum teste de concorrência cobre a ativação (os 4 testes de `test_postgresql_concurrency.py` não tratam dela). Nenhum teste envia `amount` ≥ 10^12 a um contrato; os `amount` de contratos (`contracts/schemas.py:12`, `contracts/routes.py:90`) não têm `max_digits`, ao contrário de `PaymentInput` (`finance/routes.py:76`).
- Localização: `src/archcorp/contracts/service.py:88-95`; `src/archcorp/contracts/schemas.py:12`; `src/archcorp/contracts/routes.py:90`; `tests/test_postgresql_concurrency.py` (ausência).
- Reprodução: `PY -I scripts/ativacao_concorrente_api.py http://127.0.0.1:18103 <TOKEN_ADMIN_LOCAL> 15` (pronto para PostgreSQL) → `logs/ativacao_concorrente_sqlite.txt`; `PY -I scripts/ativacao_concorrente_causa.py ISO\src 10` → `logs/ativacao_concorrente_causa.txt`.
- Impacto: em PostgreSQL, dois fatos de ativação para as integrações (AUD-10); em SQLite, 500 ao operador. A CI não detecta nenhum dos dois casos, e valores ≥ 10^12 continuam produzindo 500 em PostgreSQL (AUD-35, 01/10 E3-19).
- Evidências: E-QUA-20, E-QUA-21.
- Linha de base: AUD-10 (aberto; a correção é da F-DAD, E-01 e E-08) e AUD-35 (aberto; F-DAD). A lacuna de teste é o AUD-36 (reconciliado).
- Correção proposta e critério de aceite: teste de ativação concorrente antes da correção (que deve falhar), depois escrita condicional (`UPDATE … WHERE status='DRAFT'` com verificação de `rowcount`, P-06) e `max_digits=14` nos `amount` de contratos (P-09). Aceite: duas ativações simultâneas geram exatamente um evento, sem 500, em SQLite e PostgreSQL.
- Skill ou fluxo sugerido para a correção: `tdd`; `archcorp-dados-e-consistencia` para a escrita condicional; `surgical-patch`.

### QUA-14 — Exceção do baseline v1 para `GET /metrics` sem ADR
- Natureza / Severidade / Confiança: divergência documental (processo) / baixa / alta
- Esperado (fonte): o próprio fixture usa ADR para exceções (`approved_ADR003` aponta para o ADR-003); AGENTS.md, Forma de trabalho ("crie um novo ADR para decisões estruturais"); `test_api_v1_compatibility.py:24-27` (guarda "com exceções explícitas").
- Observado: a exceção de segurança de `GET /metrics` (`approved_security`) tem só o `_motivo` textual ("Correção de segurança (#40)…"). Nenhum ADR em `docs/adr` menciona `/metrics`. O ADR-005 cita apenas as duas exceções do ADR-003.
- Localização: `tests/fixtures/api_v1_baseline.json:5670-5677`; `docs/adr/` (ADR-001 a ADR-006).
- Reprodução: `grep -rln '/metrics' docs/adr` (0); `grep -c 'ADR' tests/fixtures/api_v1_baseline.json` (1, a chave `approved_ADR003`).
- Impacto: uma mudança de contrato v1 aceita por teste sem decisão registrada; o mesmo mecanismo pode ser usado de novo sem revisão.
- Evidências: E-QUA-22.
- Linha de base: novo.
- Correção proposta e critério de aceite: registrar a exceção em ADR (novo ou acréscimo ao ADR-005) e exigir `adr` por chave no fixture, com teste de existência do arquivo. Aceite: toda chave de `approved_*` aponta para um ADR existente.
- Skill ou fluxo sugerido para a correção: `create-adr`.

### QUA-15 — Testes alteram o `settings` global e o restauram com valor fixo
- Natureza / Severidade / Confiança: dívida técnica / baixa / alta
- Esperado (fonte): boa prática de isolamento entre testes; S-07 do plano de 01/10 (`settings` global mutável).
- Observado: `tests/test_flows.py:83` e `:91` atribuem `settings.contract_adapter_available` diretamente e restauram com `True` fixo, num `try/finally`. Em `test_extended_modules.py:73-79`, a restauração usa os valores salvos. Os demais testes usam `monkeypatch`, que restaura sozinho.
- Localização: `tests/test_flows.py:83-91`; `tests/test_extended_modules.py:73-79`.
- Reprodução: `PY -I scripts/analise_testes.py ISO\tests` → `logs/analise_testes.txt` (2 atribuições diretas).
- Impacto: se o valor padrão mudar, o teste deixa um valor errado para os testes seguintes.
- Evidências: E-QUA-06.
- Linha de base: S-07 (novo no registro).
- Correção proposta e critério de aceite: trocar por `monkeypatch.setattr`. Aceite: nenhuma atribuição direta a `settings` em `tests/`.
- Skill ou fluxo sugerido para a correção: `surgical-patch`.

### QUA-16 — Sinais estáticos (ruff e mypy) não são gate e têm ocorrências
- Natureza / Severidade / Confiança: dívida técnica (sinal) / baixa / alta (contagens); triagem por código
- Esperado (fonte): checklist da F-QUA, item 6; AGENTS.md, Testes e qualidade.
- Observado: ruff 0.6.9 com regras padrão: 12 ocorrências. São 10 E402: 5 em `src/archcorp/schemas.py:30-34` (shim de reexportação, que faz a raiz depender dos contextos) e 5 em `tests/conftest.py:8-13` (de propósito, para definir `DATABASE_URL` antes do import). São 2 F401: `tests/conftest.py:10` e `tools/build_report.py:4`. mypy 1.11.2 em `src`: 72 erros em 14 arquivos (arg-type 23, dict-item 17, list-item 14, return-value 8, union-attr 4 e outros 6). A maioria é de tipagem de FastAPI e SQLAlchemy. Os falsos positivos de `support/domain.py:93,114` vêm de `as_utc` anotada como `datetime | None`. O sinal real está em `workflow/routes.py:138-147` (QUA-17).
- Localização: `src/archcorp/schemas.py:30-34`; `tests/conftest.py:8-13`; `tests/conftest.py:10`; `tools/build_report.py:4`; mypy em `src/archcorp/support/domain.py:93,114` e `src/archcorp/workflow/routes.py:138-147`.
- Reprodução: `PY -m ruff check src tests scripts tools --output-format concise` → `logs/ruff_concise.txt`; `PY -m mypy src --ignore-missing-imports` → `logs/mypy_src.txt`.
- Impacto: sem gate, a contagem pode crescer sem bloquear a integração.
- Evidências: E-QUA-12, E-QUA-13.
- Linha de base: novo.
- Correção proposta e critério de aceite: ruff como gate com exceções nomeadas (`noqa` no `conftest`) e mypy em `support` e `workflow`, com `as_utc` sobrecarregada para o tipo não nulo. Aceite: ruff com 0 erros e mypy sem aumento de erros na área tocada.
- Skill ou fluxo sugerido para a correção: `surgical-patch`; `code-review` na revisão.

### QUA-17 — `change_task` não trata processo inexistente
- Natureza / Severidade / Confiança: risco / baixa / média (inspeção e mypy; alcançável só com tarefa órfã)
- Esperado (fonte): AGENTS.md, Confiabilidade ("nunca capture uma exceção sem … convertê-la em resultado tratado"); `create_task` trata o caso com 404 (`workflow/routes.py:119-120`).
- Observado: `change_task` faz `process = session.get(ProcessInstance, item.process_id)` e usa `process.state` sem checar `None`. Com tarefa órfã, a rota responde 500 (AttributeError), e não um problem+json 404.
- Localização: `src/archcorp/workflow/routes.py:136-147` (mypy: linhas 138, 143, 145 e 147).
- Reprodução: inspeção; `logs/mypy_src.txt`.
- Impacto: baixo. Depende de integridade referencial: não há `PRAGMA foreign_keys` no código (SQLite, FK desligada por padrão), e em PostgreSQL a FK do banco protege a rota (premissa a confirmar).
- Evidências: E-QUA-13.
- Linha de base: novo.
- Correção proposta e critério de aceite: `if process is None: raise HTTPException(404, "Processo não encontrado")`. Aceite: teste com tarefa órfã (inserida por SQL) → 404 problem+json.
- Skill ou fluxo sugerido para a correção: `tdd`.

### QUA-18 — Downgrades de migrações não são executados pela suíte
- Natureza / Severidade / Confiança: lacuna de teste / baixa / alta (cobertura)
- Esperado (fonte): AGENTS.md, Migrações ("reproduzíveis e têm estratégia de compatibilidade"); critério de caminho de volta (plano de 01/10, F-DAD item 7).
- Observado: `0001_baseline.py` `downgrade` (linhas 223-279) não é executado pela suíte (54% do arquivo). `0003_contract_closing.py` `downgrade` (linhas 27-34) é parcialmente executado (72%). Há teste de downgrade só para a 0004 (`test_finance.py:456-478`).
- Localização: `src/archcorp/infrastructure/migrations/versions/0001_baseline.py:223-279`; `…/0003_contract_closing.py:27-34`.
- Reprodução: `logs/coverage_report_src.txt`.
- Impacto: o rollback até a base não é verificado pela suíte. A F-DAD executa E-12 com dados, o que cobre parte do risco.
- Evidências: E-QUA-05, E-QUA-23.
- Linha de base: novo (cruzado com E-12 da F-DAD).
- Correção proposta e critério de aceite: teste de downgrade e de upgrade para cada revisão com dados (SQLite na suíte; PostgreSQL na CI). Aceite: as linhas de downgrade de 0001 e 0003 passam a ser executadas.
- Skill ou fluxo sugerido para a correção: `migration` (critérios de ida e volta); `tdd`.

### QUA-19 — Tracing distribuído não está implementado (meta declarada)
- Natureza / Severidade / Confiança: meta futura / informativa / alta
- Esperado (fonte): AGENTS.md, Observabilidade ("traces devem atravessar API, adaptadores e consumidores"); AGENTS.md, linha 3 (tracing distribuído é meta, não funcionalidade comprovada).
- Observado: não há instrumentação de traces (OpenTelemetry ou equivalente; grep em `src`: 0 ocorrências). Há correlação por `X-Correlation-ID`, `correlationId` nos logs e a trilha `/api/v1/operations/{id}` (RF-06), que cobrem parte da necessidade.
- Localização: `src/archcorp/main.py:85-109` (middleware de correlação); ausência de instrumentação em `src/`.
- Reprodução: grep (E-QUA-25).
- Impacto: diagnóstico entre módulos depende de `correlationId` e da trilha, sem medição de duração por etapa.
- Evidências: E-QUA-25, E-QUA-18.
- Linha de base: novo (critério de AGENTS.md, Observabilidade).
- Correção proposta e critério de aceite: decisão de arquitetura antes da implementação (ADR). Não é correção imediata.
- Skill ou fluxo sugerido para a correção: `create-adr`.

### QUA-20 — `POST /api/v1/crm/customers` não aceita `Idempotency-Key`
- Natureza / Severidade / Confiança: divergência código × AGENTS.md / baixa / alta
- Esperado (fonte): AGENTS.md, Confiabilidade ("comandos mutáveis expostos por HTTP devem aceitar `Idempotency-Key` quando puderem ser repetidos").
- Observado: a rota não lê o cabeçalho (`crm/routes.py:128-143`). A UI chama `createCustomer` sem chave (`web/src/api.ts:311`; `web/src/contexts/Crm.tsx:42`). Repetir o mesmo e-mail devolve 409 `CONFLICT` sem o `customerId` do cadastro original (`tests/test_foundation.py:51-60`). Não há duplicata, mas a resposta original não é reaproveitada.
- Localização: `src/archcorp/crm/routes.py:128-143`; `web/src/api.ts:311`; `web/src/contexts/Crm.tsx:42`.
- Reprodução: `grep -rn "Idempotency" src/archcorp/crm` (sem resultados); leitura de `test_foundation.py`.
- Impacto: baixo. Um reenvio após perda de resposta não recupera o identificador do cliente sem uma consulta extra.
- Evidências: E-QUA-24.
- Linha de base: AUD-26 (item "cadastro de cliente sem chave", parcial) e AUD-39 (idempotência heterogênea, F-DAD/F-MOD).
- Correção proposta e critério de aceite: aceitar `Idempotency-Key` em `POST /customers` pelo `IdempotencyStore` e enviá-la na UI. Aceite: repetição com a mesma chave devolve 201 com `Idempotency-Replayed: true`, e o mesmo `customerId`.
- Skill ou fluxo sugerido para a correção: `tdd`; `surgical-patch` no frontend.
