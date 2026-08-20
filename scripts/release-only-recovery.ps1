param(
  [string]$Version = '0.6.0'
)
$ErrorActionPreference = 'Stop'

if (-not $env:GITHUB_REPOSITORY) { throw 'GITHUB_REPOSITORY missing' }
if (-not $env:GITHUB_TOKEN) { throw 'GITHUB_TOKEN missing' }
if (-not $env:GITHUB_SHA) { throw 'GITHUB_SHA missing' }
if ($env:GITHUB_REF -and $env:GITHUB_REF -ne 'refs/heads/main') { throw "Release-only recovery requires main, got $($env:GITHUB_REF)" }

$repo = $env:GITHUB_REPOSITORY
$runSha = [string]$env:GITHUB_SHA
$api = if ($env:GITHUB_API_URL) { $env:GITHUB_API_URL.TrimEnd('/') } else { 'https://api.github.com' }
$headers = @{ Authorization = "Bearer $($env:GITHUB_TOKEN)"; Accept = 'application/vnd.github+json'; 'X-GitHub-Api-Version' = '2022-11-28' }
$allowedChanges = @(
  '.github/workflows/phase6-step5-release.yml',
  'scripts/publish-step5-main-release.ps1',
  'scripts/release-only-recovery.ps1'
)
$localRoot = Join-Path $env:RUNNER_TOOL_CACHE 'ELReleaseCheckpoint'

function Assert-OnlyReleasePlumbingChanged([string]$BaseSha) {
  & git fetch --no-tags --depth=1 origin $BaseSha | Out-Host
  if ($LASTEXITCODE -ne 0) { throw "CHECKPOINT_FETCH_FAILED sha=$BaseSha" }
  $changed = @(& git diff --name-only "$BaseSha..HEAD")
  if ($LASTEXITCODE -ne 0) { throw "CHECKPOINT_DIFF_FAILED sha=$BaseSha" }
  $unexpected = @($changed | Where-Object { $_ -and $allowedChanges -notcontains ([string]$_).Trim() })
  if ($unexpected.Count -gt 0) { throw "CHECKPOINT_INVALIDATED unexpected files: $($unexpected -join ', ')" }
  Write-Output "CHECKPOINT_REUSE_SAFE base=$BaseSha changed=$($changed -join ',')"
}

function Restore-LocalCertified([object]$Directory) {
  $baseSha = [string]$Directory.Name
  Assert-OnlyReleasePlumbingChanged $baseSha
  $zip = Join-Path $Directory.FullName 'phase6-certified.zip'
  Expand-Archive -LiteralPath $zip -DestinationPath . -Force
  Write-Output "LOCAL_CERTIFIED_RESTORED base=$baseSha path=$zip"
}

function Save-LocalCertified {
  $dir = Join-Path $localRoot $runSha
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  $zip = Join-Path $dir 'phase6-certified.zip'
  Remove-Item -LiteralPath $zip -Force -ErrorAction SilentlyContinue
  Compress-Archive -Path 'dist','data','proof' -DestinationPath $zip -CompressionLevel Fastest
  if (-not (Test-Path -LiteralPath $zip)) { throw 'LOCAL_CERTIFIED_SAVE_FAILED' }
  Write-Output "LOCAL_CERTIFIED_SAVED sha=$runSha path=$zip"
}

$local = $null
if (Test-Path -LiteralPath $localRoot) {
  $local = @(Get-ChildItem -LiteralPath $localRoot -Directory -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -match '^[0-9a-fA-F]{40}$' -and (Test-Path -LiteralPath (Join-Path $_.FullName 'phase6-certified.zip'))
  } | Sort-Object LastWriteTimeUtc -Descending)[0]
}

if ($local) {
  Restore-LocalCertified $local
  $mode = 'local-certified'
} else {
  $artifacts = @()
  $page = 1
  do {
    $listing = Invoke-RestMethod -Method Get -Uri "$api/repos/$repo/actions/artifacts?per_page=100&page=$page" -Headers $headers
    $batch = @($listing.artifacts)
    $artifacts += $batch
    $page++
  } while ($batch.Count -eq 100)

  $prefix = 'phase6-runtime-visual-'
  $artifact = @($artifacts | Where-Object {
    -not $_.expired -and [string]$_.name -like "$prefix*"
  } | Sort-Object created_at -Descending)[0]
  if (-not $artifact) { throw 'RUNTIME_VISUAL_CHECKPOINT_NOT_FOUND' }

  $artifactName = [string]$artifact.name
  $runtimeSha = $artifactName.Substring($prefix.Length)
  if ($runtimeSha -notmatch '^[0-9a-fA-F]{40}$') { throw "RUNTIME_CHECKPOINT_SHA_INVALID name=$artifactName" }
  Assert-OnlyReleasePlumbingChanged $runtimeSha

  $outer = Join-Path $env:RUNNER_TEMP 'phase6-runtime-visual-artifact.zip'
  $stage = Join-Path $env:RUNNER_TEMP 'phase6-runtime-visual-artifact'
  Remove-Item -LiteralPath $outer -Force -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Force -Path $stage | Out-Null
  Invoke-WebRequest -UseBasicParsing -Uri "$api/repos/$repo/actions/artifacts/$($artifact.id)/zip" -Headers $headers -OutFile $outer
  Expand-Archive -LiteralPath $outer -DestinationPath $stage -Force
  $inner = Join-Path $stage 'phase6-runtime-visual.zip'
  if (-not (Test-Path -LiteralPath $inner)) { throw 'RUNTIME_VISUAL_INNER_ZIP_MISSING' }
  Expand-Archive -LiteralPath $inner -DestinationPath . -Force
  Write-Output "RUNTIME_VISUAL_RESTORED id=$($artifact.id) sha=$runtimeSha"

  $nodeVersion = (& node --version).Trim()
  if ($nodeVersion -notmatch '^v24\.') { throw "NODE24_REQUIRED found=$nodeVersion" }
  Write-Output "NODE24_OK version=$nodeVersion"

  $pythonExe = Join-Path $env:RUNNER_TOOL_CACHE 'ELPython\3.12.10\python.exe'
  $torchDir = Join-Path $env:RUNNER_TOOL_CACHE 'ELTorch\2.13.0-cp312'
  $torchMarker = Join-Path $torchDir '.ready'
  if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'CACHED_PYTHON_3_12_10_MISSING' }
  if (-not (Test-Path -LiteralPath $torchMarker)) { throw 'CACHED_TORCH_2_13_MISSING' }
  $pth = Join-Path (Split-Path -Parent $pythonExe) 'python312._pth'
  $lines = @(Get-Content -LiteralPath $pth | Where-Object { $_ -notmatch 'ELTorch\\' })
  $lines += $torchDir
  if (-not ($lines -contains 'import site')) { $lines += 'import site' }
  [IO.File]::WriteAllLines($pth,$lines,[Text.UTF8Encoding]::new($false))
  & $pythonExe -c "import sys,torch;assert sys.version_info[:2]==(3,12);assert torch.__version__.startswith('2.13.0');print('PYTHON_TORCH_OK',sys.version.split()[0],torch.__version__)" | Out-Host
  if ($LASTEXITCODE -ne 0) { throw 'PYTHON_TORCH_VERIFY_FAILED' }
  $env:EL_PYTHON = $pythonExe
  $env:PYTHONIOENCODING = 'utf-8'

  & $pythonExe 'architecture\verify_phase6_step5_release.py' | Out-Host
  if ($LASTEXITCODE -ne 0) { throw 'STEP5_AUTHORITY_FAILED' }

  & npm install --no-audit --no-fund | Out-Host
  if ($LASTEXITCODE -ne 0) { throw 'NPM_INSTALL_FAILED' }

  & $pythonExe 'scripts\materialize-phase6-runtime.py' | Out-Host
  if ($LASTEXITCODE -ne 0) { throw 'PHASE6_RUNTIME_MATERIALIZE_FAILED' }
  $env:EL_FORGEY_REGISTRY = (Resolve-Path 'data\phase6-step3\generation-registry.json').Path
  & node 'scripts\phase6-step4-runtime-proof.js' | Out-Host
  if ($LASTEXITCODE -ne 0) { throw 'PORTABLE_REGISTRY_RUNTIME_FAILED' }
  $red = [char]::ConvertFromUtf32(0x1F534)
  & $pythonExe 'scripts\phase6-vision-infer.py' --registry $env:EL_FORGEY_REGISTRY --direction 'IMAGE_TO_EL' --fixture-concept 'red-circle' --fixture-seed 9000 --expected $red --evidence 'data\phase6-step3\runtime-vision-proof.json' | Out-Host
  if ($LASTEXITCODE -ne 0) { throw 'PORTABLE_REGISTRY_VISION_FAILED' }

  powershell -NoProfile -ExecutionPolicy Bypass -File 'scripts\materialize-phase6-python.ps1' | Out-Host
  if ($LASTEXITCODE -ne 0) { throw 'PHASE6_EMBEDDED_RUNTIME_FAILED' }
  & '.\python\python.exe' -c "import sys,torch;assert sys.version_info[:2]==(3,12);assert torch.__version__.startswith('2.13.0');print('EMBEDDED_OK',torch.__version__)" | Out-Host
  if ($LASTEXITCODE -ne 0) { throw 'EMBEDDED_RUNTIME_VERIFY_FAILED' }

  & npm run build:windows | Out-Host
  if ($LASTEXITCODE -ne 0) { throw 'WINDOWS_BUILD_FAILED' }
  foreach ($path in @(
    'dist\win-unpacked\EL-Bot.exe',
    "dist\EL-Bot-Setup-$Version-x64.exe",
    "dist\EL-Bot-Portable-$Version-x64.exe"
  )) { if (-not (Test-Path -LiteralPath $path)) { throw "PACKAGE_OUTPUT_MISSING $path" } }

  $smoke = Join-Path $env:RUNNER_TEMP 'el-bot-package-smoke.json'
  Remove-Item -LiteralPath $smoke -Force -ErrorAction SilentlyContinue
  $env:EL_PACKAGE_SMOKE_FILE = $smoke
  Remove-Item Env:EL_PYTHON -ErrorAction SilentlyContinue
  $process = Start-Process -FilePath (Resolve-Path 'dist\win-unpacked\EL-Bot.exe') -PassThru
  if (-not $process.WaitForExit(120000)) { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue; throw 'PACKAGE_SMOKE_TIMEOUT' }
  if ($process.ExitCode -ne 0) { throw "PACKAGE_SMOKE_EXIT_$($process.ExitCode)" }
  if (-not (Test-Path -LiteralPath $smoke)) { throw 'PACKAGE_SMOKE_EVIDENCE_MISSING' }
  $smokeEvidence = Get-Content -LiteralPath $smoke -Raw -Encoding UTF8 | ConvertFrom-Json
  if (-not $smokeEvidence.app_is_packaged -or -not $smokeEvidence.rendered -or -not $smokeEvidence.polished -or -not $smokeEvidence.bundled_python -or -not $smokeEvidence.python_exec) { throw 'PACKAGE_SMOKE_CONTRACT_FAILED' }
  Copy-Item -LiteralPath $smoke -Destination 'dist\package-smoke.json' -Force

  $env:EL_PYTHON = $pythonExe
  & $pythonExe 'scripts\phase6-step5-package-forgey-proof.py' | Out-Host
  if ($LASTEXITCODE -ne 0) { throw 'PACKAGED_FORGEY_PROOF_FAILED' }
  $proof = Get-Content -LiteralPath 'dist\phase6-package-forgey-proof.json' -Raw -Encoding UTF8 | ConvertFrom-Json
  if ($proof.selected_generation -ne 'G2' -or $proof.forward_provider_calls -ne 0 -or $proof.reverse_provider_calls -ne 0 -or $proof.native_vision_provider_calls -ne 0 -or -not $proof.vision_enabled -or $proof.vision_parameters -le 0 -or $proof.diagnostics -ne '44/44') { throw 'PACKAGED_FORGEY_CONTRACT_FAILED' }

  & $pythonExe 'architecture\verify_phase2_knowledge_foundation.py' | Out-Host
  if ($LASTEXITCODE -ne 0) { throw 'PHASE2_FAILED' }
  & $pythonExe 'architecture\verify_phase3_semantic_search.py' | Out-Host
  if ($LASTEXITCODE -ne 0) { throw 'PHASE3_FAILED' }
  & $pythonExe -c "import importlib.machinery,importlib.util,pathlib,sys;root=pathlib.Path('.');a=chr(0x1F9EA);p=next(x for x in root.rglob('*') if x.is_file() and x.name==a and x.parent.name==a);l=importlib.machinery.SourceFileLoader('_p6s5_diag',str(p));s=importlib.util.spec_from_loader('_p6s5_diag',l);m=importlib.util.module_from_spec(s);sys.modules['_p6s5_diag']=m;l.exec_module(m);r=m.DiagnosticsEngine().run();print(r.render_el());assert r.passed and len(r.checks)==44" | Out-Host
  if ($LASTEXITCODE -ne 0) { throw 'FINAL_44_DIAGNOSTICS_FAILED' }

  Save-LocalCertified
  $mode = "runtime-visual:$runtimeSha"
}

"EL_CERTIFIED_RELEASE_SHA=$runSha" | Out-File $env:GITHUB_ENV -Encoding utf8 -Append
$env:GITHUB_SHA = $runSha
& 'scripts\publish-step5-main-release.ps1' -Version $Version | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'PHASE6_RELEASE_PUBLISH_FAILED' }
Write-Output "PHASE6_RELEASE_ONLY_OK mode=$mode sha=$runSha"
