param(
    [switch]$EnableCodeExecution
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $RepoRoot ".runtime"
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$WebRoot = Join-Path $RepoRoot "apps\web"
$ViteEntry = Join-Path $WebRoot "node_modules\vite\bin\vite.js"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "尚未完成环境准备，请先运行 .\scripts\setup_demo.ps1。"
}
if (-not (Test-Path -LiteralPath $ViteEntry)) {
    throw "前端依赖不完整，请先运行 .\scripts\setup_demo.ps1。"
}
$Node = Get-Command node -ErrorAction Stop

foreach ($Port in @(3000, 8000)) {
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
        throw "端口 $Port 已被占用，请先停止旧演示服务。"
    }
}
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

$env:DATABASE_URL = if ($env:DATABASE_URL) {
    $env:DATABASE_URL
} else {
    "postgresql+psycopg://ciyuan:replace-before-use@127.0.0.1:5432/ciyuan?connect_timeout=3"
}
$env:CODE_EXECUTION_ENABLED = if ($EnableCodeExecution) { "true" } else { "false" }

$Backend = Start-Process -FilePath $Python `
    -ArgumentList @("-m", "uvicorn", "apps.api.app.main:app", "--host", "127.0.0.1", "--port", "8000") `
    -WorkingDirectory $RepoRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $RuntimeDir "api.out.log") `
    -RedirectStandardError (Join-Path $RuntimeDir "api.err.log")
$Web = Start-Process -FilePath $Node.Source `
    -ArgumentList @($ViteEntry, "--host", "0.0.0.0", "--port", "3000") -WorkingDirectory $WebRoot `
    -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $RuntimeDir "web.out.log") `
    -RedirectStandardError (Join-Path $RuntimeDir "web.err.log")

Set-Content -LiteralPath (Join-Path $RuntimeDir "api.pid") -Value $Backend.Id
Set-Content -LiteralPath (Join-Path $RuntimeDir "web.pid") -Value $Web.Id

$Ready = $false
for ($Attempt = 1; $Attempt -le 20; $Attempt++) {
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" -TimeoutSec 2 | Out-Null
        $Ready = $true
        break
    } catch {
        Start-Sleep -Milliseconds 500
    }
}
if (-not $Ready) {
    if (Get-Process -Id $Backend.Id -ErrorAction SilentlyContinue) { Stop-Process -Id $Backend.Id }
    if (Get-Process -Id $Web.Id -ErrorAction SilentlyContinue) { Stop-Process -Id $Web.Id }
    throw "API 未在预期时间内启动，请查看 .runtime\api.err.log。"
}

$WebReady = $false
for ($Attempt = 1; $Attempt -le 20; $Attempt++) {
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:3000" -TimeoutSec 2 -UseBasicParsing | Out-Null
        $WebReady = $true
        break
    } catch {
        Start-Sleep -Milliseconds 500
    }
}
if (-not $WebReady) {
    if (Get-Process -Id $Backend.Id -ErrorAction SilentlyContinue) { Stop-Process -Id $Backend.Id }
    if (Get-Process -Id $Web.Id -ErrorAction SilentlyContinue) { Stop-Process -Id $Web.Id }
    throw "前端未在预期时间内启动，请查看 .runtime\web.err.log。"
}

Write-Host "词元研究所已启动：http://localhost:3000"
Write-Host "API 文档：http://127.0.0.1:8000/docs"
Write-Host "停止服务：.\scripts\stop_demo.ps1"
