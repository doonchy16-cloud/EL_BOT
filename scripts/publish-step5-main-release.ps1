param(
  [string]$Version = '0.6.0'
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
$headers = @{
  Authorization = "Bearer $($env:GITHUB_TOKEN)"
  Accept = 'application/vnd.github+json'
  'X-GitHub-Api-Version' = '2022-11-28'
}

$required = @(
  "dist\EL-Bot-Setup-$Version-x64.exe",
  "dist\EL-Bot-Portable-$Version-x64.exe",
  'dist\package-smoke.json',
  'dist\phase6-package-forgey-proof.json',
  'data\phase6-step3\runtime-package-manifest.json',
  'proof\phase5\hourglass-30fps.mp4',
  'proof\phase5\hourglass-contact-sheet.png',
  'proof\phase5\ui-idle.png',
  'proof\phase5\ui-warning.png',
  'proof\phase5\preview-zoom.png',
  'proof\phase5\proof.json'
)
foreach ($path in $required) {
  if (-not (Test-Path -LiteralPath $path)) { throw "Phase-6 release asset missing: $path" }
}

$manifest = [ordered]@{
  schema_version = 1
  phase = 6
  step = 5
  status = 'VERIFIED_FOR_RELEASE'
  version = $Version
  commit_sha = $sha
  tag = $tag
  generated_utc = [DateTime]::UtcNow.ToString('o')
  selected_generation = 'G2'
  embedded_python = '3.12.10'
  embedded_torch = '2.13.0'
  assets = @()
}
foreach ($path in $required) {
  $item = Get-Item -LiteralPath $path
  $manifest.assets += [ordered]@{
    source_path = $path
    name = $item.Name
    bytes = $item.Length
    sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
  }
}
$manifestPath = 'dist\phase6-release-manifest.json'
$manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
$uploadPaths = @($required) + @($manifestPath)

$release = $null
try {
  $release = Invoke-RestMethod -Method Get -Uri "$api/repos/$repo/releases/tags/$tag" -Headers $headers
} catch {
  $status = $_.Exception.Response.StatusCode.value__
  if ($status -ne 404) { throw }
}

if (-not $release) {
  $body = @{
    tag_name = $tag
    target_commitish = $sha
    name = "EL Bot v$Version - Phase 6 Forgey Insta ($short)"
    body = "Phase 6 exact-main Windows release for commit $sha. Includes Setup + Portable x64, embedded Python 3.12.10, embedded PyTorch 2.13 CPU, portable verified G1/G2 Forgey artifacts, packaged-runtime smoke evidence, packaged G2 provider-free inference proof, 44/44 diagnostics, and retained Phase-5 rendered visual proof."
    draft = $false
    prerelease = $false
  } | ConvertTo-Json -Depth 4
  $release = Invoke-RestMethod -Method Post -Uri "$api/repos/$repo/releases" -Headers $headers -ContentType 'application/json' -Body $body
}

if (-not $release.id) { throw 'Phase-6 release id missing' }
if ([string]$release.target_commitish -and [string]$release.target_commitish -ne $sha) { throw 'existing Phase-6 release target SHA mismatch' }
$uploadBase = ([string]$release.upload_url).Split('{')[0]
if (-not $uploadBase) { throw 'release upload URL missing' }

$existing = @(Invoke-RestMethod -Method Get -Uri "$api/repos/$repo/releases/$($release.id)/assets?per_page=100" -Headers $headers)
foreach ($path in $uploadPaths) {
  $item = Get-Item -LiteralPath $path
  $name = $item.Name
  foreach ($asset in @($existing | Where-Object { $_.name -eq $name })) {
    Invoke-RestMethod -Method Delete -Uri "$api/repos/$repo/releases/assets/$($asset.id)" -Headers $headers | Out-Null
  }
  $encodedName = [Uri]::EscapeDataString($name)
  Invoke-RestMethod -Method Post -Uri "${uploadBase}?name=$encodedName" -Headers $headers -ContentType 'application/octet-stream' -InFile $item.FullName | Out-Null
}

$verified = @(Invoke-RestMethod -Method Get -Uri "$api/repos/$repo/releases/$($release.id)/assets?per_page=100" -Headers $headers)
$names = @($verified | ForEach-Object { $_.name })
foreach ($path in $uploadPaths) {
  $name = (Get-Item -LiteralPath $path).Name
  if ($names -notcontains $name) { throw "Phase-6 release verification missing asset: $name" }
}

$releaseCheck = Invoke-RestMethod -Method Get -Uri "$api/repos/$repo/releases/tags/$tag" -Headers $headers
if (-not $releaseCheck -or [string]$releaseCheck.tag_name -ne $tag) { throw 'Phase-6 release re-read failed' }
$evidence = [ordered]@{
  schema_version = 1
  phase = 6
  step = 5
  release_id = $release.id
  tag = $tag
  commit_sha = $sha
  target_commitish = $releaseCheck.target_commitish
  url = $release.html_url
  verified_assets = $names
}
$evidence | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath 'dist\phase6-release-evidence.json' -Encoding UTF8
Write-Output "PHASE6_RELEASE_OK tag=$tag sha=$sha url=$($release.html_url)"
