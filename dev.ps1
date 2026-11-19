param(
    [switch]$Backend,
    [switch]$Frontend,
    [switch]$Test,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $RepoRoot "backend\.venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    $PythonBin = $VenvPython
} elseif (Get-Command python3.11 -ErrorAction SilentlyContinue) {
    $PythonBin = "python3.11"
} else {
    $PythonBin = "python"
}

$ScriptArgs = @()
if ($Backend)  { $ScriptArgs += "--backend" }
if ($Frontend) { $ScriptArgs += "--frontend" }
if ($Test)     { $ScriptArgs += "--test" }
if ($Help)     { $ScriptArgs += "--help" }

& $PythonBin (Join-Path $RepoRoot "scripts\dev.py") @ScriptArgs
exit $LASTEXITCODE
