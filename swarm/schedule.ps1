# C:\swarm\schedule.ps1 -- daily 8:00 health report. Remove: schtasks /Delete /TN SwarmMorning /F
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = (Get-Command python).Source
schtasks /Create /F /SC DAILY /ST 08:00 /TN SwarmMorning /TR "cmd /c cd /d `"$dir`" && `"$py`" -m swarm `"health report`""
Write-Host "Scheduled. Reports land in $dir\outbox\health_YYYYMMDD.md"
