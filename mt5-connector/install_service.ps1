# PARTE 3/12 (G4): instala mt5-connector como servicio de Windows via NSSM
# (Nodo A, VPS Windows). NO VERIFICADO en esta sesion -- no hay un Windows
# con NSSM y un terminal MT5 disponibles para ejecutarlo de verdad (ver
# ASSUMPTIONS G4-17/G4-19). Escrito contra la CLI documentada de NSSM
# (https://nssm.cc/usage), no probado.
#
# Requisitos previos (manuales, fuera del alcance de este script):
#   - NSSM instalado y en PATH (https://nssm.cc/download)
#   - Python 3.12 + `pip install -e .` ya corrido dentro de .venv en este
#     directorio (mt5-connector\.venv)
#   - mt5-connector\.env ya rellenado (ver .env.example)
#
# Uso:
#   .\install_service.ps1 -ApiKey "<clave real>" -CoreEngineUrl "https://core.example.com"

param(
    [string]$ServiceName = "StratOSMt5Connector",
    [string]$PythonExe = "$PSScriptRoot\.venv\Scripts\python.exe",
    [string]$ScriptPath = "$PSScriptRoot\src\connector\main.py",
    [Parameter(Mandatory = $true)][string]$ApiKey,
    [Parameter(Mandatory = $true)][string]$CoreEngineUrl
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command nssm -ErrorAction SilentlyContinue)) {
    throw "NSSM no esta en PATH. Instalar desde https://nssm.cc/download antes de continuar."
}

if (-not (Test-Path $PythonExe)) {
    throw "No se encuentra el interprete Python en $PythonExe -- crear el venv primero (python -m venv .venv; .venv\Scripts\pip install -e .)."
}

$logDir = "$PSScriptRoot\logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

nssm install $ServiceName $PythonExe $ScriptPath
nssm set $ServiceName AppDirectory $PSScriptRoot

# La API key nunca se escribe a disco en texto plano fuera de este proceso
# NSSM (que la guarda en el registro de Windows, cifrado por ACL del
# servicio, no en un fichero del repo) -- ver PARTE 15 ("ningun secreto en
# el repo").
nssm set $ServiceName AppEnvironmentExtra "CONNECTOR_INGEST_API_KEY=$ApiKey" "CONNECTOR_CORE_ENGINE_URL=$CoreEngineUrl"

nssm set $ServiceName AppStdout "$logDir\connector.out.log"
nssm set $ServiceName AppStderr "$logDir\connector.err.log"
nssm set $ServiceName AppRotateFiles 1
nssm set $ServiceName AppRotateBytes 10485760

nssm set $ServiceName Start SERVICE_AUTO_START
nssm set $ServiceName AppExit Default Restart
nssm set $ServiceName AppRestartDelay 5000

Write-Host "Servicio '$ServiceName' instalado. Iniciando..."
nssm start $ServiceName

Write-Host "Listo. Verificar estado con: nssm status $ServiceName"
Write-Host "Logs en: $logDir"
