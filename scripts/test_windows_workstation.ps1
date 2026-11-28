$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
foreach ($script in Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.ps1') {
  $tokens = $null
  $errors = $null
  [System.Management.Automation.Language.Parser]::ParseFile($script.FullName,[ref]$tokens,[ref]$errors) | Out-Null
  if ($errors.Count) { throw ($errors | Out-String) }
}
$before = $env:HF_HOME
& "$PSScriptRoot/workstation.ps1" setup
if ($before -cne $env:HF_HOME) { throw 'Project environment leaked into parent' }
$fixture = Join-Path $Root ('.rsec-local/test fixtures/' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $fixture -Force | Out-Null
$file = Join-Path $fixture 'baseline test.gguf'
[IO.File]::WriteAllBytes($file,[byte[]](71,71,85,70,3,0,0,0))
$run = & "$PSScriptRoot/workstation.ps1" inventory -Library $fixture
$result = Get-Content -Raw -LiteralPath (Join-Path $run 'inventory.json') | ConvertFrom-Json
if ($result.models.Count -ne 1 -or $result.models[0].path -ne $file -or !$result.models[0].header_recognized) { throw 'Unexpected Windows inventory' }
function nvidia-smi {
  $global:LASTEXITCODE = 0
  'GPU-fixture, NVIDIA GeForce RTX 3060, 10000'
}
function Test-OneVisibleRuntime {
  $global:LASTEXITCODE = 0
  if ($args[0] -ne '--list-devices') { throw 'Unexpected model load' }
  'Available devices:'
}
$listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,0)
$listener.Start()
$testPort = $listener.LocalEndpoint.Port
$listener.Stop()
$blocked = $false
try {
  & "$PSScriptRoot/workstation.ps1" inference -Model $file -GpuUuid 'GPU-fixture' -Profile gaming -LlamaServerExe 'Test-OneVisibleRuntime' -Port $testPort
} catch { $blocked = $_.Exception.Message -like '*cannot see every selected CUDA GPU*' }
if (!$blocked) { throw 'The native CUDA visibility check must reject a missing GPU before loading weights' }
Remove-Item Function:nvidia-smi,Function:Test-OneVisibleRuntime
$blocked = $false
try { & "$PSScriptRoot/checkout_local.ps1" -Destination $fixture } catch { $blocked = $true }
if (!$blocked -or !(Test-Path -LiteralPath $file)) { throw 'Occupied directory guard failed' }

# Exercise the real transition checkout under an isolated destination.
$checkout = Join-Path $fixture 'project checkout'
New-Item -ItemType Directory -Path $checkout | Out-Null
& "$PSScriptRoot/checkout_local.ps1" -Destination $checkout
$current = & git -C $checkout branch --show-current
if ($LASTEXITCODE -ne 0 -or $current -ne 'dev') { throw 'Expected integration branch on first checkout' }
$marker = Join-Path $checkout 'local-uncommitted.txt'
Set-Content -LiteralPath $marker -Value 'preserve this change'
$blocked = $false
try { & "$PSScriptRoot/checkout_local.ps1" -Destination $checkout -Branch feat/rsec-physical-validation-v0.3.0 } catch { $blocked = $true }
$current = & git -C $checkout branch --show-current
if (!$blocked -or $current -ne 'dev' -or (Get-Content -LiteralPath $marker) -ne 'preserve this change') { throw 'Dirty checkout guard failed' }
