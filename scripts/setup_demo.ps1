param(
    [switch]$PullSandboxImages
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

Push-Location $RepoRoot
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "未找到 Docker CLI，请先安装并启动 Docker Desktop。"
    }
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Desktop 尚未就绪，请启动后重新运行。"
    }

    if (-not (Test-Path -LiteralPath $Python)) {
        py -3.11 -m venv .venv
    }
    & $Python -m pip install -e ".[dev]"

    Push-Location (Join-Path $RepoRoot "apps\web")
    try {
        npm ci
        if ($LASTEXITCODE -ne 0) { throw "前端依赖安装失败。" }
    } finally { Pop-Location }

    docker compose -f infra/compose.yaml up -d postgres redis
    if ($LASTEXITCODE -ne 0) { throw "PostgreSQL/Redis 启动失败。" }

    $env:DATABASE_URL = if ($env:DATABASE_URL) {
        $env:DATABASE_URL
    } else {
        "postgresql+psycopg://ciyuan:replace-before-use@127.0.0.1:5432/ciyuan?connect_timeout=3"
    }
    & $Python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw "数据库迁移失败。" }
    & $Python scripts/sync_knowledge_index.py
    if ($LASTEXITCODE -ne 0) { throw "RAG 审核来源同步失败。" }

    if ($PullSandboxImages) {
        docker pull python:3.11.15-alpine3.24
        docker pull gcc:13.4.0-bookworm
    }

    & $Python scripts/validate_course_pack.py
    Write-Host "演示环境准备完成。下一步运行：.\scripts\run_demo.ps1 -EnableCodeExecution"
} finally {
    Pop-Location
}
