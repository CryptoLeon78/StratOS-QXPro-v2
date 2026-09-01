[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Container })]
    [string]$TerminalDataRoot,

    [Parameter(Mandatory)]
    [ValidateScript({ $_ -gt 0 })]
    [int]$TerminalProcessId,

    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string]$ManifestPath,

    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-ArtifactManifestRow {
    param([System.IO.FileSystemInfo]$Item)

    if ($Item.PSIsContainer) {
        $files = @(Get-ChildItem -LiteralPath $Item.FullName -Recurse -Force -File)
        return [ordered]@{
            path = $Item.FullName
            kind = 'directory'
            file_count = $files.Count
            bytes = [long](($files | Measure-Object -Property Length -Sum).Sum ?? 0)
            sha256 = $null
        }
    }

    return [ordered]@{
        path = $Item.FullName
        kind = 'file'
        file_count = 1
        bytes = [long]$Item.Length
        sha256 = (Get-FileHash -LiteralPath $Item.FullName -Algorithm SHA256).Hash
    }
}

$originPath = Join-Path $TerminalDataRoot 'origin.txt'
if (-not (Test-Path -LiteralPath $originPath -PathType Leaf)) {
    throw "TerminalDataRoot sin origin.txt: $TerminalDataRoot"
}
$origin = [Text.Encoding]::Unicode.GetString([IO.File]::ReadAllBytes($originPath)).Trim([char]0, [char]0xFEFF)
$process = Get-Process -Id $TerminalProcessId -ErrorAction Stop
$expectedTerminal = Join-Path $origin 'terminal64.exe'
if ($process.Path -ne $expectedTerminal) {
    throw "PID $TerminalProcessId no corresponde al terminal indicado. Esperado: $expectedTerminal"
}

$targets = @(
    Join-Path $TerminalDataRoot 'MQL5\Experts\StratOS_G12'
    Join-Path $TerminalDataRoot 'MQL5\Profiles\Charts\StratOS_G12_Demo_11Ready'
    Join-Path $TerminalDataRoot 'MQL5\Profiles\Charts\StratOS_G12_Demo_11Ready.backup'
)
$testerRoot = Join-Path $TerminalDataRoot 'MQL5\Profiles\Tester'
if (Test-Path -LiteralPath $testerRoot) {
    $targets += @(Get-ChildItem -LiteralPath $testerRoot -Force -File |
        Where-Object { $_.Name -like 'StratOS_G12*' } |
        Select-Object -ExpandProperty FullName)
}
$filesRoot = Join-Path $TerminalDataRoot 'MQL5\Files'
if (Test-Path -LiteralPath $filesRoot) {
    $targets += @(Get-ChildItem -LiteralPath $filesRoot -Recurse -Force -File |
        Where-Object { $_.Name -like 'stratos_g12_*' } |
        Select-Object -ExpandProperty FullName)
}
$existing = @($targets | Where-Object { Test-Path -LiteralPath $_ } | Sort-Object -Unique)
$manifestDirectory = Split-Path -Parent $ManifestPath
if (-not (Test-Path -LiteralPath $manifestDirectory)) {
    New-Item -ItemType Directory -Path $manifestDirectory -Force | Out-Null
}
$manifest = [ordered]@{
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
    terminal_data_root = $TerminalDataRoot
    terminal_origin = $origin
    terminal_pid = $TerminalProcessId
    mode = if ($Apply) { 'apply' } else { 'dry_run' }
    artifacts = @($existing | ForEach-Object { Get-ArtifactManifestRow (Get-Item -LiteralPath $_ -Force) })
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $ManifestPath -Encoding utf8

if (-not $Apply) {
    Write-Output "Dry run: $($existing.Count) artefactos G12 inventariados en $ManifestPath"
    exit 0
}

Stop-Process -Id $TerminalProcessId -ErrorAction Stop
Start-Sleep -Milliseconds 500
if (Get-Process -Id $TerminalProcessId -ErrorAction SilentlyContinue) {
    throw "El terminal sigue activo; no se retira ningun artefacto."
}
foreach ($target in $existing) {
    if ($PSCmdlet.ShouldProcess($target, 'Retirar artefacto exclusivo G12')) {
        Remove-Item -LiteralPath $target -Force -Recurse
    }
}
Write-Output "Retirada G12 completada: $($existing.Count) artefactos. Manifiesto: $ManifestPath"
