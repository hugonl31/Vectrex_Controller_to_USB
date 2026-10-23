param(
    [ValidateSet('Flash','Recenter','Defaults','Info')][string]$Action = 'Flash',
    [ValidatePattern('^COM[0-9]+$')][string]$Port,
    [switch]$Bootloader,
    [switch]$ListPorts,
    [switch]$ValidateOnly
)
$ErrorActionPreference = 'Stop'
# Ensure Windows PowerShell's modules are found when launched from a parent
# application whose PSModulePath points at a different PowerShell installation.
$env:PSModulePath = (Join-Path $PSHOME 'Modules') + [IO.Path]::PathSeparator + $env:PSModulePath
$root = $PSScriptRoot

function Get-Ports {
    @(Get-CimInstance Win32_SerialPort | ForEach-Object {
        [pscustomobject]@{ Port=$_.DeviceID; Name=$_.Name; UsbId=$_.PNPDeviceID }
    })
}
function Is-Adapter($item) {
    $item.UsbId -match 'VID_(2341|2A03)&PID_(8037|0037|8036|0036)' -or
    $item.UsbId -match 'VID_1B4F&PID_(9205|9206)'
}
function Choose-Port {
    $all = @(Get-Ports)
    if ($Port) {
        if ($all.Port -notcontains $Port) { throw "$Port is not connected. Use -ListPorts to list ports." }
        return $Port
    }
    $matching = @($all | Where-Object { Is-Adapter $_ })
    if ($matching.Count -eq 1) { return $matching[0].Port }
    $all | Format-Table Port,Name | Out-Host
    $choice = (Read-Host 'Enter the COM port of your 5 V / 16 MHz ATmega32U4 board (for example COM6)').Trim().ToUpperInvariant()
    if ($choice -notmatch '^COM[0-9]+$' -or $all.Port -notcontains $choice) {
        throw 'No matching connected COM port selected.'
    }
    return $choice
}
function Open-Link([string]$com) {
    $link = New-Object System.IO.Ports.SerialPort $com,115200,None,8,One
    $link.ReadTimeout = 250
    $link.WriteTimeout = 1500
    $link.NewLine = "`n"
    $link.DtrEnable = $true
    $link.Open()
    return $link
}
function Request($link, [string]$command, [string]$prefix) {
    $link.WriteLine($command)
    $until = [DateTime]::UtcNow.AddSeconds(4)
    while ([DateTime]::UtcNow -lt $until) {
        try { $line = $link.ReadLine().Trim() } catch [TimeoutException] { continue }
        if ($line.StartsWith('ERR,')) { throw "Adapter rejected $command : $line" }
        if ($line.StartsWith($prefix)) { return $line }
    }
    throw "No $prefix response on $($link.PortName). Close serial monitors and check the installed firmware."
}
function Validate-Package {
    $manifestPath = Join-Path $root 'manifest.json'
    if (!(Test-Path -LiteralPath $manifestPath)) { throw 'Extract the complete ZIP first; manifest.json is missing.' }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    foreach ($file in $manifest.files) {
        $path = Join-Path $root $file.path
        if (!(Test-Path -LiteralPath $path)) { throw "Package file missing: $($file.path)" }
        if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.sha256) {
            throw "Package file changed or damaged: $($file.path). Extract a fresh copy."
        }
    }
    return $manifest
}
function Backup-Calibration($link) {
    $cal = Request $link 'GET' 'CAL,'
    $folder = Join-Path $root 'backups'
    New-Item -ItemType Directory -Path $folder -Force | Out-Null
    $file = Join-Path $folder ('calibration-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff') + '.json')
    [pscustomobject]@{utc=[DateTime]::UtcNow.ToString('o');port=$link.PortName;calibration=$cal} |
        ConvertTo-Json | Set-Content -LiteralPath $file -Encoding UTF8
    Write-Host "Previous calibration saved to $file"
    return $cal
}
function Median($values) {
    $ordered = @($values | Sort-Object)
    $n = $ordered.Count
    if ($n % 2) { return [int]$ordered[[int][Math]::Floor($n/2)] }
    return [int][Math]::Round(($ordered[$n/2-1]+$ordered[$n/2])/2.0)
}
function Touch-Reset([string]$com) {
    $touch = New-Object System.IO.Ports.SerialPort $com,1200,None,8,One
    try {
        $touch.DtrEnable = $true
        $touch.Open()
        Start-Sleep -Milliseconds 150
        $touch.DtrEnable = $false
    } finally { $touch.Dispose() }
}
function Flash-Board([string]$com) {
    $tool = Join-Path $root 'tools\avrdude.exe'
    $config = Join-Path $root 'tools\avrdude.conf'
    $firmware = Join-Path $root 'firmware\vectrex-controller.hex'
    $baseline = @(Get-Ports)
    $uploadPort = $com
    if (!$Bootloader) {
        Write-Host "Resetting $com into its Caterina bootloader..."
        Touch-Reset $com
        Write-Host 'Waiting for bootloader. If needed, press RESET twice quickly (RST to GND on Pro Micro).'
        $until = [DateTime]::UtcNow.AddSeconds(25)
        $disappeared = $false
        $uploadPort = $null
        while ([DateTime]::UtcNow -lt $until) {
            $now = @(Get-Ports)
            if ($now.Port -notcontains $com) { $disappeared = $true }
            $new = @($now | Where-Object { $baseline.Port -notcontains $_.Port })
            if ($new.Count -eq 1) { $uploadPort = $new[0].Port; break }
            if ($new.Count -gt 1) { throw 'Multiple new ports appeared. Disconnect other USB serial devices and retry.' }
            $boot = @($now | Where-Object { $_.Port -eq $com -and $_.UsbId -match 'VID_(2341|2A03)&PID_003[67]|VID_1B4F&PID_9205' })
            if ($boot.Count -eq 1 -or ($disappeared -and $now.Port -contains $com)) {
                $uploadPort = $com; break
            }
            Start-Sleep -Milliseconds 200
        }
        if (!$uploadPort) { throw 'Bootloader not found. Double-reset the board, then retry with -Port COMx -Bootloader.' }
    }
    Write-Host "Programming $uploadPort and verifying flash..."
    & $tool '-C' $config '-p' 'atmega32u4' '-c' 'avr109' '-P' $uploadPort '-b' '57600' '-D' '-U' "flash:w:${firmware}:i"
    if ($LASTEXITCODE -ne 0) { throw "AVRDUDE failed ($LASTEXITCODE). Firmware verification did not complete." }
    Write-Host 'Flash verified. Bootloader, fuses and saved EEPROM calibration were not programmed.'
    Write-Host 'Wait a few seconds for Vectrex USB Controller to reconnect.'
}

try {
    if ($ListPorts) { Get-Ports | Format-Table Port,Name,UsbId; exit 0 }
    $manifest = Validate-Package
    Write-Host "Vectrex Controller $($manifest.version) - $Action"
    if ($ValidateOnly) {
        & (Join-Path $root 'tools\avrdude.exe') '-C' (Join-Path $root 'tools\avrdude.conf') '--version' | Out-Host
        if ($LASTEXITCODE -ne 0) { throw 'Bundled AVRDUDE failed to start.' }
        Write-Host 'Package hashes and flashing tool validated. No device was changed.'
        exit 0
    }
    $com = Choose-Port
    if ($Action -eq 'Flash') { Flash-Board $com; exit 0 }
    if ($Action -eq 'Recenter') {
        Read-Host 'Release the stick and all buttons, leave it untouched, then press Enter' | Out-Null
    }
    $link = Open-Link $com
    try {
        $identity = Request $link 'INFO' 'INFO,VECTREX,1,HID,'
        Write-Host $identity
        if ($Action -eq 'Info') { Write-Host (Request $link 'GET' 'CAL,'); exit 0 }
        $before = Backup-Calibration $link
        if ($Action -eq 'Defaults') {
            Write-Host (Request $link 'STOCK' 'OK,STOCK')
            $expected = $manifest.defaults_command
        } else {
            $values = @($before.Substring(4).Split(',') | ForEach-Object { [int]$_ })
            if ($values.Count -ne 11) { throw 'Unexpected firmware calibration format.' }
            $xs = New-Object 'System.Collections.Generic.List[int]'
            $ys = New-Object 'System.Collections.Generic.List[int]'
            $link.DiscardInBuffer()
            $until = [DateTime]::UtcNow.AddSeconds(3)
            while ([DateTime]::UtcNow -lt $until) {
                try { $line = $link.ReadLine().Trim() } catch [TimeoutException] { continue }
                if ($line -match '^RAW,\d+,(\d+),(\d+),(\d+)$') {
                    if ([int]$Matches[3] -ne 0) { throw 'A button was pressed; center was not changed.' }
                    $x=[int]$Matches[1]; $y=[int]$Matches[2]
                    if ($x -gt 1023 -or $y -gt 1023) { throw 'Invalid ADC reading; center was not changed.' }
                    $xs.Add($x); $ys.Add($y)
                }
            }
            if ($xs.Count -lt 100) { throw 'Too few ADC samples; center was not changed.' }
            $xr = $xs | Measure-Object -Minimum -Maximum
            $yr = $ys | Measure-Object -Minimum -Maximum
            if ($xr.Maximum-$xr.Minimum -gt 5 -or $yr.Maximum-$yr.Minimum -gt 5) {
                throw 'Stick moved or readings varied excessively. Release it and retry.'
            }
            $values[1] = Median $xs
            $values[4] = Median $ys
            if ($values[1]-$values[6] -le $values[0] -or $values[1]+$values[6] -ge $values[2] -or
                $values[4]-$values[7] -le $values[3] -or $values[4]+$values[7] -ge $values[5]) {
                throw 'Center is outside the usable endpoint range; center was not changed.'
            }
            $expected = 'CAL,' + ($values -join ',')
            Write-Host (Request $link $expected 'OK,CAL')
        }
        $actual = Request $link 'GET' 'CAL,'
        if ($actual -ne $expected) { throw "Calibration readback mismatch: $actual" }
        Write-Host "Saved and verified: $actual"
    } finally { $link.Dispose() }
    exit 0
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
