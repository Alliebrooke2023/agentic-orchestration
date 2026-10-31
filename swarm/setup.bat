@echo off
rem C:\swarm\setup.bat  -- double-click or run in PowerShell: .\setup.bat
cd /d "%~dp0"
:menu
echo.
echo ===== SWARM (cortex) =====
echo  1  Install  (Ollama + Python + small models)
echo  2  Run swarm (interactive)
echo  3  Health check (ollama + sunshine)
echo  4  Run tests
echo  5  Build a stack  (asks for a name)
echo  6  Morning report now
echo  7  Schedule daily 8am report
echo  8  Quit
set /p c=Pick 1-8: 
if "%c%"=="1" powershell -ExecutionPolicy Bypass -File "%~dp0install.ps1" & goto menu
if "%c%"=="2" python -m swarm & goto menu
if "%c%"=="3" python -m swarm "ollama status" & python -m swarm "sunshine status" & goto menu
if "%c%"=="4" python -m unittest discover tests & goto menu
if "%c%"=="5" set /p n=Stack name: & python -m swarm "build stack %n%" & goto menu
if "%c%"=="6" python -m swarm "health report" & goto menu
if "%c%"=="7" powershell -ExecutionPolicy Bypass -File "%~dp0schedule.ps1" & goto menu
if "%c%"=="8" exit /b
goto menu
