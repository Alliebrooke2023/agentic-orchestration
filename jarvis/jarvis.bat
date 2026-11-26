@echo off
rem C:\swarm\jarvis\jarvis.bat  -- double-click
cd /d "%~dp0"
:menu
set "c="
echo.
echo ===== JARVIS // HAND LINK =====
echo  1  Install   (download hand-tracking libs, ~38 MB, once)
echo  2  Run       (opens browser, allow camera)
echo  3  Run tests
echo  4  Quit
set /p c=Pick 1-4: 
if "%c%"=="1" python jarvis.py --fetch & goto menu
if "%c%"=="2" python jarvis.py & goto menu
if "%c%"=="3" python -m unittest discover -s tests & goto menu
if "%c%"=="4" exit /b
goto menu
