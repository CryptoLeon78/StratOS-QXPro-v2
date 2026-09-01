[CmdletBinding()]
param(
    [string]$project_root = (Split-Path -Parent $PSScriptRoot),
    [switch]$restart
)

$ErrorActionPreference = 'Stop'
$resolved_root = (Resolve-Path -LiteralPath $project_root).Path
$connector_dir = Join-Path $resolved_root 'mt5-connector'
$python_exe = Join-Path $connector_dir '.venv\Scripts\python.exe'
$env_file = Join-Path $connector_dir '.env'
if (-not (Test-Path -LiteralPath $python_exe -PathType Leaf)) { throw "Connector Python not found: $python_exe" }
if (-not (Test-Path -LiteralPath $env_file -PathType Leaf)) { throw "Connector env not found: $env_file" }

$targets = @(
    Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
        Where-Object { $_.ExecutablePath -eq $python_exe -and $_.CommandLine -match 'connector\.main' }
)
if ($targets.Count -gt 1) { throw "Expected at most one G12 connector process; found $($targets.Count)." }
if ($targets.Count -eq 1 -and -not $restart) {
    [pscustomobject]@{ status = 'already_running'; connector_pid = $targets[0].ProcessId }
    exit 0
}
if ($targets.Count -eq 1) {
    Stop-Process -Id ([int]$targets[0].ProcessId)
}

$runtime_dir = Join-Path $resolved_root 'runtime\g12'
New-Item -ItemType Directory -Force -Path $runtime_dir | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$stdout = Join-Path $runtime_dir "connector-$stamp.stdout.log"
$stderr = Join-Path $runtime_dir "connector-$stamp.stderr.log"
$process = Start-Process -FilePath $python_exe -ArgumentList '-m','connector.main' -WorkingDirectory $connector_dir -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru

[pscustomobject]@{
    status = 'started'
    connector_pid = $process.Id
    stdout_log = $stdout
    stderr_log = $stderr
}
