@echo off
title BLACKCORE Launcher
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0blackcore.py"
  if not errorlevel 1 goto end
)
where python >nul 2>nul
if %errorlevel%==0 (
  python "%~dp0blackcore.py"
  goto end
)
echo.
echo Python nao foi encontrado no PATH.
echo Instale Python 3 pelo site oficial e marque "Add python.exe to PATH".
echo https://www.python.org/downloads/windows/
echo.
pause
:end
if errorlevel 1 pause
