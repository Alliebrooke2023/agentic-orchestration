# C:\swarm\schedule.ps1 -- daily 8:00 health report. Remove: Unregister-ScheduledTask SwarmMorning -Confirm:$false
$dir = $PSScriptRoot
$act = New-ScheduledTaskAction -Execute "$dir\morning.bat" -WorkingDirectory $dir
$trg = New-ScheduledTaskTrigger -Daily -At 8:00am
$set = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName SwarmMorning -Action $act -Trigger $trg -Settings $set -Force | Out-Null
Write-Host "Scheduled. Reports land in $dir\outbox\health_YYYYMMDD.md"
