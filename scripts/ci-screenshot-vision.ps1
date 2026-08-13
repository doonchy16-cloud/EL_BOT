param(
  [Parameter(Mandatory=$true)][string]$PythonExe
)
$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
Add-Type -AssemblyName System.Drawing
$png = Join-Path $env:RUNNER_TEMP 'el-vision-fixture.png'
$bmp = New-Object System.Drawing.Bitmap 900,500
$g = [System.Drawing.Graphics]::FromImage($bmp)
try {
  $g.Clear([System.Drawing.Color]::FromArgb(20,24,33))
  $titleFont = New-Object System.Drawing.Font('Segoe UI',34,[System.Drawing.FontStyle]::Bold)
  $bodyFont = New-Object System.Drawing.Font('Segoe UI',25,[System.Drawing.FontStyle]::Regular)
  $buttonFont = New-Object System.Drawing.Font('Segoe UI',23,[System.Drawing.FontStyle]::Bold)
  $white = [System.Drawing.Brushes]::White
  $red = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255,92,105))
  $yellow = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255,209,102))
  $green = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(114,242,166))
  $buttonBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(32,55,85))
  $g.DrawString('SERVER MONITOR', $titleFont, $white, 52, 42)
  $g.DrawString('ERROR: Server offline after 45 seconds', $bodyFont, $red, 52, 132)
  $g.DrawString('Connection failed - recovery required', $bodyFont, $yellow, 52, 198)
  $g.FillRectangle($buttonBrush, 52, 300, 210, 72)
  $g.DrawString('RETRY', $buttonFont, $white, 94, 318)
  $g.DrawString('Diagnostics ready', $bodyFont, $green, 320, 318)
  $bmp.Save($png,[System.Drawing.Imaging.ImageFormat]::Png)
} finally {
  $g.Dispose(); $bmp.Dispose()
  if ($titleFont) { $titleFont.Dispose() }; if ($bodyFont) { $bodyFont.Dispose() }; if ($buttonFont) { $buttonFont.Dispose() }
  if ($red) { $red.Dispose() }; if ($yellow) { $yellow.Dispose() }; if ($green) { $green.Dispose() }; if ($buttonBrush) { $buttonBrush.Dispose() }
}
$env:EL_TEST_IMAGE = 'data:image/png;base64,' + [Convert]::ToBase64String([IO.File]::ReadAllBytes($png))
$script = Join-Path $env:RUNNER_TEMP 'el_vision_boundary_test.py'
@'
import json, os, pathlib, subprocess, sys, unicodedata
camera = chr(0x1F4F8)
vision = next(path for path in pathlib.Path('.').rglob('*') if path.is_file() and path.name == camera and path.parent.name == camera)
source = vision.read_text(encoding='utf-8')
assert 'vision sensor, not a translator' in source
assert 'OllamaConnector' in source and 'ABCToEmojiEngine' in source
assert 'Do not translate into Emoji Language' in source
assert '"visible_text":12' in source and 'vision_evidence' in source
result = subprocess.run([sys.executable, str(vision), chr(0x1F500)], input='2\n'+os.environ['EL_TEST_IMAGE'], text=True, capture_output=True, encoding='utf-8', timeout=360)
raw = result.stdout.strip(); print(raw)
if result.stderr.strip(): print(result.stderr.strip())
assert result.returncode == 0 and raw
payload = json.loads(raw); winner = str(payload.get('winner','')); metrics = payload.get('metrics') or {}
assert winner and not winner.startswith(chr(0x274C))
assert not any(unicodedata.category(ch).startswith('L') for ch in winner)
assert int(metrics.get('sensor_calls',0)) in (1,2)
assert int(metrics.get('vision_facts',0)) >= 1, metrics
assert isinstance(metrics.get('vision_evidence'), dict), metrics
assert str(metrics.get('sensor_state','')) in {'structured-vision','structured-vision-retry','deterministic-structure-repair'}, metrics
assert str(metrics.get('quality_status','')) in {'pass','hold'}, metrics
print(chr(0x2705)+chr(0x1F4F8)+chr(0x1F441)+chr(0xFE0F)+str(metrics.get('vision_facts',0)))
'@ | Set-Content -LiteralPath $script -Encoding UTF8
& $PythonExe $script
