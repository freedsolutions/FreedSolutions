$ErrorActionPreference = 'Stop'

$LogDir = (Resolve-Path (Join-Path $PSScriptRoot (Join-Path '..' 'logs'))).Path
$Threshold = [TimeSpan]::FromHours(36)

$Newest = Get-ChildItem -Path $LogDir -Filter 'nightly_sweep_*.log' -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

$Alarm = $null
if (-not $Newest) {
    $Alarm = "No Post-Email Sweep logs found in $LogDir."
} else {
    $Age = (Get-Date) - $Newest.LastWriteTime
    if ($Age -gt $Threshold) {
        $Alarm = ("Post-Email Sweep log is stale.`n`nNewest: {0}`nAge:    {1:F1}h`nThreshold: {2}h`n`nCheck that last night's run completed and that the scheduled task is healthy." -f $Newest.Name, $Age.TotalHours, $Threshold.TotalHours)
    }
}

if ($Alarm) {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show($Alarm, 'Post-Email Sweep: Freshness Alarm', 'OK', 'Warning') | Out-Null
    exit 1
}

exit 0
