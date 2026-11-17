$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$candidates = @()
if ($env:CODEX_PRIMARY_RUNTIME_PYTHON) { $candidates += $env:CODEX_PRIMARY_RUNTIME_PYTHON }
$candidates += (Join-Path $projectRoot '.venv\Scripts\python.exe')
$candidates += (Join-Path $projectRoot '.venv-audit\Scripts\python.exe')
$candidates += (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
$preparationPython = $null
foreach ($candidate in ($candidates | Select-Object -Unique)) {
    if (Test-Path -LiteralPath $candidate) {
        & $candidate -c 'import importlib.util, sys; sys.exit(0 if all(importlib.util.find_spec(name) for name in ["pandas", "numpy", "openpyxl"]) else 1)'
        if ($LASTEXITCODE -eq 0) { $preparationPython = $candidate; break }
    }
}
if (-not $preparationPython) { throw 'No available Python has pandas, numpy and openpyxl.' }
Push-Location -LiteralPath $projectRoot
try {
    Write-Output "Using preparation Python: $preparationPython"
    & $preparationPython scripts/prepare_data.py
    if ($LASTEXITCODE -ne 0) { throw 'Data preparation failed; do not use partial outputs.' }
    if (Test-Path -LiteralPath 'scripts/report_preparation.py') {
        & $preparationPython scripts/report_preparation.py
        if ($LASTEXITCODE -ne 0) { throw 'Preparation report generation failed.' }
    }
} finally { Pop-Location }
