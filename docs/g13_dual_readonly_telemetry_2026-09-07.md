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

### Actualización: autenticación MCP restaurada por tailnet

El 2026-09-07 se sustituyeron los túneles SSH por `Tailscale Serve` privado en
el VPS y se registraron ambos endpoints con bearer token procedente de las
variables de entorno privadas del cliente. La inicialización MCP autenticada
de JJTI y BEPB devolvió `HTTP 200` en las dos rutas. Es evidencia de transporte
y autenticación recuperados, no de telemetría: en esta versión del bridge,
`tools/list`, `resources/list` y `prompts/list` responden correctamente pero
sin capacidades publicadas. Por tanto todavía no hay una llamada read-only de
cuenta que pruebe equity, posiciones o heartbeat mediante ese bridge.

El core operacional se publica únicamente en la tailnet con Tailscale Serve,
en una URL HTTPS privada y comprobada desde el propio equipo del core. Funnel
permanece deshabilitado: no se ha abierto ningún puerto del panel al Internet
público.

### Evidencia de ingesta real y recuperación de credencial

Tras instalar dos servicios NSSM independientes en el VPS, la comprobación
read-only `scripts/check_observation.py` devolvió `PREFLIGHT_PASS`. El core
aceptó lotes de `heartbeat`, `equity`, `positions` y `trades` con HTTP 200, y
las dos cuentas `BROKER_REAL` aportaron heartbeat y equity por debajo del
umbral contractual de 120 segundos. La evidencia sellada queda bajo
`runtime/operational/observation/` y no se versiona.

La identidad de los terminales se comprobó antes de instalar cada servicio:
los nombres de dos carpetas MT5 estaban cruzados respecto de las cuentas
logueadas. Los servicios quedaron asociados por identidad observada de cuenta,
nunca por el nombre editorial de la carpeta. No se relogueó, renombró ni
modificó ningún terminal.

Antes de configurar la clave de ingesta, ambos conectores recibían HTTP 401 y
conservaron sus lotes en SQLite. Tras configurar la misma clave permitida en
el core y reiniciar los servicios, los lotes se aceptaron sin intervención en
MT5. Esto acredita recuperación ante una credencial inválida, no una prueba de
reinicio de host ni de corte de red.

La base contiene alertas `CRITICA` recientes emitidas por `ingest_positions`,
de modo que la generación y persistencia de alertas de ingesta queda observada
en datos reales. La entrega externa por Telegram permanece no verificada:
no se inyectan alertas sintéticas ni se inspeccionan sus credenciales para
cerrar ese punto.

### Actualización: lectura diaria en el panel y recuperación del core

La vista `Cuentas/EA` se verificó contra la telemetría operacional: JJTI y
BEPB muestran equity, balance, margen libre, nivel de margen y heartbeat como
conectados. La cabecera separa ahora correctamente los dos estados: sólo
muestra `DATOS STALE` cuando el heartbeat excede el umbral de frescura; una
edad normal no se presenta como incidencia.

Se reinició exclusivamente `core-engine` y los conectores continuaron
publicando lotes read-only. Tras recuperar el servicio, el core aceptó de
nuevo `heartbeat` y `equity` de ambas cuentas con HTTP 200. El preflight
admite una desviación de reloj VPS/core de hasta cinco segundos, configurada
en `telemetry_clock_skew_tolerance_s`; no relaja el umbral contractual de
120 segundos para cada stream.

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
`terminal64.exe` ya esté abierta. Además inicializa esa ruta de forma
read-only y exige que `account_info().login` coincida con la cuenta declarada;
así no puede etiquetar por error la telemetría de Demo, JJTI o BEPB con otro
alias. Al usar `-Start`, exige además HTTP 200 del health del core desde el
VPS. Rechaza una URL localhost porque no es alcanzable desde un VPS remoto. La
API key debe llegar al proceso mediante el mecanismo protegido que gobierne el
operador; el instalador no la inspecciona ni la persiste.

La ruta se pasa a `MetaTrader5.initialize()` como su primer argumento
posicional, conforme a su contrato público. No se usa el modo automático ni
un keyword `path`, porque con varias instalaciones MT5 esa selección puede
conectar a otro terminal y alterar la procedencia de la observación.

El paquete incluye además
`mt5-connector/bootstrap_operational_readonly.ps1`. Instala únicamente las
dependencias Python del conector y `MetaTrader5`; no configura cuentas MT5 ni
secretos. El VPS debe tener Python 3.12 y NSSM disponibles antes de instalar
cualquiera de los dos servicios.

Para que NSSM, que arranca bajo `LocalSystem`, pueda autenticar la ingesta, el
operador debe crear **en el VPS y como variable de sistema de Windows**
`CONNECTOR_INGEST_API_KEY` con la clave de ingesta operacional ya existente.
No sirve una variable de usuario creada en el PC local ni un token MCP de
JJTI/BEPB. No se pega esa clave en consola, archivos, chat ni repositorio; el
instalador nunca la inspecciona. Tras crear o cambiar la variable de sistema,
se reinicia cada servicio para que reciba el nuevo entorno.

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

## Actualización: entrega Telegram a dos grupos

`Gamblers_Bastion_bot` quedó verificado como miembro de los dos grupos
operativos elegidos por el operador. El primero ya lo contenía como
administrador; el segundo lo incorporó como miembro normal. No se concedieron
permisos administrativos adicionales.

El core admite ahora `TELEGRAM_CHAT_IDS`, una lista de destinos separada por
comas que tiene prioridad sobre el destino único heredado
`TELEGRAM_CHAT_ID`. Cada alerta se intenta entregar en todos los destinos;
el resultado sólo es exitoso si todos aceptan el mensaje. La prueba controlada
de entrega devolvió éxito para los dos destinos configurados. No creó alertas
ni modificó cuentas, terminales ni EAs.

Tras el redeploy de core, worker y scheduler, `check_observation.py` devolvió
`PREFLIGHT_PASS`: servicios activos, recuperación automática, acceso anónimo
rechazado, datos legibles y telemetría real fresca de JJTI y BEPB.

### Gate pendiente: rotación segura de secretos iniciales

Los valores de ejemplo no son aceptables para operación sostenida. Antes de
declarar una configuración de producción cerrada, el operador debe sustituir
las credenciales iniciales por secretos aleatorios y rotar las contraseñas de
los roles correspondientes dentro de PostgreSQL. Cambiar sólo el archivo de
entorno de un clúster ya inicializado rompería la siguiente reconexión. Rotar
`JWT_SECRET` invalida las sesiones existentes y requiere reiniciar los
servicios que emiten o validan tokens. Los valores reales no se registran ni
se versionan.

### Verificación posterior a la rotación

Tras la rotación coordinada de las contraseñas de los roles y del secreto JWT,
se recrearon core, worker, scheduler y gateway. El acceso a la base continuó
legible, las rutas protegidas volvieron a rechazar acceso anónimo con `401` y
las dos cuentas reales siguieron aportando heartbeat y equity frescos.

La recreación del gateway cambió su IP interna de Docker. El frontend, que no
se había recreado en la misma orden, devolvió temporalmente `502` al mantener
la resolución anterior; reiniciarlo una vez restauró el proxy. El preflight
posterior devolvió `PREFLIGHT_PASS`. Una segunda entrega controlada por
Telegram fue aceptada por todos los destinos configurados. No se inspeccionó
ni versionó ningún valor secreto.
