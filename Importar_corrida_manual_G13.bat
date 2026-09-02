@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "ROOT=%~dp0"
set "PYTHON=%ROOT%.venv\Scripts\python.exe"
set "SCRIPT=%ROOT%scripts\import_manual_sqx_mt5_run.py"
set "INVENTORY=%ROOT%runtime\operational\analysis-inventory.json"
set "OUTPUT=%ROOT%runtime\operational\backtests_manual"
set "TERMINAL_ID=Darwinex MetaTrader 5"

if not exist "%PYTHON%" (
  echo ERROR: No se encuentra el Python del entorno operacional:
  echo %PYTHON%
  pause
  exit /b 1
)

echo.
echo Importador manual G13 - SOLO sella evidencia ya existente.
echo No abre MT5, no relanza backtests y no opera cuentas.
echo.
if not "%~3"=="" (
  set "SQX=%~1"
  set "MQ5=%~2"
  set "REPORT=%~3"
  set "INI=%~4"
  set "CSV=%~5"
  set "COMPARISON=%~6"
) else (
  set /p "SQX=Ruta completa del archivo .sqx: "
  set /p "MQ5=Ruta completa del archivo .mq5: "
  set /p "REPORT=Ruta completa del informe MT5 .htm/.html: "
  set /p "INI=Ruta del .ini del Tester (opcional, Enter para omitir): "
  set /p "CSV=Ruta del CSV MT5 de trades (opcional, Enter para omitir): "
  set /p "COMPARISON=Ruta del informe TXT de SQX_vs_MT5 con VEREDICTO (opcional, Enter para omitir): "
)

if "%SQX%"=="" goto :missing
if "%MQ5%"=="" goto :missing
if "%REPORT%"=="" goto :missing

set "ARGS=--inventory "%INVENTORY%" --sqx "%SQX%" --mq5 "%MQ5%" --mt5-report "%REPORT%" --output-root "%OUTPUT%" --terminal-id "%TERMINAL_ID%""
if not "%INI%"=="" set "ARGS=%ARGS% --tester-ini "%INI%""
if not "%CSV%"=="" set "ARGS=%ARGS% --mt5-trades-csv "%CSV%""
if not "%COMPARISON%"=="" set "ARGS=%ARGS% --comparison-report "%COMPARISON%""

"%PYTHON%" "%SCRIPT%" %ARGS%
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%EXIT_CODE%"=="0" echo IMPORTACION NO COMPLETADA. Revisa el mensaje anterior.
if "%EXIT_CODE%"=="0" echo IMPORTACION COMPLETADA. Si fue REPORT_ONLY, falta el informe comparativo para registrar veredicto.
pause
exit /b %EXIT_CODE%

:missing
echo ERROR: SQX, MQ5 e informe MT5 son obligatorios.
pause
exit /b 1
