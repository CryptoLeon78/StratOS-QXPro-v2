[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$install_report,
    [string]$terminal_data_root = 'C:\Users\Ivan SQX\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075',
    [string]$metaeditor_exe = 'C:\Program Files\MetaTrader 5\metaeditor64.exe'
)

$ErrorActionPreference = 'Stop'
$resolved_root = (Resolve-Path -LiteralPath $terminal_data_root).Path
$resolved_editor = (Resolve-Path -LiteralPath $metaeditor_exe).Path
$report = Get-Content -LiteralPath $install_report -Raw | ConvertFrom-Json
$logs_dir = Join-Path (Split-Path -Parent $install_report) 'metaeditor-indicator-logs'
New-Item -ItemType Directory -Force -Path $logs_dir | Out-Null

$compiled = @()
foreach ($indicator in $report.indicators) {
    $source = [string]$indicator.target
    $allowed_prefix = Join-Path $resolved_root 'MQL5\Indicators\'
    if (-not $source.StartsWith($allowed_prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing source outside target MT5 Indicators folder: $source"
    }
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Indicator source missing: $source"
    }
    $log = Join-Path $logs_dir ((Split-Path -LeafBase $source) + '.log')
    # MetaEditor requires a single raw command line containing /compile:"path".
    # Passing a token list returns exit 0 without compiling on this host.
    $launch_arguments = "/compile:`"$source`" /log:`"$log`""
    $compiler = Start-Process -FilePath $resolved_editor -ArgumentList $launch_arguments -Wait -PassThru
    if (-not (Test-Path -LiteralPath $log -PathType Leaf)) {
        throw "MetaEditor did not produce a compile log for: $source"
    }
    $log_text = Get-Content -LiteralPath $log -Raw -Encoding Unicode
    if ($log_text -notmatch 'Result:\s+0 errors') {
        throw "Indicator compilation failed for $source`n$log_text"
    }
    $binary = [System.IO.Path]::ChangeExtension($source, '.ex5')
    if (-not (Test-Path -LiteralPath $binary -PathType Leaf)) {
        throw "MetaEditor reported success but binary is missing: $binary"
    }
    $compiled += [pscustomobject]@{ name = (Split-Path -LeafBase $source); binary = $binary; log = $log }
}

[pscustomobject]@{ ok = $true; compiled_count = $compiled.Count; indicators = $compiled }
