param([string]$Destination = 'G:\Rsec')
$ErrorActionPreference = 'Stop'
$branch = 'feat/rsec-local-infrastructure-v0.3.0'
$url = 'https://github.com/Snowwiy/Rsec.git'
if (!(Test-Path -LiteralPath $Destination)) {
  & git clone --branch $branch -- $url $Destination
  if ($LASTEXITCODE -ne 0) { throw 'Clone failed; inspect destination before retry' }
} else {
  $root = & git -C $Destination rev-parse --show-toplevel
  if ($LASTEXITCODE -ne 0 -or (Resolve-Path -LiteralPath $root).Path -ne (Resolve-Path -LiteralPath $Destination).Path) { throw 'Existing directory is not the repository root' }
  $origin = & git -C $Destination remote get-url origin
  if ($LASTEXITCODE -ne 0 -or $origin -notin @($url,'https://github.com/Snowwiy/Rsec','git@github.com:Snowwiy/Rsec.git')) { throw 'Unexpected origin' }
  & git -C $Destination fetch origin
  if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
  & git -C $Destination status --short --branch
  $changes = & git -C $Destination status --porcelain
  if ($LASTEXITCODE -ne 0 -or $changes) { throw 'Preserving worktree. Review local changes before switching branches.' }
  & git -C $Destination switch --no-overwrite-ignore $branch
  if ($LASTEXITCODE -ne 0) { throw 'Branch switch failed; inspect locally' }
  & git -C $Destination merge --no-overwrite-ignore --ff-only "origin/$branch"
  if ($LASTEXITCODE -ne 0) { throw 'Local history diverges; inspect before integration' }
}
