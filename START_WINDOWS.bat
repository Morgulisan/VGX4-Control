@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto run
python --version >nul 2>nul
if errorlevel 1 goto missing
python -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
:run
".venv\Scripts\python.exe" -c "import serial, perlin_noise" >nul 2>nul
if errorlevel 1 goto repair
".venv\Scripts\python.exe" app.py %*
if errorlevel 1 goto failed
exit /b 0
:repair
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
goto run
:missing
echo Bitte Python 3.10 oder neuer installieren und zu PATH hinzufuegen.
pause
exit /b 1
:failed
echo Start fehlgeschlagen. Bitte die Fehlermeldung oben pruefen.
pause
exit /b 1
