@echo off
setlocal
cd /d "%~dp0"
py -m pip install -e ".[test]"
if errorlevel 1 exit /b %errorlevel%
py -m pytest -q
pause
