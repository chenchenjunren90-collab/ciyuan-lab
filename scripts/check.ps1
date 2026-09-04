param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot
try {
    & $Python scripts/validate_course_pack.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & $Python scripts/validate_repository.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & $Python -m ruff check apps/api scripts
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & $Python -m mypy apps/api
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & $Python -m pytest
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Push-Location apps/web
    try {
        npm run check
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    finally {
        Pop-Location
    }
}
finally {
    Pop-Location
}

Write-Host "All repository checks passed."
