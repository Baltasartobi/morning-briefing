@echo off
chcp 65001 >nul
title Morning Briefing - dieses Fenster offen lassen
cd /d "%~dp0"
set PYTHONDONTWRITEBYTECODE=1
set PYTHONIOENCODING=utf-8

set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=py"

"%PY%" app.py
if errorlevel 1 (
  echo.
  echo Es ist ein Fehler aufgetreten. Details siehe oben.
  pause
)
