@echo off
setlocal
title Admissions Assistant Backend
cd /d "%~dp0"

echo ========================================
echo   Admissions Assistant Backend
echo ========================================
echo.

set "PY_CMD="
where py.exe >nul 2>nul
if not errorlevel 1 set "PY_CMD=py"
if defined PY_CMD goto :python_found

where python.exe >nul 2>nul
if not errorlevel 1 set "PY_CMD=python"
if defined PY_CMD goto :python_found

echo [ERROR] Python was not found.
echo Install Python 3.11 or 3.12 from https://www.python.org/downloads/
echo Select "Add python.exe to PATH" during installation.
echo Restart VS Code after installation, then run this file again.
echo.
pause
exit /b 1

:python_found
echo Python launcher: %PY_CMD%
%PY_CMD% --version
if errorlevel 1 goto :python_failed

if not exist ".venv\Scripts\python.exe" (
  echo [1/4] Creating the virtual environment...
  %PY_CMD% -m venv .venv
  if errorlevel 1 goto :python_failed
)

echo [2/4] Installing dependencies. The first run may take several minutes...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

if not exist ".env" copy ".env.example" ".env" >nul

echo [3/4] Initializing the database...
".venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 goto :failed

echo [4/4] Starting the server...
echo Open http://127.0.0.1:8001/docs after startup.
echo Press Ctrl+C to stop the server.
echo.
".venv\Scripts\python.exe" -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001
exit /b 0

:python_failed
echo.
echo [ERROR] Python is present but could not create a Windows virtual environment.
echo Please install the official Python 3.11 or 3.12 Windows version.
goto :failed_pause

:failed
echo.
echo [ERROR] Backend startup failed. Keep this window open and capture the error above.

:failed_pause
pause
exit /b 1
