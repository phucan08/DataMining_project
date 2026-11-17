$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (Test-Path -LiteralPath (Join-Path $projectRoot 'results/models/final_evaluation_lock.json')) {
    throw 'Final evaluation artifacts are frozen. This training runner would overwrite them. Use scripts/evaluate_final_test.py to verify saved results.'
}
$candidates = @()
if ($env:CODEX_PRIMARY_RUNTIME_PYTHON) { $candidates += $env:CODEX_PRIMARY_RUNTIME_PYTHON }
$candidates += (Join-Path $projectRoot '.venv-model\Scripts\python.exe')
$candidates += (Join-Path $projectRoot '.venv-audit\Scripts\python.exe')
$candidates += (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
$modelPython = $null
foreach ($candidate in ($candidates | Select-Object -Unique)) {
    if (Test-Path -LiteralPath $candidate) {
        & $candidate -c 'import importlib.util, sys; sys.exit(0 if all(importlib.util.find_spec(n) for n in ["pandas", "numpy", "openpyxl", "reportlab", "PIL"]) else 1)'
        if ($LASTEXITCODE -eq 0) { $modelPython = $candidate; break }
    }
}
if (-not $modelPython) { throw 'No Python has the required analysis/graphics libraries.' }
$nodeExecutable = if ($env:CODEX_PRIMARY_RUNTIME_NODE) { $env:CODEX_PRIMARY_RUNTIME_NODE } else { Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' }
Push-Location -LiteralPath $projectRoot
try {
    foreach ($script in @('export_model_inputs.py','run_weka_fits.py','run_paired_benchmark.py','score_experiments.py','segment_experiments.py','create_figures.py')) {
        & $modelPython (Join-Path 'scripts' $script)
        if ($LASTEXITCODE -ne 0) { throw "Experiment stage failed: $script" }
    }
    & $nodeExecutable scripts/render_charts.mjs
    if ($LASTEXITCODE -ne 0) { throw 'PNG rendering failed.' }
    & $modelPython scripts/verify_experiments.py
    if ($LASTEXITCODE -ne 0) { throw 'Experiment verification failed.' }
    & $modelPython scripts/report_experiments.py
    if ($LASTEXITCODE -ne 0) { throw 'Report generation failed.' }
    & $modelPython -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
} finally { Pop-Location }
