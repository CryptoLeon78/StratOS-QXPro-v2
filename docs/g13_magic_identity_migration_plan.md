# G13 — Plan de identidad compacta: nombre visible, comment MT5 y Magic Number

> Estado: **COMPLETADO EN LECTURA (2026-09-01)**. La propuesta aprobada fue aplicada manualmente por el operador y verificada sin mutar MT5 desde StratOS.
>
> Propósito: normalizar la identidad de EAs existentes y futuros sin perder trazabilidad histórica, respetando el límite de 30 caracteres del `comment` de MT5 y preservando la regla de que JJTI y BEPB se observan en modo estrictamente read-only desde StratOS.
>
> Este documento no autoriza cambios nuevos en MetaTrader, EAs, SQX, Forja, cuentas, gráficos ni magics. Conserva el contrato de la unidad ya cerrada y sirve como especificación para cualquier migración futura, que deberá tener propuesta, aprobación y evidencia propias.

> Cierre verificable: 40 pares aprobados `(cuenta, magic)` quedaron `MIGRATION_OBSERVED`; el NQ/JJTI magic `38` quedó `OPERATOR_RETAINED_OUT_OF_PROPOSAL`. El informe local, las reglas de deduplicación de perfiles y la explicación operativa están en `runtime/operational/magic_identity/post_migration_scan_report.json` y `docs/g13_magic_identity_operator_review.md`.

## 1. Decisión y resultado perseguido

Los magics actualmente contienen tanto números cortos como números largos derivados de convenciones históricas. Al concatenarlos con nombres de estrategias, varios `CustomComment` se aproximan o superan el presupuesto de 30 caracteres disponible en MT5. Esto dificulta la lectura humana y reduce el margen para mantener una identidad útil en informes, escaneos de gráficos e históricos.

La política futura será una **identidad compacta, estable y auditable**:

```text
comment_identity = <short_strategy_label>_MN<magic_number>
```

Ejemplos ilustrativos, no asignaciones reales:

```text
DAXM30stat_2.13.18_MN42
XAUm30Lstat_1.19.27_MN43
```

La misma cadena será el nombre operativo mostrado por defecto en StratOS y el `CustomComment` del EA. La identidad larga de SQX no desaparece: se conserva en un campo separado como `canonical_strategy_name`, junto con hashes, fuente, símbolo, timeframe y versión.

Un bot idéntico desplegado en JJTI y BEPB puede conservar el **mismo magic compacto global**. Si el operador aprueba expresamente labels de despliegue distintos por cuenta, se desdobla en identidades operativas por cuenta, con `technical_strategy_key` común y magics distintos; la identidad observable completa seguirá siendo `(account_login, magic_number)`.

## 2. Objetivos y no objetivos

### Objetivos

- Hacer legible cada trade, gráfico, informe y entrada de inventario con una misma identidad corta.
- Garantizar que todo nuevo magic sea único globalmente, no reutilizable y trazable a una estrategia concreta.
- Evitar dependencia de nombres de archivo, rutas o versiones para resolver un bot.
- Mantener una correspondencia auditable entre magic anterior y magic nuevo.
- Integrar la validación en los flujos futuros SQX → MQL5, Forja, admisión operacional e Incubadora.
- Detectar antes de exportar si el comment excede el límite MT5 o si dos identidades confluyen.

### No objetivos

- No cambiar retrospectivamente los `ticket`, deals, posiciones ni el histórico MT5 ya sellado.
- No deducir magics históricos faltantes a partir de comments, nombres o heurísticas.
- No modificar automáticamente EAs en real ni sus gráficos.
- No sobrescribir filas append-only de `external_ea_inventory`, `IngestBatch`, artefactos o transiciones F7.
- No usar el magic como indicador de perfil, activo, dirección, cuenta, fase de pipeline o fecha. Esa codificación compacta se degrada y rompe al evolucionar una estrategia.

## 3. Modelo de identidad canónica

La futura implementación separará explícitamente cinco conceptos:

| Campo | Función | Mutabilidad |
| --- | --- | --- |
| `strategy_key` | ID técnico estable de la estrategia lógica; no se muestra en MT5. | Inmutable |
| `canonical_strategy_name` | Nombre SQX completo, legible y versionado. | Nueva versión = nuevo registro |
| `magic_number` | Entero compacto asignado por registro global. | Nunca se reutiliza |
| `comment_identity` | Cadena MT5 de hasta 30 caracteres: `<short_strategy_label>_MN<magic_number>`. Es también el nombre de archivo operativo. | Inmutable para una asignación |
| `deployment_identity` | `(account_login, magic_number, ea_sha256, chart_id)` para cada instalación observada. | Append-only |

`strategy_key` deberá derivarse de evidencia verificable, no de un nombre: hashes SQX/MQL5 cuando existan, identidad SQX extraída, símbolo, timeframe, lado y versión lógica. Si se recompila el mismo MQL5 sin cambio semántico, el registro añade un hash de build como observación, no asigna automáticamente otro magic. Si cambian reglas de señal, gestión o versión operativa de modo material, se crea una nueva asignación de magic.

## 4. Contrato del Magic Number

### 4.1 Asignación

- Rango permitido: entero positivo compatible con el esquema y con MQL5; `0` queda reservado para ausencia declarada de magic en importaciones históricas.
- Fuente única: registro global append-only de G13; ni Forja, ni SQX, ni un EA elegido manualmente podrán inventar un valor fuera de ese registro.
- Secuencia: el asignador toma el siguiente entero libre y nunca reutiliza uno retirado, aunque una estrategia sea eliminada.
- Repetición multi-cuenta: una misma estrategia lógica puede usar el mismo magic en varias cuentas; la unicidad de despliegue exige cuenta + magic. Un desdoblamiento explícito por cuenta crea assignments distintos, pero conserva el `technical_strategy_key` común como evidencia.
- Variantes: estrategia, timeframe, símbolo, dirección o lógica materialmente distinta reciben magic distinto, incluso si comparten una parte del nombre.
- Colisión: una coincidencia `(account_login, magic_number)` con `strategy_key`, hash o comment distinto bloquea la propuesta y requiere resolución humana. Nunca se elige "la más parecida".

### 4.2 Reasignación de EAs ya desplegados

El cambio físico de un magic afecta a la identificación de posiciones y a la gestión del EA. Por ello el sistema sólo preparará un **plan de migración**, que el operador aplicará en MT5.

Antes de cambiar un EA existente deben cumplirse todos estos requisitos:

1. Gráfico, cuenta, EA, hash, símbolo, timeframe, magic anterior y comment actual escaneados y sellados.
2. No hay posiciones, órdenes pendientes ni operaciones parcialmente cerradas bajo el magic anterior; si las hay, la migración queda diferida o requiere un procedimiento explícito de coexistencia.
3. El nuevo EA conserva su lógica y parámetros efectivos salvo `MagicNumber`/`CustomComment`; cualquier otra diferencia invalida el cambio como simple migración de identidad.
4. El operador aplica el cambio y reinicia/recarga el EA siguiendo su procedimiento habitual.
5. Un escaneo posterior verifica exactamente el nuevo magic y comment por gráfico.
6. StratOS añade una nueva observación y un evento de `magic_migration`; no actualiza ni borra la observación anterior.

El histórico previo seguirá asociado a `legacy_magic` sólo cuando la fuente lo exponga. El HTML sin magic permanece huérfano: la migración no autoriza reasignarlo.

## 5. Contrato de `comment_identity`

### 5.1 Gramática

```text
comment_identity := short_strategy_label "_MN" magic_number
short_strategy_label := [A-Za-z0-9_.-]+  (sin espacios, sin separadores ambiguos)
```

Reglas:

- Longitud máxima configurable: `mt5_comment_max_chars = 30`.
- El sufijo final `_MN<MagicNumber>` es obligatorio y el número debe coincidir exactamente con el input `MagicNumber`.
- Para migraciones de EAs existentes, `short_strategy_label` se toma del `CustomComment` contrastado en MT5, retirando únicamente su sufijo histórico `_MN<legacy_magic>`. No se deriva del nombre canónico ni se normaliza o trunca silenciosamente.
- El nombre del archivo operativo es exactamente `comment_identity`; no es una tercera variante del nombre.
- Si la evidencia técnica compartida tiene labels históricos distintos, queda `WITHHELD_LEGACY_LABEL_CONFLICT` hasta que el operador decida cuál conservar; nunca se genera un alias opaco.
- No incluir cuenta, perfil, lote, riesgo, fecha, estado de salud ni fase F1–F7: son datos de despliegue o estado, no identidad de estrategia.

### 5.2 Longitud y ejemplos

La herramienta de propuesta calculará siempre:

```text
comment_length = len(comment_identity)
remaining_chars = mt5_comment_max_chars - comment_length
```

Toda fila con `comment_length > 30` queda retenida. El nombre largo seguirá visible en StratOS, SQX, Forja y en el manifiesto; el comment está diseñado para ser una etiqueta de trazabilidad de terminal, no para contener la taxonomía completa.

## 6. Artefactos que se crearán en la fase futura

### 6.1 Política versionada

`config/magic_identity_policy.yaml` contendrá únicamente reglas, sin valores operativos de cuentas:

- gramática del comment;
- máximo de caracteres;
- rango reservado;
- tratamiento de `0`;
- definición de cambio material;
- versión de contrato;
- reglas de asignación multi-cuenta y de retirada.

### 6.2 Registro operacional no versionado

`runtime/operational/magic_identity_registry.jsonl` será append-only y cada evento se sellará con SHA-256. Campos mínimos:

```json
{
  "event_type": "ASSIGNED|MIGRATION_PLANNED|MIGRATION_OBSERVED|RETIRED|CONFLICT",
  "event_at_utc": "...",
  "strategy_key": "...",
  "canonical_strategy_name": "...",
  "short_strategy_label": "...",
  "comment_identity": "...",
  "magic_number": 42,
  "legacy_magic_numbers": [260727],
  "evidence": {"sqx_sha256": "...", "mq5_sha256": "..."},
  "accounts": ["JJTI", "BEPB"],
  "operator_confirmation_ref": "...",
  "payload_sha256": "..."
}
```

Los artefactos de propuesta y cada resultado de escaneo se almacenarán junto al registro, con manifiesto y hashes. Las rutas locales o credenciales no se incluirán en documentos versionados.

### 6.3 Herramientas previstas

| Herramienta | Modo | Efecto |
| --- | --- | --- |
| `plan_magic_identity_migration.py` | Sólo lectura / `--dry-run` | Lee inventario sellado, propone magic, comment y alias; no escribe MT5. |
| `validate_magic_identity.py` | Sólo lectura | Valida rango, unicidad, gramática, longitud, hashes y compatibilidad de asignación. |
| `record_magic_identity_registry.py` | `--apply` local | Añade un evento append-only al registro y al stack operacional; nunca contacta MT5. |
| `scan_magic_identity_post_migration.py` | SSH/MT5 read-only | Reescanea el gráfico después de que el operador aplique un cambio. |
| `export_sqx_mt5_identity.py` | Integración futura | Exige una asignación válida antes de exportar/entregar un EA candidato. |

## 7. Flujo de implantación por fases

### Fase A — Inventario y propuesta (sin mutar)

1. Leer exclusivamente los manifiestos F7, `external_ea_inventory` y pares SQX/MQL5 ya confirmados.
2. Consolidar por `strategy_key`, no por nombre de archivo.
3. Identificar despliegues compartidos JJTI/BEPB como una sola estrategia con dos observaciones.
4. Calcular una propuesta de magic corto y `comment_identity` para cada estrategia resuelta.
5. Emitir CSV humano y JSON sellado con: estrategia larga, etiqueta corta, nuevo magic, magic anterior, cuentas, comentario actual/propuesto, longitudes, hash, estado y motivo de retención.
6. Bloquear filas ambiguas, colisiones actuales, fuentes incompletas o labels que no quepan.

**Salida:** lista de revisión. Ningún EA cambia.

### Fase B — Aprobación de la tabla

El operador revisa el listado y aprueba explícitamente cada lote. Una aprobación debe referenciar el hash del artefacto de propuesta y no una tabla copiada manualmente. Las filas se pueden aceptar, editar de forma explícita, aplazar o rechazar.

**Salida:** evento `ASSIGNED`/`MIGRATION_PLANNED` por estrategia aprobada.

### Fase C — Migración física dirigida por el operador

El operador cambia los magics y comments de los EAs existentes conforme al lote aprobado. La herramienta no abre, cierra, configura ni modifica terminales reales.

Cada migración se ejecuta de forma atómica a nivel de EA/gráfico: verificación pre, cambio por el operador, recarga, verificación post. Si falla una verificación, el estado queda `MIGRATION_UNVERIFIED`; no se infiere éxito a partir del nombre visible.

### Fase D — Reconciliación post-migración

1. Ejecutar el scanner read-only en JJTI/BEPB.
2. Exigir coincidencia exacta de cuenta, gráfico, `.ex5`/hash, magic, comment, símbolo y timeframe.
3. Escribir `MIGRATION_OBSERVED` y enlazar la observación nueva con el `bot_id` F7 existente sólo si no hay ambigüedad.
4. Informar separadamente: migrados, pendientes, ausentes, colisionados y con hash cambiado.
5. No reasignar trades históricos huérfanos por el mero hecho de que ahora haya un nuevo magic.

### Fase E — Prevención para estrategia nueva

El flujo de Forja/SQX → MQL5 solicitará una asignación del registro antes de preparar una entrega. El export recibido deberá contener:

- input `MagicNumber` igual al valor registrado;
- input `CustomComment` igual a `comment_identity`;
- manifest que incluye `strategy_key`, hashes, symbol/timeframe y policy version;
- validación de longitud antes de compilar/adjuntar;
- rechazo si el usuario intenta reutilizar un magic retirado o reservado.

La Incubadora seguirá conservando su contrato de cuenta demo, permiso por gráfico, sizing y riesgo; la identidad compacta no sustituye ningún gate de estrategia, baseline o riesgo.

## 8. Integración específica por sistema

### StratOS operacional

- `external_ea_inventory` añade observaciones; no se reescribe la fila histórica.
- F7 conserva `magic_number` y enlaza la nueva identidad tras la reconciliación exacta.
- Los filtros seguirán usando `account_id` + `magic_number`; el comment es evidencia auxiliar, no clave primaria.
- La UI podrá presentar `comment_identity` como etiqueta corta y el nombre canónico como detalle/tooltip, marcando migraciones pendientes de confirmar.

### MT5 / MQL5

- El EA expone ambos inputs: `MagicNumber` y `CustomComment`.
- El propio EA o un validador de compilación comprobará que el sufijo `_MN<MagicNumber>` coincide; una desigualdad aborta la preparación del despliegue.
- El cambio de magic no se ejecutará mientras existan posiciones u órdenes identificadas por el magic anterior sin una decisión explícita documentada.
- Los reportes de deals deben conservar comment y magic para que el exportador canónico pueda asociarlos directamente, sin heurística.

### SQX y Forja

- SQX conserva nombres completos de investigación, versiones y artefactos; no se fuerza a que su nombre de archivo sea el comment MT5.
- Forja consulta el registro compartido al crear un candidato de despliegue y no asigna números por índice local, fecha ni nombre del proyecto.
- Un SQX reconstruido o una nueva versión material recibe un nuevo `strategy_key` y magic tras pasar el flujo correspondiente; nunca hereda el de una estrategia sólo por compartir activo o patrón.

## 9. Casos límite obligatorios

| Caso | Tratamiento |
| --- | --- |
| Mismo EA en JJTI y BEPB | Un magic global, dos `deployment_identity`; permitido. |
| Mismo magic, hashes distintos, en una cuenta | Conflicto bloqueante; no migrar ni asociar. |
| Dos estrategias con igual nombre corto | Exigir etiquetas distintas antes de asignar. |
| Comment propuesto >30 | `REQUIRES_LABEL_APPROVAL`; no truncado automático. |
| Posición abierta bajo magic antiguo | Migración diferida; no se cambia por el plan. |
| SQX/MQL5 sin identidad cerrada | `WITHHELD`; no recibe magic nuevo. |
| Nueva compilación idéntica | Nueva observación de hash; conserva magic sólo con evidencia de equivalencia. |
| Cambio material de señal/gestión | Nuevo `strategy_key` y nuevo magic. |
| Magic histórico ausente en HTML | Sigue huérfano, incluso tras migración. |
| Magic retirado | Permanece reservado y no se reutiliza. |

## 10. Pruebas y criterios de aceptación

### Unitarias

- Asignación secuencial sin reutilización, incluso ante entradas retiradas.
- Unicidad por estrategia y validación de coexistencia multi-cuenta.
- Parser estricto de `comment_identity` y coincidencia del sufijo con magic.
- Rechazo de longitud superior al límite configurado.
- Rechazo de `magic=0`, negativos, texto o valores fuera de rango.
- Detección de colisión por cuenta/magic y por label.
- Inmutabilidad: un nuevo evento no altera una asignación u observación anterior.

### Integración

- Propuesta reproducible a partir del mismo inventario sellado y misma política.
- Importación idempotente: repetir `ASSIGNED` con el mismo payload no crea duplicados.
- Scanner post-migración identifica correctamente un EA con nuevo magic/comment y conserva la observación previa.
- F7 enlaza sólo con identidad exacta y no reatacha HTML huérfanos.
- Exportador/validador de EA rechaza `MagicNumber` y comment discordantes antes de compilar o adjuntar.

### Aceptación operativa

- El listado humano contiene todas las filas resueltas, sus cuentas y sus longitudes.
- Ninguna fila aprobada tiene colisión o comment mayor de 30.
- Cada cambio físico tiene pre/post scan sellado y confirmación del operador.
- JJTI/BEPB no reciben instrucciones de trading ni mutaciones desde StratOS.
- Las nuevas estrategias pueden obtener una identidad antes del primer Tester/demo, sin modificar la taxonomía SQX existente.

## 11. Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Un magic nuevo deja posiciones antiguas sin gestión | Bloqueo con posiciones/órdenes abiertas y migración manual dirigida. |
| El comment se trunca en MT5 | Validación previa de longitud y lectura posterior desde gráfico. |
| Se confunde una revisión de EA con la misma estrategia | `strategy_key` y hashes; revisión humana si no hay equivalencia cerrada. |
| Dos cuentas deliberadamente repiten estrategia | El modelo usa cuenta + magic para despliegue y permite magic global compartido. |
| Se pierde trazabilidad histórica | Eventos append-only `legacy_magic → magic_number`; nunca UPDATE de evidencia histórica. |
| Forja asigna un magic local divergente | Asignador único y validación de export obligatorio. |
| Se introduce un cambio durante una operación real | Ninguna acción MT5 automática; ejecución sólo por operador y con verificación posterior. |

## 12. Próxima acción cuando se retome

Iniciar exclusivamente la **Fase A** con un dry-run sobre los 40 registros F7 resueltos. El primer entregable será un listado de propuesta sellado, no un cambio de configuración. Requerirá aprobación del operador antes de registrar asignaciones y una autorización separada antes de cualquier modificación en MT5.
