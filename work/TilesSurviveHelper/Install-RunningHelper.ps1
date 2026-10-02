$ErrorActionPreference = 'Stop'

$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Source = Join-Path $PSScriptRoot 'bin\Release\net8.0-windows\win-x64\publish\TilesSurviveHelper.exe'
$Output = Join-Path $RepositoryRoot 'downloads\TilesSurviveHelper.exe'
$Desktop = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Tiles Survive Helper.exe'

if (-not (Test-Path -LiteralPath $Source)) {
    throw "Published helper not found at $Source"
}

Get-Process | Where-Object ProcessName -eq 'Tiles Survive Helper' | Stop-Process -Force
Start-Sleep -Milliseconds 500
Copy-Item -LiteralPath $Source -Destination $Output -Force
Copy-Item -LiteralPath $Source -Destination $Desktop -Force
Start-Process -FilePath $Desktop
