> **Estado POST-migración de identidad compacta** (ASSUMPTIONS G13-18/G13-20). Los magics y los
> `CustomComment` de este documento son los **vigentes** en el terminal BEPB tras el lote MN
> aprobado, no la observación previa. La observación anterior a la migración se conserva inmutable
> en `runtime/operational/external_inventory/bepb_magic_manifest.json`; no reescribas
> este fichero con datos históricos ni al revés (ver `docs/historico/AUDITORIA_2026-09-02.md` H3).

- BEPB: 
Estrategia 1: XAU1H1BUYSTOP_0620_Strategy 3.10.66 (XAUUSD,H1)
CustomComment: XAU1H1BUYSTP_3.10.66_MN28 | MagicNumber: 28 | ProfitTargetCoef1: 8.8 | StopLossCoef1: 2.2 | TrailingStopCoef1: 1.1 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.01 | mmMaxLots: 5.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 2: SP500H1D1BUYSTPeof_R615_7.13.55 (SP500,H1)
CustomComment: SP500H1D1BUYSTP_7.13.55_MN9519 | MagicNumber: 9519 | PriceEntryMult1: 2.48 | ProfitTargetCoef1: 7.49 | StopLossCoef1: 2.31 | TrailingStopCoef1: 1.02 | BBWidthRatioPeriod1: 33 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.01 | mmMaxLots: 5.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 3: XAUH1BUYSTOPeof_1.8.81 (XAUUSD,H1)
CustomComment: XAUH1BUYSTOPeof_1.8.81_MN1 | MagicNumber: 1 | ProfitTargetCoef1: 4.2 | StopLossCoef1: 8.9 | TrailingStopCoef1: 1.2 | DonchianChannelsPrd1: 107 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.01 | mmMaxLots: 5.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 4: EURJPYM15BUYSTP_1.29.59 (EURJPY,M15)
CustomComment: EUJPYM15BUYSTP_1.29.59_MN54856 | MagicNumber: 54856 | QQERSIPeriod1: 44 | QQEsF1: 11 | ADXPeriod1: 40 | PriceEntryMult1: 1.6 | ProfitTargetCoef1: 3.1 | StopLossCoef1: 4.1 | SmallestRangePeriod1: 63 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.01 | mmMaxLots: 5.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 5: EURGBP_H1_LS_volumen_Strategy 2.4.18 (EURGBP,H1)
CustomComment: EURGPH1LSvol_2.4.18_MN20 | MagicNumber: 20 | VWAPATRBandsVWAPPrd1: 90 | ExitAfterBars1: 24 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.1 | mmMaxLots: 5.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 6: EURGBP_H1_LS_estadistico_Strategy 5.5.34 (EURGBP,H1)
CustomComment: EURGBPH1LSest_5.5.34_MN14 | MagicNumber: 14 | ExitAfterBars1: 24 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.1 | mmMaxLots: 5.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 7: EUH1SELLMKTeof_7.30.121 (EURUSD,H1)
CustomComment: EUUSH1Seof_7.30.121_MN5 | MagicNumber: 5 | ZScorePeriod1: 95 | ProfitTargetCoef1: 3.3 | StopLossCoef1: 3.5 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.01 | mmMaxLots: 5.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 8: AUDNZDH4BUY_edge_1.16.34 (AUDNZD,H4)
CustomComment: AUDNZDH4L_1.16.34_MN26 | MagicNumber: 26 | CSSAMrkRgmHLSumPrd1: 7 | CSSAMarketRgmHLPrd1: 164 | CSSAMarketRgmAvgPrd1: 9 | CSSAMrkRgmPrcRnkPrd1: 60 | ExitAfterBars1: 12 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.1 | mmMaxLots: 2.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 9: EURUSD_SELL_STOP_H4_LC_3.8.141 (EURUSD,H4)
CustomComment: EURUSDH4S_city_3.8.141_MN37 | MagicNumber: 37 | Period1: 14 | PriceEntryMult1: 1.4 | ExitAfterBars1: 26 | ProfitTargetCoef1: 2.7 | StopLossCoef1: 1.8 | TrailingStop1: 80.0 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.01 | mmMaxLots: 5.0 | mmMultiplier: 1.0

Estrategia 10: EURGBP_H1_LS_estadistico_Strategy 1.12.29 (EURGBP,H1)
CustomComment: EUGBH1LS_1.12.29_MN10726 | MagicNumber: 10726 | ExitAfterBars1: 24 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.1 | mmMaxLots: 5.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 11: EURGBP_H1_LS_volumen_Strategy 7.4.22 (EURGBP,H1)
CustomComment: EUGBH1LS_7.4.22_MN7 | MagicNumber: 7 | VWAPVWAPPeriod1: 170 | ExitAfterBars1: 24 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.1 | mmMaxLots: 5.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 12: NASDAQH1_L_City_7.13.185 (NDX,H1)
CustomComment: NQH1LCity_7.13.185_MN38 | MagicNumber: 38 | IchimokuKjnSenCrsBshTnkPrd1: 180 | IchimokuKjnSenCrsBshKjnPrd1: 34 | IchimokuKjnSenCrsBshSnkPrd1: 52 | CCIPeriod1: 50 | mmLots: 0.2 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 13: DAXH4Lstat_1.10.37Improved4.6.33 (GDAXI,H4)
CustomComment: DAXH4L_1.10.37_4_6_33_MN260728 | MagicNumber: 260728 | KeltnerChannelPrd1: 20 | MomPeriod1: 28 | ExitAfterBars1: 4 | ProfitTargetCoef1: 7.6 | StopLossCoef1: 5.7 | TrailingStopCoef1: 1.7 | UseMoneyManagement: true | mmRiskedMoney: 400.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.1 | mmMaxLots: 10.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 14: XAUm30Lstat_1.10.37Improved4.6.33 (XAUUSD,M30)
CustomComment: XAUM30L 1.10.37_4.6.33_MN260726 | MagicNumber: 260726 | KeltnerChannelPrd1: 20 | MomPeriod1: 28 | ExitAfterBars1: 4 | ProfitTargetCoef1: 7.6 | StopLossCoef1: 5.7 | TrailingStopCoef1: 1.7 | UseMoneyManagement: true | mmRiskedMoney: 400.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.1 | mmMaxLots: 10.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 15: XAUm30Lstat_1.19.27 (XAUUSD,M30)
CustomComment: XAUM30Lstat_1.19.27_MN260727 | MagicNumber: 260727 | PriceEntryMult1: 0.6 | ProfitTargetCoef1: 3.3 | StopLossCoef1: 7.2 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.1 | mmMaxLots: 10.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 16: SP500H4Lstat_Strategy 1.11.33(1) - Improved 4.10.27(1) (SP500,H1)
CustomComment: SPH4L_1.11.33_4.10.27_MN36 | MagicNumber: 36 | TrailingStop1: 60.0 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.5 | mmMaxLots: 10.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 17: SP500H4Lstat_Strategy 1.20.31 - Improved 3.6.22(1) (SP500,H1)
CustomComment: SPH4L_1.20.31_3.6.22_MN18 | MagicNumber: 18 | KeltnerChannelPrd1: 20 | ProfitTargetCoef1: 5.6 | TrailingStop1: 60.0 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.5 | mmMaxLots: 10.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 18: SP500H4Lstat_Strategy 1.25.19(3) - Improved 3.1.31(1) (SP500,H1)
CustomComment: SPH4L_1.25.19_3.1.31_MN15 | MagicNumber: 15 | ZScorePeriod1: 166 | ProfitTargetCoef1: 7.0 | TrailingStop1: 90.0 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.5 | mmMaxLots: 10.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 19: SP500H4Lstat_Strategy 1.25.33(4) - Improved 3.1.19(1) (SP500,H1)
CustomComment: SPH4_1.25.33_3.1.19_MN34 | MagicNumber: 34 | KeltnerChannelPrd1: 198 | ZScorePeriod1: 123 | ZScorePeriod2: 41 | StopLossCoef1: 8.0 | TrailingStop1: 90.0 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.5 | mmMaxLots: 10.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 20: SP500H4Lstat_Strategy 1.26.22 - Improved 3.5.18(1) (SP500,H1)
CustomComment: SPH4L_1.26.22_3.5.18_MN32 | MagicNumber: 32 | KeltnerChannelPrd1: 20 | ProfitTargetCoef1: 3.7 | TrailingStop1: 60.0 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.5 | mmMaxLots: 10.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 21: SP500H4Lstat_Strategy 1.26.31 - Improved 4.2.29(1) (SP500,H1)
CustomComment: SPH4L_1.26.31_4.2.29_MN24 | MagicNumber: 24 | StopLossCoef1: 7.4 | TrailingStop1: 90.0 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.5 | mmMaxLots: 10.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 22: SP500H4Lstat_Strategy 1.26.33 - Improved 1.6.23(1) (SP500,H1)
CustomComment: SPH4L_1.26.33_1.6.23_MN4 | MagicNumber: 4 | ATRTrlStpATRPrd1: 157 | ATRTrlStpATRSmtPrd1: 188 | TrailingStop1: 90.0 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.5 | mmMaxLots: 10.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 23: SP500H4Lstat_Strategy 5.2.27 - ImprovedStrategy 5.1.22(1) (SP500,H1)
CustomComment: SPH4L_5.2.27_5.1.22_MN31 | MagicNumber: 31 | BollingerBandsPrd1: 20 | ATRLowerPeriod1: 50 | ProfitTargetCoef1: 6.9 | TrailingStop1: 90.0 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.5 | mmMaxLots: 10.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 24: SP500H4Lstat_Strategy 5.23.18(1) - Improved 2.13.25(1)(1) (SP500,H1)
CustomComment: SPH4L_5.23.18_2.13.25_MN29 | MagicNumber: 29 | ExitAfterBars1: 12 | TrailingStop1: 80.0 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.5 | mmMaxLots: 10.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 25: GBPJPYH1L_cityKC+STDEV_3.2.163 (GBPJPY,H1)
CustomComment: GBPJPYH1L_3.2.163_MN23 | MagicNumber: 23 | StdDevCrossUpPeriod1: 30 | KCBarOpenserPeriod1: 20 | ExitAfterBars1: 26 | ProfitTargetCoef1: 4.2 | StopLossCoef1: 4.5 | TrailingStopCoef1: 1.6 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.2 | mmMaxLots: 5.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 26: GBPJPYH1L_city_ICHI+LINREG_3.18.156 (GBPJPY,H1)
CustomComment: GBPJPYH1L_3.18.156_MN16 | MagicNumber: 16 | LinRegBarOpensPrd1: 50 | IchimokuSnkSpnCrsBshTnkPrd1: 9 | IchimokuSnkSpnCrsBshKjnPrd1: 26 | IchimokuSnkSpnCrsBshSnkPrd1: 52 | ExitAfterBars1: 10 | ProfitTargetCoef1: 5.0 | StopLossCoef1: 1.5 | TrailingStop1: 60.0 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.2 | mmMaxLots: 5.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 27: DAX40H1stat_5.29.24 (GDAXI,H1)
CustomComment: DAXH1_5.29.24_MN10829 | MagicNumber: 10829 | StopLossCoef1: 5.4 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.1 | mmMaxLots: 5.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 28: DAX40M30stat_4.20.23 (GDAXI,M30)
CustomComment: DAXM30_4.20.23_MN10826 | MagicNumber: 10826 | StopLossCoef1: 5.8 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.1 | mmMaxLots: 5.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 29: DAX40H1stat_5.27.28 (GDAXI,H1)
CustomComment: DAXH1_5.27.28_MN10827 | MagicNumber: 10827 | ProfitTargetCoef1: 5.4 | StopLossCoef1: 8.1 | UseMoneyManagement: true | mmRiskedMoney: 400.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.4 | mmMaxLots: 5.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 30: OROLONGLIMITSPPSTRH1D1 4.7.77 (XAUUSD,H1)
CustomComment: XAUH1D1L_4.7.77_MN40 | MagicNumber: 40 | PriceEntryMult1: 0.5 | ProfitTargetCoef1: 8.5 | StopLoss1: 1075.0 | TrailingStopCoef1: 1.2 | EMAPeriod1: 14 | SmallestRangePeriod1: 50 | mmLots: 0.1 | mmMultiplier: 1.0

Estrategia 31: SP500LONGD1 REVERSION SL 2.86.54 (SP500,Daily)
CustomComment: SPD1L_REV_2.86.54_MN11 | MagicNumber: 11 | ExitAfterBars1: 2 | StopLossCoef1: 2.0 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.1 | mmMaxLots: 5.0 | mmMultiplier: 1.0 | mmStep: 0.01 | InitialCapital: 100000.0

Estrategia 32: SPA35LONGD1 REVERSION SL 1.31.56 (SPA35,Daily)
CustomComment: SPA35D1L_REV_1.31.56_MN27 | MagicNumber: 27 | ExitAfterBars1: 3 | StopLossCoef1: 3.0 | UseMoneyManagement: true | mmRiskedMoney: 200.0 | mmDecimals: 2 | mmLotsIfNoMM: 0.1 | mmMaxLots: 5.0 | mmMultiplier: 1.0 | mmStep: 1.0 | InitialCapital: 100000.0