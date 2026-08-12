@echo off
setlocal
cd /d "%~dp0"

where npx >nul 2>&1
if errorlevel 1 (
  echo Node.js and npm are required to launch EL Bot.
  echo Install Node.js, then double-click this launcher again.
  pause
  exit /b 1
)

call npx -y electron@latest ".\⚡\⚡"
if errorlevel 1 (
  echo.
  echo EL Bot did not launch successfully.
  pause
  exit /b 1
)

endlocal
