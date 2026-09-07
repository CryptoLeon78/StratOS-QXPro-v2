# Instala una instancia aislada del conector MT5 read-only para UNA cuenta.
#
# Este script no recibe, lee, escribe ni muestra secretos. El servicio hereda
# CONNECTOR_INGEST_API_KEY desde el mecanismo protegido de Windows que haya
# preparado el operador para el servicio. No crea .env, no toca credenciales
# del broker, EAs, perfiles, graficos ni AutoTrading.
#
# Uso (en el VPS, despues de desplegar el paquete y configurar la variable de
# entorno protegida del servicio):
#   .\install_readonly_operational_service.ps1 `
#     -AccountAlias jjti `
#     -AccountLogin '<login autorizado>' `
#     -TerminalPath 'C:\Program Files\Darwinex MetaTrader 5\terminal64.exe' `
#     -CoreEngineUrl 'https://<core-operacional-alcanzable>' `
#     -Start
#
# Antes de -Start, comprobar que la instancia MT5 correcta ya esta abierta y
# autenticada por el operador. El conector solo invoca las APIs read-only
# account_info, positions_get e history_deals_get; no contiene rutas de orden.

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9_-]+$')]
    [string]$AccountAlias,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9]+$')]
    [string]$AccountLogin,

    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$TerminalPath,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^https://')]
    [string]$CoreEngineUrl,

    [string]$ServiceName,
    [string]$PythonExe = "$PSScriptRoot\.venv\Scripts\python.exe",
    [string]$ScriptPath = "$PSScriptRoot\src\connector\main.py",
    [string]$DataRoot = 'C:\ProgramData\StratOSQXPro\operational',
    [switch]$Start
)

$ErrorActionPreference = 'Stop'

if (-not $ServiceName) {
    $ServiceName = "StratOSMt5Readonly_$AccountAlias"
}

if (-not (Get-Command nssm -ErrorAction SilentlyContinue)) {
    throw 'NSSM no esta disponible en PATH.'
}
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw "No se encuentra Python del conector en $PythonExe."
}
if (-not (Test-Path -LiteralPath $ScriptPath -PathType Leaf)) {
    throw "No se encuentra el entrypoint del conector en $ScriptPath."
}
try {
    $coreUri = [Uri]$CoreEngineUrl
    if ($coreUri.IsLoopback) {
        throw 'CORE_ENGINE_URL debe ser alcanzable desde el VPS; localhost no es valido para este despliegue remoto.'
    }
} catch {
    throw "CORE_ENGINE_URL invalida: $($_.Exception.Message)"
}

$terminal = Get-Process -Name 'terminal64' -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and $_.Path -ieq $TerminalPath } |
    Select-Object -First 1
if (-not $terminal) {
    throw 'La instancia MT5 indicada no esta abierta. Arrancarla y autenticarla manualmente antes de instalar el servicio.'
}

$instanceRoot = Join-Path $DataRoot $AccountAlias
$bufferPath = Join-Path $instanceRoot 'buffer.sqlite'
$logRoot = Join-Path $instanceRoot 'logs'
$serviceEnvironment = @(
    "CONNECTOR_CORE_ENGINE_URL=$CoreEngineUrl",
    "CONNECTOR_ACCOUNT_LOGIN=$AccountLogin",
    "CONNECTOR_BUFFER_DB_PATH=$bufferPath",
    "CONNECTOR_MT5_TERMINAL_PATH=$TerminalPath",
    'CONNECTOR_REPORTER_OUTBOX_DIR='
)

if ($PSCmdlet.ShouldProcess($ServiceName, 'install or update read-only connector service')) {
    New-Item -ItemType Directory -Path $logRoot -Force | Out-Null

    $existing = & nssm status $ServiceName 2>$null
    if ($LASTEXITCODE -ne 0) {
        & nssm install $ServiceName $PythonExe $ScriptPath
    }
    & nssm set $ServiceName AppDirectory $PSScriptRoot
    & nssm set $ServiceName AppEnvironmentExtra $serviceEnvironment
    & nssm set $ServiceName AppStdout (Join-Path $logRoot 'connector.out.log')
    & nssm set $ServiceName AppStderr (Join-Path $logRoot 'connector.err.log')
    & nssm set $ServiceName AppRotateFiles 1
    & nssm set $ServiceName AppRotateBytes 10485760
    & nssm set $ServiceName Start SERVICE_AUTO_START
    & nssm set $ServiceName AppExit Default Restart
    & nssm set $ServiceName AppRestartDelay 5000

    if ($Start) {
        $healthUrl = "$($CoreEngineUrl.TrimEnd('/'))/health"
        try {
            $health = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 10
        } catch {
            throw "El VPS no alcanza el health del core en ${healthUrl}: $($_.Exception.Message)"
        }
        if ($health.StatusCode -ne 200) {
            throw "El health del core devolvio HTTP $($health.StatusCode); no se inicia el conector."
        }
        & nssm start $ServiceName
    }
}

Write-Host "Configuracion read-only preparada para $AccountAlias en $ServiceName."
Write-Host "Buffer: $bufferPath"
Write-Host 'La API key de ingesta debe estar disponible para el servicio por el mecanismo protegido elegido por el operador; este script no la inspecciona ni la persiste.'
Write-Host 'Validar despues con scripts\check_observation.py; el servicio no certifica por si solo llegada al core.'
