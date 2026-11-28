[CmdletBinding()]
param(
  [Parameter(Mandatory)][ValidateSet('diagnose','setup','inventory','review','inference','probe','goose','gpu')][string]$Action,
  [string]$Library, [string]$Model, [string[]]$GpuUuid, [int]$Port,
  [string]$PythonExe, [string]$LlamaServerExe = 'llama-server', [string]$GooseExe = 'goose',
  [ValidateSet('ollama','openai')][string]$GooseBackend = 'ollama',
  [ValidatePattern('^[a-z][a-z0-9-]{0,31}$')][string]$GooseProfile = 'default',
  [switch]$GooseSmoke,
  [switch]$DisableReasoning,
  [ValidateSet('default','gaming','agent','inference-dual')][string]$Profile = 'default',
  [double[]]$TensorSplit,
  [ValidateSet('layer','row')][string]$SplitMode = 'layer',
  [ValidateRange(0,1)][int]$MainGpu = 0,
  [ValidateRange(1,64)][int]$Threads = 2,
  [ValidateRange(128,32768)][int]$Context = 2048,
  [string]$ReviewBundle = 'data/processed/pilot-review-1'
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
$Local = Join-Path $Root '.rsec-local'
$Python = Join-Path $Local 'windows-venv/Scripts/python.exe'
$Run = Join-Path $Local ('runs/' + [guid]::NewGuid())
$Saved = @{}
function Set-ScopedEnv($Name,$Value) {
  if (!$Saved.ContainsKey($Name)) { $Saved[$Name] = [Environment]::GetEnvironmentVariable($Name,'Process') }
  if ($null -eq $Value) { Remove-Item -LiteralPath "Env:$Name" -ErrorAction SilentlyContinue }
  else { [Environment]::SetEnvironmentVariable($Name,$Value,'Process') }
}
function Run-Checked($Program,[string[]]$Arguments) {
  & $Program @Arguments
  if ($LASTEXITCODE -ne 0) { throw "$Program exited with $LASTEXITCODE" }
}
function Require-Port($Number) {
  $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,$Number)
  try { $listener.Start() } finally { $listener.Stop() }
}
Push-Location -LiteralPath $Root
try {
  New-Item -ItemType Directory -Path $Run -Force | Out-Null
  foreach ($item in @{
    HF_HOME='cache/huggingface'; HF_HUB_CACHE='cache/huggingface/hub'; HF_DATASETS_CACHE='cache/datasets';
    TORCH_HOME='cache/torch'; PIP_CACHE_DIR='cache/pip'; TEMP='tmp'; TMP='tmp'; TMPDIR='tmp'
  }.GetEnumerator()) {
    $dir = Join-Path $Local $item.Value
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    Set-ScopedEnv $item.Key $dir
  }
  if ($Port -eq 0) {
    $Port = switch ($Action) {
      'goose' { if ($GooseBackend -eq 'ollama') { 11434 } else { 8081 } }
      'review' { 8765 }
      default { 8081 }
    }
  }
  if ($Port -lt 1 -or $Port -gt 65535) { throw 'Invalid port' }
  if ($Action -eq 'diagnose') {
    $report = [ordered]@{os=[Environment]::OSVersion.VersionString; powershell=$PSVersionTable.PSVersion.ToString();
      driveFree=(Get-PSDrive -Name (Get-Item -LiteralPath $Root).PSDrive.Name).Free;
      tools=@{}; listeners=@(Get-NetTCPConnection -State Listen | Select-Object LocalPort,OwningProcess);
      ram=(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory}
    foreach ($tool in 'git','py','python','nvidia-smi','wsl','ollama','llama-server','llama-cli','goose','openssl') {
      $cmd = Get-Command $tool -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
      if ($cmd) { $report.tools[$tool]=$cmd.Source }
    }
    foreach ($tool in 'git','python','ollama','llama-server','goose','openssl') {
      if ($report.tools[$tool]) {
        if ($tool -eq 'openssl') { & $tool version *> (Join-Path $Run "$tool.txt") }
        else { & $tool --version *> (Join-Path $Run "$tool.txt") }
      }
    }
    if ($report.tools['py']) { py -0p *> (Join-Path $Run 'py.txt') }
    if ($report.tools['wsl']) { wsl --status *> (Join-Path $Run 'wsl-status.txt'); wsl -l -v *> (Join-Path $Run 'wsl-distros.txt') }
    if ($report.tools['nvidia-smi']) { nvidia-smi *> (Join-Path $Run 'nvidia.txt') }
    $report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $Run 'windows.json')
    Write-Output $Run
    return
  }
  if ($Action -eq 'setup') {
    if (!(Test-Path -LiteralPath $Python)) {
      if (Test-Path (Join-Path $Local 'windows-venv')) { throw 'Inspect incomplete existing environment before setup' }
      $venvArgs = @('-m','venv',(Join-Path $Local 'windows-venv'))
      if ($PythonExe) { Run-Checked $PythonExe $venvArgs }
      else { Run-Checked 'py' (@('-3.12') + $venvArgs) }
    }
    Run-Checked $Python @('-m','pip','install','-r','requirements-dev.txt','-e','.')
    Run-Checked $Python @('-m','pip','check')
    return
  }
  if ($Action -eq 'gpu') {
    if ($GpuUuid.Count -ne 1) { throw 'Select one NVIDIA UUID' }
    if (!$PythonExe) { $PythonExe = $env:RSEC_CUDA_PYTHON }
    & "$PSScriptRoot/validate_gpu.ps1" -GpuUuid $GpuUuid[0] -OutputDirectory (Join-Path $Run 'gpu') -PythonExe $PythonExe
    return
  }
  if (!(Test-Path -LiteralPath $Python)) { throw 'Run workstation.ps1 setup first' }
  Set-ScopedEnv 'HF_HUB_OFFLINE' '1'
  switch ($Action) {
    'inventory' {
      if (!$Library) { $Library = Join-Path (Split-Path $Root -Parent) 'AI Local' }
      Run-Checked $Python @('-m','rsec.local','inventory',$Library,'--output',(Join-Path $Run 'inventory.json'))
      Write-Output $Run
    }
    'review' {
      Require-Port $Port
      if (!(Test-Path -LiteralPath $ReviewBundle)) {
        Run-Checked $Python @('-m','rsec.cli','data','curate','--input','data/pilot/candidates.jsonl','--version','pilot-review-1','--output',$ReviewBundle)
      }
      Run-Checked $Python @('-m','rsec.cli','data','review-ui',$ReviewBundle,'--preaudit','audits/phase02b/candidate_preaudit.jsonl','--port',$Port)
    }
    'inference' {
      if (!$Model -or !(Test-Path -LiteralPath $Model -PathType Leaf) -or [IO.Path]::GetExtension($Model) -ine '.gguf') { throw 'Select a local GGUF file' }
      $modelFile = Get-Item -LiteralPath $Model
      if ($Profile -in 'gaming','agent' -and $GpuUuid.Count -ne 1) { throw 'Select one GPU UUID for this profile' }
      if ($Profile -eq 'inference-dual' -and $GpuUuid.Count -ne 2) { throw 'Select two GPU UUIDs for distributed inference' }
      if ($GpuUuid.Count -gt 2 -or ($GpuUuid.Count -eq 2 -and $Profile -ne 'inference-dual')) { throw 'Use the explicit dual inference profile for two devices' }
      if ($Profile -eq 'gaming' -and ($Threads -gt 2 -or $Context -gt 2048 -or $modelFile.Length -gt 4GB)) { throw 'Gaming profile requires at most 2 threads, 2048 context and a GGUF up to 4 GiB' }
      Require-Port $Port
      $layers=0
      $deviceArgs = @('--device','none')
      Set-ScopedEnv 'CUDA_VISIBLE_DEVICES' '-1'
      if ($GpuUuid) {
        $rows = & nvidia-smi --query-gpu=uuid,name,memory.free --format=csv,noheader,nounits
        if ($LASTEXITCODE -ne 0) { throw 'NVIDIA device inventory unavailable' }
        $devices = @{}
        foreach ($row in $rows) {
          $columns = $row -split ',\s*', 3
          if ($columns.Count -eq 3) { $devices[$columns[0]] = $columns[1..2] }
        }
        if (@($GpuUuid | Sort-Object -Unique).Count -ne $GpuUuid.Count -or
            @($GpuUuid | Where-Object { !$devices.ContainsKey($_) }).Count) { throw 'Select distinct, present NVIDIA UUIDs' }
        Set-ScopedEnv 'CUDA_VISIBLE_DEVICES' ($GpuUuid -join ',')
        $deviceArgs = @('--device','CUDA0','--split-mode','none','--main-gpu','0')
        if ($Profile -eq 'gaming') {
          $device = $devices[$GpuUuid[0]]
          if ($device[0] -cne 'NVIDIA GeForce RTX 3060' -or
              [double]$device[1] * 1MB -lt $modelFile.Length + 768MB) { throw 'Gaming profile requires the RTX 3060 and free VRAM for weights and buffers' }
        }
        if ($Profile -eq 'inference-dual') {
          if ($TensorSplit.Count -ne 2 -or @($TensorSplit | Where-Object { ![double]::IsFinite($_) -or $_ -le 0 }).Count) { throw 'Supply two positive tensor split weights' }
          $total = $TensorSplit[0] + $TensorSplit[1]
          if (![double]::IsFinite($total)) { throw 'Tensor split total must be finite' }
          for ($index=0; $index -lt 2; $index++) {
            $device = $devices[$GpuUuid[$index]]
            $weights = $modelFile.Length * ($TensorSplit[$index] / $total)
            if ([double]$device[1] * 1MB -lt $weights + 1GB) { throw 'Distributed inference requires more free VRAM for weights and buffers' }
          }
          $split = ($TensorSplit | ForEach-Object { $_.ToString([Globalization.CultureInfo]::InvariantCulture) }) -join ','
          $deviceArgs = @('--device','CUDA0,CUDA1','--split-mode',$SplitMode,'--tensor-split',$split)
          if ($SplitMode -eq 'row') { $deviceArgs += @('--main-gpu',$MainGpu) }
        }
        $layers=99
        $llamaInventory = & $LlamaServerExe --list-devices 2>&1
        if ($LASTEXITCODE -ne 0) { throw 'Could not enumerate CUDA devices in llama.cpp' }
        $llamaDevices = @{}
        foreach ($line in $llamaInventory) {
          if ("$line" -match '^\s*CUDA(\d+):\s*(.*?)\s*\(') { $llamaDevices[[int]$Matches[1]] = $Matches[2] }
        }
        if ($llamaDevices.Count -ne $GpuUuid.Count) { throw 'llama.cpp cannot see every selected CUDA GPU in this runtime' }
        for ($index=0; $index -lt $GpuUuid.Count; $index++) {
          if ($llamaDevices[$index] -cne $devices[$GpuUuid[$index]][0]) { throw 'llama.cpp CUDA order differs from the selected devices' }
        }
      }
      $serverArgs = @('-m',$modelFile.FullName,'--alias','local-baseline','--host','127.0.0.1','--port',$Port,'-c',$Context,'-ngl',$layers,'-t',$Threads,'-tb',$Threads,'--offline')
      if ($DisableReasoning) { $serverArgs += @('--reasoning-budget','0') }
      Run-Checked $LlamaServerExe ($serverArgs + $deviceArgs)
    }
    'probe' {
      if (!$Model) { $Model='local-baseline' }
      Run-Checked $Python @('-m','rsec.local','probe','--port',$Port,'--model',$Model,'--output',(Join-Path $Run 'response.json'))
      Write-Output $Run
    }
    'goose' {
      if (!$Model) { throw 'Select the exact model ID published by the local server' }
      $probeArgs = @('-m','rsec.local','probe','--port',$Port,'--model',$Model,'--catalog-only','--output',(Join-Path $Run 'baseline.json'))
      if ($GooseBackend -eq 'ollama') { $probeArgs += '--ollama' }
      Run-Checked $Python $probeArgs
      $gooseDirectory = if ($GooseProfile -eq 'default') { 'goose' } else { "goose-$GooseProfile" }
      Set-ScopedEnv 'GOOSE_PATH_ROOT' (Join-Path $Local $gooseDirectory)
      Set-ScopedEnv 'GOOSE_DISABLE_KEYRING' '1'
      Set-ScopedEnv 'GOOSE_MODE' 'approve'
      Set-ScopedEnv 'NO_PROXY' '127.0.0.1,localhost,::1'
      Set-ScopedEnv 'GOOSE_PROVIDER' $GooseBackend
      Set-ScopedEnv 'GOOSE_PROVIDER__TYPE' $GooseBackend
      Set-ScopedEnv 'GOOSE_PROVIDER__HOST' "http://127.0.0.1:$Port"
      Set-ScopedEnv 'GOOSE_MODEL' $Model
      if ($GooseBackend -eq 'ollama') {
        Set-ScopedEnv 'OLLAMA_HOST' "http://127.0.0.1:$Port"
        Set-ScopedEnv 'GOOSE_PROVIDER__API_KEY' $null
      }
      else {
        Set-ScopedEnv 'OPENAI_HOST' "http://127.0.0.1:$Port"
        Set-ScopedEnv 'OPENAI_BASE_PATH' 'v1/chat/completions'
        Set-ScopedEnv 'OPENAI_API_KEY' 'local-baseline'
        Set-ScopedEnv 'GOOSE_PROVIDER__API_KEY' 'local-baseline'
        foreach ($name in 'OPENAI_CUSTOM_HEADERS','OPENAI_ORGANIZATION','OPENAI_PROJECT') { Set-ScopedEnv $name $null }
      }
      if ($GooseSmoke) {
        Set-ScopedEnv 'GOOSE_MAX_TOKENS' '8'
        Set-ScopedEnv 'GOOSE_MAX_TURNS' '1'
        Set-ScopedEnv 'GOOSE_DISABLE_SESSION_NAMING' '1'
        Set-ScopedEnv 'CONTEXT_FILE_NAMES' '[]'
        Run-Checked $GooseExe @('run','--no-profile','--no-session','--text','Reply with the digit 7 only.')
      } else {
        Run-Checked $GooseExe @('session','--no-profile')
      }
    }
  }
} finally {
  foreach ($name in $Saved.Keys) { Set-ScopedEnv $name ($Saved[$name]) }
  Pop-Location
}
