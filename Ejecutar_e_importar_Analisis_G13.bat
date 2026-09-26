@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "ROOT=%~dp0"
set "EXE=%ROOT%dist\G13_Manual_Analysis_Run.exe"

if not exist "%EXE%" (
  echo ERROR: no existe %EXE%
  pause
  exit /b 1
)

echo.
echo G13 - Tester manual y archivo completo de Analisis
echo Abre SQX_vs_MT5, ejecuta una candidata y pulsa Archivar.
echo Despues pega la ruta de evidence-manifest.json.
echo No opera JJTI/BEPB ni adjunta EAs demo.
echo.
"%EXE%" --open-panel --register
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" echo BLOQUEADO: revisa el error anterior; no se ha inventado ningun veredicto.
pause
exit /b %EXIT_CODE%
