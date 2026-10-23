param([string]$Drive = 'H:\')
$ErrorActionPreference = 'Stop'
# Menu installation only. Never enable automatic diagnostic boot.
py (Join-Path $PSScriptRoot 'install_menu.py') --drive $Drive
if ($LASTEXITCODE -ne 0) { throw 'Menu installation failed; inspect the reported reason.' }
