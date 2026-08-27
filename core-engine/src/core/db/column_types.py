"""Tipos Numeric reutilizables entre modulos (evita literales de precision
sueltos y repetidos). PARTE 8: Decimal para dinero, float para ratios salvo
que la propia firma de formula fije Decimal (r_multiple, max_drawdown_pct)."""

from sqlalchemy import Numeric

Money = Numeric(14, 2)  # importes en EUR: profit, balance, equity, comision, swap, retiros
Price = Numeric(18, 5)  # precios de entrada/salida/SL/TP (FX hasta cripto)
Volume = Numeric(10, 2)  # tamano de lote
FxRateValue = Numeric(12, 6)  # tipo de cambio
RMultiple = Numeric(8, 4)  # r_multiple(): PARTE 8 fija la firma como Decimal, no float
DrawdownPct = Numeric(6, 3)  # max_drawdown_pct(): PARTE 8 fija la firma como Decimal
TickSize = Numeric(12, 8)  # G10: rango real medido, 1e-05 (FX) a 0.1 (indices/oro)
TickValue = Numeric(14, 6)  # G10: point_value * tick_size, magnitud similar a Price
PointValue = Numeric(18, 6)  # G10: rango real medido, 1.0 a ~115.000 (pares FX menores)
