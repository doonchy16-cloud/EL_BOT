param(
  [string]$Version = '0.6.0',
  [string]$Phase5KeepSha = 'c489d6f79d2f21d9544d8631dda3de7793adebf0'
)
$ErrorActionPreference = 'Stop'

if (-not $env:GITHUB_REPOSITORY) { throw 'GITHUB_REPOSITORY missing' }
if (-not $env:GITHUB_SHA) { throw 'GITHUB_SHA missing' }
if (-not $env:GITHUB_TOKEN) { throw 'GITHUB_TOKEN missing' }
if ($env:GITHUB_REF -and $env:GITHUB_REF -ne 'refs/heads/main') { throw "Phase-6 release publisher requires main, got $($env:GITHUB_REF)" }

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$repo = $env:GITHUB_REPOSITORY
$sha = [string]$env:GITHUB_SHA
$short = $sha.Substring(0, [Math]::Min(12, $sha.Length))
$tag = "el-bot-v$Version-$short"
$api = if ($env:GITHUB_API_URL) { $env:GITHUB_API_URL.TrimEnd('/') } else { 'https://api.github.com' }
$headers = @{ Authorization = "Bearer $($env:GITHUB_TOKEN)"; Accept = 'application/vnd.github+json'; 'X-GitHub-Api-Version' = '2022-11-28' }

function Get-FirstScalar([object]$Value) {
  $values = @($Value)
  if ($values.Count -lt 1) { return $null }
  return $values[0]
}

function Get-HttpStatus([object]$ErrorRecord) {
  try { return [int]$ErrorRecord.Exception.Response.StatusCode.value__ } catch { return 0 }
}

function Invoke-ApiGet([string]$Uri, [int]$Attempts = 5) {
  for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
    try { return Invoke-RestMethod -Method Get -Uri $Uri -Headers $headers }
    catch {
      if ($attempt -ge $Attempts) { throw }
      $delay = [Math]::Min(30, 3 * $attempt)
      Write-Warning "API_GET_RETRY attempt=$attempt delay=$delay uri=$Uri error=$($_.Exception.Message)"
      Start-Sleep -Seconds $delay
    }
  }
}

function Get-AllReleases {
  $items = @()
  $page = 1
  do {
    $batch = @(Invoke-ApiGet "$api/repos/$repo/releases?per_page=100&page=$page")
    $items += $batch
    $page++
  } while ($batch.Count -eq 100)
  return @($items)
}

function Get-ReleaseAssets([int64]$ReleaseId) {
  return @(Invoke-ApiGet "$api/repos/$repo/releases/$ReleaseId/assets?per_page=100")
}

function Get-ReleaseByTag([string]$ReleaseTag) {
  $encoded = [Uri]::EscapeDataString($ReleaseTag)
  try { return Invoke-RestMethod -Method Get -Uri "$api/repos/$repo/releases/tags/$encoded" -Headers $headers }
  catch {
    $status = Get-HttpStatus $_
    if ($status -eq 404) { return $null }
    throw
  }
}

function Remove-ReleaseAndTag([object]$Release) {
  $releaseIdValue = Get-FirstScalar $Release.id
  if ($null -eq $releaseIdValue) { throw 'release id missing during cleanup' }
  $releaseId = [int64]$releaseIdValue
  $releaseTag = [string](Get-FirstScalar $Release.tag_name)

  for ($attempt = 1; $attempt -le 4; $attempt++) {
    try {
      Invoke-RestMethod -Method Delete -Uri "$api/repos/$repo/releases/$releaseId" -Headers $headers | Out-Null
      Write-Output "RELEASE_HISTORY_REMOVED release_id=$releaseId tag=$releaseTag"
      break
    } catch {
      $status = Get-HttpStatus $_
      if ($status -eq 404) { break }
      if ($attempt -ge 4) { throw }
      Start-Sleep -Seconds (2 * $attempt)
    }
  }

  if ($releaseTag) {
    $encodedTag = [Uri]::EscapeDataString($releaseTag)
    for ($attempt = 1; $attempt -le 4; $attempt++) {
      try {
        Invoke-RestMethod -Method Delete -Uri "$api/repos/$repo/git/refs/tags/$encodedTag" -Headers $headers | Out-Null
        Write-Output "RELEASE_TAG_REMOVED tag=$releaseTag"
        break
      } catch {
        $status = Get-HttpStatus $_
        if ($status -in @(404, 422)) { break }
        if ($attempt -ge 4) { throw }
        Start-Sleep -Seconds (2 * $attempt)
      }
    }
  }
}

function Remove-Asset([int64]$AssetId) {
  for ($attempt = 1; $attempt -le 4; $attempt++) {
    try {
      Invoke-RestMethod -Method Delete -Uri "$api/repos/$repo/releases/assets/$AssetId" -Headers $headers | Out-Null
      return
    } catch {
      $status = Get-HttpStatus $_
      if ($status -eq 404) { return }
      if ($attempt -ge 4) { throw }
      Start-Sleep -Seconds (2 * $attempt)
    }
  }
}

function Ensure-ReleaseAsset([int64]$ReleaseId, [string]$UploadBase, [string]$Path, [int]$Attempts = 5) {
  $item = Get-Item -LiteralPath $Path
  $name = $item.Name
  $expectedBytes = [int64]$item.Length
  $encodedName = [Uri]::EscapeDataString($name)
  $uploadUri = "${UploadBase}?name=$encodedName"

  for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
    $assets = @(Get-ReleaseAssets $ReleaseId)
    $matches = @($assets | Where-Object { [string](Get-FirstScalar $_.name) -eq $name })
    $exact = @($matches | Where-Object { [int64](Get-FirstScalar $_.size) -eq $expectedBytes })
    if ($matches.Count -eq 1 -and $exact.Count -eq 1) {
      Write-Output "RELEASE_ASSET_PRESENT name=$name bytes=$expectedBytes attempt=$attempt"
      return
    }
    foreach ($asset in $matches) {
      $assetId = [int64](Get-FirstScalar $asset.id)
      Remove-Asset $assetId
    }

    $curlArgs = @(
      '--http1.1', '--fail-with-body', '--silent', '--show-error', '--location',
      '--connect-timeout', '30', '--max-time', '1800',
      '-X', 'POST',
      '-H', "Authorization: Bearer $($env:GITHUB_TOKEN)",
      '-H', 'Accept: application/vnd.github+json',
      '-H', 'X-GitHub-Api-Version: 2022-11-28',
      '-H', 'Content-Type: application/octet-stream',
      '--data-binary', "@$($item.FullName)",
      $uploadUri
    )
    & curl.exe @curlArgs | Out-Null
    $curlExit = $LASTEXITCODE

    $after = @(Get-ReleaseAssets $ReleaseId)
    $uploaded = @($after | Where-Object {
      [string](Get-FirstScalar $_.name) -eq $name -and [int64](Get-FirstScalar $_.size) -eq $expectedBytes
    })
    if ($uploaded.Count -eq 1) {
      Write-Output "RELEASE_ASSET_UPLOAD_OK name=$name bytes=$expectedBytes attempt=$attempt curl=$curlExit"
      return
    }

    if ($attempt -ge $Attempts) { throw "RELEASE_ASSET_UPLOAD_FAILED name=$name bytes=$expectedBytes curl=$curlExit" }
    $delay = [Math]::Min(30, 5 * $attempt)
    Write-Warning "RELEASE_ASSET_RETRY name=$name attempt=$attempt curl=$curlExit delay=$delay"
    Start-Sleep -Seconds $delay
  }
}

function New-OrGetRelease([string]$ReleaseTag, [string]$TargetSha, [string]$Name, [string]$Body) {
  $release = Get-ReleaseByTag $ReleaseTag
  if ($release) { return $release }
  $json = @{ tag_name = $ReleaseTag; target_commitish = $TargetSha; name = $Name; body = $Body; draft = $false; prerelease = $false } | ConvertTo-Json -Depth 4
  try { $release = Invoke-RestMethod -Method Post -Uri "$api/repos/$repo/releases" -Headers $headers -ContentType 'application/json' -Body $json }
  catch {
    $release = Get-ReleaseByTag $ReleaseTag
    if (-not $release) { throw }
  }
  return $release
}

function Test-Phase5ReleaseEligible([object]$Release) {
  $names = @($Release.assets | ForEach-Object { [string](Get-FirstScalar $_.name) })
  return ($names -contains 'EL-Bot-Setup-0.5.0-x64.exe' -and $names -contains 'EL-Bot-Portable-0.5.0-x64.exe' -and $names -contains 'package-smoke.json')
}

function Test-PreferredPhase5([object]$Release) {
  $target = ([string](Get-FirstScalar $Release.target_commitish)).Trim()
  $tagName = [string](Get-FirstScalar $Release.tag_name)
  $shortKeep = $Phase5KeepSha.Substring(0, 7)
  $targetMatches = $false
  if ($target) {
    $targetMatches = $Phase5KeepSha.StartsWith($target, [StringComparison]::OrdinalIgnoreCase) -or $target.StartsWith($Phase5KeepSha, [StringComparison]::OrdinalIgnoreCase)
  }
  return ($targetMatches -or $tagName.IndexOf($shortKeep, [StringComparison]::OrdinalIgnoreCase) -ge 0)
}

function Recover-Phase5Keeper {
  $currentRoot = (Get-Location).Path
  $phase5Short = $Phase5KeepSha.Substring(0, 12)
  $phase5Tag = "el-bot-v0.5.0-$phase5Short"
  $work = Join-Path $env:RUNNER_TEMP "el-bot-phase5-recovery-$phase5Short"
  Write-Output "PHASE5_RECOVERY_BEGIN sha=$Phase5KeepSha tag=$phase5Tag"

  & git fetch --no-tags --depth=1 origin $Phase5KeepSha | Out-Host
  if ($LASTEXITCODE -ne 0) { throw 'PHASE5_RECOVERY_FETCH_FAILED' }
  & git worktree remove --force $work 2>$null | Out-Null
  & git worktree prune | Out-Null
  Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
  & git worktree add --detach $work $Phase5KeepSha | Out-Host
  if ($LASTEXITCODE -ne 0) { throw 'PHASE5_RECOVERY_WORKTREE_FAILED' }

  try {
    $proofSource = Join-Path $currentRoot 'proof\phase5'
    $proofTarget = Join-Path $work 'proof\phase5'
    New-Item -ItemType Directory -Force -Path $proofTarget | Out-Null
    foreach ($name in @('hourglass-30fps.mp4','hourglass-contact-sheet.png','ui-idle.png','ui-warning.png','preview-zoom.png','proof.json')) {
      $source = Join-Path $proofSource $name
      if (-not (Test-Path -LiteralPath $source)) { throw "PHASE5_RECOVERY_PROOF_MISSING $name" }
      Copy-Item -LiteralPath $source -Destination (Join-Path $proofTarget $name) -Force
    }

    Push-Location $work
    try {
      & npm install --no-audit --no-fund | Out-Host
      if ($LASTEXITCODE -ne 0) { throw 'PHASE5_RECOVERY_NPM_FAILED' }
      powershell -NoProfile -ExecutionPolicy Bypass -File 'scripts\materialize-python.ps1' | Out-Host
      if ($LASTEXITCODE -ne 0) { throw 'PHASE5_RECOVERY_PYTHON_FAILED' }
      & npm run build:windows -- --publish never | Out-Host
      if ($LASTEXITCODE -ne 0) { throw 'PHASE5_RECOVERY_BUILD_FAILED' }

      foreach ($path in @('dist\EL-Bot-Setup-0.5.0-x64.exe','dist\EL-Bot-Portable-0.5.0-x64.exe','dist\win-unpacked\EL-Bot.exe')) {
        if (-not (Test-Path -LiteralPath $path)) { throw "PHASE5_RECOVERY_OUTPUT_MISSING $path" }
      }

      $smoke = Join-Path $env:RUNNER_TEMP 'el-bot-phase5-recovery-smoke.json'
      Remove-Item -LiteralPath $smoke -Force -ErrorAction SilentlyContinue
      $env:EL_PACKAGE_SMOKE_FILE = $smoke
      Remove-Item Env:EL_PYTHON -ErrorAction SilentlyContinue
      $process = Start-Process -FilePath (Resolve-Path 'dist\win-unpacked\EL-Bot.exe') -PassThru
      if (-not $process.WaitForExit(90000)) { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue; throw 'PHASE5_RECOVERY_SMOKE_TIMEOUT' }
      if ($process.ExitCode -ne 0) { throw "PHASE5_RECOVERY_SMOKE_EXIT_$($process.ExitCode)" }
      if (-not (Test-Path -LiteralPath $smoke)) { throw 'PHASE5_RECOVERY_SMOKE_MISSING' }
      Copy-Item -LiteralPath $smoke -Destination 'dist\package-smoke.json' -Force

      $required5 = @(
        'dist\EL-Bot-Setup-0.5.0-x64.exe',
        'dist\EL-Bot-Portable-0.5.0-x64.exe',
        'dist\package-smoke.json',
        'proof\phase5\hourglass-30fps.mp4',
        'proof\phase5\hourglass-contact-sheet.png',
        'proof\phase5\ui-idle.png',
        'proof\phase5\ui-warning.png',
        'proof\phase5\preview-zoom.png',
        'proof\phase5\proof.json'
      )
      $manifest5 = [ordered]@{ schema_version = 1; phase = 5; status = 'VERIFIED_FOR_RELEASE'; version = '0.5.0'; commit_sha = $Phase5KeepSha; tag = $phase5Tag; generated_utc = [DateTime]::UtcNow.ToString('o'); assets = @() }
      foreach ($path in $required5) {
        $item = Get-Item -LiteralPath $path
        $manifest5.assets += [ordered]@{ name = $item.Name; bytes = $item.Length; sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
      }
      $manifest5Path = 'dist\phase5-release-manifest.json'
      $manifest5 | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifest5Path -Encoding UTF8
      $upload5 = @($required5) + @($manifest5Path)

      $release5 = New-OrGetRelease $phase5Tag $Phase5KeepSha "EL Bot v0.5.0 - Phase 5 ($phase5Short)" "Recovered historical Phase 5 Windows release for exact commit $Phase5KeepSha. Includes NSIS installer, portable EXE, packaged-runtime smoke evidence, and retained verified 30 FPS Phase-5 visual proof."
      $release5Id = [int64](Get-FirstScalar $release5.id)
      $uploadBase5 = ([string](Get-FirstScalar $release5.upload_url)).Split('{')[0]
      foreach ($path in $upload5) { Ensure-ReleaseAsset $release5Id $uploadBase5 $path }
      $verified5 = @(Get-ReleaseAssets $release5Id)
      $names5 = @($verified5 | ForEach-Object { [string](Get-FirstScalar $_.name) })
      foreach ($path in $upload5) {
        $n = (Get-Item -LiteralPath $path).Name
        if ($names5 -notcontains $n) { throw "PHASE5_RECOVERY_RELEASE_MISSING $n" }
      }
      Write-Output "PHASE5_RECOVERY_OK tag=$phase5Tag uploaded=$($upload5.Count)"
    } finally {
      Pop-Location
    }
  } finally {
    & git worktree remove --force $work 2>$null | Out-Null
    & git worktree prune | Out-Null
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
  }

  $recovered = Get-ReleaseByTag $phase5Tag
  if (-not $recovered) { throw 'PHASE5_RECOVERY_RELEASE_REREAD_FAILED' }
  return $recovered
}

# Determine the strongest usable v0.5.0 keeper. Reconstruct c489 if no usable historical release survived.
$releaseHistory = @(Get-AllReleases)
$phase5Prefix = 'el-bot-v0.5.0-'
$phase5Releases = @($releaseHistory | Where-Object { [string](Get-FirstScalar $_.tag_name) -like "$phase5Prefix*" })
$phase5Inventory = @($phase5Releases | ForEach-Object { "tag=$([string](Get-FirstScalar $_.tag_name));assets=$(@($_.assets).Count);eligible=$(Test-Phase5ReleaseEligible $_);preferred=$(Test-PreferredPhase5 $_)" })
Write-Output ("PHASE5_RELEASE_INVENTORY count=$($phase5Releases.Count) " + ($phase5Inventory -join ' | '))
$eligible5 = @($phase5Releases | Where-Object { Test-Phase5ReleaseEligible $_ })
if ($eligible5.Count -gt 0) {
  $phase5Keeper = @($eligible5 | Sort-Object `
    @{ Expression = { @($_.assets).Count }; Descending = $true }, `
    @{ Expression = { if (Test-PreferredPhase5 $_) { 1 } else { 0 } }; Descending = $true }, `
    @{ Expression = { $_.published_at }; Descending = $true } | Select-Object -First 1)[0]
} else {
  $phase5Keeper = Recover-Phase5Keeper
}
$phase5KeeperId = [int64](Get-FirstScalar $phase5Keeper.id)
$phase5KeeperTag = [string](Get-FirstScalar $phase5Keeper.tag_name)
if (-not (Test-Phase5ReleaseEligible $phase5Keeper)) { throw "PHASE5_KEEPER_NOT_INSTALLABLE tag=$phase5KeeperTag" }
Write-Output "PHASE5_RELEASE_KEEP tag=$phase5KeeperTag target=$([string](Get-FirstScalar $phase5Keeper.target_commitish)) assets=$(@($phase5Keeper.assets).Count)"

# Build and verify the current Phase-6 upload payload.
$required = @(
  "dist\EL-Bot-Setup-$Version-x64.exe",
  "dist\EL-Bot-Portable-$Version-x64.exe",
  'dist\package-smoke.json',
  'dist\phase6-package-forgey-proof.json',
  'dist\phase6-package-vision-el.json',
  'dist\phase6-package-vision-abc.json',
  'data\phase6-step3\runtime-package-manifest.json',
  'proof\phase5\hourglass-30fps.mp4',
  'proof\phase5\hourglass-contact-sheet.png',
  'proof\phase5\ui-idle.png',
  'proof\phase5\ui-warning.png',
  'proof\phase5\preview-zoom.png',
  'proof\phase5\proof.json'
)
foreach ($path in $required) { if (-not (Test-Path -LiteralPath $path)) { throw "Phase-6 release asset missing: $path" } }

$forgeyProof = Get-Content -LiteralPath 'dist\phase6-package-forgey-proof.json' -Raw -Encoding UTF8 | ConvertFrom-Json
if ($forgeyProof.selected_generation -ne 'G2' -or -not $forgeyProof.vision_enabled -or $forgeyProof.vision_parameters -le 0 -or $forgeyProof.native_vision_provider_calls -ne 0) { throw 'Phase-6 multimodal Forgey package proof is not release eligible' }
$manifest = [ordered]@{
  schema_version = 2; phase = 6; step = 5; status = 'VERIFIED_FOR_RELEASE'; version = $Version; commit_sha = $sha; tag = $tag
  generated_utc = [DateTime]::UtcNow.ToString('o'); selected_generation = 'G2'; modalities = @('text','image')
  native_vision = [ordered]@{ enabled = $true; vision_parameters = [int64]$forgeyProof.vision_parameters; provider_calls = [int]$forgeyProof.native_vision_provider_calls; image_to_el_exact = [bool]$forgeyProof.vision_image_to_el.exact; image_to_abc_exact = [bool]$forgeyProof.vision_image_to_abc.exact }
  trainable_parameters = [int64]$forgeyProof.trainable_parameters; embedded_python = '3.12.10'; embedded_torch = '2.13.0'; assets = @()
}
foreach ($path in $required) {
  $item = Get-Item -LiteralPath $path
  $manifest.assets += [ordered]@{ source_path = $path; name = $item.Name; bytes = $item.Length; sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
}
$manifestPath = 'dist\phase6-release-manifest.json'
$manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
$uploadPaths = @($required) + @($manifestPath)

$release = New-OrGetRelease $tag $sha "EL Bot v$Version - Phase 6 Multimodal Forgey Insta ($short)" "Phase 6 certified Windows release for commit $sha. Normal install flow: download EL-Bot-Setup-$Version-x64.exe and run the NSIS setup wizard. A portable x64 EXE is also included. Embedded Python 3.12.10 and PyTorch 2.13 CPU, verified G1/G2 Forgey artifacts, provider-free text and native image inference proof, 44/44 diagnostics, and retained Phase-5 rendered visual proof are included."
$releaseId = [int64](Get-FirstScalar $release.id)
$releaseTarget = [string](Get-FirstScalar $release.target_commitish)
if ($releaseTarget -and $releaseTarget -ne $sha) { throw 'existing Phase-6 release target SHA mismatch' }
$uploadBase = ([string](Get-FirstScalar $release.upload_url)).Split('{')[0]
if (-not $uploadBase) { throw 'release upload URL missing' }
foreach ($path in $uploadPaths) { Ensure-ReleaseAsset $releaseId $uploadBase $path }

$verified = @(Get-ReleaseAssets $releaseId)
$names = @($verified | ForEach-Object { [string](Get-FirstScalar $_.name) })
foreach ($path in $uploadPaths) {
  $name = (Get-Item -LiteralPath $path).Name
  if ($names -notcontains $name) { throw "Phase-6 release verification missing asset: $name" }
}
if ($names.Count -ne $uploadPaths.Count) { throw "Phase-6 release must contain exactly $($uploadPaths.Count) uploaded assets, found $($names.Count)" }
$releaseCheck = Get-ReleaseByTag $tag
$releaseCheckTag = [string](Get-FirstScalar $releaseCheck.tag_name)
$releaseCheckTarget = [string](Get-FirstScalar $releaseCheck.target_commitish)
if (-not $releaseCheck -or $releaseCheckTag -ne $tag) { throw 'Phase-6 release re-read failed' }
if ($releaseCheckTarget -ne $sha) { throw 'Phase-6 release re-read target SHA mismatch' }

# Only after both keepers are verified, remove every other release and its release tag.
$historyBeforeFinal = @(Get-AllReleases)
foreach ($old in $historyBeforeFinal) {
  $oldId = [int64](Get-FirstScalar $old.id)
  if ($oldId -in @($phase5KeeperId, $releaseId)) { continue }
  Remove-ReleaseAndTag $old
}

# Absolute final invariant requested by the project: exactly two releases total.
$finalHistory = @(Get-AllReleases)
$finalPhase5 = @($finalHistory | Where-Object { [string](Get-FirstScalar $_.tag_name) -like 'el-bot-v0.5.0-*' })
$finalPhase6 = @($finalHistory | Where-Object { [string](Get-FirstScalar $_.tag_name) -like "el-bot-v$Version-*" })
if ($finalHistory.Count -ne 2) { throw "Release-history cleanup failed: expected exactly 2 total releases, found $($finalHistory.Count)" }
if ($finalPhase5.Count -ne 1) { throw "Release-history cleanup failed: expected exactly 1 v0.5.0 release, found $($finalPhase5.Count)" }
if ($finalPhase6.Count -ne 1) { throw "Release-history cleanup failed: expected exactly 1 v$Version release, found $($finalPhase6.Count)" }
$finalPhase6Tag = [string](Get-FirstScalar $finalPhase6[0].tag_name)
if ($finalPhase6Tag -ne $tag) { throw "Release-history cleanup failed: expected current v$Version release $tag, found $finalPhase6Tag" }
$finalPhase5Tag = [string](Get-FirstScalar $finalPhase5[0].tag_name)
if (-not (Test-Phase5ReleaseEligible $finalPhase5[0])) { throw "Final v0.5.0 release is not installable: $finalPhase5Tag" }
$releaseUrl = [string](Get-FirstScalar $release.html_url)

$evidence = [ordered]@{
  schema_version = 3; phase = 6; step = 5; release_id = $releaseId; tag = $tag; commit_sha = $sha; target_commitish = $releaseCheckTarget; url = $releaseUrl
  modalities = @('text','image'); native_vision = $true; verified_assets = $names; phase5_keeper_tag = $finalPhase5Tag
  release_history = 'total=2;v0.5.0=1;v0.6.0=1'
}
$evidence | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath 'dist\phase6-release-evidence.json' -Encoding UTF8
Write-Output "PHASE6_RELEASE_OK tag=$tag sha=$sha native_vision=PASS assets=$($names.Count) phase5_keeper=$finalPhase5Tag release_history=2 url=$releaseUrl"
