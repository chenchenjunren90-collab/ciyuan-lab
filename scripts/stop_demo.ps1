param(
    [switch]$StopDataServices
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $RepoRoot ".runtime"
$Skipped = $false

foreach ($Name in @("api", "web")) {
    $PidPath = Join-Path $RuntimeDir "$Name.pid"
    if (Test-Path -LiteralPath $PidPath) {
        try {
            $Record = Get-Content -LiteralPath $PidPath -Raw | ConvertFrom-Json
            if ($Record.Version -ne 1 -or -not $Record.Processes) {
                throw "缺少进程创建时间，无法安全确认旧 PID 的归属。"
            }
            $Processes = @($Record.Processes)
            foreach ($Identity in $Processes) {
                if ($Identity.Id -le 0 -or "$($Identity.StartTimeUtcTicks)" -notmatch '^\d+$') {
                    throw "进程记录格式无效。"
                }
            }
            # Children are recorded after their launcher; stop them first.
            [array]::Reverse($Processes)
            foreach ($Identity in $Processes) {
                $Process = Get-Process -Id $Identity.Id -ErrorAction SilentlyContinue
                if ($Process -and $Process.StartTime.ToUniversalTime().Ticks.ToString() -eq $Identity.StartTimeUtcTicks) {
                    $Process | Stop-Process -ErrorAction Stop
                }
            }
            Remove-Item -LiteralPath $PidPath
        } catch {
            $Skipped = $true
            Write-Warning "已跳过 $Name 服务的停止操作：$_"
        }
    }
}

if ($StopDataServices) {
    Push-Location $RepoRoot
    try { docker compose -f infra/compose.yaml stop postgres redis } finally { Pop-Location }
}
if ($Skipped) {
    Write-Host "停止操作完成；部分旧进程记录无法确认归属，请查看上述警告。"
} else {
    Write-Host "演示服务已停止。"
}
