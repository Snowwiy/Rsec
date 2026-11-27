[CmdletBinding()]
param([string]$PythonExe)

$ErrorActionPreference = 'Stop'
& "$PSScriptRoot/workstation.ps1" setup -PythonExe $PythonExe
Write-Host 'Windows core tools are installed. Use the separate WSL2 environment for CUDA.'
