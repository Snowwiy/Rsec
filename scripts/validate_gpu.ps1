param(
  [Parameter(Mandatory=$true)][string]$GpuUuid,
  [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
$Previous = $env:CUDA_VISIBLE_DEVICES
try {
  $env:CUDA_VISIBLE_DEVICES = $GpuUuid
  & "$PSScriptRoot/../.venv/Scripts/python.exe" -m rsec.thermal --uuid $GpuUuid --output $OutputDirectory
  if ($LASTEXITCODE -ne 0) { throw "Validación CUDA terminó con código $LASTEXITCODE" }
} finally {
  $env:CUDA_VISIBLE_DEVICES = $Previous
}
