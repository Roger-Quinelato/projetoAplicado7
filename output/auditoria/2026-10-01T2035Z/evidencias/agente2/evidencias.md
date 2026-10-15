# Evidências — Agente 2 (Arquitetura e comportamento)

Referência auditada: `3a3d8bd` (cópia isolada `$SP/iso`). Data: 2026-10-01 (UTC), execuções entre 20:38 e 20:48 UTC.
`$SP` = `/tmp/claude-0/-home-user-projetoAplicado7/ec00d59b-c354-5d1f-b4d6-080b88ac1d06/scratchpad`.

Ambiente comum das execuções: Python 3.11.15, venv `$SP/agente2/venv` com `requirements-dev.txt` (fastapi 0.116.1, SQLAlchemy 2.0.43, jsonschema 4.26.0); `PYTHONPATH=$SP/agente2/exp`, código importado de `$SP/iso/src`; `PYTHONDONTWRITEBYTECODE=1`; banco SQLite descartável `$SP/agente2/run/<exp>.db` (recriado a cada script); `RABBITMQ_URL` ausente salvo indicação. Harness: `$SP/agente2/exp/harness.py` (TestClient + token `demo-admin`). Comando-padrão: `cd $SP/agente2/run && EXP=eNN PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../exp ../venv/bin/python ../exp/eNN_*.py`. Saídas integrais em `$SP/agente2/exp/eNN.out`.

Limitação geral: a suíte `pytest` NÃO foi executada (atribuição do Agente 3). SQLite serializa escritas; o comportamento em PostgreSQL foi registrado como pedido em `pedidos_execucao.md`. Falhas de consumidor foram **injetadas** por substituição de handlers em memória (monkeypatch), o que é declarado em cada evidência.

---

### E2-01 — Dependências de import entre contextos (AST)
- Tipo: comando (análise estática)
- Fonte/local: `$SP/agente2/imports_ast.py` sobre `$SP/iso/src/archcorp`; saída `exp/e00_imports.out`
- Resultado observado: `contracts.service:11 -> integration.models ['IdempotencyRecord'] (MODELS)`; `support.service:9 -> integration.models ['IdempotencyRecord'] (MODELS)`; `main:26 -> integration.models ['AuditLog','OutboxEvent']`; `contracts.service:9 -> crm.public`; `support.service:7 -> contracts.public`; todos os contextos importam `integration.service` (`audit`, `enqueue`, `LegacyIdService`, `IdempotencyStore`). Nenhum import de `<contexto>.models` entre crm/contracts/finance/support/workflow. Nenhum ciclo (integration não importa contextos).
- Limitações: não detecta acesso dinâmico; cobre `src/archcorp` exceto migrações.

### E2-02 — Dependências de framework por arquivo
- Tipo: comando (mesmo script)
- Resultado observado: todos os `service.py` importam `sqlalchemy` e recebem `Session`; `crm/public.py` e `contracts/public.py` (portas) importam `sqlalchemy.orm.Session` na assinatura; `integration/service.py` importa `pika` diretamente; apenas `contracts/domain.py` e `exceptions.py` são livres de framework.

### E2-03 — Rotas reais x `docs/api/openapi.yaml`
- Tipo: comando — `exp/e01_rotas.py`, saída `exp/e01.out`
- Resultado observado: `rotas reais: 49 operacoes no openapi.yaml: 49`, `so no codigo: []`, `so no doc: []`, `openapi gerado == salvo: True`. Comandos com `Idempotency-Key`: drafts (obrigatória), activate (obrigatória), tickets (obrigatória), reservation draft (obrigatória), reservations e close (opcional). Sem chave: payments, workflow/tasks, crm (customers/contacts/opportunities), assign/resolve/reconcile, dispatch, reprocess.
- Limitações: não substitui `tools/export_openapi.py --check` (Agente 3).

### E2-04 — Exemplos do OpenAPI validados contra os próprios schemas
- Tipo: comando — `exp/e11_exemplos_openapi.py`, saída `exp/e11.out`
- Resultado observado: `exemplos verificados=261 invalidos=11`. Ex.: `POST /api/v1/contracts/drafts [201] exemplo=created: ["billing/amount: 2500.0 is not of type 'string'"]`; `GET .../entitlement exemplo=notEligible: 'slaHours' is a required property`; `POST /api/v1/support/tickets exemplo=pending: 'slaHours'/'dueAt' required`; 4 exemplos de reserva sem `contractId` obrigatório.
- Causa (inspeção): FastAPI remove valores `null` dos exemplos; `ContractDraftResponse/ContractActivationResponse` usam `Billing` (Decimal) cuja saída é `string` (`Billing-Output`), mas o exemplo usa número.

### E2-05 — Representação monetária inconsistente entre endpoints
- Tipo: comando — `exp/e10_money.py`, saída `exp/e10.out`; inspeção `docs/api/openapi.yaml` (componentes)
- Resultado observado: `resposta POST /drafts billing: {'amount': '19.99' ...} | POST /activate billing: {'amount': '19.99' ...} | GET /contracts/{id} billing: {'amount': 19.99 ...}`. OpenAPI: `Billing-Output` = `type: string`; `BillingResponse`, `InvoiceResponse`, `PaymentResponse` = `type: number`. `POST /drafts` com 2500 devolve `"2500.0"` (E2-07).

### E2-06 — AsyncAPI `Money.amount` (`number`, `multipleOf: 0.01`) rejeita valores legítimos
- Tipo: comando — `exp/e09_ordem_contrato.py` e `exp/e10_money.py`
- Resultado observado: `Money.amount=0.07 ... erros=['0.07 is not a multiple of 0.01']`, `19.99 ...`, `1234567.89 ...`; envelope real gravado na outbox: `envelope real ContractActivated.v1 amount= 19.99 erros AsyncAPI: ['19.99 is not a multiple of 0.01']`. 100.1 e 2500.0 passam.
- Limitações: validador python-jsonschema 4.26 (aritmética de ponto flutuante); outros validadores podem divergir, o que reforça a fragilidade do contrato.

### E2-07 — F1: rascunho, idempotência, cliente inativo
- Tipo: comando — `exp/e02_f1.py`, saída `exp/e02.out`
- Resultado observado: rascunho K1 `201 replayed=false`; repetição K1 `201 replayed=true` mesmo `contractId`; K1 com amount 2600 → `409 IDEMPOTENCY_CONFLICT`; K1 com "2500.00" → `201 replayed=true`; nova chave K2 mesmo negócio → `409 CONFLICT "Já existe o contrato ..."`; amount 100.005 → `422 decimal_max_places`; amount -1 → `422`; **startsOn 2020-01-01 → `201` (rascunho no passado aceito)**; cliente inativo/inexistente → `422 BUSINESS_RULE_VIOLATION`; cliente inativado após o rascunho: replay K8 → `201 replayed=true` (resposta armazenada); reserva R1 repetida → replay; reserva sem chave repetida → **duas reservas idênticas**; draft da reserva com outra chave → `200 replayed=true` mesmo contrato; reserva de cliente inativo → `422`.

### E2-08 — F2: ativação, dupla ativação, duplo despacho, reentrega
- Tipo: comando — `exp/e03_f2.py`, saída `exp/e03.out`
- Resultado observado: A1 `200 replayed=false eventId=32e5...`; A1 repetida e A2 (outra chave) → `200 replayed=true` mesmo `eventId`; sem chave → `422 missing Idempotency-Key`; contrato inexistente → `404`; mesma chave A1 em OUTRO contrato → `200 replayed=false` (escopo da chave = operação+contrato). `dispatch 1 -> {"processed": 2}` (invoices=2 processes=2 inbox=4); `dispatch 2 -> processed 0`; reentrega (evento recolocado em PENDING) → `processed 1`, contagens inalteradas; reentrega com inbox apagada → contagens inalteradas (proteção por `uq_invoice_contract`/`uq_process_reference` e verificação prévia). SQLite: `typeof(amount)=real` para `finance_invoices`; payload do evento `{'amount': 100.1, ...}` (float).

### E2-09 — Falha parcial de consumidor persiste efeito do handler que falhou
- Tipo: comando com falha injetada — `exp/e04_falhas.py` cenário A, saída `exp/e04.out`
- Resultado observado: handler de Workflow substituído por `wf(session, env); raise RuntimeError(...)`. `dispatch -> {"processed": 0, "failed": 1}`; estado: `invoices=1 processes=1 tasks=1 inbox=['finance'] outbox=[('ContractActivated.v1','PENDING',1,...)]` → o processo/tarefa gravados pelo handler que falhou foram **confirmados** (sem savepoint/rollback). Após restaurar o handler: `processed 1`, `processes=1` (não duplicou porque `_start` verifica existência).
- Local: `src/archcorp/integration/service.py:24-45` (um único `session.commit()` em `:45`, também no ramo `except`).

### E2-10 — Erro de banco em consumidor gera 500 em loop e bloqueia a outbox (evento envenenado)
- Tipo: comando com falha injetada — `exp/e04_falhas.py` cenário B e `exp/e05_bloqueio.py` cenário B2
- Resultado observado: handler que provoca `IntegrityError` → `dispatch IntegrityError #1..#4 -> 500 INTERNAL_ERROR`; outbox `('ContractActivated.v1','PENDING',0,'')` — `attempts` não incrementa, `last_error` vazio, nunca vira `FAILED`; `GET /integration/failures -> []`. B2: `CustomerUpdated.v1` criado depois permanece `PENDING` em 3 despachos consecutivos (bloqueio de cabeça de fila).
- Causa (inspeção): após falha de `flush`, o `session.commit()` do `except` (`integration/service.py:45`) levanta `PendingRollbackError`, abortando o laço.

### E2-11 — Corrida de despacho concorrente (SQLite, threads)
- Tipo: comando — `exp/e06_concorrencia.py`, saída `exp/e06.out`
- Resultado observado: duas threads com sessões próprias chamam `dispatcher.dispatch_pending`; barreira após a verificação da inbox. `resultados: [('ok', {'processed': 1, 'failed': 0}), ('erro', "PendingRollbackError: ...")]`; `chamadas ao handler finance: 2`; `invoices: 1`. Não há `SELECT ... FOR UPDATE SKIP LOCKED`, lease ou lock: ambos selecionam e executam o mesmo evento; a duplicidade é barrada só pela restrição única, e o perdedor termina em erro (500 via HTTP).
- Limitações: SQLite serializa escritas; barreira força a intercalação. Repetir em PostgreSQL (pedido P-01).

### E2-12 — RabbitMQ configurado e indisponível
- Tipo: comando — `exp/e04_falhas.py` cenário C (porta fechada `127.0.0.1:5999`) e `exp/e05_bloqueio.py` cenário C2 (`10.255.255.1`)
- Resultado observado: consumidores internos executam e gravam inbox, mas o evento fica `PENDING` → após 3 despachos `FAILED`, `reason: ""` (mensagem de `AMQPConnectionError` vazia). `CustomerUpdated.v1` também falha (`processed 0, failed 1`) apesar de a projeção ter sido aplicada. Reprocessamento sem broker: `processed 2`, faturas continuam 3 (sem duplicação). Host sem resposta: `dispatch blackhole (30.1s) -> {"processed": 0, "failed": 3}` (~10 s por evento, uma conexão por evento, `last_error: ['', '', '']`).
- Inspeção complementar: nenhum `queue_declare`/`queue_bind`/publisher confirms em `src/` (`grep`), logo, com o Compose padrão, mensagens publicadas na exchange `archcorp.events` sem fila vinculada são descartadas pelo broker.
- Limitações: RabbitMQ não instalado; descarte de mensagens não roteáveis inferido da semântica AMQP (confiança média).

### E2-13 — Pagamentos: centavos, 3 casas, saldo, inadimplência
- Tipo: comando — `exp/e07_pagamentos.py`, saída `exp/e07.out`
- Resultado observado: fatura 100.10. `pag 0.001 -> 201 paidAmount 0.001`; `pag 0.004 -> 201`; `pag -1`/`0 -> 422`; USD/`brl` → `422 "Moeda diferente da fatura"` com `code VALIDATION_ERROR`; `pag 100.10 -> 201 status PAID` (aceito embora já houvesse 0.005 gravado); lista de pagamentos mostra `REF-0004 amount 0.0`; SQLite grava `('REF-0001','real',0.001), ('REF-0004','real',0.004)`. Fatura vencida: `GET -> status OVERDUE`, `status persistido: OPEN`; pagamento de vencida aceito (`PAID`). Encerramento do contrato: fatura permanece `OPEN`. Auditoria de finance: somente `create_first_invoice` (pagamentos não auditados).
- Local: `src/archcorp/finance/routes.py:42` (`amount: Decimal = Field(gt=0)` sem `decimal_places`), `:129-135`, `:83`.

### E2-14 — F3: chamado, elegibilidade, transições, encerramento
- Tipo: comando — `exp/e08_f3.py`, saída `exp/e08.out`
- Resultado observado: abertura `201 OPEN slaHours 8 dueAt ...Z`; mesma chave com descrição diferente → `201 replayed=true` (não conflita); categoria diferente → `409 IDEMPOTENCY_CONFLICT`; contrato inexistente / DRAFT / cliente diferente / serviceCode vazio → `422`; com adaptador indisponível, contrato **inexistente** → `201 PENDING_ENTITLEMENT` e processo de Workflow iniciado; reconciliação → `REJECTED_ENTITLEMENT`; transições inválidas de chamado → `409` com `code CONFLICT` (não `INVALID_STATE`). Releitura do chamado: `dueAt "2026-10-02T04:44:43.234..."` sem `Z`. Workflow: tarefa `OPEN->CANCELLED->IN_PROGRESS->OPEN` aceitas; tarefa `DONE` conclui o processo enquanto o chamado segue `OPEN`; tarefas duplicadas sem idempotência. Encerramento: sem chave repetido → `409`; outra chave → `200 replayed=true`; mesma chave com outro motivo → `409 IDEMPOTENCY_CONFLICT`; chamado aberto do contrato encerrado permanece `OPEN` e pode ser resolvido; novo chamado → `422`; ONBOARDING → `COMPLETED` com tarefa `CANCELLED`; fatura `OPEN`.

### E2-15 — Reprocessamento de `CustomerUpdated.v1` antigo sobrescreve projeção mais nova
- Tipo: comando com falha transitória injetada — `exp/e09_ordem_contrato.py`, saída `exp/e09.out`
- Resultado observado: v1 falha 3× (FAILED); v2 despachado → `projecao apos v2: Nome Versao 2`; reprocessa v1 → `projecao em contracts apos reprocessar v1: Nome Versao 1`; CRM (fonte oficial) = `Nome Versao 2`.
- Local: `src/archcorp/contracts/service.py:144-147` (UPDATE incondicional, sem versão/ocorrência).

### E2-16 — `dueAt` sem fuso em payloads (SQLite) e validação AsyncAPI com FormatChecker
- Tipo: comando — `exp/e09_ordem_contrato.py`
- Resultado observado: `TicketResolved.v1 formatchecker=off ... erros=[]`; `formatchecker=on dueAt=2026-10-02T04:45:41.500187 erros=["... is not a 'date-time'"]`. O teste `test_envelopes_publicados_validam_contra_asyncapi` não habilita `format_checker`.
- Limitações: em PostgreSQL (`timestamptz`) o valor deve vir com fuso; pedido P-04.

### E2-17 — Atomicidade outbox + mudança de negócio
- Tipo: comando com falha injetada — `exp/e12_tx_corrida.py`
- Resultado observado: falha injetada em `audit(... "activate_contract")` após `enqueue` → `500`; `status contrato: DRAFT | eventos outbox: 0` (transação única confirmada).

### E2-18 — Ativações concorrentes com chaves diferentes publicam dois `ContractActivated.v1`
- Tipo: comando — `exp/e12_tx_corrida.py` (barreira após `eligible_customer`)
- Resultado observado: `resultados: [('RC-2','ok','b560...'), ('RC-1','ok','36eb...')]`; `ContractActivated.v1 para o contrato: 2`; `dispatch -> processed 2`; 1 fatura (restrição única). Sem bloqueio de linha/versão otimista em `ContractService.activate` (`contracts/service.py:62-87`).
- Limitações: SQLite; intercalação forçada. Repetir em PostgreSQL (P-02).

### E2-19 — Alcance real dos testes de arquitetura
- Tipo: comando — `exp/e13_teste_arquitetura.py` (replica a lógica de `tests/test_contracts_and_architecture.py:90-115` sobre trechos sintéticos; não executa a suíte)
- Resultado observado: só `from archcorp.crm.models import Customer` é detectado; passam sem violação: `from archcorp.crm import models`, `import archcorp.crm.models [as m]`, `from archcorp.integration.models import OutboxEvent`, uso de `crm.service` interno, `text('select * from crm_customers')`, `Base.metadata.tables[...]`.

### E2-20 — Inspeção do despachante, retentativa e observabilidade de falhas
- Tipo: inspeção de código — `src/archcorp/integration/service.py:21-64`, `src/archcorp/main.py:534-556`
- Resultado observado: uma tentativa por chamada HTTP; sem backoff/jitter/agendador; sem limite de lote; `logger.exception("Falha ao despachar evento", extra={"operation": "dispatch_event", "result": "failure"})` sem `eventId`/`eventType` e com o `correlationId` da requisição de despacho, não o do evento; `pika.BlockingConnection` aberta por evento, sem timeout explícito; reprocessamento audita `previousAttempts` e correlação mas não o solicitante (ADR-001 regra 12 exige solicitante).

### E2-21 — Inspeção de regras de negócio fora do domínio
- Tipo: inspeção de código
- Resultado observado: regras em rotas HTTP: pagamento/saldo/quitação (`finance/routes.py:117-138`), resolução/atribuição de chamado com `enqueue`/`audit` direto (`support/routes.py:68-95`), transições de tarefa e conclusão de processo (`workflow/routes.py:125-142`), reprocessamento (`main.py:547-556`). `main.py` (619 linhas) define rotas de Contracts, Support e Integration além da composição. Três implementações de idempotência: `IdempotencyStore` com impressão digital (draft, reserva, close), registro bruto sem hash (`activate`, `contracts/service.py:84`; `open_ticket`, `support/service.py:43`) e comparação de 4 campos (`support/service.py:21`).

### E2-22 — Inspeção do frontend (somente leitura)
- Tipo: inspeção de código — `web/src/App.tsx` (108 linhas)
- Resultado observado: telas dos cinco contextos; `Idempotency-Key` gerada com `crypto.randomUUID()` a cada clique (reenvio do usuário cria nova chave; chamados podem duplicar); sem ações de reconciliação, falhas/reprocessamento, cancelamento de reserva ou trilha por correlação; não envia `X-Correlation-ID`; erros exibem `detail`.
- Limitações: build/execução do frontend não feitos (Agente 3).

### E2-23 — Inspeção documental de eventos
- Tipo: inspeção documental
- Resultado observado: `docs/arquitetura/TO_BE.md` ("o AsyncAPI documenta `CustomerUpdated.v1`, `ContractActivated.v1` e `TicketOpened.v1`") e `docs/DDD_LOCALIZA.md` (Eventos de Domínio: 3) listam 3 eventos; `docs/events/asyncapi.yaml` e `docs/TDD_LOCALIZA.md` listam 6; dispatcher (`main.py:340-347`) registra 6 tipos com 7 consumidores. `ContractClosed.v1` tem só o consumidor Workflow (Finance ausente, declarado como pendência T12). `causationId` sempre `null` (nenhum produtor o preenche).

### E2-24 — CRM: validação, unicidade, transições e autorização (amostra)
- Tipo: comando — `exp/e14_crm.py`, saída `exp/e14.out`
- Resultado observado: nome aparado (`"Empresa  Teste"`); e-mail e `legacyId` duplicados → `409 CONFLICT`; PATCH vazio ou `null` → `422`; telefone fora de E.164 → `422`; contato de cliente inexistente → `404`; oportunidade `WON→LOST` → `409 INVALID_STATE`; autorização: `demo-support POST customers 403`, `demo-finance GET customers 403`, `demo-support GET customers 200`, `demo-commercial deactivate 200`, `demo-finance dispatch 403`, token inválido `401`; `X-Correlation-ID` não UUID → `400 BAD_REQUEST`.
- Limitações: amostra, não a matriz completa (a suíte `tests/test_crm.py` cobre a matriz; não executada por este agente).
