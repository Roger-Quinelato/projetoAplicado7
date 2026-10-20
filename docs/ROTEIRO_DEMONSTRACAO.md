# Roteiro de demonstração

> Estado de execução em 27/09/2026: consulte [Estado da implementação](ESTADO_IMPLEMENTACAO.md) e [Cronograma executável](CRONOGRAMA_EXECUCAO.md). As seções de desenho abaixo incluem metas futuras e premissas acadêmicas; o código e os testes são a evidência do comportamento atual.

Este roteiro demonstra F1, F2 e F3, incluindo idempotência, correlação,
indisponibilidade e recuperação. Consulte os [exemplos completos de API e
eventos](EXEMPLOS_API.md) e os [diagramas de
sequência](arquitetura/FLUXOS_INTEGRACAO.md) durante a apresentação.

## Preparar o ambiente

1. Inicie os serviços em segundo plano:

   ```powershell
   docker compose up -d --build
   ```

2. Confirme os pontos de operação:

   ```powershell
   Invoke-RestMethod http://localhost:8000/health/live
   Invoke-RestMethod http://localhost:8000/health/ready
   ```

   As duas respostas devem informar `status: UP`. A prontidão também deve informar
   `database: UP` e, com `RABBITMQ_URL` configurado, `broker: UP` (listener AMQP
   aceitando conexão). `broker: DOWN` não torna a API não pronta: o despacho registra
   a falha e tenta de novo.

   Para uma pilha isolada da demonstração, com contêineres e volume próprios, use
   `docker compose -p archcorp-demo up -d --build`; `ARCHCORP_API_PORT`,
   `ARCHCORP_POSTGRES_PORT` e `ARCHCORP_RABBITMQ_UI_PORT` mudam as portas publicadas.
   O healthcheck do RabbitMQ usa `rabbitmq-diagnostics check_port_connectivity`, que
   só passa quando a porta AMQP aceita conexões (o `ping` responde antes).

3. Abra `http://localhost:8000/docs` para consultar o OpenAPI e
   `http://localhost:15672` para observar o RabbitMQ. O ambiente local usa
   `guest`/`guest` no painel do broker.

4. Execute a demonstração em um banco sem dados anteriores ou use chaves
   idempotentes novas, como nos comandos abaixo. O
   [`scripts/demo.ps1`](../scripts/demo.ps1) usa chaves fixas e deve ser executado
   apenas uma vez no mesmo banco.

## Executar o caminho principal automaticamente

Execute o script para criar cliente, contrato, cobrança, preparação de retirada, chamado e
processo de resolução:

```powershell
./scripts/demo.ps1
```

Registre os quatro valores impressos pelo script:

- `Cliente`: use como `customerId`.
- `Contrato`: use como `contractId`.
- `Chamado`: use como `ticketId`.
- `Correlação`: use para consultar a trilha operacional.

O estado final deve aumentar em um cliente, um contrato, uma cobrança, um chamado,
dois processos e um mapeamento legado. Como o endpoint mostra totais do banco,
compare os valores antes e depois quando o ambiente já possuir outros dados.

O script cobre o caminho de sucesso. Execute as seções seguintes para demonstrar
repetição idempotente e falhas controladas.

## Preparar uma sessão manual

Abra um PowerShell e defina as variáveis. Reutilize esse terminal até o final para
preservar os IDs capturados.

```powershell
$baseUrl = "http://localhost:8000"
$correlationId = [guid]::NewGuid().ToString()
$headers = @{
  Authorization = "Bearer demo-admin"
  "Content-Type" = "application/json"
  "X-Correlation-ID" = $correlationId
}
```

## F1: criar contrato sem recadastro

1. Crie o cliente oficial no CRM e capture o ID:

   ```powershell
   $customerBody = @{
     name = "Cliente Demonstração Localiza"
     email = "demo.localiza@example.com"
     eligible = $true
     consentService = $true
     legacyId = "CRM-$([guid]::NewGuid())"
   } | ConvertTo-Json

   $customer = Invoke-RestMethod -Method Post `
     -Uri "$baseUrl/api/v1/crm/customers" `
     -Headers $headers -Body $customerBody
   $customerId = $customer.customerId
   $customerId
   ```

   Verifique que `customerId` contém um UUID.

2. Crie o rascunho e capture a resposta HTTP para inspecionar os cabeçalhos:

   ```powershell
   $draftKey = "draft-$([guid]::NewGuid())"
   $headers["Idempotency-Key"] = $draftKey
   $draftBody = @{
     customerId = $customerId
     serviceCode = "RENTAL-FLEX"
     startsOn = "2026-10-01"
     billing = @{
       amount = 2500.00
       currency = "BRL"
       cycle = "MONTHLY"
     }
     slaHours = 8
   } | ConvertTo-Json -Depth 4

   $draftResponse = Invoke-WebRequest -Method Post `
     -Uri "$baseUrl/api/v1/contracts/drafts" `
     -Headers $headers -Body $draftBody
   $contract = $draftResponse.Content | ConvertFrom-Json
   $contractId = $contract.contractId
   $contract
   $draftResponse.Headers["Idempotency-Replayed"]
   ```

   Verifique `status: DRAFT`, o mesmo `customerId` do CRM e
   `Idempotency-Replayed: false`.

3. Repita a mesma chamada, com o mesmo corpo e a mesma chave:

   ```powershell
   $draftReplay = Invoke-WebRequest -Method Post `
     -Uri "$baseUrl/api/v1/contracts/drafts" `
     -Headers $headers -Body $draftBody
   $draftReplayBody = $draftReplay.Content | ConvertFrom-Json
   $draftReplay.Headers["Idempotency-Replayed"]
   $draftReplayBody.contractId -eq $contractId
   ```

   Os resultados devem ser `true` para o cabeçalho de replay e `True` para a
   comparação do `contractId`. O banco continua com um rascunho para essa chave.

### F1 verificável por script Python (T11)

[`scripts/demo_f1.py`](../scripts/demo_f1.py) executa o F1 pelo caminho cliente →
reserva → rascunho e as ramificações do plano, usando `httpx` (já em
`requirements-dev.txt`). Não tem dependência específica de SO; foi executado em
Linux e, em 17/10/2026, em Windows 11. Pode ser repetido no mesmo banco, pois gera e-mail, ID legado e chaves novas a cada execução.

1. Suba a API local (Docker Compose acima ou diretamente):

   ```bash
   PYTHONPATH=src uvicorn archcorp.main:app --port 8000
   ```

   No PowerShell: `$env:PYTHONPATH = "src"; uvicorn archcorp.main:app --port 8000`.

2. Em outro terminal, execute:

   ```bash
   python scripts/demo_f1.py
   ```

   Opções: `--base-url` (ou `ARCHCORP_BASE_URL`), `--token` (ou `ARCHCORP_TOKEN`;
   padrão `demo-admin`) e `--forbidden-token` (padrão `demo-support`). No modo
   público só existe a credencial compartilhada; informe-a por `ARCHCORP_TOKEN` e use
   `--forbidden-token ""` para pular a checagem de `403`. Nunca grave a credencial no
   repositório.

3. Observe cada linha `[OK  ]`/`[FALHA]`: ela traz o passo, o status HTTP e o
   `correlationId` devolvido pela API. O caminho principal usa um único
   `correlationId` (impresso no cabeçalho e no resumo); cada ramificação usa um
   próprio.

   | Passo | O que comprova |
   |---|---|
   | 0b | O `/openapi.json` publicado não aceita campos cadastrais em `ReservationInput` nem em `ContractDraftCreate`, e o rascunho a partir da reserva não tem corpo |
   | 1–2 | O CRM cadastra e devolve o cliente oficial (UUID, nome, e-mail e ID legado sintéticos) |
   | 3–4 | A reserva é registrada para o `customerId` do CRM; repetir a chave devolve a mesma reserva |
   | 5–6 | O rascunho é gerado da reserva **sem corpo**, com o `customerId` do CRM e período/cobrança da reserva; a repetição devolve o mesmo `contractId` com `Idempotency-Replayed: true` |
   | 7–9 | A reserva fica `DRAFTED` e vinculada; há um único contrato; o ID legado resolve o mesmo UUID global |
   | 10 | `GET /api/v1/operations/{correlationId}` mostra `crm.create_customer`, `contracts.create_reservation`, `contracts.create_draft` e `contracts.draft_from_reservation` |
   | 11–13 | `422` em `application/problem+json` para validação estrutural, cliente inexistente e cliente inativado após a reserva, com o mesmo `correlationId` enviado |
   | 14–15 | A mesma `Idempotency-Key` usada em outra reserva retorna `409 IDEMPOTENCY_CONFLICT`; o contrato da primeira reserva continua `DRAFT`. O reaproveitamento de uma chave do rascunho direto é coberto por teste automatizado |
   | 16–18 | `401` sem credencial, `403` para papel sem permissão e `400` para `X-Correlation-ID` que não é UUID |

4. O script termina com `== N/N checagens aprovadas` e código de saída `0`. Qualquer
   checagem divergente imprime o esperado e a resposta e termina com código `1`;
   API inacessível termina com `2`.

A API não possui chave para simular timeout ou indisponibilidade do CRM durante o
F1, por isso o script não cobre essa ramificação. Ela é demonstrada pelo teste
`tests/test_f1_cliente_reserva_contrato.py::test_f1_indisponibilidade_do_crm_retorna_503_sem_efeito_parcial`,
que envolve um simulador sem resposta com o adaptador `ResilientCustomerReader`
(ADR-006). O comportamento é: três tentativas com log `WARNING` e o mesmo
`correlationId`, `503 SERVICE_UNAVAILABLE` em problem+json, nenhum contrato,
vínculo ou chave idempotente gravados, e a repetição com a mesma chave cria o
rascunho uma única vez depois que o CRM volta. Uma falha transitória seguida de
sucesso é absorvida pela retentativa sem erro para o chamador.

```bash
PYTHONPATH=src python -m pytest -q tests/test_f1_cliente_reserva_contrato.py -p no:cacheprovider
```

### F2 e F3 verificáveis por script Python (T13 e T16)

[`scripts/demo_f2.py`](../scripts/demo_f2.py) e
[`scripts/demo_f3.py`](../scripts/demo_f3.py) seguem o mesmo formato, as mesmas
opções e os mesmos códigos de saída de `demo_f1.py`, com a API local já em execução:

```bash
python scripts/demo_f2.py   # ativação, despacho, uma fatura INITIAL e uma preparação de retirada; repetições sem duplicar
python scripts/demo_f3.py   # elegibilidade/SLA, chamado, processo de resolução, atribuição, resolução MET e ramificações
```

Em 17/10/2026, contra `uvicorn` local em Windows 11 com SQLite, os três roteiros
aprovaram 20/20 (F1), 14/14 (F2) e 15/15 (F3) checagens. O `demo_f3.py` mostra o prazo
do chamado e o do processo lado a lado; eles só passam a coincidir com a correção do
PR #42. Falha permanente e indisponibilidade de Contracts continuam nas seções
manuais abaixo, porque exigem reiniciar a API com outra configuração.

## F2: ativar, cobrar e iniciar preparação de retirada

1. Registre o estado anterior, ative o contrato e capture o `eventId`:

   ```powershell
   $stateBeforeF2 = Invoke-RestMethod `
     -Uri "$baseUrl/api/v1/demo/state" -Headers $headers
   $activateKey = "activate-$([guid]::NewGuid())"
   $headers["Idempotency-Key"] = $activateKey

   $activationResponse = Invoke-WebRequest -Method Post `
     -Uri "$baseUrl/api/v1/contracts/$contractId/activate" `
     -Headers $headers
   $activation = $activationResponse.Content | ConvertFrom-Json
   $eventId = $activation.eventId
   $activation
   ```

   Verifique `status: ACTIVE` e um UUID em `eventId`.

2. Repita a ativação antes do despacho:

   ```powershell
   $activationReplay = Invoke-WebRequest -Method Post `
     -Uri "$baseUrl/api/v1/contracts/$contractId/activate" `
     -Headers $headers
   $activationReplayBody = $activationReplay.Content | ConvertFrom-Json
   $activationReplay.Headers["Idempotency-Replayed"]
   $activationReplayBody.eventId -eq $eventId
   ```

   O cabeçalho deve indicar `true`, e a comparação do evento deve retornar `True`.

3. Despache a outbox duas vezes e compare o estado:

   ```powershell
   $dispatchF2 = Invoke-RestMethod -Method Post `
     -Uri "$baseUrl/api/v1/integration/outbox/dispatch" `
     -Headers $headers
   $dispatchF2Again = Invoke-RestMethod -Method Post `
     -Uri "$baseUrl/api/v1/integration/outbox/dispatch" `
     -Headers $headers
   $stateAfterF2 = Invoke-RestMethod `
     -Uri "$baseUrl/api/v1/demo/state" -Headers $headers

   $dispatchF2
   $dispatchF2Again
   $stateAfterF2.invoices - $stateBeforeF2.invoices
   $stateAfterF2.processes - $stateBeforeF2.processes
   ```

   O primeiro despacho deve processar um evento e o segundo deve processar zero.
   As duas diferenças finais devem valer `1`: uma cobrança e uma preparação de retirada.

## Financeiro: pagamento parcial, inadimplência e quitação (T12)

Use o contrato ativado em F2. O pagamento é simulado: não há PSP, conciliação
bancária, nota fiscal nem cobrança real. O vencimento é a data UTC do evento de
ativação mais 10 dias (premissa a validar), e o protótipo não tem agendador: a inadimplência é registrada
pelo comando `overdue-check`.

1. Para simular a passagem do tempo sem esperar o vencimento, reinicie só a API
   com a data de referência futura habilitada (simulação local; não use no modo
   público):

   ```powershell
   docker compose stop api
   docker compose run --rm --service-ports `
     -e FINANCE_ALLOW_FUTURE_AS_OF=true api
   ```

   Fora do Docker: `FINANCE_ALLOW_FUTURE_AS_OF=true PYTHONPATH=src uvicorn archcorp.main:app`.
   Sem essa variável, `asOf` futuro recebe `422 BUSINESS_RULE_VIOLATION`; com a
   data atual o comando funciona sempre. A API recusa iniciar com essa variável
   e `PUBLIC_DEMO=true`.

2. Consulte a fatura e registre um pagamento parcial com `Idempotency-Key`:

   ```powershell
   $invoice = (Invoke-RestMethod `
     -Uri "$baseUrl/api/v1/finance/invoices?contractId=$contractId" -Headers $headers) |
     Where-Object kind -eq "INITIAL"
   $invoice                      # status OPEN, balance 2500, delinquent False

   $headers["Idempotency-Key"] = "pay-$([guid]::NewGuid())"
   $paymentBody = @{ amount = 1000.00; currency = "BRL"; reference = "SIM-$([guid]::NewGuid().ToString().Substring(0,8))" } | ConvertTo-Json
   $partial = Invoke-WebRequest -Method Post `
     -Uri "$baseUrl/api/v1/finance/invoices/$($invoice.invoiceId)/payments" `
     -Headers $headers -Body $paymentBody
   ($partial.Content | ConvertFrom-Json).invoice   # PARTIALLY_PAID, balance 1500
   $replay = Invoke-WebRequest -Method Post `
     -Uri "$baseUrl/api/v1/finance/invoices/$($invoice.invoiceId)/payments" `
     -Headers $headers -Body $paymentBody
   $replay.Headers["Idempotency-Replayed"]          # true; nenhum pagamento novo
   $headers.Remove("Idempotency-Key")
   ```

3. Verifique o vencimento no próprio dia e no dia seguinte:

   ```powershell
   $due = [datetime]::Parse($invoice.dueDate)
   $onDue = @{ asOf = $due.ToString("yyyy-MM-dd") } | ConvertTo-Json
   $afterDue = @{ asOf = $due.AddDays(1).ToString("yyyy-MM-dd") } | ConvertTo-Json
   Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/finance/invoices/overdue-check" `
     -Headers $headers -Body $onDue      # markedOverdue vazio: só vence depois do dia
   Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/finance/invoices/overdue-check" `
     -Headers $headers -Body $afterDue   # markedOverdue contém a fatura
   Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/finance/invoices/overdue-check" `
     -Headers $headers -Body $afterDue   # repetição: markedOverdue vazio, alreadyOverdue 1
   Invoke-RestMethod -Uri "$baseUrl/api/v1/finance/invoices/$($invoice.invoiceId)" -Headers $headers
   ```

   A fatura deve aparecer com `status: OVERDUE`, `delinquent: True`,
   `overdueSince` em UTC e `balance: 1500`.

4. Pague o restante e confirme a quitação:

   ```powershell
   $rest = @{ amount = 1500.00; currency = "BRL"; reference = "SIM-$([guid]::NewGuid().ToString().Substring(0,8))" } | ConvertTo-Json
   (Invoke-RestMethod -Method Post `
     -Uri "$baseUrl/api/v1/finance/invoices/$($invoice.invoiceId)/payments" `
     -Headers $headers -Body $rest).invoice
   ```

   Esperado: `status: PAID`, `balance: 0`, `delinquent: False` e `overdueSince`
   mantido como histórico. Novo pagamento recebe `409 CONFLICT`; valor acima
   do saldo, `409 CONFLICT`; moeda diferente, `422 VALIDATION_ERROR`.

5. (Opcional) Encerre o contrato com `endsOn` posterior, despache a outbox e
   consulte de novo as faturas do contrato: surge uma fatura `FINAL` com
   `sourceEventId` igual ao `eventId` do encerramento (por exemplo, início em
   01/10/2026, fim em 08/01/2027 e R$ 2.500 mensais: 4 ciclos iniciados − 2.500
   já faturados = R$ 7.500). Repetir o despacho não cria outra.

6. A trilha `GET /api/v1/operations/$correlationId` mostra
   `finance.record_simulated_payment`, `finance.mark_invoice_overdue`,
   `finance.evaluate_overdue` e `finance.create_final_invoice`. Restaure a API
   normal com `Ctrl+C` e `docker compose up -d api`.

## F3: abrir chamado com SLA

1. Registre o estado anterior, abra o chamado e capture o `ticketId`:

   ```powershell
   $stateBeforeF3 = Invoke-RestMethod `
     -Uri "$baseUrl/api/v1/demo/state" -Headers $headers
   $ticketKey = "ticket-$([guid]::NewGuid())"
   $headers["Idempotency-Key"] = $ticketKey
   $ticketBody = @{
     customerId = $customerId
     contractId = $contractId
     serviceCode = "RENTAL-FLEX"
     category = "OUTAGE"
     description = "Serviço indisponível durante a demonstração"
   } | ConvertTo-Json

   $ticketResponse = Invoke-WebRequest -Method Post `
     -Uri "$baseUrl/api/v1/support/tickets" `
     -Headers $headers -Body $ticketBody
   $ticket = $ticketResponse.Content | ConvertFrom-Json
   $ticketId = $ticket.ticketId
   $ticket
   ```

   Verifique `status: OPEN`, `priority: HIGH`, `slaHours: 8`, `openedAt` e `dueAt`
   em UTC (`dueAt` = `openedAt` + 8 h) e `slaStatus: WITHIN`.

2. Repita a abertura com o mesmo corpo e a mesma chave:

   ```powershell
   $ticketReplay = Invoke-WebRequest -Method Post `
     -Uri "$baseUrl/api/v1/support/tickets" `
     -Headers $headers -Body $ticketBody
   $ticketReplayBody = $ticketReplay.Content | ConvertFrom-Json
   $ticketReplay.Headers["Idempotency-Replayed"]
   $ticketReplayBody.ticketId -eq $ticketId
   ```

   O cabeçalho deve indicar `true`, e o `ticketId` deve permanecer igual.

3. Despache o evento e verifique as contagens:

   ```powershell
   $dispatchF3 = Invoke-RestMethod -Method Post `
     -Uri "$baseUrl/api/v1/integration/outbox/dispatch" `
     -Headers $headers
   $stateAfterF3 = Invoke-RestMethod `
     -Uri "$baseUrl/api/v1/demo/state" -Headers $headers

   $dispatchF3
   $stateAfterF3.tickets - $stateBeforeF3.tickets
   $stateAfterF3.processes - $stateBeforeF3.processes
   ```

   O despacho deve processar um evento. As diferenças devem valer `1`: um chamado
   e um processo de resolução.

4. Atribua, reatribua e resolva duas vezes (T15):

   ```powershell
   $headers.Remove("Idempotency-Key")
   foreach ($owner in "Equipe de assistência 24h", "Equipe de pátio") {
     Invoke-RestMethod -Method Post `
       -Uri "$baseUrl/api/v1/support/tickets/$ticketId/assign" `
       -Headers $headers -ContentType "application/json" `
       -Body (@{ owner = $owner } | ConvertTo-Json)
   }
   $resolved = Invoke-WebRequest -Method Post `
     -Uri "$baseUrl/api/v1/support/tickets/$ticketId/resolve" -Headers $headers
   $resolvedAgain = Invoke-WebRequest -Method Post `
     -Uri "$baseUrl/api/v1/support/tickets/$ticketId/resolve" -Headers $headers
   ($resolved.Content | ConvertFrom-Json).slaStatus
   $resolvedAgain.Headers["Idempotency-Replayed"]
   Invoke-RestMethod -Uri "$baseUrl/api/v1/support/tickets/$ticketId/history" -Headers $headers
   ```

   A primeira resolução mostra `slaStatus: MET`; a segunda devolve
   `Idempotency-Replayed: true` sem novo `TicketResolved.v1`. O histórico lista
   `OPENED`, `ASSIGNED`, `REASSIGNED` (com `previousOwner`) e `RESOLVED`, cada um com
   `actorRole` e `correlationId`. Um novo despacho processa um evento e conclui o
   processo de resolução em Workflow.

## Demonstrar indisponibilidade e reconciliação

O Docker Compose não expõe uma rota que altere a disponibilidade em tempo de
execução. Use um contêiner temporário da API com a configuração documentada.

1. Em outro terminal, pare somente a API e inicie a variante degradada:

   ```powershell
   docker compose stop api
   docker compose run --rm --service-ports `
     -e CONTRACT_ADAPTER_AVAILABLE=false api
   ```

   Mantenha esse comando em execução. PostgreSQL e RabbitMQ permanecem ativos.

2. No PowerShell da sessão manual, abra outro chamado:

   ```powershell
   $pendingKey = "pending-$([guid]::NewGuid())"
   $headers["Idempotency-Key"] = $pendingKey
   $pendingBody = @{
     customerId = $customerId
     contractId = $contractId
     serviceCode = "RENTAL-FLEX"
     category = "QUESTION"
     description = "Consulta durante indisponibilidade de Contracts"
   } | ConvertTo-Json

   $pendingTicket = Invoke-RestMethod -Method Post `
     -Uri "$baseUrl/api/v1/support/tickets" `
     -Headers $headers -Body $pendingBody
   $pendingTicketId = $pendingTicket.ticketId
   $pendingTicket

   Invoke-RestMethod -Method Post `
     -Uri "$baseUrl/api/v1/integration/outbox/dispatch" `
     -Headers $headers
   ```

   Verifique `status: PENDING_ENTITLEMENT`, `slaHours: null` e `dueAt: null`. O
   despacho inicia a resolução em Workflow com o prazo provisório de 24 horas
   contado da abertura do chamado (`openedAt`), não da hora do despacho.

3. Interrompa o contêiner temporário com `Ctrl+C` e restaure a API normal:

   ```powershell
   docker compose up -d api
   Invoke-RestMethod http://localhost:8000/health/ready
   ```

4. Reconcilie o chamado capturado:

   ```powershell
   $reconciled = Invoke-RestMethod -Method Post `
     -Uri "$baseUrl/api/v1/support/tickets/$pendingTicketId/reconcile" `
     -Headers $headers
   $reconciled
   ```

   O chamado deve mudar para `OPEN`, receber `slaHours: 8` e `dueAt` igual a
   `openedAt` + 8 h (o tempo de indisponibilidade não estende o SLA). Repetir o
   comando devolve o mesmo corpo com `Idempotency-Replayed: true`. Se Contracts
   ainda estiver fora, a resposta é `503 SERVICE_UNAVAILABLE` e o chamado continua
   pendente. Após um novo despacho, Workflow ajusta o prazo do processo de
   resolução para o `dueAt` reconciliado (ou cancela o processo, se a elegibilidade
   for rejeitada).

5. Para vários chamados pendentes, use a reconciliação em lote:

   ```powershell
   Invoke-RestMethod -Method Post `
     -Uri "$baseUrl/api/v1/support/tickets/reconcile-pending" -Headers $headers
   ```

   A resposta informa `confirmed`, `rejected`, `remaining` e
   `contractsAvailable`. Repetir a operação não altera chamados já reconciliados.

Em 14/10/2026 a mesma sequência (abertura, SLA, atribuição/reatribuição,
resolução idempotente, chamados pendentes, `503`, reconciliação individual e em
lote, com reinício do servidor entre as fases) foi executada contra `uvicorn`
local por um cliente HTTP em Python; os comandos PowerShell acima não foram
executados nesse ambiente. Ver `docs/EVIDENCIAS_VALIDACAO.md`, seção T15.

## Demonstrar falha permanente

O protótipo não expõe uma chave de configuração ou rota para fazer um consumidor
falhar sob demanda. Use o cenário automatizado que injeta um consumidor com falha,
executa três tentativas, consulta a falha e agenda o reprocessamento:

```powershell
$env:PYTHONPATH = "src"
./.venv/Scripts/python.exe -m pytest -q `
  tests/test_flows.py::test_falha_permanente_pode_ser_listada_e_reprocessada `
  -p no:cacheprovider
```

O teste deve passar. Ele verifica o estado `FAILED`, três tentativas, a presença do
evento em `GET /api/v1/integration/failures` e o retorno ao estado `PENDING` por
`POST /api/v1/integration/failures/{eventId}/reprocess`.

Cada chamada ao dispatcher representa uma tentativa. O protótipo não implementa
agendamento, atraso exponencial ou jitter.

### Com o broker indisponível

Somente na pilha isolada da demonstração (`-p archcorp-demo`):

1. Ative um contrato e pare o broker: `docker compose -p archcorp-demo stop rabbitmq`.
2. `GET /health/ready` informa `broker: DOWN`; despache a outbox: `failed: 1`, sem
   fatura nem processo para o contrato (os consumidores são desfeitos com a
   publicação recusada).
3. Repita o despacho até o limite de tentativas (3): o evento passa a `FAILED` e
   aparece em Falhas de integração.
4. Suba o broker (`docker compose -p archcorp-demo start rabbitmq`) e espere
   `broker: UP` na prontidão.
5. Reprocesse a falha e despache: `processed: 1`; um novo despacho devolve
   `processed: 0`. Há uma fatura e um processo para o contrato, e uma cópia na fila
   `archcorp.events`.

O roteiro equivalente é automatizado em
`tests/test_rabbitmq_real.py::test_broker_indisponivel_nao_deixa_efeito_e_reprocessamento_recupera`
(job `rabbitmq` da CI). `FAILED` é estado da aplicação, não fila de erro do broker.

## Executar os fluxos pela interface

A interface em `http://localhost:8000/` cobre F1, F2 e F3 sem terminal. Informe
`demo-admin` na tela de acesso (no modo público, a credencial configurada no
provedor). A navegação lateral leva a Visão geral, CRM, Reservas e contratos,
Financeiro, Atendimento e Workflow; cada aviso de sucesso ou erro exibe o
`correlationId` da requisição.

1. **F1.** Em CRM, cadastre um cliente fictício. Na linha do cliente, use
   **Nova reserva**: a tela Reservas e contratos abre com o mesmo cliente
   selecionado. Registre a reserva e, na tabela Reservas, use **Gerar rascunho**.
   O contrato aparece como "Rascunho" para o mesmo cliente, sem recadastro.
2. **F2.** Em Contratos, use **Ativar**. Em Financeiro (ou Visão geral/Workflow),
   use **Despachar eventos pendentes**: surge a fatura "Em aberto" e, em Workflow,
   a "Preparação de retirada". Selecione a fatura e registre um pagamento simulado
   parcial: a fatura passa a "Parcialmente paga". No cartão **Verificar vencimento
   e registrar inadimplência**, informe uma data posterior ao vencimento (requer
   `FINANCE_ALLOW_FUTURE_AS_OF=true` na API) e verifique: a coluna Inadimplência
   mostra "Registrada em …". Pague o saldo restante: a fatura fica "Paga".
3. **F3.** Em Contratos, use **Abrir chamado** no contrato ativo. Em Atendimento,
   use **Consultar elegibilidade e SLA**, abra o chamado, despache os eventos,
   atribua (e, se quiser, reatribua) um responsável e resolva. A coluna **SLA**
   mostra "No prazo", "Vencido", "Cumprido", "SLA pendente" ou "Sem SLA", e
   **Histórico** lista abertura, atribuições, reconciliação e resolução. Um novo
   despacho conclui o processo de resolução em Workflow. Chamados com elegibilidade
   pendente podem ser reconciliados um a um ou por **Reconciliar pendentes**.
4. **Erros legíveis.** Registre uma reserva com fim anterior ao início (`422`
   com a regra violada) ou um contato com telefone fora do E.164 (`422` com o
   campo). Saia e entre com `demo-support` para ver `403` ao cadastrar cliente.
   Uma credencial inexistente mostra `401` na tela de acesso.
5. **Trilha.** Copie o `correlationId` de um aviso e consulte-o em Visão geral,
   no cartão "Trilha por correlação".

Os comandos com repetição segura (reserva, rascunhos, ativação, encerramento,
abertura de chamado e pagamento simulado) enviam `Idempotency-Key`. A interface só reaproveita a chave
quando a nova tentativa da mesma ação envia exatamente o mesmo corpo (por exemplo,
após uma falha de rede ambígua); se o usuário corrigir algum campo, uma chave nova
é gerada, evitando `409 IDEMPOTENCY_CONFLICT`. A chave é descartada após sucesso e
após receber `409 IDEMPOTENCY_CONFLICT`. Quando a API indica
`Idempotency-Replayed: true`, o aviso informa a repetição idempotente.

## Mostrar observabilidade e segurança

1. Consulte a correlação usada na sessão:

   ```powershell
   Invoke-RestMethod `
     -Uri "$baseUrl/api/v1/operations/$correlationId" `
     -Headers $headers | ConvertTo-Json -Depth 8
   ```

   Mostre auditorias e eventos com o mesmo `correlationId`. Operações feitas com
   outra correlação não aparecem nessa resposta.

2. Consulte as métricas:

   ```powershell
   Invoke-WebRequest "$baseUrl/metrics" -Headers $headers | Select-Object -ExpandProperty Content
   ```

3. Demonstre a autorização por papel:

   ```powershell
   $supportHeaders = @{
     Authorization = "Bearer demo-support"
     "Content-Type" = "application/json"
     "X-Correlation-ID" = $correlationId
   }
   try {
     Invoke-RestMethod -Method Post `
       -Uri "$baseUrl/api/v1/crm/customers" `
       -Headers $supportHeaders -Body $customerBody
   } catch {
     $_.Exception.Response.StatusCode.value__
   }
   ```

   A resposta deve ter código `403`.

4. Consulte os logs sem exibi-los integralmente em material público:

   ```powershell
   docker compose logs --since 10m api
   ```

   Confirme que os logs não contêm token, documento pessoal, dado bancário nem a
   descrição enviada no chamado.

## Registrar as evidências

Ao encerrar a apresentação, registre:

- data, máquina e versão do código;
- `customerId`, `contractId`, `ticketId`, `eventId` e `correlationId` usados;
- estado antes e depois de F2 e F3;
- respostas de replay e diferenças de contagem;
- resultado do teste de falha permanente;
- resultado da suíte automatizada e da medição de desempenho.

Interrompa os serviços quando não precisar mais do ambiente:

```powershell
docker compose down
```

Esse comando preserva o volume do PostgreSQL. Remover o volume apagaria os dados
da demonstração e não faz parte deste roteiro.
