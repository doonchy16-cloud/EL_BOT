param(
  [string]$Version = '3.12.10'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$target = Join-Path $root 'python'
$exe = Join-Path $target 'python.exe'
if (Test-Path -LiteralPath $exe) {
  & $exe -c "import sys; assert sys.version_info[:2] == (3, 12)"
  Write-Output '✅🐍📦'
  exit 0
}
$zip = Join-Path $env:TEMP ("el-bot-python-$Version.zip")
$url = "https://www.python.org/ftp/python/$Version/python-$Version-embed-amd64.zip"
if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
New-Item -ItemType Directory -Path $target -Force | Out-Null
Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $zip
Expand-Archive -LiteralPath $zip -DestinationPath $target -Force
Remove-Item -LiteralPath $zip -Force -ErrorAction SilentlyContinue
& $exe -c "import sys; assert sys.version_info[:2] == (3, 12)"
Write-Output '✅🐍📦'
