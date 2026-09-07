# Prepara el entorno Python del conector directo en un VPS Windows.
#
# No recibe, lee, escribe ni muestra secretos. Ejecutar como administrador en
# la raiz desplegada que contiene los directorios hermanos mt5-connector y
# shared-ingest-seal. La clave CONNECTOR_INGEST_API_KEY se configura aparte
# como variable de sistema de Windows para que el servicio LocalSystem la
# herede al arrancar.

[CmdletBinding()]
param(
    [string]$PythonExe
)

$ErrorActionPreference = 'Stop'

$connectorRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$sealRoot = Join-Path (Split-Path -Parent $connectorRoot) 'shared-ingest-seal'
$venvPython = Join-Path $connectorRoot '.venv\Scripts\python.exe'

function Test-Python312 {
    param([Parameter(Mandatory = $true)][string]$Candidate)

    if (-not (Test-Path -LiteralPath $Candidate -PathType Leaf)) {
        return $false
    }
    & $Candidate -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)'
    return $LASTEXITCODE -eq 0
}

function Resolve-Python312 {
    param([string]$RequestedPythonExe)

    if ($RequestedPythonExe -and (Test-Python312 $RequestedPythonExe)) {
        return (Resolve-Path -LiteralPath $RequestedPythonExe).Path
    }

    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        $candidate = & $launcher.Source '-3.12' -c 'import sys; print(sys.executable)' | Select-Object -Last 1
        if ($LASTEXITCODE -eq 0 -and $candidate -and (Test-Python312 $candidate)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand -and (Test-Python312 $pythonCommand.Source)) {
        return (Resolve-Path -LiteralPath $pythonCommand.Source).Path
    }

    throw 'No se encontro Python 3.12. Instalarlo para todos los usuarios y volver a abrir PowerShell.'
}

if (-not (Test-Path -LiteralPath (Join-Path $connectorRoot 'pyproject.toml') -PathType Leaf)) {
    throw 'No se encontro el pyproject.toml del mt5-connector.'
}
if (-not (Test-Path -LiteralPath (Join-Path $sealRoot 'pyproject.toml') -PathType Leaf)) {
    throw 'No se encontro shared-ingest-seal junto al mt5-connector.'
}
$python312 = Resolve-Python312 $PythonExe

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    & $python312 -m venv (Join-Path $connectorRoot '.venv')
    if ($LASTEXITCODE -ne 0) {
        throw 'No se pudo crear el entorno virtual del conector.'
    }
}

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw 'No se pudo actualizar pip en el entorno del conector.'
}
& $venvPython -m pip install -e $sealRoot
if ($LASTEXITCODE -ne 0) {
    throw 'No se pudo instalar el paquete local shared-ingest-seal.'
}
& $venvPython -m pip install -e $connectorRoot
if ($LASTEXITCODE -ne 0) {
    throw 'No se pudo instalar el paquete local mt5-connector.'
}
& $venvPython -m pip install MetaTrader5
if ($LASTEXITCODE -ne 0) {
    throw 'No se pudo instalar el paquete MetaTrader5 desde PyPI.'
}
$runtimeCheck = Join-Path $PSScriptRoot 'src\connector\verify_runtime_dependencies.py'
& $venvPython $runtimeCheck
if ($LASTEXITCODE -ne 0) {
    throw 'Las dependencias se instalaron de forma incompleta.'
}

Write-Host 'Entorno read-only preparado.'
Write-Host 'Siguiente paso: configurar la variable de sistema CONNECTOR_INGEST_API_KEY, instalar NSSM y ejecutar install_readonly_operational_service.ps1 por cuenta.'
