param([string]$Drive = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
$backup = Join-Path $Drive 'config.before-controller-test.txt'
if (!(Test-Path -LiteralPath $backup)) { throw "Backup missing: $backup" }
Copy-Item -LiteralPath $backup -Destination (Join-Path $Drive 'config.txt')
if ((Get-FileHash -LiteralPath $backup).Hash -ne (Get-FileHash -LiteralPath (Join-Path $Drive 'config.txt')).Hash) {
    throw 'Restored config failed read-back verification.'
}
Write-Output 'Original PiTrex boot menu restored. Diagnostic images and backup were retained.'
foreach ($pi in 1,2) {
    $loaderBackup = Join-Path $Drive "piZero$pi/loader.before-joytest.pit"
    $loaderTarget = Join-Path $Drive "piZero$pi/loader.pit"
    if (Test-Path -LiteralPath $loaderBackup) {
        Copy-Item -LiteralPath $loaderBackup -Destination $loaderTarget
        if ((Get-FileHash -LiteralPath $loaderBackup).Hash -ne (Get-FileHash -LiteralPath $loaderTarget).Hash) {
            throw "Loader read-back failed: $loaderTarget"
        }
        Write-Output "Original Pi Zero $pi menu entries restored."
    }
}
