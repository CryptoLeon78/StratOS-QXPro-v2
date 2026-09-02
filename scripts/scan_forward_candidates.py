"""Escanea las carpetas Forward de los proyectos SQX y mide cada candidata.

No escribe nada en SQX ni en la base: lee los `.sqx` con el mismo parser que usa el panel
SQX_vs_MT5 y calcula las metricas del gate de pipeline. Sirve para decidir QUE exportar a
MQL5, que es el cuello de botella real: sin `.mq5` no hay EA que adjuntar ni comparar.
"""

import json
import pathlib
import statistics
import sys

PANEL = pathlib.Path(
    r"C:\BOTS\Versiones\SQX_144_Full2\Apps_entorno_SQX\SQX_vs_MT5_Panel"
)
sys.path.insert(0, str(PANEL))

import compare_sqx_vs_mt5 as cmp  # noqa: E402
import sqx_mt5_config as cfgmod  # noqa: E402

cmp.aplicar_config(cfgmod.cargar())

BASE = pathlib.Path(r"C:\BOTS\Versiones\SQX_144_Full2\user\projects")
SALIDA = pathlib.Path(sys.argv[1])

filas = []
for sqx in sorted(BASE.glob("*/databanks/*Forward*/*.sqx")):
    fila = {
        "proyecto": sqx.parents[2].name,
        "databank": sqx.parent.name,
        "fichero": sqx.name,
        "ruta": str(sqx),
    }
    try:
        s = cmp.cargar_lado_sqx(sqx)
        trades = s["trades"]
        m = cmp.calcular_metricas(trades)
        fechas = sorted(t["close_time"] for t in trades if t.get("close_time"))
        dias = (fechas[-1] - fechas[0]).days if len(fechas) >= 2 else 0
        pnl = [t["pl"] for t in trades]
        media = statistics.mean(pnl) if pnl else 0.0
        desv = statistics.pstdev(pnl) if len(pnl) > 1 else 0.0
        pf = m["profit_factor"]
        fila.update(
            {
                "simbolo": s["simbolo_sqx"],
                "timeframe": s["timeframe"],
                "trades": len(trades),
                "dias": dias,
                "freq_semana": round(len(trades) / (dias / 7), 2) if dias >= 7 else None,
                "pf": round(pf, 3) if pf != float("inf") else None,
                "dd_pct": round(m["max_dd_pct"], 3),
                "np": round(m["net_profit"], 2),
                # Sharpe por trade: media/desviacion del PnL. No es el Sharpe anualizado del
                # gate, pero ordena por consistencia con lo que el .sqx expone.
                "sharpe_trade": round(media / desv, 3) if desv else None,
            }
        )
    except Exception as exc:  # noqa: BLE001 - se reporta, no se oculta
        fila["error"] = f"{type(exc).__name__}: {exc}"[:120]
    filas.append(fila)

SALIDA.write_text(json.dumps(filas, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(f"escaneados={len(filas)} legibles={sum(1 for f in filas if 'error' not in f)}")
