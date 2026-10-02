@echo off
set "HELPER=%~dp0TilesSurvive-F11.ps1"
set "PWSH=%ProgramFiles%\PowerShell\7\pwsh.exe"

if not exist "%PWSH%" set "PWSH=powershell.exe"

powershell.exe -NoLogo -NoProfile -WindowStyle Hidden -Command ^
  "Start-Process -FilePath '%PWSH%' -Verb RunAs -WindowStyle Hidden -ArgumentList '-NoLogo -NoProfile -ExecutionPolicy Bypass -File ""%HELPER%""'"
