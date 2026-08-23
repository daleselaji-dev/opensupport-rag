$ErrorActionPreference = "Continue"

Write-Host "OpenSupport RAG local readiness check" -ForegroundColor Cyan

function Get-EnvValue([string]$Name, [string]$Fallback) {
    if (Test-Path .env) {
        $line = Get-Content .env | Where-Object { $_ -match "^$Name=" } | Select-Object -First 1
        if ($line) { return ($line -split "=", 2)[1] }
    }
    return $Fallback
}

$chatBase = Get-EnvValue "CHAT_BASE_URL" "http://localhost:1234/v1"
$qdrantBase = Get-EnvValue "QDRANT_URL" "http://localhost:6333"

try {
    $models = Invoke-RestMethod -Uri "$($chatBase.TrimEnd('/'))/models" -TimeoutSec 3
    Write-Host "LM Studio: ready" -ForegroundColor Green
    $models.data | Select-Object id | Format-Table -AutoSize
} catch {
    Write-Host "LM Studio: offline. Open LM Studio > Developer > Start server." -ForegroundColor Yellow
}

try {
    $qdrant = Invoke-RestMethod -Uri "$($qdrantBase.TrimEnd('/'))/healthz" -TimeoutSec 3
    Write-Host "Qdrant: ready" -ForegroundColor Green
} catch {
    Write-Host "Qdrant: offline. Start Docker Desktop, then run: docker compose up -d qdrant" -ForegroundColor Yellow
}

if (Test-Path .env) {
    Write-Host "Configured model identifiers:" -ForegroundColor Cyan
    Get-Content .env | Where-Object { $_ -match '^(CHAT_MODEL|EMBEDDING_MODEL|EMBEDDING_FAMILY)=' }
} else {
    Write-Host ".env missing. Run: Copy-Item .env.example .env" -ForegroundColor Yellow
}
