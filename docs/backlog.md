# Backlog — StratOS-QXPro

Cosas detectadas fuera del scope de la fase en curso. No se actúa sobre ellas hasta que el operador las priorice.

- **Docs sueltos en `doc_app\` ajenos al prompt maestro**: `Documento_Auditoria_Estrategias_SQX.md`, `Documento_Auditoria_Estrategias_SQX (1).md` y `Strategy_Robustness_Auditor_SRA_Especificacion_Proyecto.md` pertenecen a otro proyecto ("SQX Analyzer Pro"), no al árbol de referencias de PARTE 0.1. Ver `ASSUMPTIONS.md` G0-09. Decidir si se archivan fuera de `doc_app\` o se quedan (no bloquean nada, `doc_app` es solo lectura para el agente).
- **`api-gateway\` real**: en G0 es un placeholder sin lógica ni cobertura de CI (ver ASSUMPTIONS G0-04). Revisar su alcance concreto (JWT, rate limit, WS broker según CLAUDE.md) cuando se ataque G5.
- **Página `docs\runbook.md` completa**: PARTE 14 la especifica con detalle (instalación 2 nodos, backups, rotación de API keys, calendario de decisiones); se escribe en G9, no en G0.
- **`eslint` y `vitest` en frontend**: PARTE 4 los lista en el stack de testing/CI, pero el `ci.yml` entregado solo corre `tsc && vite build` (sin lint ni tests) para el frontend. Se deja para cuando existan componentes reales que lintar/testear (G6), en vez de configurar reglas vacías ahora.
- **`Account.login` sin `UNIQUE`** (encontrado en G4 al escribir `core/ingest/accounts.py::resolve_account`): un seed con logins duplicados haría que la resolución por login lance `MultipleResultsFound` (500) en vez de fallar limpio o resolver de forma determinista. Gap real del esquema G1, fuera de alcance de G4 (no se toca el modelo sin más contexto) — decidir en una fase de hardening o cuando se escriba `scripts/seed.py` (G8) si el login debe ser único por diseño.
