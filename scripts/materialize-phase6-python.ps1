param(
  [string]$PythonVersion = '3.12.10'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$baseScript = Join-Path $PSScriptRoot 'materialize-python.ps1'
if (-not (Test-Path -LiteralPath $baseScript)) { throw 'Phase-5 Python materializer missing' }

powershell -NoProfile -ExecutionPolicy Bypass -File $baseScript -Version $PythonVersion
if ($LASTEXITCODE -ne 0) { throw 'embedded Python materialization failed' }

$pythonDir = Join-Path $root 'python'
$pythonExe = Join-Path $pythonDir 'python.exe'
$site = Join-Path $pythonDir 'site-packages'
$pth = Join-Path $pythonDir 'python312._pth'
$ready = Join-Path $pythonDir '.phase6-torch-ready'
$requirements = Join-Path $root 'requirements-phase6-step2.txt'
if (-not (Test-Path -LiteralPath $requirements)) { throw 'Phase-6 Torch requirements missing' }

$needsInstall = $true
if (Test-Path -LiteralPath $ready) {
  try {
    & $pythonExe -c "import torch; assert torch.__version__.startswith('2.13.0'); print(torch.__version__)"
    if ($LASTEXITCODE -eq 0) { $needsInstall = $false }
  } catch {}
}

if ($needsInstall) {
  if (Test-Path -LiteralPath $site) { Remove-Item -LiteralPath $site -Recurse -Force }
  New-Item -ItemType Directory -Force -Path $site | Out-Null
  $pipDir = Join-Path $env:TEMP 'el-bot-phase6-pip'
  $pipz = Join-Path $pipDir 'pip.pyz'
  New-Item -ItemType Directory -Force -Path $pipDir | Out-Null
  if (-not (Test-Path -LiteralPath $pipz)) {
    Invoke-WebRequest -UseBasicParsing -Uri 'https://bootstrap.pypa.io/pip/pip.pyz' -OutFile $pipz
  }
  & $pythonExe $pipz install --disable-pip-version-check --only-binary=:all: --upgrade --target $site -r $requirements
  if ($LASTEXITCODE -ne 0) { throw 'Phase-6 embedded Torch install failed' }
}

if (-not (Test-Path -LiteralPath $pth)) { throw 'embedded Python path file missing' }
$lines = @(Get-Content -LiteralPath $pth | Where-Object { $_ -and $_ -notmatch '^site-packages$' -and $_ -notmatch '^#?import site$' })
$lines += 'site-packages'
$lines += 'import site'
[IO.File]::WriteAllLines($pth, $lines, [Text.UTF8Encoding]::new($false))

& $pythonExe -c "import sys,torch; assert sys.version_info[:2]==(3,12); assert torch.__version__.startswith('2.13.0'); print(sys.version.split()[0], torch.__version__)"
if ($LASTEXITCODE -ne 0) { throw 'Phase-6 embedded Python/Torch verification failed' }
Set-Content -LiteralPath $ready -Value 'python=3.12.10;torch=2.13.0' -Encoding ASCII
Write-Output 'PHASE6_STEP5_PYTHON_TORCH_OK python=3.12.10 torch=2.13.0'
