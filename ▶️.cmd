@echo off
setlocal
cd /d "%~dp0"

where powershell >nul 2>&1
if errorlevel 1 (
  echo PowerShell is required to launch EL Bot.
  pause
  exit /b 1
)

where npx >nul 2>&1
if errorlevel 1 (
  echo Node.js and npm are required to launch EL Bot.
  echo Install Node.js, then double-click this launcher again.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $root=(Get-Location); $spark=[char]::ConvertFromUtf32(0x26A1); $entry=Join-Path (Join-Path $root $spark) $spark; if(-not (Test-Path -LiteralPath $entry)){exit 3}; $local=Join-Path $root 'node_modules\.bin\electron.cmd'; if(Test-Path -LiteralPath $local){ & $local $entry } else { $npx=(Get-Command npx.cmd -ErrorAction Stop).Source; & $npx -y electron@43.2.0 $entry }; exit $LASTEXITCODE"
set "code=%errorlevel%"
if not "%code%"=="0" (
  echo.
  echo EL Bot did not launch successfully. Exit code: %code%
  pause
  exit /b %code%
)

endlocal
