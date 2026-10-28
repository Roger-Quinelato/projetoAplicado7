# Achados da frente F-DAD — Dados, consistência, contratos e migrações

Referência: `main` = `44b8325`. Severidade: alta 1 · média 8 · baixa 8 · informativa 1 (18 achados). Premissas e limites estão em `resumo.md`. Itens de linha de base sem achado novo (resolvidos): AUD-01, AUD-09, AUD-11, AUD-12 (ver `linha_de_base.md`).

---

### DAD-01 — Ativação de contrato sem bloqueio nem atualização condicional: corrida pode gravar dois ContractActivated.v1
- Natureza: defeito (inspeção; reprodução limitada pelo SQLite)
- Severidade: média
- Confiança: média (PostgreSQL não executado; no SQLite a corrida vira erro de bloqueio, não duplicata)
- Esperado (fonte): idempotência de comandos repetíveis (AGENTS.md:91); `archcorp-dados-e-consistencia` §1 (bloquear a entidade ou `UPDATE ... WHERE estado = esperado` com conferência de linhas); critério de ativação única (01/10, A2-06).
- Observado: `activate` lê o contrato sem lock, confere `DRAFT`, grava `ACTIVE` e enfileira o evento sem `UPDATE ... WHERE status='DRAFT'` e sem conferir `rowcount`. No SQLite (E-01 A; E-08 S5) uma das transações perde por `database is locked` e só um evento existe. Em PostgreSQL (READ COMMITTED, sem bloqueio) as duas transações veem `DRAFT`: a previsão é dois eventos (não executado).
- Localização: `src/archcorp/contracts/service.py:87` (leitura sem lock), `:93-95` (verificação e atribuição), `:101` (enqueue), `:106` (commit). Padrão correto existente: `src/archcorp/support/service.py:302-310`.
- Reprodução: `scripts/e01_concorrencia.py` (cenário A; SQLite executado; PG com `ADB_URL`, não executado); E-08 S5 por HTTP.
- Impacto: dois fatos de ativação na outbox e no broker; consumidor externo não deduplica por `eventId` distinto; duplo clique no frontend gera chave nova a cada envio (01/10, A3-03).
- Evidências: E-DAD-03, E-DAD-05, E-DAD-11, E-DAD-24.
- Linha de base: AUD-10 (= Q-02).
- Correção proposta e critério de aceite: `UPDATE contracts_contracts SET status='ACTIVE' WHERE contract_id=:id AND status='DRAFT'` com `rowcount == 1` (ou `with_for_update()` na leitura). Aceite: teste PG com duas ativações paralelas e chaves diferentes → exatamente um `ContractActivated.v1` e a outra resposta é 409 ou replay; teste SQLite com barreira equivalente.
- Skill ou fluxo sugerido: `archcorp-dados-e-consistencia` §1 e §5; `tdd`.

### DAD-02 — Reprocessamento de CustomerUpdated.v1 antigo sobrescreve a projeção de Contracts (AUD-04 = Q-03)
- Natureza: defeito demonstrado
- Severidade: média
- Confiança: alta (executado no SQLite)
- Esperado (fonte): AGENTS.md:74 ("não aplique 'última escrita vence' sem decisão explícita; preserve a fonte oficial e registre a inconsistência"); RF-05/RF-07 (01/10).
- Observado: a v1 falha três vezes e vai a `FAILED`; a v2 é aplicada (`Nome Versao 2`); ao reprocessar a v1, a projeção vira `Nome Versao 1` e o CRM segue com `Nome Versao 2`. Nenhuma inconsistência é registrada.
- Localização: `src/archcorp/contracts/service.py:166-169` (`UPDATE` incondicional); `src/archcorp/crm/service.py:52` (payload sem versão nem `occurredAt` do agregado); `src/archcorp/integration/routes.py:54-63` (reprocessamento sem checar eventos mais novos).
- Reprodução: `scripts/e02_ordem_projecao.py` (log `logs\e02_ordem_projecao_sqlite.log`).
- Impacto: projeção de Contracts diverge da fonte oficial sem alarme; o mesmo padrão ameaça qualquer projeção futura (por exemplo, estado de chamado).
- Evidências: E-DAD-06, E-DAD-18.
- Linha de base: AUD-04 (= Q-03).
- Correção proposta e critério de aceite: incluir versão ou `occurredAt` do cliente em `CustomerUpdated.v1` e na projeção; aplicar `UPDATE ... WHERE projected_at < :v` e registrar o descarte em auditoria. Aceite: teste "falha v1 → aplica v2 → reprocessa v1" mantém `Nome Versao 2` e registra o descarte, em SQLite e PG; AsyncAPI atualizado.
- Skill ou fluxo sugerido: `archcorp-dados-e-consistencia` §1 (ordem de eventos); `archcorp-contratos-e-migracoes` §2 (evento alterado exige schema e exemplo).

### DAD-03 — Recusa ou queda do broker desfaz o consumo interno e bloqueia o fluxo de cobrança e preparação (AUD-05 = Q-10)
- Natureza: divergência entre código e contrato (acoplamento decidido no commit `3557d20`, não refletido no AsyncAPI, que diz "pode publicar uma cópia"), com defeito demonstrado.
- Severidade: alta — premissa: `RABBITMQ_URL` definida, como em `docker-compose.yml:6`. `render.yaml` não define `RABBITMQ_URL`, então a implantação pública não é afetada.
- Confiança: alta (executado; o caminho do broker está no savepoint e não depende do banco).
- Esperado (fonte): `docs/events/asyncapi.yaml:5-7` ("pode publicar uma cópia no RabbitMQ local"); `AGENTS.md:92` (retentativa apenas para erros transitórios); plano de 01/10, P-07 (com broker indisponível, o evento fica consumido internamente).
- Observado: com a porta do broker fechada, três despachos (cada um ~2,2 s) deixaram o evento novo `FAILED` com `attempts=3` e motivo não vazio, e sem fatura nem processo (efeitos desfeitos). Com o broker desligado, o evento seguinte foi processado normalmente (E-05). Ou seja, com o Compose e o broker fora do ar, nenhum contrato novo gera cobrança nem preparação.
- Localização: `src/archcorp/integration/service.py:38` (savepoint), `:46` (`_publish_broker` dentro do savepoint), `:48` e `:92-96` (falha conta como tentativa), `:108-145` (broker); `docker-compose.yml:6`.
- Reprodução: `scripts/e05_broker_fechado.py` (log `logs\e05_broker_fechado_sqlite.log`).
- Impacto: na stack Compose, a indisponibilidade do broker interrompe F2 e F3; o evento só volta por reprocessamento manual; a afirmação "cópia opcional" fica falsa para essa configuração.
- Evidências: E-DAD-04, E-DAD-09, E-DAD-18, E-DAD-19.
- Linha de base: AUD-05 (= Q-10). Parcial: "motivo vazio" e "falha depois dos efeitos" já foram resolvidos; o acoplamento é novo e mais grave.
- Correção proposta e critério de aceite: decidir por ADR. (a) Desacoplar: consumo interno no savepoint e publicação com estado próprio e retentativa, com timeouts curtos; aceite: com broker fora, eventos ficam `PUBLISHED` e a falha de publicação aparece com motivo. (b) Se o broker for obrigatório, ajustar AsyncAPI e README e documentar o bloqueio. Em ambos os casos reescrever `test_falha_no_broker_nao_marca_publicado_e_desfaz_efeitos` conforme a decisão.
- Skill ou fluxo sugerido: `create-adr` (decisão); `archcorp-dados-e-consistencia` §2; `tdd`.

### DAD-04 — Retentativa sem backoff, reprocessamento sem solicitante e despacho sem limite de lote (AUD-31)
- Natureza: divergência entre código e AGENTS.md
- Severidade: média
- Confiança: alta (executado e inspecionado)
- Esperado (fonte): AGENTS.md:92-93 (retentativa com atraso exponencial e jitter, só para transitórios; falha permanente para fila de erro com motivo e tentativas); ADR-001, regra 12 (auditoria do solicitante do reprocessamento, citada em 01/10 e não lida nesta frente).
- Observado: `_register_failure` incrementa `attempts` e não agenda próxima tentativa; o despacho carrega todos os `PENDING` sem `LIMIT`; o reprocessamento grava `{"previousAttempts": 3}` sem principal. Já resolvido: a falha loga `eventId` e `correlationId` (`integration/service.py:105-106`).
- Localização: `src/archcorp/integration/service.py:26-27` (sem limite), `:92-96` (sem backoff); `src/archcorp/integration/routes.py:60-61` (auditoria sem principal, `attempts = 0`).
- Reprodução: `scripts/e07_evento_venenoso.py` (último bloco: `auditoria do reprocessamento = {"previousAttempts": 3}`).
- Impacto: reprocessamento sem trilha de quem pediu; repetições imediatas em falhas transitórias; lote grande pode prender a requisição de despacho.
- Evidências: E-DAD-04, E-DAD-10, E-DAD-18.
- Linha de base: AUD-31. Estado: parcial.
- Correção proposta e critério de aceite: incluir `principal.subject` na auditoria do reprocessamento; agendar `next_attempt_at` com backoff exponencial e jitter (ou registrar a ausência em ADR, se for aceita para o protótipo); `LIMIT` no lote de despacho. Aceite: auditoria com solicitante; com relógio injetado, a próxima tentativa só ocorre após o atraso; lote de N eventos respeita o limite.
- Skill ou fluxo sugerido: `archcorp-dados-e-consistencia` §2; `create-adr` se a ausência de backoff for mantida.

### DAD-05 — Chave de idempotência não escopada por principal (AUD-39, parcial)
- Natureza: risco
- Severidade: baixa
- Confiança: alta (executado)
- Esperado (fonte): AGENTS.md:91 (comandos repetíveis aceitam `Idempotency-Key`); `IdempotencyStore` com impressão digital completa (01/10, P-26).
- Observado: o perfil `support` repete a chave do `admin` com o mesmo corpo e recebe o chamado do `admin` (201, `replay=true`, mesmo `ticketId`). A chave é única por `(key, operation)`, sem o principal. A descrição já entra na impressão digital (409 com descrição diferente), o que está resolvido.
- Localização: `src/archcorp/integration/models.py:75-81` (PK `key` + `operation`); `src/archcorp/integration/service.py:214-218` (`replay` sem principal); `src/archcorp/support/service.py:30` (`OPEN_OPERATION` constante) e `:86-90`.
- Reprodução: `scripts/e09_chave_tempo.py` (bloco a).
- Impacto: outro perfil recebe a resposta de um comando alheio; risco baixo na demonstração.
- Evidências: E-DAD-12.
- Linha de base: AUD-39. Estado: parcial.
- Correção proposta e critério de aceite: incluir o principal na chave ou na impressão digital; teste com dois principais e a mesma chave. Aceite: o segundo principal recebe resposta nova ou 409, conforme a regra escolhida em ADR.
- Skill ou fluxo sugerido: `archcorp-dados-e-consistencia` §1 (repetição).

### DAD-06 — Drafts e reservas sem teto de dígitos: 1e12 e 1e15 aceitos (AUD-35 remanescente)
- Natureza: risco (o defeito em PostgreSQL é por inspeção e por 01/10)
- Severidade: média
- Confiança: média (SQLite executado; PostgreSQL não executado)
- Esperado (fonte): AGENTS.md:83 (decimal com moeda; validação na fronteira); ADR-003 §2 (limite `Numeric(14,2)` aplicado na entrada).
- Observado: `1e12` e `1e15` retornam 201 em drafts e reservas (E-04) e o valor fica gravado no SQLite. Em PostgreSQL, `Numeric(14,2)` aceita 12 dígitos inteiros; o INSERT falharia com `DataError` e 01/10 registrou 500 (A3-06). Pagamentos já estão cobertos: `max_digits=14` mais o teto de 12 dígitos inteiros dão 422 para `1e12` e `1e15` (E-04).
- Localização: `src/archcorp/contracts/schemas.py:12` (`Billing.amount` sem `max_digits`); `src/archcorp/contracts/routes.py:90` (`ReservationInput.amount`); colunas `src/archcorp/contracts/models.py:19` e `:38` (`Numeric(14,2)`); referência de acerto: `src/archcorp/finance/routes.py:76`.
- Reprodução: `scripts/e04_dinheiro.py` (SQLite executado; PG com `ADB_URL`, não executado).
- Impacto: 500 exposto na criação de contrato e de reserva em PostgreSQL; o SQLite aceita valores que o PostgreSQL recusa (ambientes divergentes). O evento envenenado não se forma porque a falha ocorre antes da outbox.
- Evidências: E-DAD-08, E-DAD-24.
- Linha de base: AUD-35 (= Q-06). Estado: parcial.
- Correção proposta e critério de aceite: `max_digits=14, decimal_places=2` (ou `le=999999999999.99`) em `Billing` e `ReservationInput`; handler de `DataError` → 422 como defesa. Aceite: `1e12` → 422 em SQLite e PG; `999999999999.99` → 201.
- Skill ou fluxo sugerido: `archcorp-contratos-e-migracoes` §3.

### DAD-07 — OpenAPI com 11 de 278 exemplos inválidos e tipo monetário inconsistente entre respostas (AUD-20 = Q-05)
- Natureza: divergência entre código e contrato
- Severidade: média
- Confiança: alta (executado)
- Esperado (fonte): AGENTS.md:82-83 (envelope obrigatório; decimal com moeda; datas UTC); critério de exemplos válidos (01/10, P-10).
- Observado: 11 exemplos omitem campos nulos obrigatórios (`slaHours`, `dueAt`, `fromStatus`, `owner`, `overdueSince`, `contractId`). `billing.amount` é número nos exemplos de `POST /contracts/drafts` e de `activate`, mas a resposta real devolve string (`"2500.1"`, E-04), enquanto `GET /contracts/{id}` devolve número (`to_dict` com `float`).
- Localização: `src/archcorp/contracts/schemas.py:11-14` (`Billing` com `Decimal`) e `:49` (`ContractDraftResponse` usa `Billing`); `src/archcorp/contracts/service.py:178` (`to_dict` em `float`); exemplos: `src/archcorp/support/routes.py:29-46`, `src/archcorp/finance/routes.py:41-62`; artefato `docs/api/openapi.yaml`.
- Reprodução: `scripts/e03_exemplos_contrato.py` (bloco OpenAPI).
- Impacto: o mesmo campo chega com tipos diferentes conforme a rota; quem gera cliente tipado a partir do OpenAPI falha em alguns casos.
- Evidências: E-DAD-07, E-DAD-08, E-DAD-13, E-DAD-20.
- Linha de base: AUD-20 (= Q-05). Estado: aberto.
- Correção proposta e critério de aceite: um único tipo monetário nas respostas (string decimal ou número), decidido por ADR porque é mudança na v1; exemplos com nulos explícitos; teste que valida todo exemplo (ver DAD-09). Aceite: 0 exemplos inválidos no script de E-03.
- Skill ou fluxo sugerido: `archcorp-contratos-e-migracoes` §2 e §3; `create-adr`.

### DAD-08 — `Money.amount` do AsyncAPI com `multipleOf: 0.01` rejeita 19,99 e 0,07 (AUD-21 = Q-04)
- Natureza: divergência entre código e contrato
- Severidade: média
- Confiança: alta (executado)
- Esperado (fonte): envelope publicado deve validar contra o AsyncAPI (`tests/test_contracts_and_architecture.py:183-204`); AGENTS.md:83 (decimal com moeda).
- Observado: a validação rejeita `19.99`, `0.07` e `1234567.89` ("is not a multiple of 0.01"); `2500.0` e `100.1` passam. O teste de envelope da CI usa 2500 e não cobre o caso.
- Localização: `docs/events/asyncapi.yaml:397`; produtor `src/archcorp/contracts/service.py:178` (float) e `:101` (payload do evento).
- Reprodução: `scripts/e03_exemplos_contrato.py` (bloco Money).
- Impacto: um consumidor que valida o contrato rejeita envelope real com centavos comuns.
- Evidências: E-DAD-07, E-DAD-20.
- Linha de base: AUD-21 (= Q-04). Estado: aberto.
- Correção proposta e critério de aceite: `amount` como string decimal com `pattern: '^\d+\.\d{2}$'` (ou `number` sem `multipleOf`, documentado); incluir 19.99 e 0.07 no teste de envelope. Aceite: envelopes com 0,07, 19,99 e 1234567,89 validam.
- Skill ou fluxo sugerido: `archcorp-contratos-e-migracoes` §2 e §3.

### DAD-09 — Testes de contrato não validam os exemplos do OpenAPI e não usam FormatChecker
- Natureza: dívida técnica (teste)
- Severidade: média
- Confiança: alta (inspeção dos testes; E-03 mostra as violações que a CI não pega)
- Esperado (fonte): `archcorp-contratos-e-migracoes` §2 ("exemplos precisam validar contra o schema").
- Observado: o teste do OpenAPI só checa a presença de exemplos (`test_contracts_and_architecture.py:207-227`); os validadores AsyncAPI não usam `FormatChecker` (`:21-23`, e `test_t15_atendimento.py:564`); nenhum teste usa 19.99. A CI passa no SHA `44b8325` com 11 exemplos inválidos.
- Localização: `tests/test_contracts_and_architecture.py:21-23`, `:207-227`; `tests/test_t15_atendimento.py:564`.
- Reprodução: `scripts/e03_exemplos_contrato.py`; leitura dos testes.
- Impacto: defeitos de contrato chegam ao SHA auditado com CI verde.
- Evidências: E-DAD-07, E-DAD-16, E-DAD-20.
- Linha de base: novo (associado a AUD-20, AUD-21 e AUD-41).
- Correção proposta e critério de aceite: teste parametrizado que valida cada exemplo de OpenAPI e de AsyncAPI com `FormatChecker` e falha se algum for inválido; teste de envelope com valores de borda. Aceite: falha hoje (11 exemplos) e passa após DAD-07 e DAD-08.
- Skill ou fluxo sugerido: `engineering:testing-strategy`; `archcorp-contratos-e-migracoes` §5.

### DAD-10 — Prazo do ONBOARDING (72 h) contado do despacho, não do evento (resíduo do Q-01)
- Natureza: defeito
- Severidade: média
- Confiança: alta (executado)
- Esperado (fonte): regra adotada no PR #42 para TICKET_RESOLUTION (o prazo vem do instante publicado pelo evento: `src/archcorp/workflow/service.py:48-51`); `archcorp-dados-e-consistencia` §3; ADR-003 §3 (vencimento pela data UTC do evento, em Finance).
- Observado: `dueAt` do ONBOARDING = instante do despacho + 72 h. Com despacho 10 h depois do evento, `dueAt` vira `2026-10-22T20:00` em vez de `2026-10-22T10:00`. O commit `d6c8924` deixou o onboarding "inalterado".
- Localização: `src/archcorp/workflow/service.py:40-42`.
- Reprodução: `scripts/e09_chave_tempo.py` (bloco b).
- Impacto: atraso no despacho alonga o prazo de preparação da retirada; é a mesma classe de problema que o Q-01 corrigiu para o SLA do chamado.
- Evidências: E-DAD-12, E-DAD-23.
- Linha de base: Q-01 (correção parcial: TICKET_RESOLUTION corrigido; ONBOARDING pendente).
- Correção proposta e critério de aceite: usar `envelope["occurredAt"]` + 72 h ou registrar em ADR que o prazo conta do despacho. Aceite: teste com despacho 10 h depois mostra `dueAt = occurredAt + 72 h`.
- Skill ou fluxo sugerido: `archcorp-dados-e-consistencia` §3.

### DAD-11 — Requisições concorrentes com a mesma chave devolvem 500 em vez de replay (AUD-48)
- Natureza: defeito demonstrado (SQLite)
- Severidade: baixa
- Confiança: alta (executado no SQLite); a previsão de PostgreSQL é 409, por inspeção e 01/10
- Esperado (fonte): AGENTS.md:91 (repetição de comando devolve a mesma resposta); 01/10, P-26 (replay em vez de 409 sob corrida).
- Observado: S1 (mesma chave, reserva, 3 requisições simultâneas) → `[201, 500, 500]`, sem replay. Reserva sem chave, em SQLite, gravou 1 linha (bloqueio); em PostgreSQL, 01/10 registrou 2 reservas (não executado aqui). O 500 é "Erro não tratado"; não é `IntegrityError`, que o handler converte em 409.
- Localização: `src/archcorp/contracts/service.py:191-194` (replay antes da escrita; a corrida não é tratada) e `:208-209` (gravação da chave após o flush); `src/archcorp/errors.py:128-131` (`IntegrityError` → 409).
- Reprodução: `scripts/e08_cliente_paralelo.py` (S1, S2) com uvicorn na porta 18102 (SQLite).
- Impacto: cliente legítimo em retentativa paralela recebe erro interno; reserva sem chave pode duplicar em PostgreSQL.
- Evidências: E-DAD-11, E-DAD-22.
- Linha de base: AUD-48. Estado: aberto.
- Correção proposta e critério de aceite: capturar a violação da chave no commit e devolver a resposta armazenada com `Idempotency-Replayed: true`; teste paralelo em SQLite e PG com ambas as respostas 2xx e a segunda com replay. Para reserva sem chave, decidir se a chave é obrigatória (decisão registrada).
- Skill ou fluxo sugerido: `archcorp-dados-e-consistencia` §1 e §5.

### DAD-12 — Relógio local (`date.today()`) define o encerramento sem `endsOn` e a validação de início de reserva
- Natureza: risco
- Severidade: baixa
- Confiança: média (inspeção; E-09 d mostra o valor vindo do relógio local)
- Esperado (fonte): AGENTS.md:83 (datas em UTC); `archcorp-dados-e-consistencia` §3 (tudo em UTC). Finance e Support já usam relógio UTC injetado (`src/archcorp/finance/domain.py:24-25,35-36`; `src/archcorp/support/service.py:40-41`).
- Observado: `ends_on = max(date.today(), contract.starts_on)` e `startsOn < date.today()` usam o dia local do processo. Com a data local simulada em 18/10 e a UTC em 19/10, o encerramento grava `2026-10-18`.
- Localização: `src/archcorp/contracts/service.py:123`; `src/archcorp/contracts/routes.py:100`.
- Reprodução: `scripts/e09_chave_tempo.py` (bloco d).
- Impacto: perto da meia-noite em fusos negativos, o encerramento e a validação de reserva usam o dia anterior ao UTC; diverge do contrato, sem quebrar a consistência interna.
- Evidências: E-DAD-12.
- Linha de base: novo.
- Correção proposta e critério de aceite: relógio UTC injetado em Contracts, como em Finance e Support. Aceite: teste com relógio UTC fixo prova o dia de encerramento.
- Skill ou fluxo sugerido: `archcorp-dados-e-consistencia` §3.

### DAD-13 — Datas sem indicador UTC em respostas de Workflow e de Operations (AUD-41, residual)
- Natureza: divergência entre código e contrato
- Severidade: baixa
- Confiança: alta (executado)
- Esperado (fonte): AGENTS.md:82-83 (ISO 8601 UTC); o envelope de eventos já cumpre (`Z`, `E-DAD-20`).
- Observado: `GET /workflow/processes` devolve `dueAt` sem fuso (`2026-10-22T11:17:18.685397`); `GET /operations/{id}` devolve `occurredAt` sem fuso. Em PostgreSQL, o valor sairia com `+00:00`, não `Z` (inspeção). As rotas de Support já usam `iso_utc`.
- Localização: `src/archcorp/workflow/routes.py:82` (`item.due_at.isoformat()`); `src/archcorp/integration/routes.py:97` (`a.occurred_at`); referência correta: `src/archcorp/support/domain.py:82-84`.
- Reprodução: `scripts/e09_chave_tempo.py` (bloco c).
- Impacto: cliente que interpreta sem fuso pode deslocar prazos; a inconsistência entre rotas é visível.
- Evidências: E-DAD-12, E-DAD-20.
- Linha de base: AUD-41. Estado: parcial.
- Correção proposta e critério de aceite: `iso_utc` nas serializações de Workflow e Integration; teste com `FormatChecker` sobre as respostas. Aceite: toda data de resposta termina em `Z`.
- Skill ou fluxo sugerido: `archcorp-dados-e-consistencia` §3; DAD-09.

### DAD-14 — N+1 em `GET /finance/invoices` e filtros de estado sem índice (dívida)
- Natureza: dívida técnica
- Severidade: baixa
- Confiança: alta (executado: 8 comandos com 5 faturas, 28 com 25)
- Esperado (fonte): consultas sem N+1 em listagens e índices conforme o padrão de acesso (`ddia-storage-retrieval`).
- Observado: `list_invoices` chama `to_dict` por fatura e cada `to_dict` faz `paid_total` (uma consulta por fatura; até 201 com o limite de 200). A listagem de chamados já é em lote (owners). Filtros sem índice: `finance_invoices` em `status` e `due_date` (candidatos de `evaluate_overdue`) e `support_tickets` em `status` (`reconcile_pending`).
- Localização: `src/archcorp/finance/service.py:209-213` (listagem), `:215-229` (`to_dict` e `paid_total` na `:216`, `:227-229`), `:169-171` (candidatos sem índice); `src/archcorp/support/service.py:190-191` (pendentes sem índice).
- Reprodução: `scripts/e10_codigos_consultas.py` (parte C).
- Impacto: a latência de `GET /finance/invoices` cresce linearmente com o número de faturas.
- Evidências: E-DAD-14.
- Linha de base: novo.
- Correção proposta e critério de aceite: agregar pagamentos numa consulta (`GROUP BY invoice_id`) ou `selectinload`; índices em `(status, due_date)` e `(status)` por migração aditiva (ADR-002 permite criar índice). Aceite: número de comandos SQL constante para N=5 e N=25.
- Skill ou fluxo sugerido: `archcorp-contratos-e-migracoes` §4 (migração aditiva); `ddia-storage-retrieval`.

### DAD-15 — Códigos e status de erro divergentes para a mesma condição (AUD-40, parcial)
- Natureza: divergência entre código e contrato
- Severidade: baixa
- Confiança: alta (executado)
- Esperado (fonte): coerência entre código, OpenAPI e testes (critério desta frente); ADR-004 (409 preservado em resolução e atribuição).
- Observado: cliente inexistente → 422 `BUSINESS_RULE_VIOLATION` no rascunho e 404 `NOT_FOUND` na reserva. `INVALID_STATE` (encerrar rascunho) e `IDEMPOTENCY_CONFLICT` (reserva) não aparecem no OpenAPI da operação. `INTERNAL_ERROR` (500) não está documentado. Os status observados são todos documentados para suas operações.
- Localização: `src/archcorp/contracts/service.py:39` (`BusinessRuleError`) e `:197` (`NotFoundError` na reserva); `src/archcorp/errors.py:24-33` (`STATUS_CODES`).
- Reprodução: `scripts/e10_codigos_consultas.py` (partes A e B).
- Impacto: o cliente trata "não encontrado" de forma diferente conforme o recurso.
- Evidências: E-DAD-13.
- Linha de base: AUD-40. Estado: parcial.
- Correção proposta e critério de aceite: uma regra única para cliente inexistente; declarar no OpenAPI os códigos realmente devolvidos; documentar `INTERNAL_ERROR` como genérico. Mudar 422 para 404 é incompatível na v1: exige ADR. Aceite: tabela por operação coberta por teste.
- Skill ou fluxo sugerido: `archcorp-contratos-e-migracoes` §1 e `create-adr`.

### DAD-16 — Exceção de segurança do contrato v1 (`GET /metrics`) sem ADR (governança)
- Natureza: divergência de governança
- Severidade: baixa
- Confiança: alta (inspeção do baseline e dos ADRs)
- Esperado (fonte): exceções contratuais registradas em ADR (ADR-003 §2 e ADR-004 como precedente).
- Observado: `tests/fixtures/api_v1_baseline.json` aprova `GET /metrics` com `HTTPBearer` e justificativa textual ("#40"), mas nenhum ADR cita o caminho. ADR-005 (`:12-13`) trata a composição de `main.py` com métricas, sem decidir autenticação.
- Localização: `tests/fixtures/api_v1_baseline.json` (`approved_security`); `docs/adr/ADR-005-fronteiras-http-e-integracao-publica.md:12-13`.
- Reprodução: `scripts/e03_exemplos_contrato.py` (último bloco).
- Impacto: quem coletava métricas anonimamente quebra sem registro formal da decisão.
- Evidências: E-DAD-07, E-DAD-19.
- Linha de base: novo.
- Correção proposta e critério de aceite: ADR curto registrando a exigência de papel em `/metrics` e o impacto para coleta; ou remover a exceção do baseline se a mudança for revertida. Aceite: toda entrada de `approved_*` cita um ADR.
- Skill ou fluxo sugerido: `create-adr`.

### DAD-17 — Banco sem `alembic_version` em estado intermediário falha em PostgreSQL (AUD-33): não reproduzível em SQLite
- Natureza: defeito demonstrado em PostgreSQL em 01/10; mesma lógica no código atual
- Severidade: baixa
- Confiança: média (PostgreSQL não executado; SQLite passa)
- Esperado (fonte): ADR-002 (migrações reproduzíveis; inicialização com upgrade até head); AGENTS.md (migrações com estratégia de compatibilidade).
- Observado: no SQLite, sem carimbo em `0001` e em `0002`, `upgrade_to_head` termina com cabeça `0005` e sem divergência (E-12 D). Por inspeção, `upgrade_to_head` carimba `0001_baseline` quando há divergência (`migrate.py:53-57`) e a migração `0002` tenta `add_column('active')`, que já existe no banco; em PostgreSQL isso dá `DuplicateColumn` (01/10, caso 5).
- Localização: `src/archcorp/infrastructure/migrate.py:53-57`; `src/archcorp/infrastructure/migrations/versions/0002_customer_active.py` (`add_column`).
- Reprodução: `scripts/e12_migracoes.py` (bloco D, SQLite). PG: `evidencias/agente3/scripts/mig_exp.py` (caso 5), reaproveitado, não executado.
- Impacto: banco legado criado por `create_all` em estado intermediário não sobe em PostgreSQL.
- Evidências: E-DAD-15, E-DAD-22, E-DAD-24.
- Linha de base: AUD-33. Estado: aberto (não verificado em PostgreSQL).
- Correção proposta e critério de aceite: detectar a revisão por comparação com cada revisão (ou exigir carimbo manual documentado); teste por revisão intermediária sem carimbo em PostgreSQL. Aceite: caso 5 passa em PostgreSQL.
- Skill ou fluxo sugerido: `archcorp-contratos-e-migracoes` §4 e `migration`.

### DAD-18 — `causationId` sempre nulo (informativa)
- Natureza: dívida técnica
- Severidade: informativa
- Confiança: alta (inspeção)
- Esperado (fonte): AGENTS.md:82 (envelope com `causationId`); AsyncAPI aceita `null`.
- Observado: nenhuma chamada a `enqueue` passa `causation_id`. Fatos derivados (por exemplo, `TicketEntitlementReconciled.v1` a partir de `TicketOpened.v1`) não apontam a causa.
- Localização: `src/archcorp/integration/service.py:153-157` (padrão `None`); chamadores em `contracts/service.py`, `support/service.py` e `crm/service.py`.
- Reprodução: `Grep` por `causation` em `src/archcorp` (E-DAD-21).
- Impacto: rastreabilidade causal entre eventos ausente; não há violação de schema.
- Evidências: E-DAD-21.
- Linha de base: novo (01/10, A2-19, fora desta frente).
- Correção proposta e critério de aceite: passar `causation_id` em fatos derivados. Aceite: teste confirma `causationId` não nulo em `TicketEntitlementReconciled.v1`.
- Skill ou fluxo sugerido: `archcorp-contratos-e-migracoes` §2.
