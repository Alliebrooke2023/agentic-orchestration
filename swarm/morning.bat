@echo off
rem C:\swarm\morning.bat  -- run by the SwarmMorning scheduled task
cd /d "%~dp0"
python -m swarm "health report"
