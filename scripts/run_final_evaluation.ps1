$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$candidates = @()
if ($env:CODEX_PRIMARY_RUNTIME_PYTHON) { $candidates += $env:CODEX_PRIMARY_RUNTIME_PYTHON }
$candidates += (Join-Path $projectRoot '.venv-model/Scripts/python.exe')
$candidates += (Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
$analysisPython = $null
foreach ($candidate in $candidates) {
    if (-not (Test-Path -LiteralPath $candidate)) { continue }
    & $candidate -B -c 'import pandas,numpy,reportlab,PIL'
    if ($LASTEXITCODE -eq 0) { $analysisPython = $candidate; break }
}
if (-not $analysisPython) { throw 'No Python with analysis/graphics dependencies was found.' }
$nodeExecutable = if ($env:CODEX_PRIMARY_RUNTIME_NODE) { $env:CODEX_PRIMARY_RUNTIME_NODE } else { Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' }
Push-Location -LiteralPath $projectRoot
try {
    foreach ($script in @('evaluate_final_test.py','report_final_evaluation.py')) {
        & $analysisPython -B (Join-Path 'scripts' $script)
        if ($LASTEXITCODE -ne 0) { throw "Final evaluation stage failed: $script" }
    }
    & $nodeExecutable scripts/render_charts.mjs 16_final_test_comparison.svg
    if ($LASTEXITCODE -ne 0) { throw 'Figure rendering failed.' }
    & $analysisPython -B scripts/verify_final_delivery.py
    if ($LASTEXITCODE -ne 0) { throw 'Final delivery verification failed.' }
} finally { Pop-Location }
