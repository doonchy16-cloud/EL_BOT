param(
  [string]$Version = '0.5.0'
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
foreach ($path in $required) {
  if (-not (Test-Path -LiteralPath $path)) { throw "release asset missing: $path" }
}

$manifest = [ordered]@{
  schema_version = 1
  phase = 5
  status = 'VERIFIED_FOR_RELEASE'
  version = $Version
  commit_sha = $sha
  tag = $tag
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
$manifestPath = 'dist\phase5-release-manifest.json'
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
    name = "EL Bot v$Version — Phase 5 ($short)"
    body = "Phase 5 Windows release for exact commit $sha. Includes NSIS installer, portable EXE, packaged-runtime smoke evidence, and real rendered 30 FPS visual proof."
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
  verified_assets = $names
}
$evidence | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath 'dist\release-evidence.json' -Encoding UTF8
Write-Output "✅📤9️⃣📦🪟 $($release.html_url)"
