# Achados — Agente 2 (Arquitetura e comportamento)

Referência: `3a3d8bd`. Ordenados por severidade. "Falha injetada" = handler substituído em memória para simular falha de consumidor; o defeito está no tratamento pelo despachante, não na injeção.
Nenhum achado classificado como **crítico** (não houve perda de fato confirmado na outbox nem duplicação de cobrança/processo nos cenários executados).

---

### A2-01 — Erro de banco em consumidor transforma o evento em "veneno": 500 em loop, sem `FAILED`, outbox bloqueada
- Natureza / Severidade / Confiança: defeito demonstrado (falha injetada) / **alta** / alta
- Esperado: AGENT.md "Confiabilidade e erros" (falha permanente encaminhada com motivo, tentativas e correlação; nunca ocultar falhas); ADR-001 regra 8; RF-07; critério T13 (reentrega/falha).
- Observado: um `IntegrityError` (ou qualquer erro de `flush`) dentro de um handler deixa a sessão em estado inválido; o `session.commit()` do ramo `except` levanta `PendingRollbackError`, a rota responde 500, `attempts` não incrementa, `last_error` fica vazio, o evento nunca chega a `FAILED` (não aparece em `/integration/failures`) e todos os eventos posteriores ficam presos em `PENDING`.
- Localização: `src/archcorp/integration/service.py:24-45` (commit em `:45` sem `rollback`/savepoint).
- Reprodução: `exp/e04_falhas.py` (cenário B) e `exp/e05_bloqueio.py` (B2) — 4 despachos → `500`, outbox `('ContractActivated.v1','PENDING',0,'')`, `CustomerUpdated.v1` posterior permanece `PENDING`.
- Impacto: F2/F3 param silenciosamente; o operador não vê a falha na API de falhas. Gatilhos realistas: corrida entre despachantes (A2-04), violação de restrição, erro SQL em PostgreSQL (transação abortada).
- Evidências: E2-10, E2-11
- Correção proposta: processar cada consumidor dentro de `session.begin_nested()` (savepoint) ou sessão própria; no `except`, `session.rollback()` e registrar `attempts/last_error` numa transação separada; incluir `eventId` e tipo da exceção em `last_error` quando `str(exc)` for vazio. Aceite: teste que injeta `IntegrityError` mostra `attempts` crescente, `FAILED` após `RETRY_LIMIT`, item em `/integration/failures` e eventos posteriores processados no mesmo despacho.

### A2-02 — RabbitMQ configurado e indisponível marca eventos como falhos mesmo com consumidores internos concluídos; motivo vazio; ~10 s por evento; cópia sem fila é descartada
- Natureza / Severidade / Confiança: defeito demonstrado (porta fechada e host sem resposta) + risco (descarte, inspeção) / **alta** / alta (descarte: média)
- Esperado: README/ESTADO ("RabbitMQ recebe cópia opcional"); AGENT.md (timeout em chamadas externas; retentativa só para erros transitórios; motivo da falha preservado); RNF-04.
- Observado: `_publish_broker` roda dentro do mesmo `try` dos consumidores; falha do broker incrementa `attempts` e, após 3 despachos, todo evento (de qualquer tipo) vira `FAILED` com `reason: ""`, embora fatura/processo/projeção já tenham sido gravados e a inbox registrada. Sem timeout explícito, cada evento custa ~10 s (`dispatch blackhole (30.1s)` para 3 eventos) e abre uma conexão nova. Não há `queue_declare/queue_bind` nem publisher confirms: no Compose padrão (`RABBITMQ_URL` definido), mensagens publicadas na exchange topic sem fila vinculada são descartadas pelo broker.
- Localização: `src/archcorp/integration/service.py:32,48-64`; `docker-compose.yml` (`RABBITMQ_URL`).
- Reprodução: `exp/e04_falhas.py` (cenário C) e `exp/e05_bloqueio.py` (C2).
- Impacto: na configuração de demonstração padrão, uma indisponibilidade do broker torna a lista de falhas enganosa (falha de "integração" com efeitos de negócio concluídos) e a requisição de despacho pode exceder timeouts de proxy; a "cópia" no broker não é observável por nenhum consumidor.
- Evidências: E2-12
- Correção proposta: separar o estado de entrega interna do de publicação externa (ex.: `broker_status`/segunda outbox), definir `socket_timeout`/`blocked_connection_timeout` curtos, reutilizar conexão por despacho, declarar fila de auditoria ou documentar que a cópia é descartada; registrar `type(exc).__name__` quando a mensagem for vazia. Aceite: com broker indisponível, eventos internos ficam `PUBLISHED` (ou estado equivalente) e a falha de broker aparece com motivo não vazio; despacho de N eventos com broker fora termina em tempo limitado e documentado.

### A2-03 — Reprocessamento de evento antigo sobrescreve projeção mais nova ("última escrita vence")
- Natureza / Severidade / Confiança: defeito demonstrado (falha transitória injetada) / **alta** / alta
- Esperado: AGENT.md ("não aplique última escrita vence"; "reprocessamento ... incapaz de duplicar efeitos"); RF-05; RF-07; INTEGRACOES "Fluxo auxiliar".
- Observado: `CustomerUpdated.v1` (v1) falha 3× e vai a `FAILED`; v2 é aplicado; reprocessar v1 grava "Nome Versao 1" na projeção de Contracts, enquanto o CRM (fonte oficial) mantém "Nome Versao 2".
- Localização: `src/archcorp/contracts/service.py:144-147` (UPDATE incondicional); `src/archcorp/main.py:547-556` (reprocessa sem checar eventos mais novos do mesmo agregado).
- Reprodução: `exp/e09_ordem_contrato.py`.
- Impacto: projeção divergente da fonte oficial sem registro de inconsistência; o mesmo padrão ameaça qualquer consumidor de estado (ex.: `TicketEntitlementReconciled.v1`).
- Evidências: E2-15
- Correção proposta: incluir versão/`occurredAt` do agregado no payload e aplicar somente se mais novo (guardar `customer_version`/`updated_at` na projeção); registrar divergência em auditoria. Aceite: teste "falha v1 → aplica v2 → reprocessa v1" mantém v2 e registra o descarte.

### A2-04 — Pagamento aceita frações de centavo e registra pagamentos de valor efetivo 0,00
- Natureza / Severidade / Confiança: defeito demonstrado / **alta** / alta (SQLite); comportamento em PostgreSQL inferido
- Esperado: AGENT.md/RNF-01 (valores monetários em decimal com moeda explícita); critério T12 (pagamento simulado); `INTEGRACOES.md` ("decimal positivo").
- Observado: `PaymentInput.amount` não tem `decimal_places=2`; `0.001` e `0.004` retornam `201`; a listagem mostra `amount 0.0`; o saldo é comparado com o valor não arredondado e depois lido arredondado, de modo que `100.10` quita uma fatura de 100.10 que já tinha 0.005 "pago". SQLite grava `real` (0.001, 0.004); em PostgreSQL `numeric(14,2)` arredondaria 0.005 → 0.01, gerando resultado diferente entre ambientes. A moeda do pagamento não exige padrão de 3 letras maiúsculas.
- Localização: `src/archcorp/finance/routes.py:42`, `:129-135`; `src/archcorp/finance/models.py` (`Numeric(14,2)`).
- Reprodução: `exp/e07_pagamentos.py`.
- Impacto: livro de pagamentos com lançamentos nulos e soma bruta ≠ soma exibida; regra de quitação dependente do banco.
- Evidências: E2-13
- Correção proposta: `Field(gt=0, decimal_places=2)` e `pattern="^[A-Z]{3}$"`; quantizar antes de comparar. Aceite: `0.001` → 422; teste de pagamento parcial com centavos (100.10 = 100.09 + 0.01) passa em SQLite e PostgreSQL.

### A2-05 — Despacho sem exclusão mútua: dois despachos processam o mesmo evento
- Natureza / Severidade / Confiança: defeito demonstrado (SQLite, intercalação forçada) / média / alta (SQLite); PostgreSQL pendente (P-01)
- Esperado: RNF-02 e RNF-08 ("consumidores idempotentes podem ser replicados"); AGENT.md (idempotência).
- Observado: `dispatch_pending` seleciona `PENDING` sem lock/lease/`FOR UPDATE SKIP LOCKED`; com duas sessões, o handler de Finance executou 2×; a duplicidade foi barrada apenas por `uq_invoice_contract`, e o segundo despacho terminou em `PendingRollbackError` (500).
- Localização: `src/archcorp/integration/service.py:22`.
- Reprodução: `exp/e06_concorrencia.py`.
- Impacto: dois cliques no botão "Despachar eventos" ou duas instâncias geram 500 e podem publicar cópias duplicadas no broker; a escala horizontal declarada não é segura.
- Evidências: E2-11
- Correção proposta: reivindicar eventos com `UPDATE ... SET status='DISPATCHING', locked_until=...` ou `SELECT ... FOR UPDATE SKIP LOCKED` (PostgreSQL) e serializar em SQLite. Aceite: teste concorrente com 2 despachantes → handler executado 1×, nenhum 500.

### A2-06 — Ativações concorrentes com chaves diferentes gravam dois `ContractActivated.v1`
- Natureza / Severidade / Confiança: defeito demonstrado (SQLite, intercalação forçada) / média / alta (SQLite)
- Esperado: DDD ("contrato só pode ser ativado uma vez"); RF-03; critério T09/T13 ("sem duplicidade").
- Observado: duas chamadas `activate` (RC-1, RC-2) concluem com `eventId` distintos; 2 eventos para o mesmo contrato; `dispatch -> processed 2`. Faturas/processos não duplicaram (restrições únicas), mas dois fatos de ativação existem na outbox/broker e duas auditorias de sucesso.
- Localização: `src/archcorp/contracts/service.py:62-87` (verificação de estado sem bloqueio ou versão).
- Reprodução: `exp/e12_tx_corrida.py`.
- Impacto: consumidores externos (broker) não deduplicam por `eventId` distinto.
- Evidências: E2-18
- Correção proposta: `UPDATE contracts_contracts SET status='ACTIVE' WHERE contract_id=:id AND status='DRAFT'` com checagem de linhas afetadas (ou `with_for_update()`), ou restrição única de ativação por contrato. Aceite: teste concorrente → 1 evento.

### A2-07 — Falha parcial: efeito do consumidor que falhou é confirmado (sem rollback/savepoint)
- Natureza / Severidade / Confiança: defeito demonstrado (falha injetada) / média / alta
- Esperado: AGENT.md (rollback em falha; "Nunca capture uma exceção sem ... convertê-la em resultado tratado"); FLUXOS F2.
- Observado: handler que grava processo e depois falha → processo/tarefa persistidos sem registro na inbox; o evento permanece `PENDING`. A ausência de duplicação no retry depende de cada handler ser "check-then-insert", não do despachante.
- Localização: `src/archcorp/integration/service.py:25-45`.
- Reprodução: `exp/e04_falhas.py` (cenário A).
- Impacto: qualquer handler futuro não naturalmente idempotente duplicará efeitos em retentativa.
- Evidências: E2-09
- Correção proposta: mesma de A2-01 (savepoint por consumidor). Aceite: após falha injetada, nenhum efeito do consumidor que falhou fica persistido.

### A2-08 — OpenAPI: 11 de 261 exemplos inválidos contra o próprio schema; dinheiro como string em uns endpoints e número em outros
- Natureza / Severidade / Confiança: defeito demonstrado (contrato) / média / alta
- Esperado: critério T06 ("exemplos válidos"); RNF-01; AGENT.md (decimal com moeda).
- Observado: `ContractDraftResponse`/`ContractActivationResponse` serializam `billing.amount` como string (`"2500.0"`, `"19.99"`), mas os exemplos usam número; `GET /contracts/{id}`, `POST /close`, faturas e pagamentos usam número `float`. Exemplos com `null` perdem campos obrigatórios (`slaHours`, `dueAt`, `contractId`) na exportação. Os testes só verificam presença de exemplos, não validade.
- Localização: `src/archcorp/schemas.py:110-113, 230-250`; `src/archcorp/contracts/service.py:154`; `docs/api/openapi.yaml`.
- Reprodução: `exp/e11_exemplos_openapi.py`; `exp/e10_money.py`.
- Evidências: E2-04, E2-05
- Correção proposta: um único tipo monetário de saída (string decimal com 2 casas, ou número documentado) em todos os recursos; corrigir exemplos/nulos (usar `examples` sem `exclude_none` ou campos opcionais); adicionar teste que valide cada exemplo contra o schema. Aceite: script de validação de exemplos → 0 inválidos.

### A2-09 — AsyncAPI `Money.amount` (`number` + `multipleOf: 0.01`) rejeita valores comuns
- Natureza / Severidade / Confiança: defeito demonstrado (contrato) / média / alta
- Esperado: critério T06; RNF-01; teste "envelopes publicados validam contra AsyncAPI".
- Observado: envelope real com 19,99 → `19.99 is not a multiple of 0.01`; também 0,07 e 1.234.567,89. Os testes só usam 2500.
- Localização: `docs/events/asyncapi.yaml` (`components.schemas.Money`); produtor `contracts/service.py:154` (float).
- Reprodução: `exp/e09_ordem_contrato.py`, `exp/e10_money.py`.
- Evidências: E2-06
- Correção proposta: `amount` como string decimal (`pattern: ^\d+\.\d{2}$`) produzida por `money()`; incluir caso 19.99 no teste de envelope. Aceite: envelopes com 0.07/19.99/1234567.89 validam.

### A2-10 — Fronteiras: Contracts e Support importam modelo interno de Integration; composição lê/escreve outbox; testes de arquitetura cegos a isso
- Natureza / Severidade / Confiança: dívida técnica (violação de regra verificada por AST) / média / alta
- Esperado: AGENT.md ("É proibido acessar diretamente tabelas, classes internas ou repositórios de outro módulo"); ADR-001 regra 13; RNF-05.
- Observado: `contracts/service.py:11` e `support/service.py:9` importam `integration.models.IdempotencyRecord` e manipulam a tabela diretamente (contornando `IdempotencyStore`); `main.py:26,534-556,588-592` consulta e altera `OutboxEvent`/`AuditLog`. Os testes `test_modulos_de_negocio_nao_importam_models_de_outro_contexto` e `test_composicao_da_aplicacao_nao_le_modelos_dos_contextos` excluem `integration` e detectam só a forma `from archcorp.<ctx>.models import ...` (não detectam `from archcorp.crm import models`, `import archcorp.crm.models`, SQL textual, `Base.metadata.tables`, nem uso de `service` interno de outro contexto).
- Localização: arquivos citados; `tests/test_contracts_and_architecture.py:90-115`.
- Reprodução: `imports_ast.py` (E2-01) e `exp/e13_teste_arquitetura.py` (E2-19).
- Evidências: E2-01, E2-19
- Correção proposta: expor operações de idempotência/outbox/falhas como API pública de `integration` (ex.: `integration.public`); mover consultas de falhas/trilha para `integration`; ampliar o teste (todas as formas de import, incluir `integration`, proibir `text(` com prefixos de outros contextos) ou adotar `import-linter`. Aceite: teste ampliado passa e falha com os 7 trechos de E2-19.

### A2-11 — Arquitetura hexagonal apenas parcial
- Natureza / Severidade / Confiança: dívida técnica / média / alta
- Esperado: AGENT.md ("domínio e casos de uso não dependem de HTTP, banco, broker"); TO-BE.
- Observado: só `contracts/domain.py` é independente de framework; serviços e portas (`CustomerReader`, `ContractEntitlementPort`) recebem `sqlalchemy.orm.Session`; regras de negócio em rotas FastAPI com `HTTPException` (pagamento/quitação em `finance/routes.py:117-138`, resolução/atribuição em `support/routes.py:68-95`, transições de tarefa em `workflow/routes.py:125-142`); `finance/service.py` e `workflow/service.py` são apenas handlers; `integration/service.py` importa `pika` sem porta/adaptador; `main.py` (619 linhas) mistura composição com rotas de Contracts, Support e Integration.
- Evidências: E2-02, E2-21
- Correção proposta (incremental, sem microsserviços): casos de uso por contexto sem `HTTPException`; portas sem `Session` (unidade de trabalho injetada); adaptador `BrokerPublisher`; mover rotas de `main.py` para os routers dos contextos. Aceite: teste estático "nenhum `service.py`/`domain.py` importa `fastapi`" e "portas públicas não importam `sqlalchemy`".

### A2-12 — Encerramento do contrato não se propaga a Finance/Support e conclui a preparação de retirada com tarefas canceladas
- Natureza / Severidade / Confiança: meta futura declarada (Finance, T12) + risco (Support/Workflow) / média / alta
- Esperado: critério T09 (encerramento); T12; DDD (estado operacional coerente).
- Observado: após `ContractClosed.v1`, a fatura continua `OPEN` (pode virar `OVERDUE`), chamados `OPEN` do contrato permanecem abertos e resolvíveis, processos `TICKET_RESOLUTION` seguem ativos; o processo `ONBOARDING` vira `COMPLETED` com a tarefa `CANCELLED`.
- Localização: `src/archcorp/workflow/service.py:67-79`; `main.py:342`.
- Reprodução: `exp/e08_f3.py`, `exp/e07_pagamentos.py`.
- Evidências: E2-13, E2-14, E2-23
- Correção proposta: definir no ADR/TDD a regra de encerramento (fatura final, chamados abertos), usar estado `CANCELLED`/`CLOSED_BY_CONTRACT` para preparação não executada. Aceite: testes de encerramento cobrindo fatura e chamado aberto.

### A2-13 — Workflow sem máquina de estados de tarefa e sem retorno ao Support
- Natureza / Severidade / Confiança: defeito demonstrado / média / alta
- Esperado: critério T16 ("transições"); FLUXOS F3.
- Observado: qualquer transição é aceita (`OPEN→CANCELLED→IN_PROGRESS→OPEN`); tarefa `DONE` conclui o processo `TICKET_RESOLUTION` mas o chamado continua `OPEN` (não há evento de Workflow para Support); `POST /workflow/tasks` duplica tarefas sem chave; transições não são auditadas.
- Localização: `src/archcorp/workflow/routes.py:125-142`.
- Reprodução: `exp/e08_f3.py`.
- Evidências: E2-14
- Correção proposta: tabela de transições no domínio de Workflow (como `contracts/domain.py`), auditoria e evento `ProcessCompleted.v1` (ou bloqueio de conclusão manual de `TICKET_RESOLUTION`). Aceite: transições inválidas → 409 `INVALID_STATE`.

### A2-14 — Inadimplência apenas calculada na leitura; pagamentos sem auditoria
- Natureza / Severidade / Confiança: defeito demonstrado / média / alta
- Esperado: critério T12 ("inadimplência por vencimento"); AGENT.md ("trilha de auditoria para operações críticas"); RNF-04.
- Observado: `OVERDUE` é derivado em `invoice_data` (status persistido `OPEN`), sem evento, filtro ou auditoria; usa `date.today()` local; pagamentos não geram auditoria nem correlação (apenas `create_first_invoice` é auditado).
- Localização: `src/archcorp/finance/routes.py:80-87, 117-138`.
- Reprodução: `exp/e07_pagamentos.py`.
- Evidências: E2-13
- Correção proposta: caso de uso de pagamento com `audit(...)` e correlação; rotina/endpoint explícito de marcação de inadimplência (persistida e auditada) com data UTC. Aceite: trilha `/operations/{correlationId}` mostra o pagamento.

### A2-15 — Retentativa sem backoff/jitter e observabilidade fraca das falhas de despacho
- Natureza / Severidade / Confiança: divergência documental (AGENT.md/ADR-001 x implementação; parcialmente declarada em FLUXOS) / média / alta
- Esperado: AGENT.md (retentativa com atraso exponencial e jitter; correlação em registros de erro); ADR-001 regra 12 (auditoria do solicitante do reprocessamento).
- Observado: uma tentativa por chamada manual; log de falha sem `eventId`/`eventType` e com o `correlationId` da requisição de despacho; auditoria do reprocessamento registra `previousAttempts` e correlação, mas não o solicitante (`details {'previousAttempts': 3}`); lote sem limite.
- Localização: `src/archcorp/integration/service.py:21-46`; `src/archcorp/main.py:547-556`.
- Evidências: E2-12, E2-20
- Correção proposta: incluir `principal.subject` na auditoria do reprocessamento; logar `eventId`/`eventType`/correlação do evento; registrar formalmente (ADR) a ausência de backoff no protótipo ou implementar `next_attempt_at` com jitter. Aceite: auditoria contém solicitante; log de falha contém `eventId`.

### A2-16 — Idempotência heterogênea e de escopo frágil
- Natureza / Severidade / Confiança: risco / baixa / alta
- Observado: três implementações (E2-21); em chamados a mesma chave com descrição diferente é aceita como repetição; chaves não são escopadas por principal; o frontend gera chave nova a cada clique (reenvio cria novo chamado); reserva sem chave duplica.
- Localização: `support/service.py:19-22`; `contracts/service.py:62-87`; `web/src/App.tsx` (`crypto.randomUUID()`).
- Evidências: E2-07, E2-14, E2-22
- Correção proposta: usar `IdempotencyStore` (impressão digital completa) em todos os comandos; chave gerada uma vez por formulário. Aceite: mesma chave + descrição diferente → 409.

### A2-17 — Regras de entrada inconsistentes e códigos de erro divergentes do contrato
- Natureza / Severidade / Confiança: divergência documental / baixa / alta
- Observado: rascunho direto aceita `startsOn` no passado (reserva rejeita); cliente inexistente → 404 em reserva e 422 em rascunho; transições inválidas de chamado/tarefa → `409 CONFLICT` (INTEGRACOES define `INVALID_STATE`); moeda divergente no pagamento → 422 `VALIDATION_ERROR` sem lista `errors` (deveria ser `BUSINESS_RULE_VIOLATION`); 400 de correlação só documentado em rotas de `main.py`.
- Evidências: E2-07, E2-13, E2-14
- Correção proposta: alinhar validações e usar exceções de domínio (`InvalidStateError`, `BusinessRuleError`) nas rotas. Aceite: tabela de erros de INTEGRACOES coberta por teste.

### A2-18 — `dueAt` sem indicador UTC em SQLite e teste de envelope sem verificação de formato
- Natureza / Severidade / Confiança: defeito demonstrado (SQLite) / baixa / alta (SQLite), PostgreSQL pendente (P-04)
- Observado: após releitura, `dueAt` sai `2026-10-02T04:44:43.234` (sem `Z`) em API e em `TicketResolved.v1`; com `FormatChecker` falha `date-time`.
- Localização: `support/service.py` (`as_dict`), `workflow/routes.py` (`process_data`/`task_data`); `tests/test_contracts_and_architecture.py:155-176`.
- Evidências: E2-14, E2-16
- Correção proposta: normalizar `datetime` para UTC aware na serialização; habilitar `format_checker` no teste. Aceite: teste com FormatChecker passa em SQLite e PostgreSQL.

### A2-19 — Documentação de eventos desatualizada e `causationId` nunca preenchido
- Natureza / Severidade / Confiança: divergência documental / baixa / alta
- Observado: TO-BE e DDD citam 3 eventos; AsyncAPI/TDD/dispatcher têm 6. `causationId` é sempre `null`, inclusive em `TicketEntitlementReconciled.v1` (consequência de `TicketOpened.v1`).
- Evidências: E2-23
- Correção proposta: atualizar TO-BE/DDD; preencher `causationId` quando um fato decorre de outro. Aceite: revisão documental.

### A2-20 — Chamado pendente aceita contrato inexistente e inicia processo de Workflow
- Natureza / Severidade / Confiança: risco (comportamento documentado) / baixa / alta
- Observado: com `CONTRACT_ADAPTER_AVAILABLE=false`, `contractId` inexistente gera `201 PENDING_ENTITLEMENT` e processo `TICKET_RESOLUTION` de 24 h, cancelado só após reconciliação manual.
- Evidências: E2-14
- Correção proposta: documentar como decisão explícita (RNF-06) e expor a reconciliação na interface. Aceite: roteiro de demonstração cobre o caso.
