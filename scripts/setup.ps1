$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the project virtual environment.' }
    }
    $projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
    $dependencyFile = if (Test-Path -LiteralPath 'requirements.lock.txt') { 'requirements.lock.txt' } else { 'requirements.in' }
    & $projectPython -m pip install --disable-pip-version-check --retries 0 --timeout 15 -r $dependencyFile
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check network access, then rerun this script.' }
    $installed = & $projectPython -m pip freeze
    if ($LASTEXITCODE -ne 0) { throw 'Could not record installed package versions.' }
    Set-Content -LiteralPath 'requirements.lock.txt' -Value $installed -Encoding utf8
    & $projectPython scripts/check_environment.py
    if ($LASTEXITCODE -ne 0) { throw 'Environment verification failed.' }
} finally {
    Pop-Location
}
