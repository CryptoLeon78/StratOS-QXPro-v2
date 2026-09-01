[CmdletBinding()]
param(
    [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Split-Path -Parent $PSScriptRoot
}
$root = (Resolve-Path -LiteralPath $ProjectRoot).Path
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw "No existe el intérprete operacional: $python"
}

& $python -m PyInstaller --version *> $null
if ($LASTEXITCODE -ne 0) {
    throw 'PyInstaller no está instalado en .venv. Instálelo explícitamente con: .venv\Scripts\python.exe -m pip install pyinstaller'
}

& $python -m PyInstaller --noconfirm --clean --onefile --name StratOS_Operational `
    --distpath (Join-Path $root 'dist') `
    --workpath (Join-Path $root 'runtime\operational\pyinstaller-work') `
    --specpath (Join-Path $root 'runtime\operational\pyinstaller-spec') `
    (Join-Path $root 'scripts\stratos_operational_launcher.py')
if ($LASTEXITCODE -ne 0) {
    throw 'Falló el empaquetado de StratOS_Operational.exe'
}

Write-Host "Creado: $(Join-Path $root 'dist\StratOS_Operational.exe')"
