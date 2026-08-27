# Runbook — StratOS-QXPro

PARTE 14 del prompt maestro. Este documento cubre lo que `README.md` deliberadamente deja fuera (instalación real en 2 nodos, backups, rotación de claves, playbook de alertas): operación de un despliegue REAL, no el arranque de desarrollo local (para eso, `README.md`).

**Honestidad operativa (léase antes de operar en real)**: las secciones de instalación de Nodo A (Windows+MT5) y Nodo B (Linux+certbot+dominio) están escritas a spec contra la documentación oficial de cada herramienta (NSSM, certbot, Docker Compose) pero **no se han ejecutado contra un VPS real, un terminal MT5 real, ni un dominio real** en ninguna sesión de este proyecto — mismo caveat que `mt5-connector/install_service.ps1` desde G4 (ver `ASSUMPTIONS.md` G4-17/G4-19). Las secciones de **backups SÍ están verificadas de verdad** (G9, contra Postgres local real) — ver esa sección para el detalle exacto de qué se probó y qué no.

## 1. Arquitectura de despliegue (2 nodos, PARTE 3)

| Nodo | SO | Qué corre | Por qué separado |
|---|---|---|---|
| **A** | Windows | terminal(es) MT5 + `mt5-connector` (servicio NSSM) | MetaTrader 5 solo corre en Windows; el conector necesita el terminal en el mismo host/LAN |
| **B** | Linux | `docker compose` completo (postgres, redis, core-engine, worker, scheduler, api-gateway, frontend, nginx) | el resto del sistema no tiene esa dependencia de SO — Linux es más barato y estándar para un VPS de servicio |

El Nodo A llama al Nodo B por HTTPS (`CORE_ENGINE_URL` del conector apuntando al dominio público del Nodo B, vía nginx+api-gateway) — nunca al revés, el conector es el único que inicia conexión.

## 2. Instalación — Nodo A (Windows, MT5 + conector)

**No verificado contra un Windows con MT5 real en ninguna sesión.** Pasos a spec:

1. Instalar Python 3.12 + el/los terminal(es) MT5 necesarios (login de solo lectura si el broker lo permite — el conector nunca envía órdenes, P4).
2. `cd mt5-connector; python -m venv .venv; .venv\Scripts\pip install -e .`
3. Copiar `mt5-connector\.env.example` → `.env`, rellenar `CORE_ENGINE_URL` (dominio público del Nodo B), `INGEST_API_KEY` (ver §4, rotación), `MT5_TERMINAL_PATH` por cuenta.
4. Instalar como servicio Windows con NSSM: `mt5-connector\install_service.ps1 -ApiKey "<clave real>" -CoreEngineUrl "https://<dominio-nodo-b>"` (ver el propio script para requisitos previos — NSSM en PATH, venv ya creado).
5. Verificar: `nssm status StratOSMt5Connector` → `SERVICE_RUNNING`; revisar `mt5-connector\logs\` por errores de conexión al primer arranque.

## 3. Instalación — Nodo B (Linux, docker compose + nginx + certbot)

**No verificado contra un VPS Linux ni un dominio real en ninguna sesión.** Pasos a spec:

1. Instalar Docker + Docker Compose v2 en el VPS.
2. Clonar el repo, copiar `.env.example` → `.env`, rellenar TODOS los `change-me` (contraseñas de Postgres, `JWT_SECRET` con una cadena aleatoria real ≥32 bytes, `INGEST_API_KEYS`, `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` si aplica).
3. `docker compose --profile prod up -d --build` (perfil `prod`, cuando se añada el servicio `nginx` — ver §8, pendiente en esta iteración de G9; hasta entonces, `docker compose up -d --build` expone `frontend`/`api-gateway` directo en los puertos de host ya mapeados, sin TLS).
4. TLS con certbot (modo webroot, sin exponer el puerto 80 de otro servicio):
   ```bash
   docker run --rm -v /etc/letsencrypt:/etc/letsencrypt -v /var/www/certbot:/var/www/certbot \
     certbot/certbot certonly --webroot -w /var/www/certbot \
     -d <dominio-real> --email <email-real> --agree-tos --non-interactive
   ```
   Renovación: cron diario ejecutando el mismo contenedor con `renew` en vez de `certonly` (certbot es idempotente, no renueva si no toca).
5. WAL archiving (RPO 24h/RTO 2h junto con los backups diarios de §4): montar `infra/postgres/postgresql.conf.example` como el `postgresql.conf` real del contenedor `postgres`, tras rellenar `WAL_ARCHIVE_DIR` con un destino real (disco separado o almacenamiento remoto montado) — ver los comentarios del propio fichero para el porqué de no montarlo por defecto en `docker-compose.yml`.
6. Verificar: `curl https://<dominio-real>/health` (vía nginx, cuando exista) o `curl http://<ip-vps>:8180/health` (api-gateway directo, hoy).

## 4. Backups (G9, verificado de verdad)

`scripts/backup_postgres.sh` (pg_dump diario, formato custom, vía `docker compose exec` — nunca abre una conexión TCP nueva ni toca `.env`) + `scripts/restore_postgres.sh` (restaura SIEMPRE a una BBDD de verificación separada, nunca sobre `stratos` directo).

**Programación**: cron diario en el Nodo B —
```cron
0 3 * * * cd /ruta/al/repo && BACKUP_DIR=/ruta/a/backups BACKUP_RETENTION_DAYS=14 scripts/backup_postgres.sh >> /var/log/stratos-backup.log 2>&1
```
(`BACKUP_RETENTION_DAYS` también en `.env.example`, cero hardcoding — el cron solo referencia la variable, el valor real vive en `.env`.)

**Verificado end-to-end en esta sesión** (G9, contra el Postgres local real de este entorno, no simulado): backup real de 4.6 MB → restore a `stratos_restore_verify` → recuentos de filas confirmados vía `SELECT count(*)` (no `n_live_tup` del hypertable padre, que es siempre 0 — la data vive en los chunks internos de TimescaleDB): `trade`=1257, `equity_snapshot`=88, `heartbeat_log`=86402.

**Hallazgo real, no oculto**: `pg_restore` ignora 6 `ALTER TABLE ... ADD CONSTRAINT` sobre las hypertables comprimidas (`trade`, `equity_snapshot`, `heartbeat_log`, G1) — TimescaleDB no soporta añadir FK constraints sobre una hypertable con compresión activa vía el camino estándar de `pg_restore`. **Los datos restauran al 100%** (verificado arriba); lo que falta son esas 3 FK, recuperables a mano tras un restore real:
```sql
ALTER TABLE trade ADD CONSTRAINT trade_account_id_fkey FOREIGN KEY (account_id) REFERENCES account(id);
ALTER TABLE trade ADD CONSTRAINT trade_bot_id_fkey FOREIGN KEY (bot_id) REFERENCES bot(id);
ALTER TABLE trade ADD CONSTRAINT trade_ingest_batch_id_fkey FOREIGN KEY (ingest_batch_id) REFERENCES ingest_batch(id);
ALTER TABLE equity_snapshot ADD CONSTRAINT equity_snapshot_account_id_fkey FOREIGN KEY (account_id) REFERENCES account(id);
ALTER TABLE heartbeat_log ADD CONSTRAINT heartbeat_log_account_id_fkey FOREIGN KEY (account_id) REFERENCES account(id);
```
(Si alguna de las 6 falla también por estar la hypertable comprimida en el momento de reaplicarla, descomprimir el chunk afectado primero — `SELECT decompress_chunk(...)` de TimescaleDB — antes de la `ALTER TABLE`.) `restore_postgres.sh` ya detecta "errors ignored on restore" en el log real de `pg_restore` y lo señala explícito, apuntando aquí.

**Verificación periódica recomendada**: ejecutar `restore_postgres.sh` contra el backup más reciente una vez al mes (RTO 2h de PARTE 14 exige saber que un backup SÍ restaura antes de necesitarlo de verdad, no descubrirlo en el incidente).

## 5. Rotación de API keys (G9, PARTE 14)

**`INGEST_API_KEYS`** (`core/ingest/security.py::require_api_key`) ya soporta una lista separada por comas, comparada en cada request sin caché — rotación sin downtime:
1. Añadir la clave nueva a `INGEST_API_KEYS` en `.env` del Nodo B (`clave-vieja,clave-nueva`), reiniciar `core-engine`/`worker`/`scheduler` (`docker compose restart core-engine worker scheduler`).
2. Actualizar `mt5-connector\.env` en el Nodo A con la clave nueva, reiniciar el servicio (`nssm restart StratOSMt5Connector`).
3. Confirmar que el conector vuelve a enviar sin errores 401 (`mt5-connector\logs\`).
4. Retirar la clave vieja de `INGEST_API_KEYS`, reiniciar de nuevo el Nodo B.

**`JWT_SECRET`**: rotar invalida INSTANTÁNEAMENTE todas las sesiones activas (no hay forma de rotarlo sin desconectar a todo el mundo — es la clave de firma, no una clave de API con lista). Procedimiento de "compromiso" (sospecha real de fuga), no rutinario:
1. Generar un secreto nuevo (≥32 bytes aleatorios reales, nunca un valor memorizable).
2. `JWT_SECRET=<nuevo>` en `.env` del Nodo B, `docker compose restart core-engine worker scheduler`.
3. Todos los usuarios deben volver a hacer login — comunicarlo antes de rotar si es una rotación planeada, no un incidente.
4. La denylist de revocación (G9, `auth/revocation.py`) vive en Redis, no en el secreto — sobrevive a esta rotación sin acción adicional.

## 6. Playbook de alertas (G9, PARTE 14)

Una entrada por combinación real `module`×`level` que el código ya emite (ver `core-engine/src/core/services/*.py`, `state_machines/*.py`, `ingest/services/positions.py` — nunca acción inventada, todas citadas literal del código real):

| Módulo | Nivel | Cuándo | Acción humana (`action_required`/`instruction_text` real) |
|---|---|---|---|
| `ingest_positions` | CRITICA | posición abierta sin SL (P5) | "Colocar SL de inmediato (P5)." |
| `audit` | CRITICA | discrepancia balance+flujos > tolerancia | "Revisar reconciliación en la pestaña Auditoría." |
| `config_drift` | CRITICA | EA en modo incorrecto (NARANJA + `EaState.mode=="REAL"`) | "Corregir el modo del EA en el terminal MT5." |
| `ums` | CRITICA | downgrade automático de fase (equity cae bajo el rango) | "Revisar la causa de la caída de equity." |
| `watchdog` | CRITICA | bot muerto o desbocado | "Revisar el bot en el terminal MT5." |
| `watchdog` | SUAVE | drift horario del VPS >120s | "Resincronizar el reloj del VPS." |
| `semaphore` | CRITICA/confirmación requerida | bot pasa a NARANJA | ver escalera de instrucciones abajo (`semaphore_naranja`, con el magic number real interpolado) |
| `semaphore` | SUAVE | bot pasa a AMARILLO | `semaphore_amarillo`: "Reducir sizing al 50% (bajar fraction Kelly). Aumentar frecuencia de revisión." |
| `killswitch` | escalonado, confirmación requerida en desescalada | DD de portfolio cruza un nivel | ver escalera L1-L4 abajo |
| `pipeline` | — | candidato pasa a cementerio | "Autopsia obligatoria antes de archivar en el Cementerio." |
| `challenger` | — | challenger en F6 >6 meses (overstay) | "Competitivo pero no superior — valorar retirar y liberar plaza" (`types.py::instruction_overstay`) |

**Escalera de kill-switch** (`config/thresholds.seed.json::instruction_templates`, literal):
- **L1**: "Notificar. Vigilar sin intervenir."
- **L2**: "Reducir sizing 50% en todos los bots."
- **L3**: "Cerrar todas las posiciones abiertas."
- **L4**: "Cerrar posiciones y DESACTIVAR todos los EAs."

Desescalada de cualquier nivel: **exige firma** (`signed_by`, nunca automática — `state_machines/killswitch.py::evaluate_killswitch_deescalation`).

**Escalera de semáforo**:
- **VERDE**: "Mantener. No tocar nada."
- **AMARILLO**: "Reducir sizing al 50% (bajar fraction Kelly). Aumentar frecuencia de revisión."
- **NARANJA**: "En el EA magic {magic}: desactivar apertura de nuevas posiciones (modo paper) y dejar cerrar las existentes por sus reglas." (requiere confirmación humana antes de aplicar)

## 7. Modo pequeña escala

Ver `config/small_scale.yaml` — documento de referencia estático (decisión G9, no wireado en runtime). Migrar un despliegue real a este modo es un procedimiento manual: reconfigurar `SystemConfig`/`thresholds.seed.json` a los 7 valores de ese fichero a mano, no cambiar `DEPLOYMENT_PROFILE` y reiniciar.

## 8. Actualizaciones (Alembic con backup previo)

1. `scripts/backup_postgres.sh` — backup previo SIEMPRE, sin excepción, antes de cualquier migración en producción.
2. `git pull`, revisar el changelog/commits de la actualización.
3. `docker compose build core-engine worker scheduler frontend api-gateway`.
4. `docker compose run --rm core-engine python -m alembic -c alembic.ini upgrade head` (migración antes de reiniciar los servicios, nunca en paralelo).
5. `docker compose up -d` (reinicia con las imágenes nuevas).
6. Verificar `curl .../health` en `core-engine`/`api-gateway`/`frontend` + revisar logs de arranque.
7. Si algo rompe: `docker compose run --rm core-engine python -m alembic -c alembic.ini downgrade -1` + `scripts/restore_postgres.sh` del backup del paso 1 si la migración ya escribió datos incompatibles.

## 9. Calendario de decisiones (checklist imprimible, PARTE 14 literal)

- [ ] **Domingo (20 min, mercado cerrado)**: revisión técnica (errores de EA, desconexiones, órdenes rechazadas) + copiar noticias de la semana entrante al filtro horario. **PROHIBIDO mirar rentabilidad** (la vista dominical la oculta — ver `docs/backlog.md`, superficie de UI aún sin construir).
- [ ] **Cada 15 días**: semáforos vs baseline; confirmar los AMARILLO al 50% de sizing.
- [ ] **Primer domingo del mes**: bots vs backtest (rebalanceo de bloques si |Δ|>10 pp); correlaciones; **ejecutar el retiro mensual** — una línea más del checklist, nunca un impulso; retiro mensual SIN EXCEPCIÓN aunque el mes sea negativo (es nómina: retorno medio 2,69% vs max DD 4,76%).
- [ ] **Trimestral**: robustez, alpha decay, informe de coste de impulsos.
- [ ] **Enero**: reestructuración anual (resolver pares redundantes, contratos Monte Carlo, overstay de challengers).
