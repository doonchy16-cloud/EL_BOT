param(
  [switch]$Force
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$data = Join-Path $root 'data'
$unicodeDir = Join-Path $data 'unicode'
$oewnDir = Join-Path $data 'oewn'
New-Item -ItemType Directory -Force -Path $unicodeDir,$oewnDir | Out-Null

$emojiUrl = 'https://www.unicode.org/Public/17.0.0/emoji/emoji-test.txt'
$emojiPath = Join-Path $unicodeDir 'emoji-test.txt'
if ($Force -or -not (Test-Path -LiteralPath $emojiPath)) {
  Invoke-WebRequest -UseBasicParsing -Uri $emojiUrl -OutFile $emojiPath
}
$emojiRaw = Get-Content -LiteralPath $emojiPath -Raw -Encoding UTF8
if (-not $emojiRaw.Contains('# Version: 17.0')) { throw 'Unicode emoji-test version mismatch' }
$rgiCount = 0
foreach ($line in (Get-Content -LiteralPath $emojiPath -Encoding UTF8)) {
  if ($line -match ';\s*(fully-qualified|component)\s+#') { $rgiCount++ }
}
if ($rgiCount -lt 3000) { throw "Unicode RGI inventory unexpectedly small: $rgiCount" }

$oewnUrl = 'https://en-word.net/static/english-wordnet-2025.zip'
$oewnZip = Join-Path $oewnDir 'english-wordnet-2025.zip'
$marker = Join-Path $oewnDir '.ready-2025'
if ($Force -or -not (Test-Path -LiteralPath $marker)) {
  if ($Force -or -not (Test-Path -LiteralPath $oewnZip)) {
    Invoke-WebRequest -UseBasicParsing -Uri $oewnUrl -OutFile $oewnZip
  }
  Get-ChildItem -LiteralPath $oewnDir -Force | Where-Object { $_.Name -ne 'english-wordnet-2025.zip' } | Remove-Item -Recurse -Force
  Expand-Archive -LiteralPath $oewnZip -DestinationPath $oewnDir -Force
  $required = @('index.noun','data.noun','index.verb','data.verb','index.adj','data.adj','index.adv','data.adv')
  foreach ($name in $required) {
    $found = Get-ChildItem -LiteralPath $oewnDir -Recurse -File -Filter $name | Select-Object -First 1
    if (-not $found) { throw "Open English WordNet missing $name" }
  }
  Set-Content -LiteralPath $marker -Value 'Open English WordNet 2025 materialized' -Encoding ASCII
}

$manifest = [ordered]@{
  schema_version = 1
  unicode_emoji_version = '17.0'
  unicode_emoji_source = $emojiUrl
  unicode_rgi_count = $rgiCount
  oewn_edition = '2025'
  oewn_source = $oewnUrl
  generated_utc = [DateTime]::UtcNow.ToString('o')
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $data 'phase6-data-manifest.json') -Encoding UTF8
Write-Output "PHASE6_DATA_OK emoji=$rgiCount oewn=2025"
