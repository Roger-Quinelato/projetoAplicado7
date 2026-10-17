# Instala o cliente (wrapper) do ai-memory no Windows nativo e conecta o Claude Code.
# Pré-requisito: Docker Desktop em execução. Execute no PowerShell a partir desta pasta:
#   .\instalar-windows.ps1
# Fonte: https://github.com/akitaonrails/ai-memory/blob/main/docs/windows.md
# O suporte nativo ao Windows é experimental; se falhar, use instalar-wsl.sh dentro do WSL2.
$ErrorActionPreference = "Stop"

# 1. Instalar o wrapper com verificação de checksum
$UserBin = "$HOME\bin"
New-Item -ItemType Directory -Force $UserBin | Out-Null
$ReleaseBase = "https://github.com/akitaonrails/ai-memory/releases/latest/download"
$WrapperAssets = @{
    "ai-memory.ps1" = "ai-memory-wrapper.ps1"
    "ai-memory.cmd" = "ai-memory-wrapper.cmd"
}
foreach ($Entry in $WrapperAssets.GetEnumerator()) {
    $File = $Entry.Key
    $Asset = $Entry.Value
    Invoke-WebRequest -Uri "$ReleaseBase/$Asset" -OutFile "$UserBin\$File"
    Invoke-WebRequest -Uri "$ReleaseBase/$Asset.sha256" -OutFile "$UserBin\$File.sha256"
    $Expected = ((Get-Content "$UserBin\$File.sha256" -Raw) -split '\s+')[0]
    $Actual = (Get-FileHash "$UserBin\$File" -Algorithm SHA256).Hash.ToLower()
    if ($Actual -ne $Expected.ToLower()) {
        throw "Checksum divergente em $Asset"
    }
    Remove-Item "$UserBin\$File.sha256"
}
Get-ChildItem "$UserBin\ai-memory.*" | Unblock-File

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (($UserPath -split ';') -notcontains $UserBin) {
    $NewUserPath = (($UserPath, $UserBin) | Where-Object { $_ }) -join ";"
    [Environment]::SetEnvironmentVariable("Path", $NewUserPath, "User")
    $env:Path = "$env:Path;$UserBin"
}

# 2. Subir o servidor (container). Não rode também `ai-memory serve`.
docker compose -f "$PSScriptRoot\docker-compose.yml" up -d

# 3. Verificar e conectar o Claude Code
ai-memory status
ai-memory install-mcp --client claude-code --apply
ai-memory install-hooks --agent claude-code --apply

Write-Host "Pronto. Reinicie o Claude Code e verifique com a ferramenta memory_status."
