# G13 — Preparación del panel de observación diario — 2026-09-07

## Resultado de esta unidad

El stack `stratos_operational` queda recuperado y protegido contra paradas
accidentales de Docker: PostgreSQL, Redis, core, gateway, frontend, worker y
scheduler usan `restart: unless-stopped`. Los siete contenedores se arrancaron
de nuevo y el reinicio controlado de core, gateway y frontend volvió a entregar
sus endpoints HTTP saludables.

El panel local está disponible en `http://localhost:5473/login`. El endpoint
protegido de cabecera devuelve `401` sin sesión; no se usaron ni se leyeron
credenciales del operador.

El recorrido de navegador con una sesión autenticada ya existente confirma la
vista `Cuentas/EA`: JJTI y BEPB aparecen como `REAL / BROKER_REAL`, Incubadora
como `DEMO / BROKER_DEMO`, y las tres cuentas se muestran como
`Desconectado`, con equity, balance y margen ausentes. La interfaz, por tanto,
declara la ausencia de telemetría en vez de completar esos campos con fixture.
La pestaña permanece abierta localmente para revisión del operador.

La restauración de la base operacional se verificó desde un dump lógico
sellado hacia una base temporal del mismo clúster. Se compararon recuentos de
todas las tablas públicas y restricciones. La base temporal y el dump temporal
del contenedor se eliminaron al finalizar. Evidencia local ignorada por Git:
`runtime/operational/observation/backup-20260907t060542535502z/`.

La variación textual de `ck_execution_fill_status` después de `pg_restore` es
un cambio de presentación de PostgreSQL, no de semántica: las dos expresiones
aceptan exactamente `FILLED` y `REJECTED`. Su equivalencia exacta está
versionada en `config/observation_check.json`; ninguna otra restricción se
normaliza.

## Comprobación repetible

```powershell
cd C:\BOTS\Versiones\SQX_144_Full2\Apps_entorno_SQX\StratOS-QXPro-v2
.venv\Scripts\python.exe scripts\check_observation.py
.venv\Scripts\python.exe scripts\verify_observation_backup.py
```

`check_observation.py` no crea sesiones ni lee secretos. Exige que todos los
servicios estén activos, tengan política de reinicio, expongan HTTP, rechacen
acceso anónimo y que **cada** cuenta real aporte heartbeat y equity dentro de
la ventana contractual. Si falla un dato, devuelve `BLOCKED` y escribe un
informe sellado en `runtime/operational/observation/`.

`verify_observation_backup.py` usa sólo las credenciales que ya están dentro
del contenedor PostgreSQL. No restaura sobre la base operacional ni borra una
base existente: crea un nombre único de verificación y lo elimina al acabar.
El resultado `PASS` acredita el restore en el mismo clúster; no sustituye una
prueba de recuperación en un host vacío ni respalda roles globales de
PostgreSQL.

## Estado actual y bloqueos

La comprobación más reciente queda en `BLOCKED` únicamente por
`real_telemetry_fresh=false`:

- La base tiene 3 cuentas, 40 bots y 8.831 trades históricos, pero 0
  heartbeats y 0 snapshots de equity para las dos cuentas `BROKER_REAL`.
- Los servicios de MCP de BEPB y JJTI escuchan en el VPS y el túnel SSH de
  lectura funciona, pero las llamadas MCP reciben `HTTP 401`. No se intentó
  alterar tokens, EAs, terminales, gráficos ni AutoTrading.
- Telegram no está configurado en el core; por tanto la entrega real de alertas
  no puede certificarse. La lógica de alertas y sus reintentos sí se validó de
  forma aislada con mock.
- Falta recorrido autenticado del operador y comprobación visual de WebSocket.

Mientras esos puntos sigan abiertos, StratOS puede conservar y presentar el
histórico disponible, pero **no está habilitado como panel de observación
diaria de las cuentas reales**. La cabecera debe mostrar desconexión/datos
stale, nunca una apariencia de telemetría viva.

## Validación aislada

El entorno efímero exclusivo ejecutó 125 pruebas verdes:

- 71 de core: ingesta idempotente, sellos, watchdog y alertas por posición sin
  SL.
- 34 de conector: buffer SQLite, polling, reintentos y outbox del reporter.
- 1 integración de corte/reanudación: tres fallos simulados, cuatro lotes
  drenados y un trade, snapshot y heartbeat persistidos sin duplicado.
- 19 de notificaciones y WebSocket con Redis aislado y Telegram mock.

La evidencia está en
`runtime/observation-tests-20260907/verification-report.md`. Esto demuestra
recuperación de software, no una caída real de diez minutos, reinicio del host
ni entrega Telegram real.
