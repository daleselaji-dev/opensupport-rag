param(
  [int]$Port = 18001
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$releasePath = Join-Path $root 'reports\release_check_latest.json'
if (-not (Test-Path -LiteralPath $releasePath)) {
  throw '找不到 reports/release_check_latest.json；先运行 scripts/release_check.py。'
}
$release = Get-Content -LiteralPath $releasePath -Raw | ConvertFrom-Json
if (-not $release.release_ready) {
  $failed = @($release.checks | Where-Object { -not $_.passed } | ForEach-Object { $_.key }) -join ', '
  throw "Release gate 未通过，拒绝启动 V1 Agent。失败项：$failed"
}

$env:AGENT_ENABLED = 'true'
$env:PYTHONPATH = $root
Write-Host "Starting the isolated V1 controlled Agent on http://127.0.0.1:$Port"
Write-Host 'Only whitelisted retrieval and local draft tools are enabled; external actions remain forbidden.'
& (Join-Path $root '.venv\Scripts\python.exe') -m uvicorn app.main:app --host 127.0.0.1 --port $Port
