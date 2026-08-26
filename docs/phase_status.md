# Estado de fase — StratOS-QXPro

> Se actualiza SIEMPRE al cerrar trabajo (regla de continuidad entre sesiones). Al abrir sesión, leer esto + `CLAUDE.md` + `ASSUMPTIONS.md` antes de proponer nada.

## Fase actual: G4 — mt5-connector + mt5-simulador + ingesta real

**Estado**: **cerrada en lo local, pendiente de confirmar CI verde** (GitHub Actions con congestión de runners al cierre de esta sesión — varios pushes quedaron en cola >15 min con "job was not acquired by Runner"; ver nota abajo. No se afirma "CI verde" sin el run real confirmado, por regla del proyecto).

### Verde (verificado con comandos reales en esta sesión)
- **5 paquetes nuevos/tocados, 299 tests, 100% en 3 de ellos**: `core-engine/src/core/ingest/` (213 statements, 48 tests, **100%** — los 7 endpoints de PARTE 9.1) · `shared-ingest-seal` (17 statements, 11 tests, **100%**) · `mt5-simulator` (97 statements, 11 tests, **100%**) · `mt5-connector` (371 statements, 55 tests, **94%** — 100% salvo `real_adapter.py` 71% y `main.py` 90%, los 2 módulos que tocan MT5/el proceso real y que NO se pueden verificar sin un terminal Windows) · `integration-tests` (1 test, el criterio de salida literal de G4).
- Los 7 endpoints `/ingest/*` de PARTE 9.1 con persistencia real, dedup idempotente (`ON CONFLICT`), sello SHA-256 verificado (mismatch → 422, cero filas) y P5 (posición sin SL → `Alert` CRITICA inline, auto-resuelta si el SL reaparece).
- `mt5-simulator`: 5 escenarios (`crash_21` es el único identificador literal contractual, PARTE 13) + `SimulatedMt5Client` determinista.
- `mt5-connector`: buffer SQLite store-and-forward, backoff exponencial (cap 5 min contractual), poller (4 cadencias), sender con clasificación transitorio/permanente de errores HTTP, `real_adapter.py` (no verificado, explícito) e `install_service.ps1` (NSSM, no verificado, explícito).
- **Criterio de salida de G4 probado de verdad** (`integration-tests`): corte de red simulado (comprimido en tiempo, no 10 min reales) → cero pérdidas, cero duplicados, verificado contra Postgres real.
- `ruff check` + `ruff format --check` + `mypy --strict` limpios en los 5 paquetes. `scan_hardcoding` limpio o justificado (ASSUMPTIONS G4-05/13/14/21).

### Diseño propio documentado en ASSUMPTIONS (G4-01 a G4-21)
Puntos más significativos: 2 tablas nuevas aprobadas por el operador (`VirtualTrade`/`EaState`) · mecánica de sellado cliente-calcula/servidor-verifica · hallazgo crítico de Pydantic estricto + JSON (Decimal como string, datetime con "Z") que habría roto el sello si no se hubiera verificado con HTTP real antes de codificar · `connector_instance_id`/`ts` de heartbeat añadidos a 6+1 DTOs que PARTE 9.1 no mostraba explícitos · bug real de Alembic (enum `create_type`) y de rutas de `.env` (`parents[N]` mal contado) encontrados via ejecución real · hallazgo de tooling (`concurrency=["greenlet"]` en coverage, sin el cual las rutas HTTP reportaban cobertura falsamente baja) · `real_adapter.py`/`main.py`/`install_service.ps1` explícitamente NO VERIFICADOS contra un terminal MT5 o Windows real.

### Pendiente — depende del operador, no de más trabajo de agente
- Confirmar que los 4 jobs de CI nuevos (`lint-mt5-connector`, `test-mt5-connector`, `lint-and-test-mt5-simulator`, `test-integration`) corren verdes en GitHub Actions una vez la cola de runners se libere — verificado localmente con la secuencia exacta de instalación, pero el run real de CI no llegó a completarse antes de cerrar esta sesión.
- `real_adapter.py`/`install_service.ps1` necesitan verificación real contra un terminal MT5 y un Windows con NSSM antes de considerarse listos para producción — ningún entorno de este tipo estuvo disponible en esta sesión.
- Revisar los diseños propios acumulados en `ASSUMPTIONS.md` (G4-01 a G4-21) antes de G5, que cablea estos endpoints a los servicios/API/WS reales.

## Fases cerradas

### G3 — Máquinas de estado (cerrada)
3 máquinas de estado (semáforo/kill-switch/pipeline+challenger), 100% cobertura (357/357 statements, 66/66 tests), CI verde 3/3 (run [`32956020786`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/32956020786)). Detalle en `ASSUMPTIONS.md` G3-01 a G3-06.

### G2 — Fórmulas (cerrada)
20 fórmulas de PARTE 8, 100% cobertura (217/217 statements, 87/87 tests), CI verde 3/3 (run [`32939959347`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/32939959347)). Detalle en `ASSUMPTIONS.md` G2-01 a G2-07.

### G1 — Modelo de datos (cerrada)
25/25 tablas de PARTE 5.2, migraciones Alembic 0001/0002, rol `stratos_app` con grants exactos, 16/16 tests contra Postgres/TimescaleDB real. Detalle en `ASSUMPTIONS.md` G1-01 a G1-14 y el historial de commits.

### G0 — Scaffold + tooling de gobierno (cerrada)
Repo git independiente en `https://github.com/CryptoLeon78/StratOS-QXPro-v2` (privado), `.mcp.json` operativo, `docker compose up -d postgres redis` healthy, CI verde, `config/thresholds.seed.json` (61 claves), scaffolds de `core-engine`/`api-gateway`/`frontend`. Detalle en `ASSUMPTIONS.md` G0-01 a G0-14.

## Fases futuras (PARTE 12)
G5 core-engine (servicios/API/WS) · G6 Frontend shell + Resumen · G7 Frontend resto de pestañas · G8 Seed + E2E · G9 Hardening.
