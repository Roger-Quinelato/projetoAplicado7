# F-SEG: sobe ou encerra o uvicorn da cópia isolada (porta 18101). Uso:
#   powershell -NoProfile -ExecutionPolicy Bypass -File seg_servidor.ps1 -Acao start -Modo local|publico
#   powershell -NoProfile -ExecutionPolicy Bypass -File seg_servidor.ps1 -Acao stop -Modo local|publico
# O modo publico gera um DEMO_ACCESS_TOKEN aleatório, grava-o só em tmp/ da cópia e não o imprime.
param(
  [Parameter(Mandatory = $true)][ValidateSet('start', 'stop')][string]$Acao,
  [ValidateSet('local', 'publico')][string]$Modo = 'local',
  [int]$Porta = 18101
)
$ErrorActionPreference = 'Stop'
$iso = 'C:\Users\roger\.claude\jobs\f5019419\tmp\iso-seg'
$py = 'C:\Users\roger\.claude\jobs\f5019419\tmp\venv-auditoria\Scripts\python.exe'
$logs = 'C:\Users\roger\projetoAplicado7\.claude\worktrees\auditoria-2026-10-18\output\auditoria\2026-10-18T2018Z\evidencias\seg\logs'
$pidFile = Join-Path $logs "uvicorn_${Modo}_${Porta}.pid"

if ($Acao -eq 'stop') {
  if (Test-Path $pidFile) {
    $alvo = [int](Get-Content $pidFile)
    Stop-Process -Id $alvo -Force -ErrorAction SilentlyContinue
    Remove-Item $pidFile -Force
  }
  Start-Sleep -Milliseconds 1000
  $escuta = $null -ne (Get-NetTCPConnection -LocalPort $Porta -State Listen -ErrorAction SilentlyContinue)
  "porta $Porta em escuta apos encerramento: $escuta"
  return
}

Remove-Item Env:RABBITMQ_URL -ErrorAction SilentlyContinue
$env:PYTHONPATH = "$iso\src"
$env:DATABASE_URL = "sqlite:///C:/Users/roger/.claude/jobs/f5019419/tmp/iso-seg/tmp/servidor_$Modo.db"
if (Test-Path "$iso\tmp\servidor_$Modo.db") { Remove-Item "$iso\tmp\servidor_$Modo.db" -Force }
if ($Modo -eq 'publico') {
  $token = (New-Guid).ToString('N') + (New-Guid).ToString('N')
  Set-Content -Path "$iso\tmp\seg_token_publico.txt" -Value $token -NoNewline -Encoding ascii
  $env:PUBLIC_DEMO = 'true'
  $env:DEMO_ACCESS_TOKEN = $token
} else {
  Remove-Item Env:PUBLIC_DEMO -ErrorAction SilentlyContinue
  Remove-Item Env:DEMO_ACCESS_TOKEN -ErrorAction SilentlyContinue
}
$out = Join-Path $logs "uvicorn_${Modo}_${Porta}.stdout.log"
$err = Join-Path $logs "uvicorn_${Modo}_${Porta}.stderr.log"
$p = Start-Process -FilePath $py -ArgumentList @('-m', 'uvicorn', 'archcorp.main:app', '--host', '127.0.0.1', '--port', "$Porta") `
  -WorkingDirectory $iso -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -WindowStyle Hidden
$p.Id | Set-Content -Path $pidFile -Encoding ascii
for ($i = 0; $i -lt 90; $i++) {
  Start-Sleep -Milliseconds 500
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Porta/health/live" -UseBasicParsing -TimeoutSec 3
    if ($r.StatusCode -eq 200) { "servidor $Modo pronto na porta $Porta (pid $($p.Id))"; return }
  } catch { }
}
throw "servidor $Modo não respondeu na porta $Porta"
