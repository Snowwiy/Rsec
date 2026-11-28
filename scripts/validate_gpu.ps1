param(
  [Parameter(Mandatory=$true)][string]$GpuUuid,
  [Parameter(Mandatory=$true)][string]$OutputDirectory,
  [string]$PythonExe = $env:RSEC_CUDA_PYTHON
)
$ErrorActionPreference = 'Stop'
if (!$PythonExe) { $PythonExe = "$PSScriptRoot/../.rsec-local/windows-cuda-venv/Scripts/python.exe" }
if (!(Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
  throw 'Select a dedicated Windows CUDA Python with -PythonExe or use validate_gpu.sh in WSL2.'
}
& $PythonExe -m rsec.thermal --uuid $GpuUuid --output $OutputDirectory
if ($LASTEXITCODE -ne 0) { throw "Validación CUDA terminó con código $LASTEXITCODE" }
