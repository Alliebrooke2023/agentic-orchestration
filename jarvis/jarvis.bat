@echo off
rem C:\swarm\jarvis\jarvis.bat  -- double-click
cd /d "%~dp0"
rem use python if it runs (skips the Microsoft Store stub), else the py launcher
set "PY=python"
python --version >nul 2>nul || set "PY=py -3"
%PY% --version >nul 2>nul || (echo Python 3 not found. Install from python.org, tick "Add to PATH". & pause & exit /b 1)
:menu
set "c="
echo.
echo ===== JARVIS // HAND LINK =====
echo  1  Install   (download hand-tracking libs, ~38 MB, once)
echo  2  Run       (opens browser, allow camera)
echo  3  Run tests
echo  4  Quit
set /p c=Pick 1-4: 
if "%c%"=="1" %PY% jarvis.py --fetch & goto menu
if "%c%"=="2" %PY% jarvis.py & goto menu
if "%c%"=="3" %PY% -m unittest discover -s tests & goto menu
if "%c%"=="4" exit /b
goto menu
