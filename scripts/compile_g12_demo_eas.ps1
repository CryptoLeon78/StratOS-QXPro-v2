[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$prepare_report,
    [string]$terminal_data_root = 'C:\Users\Ivan SQX\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075',
    [string]$metaeditor_exe = 'C:\Program Files\MetaTrader 5\MetaEditor64.exe'
)

# Compila exclusivamente los once fuentes preparados por G12. No inicia MT5,
# no toca perfiles y no puede enviar órdenes.
$ErrorActionPreference = 'Stop'
$resolved_root = (Resolve-Path -LiteralPath $terminal_data_root).Path
$resolved_editor = (Resolve-Path -LiteralPath $metaeditor_exe).Path
$report = Get-Content -LiteralPath $prepare_report -Raw | ConvertFrom-Json
$allowed_prefix = Join-Path $resolved_root 'MQL5\Experts\StratOS_G12\'
$logs_dir = Join-Path (Split-Path -Parent $prepare_report) 'metaeditor-ea-logs'
New-Item -ItemType Directory -Force -Path $logs_dir | Out-Null

$compiled = @()
foreach ($entry in $report.prepared) {
    $source = [string]$entry.target
    if (-not $source.StartsWith($allowed_prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing source outside target MT5 Experts folder: $source"
    }
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "EA source missing: $source"
    }
    $log = Join-Path $logs_dir ((Split-Path -LeafBase $source) + '.log')
    $launch_arguments = "/compile:`"$source`" /log:`"$log`""
    Start-Process -FilePath $resolved_editor -ArgumentList $launch_arguments -Wait | Out-Null
    if (-not (Test-Path -LiteralPath $log -PathType Leaf)) {
        throw "MetaEditor did not produce a compile log for: $source"
    }
    $log_text = Get-Content -LiteralPath $log -Raw -Encoding Unicode
    if ($log_text -notmatch 'Result:\s+0 errors') {
        throw "EA compilation failed for $source`n$log_text"
    }
    $binary = [System.IO.Path]::ChangeExtension($source, '.ex5')
    if (-not (Test-Path -LiteralPath $binary -PathType Leaf)) {
        throw "MetaEditor reported success but binary is missing: $binary"
    }
    $compiled += [pscustomobject]@{ name = (Split-Path -LeafBase $source); binary = $binary; log = $log }
}

[pscustomobject]@{ ok = $true; compiled_count = $compiled.Count; eas = $compiled }
