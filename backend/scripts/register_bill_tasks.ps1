param(
    [string]$TaskPrefix = "SSKLaw"
)

$backendDir = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $backendDir "venv\Scripts\python.exe"
$managePath = Join-Path $backendDir "manage.py"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Python virtual environment was not found: $pythonPath"
}

$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

function New-ManagementAction([string]$Arguments) {
    New-ScheduledTaskAction `
        -Execute $pythonPath `
        -Argument "`"$managePath`" $Arguments" `
        -WorkingDirectory $backendDir
}

$morningTriggers = @()
foreach ($time in @("09:00", "09:10", "09:20", "09:30", "09:40", "09:50", "10:00")) {
    $morningTriggers += New-ScheduledTaskTrigger -Daily -At $time
}

Register-ScheduledTask `
    -TaskName "$TaskPrefix-BillSync-Morning" `
    -Action (New-ManagementAction "sync_bills --trigger scheduled") `
    -Trigger $morningTriggers `
    -Settings $settings `
    -Description "Poll National Assembly bills every 10 minutes from 09:00 through 10:00." `
    -Force

Register-ScheduledTask `
    -TaskName "$TaskPrefix-BillSync-Catchup" `
    -Action (New-ManagementAction "sync_bills --trigger catchup --catch-up-only") `
    -Trigger (New-ScheduledTaskTrigger -Daily -At "13:00") `
    -Settings $settings `
    -Description "Run the 13:00 catch-up only when the morning sync created no bills." `
    -Force

$workerTrigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 1) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

Register-ScheduledTask `
    -TaskName "$TaskPrefix-BillWorker" `
    -Action (New-ManagementAction "process_bill_tasks --limit 1") `
    -Trigger $workerTrigger `
    -Settings $settings `
    -Description "Process one due bill enrichment task at a time." `
    -Force

Write-Host "Registered $TaskPrefix bill synchronization and processing tasks."

