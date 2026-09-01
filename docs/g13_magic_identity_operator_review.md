# G13 — Revisión del operador: identidad compacta de magics

## Estado actual — CERRADO EN LECTURA (2026-09-01)

La Fase A se ejecutó sólo en lectura sobre los manifiestos F7 sellados de JJTI y BEPB. No se modificó MetaTrader, ningún EA, gráfico, cuenta, histórico, Forja, SQX ni el registro append-only.

Artefactos de revisión locales, no versionados:

- `runtime/operational/magic_identity/magic-identity-proposal-318e99792860.csv`
- `runtime/operational/magic_identity/magic-identity-proposal-318e99792860.json`
- `runtime/operational/magic_identity/magic-identity-label-overrides-13f60f27d1d4.json`

La regla de esta propuesta es fija: `comment_identity = <label histórico>_MN<nuevo_magic>` y `file_identity = comment_identity`. El prefijo se conserva desde el `CustomComment` ya contrastado en MT5, retirando sólo el antiguo `_MN<legacy_magic>`; no se deriva del nombre SQX canónico.

Resultado del dry-run sellado y posteriormente aprobado:

| Estado | Estrategias | Acción |
| --- | ---: | --- |
| `PROPOSED` | 40 | Aprobadas por el operador mediante el hash de propuesta y ejecutadas manualmente. |

## Historial de aprobación y ejecución del operador

### 1. Revisar y aprobar el CSV sellado — COMPLETADO

Abre el CSV y revisa las 40 filas `PROPOSED`, especialmente `short_strategy_label`, `comment_identity`, `file_identity`, `legacy_magic_numbers` y `magic_number`. `file_identity` debe coincidir exactamente con `comment_identity` en todas las filas.

El operador aprobó el lote completo con `payload_sha256=318e99792860a513e531bf5c716c52b19d4fac0d3f7594b8343ef05c8df7be7f`.

**Por qué es necesario:** registrar una asignación reserva el magic globalmente y no puede basarse en una tabla copiada o en una conversación sin el hash del artefacto exacto.

### 2. Decisión registrada: variantes por cuenta — COMPLETADO

El operador ha resuelto los dos conflictos como identidades operativas distintas, manteniendo el hash EX5 común en `technical_strategy_key`:

| Cuenta | XAUUSD M30 | EURGBP H1 |
| --- | --- | --- |
| BEPB | `XAUM30L_1.19.27a` | `EUGBH1LS_1.12.29a` |
| JJTI | `XAUM30L_1.19.27b` | `EUGBH1LS_1.12.29b` |

No queda ningún conflicto de label pendiente. El CSV revisado asigna un magic distinto a cada variante y mantiene `file_identity = comment_identity`.

## Procedimiento histórico de cambio físico

## Resultado del post-scan de perfiles persistidos (2026-09-01)

El escaneo SSH/SFTP de sólo lectura se repitió después de guardar los perfiles `Default`. La regla confirmada por el operador para este lote es que sólo cambian archivo, magic y comment; por ello hash EX5 y timeframe se heredan del manifiesto F7 sellado, mientras que cuenta, gráfico, archivo, magic, comment y símbolo se vuelven a observar desde MT5.

El informe `runtime/operational/magic_identity/post_migration_scan_report.json` completa los 40 pares aprobados cuenta+magic como `MIGRATION_OBSERVED`. Las aparentes duplicidades JJTI de los magics `19` y `30` son dos serializaciones `.chr` del mismo gráfico MT5: conservan el mismo ID interno, EA, magic, comment y símbolo, y sólo difieren en campos visuales. El escáner las colapsa en una única identidad lógica y conserva las rutas físicas como evidencia; no requieren ninguna acción del operador. Cualquier reutilización de ID con identidad distinta se retiene como `MIGRATION_UNVERIFIED`. El NQ de JJTI magic `38` queda separado como `OPERATOR_RETAINED_OUT_OF_PROPOSAL`, enlazado al manifiesto de excepción sellado. El perfil evidencia dos codificaciones efectivas permitidas para `CustomComment`: la configurada con puntos y la persistida con guiones bajos; se acepta sólo una de esas dos coincidencias exactas. Para DAX, la regla auditada conserva `DAX`/`DAX40` de F7/SQX y `GDAXI` de Darwinex MT5 sin reescribir ninguno.

### 3. Cambio físico de cada EA/gráfico — COMPLETADO MANUALMENTE

Antes de cada cambio, confirma que no existen posiciones abiertas, órdenes pendientes ni cierres parciales bajo el magic antiguo. Cambia exclusivamente `MagicNumber`, `CustomComment` y el nombre del archivo al par aprobado; los tres valores de identidad deben respetar `CustomComment = nombre_archivo = <label>_MN<MagicNumber>`. Recarga el EA por tu procedimiento normal y conserva todos los demás inputs.

**Por qué es necesario:** cambiar un magic durante una posición puede separar la gestión de la instancia que la abrió. StratOS es read-only y no puede cerrar, reconfigurar ni reiniciar los terminales por ti.

### 4. Verificación posterior read-only — COMPLETADA

Tras cada cambio, facilita o ejecuta un escaneo que incluya cuenta, gráfico, hash EX5, nombre de archivo, magic, comment, símbolo y timeframe. Sólo una coincidencia exacta generará `MIGRATION_OBSERVED`; cualquier ausencia o diferencia queda `MIGRATION_UNVERIFIED`.

**Por qué es necesario:** el nombre visible o un comment parcial no prueban que el EA correcto quedó cargado en el gráfico correcto. La observación nueva se añadirá sin borrar la evidencia anterior y el histórico HTML sin magic seguirá huérfano.
