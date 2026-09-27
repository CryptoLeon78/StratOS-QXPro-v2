# StratOS-QXPro-v2 — gobierno del subproyecto (Codex)

Este directorio es un **repositorio git propio** (`CryptoLeon78/StratOS-QXPro-v2`), anidado dentro
de la instalación de SQX pero con su propio historial, CI y reglas. El `AGENTS.md` de la raíz
describe el entorno SQX (minado, blocksettings, FORJA); **no describe este proyecto**. Manda este
fichero.

Creado 2026-09-02 tras la auditoría: hasta entonces Codex trabajaba aquí heredando sólo el índice
de la raíz, que ni menciona StratOS. Ver `docs/historico/AUDITORIA_2026-09-02.md` H10.

## Antes de proponer nada

Lee, en este orden:

1. `docs/phase_status.md` — fase activa, qué está verde, qué falta. Es lo primero que se actualiza
   al cerrar trabajo.
2. `ASSUMPTIONS.md` — todas las decisiones ante ambigüedad, numeradas `G<fase>-<NN>`. Es el registro
   autoritativo de por qué el sistema es como es.
3. `docs/backlog.md` — trabajo abierto, clasificado en defecto / capacidad bloqueada por datos /
   decisión deliberada.
4. `docs/historico/AUDITORIA_2026-09-02.md` — estado de las garantías (CI, tests, lint) y deuda abierta (snapshot histórico).

La especificación contractual completa está en `doc_app/PROMPT_MAESTRO.md` (PARTES 0–17).
**`doc_app/` y `capturas_proyecto_dashboard/` son de sólo lectura**: son entradas contractuales.

## Reglas que no se negocian

- **Español**, tono técnico y directo. Sin adulación ni preámbulos.
- **Plan antes de código.** Scope cerrado: lo que no pertenece a la unidad actual va a
  `docs/backlog.md` y se sigue. Nada de "ya que estoy, mejoro esto otro".
- **Cero hardcoding (P11).** Umbrales → `SystemConfig`/`config/thresholds.seed.json`; colores →
  `design_tokens.json`; textos → `frontend/src/styles/ui_strings.es.json`. Si un literal no tiene
  hogar declarado, no se escribe. Verificar con `scan_hardcoding` del MCP `stratos` — **añádelo a
  `.codex/config.toml` si no lo tienes**, hoy sólo registra `sqx_forja`.
- **Arquitectura sagrada**: lógica de negocio sólo en `core-engine`; frontend sin reglas; conector
  **read-only**; gateway sin dominio.
- **TDD** en `formulas/` y `state_machines/`. En el resto, tests en el mismo commit.
- **Un commit por unidad completada**, conventional commits (`feat(core):`, `test(formulas):`).
  Prohibido el commit de fase entera.
- **Nunca afirmes "hecho", "funciona" o "pasan los tests" sin haberlo ejecutado en esa sesión.**
  Si no puedes verificar algo, dilo: "no verificado".

## Límites operativos con dinero real

- **JJTI (`4000059903`) y BEPB (`4000055216`) son cuentas Darwinex Live reales.** StratOS es
  estrictamente read-only sobre ellas: nunca envía órdenes, nunca modifica EAs, gráficos, perfiles
  ni AutoTrading. Toda observación es por SSH/SFTP de lectura.
- **No fuerces el cierre de un terminal MT5.** El lanzador de backtests pide un cierre limpio de la
  instancia Tester autorizada y falla si no lo acepta. Nunca `taskkill`, nunca sobre JJTI/BEPB.
- **El único camino futuro con operaciones** es una cuenta `BROKER_DEMO` de Incubadora, máximo 8
  gráficos, después de backtest y baseline. Hoy está bloqueada.
- **No inventes evidencia.** Una ausencia se declara como ausencia (`—`, `NULL`, `ABSENT`), nunca se
  rellena con una estimación. Un nombre de carpeta (`WFM`, `MC`, `RETEST OOS`) no es una métrica.

## Antes de cerrar cualquier unidad

```bash
.venv/Scripts/python.exe -m ruff check core-engine/
.venv/Scripts/python.exe -m ruff format --check core-engine/
.venv/Scripts/python.exe -m mypy --config-file core-engine/pyproject.toml core-engine/src/ --strict
.venv/Scripts/python.exe -m pytest <suite tocada> -q
```

**A fecha 2026-09-02 los tres primeros están rojos** (7 + 8 + 7 hallazgos) y hay 2 tests rojos —
son deuda heredada, no la introduzcas tú y no la des por verde. Ver `docs/backlog.md` A1-A10.

## Convenciones que se han roto antes

- **Numeración de `ASSUMPTIONS.md`**: antes de añadir una entrada, comprueba el último número real
  con `grep -o 'G13-[0-9]*' ASSUMPTIONS.md | sort -u | tail -1`. Ya hubo una colisión (`G13-24`
  significaba dos cosas distintas en `ASSUMPTIONS.md` y en `phase_status.md`).
- **Toda decisión de contrato va a `ASSUMPTIONS.md`**, no sólo a `phase_status.md`. Si redefine qué
  se considera válido, además merece un ADR en `docs/adr/`.
- **Si actualizas un párrafo de `phase_status.md` que otro párrafo anterior contradice**, marca el
  anterior como supersedido en el mismo cambio.
- **Si un artefacto de `runtime/` deja de significar lo que decía**, dilo. El caso real:
  `docs/registro_BEPB_MN_bots_real_mt5_vps.md` pasó de "observación pre-migración" a "estado
  post-migración" y dejó un test rojo verificando la realidad anterior.

## Qué NO se versiona

`.env*` reales, `runtime/` (artefactos operativos, manifiestos sellados, evidencia local), `dist/`,
capturas de evidencia. Las plantillas sí: `.env.operational.example`,
`config/operational_sources.example.yaml`.
