$ErrorActionPreference = 'Stop'

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-File', ('"{0}"' -f $PSCommandPath)
    )
    exit
}

$captureDir = Join-Path (Split-Path -Parent $PSScriptRoot) 'captures'
New-Item -ItemType Directory -Force -Path $captureDir | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$etl = Join-Path $captureDir "tiles-map-all-$stamp.etl"
$pcap = Join-Path $captureDir "tiles-map-all-$stamp.pcapng"
$captureStarted = $false

try {
    $game = Get-Process -Name 'tspc' -ErrorAction Stop | Select-Object -First 1
    $tcpConnections = Get-NetTCPConnection -OwningProcess $game.Id -ErrorAction SilentlyContinue |
        Where-Object {
            $_.State -eq 'Established' -and
            $_.RemoteAddress -notin @('0.0.0.0', '::', '127.0.0.1', '::1')
        } |
        Select-Object RemoteAddress, RemotePort -Unique
    $udpPorts = Get-NetUDPEndpoint -OwningProcess $game.Id -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalPort -gt 0 } |
        Select-Object -ExpandProperty LocalPort -Unique

    if (-not $tcpConnections -and -not $udpPorts) {
        throw 'No live Tiles Survive network endpoints were found.'
    }

    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    pktmon stop 2>$null | Out-Null
    pktmon filter remove 2>$null | Out-Null
    $ErrorActionPreference = $previousPreference

    $index = 0
    foreach ($connection in $tcpConnections) {
        $index++
        pktmon filter add "TilesTcp$index" -i $connection.RemoteAddress -t TCP -p $connection.RemotePort | Out-Null
        Write-Host "Watching TCP $($connection.RemoteAddress):$($connection.RemotePort)"
    }
    foreach ($port in $udpPorts) {
        $index++
        pktmon filter add "TilesUdp$index" -t UDP -p $port | Out-Null
        Write-Host "Watching UDP local port $port"
    }

    Write-Host ''
    Write-Host 'Capture starts in 3 seconds.' -ForegroundColor Yellow
    Write-Host 'Jump to several FAR-APART wilderness coordinates until this window says DONE.' -ForegroundColor Yellow
    Start-Sleep -Seconds 3

    pktmon start --capture --pkt-size 0 --file-name $etl | Out-Null
    $captureStarted = $true
    Write-Host ''
    Write-Host 'CAPTURING NOW - make two or three long-distance map jumps...' -ForegroundColor Green
    Start-Sleep -Seconds 40

    pktmon stop | Out-Null
    $captureStarted = $false
    pktmon etl2pcap $etl --out $pcap | Out-Null
    Write-Host ''
    Write-Host "DONE. Capture saved to $pcap" -ForegroundColor Green
}
catch {
    Write-Host ''
    Write-Host "Capture failed: $($_.Exception.Message)" -ForegroundColor Red
}
finally {
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    if ($captureStarted) {
        pktmon stop 2>$null | Out-Null
    }
    pktmon filter remove 2>$null | Out-Null
    $ErrorActionPreference = $previousPreference
    Write-Host ''
    Read-Host 'Press Enter to close'
}
