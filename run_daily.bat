@echo off
setlocal

cd /d "%~dp0"

if not exist "%~dp0logs" mkdir "%~dp0logs"

set LOGFILE=%~dp0logs\run_daily.log

echo. >> "%LOGFILE%"
echo ============================================================ >> "%LOGFILE%"
echo Inicio: %date% %time% >> "%LOGFILE%"
echo ============================================================ >> "%LOGFILE%"

call "%~dp0.venvSSIData\Scripts\activate.bat"

python "%~dp0run_daily.py" >> "%LOGFILE%" 2>&1

echo Fim: %date% %time%  (codigo: %errorlevel%) >> "%LOGFILE%"

endlocal
