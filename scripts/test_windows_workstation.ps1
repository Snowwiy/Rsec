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
$blocked = $false
try { & "$PSScriptRoot/checkout_local.ps1" -Destination $fixture } catch { $blocked = $true }
if (!$blocked -or !(Test-Path -LiteralPath $file)) { throw 'Occupied directory guard failed' }

# Exercise the real transition checkout under an isolated destination.
$checkout = Join-Path $fixture 'project checkout'
& "$PSScriptRoot/checkout_local.ps1" -Destination $checkout
$current = & git -C $checkout branch --show-current
if ($LASTEXITCODE -ne 0 -or $current -ne 'dev') { throw 'Expected integration branch on first checkout' }
$marker = Join-Path $checkout 'local-uncommitted.txt'
Set-Content -LiteralPath $marker -Value 'preserve this change'
$blocked = $false
try { & "$PSScriptRoot/checkout_local.ps1" -Destination $checkout -Branch feat/rsec-physical-validation-v0.3.0 } catch { $blocked = $true }
$current = & git -C $checkout branch --show-current
if (!$blocked -or $current -ne 'dev' -or (Get-Content -LiteralPath $marker) -ne 'preserve this change') { throw 'Dirty checkout guard failed' }
