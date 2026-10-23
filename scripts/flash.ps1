param(
    [ValidateSet('calibration', 'hid')][string]$Firmware = 'hid',
    [string]$Port
)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
Push-Location $project
try {
    if (-not $Port) {
        $devices = @(pio device list --json-output | ConvertFrom-Json | Where-Object {
            $_.hwid -match 'VID:PID=(2341|2A03):[08]037'
        })
        if ($devices.Count -ne 1) { throw 'Specify -Port COMx; expected exactly one Arduino Micro.' }
        $Port = $devices[0].port
    }
    # PlatformIO performs the 1200-baud touch and tracks the Caterina boot port.
    pio run -e $Firmware -t upload --upload-port $Port
    if ($LASTEXITCODE -ne 0) { throw "Build/upload failed ($LASTEXITCODE)." }
} finally { Pop-Location }
