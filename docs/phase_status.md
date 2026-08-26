# Estado de fase — StratOS-QXPro

> Se actualiza SIEMPRE al cerrar trabajo (regla de continuidad entre sesiones). Al abrir sesión, leer esto + `CLAUDE.md` + `ASSUMPTIONS.md` antes de proponer nada.

## Fase actual: G3 — Máquinas de estado (TDD)

**Estado**: **cerrada por completo**. Las 3 máquinas de estado formales de PARTE 6 (semáforo, kill-switch, pipeline gate + challenger/cementerio) implementadas con TDD real (rojo confirmado con `pytest` antes de cada implementación, nunca narrado) y CI en GitHub Actions verde 3/3 (run [`32956020786`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/32956020786)).

### Verde (verificado con comandos reales en esta sesión)
- `core-engine/src/core/state_machines/` (6 módulos: `types`, `hash_chain`, `semaphore`, `killswitch`, `pipeline`, `challenger`) — **100 % de cobertura, 357/357 statements, 66/66 tests** (exige PARTE 12: ≥95 %). Suite completa del proyecto: **169/169 en verde** (sin regresión de G0/G1/G2).
- Las 5 transiciones de la tabla 6.1 (semáforo), las 4 de 6.2 (kill-switch, con desescalado firmado + histéresis 2pp), el gate de 7 criterios de 6.3 con sus 2 casos límite literales del seed (Estige PF32,75/9 trades → HOLD; Sigma MR 95d/51 → GO), los 5 criterios de rotación darwiniana con el ejemplo real de Helios (Sharpe ×1,22, p=0,03), y el cementerio (autopsia obligatoria, sin retorno) — todos con persistencia real contra Postgres (`stratos_test`) + `fakeredis`, verificando fila insertada, hash-chain encadenado de verdad y el mensaje publicado en el topic Redis correcto.
- Property-based con `hypothesis` en las 3 propiedades que PARTE 12 exige explícitamente: ninguna transición de semáforo inválida alcanzable, kill-switch nunca desescala sin firma, cementerio sin retorno (siempre rechaza, cualquier input).
- Demo obligatoria de PARTE 12 (Poseidón Trend GER40, magic 118685, PF 1,18 vs 1,94, 15 días en AMARILLO): `instruction_text` verificado carácter a carácter contra el literal exacto de la captura.
- `ruff check` + `ruff format --check` + `mypy --config-file core-engine/pyproject.toml ... --strict` limpios. `scan_hardcoding`: solo defaults de `*Config` que mirror-ean 1:1 el seed (patrón G2-01/04, formalizado como G3-03).

### Diseño propio documentado en ASSUMPTIONS (G3-01 a G3-06)
2 huecos nuevos en `thresholds.seed.json` (`semaphore_sizing_*`, `semaphore_pf_recover`, `semaphore_dd_contract_orange_ratio`) · algoritmo del hash-chain (SHA-256, no fijado en PARTE 5.2) · severidad `SUAVE` para VERDE→AMARILLO (no fijada en la tabla 6.1) · prioridad de veredicto en el gate de pipeline (KILL > SIZING_CAP > GO > HOLD, PARTE 6.3 no fija el orden explícito).

### Pendiente — depende del operador, no de más trabajo de agente
- Revisar los defaults/diseños propios acumulados en `ASSUMPTIONS.md` antes de G4 (mt5-connector), que empezará a alimentar estas máquinas con datos reales del terminal.

## Fases cerradas

### G2 — Fórmulas (cerrada)
20 fórmulas de PARTE 8, 100% cobertura (217/217 statements, 87/87 tests), CI verde 3/3 (run [`32939959347`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/32939959347)). Detalle en `ASSUMPTIONS.md` G2-01 a G2-07.

### G1 — Modelo de datos (cerrada)
25/25 tablas de PARTE 5.2, migraciones Alembic 0001/0002, rol `stratos_app` con grants exactos, 16/16 tests contra Postgres/TimescaleDB real. Detalle en `ASSUMPTIONS.md` G1-01 a G1-14 y el historial de commits.

### G0 — Scaffold + tooling de gobierno (cerrada)
Repo git independiente en `https://github.com/CryptoLeon78/StratOS-QXPro-v2` (privado), `.mcp.json` operativo, `docker compose up -d postgres redis` healthy, CI verde, `config/thresholds.seed.json` (61 claves), scaffolds de `core-engine`/`api-gateway`/`frontend`. Detalle en `ASSUMPTIONS.md` G0-01 a G0-14.

## Fases futuras (PARTE 12)
G4 mt5-connector + simulador · G5 core-engine (servicios/API/WS) · G6 Frontend shell + Resumen · G7 Frontend resto de pestañas · G8 Seed + E2E · G9 Hardening.
