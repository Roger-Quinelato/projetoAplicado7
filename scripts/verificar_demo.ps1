# Verificação antes da demonstração do ArchCorp (Windows PowerShell).
#
# Confere, contra a API já no ar, tudo o que precisa funcionar diante da banca:
# prontidão, token, os três fluxos (F1, F2 e F3) e o relatório operacional.
# Não apaga dados. Os roteiros criam registros sintéticos novos a cada execução.
#
# Uso, na raiz do repositório:
#   ./scripts/verificar_demo.ps1                       # http://localhost:8000 com demo-admin
#   ./scripts/verificar_demo.ps1 -BaseUrl http://localhost:8000 -Token demo-admin
#
# Saída 0 quando tudo passa; 1 quando alguma checagem falha.
param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$Token = "demo-admin"
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
$python = if (Test-Path ".venv/Scripts/python.exe") { ".venv/Scripts/python.exe" } else { "python" }
$env:PYTHONPATH = "src"
New-Item -ItemType Directory -Force tmp | Out-Null
$resultados = [System.Collections.Generic.List[object]]::new()

function Registrar([string]$Checagem, [bool]$Ok, [string]$Detalhe) {
    $resultados.Add([pscustomobject]@{ Checagem = $Checagem; Resultado = $(if ($Ok) { "OK" } else { "FALHA" }); Detalhe = $Detalhe })
}

$commit = (git rev-parse --short HEAD).Trim()
$alteracoes = (git status --porcelain --untracked-files=no)
Registrar "Commit demonstrado" ([string]::IsNullOrEmpty($alteracoes)) "$commit$(if ($alteracoes) { ' com alterações não commitadas' })"

try {
    $pronto = Invoke-RestMethod "$BaseUrl/health/ready" -TimeoutSec 10
    Registrar "API pronta (/health/ready)" ($pronto.status -eq "UP") "banco $($pronto.database)$(if ($pronto.broker) { ", broker $($pronto.broker)" })"
} catch {
    Registrar "API pronta (/health/ready)" $false "API inacessível em $BaseUrl"
    $resultados | Format-Table -AutoSize
    exit 1
}

try {
    $estado = Invoke-RestMethod "$BaseUrl/api/v1/demo/state" -Headers @{ Authorization = "Bearer $Token" } -TimeoutSec 10
    Registrar "Token aceito" $true "clientes $($estado.customers), contratos $($estado.contracts), chamados $($estado.tickets)"
} catch {
    Registrar "Token aceito" $false "o token não acessa /api/v1/demo/state (exige papel admin)"
}

try {
    $interface = Invoke-WebRequest "$BaseUrl/" -UseBasicParsing -TimeoutSec 10
    Registrar "Interface servida" ($interface.Content -match "<div id=") "rode 'npm run build' em web/ se falhar"
} catch {
    Registrar "Interface servida" $false "web/dist ausente: rode 'npm run build' em web/ e reinicie a API"
}

foreach ($fluxo in "f1", "f2", "f3") {
    & $python "scripts/demo_$fluxo.py" --base-url $BaseUrl --token $Token *> "tmp/verificar_demo_$fluxo.log"
    $codigo = $LASTEXITCODE
    Registrar "Fluxo $($fluxo.ToUpper())" ($codigo -eq 0) "saída $codigo; log em tmp/verificar_demo_$fluxo.log"
}

& $python "scripts/relatorio_operacional.py" --base-url $BaseUrl --token $Token *> "tmp/verificar_demo_relatorio.log"
Registrar "Relatório operacional" ($LASTEXITCODE -eq 0) "output/insights/relatorio_operacional.md"

$resultados | Format-Table -AutoSize
if ($resultados.Resultado -contains "FALHA") {
    Write-Host "Há checagens com falha. Corrija antes da demonstração." -ForegroundColor Red
    exit 1
}
Write-Host "Pronto para a demonstração no commit $commit." -ForegroundColor Green
exit 0
