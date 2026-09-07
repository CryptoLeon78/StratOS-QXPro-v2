# Prepara el entorno Python del conector directo en un VPS Windows.
#
# No recibe, lee, escribe ni muestra secretos. Ejecutar como administrador en
# la raiz desplegada que contiene los directorios hermanos mt5-connector y
# shared-ingest-seal. La clave CONNECTOR_INGEST_API_KEY se configura aparte
# como variable de sistema de Windows para que el servicio LocalSystem la
# herede al arrancar.

[CmdletBinding()]
param(
    [ValidateSet('3.12')]
    [string]$PythonVersion = '3.12'
)

$ErrorActionPreference = 'Stop'

$connectorRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$sealRoot = Join-Path (Split-Path -Parent $connectorRoot) 'shared-ingest-seal'
$venvPython = Join-Path $connectorRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath (Join-Path $connectorRoot 'pyproject.toml') -PathType Leaf)) {
    throw 'No se encontro el pyproject.toml del mt5-connector.'
}
if (-not (Test-Path -LiteralPath (Join-Path $sealRoot 'pyproject.toml') -PathType Leaf)) {
    throw 'No se encontro shared-ingest-seal junto al mt5-connector.'
}
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'No se encontro el lanzador Python (py). Instalar Python 3.12 para todos los usuarios y reabrir PowerShell.'
}

& py "-$PythonVersion" -c 'import sys; assert sys.version_info[:2] == (3, 12)'
if ($LASTEXITCODE -ne 0) {
    throw 'Python 3.12 no esta disponible mediante el lanzador py.'
}

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    & py "-$PythonVersion" -m venv (Join-Path $connectorRoot '.venv')
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
& $venvPython -c 'import MetaTrader5, connector, ingest_seal; print("Readonly connector dependencies ready")'
if ($LASTEXITCODE -ne 0) {
    throw 'Las dependencias se instalaron de forma incompleta.'
}

Write-Host 'Entorno read-only preparado.'
Write-Host 'Siguiente paso: configurar la variable de sistema CONNECTOR_INGEST_API_KEY, instalar NSSM y ejecutar install_readonly_operational_service.ps1 por cuenta.'
