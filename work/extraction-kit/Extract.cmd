@echo off
setlocal
"%~dp0runtime\python.exe" -B -X utf8 "%~dp0kit.py" %*
set "kitExit=%errorlevel%"
if "%~1"=="" pause
exit /b %kitExit%
