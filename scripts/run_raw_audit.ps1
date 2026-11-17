$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$candidatePythons = @()
if ($env:CODEX_PRIMARY_RUNTIME_PYTHON) { $candidatePythons += $env:CODEX_PRIMARY_RUNTIME_PYTHON }
$candidatePythons += (Join-Path $projectRoot '.venv\Scripts\python.exe')
$candidatePythons += (Join-Path $projectRoot '.venv-audit\Scripts\python.exe')
$candidatePythons += (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
$auditPython = $null
foreach ($candidatePython in ($candidatePythons | Select-Object -Unique)) {
    if (Test-Path -LiteralPath $candidatePython) {
        & $candidatePython -c 'import importlib.util, sys; sys.exit(0 if all(importlib.util.find_spec(name) for name in ["pandas", "numpy", "openpyxl"]) else 1)'
        if ($LASTEXITCODE -eq 0) { $auditPython = $candidatePython; break }
    }
}
if (-not $auditPython) { throw 'No available Python has pandas, numpy and openpyxl. Run scripts/setup.ps1 when network access is available.' }
Push-Location -LiteralPath $projectRoot
try {
    Write-Output "Using audit Python: $auditPython"
    & $auditPython scripts/download_data.py
    if ($LASTEXITCODE -ne 0) { throw 'Dataset acquisition or raw integrity verification failed.' }
    & $auditPython scripts/check_environment.py
    if ($LASTEXITCODE -ne 0) { throw 'Environment recording failed.' }
    & $auditPython scripts/audit_data.py
    if ($LASTEXITCODE -ne 0) { throw 'Raw audit failed.' }
    & $auditPython scripts/report_raw_audit.py
    if ($LASTEXITCODE -ne 0) { throw 'Raw audit report generation failed.' }
} finally {
    Pop-Location
}
