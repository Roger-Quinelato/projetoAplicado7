$ErrorActionPreference = "Stop"
$base = "http://localhost:8000"
$headers = @{ Authorization = "Bearer demo-admin"; "Content-Type" = "application/json" }
$correlation = [guid]::NewGuid().ToString()
$headers["X-Correlation-ID"] = $correlation

$customer = Invoke-RestMethod -Method Post -Uri "$base/api/v1/crm/customers" -Headers $headers -Body (@{
  name = "Cliente Demonstração"; email = "demo@example.com"; eligible = $true; consentService = $true; legacyId = "CRM-1001"
} | ConvertTo-Json)

$headers["Idempotency-Key"] = "demo-contract-001"
$contract = Invoke-RestMethod -Method Post -Uri "$base/api/v1/contracts/drafts" -Headers $headers -Body (@{
  customerId = $customer.customerId; serviceCode = "SUPPORT-PREMIUM"; startsOn = "2026-10-01"
  billing = @{ amount = 2500.00; currency = "BRL"; cycle = "MONTHLY" }; slaHours = 8
} | ConvertTo-Json -Depth 4)

$headers["Idempotency-Key"] = "demo-activate-001"
Invoke-RestMethod -Method Post -Uri "$base/api/v1/contracts/$($contract.contractId)/activate" -Headers $headers | Out-Null
Invoke-RestMethod -Method Post -Uri "$base/api/v1/integration/outbox/dispatch" -Headers $headers | Out-Null

$headers["Idempotency-Key"] = "demo-ticket-001"
$ticket = Invoke-RestMethod -Method Post -Uri "$base/api/v1/support/tickets" -Headers $headers -Body (@{
  customerId = $customer.customerId; contractId = $contract.contractId; serviceCode = "SUPPORT-PREMIUM"
  category = "OUTAGE"; description = "Serviço indisponível para a demonstração"
} | ConvertTo-Json)
Invoke-RestMethod -Method Post -Uri "$base/api/v1/integration/outbox/dispatch" -Headers $headers | Out-Null

Write-Host "Cliente: $($customer.customerId)"
Write-Host "Contrato: $($contract.contractId)"
Write-Host "Chamado: $($ticket.ticketId)"
Write-Host "Correlação: $correlation"
Invoke-RestMethod -Method Get -Uri "$base/api/v1/demo/state" -Headers $headers | ConvertTo-Json
