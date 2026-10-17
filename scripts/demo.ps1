[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('start', 'verify', 'reset', 'stop')]
    [string]$Action = 'start',

    [ValidateRange(1024, 65535)]
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'
$script:DatasetVersion = 'relapaw-demo/v1-observe-review-baseline'
$script:RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$script:BackendDir = [System.IO.Path]::GetFullPath((Join-Path $script:RepoRoot 'backend'))
$script:FrontendDir = [System.IO.Path]::GetFullPath((Join-Path $script:RepoRoot 'frontend'))
$script:StaticDir = [System.IO.Path]::GetFullPath((Join-Path $script:FrontendDir 'dist'))
$script:DemoDir = [System.IO.Path]::GetFullPath((Join-Path $script:BackendDir '.demo'))
$script:DatabasePath = [System.IO.Path]::GetFullPath((Join-Path $script:DemoDir 'relapaw-demo.db'))
$script:ManifestPath = [System.IO.Path]::GetFullPath((Join-Path $script:DemoDir 'manifest.json'))
$script:PidPath = [System.IO.Path]::GetFullPath((Join-Path $script:DemoDir 'server.pid.json'))
$script:StdoutPath = [System.IO.Path]::GetFullPath((Join-Path $script:DemoDir 'server.stdout.log'))
$script:StderrPath = [System.IO.Path]::GetFullPath((Join-Path $script:DemoDir 'server.stderr.log'))
$script:PythonPath = [System.IO.Path]::GetFullPath((Join-Path $script:BackendDir '.venv\Scripts\python.exe'))

function Assert-RepositoryLayout {
    $required = @(
        (Join-Path $script:BackendDir 'alembic.ini'),
        (Join-Path $script:BackendDir 'app\main.py'),
        (Join-Path $script:FrontendDir 'package.json'),
        $script:PythonPath
    )
    foreach ($path in $required) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Required project file is missing: $path"
        }
    }
    $expectedDemoParent = [System.IO.Path]::GetFullPath($script:BackendDir)
    if ([System.IO.Path]::GetDirectoryName($script:DemoDir) -ne $expectedDemoParent) {
        throw 'Unsafe demo directory resolution.'
    }
}

function Set-DemoEnvironment {
    $env:RELAPAW_ENV = 'demo'
    $env:RELAPAW_AI_ENABLED = 'false'
    $env:RELAPAW_DATABASE_URL = 'sqlite:///' + ($script:DatabasePath -replace '\\', '/')
    $env:RELAPAW_STATIC_DIR = $script:StaticDir
}

function Invoke-CheckedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][string]$Label
    )
    Push-Location -LiteralPath $WorkingDirectory
    try {
        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "$Label failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}

function Test-PortOpen {
    param([int]$TargetPort)
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync('127.0.0.1', $TargetPort)
        return $task.Wait(300) -and $client.Connected
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

function Get-PidRecord {
    if (-not (Test-Path -LiteralPath $script:PidPath -PathType Leaf)) {
        return $null
    }
    try {
        return Get-Content -LiteralPath $script:PidPath -Raw | ConvertFrom-Json
    }
    catch {
        throw "PID file is invalid; refusing automatic process control: $script:PidPath"
    }
}

function Test-OwnedProcess {
    param($Record)
    if ($null -eq $Record -or $Record.pid -notmatch '^\d+$') {
        return $false
    }
    if (
        [string]$Record.python_path -ne $script:PythonPath -or
        [string]$Record.database_path -ne $script:DatabasePath -or
        [string]$Record.command -ne 'uvicorn app.main:app' -or
        $Record.port -notmatch '^\d+$'
    ) {
        return $false
    }
    $process = Get-Process -Id ([int]$Record.pid) -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        return $false
    }
    try {
        $actualStart = $process.StartTime.ToUniversalTime()
        $actualPath = [System.IO.Path]::GetFullPath($process.Path)
    }
    catch {
        return $false
    }
    try {
        $recordedStart = ([datetime]$Record.process_start_time_utc).ToUniversalTime()
    }
    catch {
        return $false
    }
    if ($actualStart.Ticks -ne $recordedStart.Ticks) {
        return $false
    }
    if ($actualPath -ne $script:PythonPath) {
        return $false
    }
    return $true
}

function Test-DemoHealth {
    param([int]$TargetPort)
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$TargetPort/health" -TimeoutSec 2
        $capabilities = Invoke-RestMethod -Uri "http://127.0.0.1:$TargetPort/api/v1/capabilities" -TimeoutSec 2
        return (
            $health.status -eq 'ok' -and
            $health.environment -eq 'demo' -and
            $health.static_frontend -eq $true -and
            $capabilities.synthetic_data -eq $true -and
            $capabilities.dataset_version -eq $script:DatasetVersion -and
            $capabilities.ai_analysis_enabled -eq $false
        )
    }
    catch {
        return $false
    }
}

function Remove-ExactDemoFile {
    param([Parameter(Mandatory = $true)][string]$Path)
    $resolved = [System.IO.Path]::GetFullPath($Path)
    if ([System.IO.Path]::GetDirectoryName($resolved) -ne $script:DemoDir) {
        throw "Refusing to remove a file outside backend/.demo: $resolved"
    }
    $allowed = @(
        'relapaw-demo.db', 'relapaw-demo.db-wal', 'relapaw-demo.db-shm',
        'manifest.json', 'server.pid.json', 'server.pid.json.tmp',
        'server.stdout.log', 'server.stderr.log'
    )
    if ([System.IO.Path]::GetFileName($resolved) -notin $allowed) {
        throw "Refusing to remove an unrecognized demo file: $resolved"
    }
    if (Test-Path -LiteralPath $resolved) {
        Remove-Item -LiteralPath $resolved -Force
    }
}

function Initialize-DemoData {
    Set-DemoEnvironment
    New-Item -ItemType Directory -Path $script:DemoDir -Force | Out-Null
    Invoke-CheckedProcess -FilePath $script:PythonPath -Arguments @('-m', 'alembic', '-c', 'alembic.ini', 'upgrade', 'head') -WorkingDirectory $script:BackendDir -Label 'Database migration'
    Invoke-CheckedProcess -FilePath $script:PythonPath -Arguments @('-m', 'app.demo.seed') -WorkingDirectory $script:BackendDir -Label 'Demo seed'
    Invoke-CheckedProcess -FilePath $script:PythonPath -Arguments @('-m', 'app.demo.verify') -WorkingDirectory $script:BackendDir -Label 'Demo verification'
}

function Build-Frontend {
    Invoke-CheckedProcess -FilePath 'npm.cmd' -Arguments @('run', 'build') -WorkingDirectory $script:FrontendDir -Label 'Frontend production build'
    if (-not (Test-Path -LiteralPath (Join-Path $script:StaticDir 'index.html') -PathType Leaf)) {
        throw 'Frontend build completed without dist/index.html.'
    }
}

function Stop-Demo {
    $record = Get-PidRecord
    if ($null -eq $record) {
        Write-Host 'Relapaw demo is already stopped.'
        return
    }
    if (-not (Test-OwnedProcess -Record $record)) {
        throw 'PID record does not match a live Relapaw demo process; refusing to stop it.'
    }
    if (-not (Test-DemoHealth -TargetPort ([int]$record.port))) {
        throw 'Process identity matched but the demo health contract failed; refusing to stop it automatically.'
    }
    Stop-Process -Id ([int]$record.pid) -ErrorAction Stop
    Wait-Process -Id ([int]$record.pid) -Timeout 10 -ErrorAction SilentlyContinue
    Remove-ExactDemoFile -Path $script:PidPath
    Write-Host 'Relapaw demo stopped.'
}

function Verify-Demo {
    Assert-RepositoryLayout
    Set-DemoEnvironment
    Invoke-CheckedProcess -FilePath $script:PythonPath -Arguments @('-m', 'app.demo.verify') -WorkingDirectory $script:BackendDir -Label 'Demo verification'
    $record = Get-PidRecord
    if ($null -ne $record) {
        if (-not (Test-OwnedProcess -Record $record)) {
            throw 'PID record is stale or does not identify the Relapaw demo process.'
        }
        if (-not (Test-DemoHealth -TargetPort ([int]$record.port))) {
            throw 'Demo process is running but its health or capability contract failed.'
        }
    }
    Write-Host 'Relapaw demo verification passed.'
}

function Reset-Demo {
    Assert-RepositoryLayout
    Stop-Demo
    New-Item -ItemType Directory -Path $script:DemoDir -Force | Out-Null
    foreach ($path in @(
        $script:DatabasePath,
        "$($script:DatabasePath)-wal",
        "$($script:DatabasePath)-shm",
        $script:ManifestPath,
        $script:PidPath,
        "$($script:PidPath).tmp",
        $script:StdoutPath,
        $script:StderrPath
    )) {
        Remove-ExactDemoFile -Path $path
    }
    Initialize-DemoData
    Write-Host 'Relapaw demo data reset and verified. The server remains stopped.'
}

function Start-Demo {
    Assert-RepositoryLayout
    $record = Get-PidRecord
    if ($null -ne $record) {
        if ((Test-OwnedProcess -Record $record) -and (Test-DemoHealth -TargetPort ([int]$record.port))) {
            Write-Host "Relapaw demo is already running at http://127.0.0.1:$($record.port)/"
            return
        }
        throw 'A stale or mismatched PID record exists; refusing to start. Inspect backend/.demo/server.pid.json.'
    }
    if (Test-PortOpen -TargetPort $Port) {
        throw "Port $Port is already in use; no process was stopped. Choose another port with -Port."
    }
    Build-Frontend
    Initialize-DemoData
    Set-DemoEnvironment
    $arguments = @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', [string]$Port)
    $process = Start-Process -FilePath $script:PythonPath -ArgumentList $arguments -WorkingDirectory $script:BackendDir -WindowStyle Hidden -RedirectStandardOutput $script:StdoutPath -RedirectStandardError $script:StderrPath -PassThru
    $process.Refresh()
    $recordPayload = [ordered]@{
        pid = $process.Id
        port = $Port
        process_start_time_utc = $process.StartTime.ToUniversalTime().ToString('o')
        python_path = $script:PythonPath
        database_path = $script:DatabasePath
        command = 'uvicorn app.main:app'
    }
    $temporaryPid = "$($script:PidPath).tmp"
    $recordPayload | ConvertTo-Json | Set-Content -LiteralPath $temporaryPid -Encoding UTF8
    Move-Item -LiteralPath $temporaryPid -Destination $script:PidPath -Force
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if (Test-DemoHealth -TargetPort $Port) {
            Write-Host "Relapaw demo running at http://127.0.0.1:$Port/"
            return
        }
        if ($process.HasExited) {
            break
        }
        Start-Sleep -Milliseconds 500
        $process.Refresh()
    }
    if (Test-OwnedProcess -Record $recordPayload) {
        Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
    }
    Remove-ExactDemoFile -Path $script:PidPath
    $tail = if (Test-Path -LiteralPath $script:StderrPath) { Get-Content -LiteralPath $script:StderrPath -Tail 20 } else { @() }
    throw "Demo server failed its startup health check.`n$($tail -join [Environment]::NewLine)"
}

Assert-RepositoryLayout
switch ($Action) {
    'start' { Start-Demo }
    'verify' { Verify-Demo }
    'reset' { Reset-Demo }
    'stop' { Stop-Demo }
}
