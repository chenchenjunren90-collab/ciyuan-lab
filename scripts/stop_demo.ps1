param(
    [switch]$StopDataServices
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $RepoRoot ".runtime"

foreach ($Name in @("api", "web")) {
    $PidPath = Join-Path $RuntimeDir "$Name.pid"
    if (Test-Path -LiteralPath $PidPath) {
        $ProcessId = [int](Get-Content -LiteralPath $PidPath)
        $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if ($Process) { Stop-Process -Id $ProcessId }
        Remove-Item -LiteralPath $PidPath
    }
}

if ($StopDataServices) {
    Push-Location $RepoRoot
    try { docker compose -f infra/compose.yaml stop postgres redis } finally { Pop-Location }
}
Write-Host "演示服务已停止。"
