# Roteiro de demonstração

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
   `database: UP`.

3. Abra `http://localhost:8000/docs` para consultar o OpenAPI e
   `http://localhost:15672` para observar o RabbitMQ. O ambiente local usa
   `guest`/`guest` no painel do broker.

4. Execute a demonstração em um banco sem dados anteriores ou use chaves
   idempotentes novas, como nos comandos abaixo. O
   [`scripts/demo.ps1`](../scripts/demo.ps1) usa chaves fixas e deve ser executado
   apenas uma vez no mesmo banco.

## Executar o caminho principal automaticamente

Execute o script para criar cliente, contrato, cobrança, onboarding, chamado e
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
     name = "Empresa Demonstração"
     email = "demonstracao@example.com"
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
     serviceCode = "SUPPORT-PREMIUM"
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

## F2: ativar, cobrar e iniciar onboarding

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
   As duas diferenças finais devem valer `1`: uma cobrança e um onboarding.

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
     serviceCode = "SUPPORT-PREMIUM"
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

   Verifique `status: OPEN`, `priority: HIGH`, `slaHours: 8` e um `dueAt` em UTC.

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
     serviceCode = "SUPPORT-PREMIUM"
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
   despacho inicia a resolução em Workflow com o prazo padrão de 24 horas.

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

   O chamado deve mudar para `OPEN`, receber `slaHours: 8` e um novo `dueAt`. O
   protótipo não recalcula o prazo do processo de Workflow criado anteriormente.

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
   Invoke-WebRequest "$baseUrl/metrics" | Select-Object -ExpandProperty Content
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
