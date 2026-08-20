param(
  [string]$Version = '0.6.0'
)
$ErrorActionPreference = 'Stop'

if (-not $env:GITHUB_REPOSITORY) { throw 'GITHUB_REPOSITORY missing' }
if (-not $env:GITHUB_TOKEN) { throw 'GITHUB_TOKEN missing' }
if ($env:GITHUB_REF -and $env:GITHUB_REF -ne 'refs/heads/main') { throw "Release-only recovery requires main, got $($env:GITHUB_REF)" }

$api = if ($env:GITHUB_API_URL) { $env:GITHUB_API_URL.TrimEnd('/') } else { 'https://api.github.com' }
$headers = @{ Authorization = "Bearer $($env:GITHUB_TOKEN)"; Accept = 'application/vnd.github+json'; 'X-GitHub-Api-Version' = '2022-11-28' }
$repo = $env:GITHUB_REPOSITORY

function Get-AllArtifacts {
  $items = @()
  $page = 1
  do {
    $listing = Invoke-RestMethod -Method Get -Uri "$api/repos/$repo/actions/artifacts?per_page=100&page=$page" -Headers $headers
    $batch = @($listing.artifacts)
    $items += $batch
    $page += 1
  } while ($batch.Count -eq 100)
  return @($items)
}

function Get-LatestCheckpoint([object[]]$Artifacts, [string]$Prefix) {
  return @($Artifacts | Where-Object {
    -not $_.expired -and [string]$_.name -like "$Prefix*"
  } | Sort-Object created_at -Descending)[0]
}

function Get-CheckpointSha([object]$Artifact, [string]$Prefix) {
  if (-not $Artifact) { throw "CHECKPOINT_MISSING prefix=$Prefix" }
  $name = [string]$Artifact.name
  if (-not $name.StartsWith($Prefix, [StringComparison]::Ordinal)) { throw "CHECKPOINT_NAME_INVALID name=$name prefix=$Prefix" }
  $sha = $name.Substring($Prefix.Length)
  if ($sha -notmatch '^[0-9a-fA-F]{40}$') { throw "CHECKPOINT_SHA_INVALID name=$name" }
  if ($Artifact.workflow_run -and [string]$Artifact.workflow_run.head_branch -and [string]$Artifact.workflow_run.head_branch -ne 'main') {
    throw "CHECKPOINT_NOT_MAIN name=$name branch=$($Artifact.workflow_run.head_branch)"
  }
  if ($Artifact.workflow_run -and [string]$Artifact.workflow_run.head_sha -and [string]$Artifact.workflow_run.head_sha -ne $sha) {
    throw "CHECKPOINT_SHA_MISMATCH name=$name head_sha=$($Artifact.workflow_run.head_sha)"
  }
  return $sha
}

function Download-Checkpoint([object]$Artifact, [string]$ExpectedInnerZip, [string]$ExpandInto) {
  $outer = Join-Path $env:RUNNER_TEMP ("artifact-$($Artifact.id).zip")
  $staging = Join-Path $env:RUNNER_TEMP ("artifact-$($Artifact.id)")
  Remove-Item $outer -Force -ErrorAction SilentlyContinue
  Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Force -Path $staging | Out-Null
  Invoke-WebRequest -UseBasicParsing -Uri "$api/repos/$repo/actions/artifacts/$($Artifact.id)/zip" -Headers $headers -OutFile $outer
  Expand-Archive -LiteralPath $outer -DestinationPath $staging -Force
  $inner = Join-Path $staging $ExpectedInnerZip
  if (-not (Test-Path -LiteralPath $inner)) { throw "CHECKPOINT_INNER_ZIP_MISSING artifact=$($Artifact.name) expected=$ExpectedInnerZip" }
  Expand-Archive -LiteralPath $inner -DestinationPath $ExpandInto -Force
  Write-Output "CHECKPOINT_RESTORED name=$($Artifact.name) id=$($Artifact.id)"
}

function Resolve-Python {
  $candidates = @(
    (Join-Path $env:RUNNER_TOOL_CACHE 'ELPython\3.12.10\python.exe'),
    (Join-Path (Get-Location) 'dist\win-unpacked\resources\app\python\python.exe')
  )
  foreach ($candidate in $candidates) {
    if (Test-Path -LiteralPath $candidate) { return (Resolve-Path -LiteralPath $candidate).Path }
  }
  throw 'CERTIFICATION_PYTHON_MISSING'
}

function Certify-PackageCheckpoint([string]$PythonExe) {
  $smoke = Join-Path $env:RUNNER_TEMP 'el-bot-package-smoke.json'
  Remove-Item -LiteralPath $smoke -Force -ErrorAction SilentlyContinue
  $env:EL_PACKAGE_SMOKE_FILE = $smoke
  Remove-Item Env:EL_PYTHON -ErrorAction SilentlyContinue
  $process = Start-Process -FilePath (Resolve-Path 'dist\win-unpacked\EL-Bot.exe') -PassThru
  if (-not $process.WaitForExit(120000)) {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    throw 'packaged UI smoke timed out'
  }
  if ($process.ExitCode -ne 0) { throw "packaged UI smoke exit $($process.ExitCode)" }
  if (-not (Test-Path -LiteralPath $smoke)) { throw 'packaged UI smoke evidence missing' }
  $e = Get-Content -LiteralPath $smoke -Raw -Encoding UTF8 | ConvertFrom-Json
  if (-not $e.app_is_packaged -or -not $e.rendered -or -not $e.polished -or -not $e.bundled_python -or -not $e.python_exec) {
    throw 'packaged UI/Python smoke failed'
  }
  Copy-Item -LiteralPath $smoke -Destination 'dist\package-smoke.json' -Force

  $env:EL_PYTHON = $PythonExe
  $env:PYTHONIOENCODING = 'utf-8'
  & $PythonExe 'scripts\phase6-step5-package-forgey-proof.py'
  if ($LASTEXITCODE -ne 0) { throw 'PACKAGED_FORGEY_PROOF_FAILED' }
  $p = Get-Content -LiteralPath 'dist\phase6-package-forgey-proof.json' -Raw -Encoding UTF8 | ConvertFrom-Json
  if ($p.selected_generation -ne 'G2' -or $p.forward_provider_calls -ne 0 -or $p.reverse_provider_calls -ne 0 -or $p.native_vision_provider_calls -ne 0 -or -not $p.vision_enabled -or $p.vision_parameters -le 0 -or $p.diagnostics -ne '44/44') {
    throw 'packaged multimodal Forgey evidence contract failed'
  }

  & $PythonExe 'architecture\verify_phase2_knowledge_foundation.py'
  if ($LASTEXITCODE -ne 0) { throw 'PHASE2_FAILED' }
  & $PythonExe 'architecture\verify_phase3_semantic_search.py'
  if ($LASTEXITCODE -ne 0) { throw 'PHASE3_FAILED' }
  $diag = "import importlib.machinery,importlib.util,pathlib,sys;root=pathlib.Path('.');a=chr(0x1F9EA);p=next(x for x in root.rglob('*') if x.is_file() and x.name==a and x.parent.name==a);l=importlib.machinery.SourceFileLoader('_p6s5_diag',str(p));s=importlib.util.spec_from_loader('_p6s5_diag',l);m=importlib.util.module_from_spec(s);sys.modules['_p6s5_diag']=m;l.exec_module(m);r=m.DiagnosticsEngine().run();print(r.render_el());assert r.passed and len(r.checks)==44"
  & $PythonExe -c $diag
  if ($LASTEXITCODE -ne 0) { throw 'CURRENT_44_DIAGNOSTICS_FAILED' }
  Write-Output 'PACKAGE_CHECKPOINT_CERTIFICATION_OK'
}

$artifacts = @(Get-AllArtifacts)
$phase6Names = @($artifacts | Where-Object { [string]$_.name -like 'phase6-*' } | Sort-Object created_at -Descending | ForEach-Object { "$($_.name):expired=$($_.expired):created=$($_.created_at)" })
Write-Output ("PHASE6_ARTIFACT_INVENTORY count=$($phase6Names.Count) " + ($phase6Names -join ';'))

$sourceSha = $null
$mode = $null
$certified = Get-LatestCheckpoint $artifacts 'phase6-certified-'
if ($certified) {
  $sourceSha = Get-CheckpointSha $certified 'phase6-certified-'
  Download-Checkpoint $certified 'phase6-certified.zip' (Get-Location)
  $mode = 'certified'
} else {
  $package = Get-LatestCheckpoint $artifacts 'phase6-package-'
  if (-not $package) {
    throw 'NO_CERTIFIED_OR_PACKAGE_CHECKPOINT_AVAILABLE'
  }
  $sourceSha = Get-CheckpointSha $package 'phase6-package-'
  Download-Checkpoint $package 'phase6-package.zip' (Get-Location)
  $pythonExe = Resolve-Python
  Certify-PackageCheckpoint $pythonExe
  $mode = 'package-certify'
}

if (-not $sourceSha) { throw 'RELEASE_SOURCE_SHA_UNRESOLVED' }
"EL_CERTIFIED_RELEASE_SHA=$sourceSha" | Out-File $env:GITHUB_ENV -Encoding utf8 -Append
$env:GITHUB_SHA = $sourceSha
& 'scripts\publish-step5-main-release.ps1' -Version $Version
if ($LASTEXITCODE -ne 0) { throw 'PHASE6_RELEASE_ONLY_PUBLISH_FAILED' }
Write-Output "PHASE6_RELEASE_ONLY_OK mode=$mode sha=$sourceSha"
