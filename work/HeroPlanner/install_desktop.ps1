# Install a real Desktop shortcut to this repository's current published build.
# Existing standalone Desktop copies are retained in a recoverable backup.
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$plannerTarget = Join-Path $repoRoot 'outputs\hero-tool\publish\Tiles-Survive-Hero-Planner.exe'
if (-not (Test-Path -LiteralPath $plannerTarget -PathType Leaf)) { throw 'Publish the planner before installing the shortcut.' }
$desktopPath = [Environment]::GetFolderPath('Desktop')
$oldPlanner = Join-Path $desktopPath 'Tiles-Survive-Hero-Planner.exe'
foreach ($process in (Get-Process | Where-Object { $_.Path -eq $oldPlanner -or $_.Path -eq $plannerTarget })) {
    if (-not $process.CloseMainWindow() -or -not $process.WaitForExit(10000)) { throw 'Planner is still open. Close it before installing.' }
}
if (Test-Path -LiteralPath $oldPlanner) {
    $backupPath = Join-Path $desktopPath 'Tiles-Tools-Launcher-Backup'
    New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
    $backupFile = Join-Path $backupPath ('Tiles-Survive-Hero-Planner-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.exe')
    Move-Item -LiteralPath $oldPlanner -Destination $backupFile
    Write-Output "Previous Desktop executable preserved: $backupFile"
}
$shortcutPath = Join-Path $desktopPath 'Tiles Survive Hero Planner.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $plannerTarget
$shortcut.WorkingDirectory = Split-Path $plannerTarget
$shortcut.IconLocation = "$plannerTarget,0"
$shortcut.Description = 'Tiles Survive Hero Planner - current Desktop toolkit build'
$shortcut.Save()
$check = $shell.CreateShortcut($shortcutPath)
if ($check.TargetPath -ne $plannerTarget) { throw 'Shortcut verification failed.' }
Write-Output "Desktop shortcut: $shortcutPath -> $($check.TargetPath)"
$launchedPlanner = Start-Process -FilePath $plannerTarget -WorkingDirectory (Split-Path $plannerTarget) -WindowStyle Normal -PassThru
$launchedPlanner.WaitForInputIdle(15000) | Out-Null
Write-Output "Planner restarted: PID $($launchedPlanner.Id)"
