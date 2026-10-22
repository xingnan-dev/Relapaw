param([Parameter(Mandatory=$true)][ValidateSet('backup','restore','status')] [string]$Action, [string]$Archive, [switch]$ConfirmRestore)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $repo 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Backend virtualenv Python is missing: $python" }
$arguments = @('-m', 'app.local_data', $Action)
if ($Archive) { $arguments += @('--archive', $Archive) }
if ($ConfirmRestore) { $arguments += '--confirm-restore' }
Push-Location (Join-Path $repo 'backend')
try { & $python @arguments; if ($LASTEXITCODE -ne 0) { throw "Local data command failed with exit code $LASTEXITCODE" } }
finally { Pop-Location }
