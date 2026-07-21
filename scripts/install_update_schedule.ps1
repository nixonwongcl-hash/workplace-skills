param(
    [string]$RepoRoot = "$env:USERPROFILE\Workplace-Skills",
    [string]$PythonExe = "",
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$taskName = "Workplace Skills Auto Update"
$logonTaskName = "$taskName At Logon"

if ($Uninstall) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $logonTaskName -Confirm:$false -ErrorAction SilentlyContinue
    & "$env:SystemRoot\System32\schtasks.exe" /Delete /TN $taskName /F 2>$null | Out-Null
    & "$env:SystemRoot\System32\schtasks.exe" /Delete /TN $logonTaskName /F 2>$null | Out-Null
    Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "WorkplaceSkillsAutoUpdate" -ErrorAction SilentlyContinue
    Write-Output "Removed scheduled task: $taskName"
    exit 0
}

if (-not $PythonExe) {
    $python = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if (-not $python) {
        $python = Get-Command python.exe -ErrorAction Stop
    }
    $PythonExe = $python.Source
}

$updater = Join-Path $RepoRoot "scripts\update_workplace_skills.py"
if (-not (Test-Path -LiteralPath $updater)) {
    throw "Updater not found: $updater"
}

$arguments = ('"{0}" --repo-root "{1}"' -f $updater, $RepoRoot)
$action = New-ScheduledTaskAction -Execute $PythonExe -Argument $arguments
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn
$repeatTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Hours 6) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($logonTrigger, $repeatTrigger) -Settings $settings -Description "Fast-forward and validate the shared workplace skill store." -Force | Out-Null
} catch {
    Write-Warning "ScheduledTasks API was denied; falling back to user-level schtasks entries."
    $taskAction = ('"{0}" "{1}" --repo-root "{2}"' -f $PythonExe, $updater, $RepoRoot)
    & "$env:SystemRoot\System32\schtasks.exe" /Create /TN $taskName /TR $taskAction /SC HOURLY /MO 6 /F | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Could not create six-hour update task." }
    & "$env:SystemRoot\System32\schtasks.exe" /Create /TN $logonTaskName /TR $taskAction /SC ONLOGON /F 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "WorkplaceSkillsAutoUpdate" -Value $taskAction
        Write-Warning "ONLOGON task was denied; installed a per-user logon entry instead."
    }
}

Write-Output "Installed scheduled task: $taskName"
Write-Output "Python: $PythonExe"
Write-Output "Updater: $updater"
