[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$terminal_exe = 'C:\Program Files\MetaTrader 5\terminal64.exe',
    [string]$profile_name = 'StratOS_G12_Demo_11Ready',
    [switch]$restart
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $terminal_exe -PathType Leaf)) {
    throw "MT5 executable not found: $terminal_exe"
}
if ($profile_name -notmatch '^[A-Za-z0-9_.-]{1,96}$') {
    throw 'profile_name contains unsupported characters'
}

$resolved_terminal = (Resolve-Path -LiteralPath $terminal_exe).Path
$targets = @(
    Get-CimInstance Win32_Process -Filter "Name = 'terminal64.exe'" |
        Where-Object { $_.ExecutablePath -eq $resolved_terminal }
)

if ($targets.Count -gt 1) {
    throw "Expected at most one exact MetaQuotes-Demo terminal process; found $($targets.Count)."
}
if ($targets.Count -eq 1 -and -not $restart) {
    throw "Target terminal is already running (PID $($targets[0].ProcessId)); rerun with -restart."
}
if ($targets.Count -eq 1 -and $restart) {
    $target_pid = [int]$targets[0].ProcessId
    if ($PSCmdlet.ShouldProcess("PID $target_pid ($resolved_terminal)", 'Stop exact demo terminal')) {
        Stop-Process -Id $target_pid
        $deadline = (Get-Date).AddSeconds(20)
        while ((Get-Process -Id $target_pid -ErrorAction SilentlyContinue) -and (Get-Date) -lt $deadline) {
            Start-Sleep -Milliseconds 200
        }
        if (Get-Process -Id $target_pid -ErrorAction SilentlyContinue) {
            throw "Target MT5 process did not stop within 20 seconds: $target_pid"
        }
    }
}

if ($PSCmdlet.ShouldProcess($resolved_terminal, "Start MT5 profile $profile_name")) {
    Start-Process -FilePath $resolved_terminal -ArgumentList "/profile:$profile_name" -WorkingDirectory (Split-Path -Parent $resolved_terminal) | Out-Null
}

[pscustomobject]@{
    terminal_exe = $resolved_terminal
    profile_name = $profile_name
    launch_args = "/profile:$profile_name"
    restarted = [bool]$restart
}
