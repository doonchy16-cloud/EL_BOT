param(
  [string]$Version = '0.6.0'
)
$ErrorActionPreference = 'Stop'

if (-not $env:GITHUB_REPOSITORY) { throw 'GITHUB_REPOSITORY missing' }
if (-not $env:GITHUB_TOKEN) { throw 'GITHUB_TOKEN missing' }
if (-not $env:GITHUB_SHA) { throw 'GITHUB_SHA missing' }
if ($env:GITHUB_REF -and $env:GITHUB_REF -ne 'refs/heads/main') { throw "Release-only recovery requires main, got $($env:GITHUB_REF)" }

$api = if ($env:GITHUB_API_URL) { $env:GITHUB_API_URL.TrimEnd('/') } else { 'https://api.github.com' }
$headers = @{ Authorization = "Bearer $($env:GITHUB_TOKEN)"; Accept = 'application/vnd.github+json'; 'X-GitHub-Api-Version' = '2022-11-28' }
$repo = $env:GITHUB_REPOSITORY
$runSha = [string]$env:GITHUB_SHA
$localCheckpointRoot = Join-Path $env:RUNNER_TOOL_CACHE 'ELReleaseCheckpoint'

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

function Get-LocalCertifiedCheckpoint {
  if (-not (Test-Path -LiteralPath $localCheckpointRoot)) { return $null }
  $candidates = @(Get-ChildItem -LiteralPath $localCheckpointRoot -Directory -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -match '^[0-9a-fA-F]{40}$' -and (Test-Path -LiteralPath (Join-Path $_.FullName 'phase6-certified.zip'))
  } | Sort-Object LastWriteTimeUtc -Descending)
  if ($candidates.Count -eq 0) { return $null }
  return $candidates[0]
}

function Restore-LocalCertifiedCheckpoint([object]$Directory) {
  $zip = Join-Path $Directory.FullName 'phase6-certified.zip'
  Expand-Archive -LiteralPath $zip -DestinationPath . -Force
  Write-Output "LOCAL_CERTIFIED_CHECKPOINT_RESTORED sha=$($Directory.Name) path=$zip"
}

function Save-LocalCertifiedCheckpoint([string]$SourceSha) {
  if ($SourceSha -notmatch '^[0-9a-fA-F]{40}$') { throw "LOCAL_CHECKPOINT_SHA_INVALID sha=$SourceSha" }
  $dir = Join-Path $localCheckpointRoot $SourceSha
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  $zip = Join-Path $dir 'phase6-certified.zip'
  Remove-Item $zip -Force -ErrorAction SilentlyContinue
  Compress-Archive -Path 'dist','data','proof' -DestinationPath $zip -CompressionLevel Fastest
  if (-not (Test-Path -LiteralPath $zip)) { throw 'LOCAL_CERTIFIED_CHECKPOINT_SAVE_FAILED' }
  Write-Output "LOCAL_CERTIFIED_CHECKPOINT_SAVED sha=$SourceSha path=$zip"
}

function Assert-RuntimeCheckpointApplicable([string]$CheckpointSha) {
  $allowed = @(
    '.github/workflows/phase6-step5-release.yml',
    'scripts/publish-step5-main-release.ps1',
    'scripts/release-only-recovery.ps1'
  )
  & git fetch --no-tags --depth=1 origin $CheckpointSha
  if ($LASTEXITCODE -ne 0) { throw "RUNTIME_CHECKPOINT_FETCH_FAILED sha=$CheckpointSha" }
  $changed = @(& git diff --name-only "$CheckpointSha..HEAD")
  if ($LASTEXITCODE -ne 0) { throw "RUNTIME_CHECKPOINT_DIFF_FAILED sha=$CheckpointSha" }
  $forbidden = @($changed | Where-Object { $_ -and $allowed -notcontains ([string]$_).Trim() })
  if ($forbidden.Count -gt 0) {
    throw "RUNTIME_CHECKPOINT_INVALIDATED app/runtime files changed since $CheckpointSha: $($forbidden -join ', ')"
  }
  Write-Output "RUNTIME_CHECKPOINT_REUSE_SAFE sha=$CheckpointSha changed_only=$($changed -join ',')"
}

function Ensure-Node24 {
  $existing = Get-Command node -ErrorAction SilentlyContinue
  if ($existing) {
    $v = (& $existing.Source --version).Trim()
    if ($v -match '^v24\.') {
      Write-Output "NODE24_OK source=PATH version=$v"
      return
    }
  }

  $toolNodeRoot = Join-Path $env:RUNNER_TOOL_CACHE 'node'
  if (Test-Path -LiteralPath $toolNodeRoot) {
    $cached = @(Get-ChildItem -LiteralPath $toolNodeRoot -Filter node.exe -File -Recurse -ErrorAction SilentlyContinue | Where-Object {
      $_.FullName -match '[\\/]24\.[^\\/]*[\\/]x64[\\/]node\.exe$'
    } | Sort-Object FullName -Descending)
    if ($cached.Count -gt 0) {
      $env:PATH = "$($cached[0].Directory.FullName);$env:PATH"
      $v = (& $cached[0].FullName --version).Trim()
      if ($v -notmatch '^v24\.') { throw "CACHED_NODE24_INVALID version=$v" }
      Write-Output "NODE24_OK source=RUNNER_TOOL_CACHE version=$v"
      return
    }
  }

  $index = @(Invoke-RestMethod -UseBasicParsing -Uri 'https://nodejs.org/dist/index.json')
  $entry = @($index | Where-Object { [string]$_.version -match '^v24\.' })[0]
  if (-not $entry) { throw 'NODE24_DISTRIBUTION_NOT_FOUND' }
  $version = [string]$entry.version
  $install = Join-Path $env:RUNNER_TOOL_CACHE ("ELNode\$version")
  $nodeExe = Join-Path $install 'node.exe'
  if (-not (Test-Path -LiteralPath $nodeExe)) {
    $zip = Join-Path $env:RUNNER_TEMP ("node-$version-win-x64.zip")
    $extract = Join-Path $env:RUNNER_TEMP ("node-$version-win-x64")
    Remove-Item $zip -Force -ErrorAction SilentlyContinue
    Remove-Item $extract -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path $extract | Out-Null
    Invoke-WebRequest -UseBasicParsing -Uri "https://nodejs.org/dist/$version/node-$version-win-x64.zip" -OutFile $zip
    Expand-Archive -LiteralPath $zip -DestinationPath $extract -Force
    $sourceDir = Get-ChildItem -LiteralPath $extract -Directory | Select-Object -First 1
    if (-not $sourceDir) { throw 'NODE24_ARCHIVE_LAYOUT_INVALID' }
    Remove-Item $install -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path $install | Out-Null
    Copy-Item -Path (Join-Path $sourceDir.FullName '*') -Destination $install -Recurse -Force
  }
  $env:PATH = "$install;$env:PATH"
  $v = (& $nodeExe --version).Trim()
  if ($v -notmatch '^v24\.') { throw "NODE24_INSTALL_INVALID version=$v" }
  Write-Output "NODE24_OK source=download version=$v"
}

function Ensure-PythonTorch {
  $dir = Join-Path $env:RUNNER_TOOL_CACHE 'ELPython\3.12.10'
  $exe = Join-Path $dir 'python.exe'
  if (-not (Test-Path -LiteralPath $exe)) {
    $zip = Join-Path $env:RUNNER_TEMP 'python-3.12.10-embed.zip'
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' -OutFile $zip
    Expand-Archive -LiteralPath $zip -DestinationPath $dir -Force
  }
  $pth = Join-Path $dir 'python312._pth'
  if (Test-Path -LiteralPath $pth) {
    $text = Get-Content -LiteralPath $pth -Raw
    if ($text -match '#import site') {
      $text = $text -replace '#import site','import site'
      [IO.File]::WriteAllText($pth,$text,[Text.UTF8Encoding]::new($false))
    }
  }

  $torchDir = Join-Path $env:RUNNER_TOOL_CACHE 'ELTorch\2.13.0-cp312'
  $marker = Join-Path $torchDir '.ready'
  if (-not (Test-Path -LiteralPath $marker)) {
    if (Test-Path -LiteralPath $torchDir) { Remove-Item $torchDir -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $torchDir | Out-Null
    $pipDir = Join-Path $env:RUNNER_TOOL_CACHE 'ELPip'
    $pipz = Join-Path $pipDir 'pip.pyz'
    New-Item -ItemType Directory -Force -Path $pipDir | Out-Null
    if (-not (Test-Path -LiteralPath $pipz)) {
      Invoke-WebRequest -UseBasicParsing -Uri 'https://bootstrap.pypa.io/pip/pip.pyz' -OutFile $pipz
    }
    & $exe $pipz install --disable-pip-version-check --only-binary=:all: --target $torchDir -r 'requirements-phase6-step2.txt'
    if ($LASTEXITCODE -ne 0) { throw 'TORCH_INSTALL_FAILED' }
    Set-Content -LiteralPath $marker -Value 'ready' -Encoding ASCII
  }

  $lines = @(Get-Content -LiteralPath $pth | Where-Object { $_ -notmatch 'ELTorch\\' })
  $lines += $torchDir
  if (-not ($lines -contains 'import site')) { $lines += 'import site' }
  [IO.File]::WriteAllLines($pth,$lines,[Text.UTF8Encoding]::new($false))
  & $exe -c "import sys,torch;assert sys.version_info[:2]==(3,12);assert torch.__version__.startswith('2.13.0');print(sys.version);print(torch.__version__)"
  if ($LASTEXITCODE -ne 0) { throw 'PYTHON_TORCH_VERIFY_FAILED' }
  $env:EL_PYTHON = $exe
  return $exe
}

function Build-PackageFromRuntimeCheckpoint([string]$PythonExe) {
  $env:PYTHONIOENCODING = 'utf-8'
  & $PythonExe 'architecture\verify_phase6_step5_release.py'
  if ($LASTEXITCODE -ne 0) { throw 'STEP5_AUTHORITY_FAILED' }

  & npm install --no-audit --no-fund
  if ($LASTEXITCODE -ne 0) { throw 'NPM_INSTALL_FAILED' }

  & $PythonExe 'scripts\materialize-phase6-runtime.py'
  if ($LASTEXITCODE -ne 0) { throw 'PHASE6_RUNTIME_MATERIALIZE_FAILED' }
  $env:EL_FORGEY_REGISTRY = (Resolve-Path 'data\phase6-step3\generation-registry.json').Path
  & node 'scripts\phase6-step4-runtime-proof.js'
  if ($LASTEXITCODE -ne 0) { throw 'PORTABLE_REGISTRY_RUNTIME_FAILED' }
  $red = [char]::ConvertFromUtf32(0x1F534)
  & $PythonExe 'scripts\phase6-vision-infer.py' --registry $env:EL_FORGEY_REGISTRY --direction 'IMAGE_TO_EL' --fixture-concept 'red-circle' --fixture-seed 9000 --expected $red --evidence 'data\phase6-step3\runtime-vision-proof.json'
  if ($LASTEXITCODE -ne 0) { throw 'PORTABLE_REGISTRY_VISION_FAILED' }

  powershell -NoProfile -ExecutionPolicy Bypass -File 'scripts\materialize-phase6-python.ps1'
  if ($LASTEXITCODE -ne 0) { throw 'PHASE6_EMBEDDED_RUNTIME_FAILED' }
  & '.\python\python.exe' -c "import sys,torch;assert sys.version_info[:2]==(3,12);assert torch.__version__.startswith('2.13.0');print(torch.__version__)"
  if ($LASTEXITCODE -ne 0) { throw 'EMBEDDED_PYTHON_TORCH_VERIFY_FAILED' }

  & npm run build:windows
  if ($LASTEXITCODE -ne 0) { throw 'WINDOWS_BUILD_FAILED' }
  if (-not (Test-Path -LiteralPath 'dist\win-unpacked\EL-Bot.exe')) { throw 'unpacked packaged executable missing' }
  if (-not (Test-Path -LiteralPath "dist\EL-Bot-Setup-$Version-x64.exe")) { throw 'Phase-6 NSIS installer missing' }
  if (-not (Test-Path -LiteralPath "dist\EL-Bot-Portable-$Version-x64.exe")) { throw 'Phase-6 portable executable missing' }
  $app = 'dist\win-unpacked\resources\app'
  $brain = [char]::ConvertFromUtf32(0x1F9E0)
  $robot = [char]::ConvertFromUtf32(0x1F916)
  $eye = ([char]::ConvertFromUtf32(0x1F441) + [char]0xFE0)
  $requiredPaths = @(
    'python\python.exe',
    'data\phase6-step3\generation-registry.json',
    'scripts\phase6-step4-status.py',
    'scripts\phase6-step4-admin-action.py',
    'scripts\phase6-vision-infer.py',
    (Join-Path $brain $robot),
    (Join-Path $brain $eye),
    'architecture\phase6_step4_runtime_console_manifest.json'
  )
  foreach ($required in $requiredPaths) {
    if (-not (Test-Path -LiteralPath (Join-Path $app $required))) { throw "packaged runtime missing $required" }
  }
  Write-Output 'WINDOWS_PACKAGE_FROM_RUNTIME_CHECKPOINT_OK'
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
$localCertified = Get-LocalCertifiedCheckpoint
$package = Get-LatestCheckpoint $artifacts 'phase6-package-'
$runtimeVisual = Get-LatestCheckpoint $artifacts 'phase6-runtime-visual-'

if ($certified) {
  $sourceSha = Get-CheckpointSha $certified 'phase6-certified-'
  Download-Checkpoint $certified 'phase6-certified.zip' (Get-Location)
  $mode = 'github-certified'
} elseif ($localCertified) {
  $sourceSha = [string]$localCertified.Name
  Restore-LocalCertifiedCheckpoint $localCertified
  $mode = 'local-certified'
} elseif ($package) {
  $sourceSha = Get-CheckpointSha $package 'phase6-package-'
  Download-Checkpoint $package 'phase6-package.zip' (Get-Location)
  $pythonExe = Ensure-PythonTorch
  Certify-PackageCheckpoint $pythonExe
  Save-LocalCertifiedCheckpoint $sourceSha
  $mode = 'github-package-certify'
} elseif ($runtimeVisual) {
  $runtimeSha = Get-CheckpointSha $runtimeVisual 'phase6-runtime-visual-'
  Assert-RuntimeCheckpointApplicable $runtimeSha
  Download-Checkpoint $runtimeVisual 'phase6-runtime-visual.zip' (Get-Location)
  Ensure-Node24
  $pythonExe = Ensure-PythonTorch
  Build-PackageFromRuntimeCheckpoint $pythonExe
  Certify-PackageCheckpoint $pythonExe
  $sourceSha = $runSha
  Save-LocalCertifiedCheckpoint $sourceSha
  $mode = "runtime-visual-package-certify:$runtimeSha"
} else {
  throw 'NO_RELEASE_RECOVERY_CHECKPOINT_AVAILABLE'
}

if (-not $sourceSha) { throw 'RELEASE_SOURCE_SHA_UNRESOLVED' }
"EL_CERTIFIED_RELEASE_SHA=$sourceSha" | Out-File $env:GITHUB_ENV -Encoding utf8 -Append
$env:GITHUB_SHA = $sourceSha
& 'scripts\publish-step5-main-release.ps1' -Version $Version
if ($LASTEXITCODE -ne 0) { throw 'PHASE6_RELEASE_ONLY_PUBLISH_FAILED' }
Write-Output "PHASE6_RELEASE_ONLY_OK mode=$mode sha=$sourceSha"
