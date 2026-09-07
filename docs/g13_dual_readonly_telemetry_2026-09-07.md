# G13 — Dos vías read-only para telemetría real

## Propósito y separación de responsabilidades

Se mantienen dos rutas que se complementan y no intercambian secretos:

| Ruta | Función | Resultado aceptable |
| --- | --- | --- |
| Bridge MCP remoto | Diagnóstico y consulta puntual del terminal a través de SSH/túnel local | Una llamada MCP read-only autenticada por JJTI y BEPB |
| `mt5-connector` directo | Ingesta continua y sellada de posiciones, deals, equity y heartbeat hacia `core-engine` | Filas frescas de `heartbeat_log` y `equity_snapshot` para las dos cuentas reales |

El bridge no sustituye al conector: sus respuestas no crean `IngestBatch`, no
actualizan el panel y no generan alertas. El conector no envía órdenes, no
autentica brokers ni modifica EAs, perfiles, gráficos o AutoTrading.

## Estado comprobado

Los dos servicios MCP remotos estaban escuchando y fueron alcanzables mediante
túnel SSH read-only. Ambos rechazaron las llamadas con `HTTP 401`. La red y el
servicio remoto no son el bloqueo conocido; el bearer token privado debe
renovarse por el operador en su configuración MCP local. Ningún secreto fue
leído, mostrado ni modificado durante esta comprobación.

La base operacional sigue sin filas reales de `heartbeat_log` ni
`equity_snapshot`. La comprobación `scripts/check_observation.py` permanece
bloqueada hasta que ambas cuentas las aporten dentro de la ventana contractual.

## Preparación del bridge MCP

1. Mantener los túneles ligados exclusivamente a `127.0.0.1`; no exponer los
   puertos MCP del VPS a una red pública.
2. Renovar los dos bearer tokens en la configuración privada existente del
   cliente MCP. No añadirlos a este repositorio, archivos `.example`, logs ni
   variables impresas en consola.
3. Ejecutar una lectura inocua por cada cuenta (información de cuenta o estado
   del terminal) y exigir HTTP 200. Un 401 detiene este gate; no se cambia el
   terminal para intentar arreglarlo.

La plantilla no sensible de las dos rutas vive en
`config/mt5_readonly_telemetry.example.json`.

## Preparación del conector directo

El VPS de cada cuenta necesita una instancia independiente: distinto servicio
NSSM, ruta de terminal, `account_login`, buffer SQLite y logs. Ambos comparten
la misma URL HTTPS alcanzable del `core-engine` y heredan la API key de ingesta
desde el entorno protegido del servicio, sin que el instalador la reciba ni la
persista.

El instalador versionado es
`mt5-connector/install_readonly_operational_service.ps1`. Antes de iniciar,
comprueba NSSM, Python, la ruta del terminal y que la instancia exacta de
`terminal64.exe` ya esté abierta. Al usar `-Start`, exige además HTTP 200 del
health del core desde el VPS. Rechaza una URL localhost porque no es alcanzable
desde un VPS remoto. La API key debe llegar al proceso mediante el mecanismo
protegido que gobierne el operador; el instalador no la inspecciona ni la
persiste.

Ejemplo para ejecutar localmente en cada VPS, sustituyendo sólo valores que ya
administra el operador:

```powershell
Set-Location <ruta-del-paquete-mt5-connector>
.\install_readonly_operational_service.ps1 `
  -AccountAlias <bepb-o-jjti> `
  -AccountLogin '<login-autorizado>' `
  -TerminalPath '<ruta-exacta-a-terminal64.exe>' `
  -CoreEngineUrl 'https://<core-operacional-alcanzable>' `
  -Start
```

Una respuesta 401 o 403 del core ya no descarta lotes: el sender los conserva
en su SQLite y reintenta con backoff. Los 422 y 404 continúan siendo rechazos
permanentes porque un payload idéntico no se corrige con un reintento.

## Evidencia de cierre pendiente

Después de arrancar ambas instancias, esperar al menos un ciclo completo de
heartbeat y equity, y ejecutar desde la instalación operacional:

```powershell
.venv\Scripts\python.exe scripts\check_observation.py
```

El resultado sólo será `PASS` si las dos cuentas `BROKER_REAL` aportan
heartbeat y equity frescos. Para certificar una alerta real, Telegram debe
estar configurado por el operador y debe observarse una alerta producida por
un hecho operativo real (por ejemplo, una posición real sin SL); no se inyecta
una alerta sintética en cuentas reales para cerrar este gate.
