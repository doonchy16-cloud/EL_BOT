param(
  [string]$Version = '0.6.0'
)
$ErrorActionPreference = 'Stop'

if (-not $env:GITHUB_REPOSITORY) { throw 'GITHUB_REPOSITORY missing' }
if (-not $env:GITHUB_SHA) { throw 'GITHUB_SHA missing' }
if (-not $env:GITHUB_TOKEN) { throw 'GITHUB_TOKEN missing' }

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
  'data\phase6-data-manifest.json',
  'THIRD-PARTY-DATA-NOTICES.txt',
  'proof\phase5\hourglass-30fps.mp4',
  'proof\phase5\hourglass-contact-sheet.png',
  'proof\phase5\ui-idle.png',
  'proof\phase5\ui-warning.png',
  'proof\phase5\preview-zoom.png',
  'proof\phase5\proof.json'
)
foreach ($path in $required) {
  if (-not (Test-Path -LiteralPath $path)) { throw "release asset missing: $path" }
}

$data = Get-Content -LiteralPath 'data\phase6-data-manifest.json' -Raw -Encoding UTF8 | ConvertFrom-Json
if ($data.unicode_emoji_version -ne '17.0' -or [int]$data.unicode_rgi_count -lt 3000 -or $data.oewn_edition -ne '2025') {
  throw 'Phase-6 data manifest is not release-authorized'
}

$manifest = [ordered]@{
  schema_version = 1
  phase = 6
  status = 'VERIFIED_FOR_RELEASE'
  version = $Version
  commit_sha = $sha
  tag = $tag
  unicode_emoji_version = $data.unicode_emoji_version
  unicode_emoji_count = [int]$data.unicode_rgi_count
  oewn_edition = $data.oewn_edition
  generated_utc = [DateTime]::UtcNow.ToString('o')
  assets = @()
}
foreach ($path in $required) {
  $item = Get-Item -LiteralPath $path
  $manifest.assets += [ordered]@{
    name = $item.Name
    bytes = $item.Length
    sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
  }
}
$manifestPath = 'dist\phase6-release-manifest.json'
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
$required += $manifestPath

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
    name = "EL Bot v$Version - Phase 6 ($short)"
    body = "Phase 6 lexical-coverage Windows release for exact commit $sha. Includes Setup + Portable, packaged-runtime smoke evidence, Unicode/OEWN data authority evidence, third-party data notices, and retained Phase-5 rendered visual proof."
    draft = $false
    prerelease = $false
  } | ConvertTo-Json -Depth 4
  $release = Invoke-RestMethod -Method Post -Uri "$api/repos/$repo/releases" -Headers $headers -ContentType 'application/json' -Body $body
}

if (-not $release.id) { throw 'release id missing' }
$uploadBase = ([string]$release.upload_url).Split('{')[0]
if (-not $uploadBase) { throw 'release upload URL missing' }

$existing = @(Invoke-RestMethod -Method Get -Uri "$api/repos/$repo/releases/$($release.id)/assets?per_page=100" -Headers $headers)
foreach ($path in $required) {
  $item = Get-Item -LiteralPath $path
  $name = $item.Name
  foreach ($asset in @($existing | Where-Object { $_.name -eq $name })) {
    Invoke-RestMethod -Method Delete -Uri "$api/repos/$repo/releases/assets/$($asset.id)" -Headers $headers | Out-Null
  }
  $encodedName = [Uri]::EscapeDataString($name)
  $uploadUri = "${uploadBase}?name=$encodedName"
  Invoke-RestMethod -Method Post -Uri $uploadUri -Headers $headers -ContentType 'application/octet-stream' -InFile $item.FullName | Out-Null
}

$verified = @(Invoke-RestMethod -Method Get -Uri "$api/repos/$repo/releases/$($release.id)/assets?per_page=100" -Headers $headers)
$names = @($verified | ForEach-Object { $_.name })
foreach ($path in $required) {
  $name = (Get-Item -LiteralPath $path).Name
  if ($names -notcontains $name) { throw "release verification missing asset: $name" }
}

$evidence = [ordered]@{
  release_id = $release.id
  tag = $tag
  commit_sha = $sha
  url = $release.html_url
  unicode_emoji_count = [int]$data.unicode_rgi_count
  oewn_edition = $data.oewn_edition
  verified_assets = $names
}
$evidence | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath 'dist\release-evidence.json' -Encoding UTF8
Write-Output "PHASE6_RELEASE_OK $($release.html_url)"
