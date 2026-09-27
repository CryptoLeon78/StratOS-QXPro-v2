# Plan de continuación — StratOS-QXPro-v2 (2026-09-27)

> Sustituye a `docs/PLAN_CONTINUACION_2026-09-02.md` como plan vigente (ese documento queda
> como snapshot histórico útil, no se ha vuelto a tocar desde su fecha mientras
> `docs/phase_status.md` acumuló ~20 entradas G13 nuevas después). Generado tras una
> auditoría completa del repo (lectura de `phase_status.md`, `backlog.md`, ADRs,
> `PLAN_CONTINUACION_2026-09-02.md`, ejecución real de las 4 suites de test, grep de
> TODO/FIXME, y escaneo de candidatos a limpieza) más el trabajo cerrado en esta misma
> sesión (G13-67 a G13-72).
>
> **Regla de uso**: este documento es un mapa, no una autorización. Nada de lo que
> propone aquí se ejecuta sin que una sesión futura lo retome explícitamente, y las
> tareas marcadas "requiere decisión del operador" NO se resuelven por inferencia — se
> preguntan, igual que exige `comportamiento.md`.

---

## 0. Cómo usar este documento

1. Al abrir una sesión nueva, lee primero `CLAUDE.md`, `docs/phase_status.md` y
   `ASSUMPTIONS.md` (regla de continuidad ya establecida) — **este plan es el cuarto
   documento**, no el primero: da el mapa completo, pero el estado línea a línea vive en
   esos tres.
2. Las secciones 1-3 son snapshot verificado (hechos, no opiniones). La sección 4 es lo
   pendiente. La sección 5 es limpieza. La sección 6 es el orden recomendado. La 7 son
   preguntas bloqueantes para el operador. La 8 es el mensaje literal para abrir una
   sesión nueva sin perder contexto.
3. Cuando una tarea de este plan se cierre, táchala aquí (`~~texto~~`) con una línea de
   una frase diciendo dónde quedó documentada en detalle (`ASSUMPTIONS.md`,
   `phase_status.md` o `backlog.md`) — el detalle vive siempre en esos tres, este plan
   solo indexa.

---

## 1. Resumen ejecutivo del estado actual (2026-09-27, tras G13-67 a G13-72)

- **Fase activa**: G13 — "Stack operacional real/incubadora/análisis". Fundación
  implementada; los gates que faltan son **externos** (evidencia real de mercado, tiempo
  de incubación, decisiones del operador), no trabajo de código pendiente de escribir.
- **Ningún candidato tiene todavía `BACKTEST_VALIDATED` real ni ha entrado en cola de
  Incubadora.** Las dos candidatas AUDCAD (asset_id 958/2.92.87 y 479/3.4.65, magics
  295/243) están en F4/F5 (adjunto demo hecho, observación posterior a la entrada F5 sin
  trades demo todavía). Esto sigue exactamente igual tras el trabajo de hoy — G13-67 a
  G13-72 corrigieron el GATE que decide si el *coste* del backtest es comparable a MT5,
  no crearon ninguna candidata nueva.
- **Suites de test, ejecutadas de verdad en esta sesión**:
  | Suite | Resultado | Nota |
  |---|---|---|
  | `core-engine` (`pytest core-engine/tests -q`) | **680 passed, 8 failed** | Los 8 fallos son 100% `test_g8_acceptance_criteria.py`, causa única: Postgres local sin migrar al head (`column bot.origin_kind does not exist`). Ver §4.5. |
  | `scripts` (`pytest scripts -q`) | **268 passed, 1 skipped** | Verde. |
  | `frontend` (`npm test`, vitest) | **58/58 passed** (22 ficheros) | Verde. |
  | `frontend` (`npm run build`) | **0 errores TS** | Aviso no bloqueante: chunk `recharts-*` >500kB, ya conocido. |
  | `capa2_candidate_selector` (`pytest`, repo raíz) | **54/54 passed** | Verde (hoy). |
  | `spread_sqx` (`pytest`, repo raíz) | **174/174 passed** | Verde (hoy). |
- **`dist/StratOS_Operational.exe`**: compilado 2026-09-02 01:57, **29 commits de
  `scripts/` por detrás** del HEAD actual (`e96b322`, 2026-09-27). No incorpora nada de
  G13-4x a G13-72. Mismo patrón de deuda que ya se había cerrado una vez (backlog A6,
  "0 scripts por detrás" el 2026-09-02).
- **Cero TODO/FIXME/HACK/XXX reales** en `core-engine/src` ni `frontend/src` (grep
  verificado; los únicos matches son la palabra española "todo/todos/toda" en
  comentarios, no marcadores de deuda).
- **Repo anidado sin resolver**: `StratOS-QXPro-v2` es un repo git propio con remoto
  propio, pero el repo padre `SQX_144_Full2` sigue trackeando sus ~140+ ficheros
  directamente en su propio índice en vez de como submódulo o ruta ignorada. Ya señalado
  en el plan del 2026-09-02 (P0.1) y **sigue sin resolver 25 días después**.

---

## 2. Snapshot verificado de salud

### 2.1 Migraciones / entorno local

- `alembic current` (Postgres local de `core-engine`): **`3960d7d19b0d`**.
- `alembic heads` (cadena real del código): **`c8d9e0f1a2b3`**.
- El Postgres local NO está al día. Esto es *drift de entorno de desarrollo*, no
  necesariamente un problema de CI (que migra desde cero en cada run y da 10/10 verde
  según entradas recientes de `phase_status.md`). Corregirlo es un `alembic upgrade head`
  contra el Postgres local — trivial, pero debe hacerse antes de fiarse de cualquier test
  que toque `Bot`/`origin_kind` en local.

### 2.2 ADRs

11 ADRs + README, ya indexados correctamente tras el fix de hoy (§ver commit de esta
sesión). Dos anotaciones de estado añadidas al índice:
- **0006** (Graveyard sin fecha de inicio) — parcialmente superado por G13-66, el propio
  documento no se ha reescrito.
- **0011** (Pipeline operacional G13, F0-F7 encolable) — supersedido por 0012 (Pipeline
  pivotó a Incubadora/portfolios), el propio documento no tiene nota de superseded.

Ninguno de los dos requiere reescritura urgente (son decisiones ya cerradas en la
práctica, el "problema" es solo que el texto del ADR no lo refleja) — pero si se hace una
pasada de higiene documental, **añadir un párrafo "Superado por…" al principio de 0006 y
0011** es la forma correcta de cerrarlo (nunca editar la decisión original, solo anotar
su estado vigente).

### 2.3 Especificación (`doc_app/PROMPT_MAESTRO.md`) vs implementación

Huecos de spec ya conocidos y documentados como desviación deliberada (no "olvido"):
- **PARTE 9** (`/ingest/execution`, TCA v1.1): sin consumidor real — el EA reporter no
  manda fills reales todavía. Ver §4.2 (`ea_required_version`, TCA/Perfil de broker en
  backlog.md).
- **PARTE 3** (token de servicio api-gateway↔core-engine): implementado distinto a spec,
  documentado en ADR 0007 (proxy pass-through).
- **PARTE 7** (11 pestañas, Pipeline con F1-F7 completo): Pipeline visible NO refleja
  F1-F7 (retirado por decisión del operador, ADR 0012). Desviación deliberada y
  documentada, no un hueco a rellenar.
- **PARTE 6.3** (gate 7 criterios) vs capturas: implementado a spec real, no al mockup
  (ADR 0004).

Ninguno de estos 4 es "trabajo pendiente" en sentido estricto — son desviaciones ya
decididas y documentadas. Se listan aquí para que quede explícito que se revisaron, no
para reabrirlos.

---

## 3. Trabajo cerrado en esta sesión (2026-09-27, G13-67 a G13-72) — resumen para quien no la vivió

Detalle completo, código exacto, comandos de reproducción y tests en `ASSUMPTIONS.md`
(entradas G13-67 a G13-72) y `docs/phase_status.md` (entrada añadida hoy al principio de
la sección G13). Resumen de una frase por hito:

1. **G13-67**: causa raíz real del bloqueo de costes AUDCAD — el swap en `data.db` estaba
   invertido de signo y ~8x infravalorado; corregidos 15 instrumentos Darwinex.
2. **G13-68**: `close_target_terminal` (cierre del terminal MT5 antes del Tester) se hizo
   auto-reparable con reintentos.
3. **G13-69**: el gate de costes se cablea con `economia.py`/`darwinex.py` de
   `spread_sqx` — cross-check en vivo del swap contra MT5 + web pública antes de un
   lanzamiento real.
4. **G13-70**: bug real encontrado y corregido — el resellado post-Tester perdía el
   bloqueo del cross-check en vivo; una corrida selló `PROVEN` sin el swap confirmado de
   verdad. Corregido, con test de regresión.
5. **G13-71**: decisión del operador — MT5 en vivo manda sobre una web Darwinex ya
   marcada como conocida-desactualizada; implementado como registro declarativo editable
   (`politica_spread.json`), nunca como excepción oculta en código.
6. **G13-72**: el terminal que abre el cross-check en vivo no se podía cerrar por
   automatización una vez conectado a la cuenta real. Auditado el resto del proyecto
   (confirmado: no afecta a ninguna otra app) y corregido alineando el cross-check con el
   patrón ya probado del resto del código (nunca abre/cierra el terminal por su cuenta,
   solo consulta si ya estaba abierto).
7. **Resultado final**: manifiesto `20260927T123447Z_ed75e0ea14f9` sellado `PROVEN` de
   punta a punta con el código ya corregido. Sigue siendo 1 sola estrategia diagnóstica
   fuera de cola — no crea `BACKTEST_VALIDATED` ni candidata nueva.

---

## 4. PENDIENTE — lo que falta para terminar la aplicación

### 4.1 Gates operativos bloqueantes (requieren evidencia externa o decisión del operador — NO son código)

Estos son los genuinamente abiertos según `docs/phase_status.md` a fecha de hoy. Ninguno
se resuelve escribiendo código sin más — todos necesitan, o bien tiempo real de mercado,
o bien una decisión del operador, o bien acceso a un entorno (Contabo VPS) que Claude no
tiene.

1. **Candidata real con `BACKTEST_VALIDATED` + baseline + admisión a Incubadora.** Cero
   candidatas lo tienen todavía. Requiere: (a) un backtest cuyo gate de costes dé
   `PROVEN` **dentro del flujo operacional normal** (no una corrida diagnóstica aislada
   como la de hoy — AUDCAD sigue fuera de cola), (b) que pase el resto del pipeline
   contractual F1→F4 con los 7 criterios, (c) baseline aplicable, (d) manifiesto/adjunto
   demo por gráfico. Matriz completa de qué falta exactamente en
   `docs/g13_closure_gate_matrix.md`.
2. **F5→F6 de las dos candidatas AUDCAD (42/43, magics 295/243).** Están en observación
   F5 desde el 2026-09-10, con 0 trades demo y 1 día válido en la última evaluación F6
   real (`POSTPONE`). Necesitan: más días de observación con telemetría real desde la
   entrada F5, y ≥30 trades OOS demo antes de que el evaluador F6 pueda dar `APPROVE`.
   **Esto es tiempo de mercado, no código.**
3. **`incubator_admission` desde evidencia sellada** (ADR 0012, marcado "pendiente
   imprescindible" en `phase_status.md` G13-55) — el mecanismo de admisión formal a
   Incubadora sin reintroducir F1-F3 como fases visibles. Confirmar si sigue sin
   implementar o si quedó cubierto implícitamente por el flujo de adjunto demo de G13-41
   — **requiere lectura dedicada de `routers/pipeline.py` para confirmarlo con certeza**,
   no asumir por el nombre.
4. **Agente Windows en el VPS Contabo (G13-46/47)**: F1 (FORJA/SQX encolado) y F2 (Tester
   secuencial) están implementados y testeados localmente, pero el agente **no está
   instalado ni validado en el VPS real**. Sin esto, el flujo F1→F2 automático no
   funciona fuera de local. Requiere acceso al VPS (fuera del alcance de una sesión de
   Claude sin ese acceso).
5. **Gate de correlación cross-source (G13-56)**: "adaptar el gate antiguo de admisión
   para que no compare series de fuentes diferentes" (`MT5_BACKTEST` vs `MT5_REAL`) —
   pendiente de diseño, no solo de código. Necesita decisión de qué comparación
   contractual homogénea sustituye a la actual antes de picar código.
6. **Segunda corrida diagnóstica de costes retenida (G13-59/61, distinta de la de hoy)**:
   necesita un proyecto/databank SQX duplicado recalculable + serie histórica de tarifas
   Darwinex completa — ninguna de las dos existe todavía.
7. **P4.2 (recorrido autenticado UI+WebSocket) y P4.4 (baselines visuales Playwright)**:
   siguen "PENDIENTE" en `PLAN_CONTINUACION_2026-09-02.md`, **sin cambio 25 días
   después**. Requieren sesión autenticada real del operador en la UI — no se pueden
   completar por agente sin credenciales/entorno.
8. ~~**G11-f**~~ **VERIFICADO 2026-09-27, sigue bloqueado, sin cambio**: `close_target_terminal`
   (G13-68/72) toca un flujo de automatización totalmente distinto (Strategy Tester vía
   `/config` de `run_operational_sqx_mt5_backtest.py`), no el MCP nativo de MT5 cuyo
   `tester_run_backtest` es el que falla. Nada en el trabajo de hoy lo toca. Sigue
   requiriendo que el operador deje operativo el Strategy Tester del VPS demo.
9. **G12-00 "CIERRE DE UI/WS PENDIENTE"** (fase anterior, sigue formalmente abierta) y
   **G12 procedencia de pestañas mezclada** (`docs/g12_tabs_provenance_validation.md`):
   Portfolio/Riesgo/Auditoría/Dominical siguen sin selectores/etiquetas de procedencia
   consistentes (Bots/Pipeline/Cuentas-EA ya los tienen).

### 4.2 Deuda de código/documentación (de `docs/backlog.md`, ítems sin tachar)

Estos SÍ son tareas de código/documentación bien acotadas, ninguna bloqueada por tiempo
de mercado:

1. **`docs/registro_*_MN_*.md` sin regenerar** (backlog A13, el único de los `[AXX]`
   numerados que sigue abierto según `phase_status.md` L227-230): registran el comment
   con el magic legacy en vez de los magics cortos ya desplegados. Regenerarlos desde el
   post-scan en vez de mantenerlos a mano. **Acotado, bajo riesgo, buena tarea de
   arranque para una sesión nueva.**
2. ~~**Desincronización backlog.md vs phase_status.md sobre G13-49**~~ **RESUELTO
   2026-09-27**: verificado contra `stratos_operational` real (no la BD de test/seed que
   usa pytest — esa no tiene las candidatas AUDCAD). `pipeline_candidate.current_phase='F5'`
   para bot 42 (magic 295) y bot 43 (magic 243), `entered_phase_at=2026-09-10`. Tenía razón
   `phase_status.md`; `backlog.md` estaba desactualizado y ya se corrigió.
3. **Selectores/etiquetas de procedencia** para Portfolio, Salud, Riesgo, Auditoría y
   Dominical (backlog L515) — mismo patrón ya aplicado a Bots/Pipeline/Cuentas-EA,
   extenderlo al resto de pestañas.
4. **G13-61 persistencia pendiente** (backlog L523): el evento de sensibilidad de tarifa
   vigente se generó y validó en dry-run, pero la escritura real no se completó porque
   `stratos_operational` no existía en el Postgres local de esa sesión. Verificar si
   sigue así y completar la escritura si el Postgres ya está disponible.
5. **`USDJPYH1Lcity_5.15.110` con candidato F4 y bot F3 simultáneamente** (backlog L531,
   G12): requiere una transición append-only auditada para corregir la inconsistencia —
   **nunca editar directamente**, seguir el mismo patrón append-only usado en el resto
   del proyecto.
6. **`e2e-acceptance-full` criterio 9 (Lyra×Phoenix)** (backlog L538): roto, no
   determinista, decisión explícita de NO investigarlo por ahora. Dejar así salvo que el
   operador pida retomarlo.
7. **Precios sintéticos no realistas** en GDAXI/NDX/SPX500/US30 del seed (backlog L539) —
   cosmético, bajo impacto, solo importa si se usa el seed `full` para demos visuales.
8. ~~**Tabla `Baseline` nunca se crea**~~ **RESUELTO, verificado 2026-09-27**: sí se crea.
   2 filas reales en `stratos_operational` (`id=2`→bot 42, `id=3`→bot 43,
   `source=BACKTEST`), obra de `import_archived_sqx_mt5_evidence.py` (G13-49). La entrada
   de `backlog.md` (línea de G7) no se había reconciliado con la de línea 564 del mismo
   fichero, que ya decía "RESUELTO EN CÓDIGO" — corregido.
9. **TCA y Perfil de broker** (backlog L601): depende de v1.1 del EA reporter, sin
   consumidor todavía. Ligado al hueco de PARTE 9 de la spec (§2.3).
10. **`ea_required_version`** (backlog L600): no existe el concepto de versión esperada
    del EA en ningún sitio del sistema — decisión de diseño pendiente antes de picar
    código (¿dónde vive esa versión esperada? ¿por candidata, por perfil, global?).

### 4.3 Higiene de repo / documentación desincronizada

1. ~~**ADR README sin indexar 0008/0011**~~ — **CORREGIDO en esta sesión** (ver commit).
2. **Repo anidado `StratOS-QXPro-v2` dentro de `SQX_144_Full2`**: sigue sin decidirse si
   convertirlo en submódulo git propio o excluirlo del índice del repo padre. Señalado ya
   en `PLAN_CONTINUACION_2026-09-02.md` P0.1, **sin resolver 25 días después**. Esto es
   una **decisión del operador**, no algo que Claude deba decidir unilateralmente — tiene
   implicaciones de flujo de trabajo (cómo se hacen los `git push`, si hace falta
   `git submodule update`, etc.). Ver §7 (pregunta bloqueante).
3. **`Apps_entorno_SQX/SQX_vs_MT5_Panel/__pycache__/*.pyc` trackeados en git** (repo
   raíz): 8 ficheros `.pyc` aparecen como modificados en cada sesión que ejecuta esos
   scripts, porque están commiteados cuando deberían estar en `.gitignore`. Arreglo
   trivial: `git rm --cached` esos 8 ficheros + confirmar que `__pycache__/` ya está en
   `.gitignore` del repo raíz (ya lo está, línea 33 de `.gitignore` según lo visto en
   sesiones anteriores) — el problema es que se commitearon ANTES de que existiera esa
   regla.
4. **Snapshot vs plan vigente**: `PLAN_CONTINUACION_2026-09-02.md` queda como histórico;
   este documento (`PLAN_CONTINUACION_2026-09-27.md`) es el vigente a partir de hoy.

### 4.4 Entorno local desincronizado

1. ~~**Postgres local sin migrar al head**~~ **HECHO 2026-09-27 (tarde)**: `alembic
   upgrade head` aplicado (`3960d7d19b0d` → `c8d9e0f1a2b3`). Los 8 fallos bajan a 3
   (criterios 6/7/8 de `test_g8_acceptance_criteria.py`), pero por una causa distinta a
   la esperada: estado sucio preexistente en la base local (`Alert` de auditoría sin
   resolver), no drift de esquema. Ver `docs/phase_status.md`, entrada de hoy. Queda
   pendiente decidir si se limpia la base o se investiga por qué persiste ese estado.
2. **`dist/StratOS_Operational.exe` 29 commits por detrás**: regenerar el build
   (`build_desktop.ps1` o el proceso equivalente ya documentado en el propio repo) para
   que incorpore G13-4x a G13-72. Mismo patrón de deuda que ya se cerró una vez el
   2026-09-02 (backlog A6) — **vale la pena preguntarse si conviene automatizar esto en
   CI** en vez de volver a acumularlo por tercera vez.

---

## 5. PLAN DE LIMPIEZA — archivos obsoletos/no usados/desactualizados

**Ninguno de los siguientes se ha borrado.** Es una lista de candidatos con la evidencia
que los respalda, para que una sesión futura (o el operador) decida y ejecute con
confirmación explícita — coherente con la regla de "nunca comandos destructivos sin
confirmación explícita en ese mismo mensaje".

### 5.1 Limpieza de bajo riesgo (candidatos claros, sin ambigüedad de negocio)

| Candidato | Evidencia | Acción sugerida |
|---|---|---|
| `Apps_entorno_SQX/SQX_vs_MT5_Panel/build_g13/` a `build_g13_v6/` (6 carpetas, 14MB c/u, 84MB total) | Builds PyInstaller iterativos intermedios, todas fechadas 2026-09-02, superadas por `dist/` (mismo día, más reciente). **Untracked en git** (no hay que hacer `git rm`, solo borrar del disco). | **Confirmado por el operador 2026-09-27, PENDIENTE DE EJECUCIÓN**: el `rm -rf` fue denegado por el sistema de permisos de la sesión de Claude. Comando exacto entregado al operador; ejecutar manualmente. |
| ~~`Apps_entorno_SQX/SQX_vs_MT5_Panel/dist_legacy/`~~ | **HECHO 2026-09-27**. | Commiteado. |
| ~~`Apps_entorno_SQX/SQX_vs_MT5_Panel/__pycache__/*.pyc` trackeados~~ | **HECHO 2026-09-27**: eran 15, no 8 (conteo del plan desactualizado). | `git rm --cached` aplicado y commiteado. |
| `runtime/operational/backtests_diagnostic/` — verificar antigüedad | 9 subcarpetas (2 del 2026-09-24, 7 del 2026-09-27). Cada una es evidencia sellada inmutable (nunca se borran manifiestos sellados por principio de auditoría), pero podría valer la pena mover las más antiguas a un almacenamiento frío si el directorio crece sin control. **No es limpieza en el sentido de "basura"** — es evidencia contractual, tratarla con el mismo cuidado que cualquier `run-manifest.json` sellado. |

### 5.2 Limpieza que requiere decisión del operador antes de tocar

| Candidato | Por qué no es automático |
|---|---|
| ~~`docs/AUDITORIA_2026-09-02.md`, `docs/PLAN_CONTINUACION_2026-09-02.md`, `docs/CANDIDATAS_FORWARD_2026-09-02.md`~~ | **HECHO 2026-09-27**: el operador confirmó archivar. `git mv` a `docs/historico/` (preserva historial); las 11 referencias cruzadas en otros `.md` corregidas a la nueva ruta. |
| Repo anidado `StratOS-QXPro-v2` sin submódulo (§4.3.2) | Cambiar esto afecta el flujo de trabajo diario de `git` del operador — es una decisión de arquitectura de repos, no limpieza de ficheros. Ver §7. |
| `dist/StratOS_Operational.exe` desactualizado | No se borra — se regenera. Requiere confirmar que el proceso de build (`build_desktop.ps1` o equivalente) sigue funcionando tal cual antes de invocarlo sin supervisión. |

### 5.3 Comandos sugeridos (NO ejecutados — para cuando el operador confirme)

```bash
# 5.1.a — builds PyInstaller intermedios superados (verificar antes que dist/ es el vigente)
rm -rf "Apps_entorno_SQX/SQX_vs_MT5_Panel/build_g13" \
       "Apps_entorno_SQX/SQX_vs_MT5_Panel/build_g13_v2" \
       "Apps_entorno_SQX/SQX_vs_MT5_Panel/build_g13_v3" \
       "Apps_entorno_SQX/SQX_vs_MT5_Panel/build_g13_v4" \
       "Apps_entorno_SQX/SQX_vs_MT5_Panel/build_g13_v5" \
       "Apps_entorno_SQX/SQX_vs_MT5_Panel/build_g13_v6"

# 5.1.b — commitear la eliminación de dist_legacy ya reflejada en git status (repo raíz SQX_144_Full2)
git add "Apps_entorno_SQX/SQX_vs_MT5_Panel/dist_legacy"
git commit -m "chore(sqx_vs_mt5_panel): elimina dist_legacy, ya reemplazado por dist/"

# 5.1.c — dejar de trackear los .pyc versionados por error (repo raíz SQX_144_Full2)
git rm --cached "Apps_entorno_SQX/SQX_vs_MT5_Panel/__pycache__/"*.pyc
git commit -m "chore(sqx_vs_mt5_panel): deja de trackear bytecode compilado (.pyc)"
```

---

## 6. Orden de trabajo recomendado (roadmap priorizado)

No es obligatorio seguir este orden exacto, pero minimiza dependencias cruzadas:

1. **Higiene rápida y de bajo riesgo (una sesión corta)**: §5.1 completo + §4.2.1
   (regenerar `docs/registro_*_MN_*.md`) + §4.2.2 (reconciliar backlog.md vs
   phase_status.md sobre G13-49, verificando contra la BD real).
2. **Entorno local al día**: `alembic upgrade head` local (§4.4.1) para poder confiar en
   la suite `core-engine` completa en sesiones futuras.
3. **Rebuild del ejecutable** (§4.4.2): regenerar `dist/StratOS_Operational.exe` con el
   código actual, y valorar si conviene automatizarlo (CI o un hook) para no volver a
   acumular 29 commits de deuda una tercera vez.
4. ~~**Verificaciones puntuales**~~ **HECHAS 2026-09-27**: G11-f sigue bloqueado, sin
   cambio (no relacionado con el trabajo de `close_target_terminal`). Tabla `Baseline`
   resuelta (2 filas reales, ver §4.2.8). `incubator_admission` implementado desde
   G13-30/G13-62 (`core/services/incubator_admission.py`), no era una pregunta abierta.
5. **Deuda de código acotada, sin dependencia de tiempo de mercado**: §4.2.3
   (selectores de procedencia en el resto de pestañas), §4.2.5 (transición append-only
   para `USDJPYH1Lcity_5.15.110`).
6. **Decisiones de arquitectura pendientes del operador** (§7): repo anidado, si
   automatizar el rebuild del exe, si retomar el criterio 9 de e2e-acceptance-full.
7. **Gates de tiempo/evidencia externa** (§4.1): esto avanza solo, no por trabajo de
   código — cada sesión futura solo necesita comprobar si ya hay suficiente evidencia
   real (trades demo, días de incubación) para que F5→F6 avance, y actuar cuando la haya.

---

## 7. Preguntas bloqueantes — RESPONDIDAS 2026-09-27 (tarde)

1. **Repo anidado**: convertir a submódulo git. **Ejecución pendiente** (§4.3.2 actualizado)
   — es cirugía de git no trivial (`git rm -r --cached` + `git submodule add` en el repo
   padre `SQX_144_Full2`), se hace como unidad propia después de esta ronda de docs.
2. **Rebuild del exe**: automatizar (CI o hook). **Pendiente de implementar** — añadir un
   step al workflow de CI de `StratOS-QXPro-v2` que regenere `dist/StratOS_Operational.exe`
   en cada push a `main`, o un hook local equivalente.
3. **Criterio 9 e2e (Lyra×Phoenix)**: retomarlo ahora. **Investigado y causa raíz
   confirmada en código, sin arreglar (ver `docs/backlog.md` G13-74)**: no es solo el
   criterio 9 — es un mecanismo de deriva de calendario compartido con los criterios 6/7/8,
   por `scripts/seed.py:88` usando reloj real (`datetime.now(UTC)`) para sweeps/escenarios
   mientras el perfil `full` fija su historia en `FULL_HISTORY_END=2026-06-30`. Arreglarlo
   bien exige tocar `seed.py`/`derived_states.py`/`scenarios.py` de forma coherente sin
   romper el `now` fresco deliberado de los heartbeats (comentario en `seed.py:154-167`) —
   se deja como unidad propia con plan mode, no un parche de una línea.
4. **Docs de 2026-09-02**: archivar en `docs/historico/`. **HECHO** — `git mv` de los 3
   ficheros + 11 referencias cruzadas corregidas en esta sesión.
5. **Segunda corrida diagnóstica de costes (G13-59/61)**: sin responder todavía — no se
   preguntó en la ronda de 4 (límite de `AskUserQuestion` por llamada). Sigue abierta para
   la próxima vez que se retome el gate de costes.

---

## 8. Mensaje de continuidad para nueva sesión de chat

Ver el mensaje formateado en la respuesta del chat (para copiar y pegar directamente al
abrir una sesión nueva). Su contenido resume: fase activa, qué se cerró hoy, qué sigue
abierto, y remite a este documento como mapa completo.
