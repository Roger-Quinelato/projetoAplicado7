# Evidências da frente F-DAD — Dados, consistência, contratos e migrações

Referência: `main` = `44b8325`. Execuções na cópia `iso-dad` (`git archive`, sem `.git`), SQLite descartável em `iso-dad\tmp`, Python `venv-auditoria` (3.12.10), sem Docker. Data das execuções: 2026-10-19, UTC 11:09–11:25. PostgreSQL e RabbitMQ não estão disponíveis localmente: os roteiros que dependem deles estão em `scripts\` com a marca "PG pronto" e constam como não executados (ver fim do arquivo).

Convenção dos roteiros: cada `scripts\<nome>.py` importa `scripts\dad_common.py`, que aponta `DATABASE_URL` para `iso-dad\tmp\<banco>.db`. Com `ADB_URL` definido, o mesmo roteiro roda contra um banco PostgreSQL descartável (não executado).

---

### E-DAD-01 — Integridade da cópia de execução
- Tipo: comando
- Fonte/local: `PKG\evidencias\manifest_44b8325.sha256` (292 entradas) contra `iso-dad`
- Comando e ambiente: PowerShell 5.1, `Get-FileHash -Algorithm SHA256` por arquivo listado no manifesto, comparação com o hash gravado.
- Resultado observado: `checked=292 bad=0`.
- Limitações: `.claude/` não está no manifesto (fora do escopo do manifesto por desenho). Não verifica o `.git` do worktree, que não é usado.

### E-DAD-02 — Ambiente e formatos do validador
- Tipo: comando
- Fonte/local: `venv-auditoria` (`PY -c` com `import`)
- Comando e ambiente: Python 3.12.10; jsonschema 4.26.0; SQLAlchemy 2.0.43; pydantic 2.13.5; FastAPI 0.143.2; alembic 1.20.0; pika 1.3.2; starlette 1.8.0; httpx 0.28.1; openapi-spec-validator 0.9.0; rfc3339-validator 0.1.4 (instalado).
- Resultado observado: `FormatChecker` com formatos `date`, `date-time`, `email`, `uuid` (e demais). `date-time` é verificado porque `rfc3339-validator` está presente.
- Limitações: nenhuma instalação foi feita no venv; só leitura de versões.

### E-DAD-03 — Inspeção do caminho de ativação, pagamento e resolução
- Tipo: inspeção de código
- Fonte/local: `src/archcorp/contracts/service.py:81-107` (`activate`: `require` sem lock na linha 87; verificação de estado na 93; `status = ACTIVE` na 95; `enqueue` na 101; `commit` na 106); `src/archcorp/contracts/service.py:166-169` (`apply_customer_update`: `UPDATE` incondicional); `src/archcorp/finance/service.py:130` (`_require(..., lock=True)` em `record_payment`) e `:233` (`with_for_update`); `src/archcorp/support/service.py:302-310` (`_transition`: `UPDATE ... WHERE status = expected` com `rowcount`).
- Comando e ambiente: `Grep` por `with_for_update|skip_locked|begin_nested` em `src/archcorp`; leitura das linhas acima na cópia.
- Resultado observado: `with_for_update` aparece em `integration/service.py:31,61`, `finance/service.py:171,233` e `support/service.py:291`. Não aparece em `contracts/service.py`. A ativação não tem bloqueio nem `UPDATE ... WHERE` com verificação de linhas afetadas. O padrão condicional com `rowcount` existe em `support/service.py:302-310`.
- Limitações: inspeção. A ausência de bloqueio é a condição para a corrida; a confirmação em PostgreSQL está em E-DAD-05 (roteiro pronto, não executado em PG).

### E-DAD-04 — Inspeção do despachante, do savepoint e do broker
- Tipo: inspeção de código
- Fonte/local: `src/archcorp/integration/service.py:25-72` (`dispatch_pending`); `:26-27` (pendentes sem `LIMIT`); `:31` (`with_for_update(skip_locked=True)`); `:38` (`begin_nested()` por evento, que envolve todos os consumidores); `:46` (`_publish_broker` dentro do savepoint); `:48` (`_register_failure`); `:61-65` (recuperação de falha de commit); `:92-96` (`_register_failure`: `attempts += 1` e `FAILED` ao atingir `retry_limit`); `:108-145` (`_publish_broker`: `pika` com timeouts nas linhas 117-120, `queue_declare` durável com `x-max-length` nas linhas 128-129, `confirm_delivery` na 135, `mandatory=True`); `src/archcorp/integration/routes.py:54-63` (reprocessamento: `attempts = 0` na 61; auditoria na 60 sem principal).
- Comando e ambiente: leitura direta e `Select-String` dos números de linha na cópia.
- Resultado observado: o savepoint é por evento (não por consumidor) e inclui a publicação no broker. Uma recusa do broker desfaz os efeitos de todos os consumidores daquele evento. A contagem de tentativa é gravada em transação própria. O reprocessamento registra só `previousAttempts`.
- Limitações: inspeção. A consequência operacional do acoplamento foi executada em E-DAD-09.

### E-DAD-05 — E-01: concorrência de ativação, ativação×cancelamento, pagamentos e resolução (SQLite)
- Tipo: comando (execução)
- Fonte/local: `scripts\e01_concorrencia.py`; log `logs\e01_concorrencia_sqlite.log`
- Comando e ambiente: `& $py scripts\e01_concorrencia.py`, SQLite `iso-dad\tmp\e01.db`; barreiras em instância entre leitura e escrita (`wrap_after`). Dois runs; a ordem de qual thread perde variou entre runs, o resultado não.
- Resultado observado:
  - A (ativação × ativação, chaves diferentes): `[('erro', 'OperationalError', 'database is locked ... UPDATE contracts_contracts'), ('ok', ...)]`; `ContractActivated.v1 = 1`; `status = ACTIVE`.
  - B (ativação × cancelamento): uma thread com `database is locked`; `estado final (contrato, reserva) = ('CANCELLED', 'CANCELLED')`; `ContractActivated.v1 = 0`.
  - C (pagamentos 60 + 60 sobre 100): uma com `database is locked`, a outra `PARTIALLY_PAID`; `soma gravada = 60.00`.
  - D (resolução simultânea): uma `RESOLVED`, a outra `database is locked`; `TicketResolved.v1 = 1`.
- Limitações: no SQLite, o bloqueio do arquivo impede a dupla gravação; o resultado não reproduz a corrida de PostgreSQL (`READ COMMITTED` sem bloqueio na ativação). A versão PostgreSQL está pronta no mesmo roteiro com `ADB_URL` (não executada: sem PostgreSQL local). O perdedor recebe exceção não tratada (HTTP 500 na API, ver E-DAD-11).

### E-DAD-06 — E-02: CustomerUpdated.v1 antigo reprocessado sobre projeção mais nova (SQLite)
- Tipo: comando (execução)
- Fonte/local: `scripts\e02_ordem_projecao.py`; log `logs\e02_ordem_projecao_sqlite.log`
- Comando e ambiente: `& $py scripts\e02_ordem_projecao.py`, SQLite `iso-dad\tmp\e02.db`; falha transitória injetada no consumidor de produção (mesma função `ContractService.apply_customer_update`).
- Resultado observado: controle sem falha: `projeção = Controle Versao 2`. Cenário: `despacho 1..3 (v1 falhando): failed 1` → `FAILED`; `despacho com v2: projeção = Nome Versao 2`; `reprocessamento da v1: 200 PENDING`; `despacho após reprocessamento: projeção = Nome Versao 1`; `fonte oficial (CRM): Nome Versao 2`.
- Limitações: a falha foi injetada no consumidor (como em 01/10). O defeito está na ausência de versão/`occurredAt` na projeção, não na injeção.

### E-DAD-07 — E-03: exemplos de contrato validados contra os próprios esquemas
- Tipo: comando (execução)
- Fonte/local: `scripts\e03_exemplos_contrato.py`; log `logs\e03_exemplos_contrato_sqlite.log`; artefatos `docs/api/openapi.yaml`, `docs/events/asyncapi.yaml`, `tests/fixtures/api_v1_baseline.json`
- Comando e ambiente: `& $py scripts\e03_exemplos_contrato.py`. Leitura por `yaml.safe_load` com normalização de `date` para texto ISO. `jsonschema` `Draft202012Validator` com `FormatChecker()`; referências resolvidas por `Registry`.
- Resultado observado:
  - `OpenAPI 3.1.0 | artefato igual ao gerado pela aplicação: True`.
  - `OpenAPI: exemplos verificados=278 invalidos=11`. Exemplos com `billing.amount` numérico onde o esquema exige string (`POST /contracts/drafts` created/replayed; `POST /contracts/{id}/activate` activated/replayed). Exemplos sem campos nulos obrigatórios (`slaHours`, `dueAt`, `fromStatus`, `owner`, `overdueSince`, `contractId`) nas operações `entitlement`, `tickets` (pending), `history`, `reconcile` (rejected) e nos componentes `InvoiceResponse`, `PaymentResultResponse`, `ReservationResponse`.
  - `AsyncAPI: exemplos verificados=7 invalidos=0`.
  - Envelope com `causationId=null` e com uuid: ambos `válido`.
  - `Money.amount=0.07`, `19.99` e `1234567.89`: `is not a multiple of 0.01`. `2500.0` e `100.1`: válido.
  - Testes sem `FormatChecker`: `tests/test_contracts_and_architecture.py` e `tests/test_t15_atendimento.py` (`False`).
  - Baseline: `approved_ADR003` (`InvoiceResponse.status` e `PaymentInput.amount`) registrado em `ADR-003`. `approved_security` (`GET /metrics`, HTTPBearer): `ADR que cita o caminho = NENHUM`.
- Limitações: a validação cobre exemplos do artefato, não as respostas reais (estas estão em E-DAD-08 e E-DAD-13). A referência de exceção ao ADR foi verificada por texto (`PARTIALLY_PAID`, "duas casas" em ADR-003).

### E-DAD-08 — E-04: valores monetários na API v1 (SQLite)
- Tipo: comando (execução)
- Fonte/local: `scripts\e04_dinheiro.py`; log `logs\e04_dinheiro_sqlite.log`; PG pronto com `ADB_URL` (não executado)
- Comando e ambiente: `& $py scripts\e04_dinheiro.py` (TestClient, SQLite `iso-dad\tmp\e04.db`).
- Resultado observado:
  - Drafts: `0.001` → 422 (`decimal_max_places`); `0.005` → 422; `2500.10` → 201, `billing.amount` devolvido como string `"2500.1"`; `1e12` → 201; `1e15` → 201.
  - Reservas: `0.001` e `0.005` → 422; `1e12` e `1e15` → 201.
  - Pagamentos sobre fatura de 100.10: `0.001`, `0.005` → 422 (`decimal_max_places`); `1e12` → 422 (`decimal_whole_digits`); `1e15` → 422 (`decimal_max_digits`); `0.01` → 201; `100.09` → 201; `fatura final: PAID`.
  - Valores gravados em `contracts_contracts`: `2500.1`, `1000000000000`, `1000000000000000`, `100.1`.
- Limitações: no SQLite não há limite de precisão, por isso `1e12` e `1e15` são aceitos. No PostgreSQL com `Numeric(14,2)` (12 dígitos inteiros), esses drafts e reservas falham no INSERT (previsão por inspeção e por 01/10: A3-06 e `uvicorn_pg_valid.log`), não executado localmente. Pagamentos não chegam ao INSERT com valor acima do limite (422 na entrada). A resposta de draft devolve `amount` como string, enquanto `GET /contracts/{id}` devolve número (ver E-DAD-07 e E-DAD-13).

### E-DAD-09 — E-05: broker RabbitMQ configurado e fora do ar (porta fechada)
- Tipo: comando (execução)
- Fonte/local: `scripts\e05_broker_fechado.py`; log `logs\e05_broker_fechado_sqlite.log`; `docker-compose.yml:6` (`RABBITMQ_URL` definido); `render.yaml` (sem `RABBITMQ_URL`)
- Comando e ambiente: `& $py scripts\e05_broker_fechado.py`; `settings.rabbitmq_url = amqp://guest:guest@127.0.0.1:1/%2F` em tempo de execução; SQLite `iso-dad\tmp\e05.db`.
- Resultado observado:
  - Controle sem broker: `{'processed': 1, 'failed': 0}`; efeitos: faturas 1, processos 1, inbox 2, auditoria finance 1.
  - Com broker fora do ar: `despacho 1 ... http=200 corpo={'processed': 0, 'failed': 1} tempo=2.29s`; `despacho 2 ... tempo=2.19s`; `despacho 3 ... tempo=2.18s`. Após o 3º: evento novo `FAILED`, `attempts=3`, motivo `'Falha no despacho do evento; consulte a correlação e reprocesse após corrigir a causa'`. Efeitos do evento novo: nenhum (faturas continuam 1, processos 1).
  - Log de falha: `errorType: AMQPConnectionError` com `eventId`.
  - Com o broker desligado: `novo evento com broker desligado: {'processed': 1, 'failed': 0}`.
- Limitações: porta fechada (recusa imediata), não host sem resposta (01/10: 10–15 s por evento). Fila cheia e recusa (`nack`) exigem RabbitMQ real: não executado localmente; cobertura pela CI (ver E-DAD-16 e E-DAD-19).

### E-DAD-10 — E-07: evento venenoso, consumidor com erro de banco e reprocessamento (SQLite)
- Tipo: comando (execução)
- Fonte/local: `scripts\e07_evento_venenoso.py`; log `logs\e07_evento_venenoso_sqlite.log`; PG pronto com `ADB_URL` (não executado)
- Comando e ambiente: `& $py scripts\e07_evento_venenoso.py`; SQLite `iso-dad\tmp\e07.db`.
- Resultado observado:
  - A (exceção Python após auditoria): `ciclo 1 ... veneno=PENDING/tentativas=1 | saudavel=PUBLISHED`; `ciclo 3 ... veneno=FAILED/tentativas=3`; `ciclo 4 ... {'processed': 0, 'failed': 0}`; `auditoria do veneno gravada=0 | inbox do veneno=0 | auditoria saudável=1`.
  - B (IntegrityError real, `NOT NULL`): mesmo padrão; `auditoria do veneno gravada=0 | inbox do veneno=0 | auditoria saudável=1`.
  - C (faturamento final sem fatura inicial, regra real de Finance): `status=FAILED tentativas=3`.
  - D (`1e20` em `ContractActivated.v1`): `ciclo 1 {'processed': 1, 'failed': 0}`, `PUBLISHED`; fatura gravada com `1e+20` (SQLite aceita).
  - Reprocessamento: `200 PENDING`; `integration_audit reprocess_event details = {"previousAttempts": 3}`.
- Limitações: o DataError de PostgreSQL (cenário D em 01/10) não é reproduzível no SQLite. Em PG, o roteiro com `ADB_URL` deve mostrar `FAILED` e os saudáveis `PUBLISHED`; não executado. Cobertura de PG para o erro de banco: teste `test_outbox_recupera_sessao_apos_erro_sql_e_continua` (E-DAD-16).

### E-DAD-11 — E-08: requisições paralelas por HTTP com mesma chave, chaves diferentes e concorrência do despacho (SQLite, uvicorn 18102)
- Tipo: comando (execução)
- Fonte/local: `scripts\e08_cliente_paralelo.py`; logs `logs\e08_cliente_paralelo_sqlite.log`, `logs\e08_uvicorn_stdout.log`, `logs\e08_uvicorn_stderr.log`
- Comando e ambiente: PowerShell: `Start-Process` do `uvicorn archcorp.main:app --host 127.0.0.1 --port 18102` (cwd `iso-dad`, `DATABASE_URL` SQLite `iso-dad\tmp\e08.db`), cliente `scripts\e08_cliente_paralelo.py` com barreira, `Stop-Process` ao final. Porta 18102 sem escuta depois (verificado).
- Resultado observado:
  - S1 reserva, mesma chave, 3 simultâneas: `[(201,'false'), (500,...), (500,...)]`; `reservas gravadas [(1,)]`. Sem replay.
  - S2 reserva sem chave, 3 simultâneas: `[(500,...), (500,...), (201,'false')]`; `reservas gravadas [(1,)]`.
  - S3 chamado, mesma chave, 2 simultâneas: `[(201,'true'), (201,'false')]`; `chamados gravados [(1,)]` (replay correto).
  - S4 ativação, mesma chave, 2 simultâneas: `[(200,'false'), (200,'true')]`; `ContractActivated.v1 = [(1,)]`.
  - S5 ativação, chaves diferentes, 2 simultâneas: `[(200,'false'), (500,...)]`; `ContractActivated.v1 = [(1,)]`.
  - S6 resolução sem chave, 2 simultâneas: `[(409,'conflict'), (200,'false')]`; `TicketResolved.v1 = [(1,)]`.
  - S7 dois despachos simultâneos com pendentes: `[(500,...), (200,None)]`; `faturas duplicadas []`; `inbox duplicada []`; `status da outbox [('PUBLISHED', 7, 0)]`.
  - S8 pagamentos 1600 + 1600 sobre fatura de 2500: `[(500,...), (201,'false')]`; `soma gravada [(1600,)]`; `status PARTIALLY_PAID`.
  - S9 pagamentos com a mesma referência e chaves diferentes: `[(201,'true'), (201,'false')]`; `pagamentos com a referência = [(1,)]`.
  - Log do uvicorn: 4 `"Erro não tratado"` em `/contracts/reservations`, 1 em `/activate`, 1 em `/outbox/dispatch`, 1 em `/payments`; a única causa registrada é `dispatch_event ... "Falha ao registrar tentativa de despacho; lote interrompido" errorType: OperationalError/OperationalError`.
- Limitações: SQLite serializa escritas por arquivo. Os 500 são exceções não tratadas e o tipo não está nos logs; a inferência de bloqueio (`database is locked`) é a causa provável, confirmada só no despacho. `IntegrityError` seria convertido em 409 pelo handler de `errors.py`, então não é a causa dos 500. Os resultados de PG (409 esperado para a mesma chave, duplicata esperada para chaves diferentes e reserva sem chave duplicada) não foram executados: o roteiro aponta para PG com `DB_URL` e `uvicorn` com `DATABASE_URL` de PG descartável.

### E-DAD-12 — E-09: escopo da chave, prazo do ONBOARDING, datas sem fuso e data local (SQLite)
- Tipo: comando (execução)
- Fonte/local: `scripts\e09_chave_tempo.py`; log `logs\e09_chave_tempo_sqlite.log`
- Comando e ambiente: `& $py scripts\e09_chave_tempo.py`; relógio de `archcorp.workflow.service` e data de `archcorp.contracts.service` substituídos em instância para o teste (restaurados depois).
- Resultado observado:
  - a) `admin abre chamado` → 201 `replay=false`; `suporte repete chave e corpo` (token `demo-support`) → 201 `replay=true` com o mesmo `ticketId`; `mesma chave, descrição diferente` → 409 `IDEMPOTENCY_CONFLICT`.
  - b) ONBOARDING sem atraso (occurredAt = despacho = 2026-10-19T10:00Z): `dueAt=2026-10-22T10:00:00`. Com despacho 10 h depois (occurredAt 10:00Z, despacho 20:00Z): `dueAt=2026-10-22T20:00:00`.
  - c) `support dueAt` com `Z` (`2026-10-19T19:17:21.035376Z`, serviço usa `iso_utc`); `operations audit.occurredAt` sem fuso (`2026-10-19T11:17:10.516691`); `workflow processes (processType, dueAt)` sem fuso: `ONBOARDING 2026-10-22T11:17:18.685397`, `TICKET_RESOLUTION 2026-10-19T19:17:21.035376`, `ONBOARDING 2026-10-22T10:00:00`, `ONBOARDING 2026-10-22T20:00:00`.
  - d) encerramento sem `endsOn` com data local simulada 2026-10-18 (UTC 2026-10-19): `"endsOn": "2026-10-18"`.
- Limitações: o relógio é simulado. A tese de (b) não depende do fuso do teste: o código usa `datetime.now` no despacho (`workflow/service.py:42`). Em (d), a demonstração mostra que o valor vem do relógio local; o fuso real da máquina não foi alterado.

### E-DAD-13 — E-10 partes A e B: coerência de códigos de erro e cenários reais x OpenAPI
- Tipo: comando (execução) e inspeção
- Fonte/local: `scripts\e10_codigos_consultas.py`; log `logs\e10_codigos_consultas_sqlite.log`
- Comando e ambiente: `& $py scripts\e10_codigos_consultas.py`; SQLite `iso-dad\tmp\e10.db`; regex sobre `src/`, `tests/` e o OpenAPI lido.
- Resultado observado (parte A): códigos em `src` e OpenAPI, sem testes que afirmem `code`: `SERVICE_UNAVAILABLE`, `UNAUTHORIZED`, `BAD_REQUEST`; `INTERNAL_ERROR` no código e não no OpenAPI (`só no código: ['INTERNAL_ERROR', '_']`; `_` é artefato do regex).
- Resultado observado (parte B), cenário: observado x documentado para a mesma operação:
  - B1 rascunho com cliente inexistente → 422 `BUSINESS_RULE_VIOLATION` (documentado: sim, 422).
  - B2 reserva com cliente inexistente → 404 `NOT_FOUND`. Mesma condição, status diferente de B1.
  - B3 reconciliar OPEN → 409 `INVALID_STATE` (documentado).
  - B4 resolver resolvido → 409 `CONFLICT` (documentado).
  - B5 moeda diferente → 422 `VALIDATION_ERROR` (documentado).
  - B6 acima do saldo → 409 `CONFLICT` (documentado).
  - B7 e-mail duplicado → 409 `CONFLICT` (documentado).
  - B8 encerrar rascunho → 409 `INVALID_STATE`; status documentado (409), mas o código não aparece no OpenAPI da operação (`code no OpenAPI=False`).
  - B9 legado inexistente → 404 `NOT_FOUND` (documentado).
  - B10 chave reutilizada em outra reserva → 409 `IDEMPOTENCY_CONFLICT`; o código não aparece no OpenAPI da operação (`False`).
  - B11 tarefa em processo inexistente → 404 `NOT_FOUND` (documentado).
- Limitações: o critério de AUD-40 original era INTEGRACOES.md (documentação, fora do escopo). Aqui a coerência é entre código, OpenAPI e testes, conforme o briefing.

### E-DAD-14 — E-10 parte C: consultas por listagem (N+1) e índices reais (SQLite)
- Tipo: comando (execução)
- Fonte/local: mesmo roteiro `scripts\e10_codigos_consultas.py`, parte C; log `logs\e10_codigos_consultas_sqlite.log`
- Comando e ambiente: contagem de `before_cursor_execute` no engine durante cada `GET` (TestClient); índices via `inspect(engine)` depois das migrações.
- Resultado observado:
  - `N=5 GET /finance/invoices: linhas=6 comandos_sql=8`; `N=25 GET /finance/invoices: linhas=26 comandos_sql=28` (uma consulta de pagamentos por fatura).
  - `N=5 GET /support/tickets: comandos_sql=3`; `N=25 ...: comandos_sql=3` (owners em lote).
  - Índices: `finance_invoices` tem índice só em `customer_id` e unicidade `(contract_id, kind)`; sem índice em `status` e `due_date` (usados por `evaluate_overdue`, `finance/service.py:169-171`). `support_tickets` tem índices em `contract_id` e `customer_id`; sem índice em `status` (usado por `reconcile_pending`, `support/service.py:190-191`). `integration_outbox` tem índice em `status`, `event_type` e `correlation_id`. `contracts_contracts` tem índice em `customer_id`.
- Limitações: SQLite com volume pequeno; o custo real em PostgreSQL não foi medido. Os índices são lidos do SQLite após as migrações; o modelo é o mesmo em PostgreSQL.

### E-DAD-15 — E-12: migrações em SQLite (upgrade com dados, downgrade, bloqueio FINAL, carimbo, política AST, cabeça)
- Tipo: comando (execução)
- Fonte/local: `scripts\e12_migracoes.py`; log `logs\e12_migracoes_sqlite.log`; PG coberto por `tests/test_migration_convergence.py` (job postgresql da CI, ver E-DAD-16)
- Comando e ambiente: `& $py scripts\e12_migracoes.py`; bancos em `iso-dad\tmp\e12_*.db`.
- Resultado observado:
  - A: upgrade a partir de `0001_baseline`, `0002_customer_active`, `0003_contract_closing`, `0004_finance_lifecycle`, `0004_support_sla_history` e `0005_merge_finance_support` com dados. Em todos: `cabeca=('0005_merge_finance_support',)`, `divergencias_modelo=0`, dados preservados (1 de cada tabela). Fatura seeded com pagamento: `PARTIALLY_PAID` quando a 0004 financeira roda na subida; `OPEN` quando a semente é inserida depois da 0004 (esperado: a migração não reprocessa dados já migrados).
  - B: `downgrade -> 0003`, `-> 0002`, `-> 0001`, `-> base`: todos OK. Subida ao head: `cabeca=('0005_merge_finance_support',)`, `divergencias_modelo=0`.
  - C: com fatura `FINAL`, `downgrade 0003` → `RuntimeError: Downgrade da 0004 bloqueado: 1 fatura(s) FINAL`; faturas inalteradas.
  - D: sem `alembic_version` em `0001` e em `0002`: `upgrade_to_head` → OK nos dois, `divergencias_modelo=0`.
  - E: AST de `upgrade`: `0004_finance_lifecycle.py: {'execute UPDATE': 1, 'drop_constraint': 1}`; os demais sem operações destrutivas; `cabeças: ['0005_merge_finance_support']`. Confere com `MIGRATION_EXCEPTIONS` de `tests/test_foundation.py:135-139` e com ADR-003 §1.
- Limitações: no SQLite, `batch_alter_table` recria tabelas e pode mascarar falhas de PostgreSQL. O caso D (AUD-33) falha em PostgreSQL segundo 01/10 (`evidencias/agente3/logs/migracoes_pg.log`, caso 5); não reproduzido aqui porque o SQLite passa. O roteiro de PG é `evidencias/agente3/scripts/mig_exp.py` (caso 5), reaproveitado e não executado.

### E-DAD-16 — Logs da CI da run 39063148796 (leitura, `gh`)
- Tipo: log da CI (consulta externa, somente leitura)
- Fonte/local: `gh run view 39063148796 --repo Roger-Quinelato/projetoAplicado7 --job <id> --log`, filtrado para `logs\ci_<job>_run39063148796_filtro.log`
- Comando e ambiente: PowerShell, `gh` autenticado; apenas leitura.
- Resultado observado:
  - job `postgresql` (117485116770): `221 passed, 2 skipped, 1 warning in 43.83s`.
  - job `application` (117485116908): `213 passed, 10 skipped, 1 warning in 22.40s`.
  - job `rabbitmq` (117485117016): `20 passed, 1 warning in 0.99s`.
  - Skips: a configuração do job `postgresql` não define `TEST_RABBITMQ_URL`, então os 2 testes de `tests/test_rabbitmq_real.py` são os 2 skips (inferência pela configuração; o `-q` não lista o motivo). Na suíte local (E-DAD-17), os 10 skips do `application` são: 4 de `test_postgresql_concurrency.py`, 4 de `test_migration_convergence.py` (variante PostgreSQL) e 2 de `test_rabbitmq_real.py`.
- Configuração lida (inspeção de `.github/workflows/verify.yml`): job `postgresql` roda `pytest -q tests` com `TEST_DATABASE_URL` (linhas 12-34); job `rabbitmq` roda só `tests/test_rabbitmq_real.py` e `tests/test_reliability_regressions.py` (linhas 35-53); job `application` roda `pytest -q tests` no SQLite (linhas 54-66).
- Limitações: a CI é evidência do SHA `44b8325` apenas para o que os testes cobrem; não há teste de CI para ativação concorrente (AUD-10), reserva com chave repetida em paralelo (AUD-48) nem para a ordem de projeção (AUD-04).

### E-DAD-17 — Suíte dos arquivos da frente F-DAD em SQLite
- Tipo: comando (execução)
- Fonte/local: `logs\pytest_dad_sqlite.log`
- Comando e ambiente: `PYTHONPATH=iso-dad\src`, `Push-Location iso-dad`, `& $py -m pytest -q -p no:cacheprovider -rs` com `tests/test_reliability_regressions.py tests/test_flows.py tests/test_finance.py tests/test_t15_atendimento.py tests/test_migration_convergence.py tests/test_foundation.py tests/test_contracts_and_architecture.py tests/test_api_v1_compatibility.py tests/test_postgresql_concurrency.py tests/test_rabbitmq_real.py tests/test_public_database_security.py`. Variáveis `DATABASE_URL`, `TEST_DATABASE_URL`, `TEST_RABBITMQ_URL` removidas do ambiente.
- Resultado observado: `152 passed, 10 skipped, 1 warning in 32.84s`. Motivos dos skips: `test_migration_convergence.py:39` e `:57` (TEST_DATABASE_URL não configurada, 4 casos); `test_postgresql_concurrency.py:34,55,93,123` (Exige PostgreSQL real, 4); `test_rabbitmq_real.py:36,47` (Exige RabbitMQ real, 2).
- Relevância: Q-01 verificado (`test_t15_atendimento.py:454` e `:472`, passaram); `test_foundation.py` (AST das migrações) passou; `test_api_v1_compatibility.py` passou.
- Limitações: a suíte completa é de F-QUA; aqui só os arquivos ligados à F-DAD.

### E-DAD-18 — Inspeção: contrato de eventos e critérios do AGENTS.md
- Tipo: inspeção de código e documentação de regra (leitura)
- Fonte/local: `docs/events/asyncapi.yaml:5-12` (descrição: "pode publicar uma cópia no RabbitMQ local ... Mensagem sem rota ou recusada conta como falha da tentativa"); `docs/events/asyncapi.yaml:393-399` (`Money`, `multipleOf: 0.01` na linha 397); `AGENTS.md:74` ("não aplique 'última escrita vence' sem uma decisão explícita"), `:82-83` (envelope obrigatório; datas ISO 8601 UTC; valores monetários em decimal), `:91-93` (Idempotency-Key em comandos repetíveis; retentativa só para transitórios com backoff exponencial e jitter; falhas permanentes para fila de erro com motivo e tentativas).
- Comando e ambiente: leitura e `Grep` com número de linha, na cópia de execução e no worktree (somente leitura).
- Resultado observado: o contrato de eventos declara o broker como cópia opcional e registra que recusa conta como falha da tentativa. Não diz que a cópia deve bloquear o consumo interno. AGENTS.md exige backoff com jitter para retentativa (linhas 91-93). A exigência de auditoria do solicitante no reprocessamento vem da auditoria de 01/10 (ADR-001, regra 12); esse ADR não foi lido nesta frente.
- Limitações: AGENTS.md e ADRs são critério, não objeto de reescrita. O texto de documentação não foi avaliado como redação (fora do escopo).

### E-DAD-19 — Inspeção: exceções do baseline v1, ADRs e configuração de implantação
- Tipo: inspeção de código e documentação
- Fonte/local: `tests/fixtures/api_v1_baseline.json` (`approved_ADR003`, `approved_security` "GET /metrics"); `docs/adr/ADR-003-...md` §1 (exceção à regra aditiva) e §2 (tabela de exceções na v1); `docs/adr/ADR-005-...md:12-13` ("`main.py` mantém ... métricas ..." sem decisão de autenticação); `tests/test_foundation.py:135-139` (`MIGRATION_EXCEPTIONS`); `docker-compose.yml:6` (`RABBITMQ_URL`); `render.yaml` (`healthCheckPath`, `PUBLIC_DEMO`, sem `RABBITMQ_URL`).
- Comando e ambiente: leitura; `Select-String` de `RABBITMQ|PUBLIC_DEMO` nos dois arquivos de implantação.
- Resultado observado: as duas exceções de `approved_ADR003` estão em ADR-003. A exceção `approved_security` de `GET /metrics` não tem ADR que a registre (ADR-005 trata a composição de métricas, não a exigência de papel). O broker é configurado no compose e não no Render.
- Limitações: o `_motivo` do baseline cita "#40" (PR de segurança), mas não há ADR.

### E-DAD-20 — Inspeção: testes de contrato e de envelope
- Tipo: inspeção de código de teste
- Fonte/local: `tests/test_contracts_and_architecture.py:21-23` (`asyncapi_validator` sem `format_checker`), `:174-180` (exemplos AsyncAPI validados), `:183-204` (envelopes publicados, asserta `Z` mas não valida formato `date-time`), `:207-227` (teste OpenAPI só verifica presença de exemplos); `tests/test_t15_atendimento.py:564` (envelopes do chamado, sem `FormatChecker`).
- Comando e ambiente: leitura com número de linha.
- Resultado observado: nenhum teste valida cada exemplo do OpenAPI; a validação AsyncAPI não usa `FormatChecker`; nenhum teste usa o valor 19.99 em `ContractActivated.v1`. Por isso AUD-20, AUD-21 e AUD-41 não são detectados pela CI.
- Limitações: inspeção; o efeito foi medido em E-DAD-07.

### E-DAD-21 — Inspeção: causationId e relógio do banco
- Tipo: inspeção de código
- Fonte/local: `src/archcorp/integration/service.py:153-157` (`enqueue` com `causation_id=None` por padrão); `src/archcorp/integration/models.py:20` (`occurred_at` default `utcnow`), `:22` (`causation_id`), `:36` (`envelope()` com `causationId`).
- Comando e ambiente: `Grep` por `causation` em `src/archcorp` (sem chamadas com `causation_id=`).
- Resultado observado: nenhuma chamada de `enqueue` passa `causation_id`; o campo sai sempre `null` (AUD-19/A2-19 de 01/10 continua).
- Limitações: `null` é válido pelo AsyncAPI (`type: [string, 'null']`), então é dívida, não violação.

### E-DAD-22 — Reaproveitamento dos roteiros de 01/10
- Tipo: inspeção (reuso)
- Fonte/local: `evidencias/agente2/exp/e09_ordem_contrato.py` (base de E-02 e de E-03); `evidencias/agente2/exp/e11_exemplos_openapi.py` (base de E-03, parte OpenAPI); `evidencias/agente2/exp/e10_money.py` e `e04_falhas.py` (base de E-04 e E-07); `evidencias/agente2/exp/e12_tx_corrida.py` (base de E-01); `evidencias/agente3/scripts/conc_exp.py` (base de E-08); `poison_exp.py` (base do cenário D de E-07 em PG); `rabbit_exp.py` e `rabbit_timing.py` (base de E-05); `mig_exp.py` (base de E-12 e do caso 5 em PG). Novos: `e09_chave_tempo.py`, `e10_codigos_consultas.py` (N+1 e códigos).
- Comando e ambiente: leitura dos scripts de 01/10 (sem executá-los na cópia antiga; o `harness.py` original usava caminhos `/tmp/claude-0/...`).
- Resultado observado: os roteiros novos seguem os de 01/10, mas usam o código de 44b8325 e caminhos de `iso-dad`.
- Limitações: os scripts de 01/10 apontam para caminhos do ambiente anterior; não foram reexecutados.

### E-DAD-23 — Inspeção: correção de Q-01 (prazo do Workflow) e resíduo do ONBOARDING
- Tipo: inspeção de código e de histórico
- Fonte/local: `src/archcorp/workflow/service.py:40-42` (`handle_contract_activated` usa `datetime.now(timezone.utc) + timedelta(hours=72)`); `:45-59` (`handle_ticket_opened` usa `dueAt` publicado); commit `d6c8924` (mensagem: "Onboarding (72 h) inalterado").
- Comando e ambiente: `git -C WT show --stat d6c8924` e leitura das linhas.
- Resultado observado: TICKET_RESOLUTION corrigido (usa `dueAt`, com 24 h provisórias para chamado pendente); ONBOARDING continua no relógio do despacho. Testes `test_t15_atendimento.py:454` e `:472` passam (E-DAD-17).
- Limitações: inspeção do código; o efeito do ONBOARDING foi medido em E-DAD-12 (b).

### E-DAD-24 — Roteiros "PG pronto" (não executados) e cobertura por CI
- Tipo: inspeção (roteiros preparados)
- Fonte/local: `scripts\e01_concorrencia.py`, `scripts\e04_dinheiro.py`, `scripts\e07_evento_venenoso.py` (via `ADB_URL`); `scripts\e08_cliente_paralelo.py` (uvicorn com `DATABASE_URL` de PG e `DB_URL`); cobertura de CI: `tests/test_postgresql_concurrency.py` (4 testes, job postgresql) e `tests/test_migration_convergence.py` (job postgresql).
- Comando e ambiente: não executados (sem PostgreSQL local). Para rodar: `ADB_URL=postgresql+psycopg://USUARIO:SENHA@127.0.0.1:5432/BANCO_TESTE` com banco descartável.
- Resultado observado: os roteiros estão prontos e apagam apenas o banco indicado. Não há script de RabbitMQ real além de `tests/test_rabbitmq_real.py` (CI, job rabbitmq).
- Limitações: nenhuma afirmação de PostgreSQL é feita como executada nesta frente; ver `linha_de_base.md` para o estado de cada item.
