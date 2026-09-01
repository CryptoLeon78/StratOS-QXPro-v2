# G12 — Perfil operativo MetaQuotes-Demo

Este flujo adjunta exclusivamente los EAs `READY` del manifest G12 a un perfil
aislado de MetaQuotes-Demo. No modifica terminales Darwinex, VPS ni perfiles
existentes. El conector es de sólo lectura: no crea ni envía órdenes.

## Flujo repetible

Ejecutar desde la raíz de StratOS-QXPro-v2. El terminal objetivo debe ser el
MetaQuotes-Demo de la ruta indicada; los nombres de símbolo se validan contra
el terminal antes de escribir el perfil.

```powershell
$data_root = 'C:\Users\Ivan SQX\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075'
.\mt5-connector\.venv\Scripts\python.exe scripts\attach_g12_demo_eas.py `
  --manifest runtime\g12\survivors-manifest.json `
  --terminal-exe 'C:\Program Files\MetaTrader 5\terminal64.exe' `
  --terminal-data-root $data_root `
  --symbol-map config\g12_mt5_demo_symbol_map.json `
  --report runtime\g12\mt5-attachment.json `
  --allow-withheld --verify-live-terminal --apply --resume

.\.venv\Scripts\python.exe scripts\install_g12_mt5_indicators.py `
  --manifest runtime\g12\survivors-manifest.json `
  --terminal-data-root $data_root `
  --indicator-source-root 'C:\BOTS\Versiones\SQX_144_Full2\custom_indicators\MetaTrader5\Indicators' `
  --report runtime\g12\mt5-indicators-install.json --apply --resume

.\scripts\compile_g12_mt5_indicators.ps1 `
  -install_report .\runtime\g12\mt5-indicators-install.json `
  -terminal_data_root $data_root

.\scripts\launch_g12_demo_profile.ps1 -restart
.\scripts\start_g12_connector.ps1 -restart
```

`--allow-withheld` es deliberado: el manifest contiene cinco candidatos
retenidos y el automatismo sólo adjunta los 11 `READY`. Si el perfil existe,
`--resume` sólo acepta ficheros idénticos; no sobrescribe gráficos distintos.

## Evidencia requerida

1. `logs\YYYYMMDD.log` de MT5 contiene 11 líneas `loaded successfully` y
   ninguna `initializing ... failed` posterior al arranque.
2. `Common\Files\stratos_g12_*.jsonl` contiene 11 outboxes con eventos de
   estado emitidos por `OnInit`.
3. El log del conector muestra 200 para `ea_state`, `positions`, `equity` y
   `heartbeat`.
4. La tabla `ea_state` contiene 11 filas para la cuenta demo. Un mercado
   cerrado puede dejar posiciones en cero; eso no invalida el despliegue.

## Recuperación del lector de outbox

Si se corrige una versión del conector después de un rechazo permanente, no se
alteran los JSONL. Con el conector detenido, se pueden reponer sólo sus marcas
locales de deduplicación:

```powershell
.\.venv\Scripts\python.exe scripts\requeue_g12_reporter_events.py `
  --buffer runtime\g12\connector-buffer.sqlite `
  --report runtime\g12\reporter-requeue.json --apply
```

El core vuelve a verificar el sello y el estado de EA es un UPSERT, por lo que
esta recuperación no crea operaciones ni modifica los ficheros de MT5.
