> **Estado POST-migración de identidad compacta** (ASSUMPTIONS G13-18/G13-20). Los magics y los
> `CustomComment` de este documento son los **vigentes** en el terminal JJTI tras el lote MN
> aprobado, no la observación previa. La observación anterior a la migración se conserva inmutable
> en `runtime/operational/external_inventory/jjti_magic_manifest.json`; no reescribas
> este fichero con datos históricos ni al revés (ver `docs/historico/AUDITORIA_2026-09-02.md` H3).

JJTI:

ESTRATEGIA 1: EURUSD M15 (Venta)
Identificadores: EURUSDM15S_3.76.81_MN301
MagicNumber: 301
Configuración de Entrada/Salida:
- ATRPeriod: 11
Gestión de Capital (Money Management):
- UseMoneyManagement: true
- mmRiskedMoney: 200.0
- InitialCapital: 100000.0
--------------------------------------------------

ESTRATEGIA 2: XAUUSD H1 (Compra)
Identificadores: XAUH1D1L__3.12.88_MN12
MagicNumber: 12
Configuración de Indicadores:
- Schaff Cycle: 100, 101, 126
- Bollinger Bands: 54
Gestión de Capital (Money Management):
- UseMoneyManagement: true
- mmRiskedMoney: 200.0
- InitialCapital: 100000.0
--------------------------------------------------

ESTRATEGIA 3: EURJPY M15 (Compra)
Identificadores: EURJPYM15L_1.29.59_MN9
MagicNumber: 9
Configuración de Indicadores:
- QQERSI: 44
- QQEsF: 11
- ADX: 40
- SmallestRange: 63
Gestión de Capital (Money Management):
- UseMoneyManagement: true
- mmRiskedMoney: 200.0
--------------------------------------------------

ESTRATEGIA 4: EURGBP H1 (Compra/Venta)
Identificadores: EURGBPH1LS_1.12.29_MN10726
MagicNumber: 10726
Configuración de Salida:
- ExitAfterBars: 24
Gestión de Capital (Money Management):
- UseMoneyManagement: true
- mmRiskedMoney: 200.0
- InitialCapital: 100000.0
--------------------------------------------------

ESTRATEGIA 5: EURGBP H1 (Compra/Venta)
Identificadores: EURGBPH1LS_2.17.28_MN50726
MagicNumber: 50726
Configuración de Coeficientes:
- VWAPBllBndVWPrd: 146
- ProfitTargetCoef: 1.71
- TrailingStopCoef: 1.28
- TrailingStopCoef (Alternativo): 0.43
Gestión de Capital (Money Management):
- UseMoneyManagement: true
- mmRiskedMoney: 1000.0
- mmLotsIfNoMM: 1.0
--------------------------------------------------

ESTRATEGIA 6: NASDAQ NQH1 (Compra/Venta)
Identificadores: NQH1LS_0.80730_MN90727
MagicNumber: 90727
Configuración de Indicadores/Coeficientes:
- SuperTrendATRPeriod: 500
- TrailingStopCoef: 2.0
Gestión de Capital (Money Management):
- UseMoneyManagement: true
- mmRiskedMoney: 200.0
- mmLotsIfNoMM: 0.5
--------------------------------------------------

ESTRATEGIA 7: NASDAQ NQH1 (Compra)
Identificadores: NQH1L_7.13.185_MN120726
MagicNumber: 120726
Configuración de Indicadores:
- Ichimoku Kijun Sen Cross: 180, 34, 52
- CCIPeriod: 50
Gestión de Capital (Money Management):
- Money Management - Fixed size (mmLots): 0.2
--------------------------------------------------

ESTRATEGIA 8: EURGBP H1 (Compra)
Identificadores: EURGBPH1L_5.8.133_MN150729
MagicNumber: 150729
Configuración de Indicadores:
- Desviación estándar ascendente: 30
- Media móvil exponencial EMA: 40
- ExitAfterBars: 50
Coeficientes y Gestión:
- ProfitTargetCoef: 4.1
- StopLossCoef: 3.6
- mmRiskedMoney: 200.0
--------------------------------------------------

ESTRATEGIA 9: EURGBP H1 (Compra)
Identificadores: EURGBPH1L_5.3.185_MN150728
MagicNumber: 150728
Configuración de Indicadores/Coeficientes:
- ATRPeriod1: 50
- ATRPeriod2: 14
- ExitAfterBars1: 44
- ProfitTargetCoef1: 5.0
- StopLossCoef1: 4.4
Gestión de Capital (Money Management):
- UseMoneyManagement: true
- mmRiskedMoney: 200.0
- mmLotsIfNoMM: 0.1
--------------------------------------------------

ESTRATEGIA 10: EURGBP H1 (Compra)
Identificadores: EURGBPH1L_1.7.127_MN150727
MagicNumber: 150727
Configuración de Indicadores/Coeficientes:
- ExitAfterBars1: 26
- ProfitTargetCoef1: 4.7
- StopLossCoef1: 4.7
Gestión de Capital (Money Management):
- UseMoneyManagement: true
- mmRiskedMoney: 200.0
- mmLotsIfNoMM: 0.1
--------------------------------------------------

ESTRATEGIA 11: EURGBP H1 (Compra)
Identificadores: EURGBPH1L_5.12.175_MN30
MagicNumber: 30
Configuración de Indicadores/Coeficientes:
- ExitAfterBars1: 40
- ProfitTargetCoef1: 3.7
- StopLossCoef1: 4.9
Gestión de Capital (Money Management):
- UseMoneyManagement: true
- mmRiskedMoney: 200.0
- mmLotsIfNoMM: 0.1
--------------------------------------------------

ESTRATEGIA 12: EURGBP H1 (Compra)
Identificadores: EURGBPH1L_4.8.196_MN33
MagicNumber: 33
Configuración de Indicadores/Coeficientes:
- ExitAfterBars1: 30
- ProfitTargetCoef1: 4.6
- StopLossCoef1: 3.4
Gestión de Capital (Money Management):
- UseMoneyManagement: true
- mmRiskedMoney: 200.0
- mmLotsIfNoMM: 0.2
--------------------------------------------------

ESTRATEGIA 13: SP500 H4 (Compra)
Identificadores: SPH4L_5.2.27_MN200738
MagicNumber: 200738
Configuración de Indicadores/Coeficientes:
- BollingerBandsPrd1: 20
- ExitAfterBars1: 46
- ProfitTargetCoef1: 6.9
- TrailingStop1: 90.0
Gestión de Capital (Money Management):
- UseMoneyManagement: true
- mmRiskedMoney: 200.0
- mmLotsIfNoMM: 0.3
--------------------------------------------------

ESTRATEGIA 14: SP500 H4 (Compra)
Identificadores: SPH4L_5.3.20_MN19
MagicNumber: 19
Configuración de Indicadores/Coeficientes:
- BollingerBandsPrd1: 20
- ExitAfterBars1: 46
- StopLossCoef1: 8.5
- TrailingStop1: 100.0
Gestión de Capital (Money Management):
- UseMoneyManagement: true
- mmRiskedMoney: 200.0
- mmLotsIfNoMM: 0.3
--------------------------------------------------

ESTRATEGIA 15: USDJPY H1 (Compra)
Identificadores: USDJPYH1L_5.15.110_MN8
MagicNumber: 8
Configuración de Indicadores/Salidas:
- ExitAfterBars1: 46
Gestión de Capital (Money Management):
- UseMoneyManagement: true
- mmRiskedMoney: 200.0
- mmLotsIfNoMM: 1.0
--------------------------------------------------

ESTRATEGIA 16: USDJPY H1 (Compra)
Identificadores: USDJPYH1L_3.16.113_MN3
MagicNumber: 3
Configuración de Indicadores/Coeficientes:
- BollingerBandsPrd1: 20
- IchimokuTnkKjnCrsBshTnkPrd1: 155
- IchimokuTnkKjnCrsBshKjnPrd1: 26
- IchimokuTnkKjnCrsBshSnkPrd1: 52
- TrailingStop1: 80.0
Gestión de Capital (Money Management):
- UseMoneyManagement: true
- mmRiskedMoney: 200.0
- mmLotsIfNoMM: 1.0
--------------------------------------------------

ESTRATEGIA 17: USDJPY H1 (Compra)
Identificadores: USDJPYH1L_2.22.171_MN13
MagicNumber: 13
Configuración de Indicadores:
- LinearRegressionPrd1: 40
- ExitAfterBars1: 42
- TrailingStop1: 60.0
Gestión de Capital (Money Management):
- UseMoneyManagement: true
- mmRiskedMoney: 200.0
- mmLotsIfNoMM: 1.0
--------------------------------------------------

ESTRATEGIA 18: DAX GDAXI H4 (Compra)
Identificadores: DAXH4L_1.10.37_4.6.33_MN260728
MagicNumber: 260728
Configuración de Indicadores/Coeficientes:
- KeltnerChannelPrd1: 20
- MomPeriod1: 28
- ExitAfterBars1: 4
- ProfitTargetCoef1: 7.6
- StopLossCoef1: 5.7
- TrailingStopCoef1: 1.7
Gestión de Capital (Money Management):
- UseMoneyManagement: true
- mmRiskedMoney: 200.0
- mmLotsIfNoMM: 0.1
--------------------------------------------------

ESTRATEGIA 19: XAUUSD M30 (Compra)
Identificadores: XAUM30L_1.10.37_4.6.33_MN260726
MagicNumber: 260726
Configuración de Indicadores/Coeficientes:
- KeltnerChannelPrd1: 20
- MomPeriod1: 28
- ExitAfterBars1: 4
- ProfitTargetCoef1: 7.6
- StopLossCoef1: 5.7
- TrailingStopCoef1: 1.7
Gestión de Capital (Money Management):
- UseMoneyManagement: true
- mmRiskedMoney: 400.0
- mmLotsIfNoMM: 0.1
--------------------------------------------------

ESTRATEGIA 20: XAUUSD M30 (Compra)
Identificadores: XAUM30L_1.19.27_MN260727
MagicNumber: 260727
Configuración de Indicadores/Coeficientes:
- PriceEntryMult1: 0.6
- ProfitTargetCoef1: 3.3
- StopLossCoef1: 7.2
Gestión de Capital (Money Management):
- UseMoneyManagement: true
- mmRiskedMoney: 400.0
- mmLotsIfNoMM: 0.1
--------------------------------------------------

ESTRATEGIA 21: DAX DAX40 H1
Identificadores: DAX40H1_5.27.28_MN10
MagicNumber: 10
Configuración de Indicadores/Coeficientes:
- ProfitTargetCoef1: 5.4
- StopLossCoef1: 8.1
Gestión de Capital (Money Management):
- UseMoneyManagement: true
- mmRiskedMoney: 200.0
- mmLotsIfNoMM: 0.1
--------------------------------------------------

ESTRATEGIA 22: DAX DAX40 M30
Identificadores: DAX40M30_2.13.18_MN10826
MagicNumber: 10826
Configuración de Indicadores/Coeficientes:
- ZScorePeriod1: 150
- ZScorePeriod2: 90
- PriceEntryMult1: 1.7
- ProfitTargetCoef1: 3.6
- StopLossCoef1: 10.0
Gestión de Capital (Money Management):
- UseMoneyManagement: true
- mmRiskedMoney: 200.0
- mmLotsIfNoMM: 0.1
--------------------------------------------------

ESTRATEGIA 23: DAX DAX40 M30
Identificadores: DAX40M30_4.15.28_MN17
MagicNumber: 17
Configuración de Indicadores/Coeficientes:
- StopLossCoef1: 5.8
Gestión de Capital (Money Management):
- UseMoneyManagement: true
- mmRiskedMoney: 200.0
- mmLotsIfNoMM: 0.1
--------------------------------------------------

ESTRATEGIA 24: USDJPY H1 (Compra)
Identificadores: USDJPYH1L_3.40.187_MN25
MagicNumber: 25
Configuración de Indicadores:
- LinearRegressionPrd1: 30
Gestión de Capital (Money Management):
- smm: Money Management - Fixed Amount
- UseMoneyManagement: true
- mmRiskedMoney: 200.0
- mmDecimals: 2
- mmLotsIfNoMM: 1.0
- mmMaxLots: 5.0
- mmMultiplier: 1.0
- mmStep: 0.01
- InitialCapital: 100000.0