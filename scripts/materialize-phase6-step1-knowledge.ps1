param(
  [switch]$Force
)
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$data = Join-Path $root 'data'
$unicodeDir = Join-Path $data 'unicode'
$oewnDir = Join-Path $data 'oewn'
New-Item -ItemType Directory -Force -Path $unicodeDir,$oewnDir | Out-Null

function Get-ContentHash([string]$Path) {
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Count-WordNetIndexRecords([string]$Path) {
  $count = 0
  foreach ($line in [System.IO.File]::ReadLines($Path)) {
    if ($line -and -not [char]::IsWhiteSpace($line[0])) { $count++ }
  }
  return $count
}

# Unicode Emoji: always use the current RELEASED Phase-6 authority, never beta data.
$emojiVersion = '17.0'
$emojiUrl = 'https://www.unicode.org/Public/17.0.0/emoji/emoji-test.txt'
$emojiPath = Join-Path $unicodeDir 'emoji-test.txt'
if ($Force -or -not (Test-Path -LiteralPath $emojiPath)) {
  Invoke-WebRequest -UseBasicParsing -Uri $emojiUrl -OutFile $emojiPath
}
$emojiRaw = Get-Content -LiteralPath $emojiPath -Raw -Encoding UTF8
if (-not $emojiRaw.Contains('# Version: 17.0')) { throw 'Unicode emoji-test version mismatch' }
$rgiCount = 0
$fullyQualified = 0
$componentCount = 0
foreach ($line in [System.IO.File]::ReadLines($emojiPath)) {
  if ($line -match ';\s*fully-qualified\s+#') { $fullyQualified++; $rgiCount++ }
  elseif ($line -match ';\s*component\s+#') { $componentCount++; $rgiCount++ }
}
if ($rgiCount -lt 3000) { throw "Unicode RGI inventory unexpectedly small: $rgiCount" }

# Open English WordNet 2025+ maximizes the released 2025 lexical coverage by adding
# the curated Namenet proper-name extension while retaining the same WNDB contract.
$oewnEdition = '2025+'
$oewnUrl = 'https://en-word.net/static/english-wordnet-2025-plus.zip'
$oewnZip = Join-Path $oewnDir 'english-wordnet-2025-plus.zip'
$readyMarker = Join-Path $oewnDir '.ready-2025-plus'
if ($Force -or -not (Test-Path -LiteralPath $readyMarker)) {
  if ($Force -or -not (Test-Path -LiteralPath $oewnZip)) {
    Invoke-WebRequest -UseBasicParsing -Uri $oewnUrl -OutFile $oewnZip
  }
  Get-ChildItem -LiteralPath $oewnDir -Force | Where-Object { $_.Name -ne 'english-wordnet-2025-plus.zip' } | Remove-Item -Recurse -Force
  Expand-Archive -LiteralPath $oewnZip -DestinationPath $oewnDir -Force
}

$required = @('index.noun','data.noun','index.verb','data.verb','index.adj','data.adj','index.adv','data.adv')
$resolved = @{}
foreach ($name in $required) {
  $found = Get-ChildItem -LiteralPath $oewnDir -Recurse -File -Filter $name | Select-Object -First 1
  if (-not $found) { throw "Open English WordNet missing $name" }
  $resolved[$name] = $found.FullName
}
Set-Content -LiteralPath $readyMarker -Value 'Open English WordNet 2025+ materialized' -Encoding ASCII

# These are raw source index records. Runtime normalized lexical keys are measured
# independently because normalization can intentionally collapse equivalent spellings.
$indexRecordCounts = [ordered]@{
  noun = Count-WordNetIndexRecords $resolved['index.noun']
  verb = Count-WordNetIndexRecords $resolved['index.verb']
  adjective = Count-WordNetIndexRecords $resolved['index.adj']
  adverb = Count-WordNetIndexRecords $resolved['index.adv']
}
$indexRecordTotal = [int]$indexRecordCounts.noun + [int]$indexRecordCounts.verb + [int]$indexRecordCounts.adjective + [int]$indexRecordCounts.adverb
if ($indexRecordTotal -lt 100000) { throw "Open English WordNet index unexpectedly small: $indexRecordTotal" }

$manifest = [ordered]@{
  schema_version = 3
  phase = 6
  step = 1
  status = 'MATERIALIZED'
  generated_utc = [DateTime]::UtcNow.ToString('o')
  unicode = [ordered]@{
    emoji_version = $emojiVersion
    source = $emojiUrl
    rgi_count = $rgiCount
    fully_qualified_count = $fullyQualified
    component_count = $componentCount
    sha256 = Get-ContentHash $emojiPath
  }
  oewn = [ordered]@{
    edition = $oewnEdition
    source = $oewnUrl
    archive_sha256 = Get-ContentHash $oewnZip
    index_record_count = $indexRecordTotal
    index_record_counts = $indexRecordCounts
    runtime_normalized_lexical_keys = 'measured-by-runtime-verifier'
  }
}
$manifestPath = Join-Path $data 'phase6-step1-data-manifest.json'
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
Write-Output "PHASE6_STEP1_DATA_OK emoji=$rgiCount oewn=$oewnEdition index_records=$indexRecordTotal"
