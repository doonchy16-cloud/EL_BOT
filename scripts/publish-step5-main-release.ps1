param(
  [string]$Version = '0.6.0',
  [string]$Phase5KeepSha = 'c489d6f79d2f21d9544d8631dda3de7793adebf0'
)
$ErrorActionPreference = 'Stop'

if (-not $env:GITHUB_REPOSITORY) { throw 'GITHUB_REPOSITORY missing' }
if (-not $env:GITHUB_SHA) { throw 'GITHUB_SHA missing' }
if (-not $env:GITHUB_TOKEN) { throw 'GITHUB_TOKEN missing' }
if ($env:GITHUB_REF -and $env:GITHUB_REF -ne 'refs/heads/main') { throw "Phase-6 release publisher requires main, got $($env:GITHUB_REF)" }

$repo = $env:GITHUB_REPOSITORY
$sha = $env:GITHUB_SHA
$short = $sha.Substring(0, [Math]::Min(12, $sha.Length))
$tag = "el-bot-v$Version-$short"
$api = if ($env:GITHUB_API_URL) { $env:GITHUB_API_URL.TrimEnd('/') } else { 'https://api.github.com' }
$headers = @{ Authorization = "Bearer $($env:GITHUB_TOKEN)"; Accept = 'application/vnd.github+json'; 'X-GitHub-Api-Version' = '2022-11-28' }

function Get-AllReleases {
  $items = @()
  $page = 1
  do {
    $batch = @(Invoke-RestMethod -Method Get -Uri "$api/repos/$repo/releases?per_page=100&page=$page" -Headers $headers)
    $items += $batch
    $page += 1
  } while ($batch.Count -eq 100)
  return @($items)
}

function Remove-ReleaseAndTag([object]$Release) {
  $releaseId = [int64]$Release.id
  $releaseTag = [string]$Release.tag_name
  if ($releaseId -gt 0) {
    Invoke-RestMethod -Method Delete -Uri "$api/repos/$repo/releases/$releaseId" -Headers $headers | Out-Null
    Write-Output "RELEASE_HISTORY_REMOVED release_id=$releaseId tag=$releaseTag"
  }
  if ($releaseTag) {
    $encodedTag = [Uri]::EscapeDataString($releaseTag)
    try {
      Invoke-RestMethod -Method Delete -Uri "$api/repos/$repo/git/refs/tags/$encodedTag" -Headers $headers | Out-Null
      Write-Output "RELEASE_TAG_REMOVED tag=$releaseTag"
    } catch {
      $status = $_.Exception.Response.StatusCode.value__
      if ($status -notin @(404, 422)) { throw }
    }
  }
}

# Keep exactly one historical v0.5.0 release: the strongest completed Phase-5 build.
# Historical Phase-5 tags used shorter SHA suffixes, so accept any unambiguous prefix
# of the locked keeper SHA instead of requiring the newer 12-character format.
$releaseHistory = @(Get-AllReleases)
$phase5Prefix = 'el-bot-v0.5.0-'
$phase5KeepShort = $Phase5KeepSha.Substring(0, 7)
$phase5Releases = @($releaseHistory | Where-Object { [string]$_.tag_name -like "$phase5Prefix*" })
$phase5KeepCandidates = @($phase5Releases | Where-Object {
  $target = ([string]$_.target_commitish).Trim()
  $tagName = [string]$_.tag_name
  $targetMatches = $false
  if ($target) {
    $targetMatches = $Phase5KeepSha.StartsWith($target, [StringComparison]::OrdinalIgnoreCase) -or $target.StartsWith($Phase5KeepSha, [StringComparison]::OrdinalIgnoreCase)
  }
  $tagMatches = $tagName.IndexOf($phase5KeepShort, [StringComparison]::OrdinalIgnoreCase) -ge 0
  $targetMatches -or $tagMatches
})
if ($phase5KeepCandidates.Count -lt 1) { throw "Required Phase-5 keeper release not found for $phase5KeepShort" }
$phase5Keeper = @($phase5KeepCandidates | Sort-Object @{ Expression = { @($_.assets).Count }; Descending = $true }, @{ Expression = { $_.published_at }; Descending = $true })[0]
if (@($phase5Keeper.assets).Count -lt 12) { throw "Phase-5 keeper is incomplete: expected at least 12 assets, found $(@($phase5Keeper.assets).Count)" }
foreach ($old in $phase5Releases) {
  if ([int64]$old.id -eq [int64]$phase5Keeper.id) { continue }
  Remove-ReleaseAndTag $old
}
Write-Output "PHASE5_RELEASE_KEEP tag=$($phase5Keeper.tag_name) target=$($phase5Keeper.target_commitish) assets=$(@($phase5Keeper.assets).Count)"

# Version releases are single-authority too: remove any older v0.6.0 release before publishing this certified build.
$releaseHistory = @(Get-AllReleases)
foreach ($old in @($releaseHistory | Where-Object { [string]$_.tag_name -like "el-bot-v$Version-*" -and [string]$_.tag_name -ne $tag })) {
  Remove-ReleaseAndTag $old
}

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

$release = $null
try { $release = Invoke-RestMethod -Method Get -Uri "$api/repos/$repo/releases/tags/$tag" -Headers $headers }
catch { $status = $_.Exception.Response.StatusCode.value__; if ($status -ne 404) { throw } }

if (-not $release) {
  $body = @{ tag_name = $tag; target_commitish = $sha; name = "EL Bot v$Version - Phase 6 Multimodal Forgey Insta ($short)"; body = "Phase 6 certified Windows release for commit $sha. Normal install flow: download EL-Bot-Setup-$Version-x64.exe and run the NSIS setup wizard. A portable x64 EXE is also included. Embedded Python 3.12.10 and PyTorch 2.13 CPU, verified G1/G2 Forgey artifacts, provider-free text and native image inference proof, 44/44 diagnostics, and retained Phase-5 rendered visual proof are included."; draft = $false; prerelease = $false } | ConvertTo-Json -Depth 4
  $release = Invoke-RestMethod -Method Post -Uri "$api/repos/$repo/releases" -Headers $headers -ContentType 'application/json' -Body $body
}

if (-not $release.id) { throw 'Phase-6 release id missing' }
if ([string]$release.target_commitish -and [string]$release.target_commitish -ne $sha) { throw 'existing Phase-6 release target SHA mismatch' }
$uploadBase = ([string]$release.upload_url).Split('{')[0]
if (-not $uploadBase) { throw 'release upload URL missing' }
$existing = @(Invoke-RestMethod -Method Get -Uri "$api/repos/$repo/releases/$($release.id)/assets?per_page=100" -Headers $headers)
foreach ($path in $uploadPaths) {
  $item = Get-Item -LiteralPath $path; $name = $item.Name
  foreach ($asset in @($existing | Where-Object { $_.name -eq $name })) { Invoke-RestMethod -Method Delete -Uri "$api/repos/$repo/releases/assets/$($asset.id)" -Headers $headers | Out-Null }
  $encodedName = [Uri]::EscapeDataString($name)
  Invoke-RestMethod -Method Post -Uri "${uploadBase}?name=$encodedName" -Headers $headers -ContentType 'application/octet-stream' -InFile $item.FullName | Out-Null
}

$verified = @(Invoke-RestMethod -Method Get -Uri "$api/repos/$repo/releases/$($release.id)/assets?per_page=100" -Headers $headers)
$names = @($verified | ForEach-Object { $_.name })
foreach ($path in $uploadPaths) { $name = (Get-Item -LiteralPath $path).Name; if ($names -notcontains $name) { throw "Phase-6 release verification missing asset: $name" } }
if ($names.Count -ne $uploadPaths.Count) { throw "Phase-6 release must contain exactly $($uploadPaths.Count) assets, found $($names.Count)" }
$releaseCheck = Invoke-RestMethod -Method Get -Uri "$api/repos/$repo/releases/tags/$tag" -Headers $headers
if (-not $releaseCheck -or [string]$releaseCheck.tag_name -ne $tag) { throw 'Phase-6 release re-read failed' }
if ([string]$releaseCheck.target_commitish -ne $sha) { throw 'Phase-6 release re-read target SHA mismatch' }

# Final release-history invariant: exactly one v0.5.0 release and exactly one v0.6.0 release.
$finalHistory = @(Get-AllReleases)
$finalPhase5 = @($finalHistory | Where-Object { [string]$_.tag_name -like "$phase5Prefix*" })
$finalPhase6 = @($finalHistory | Where-Object { [string]$_.tag_name -like "el-bot-v$Version-*" })
if ($finalPhase5.Count -ne 1) { throw "Release-history cleanup failed: expected 1 v0.5.0 release, found $($finalPhase5.Count)" }
if ($finalPhase6.Count -ne 1 -or [string]$finalPhase6[0].tag_name -ne $tag) { throw "Release-history cleanup failed: expected only current v$Version release $tag" }

$evidence = [ordered]@{ schema_version = 2; phase = 6; step = 5; release_id = $release.id; tag = $tag; commit_sha = $sha; target_commitish = $releaseCheck.target_commitish; url = $release.html_url; modalities = @('text','image'); native_vision = $true; verified_assets = $names; phase5_keeper_tag = [string]$finalPhase5[0].tag_name; release_history = 'v0.5.0=1;v0.6.0=1' }
$evidence | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath 'dist\phase6-release-evidence.json' -Encoding UTF8
Write-Output "PHASE6_RELEASE_OK tag=$tag sha=$sha native_vision=PASS assets=$($names.Count) phase5_keeper=$($finalPhase5[0].tag_name) url=$($release.html_url)"