@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Please run start-backend.bat first.
  pause
  exit /b 1
)

echo ========================================
echo   Admissions API Smoke Tests
echo ========================================
echo.
".venv\Scripts\python.exe" -m backend.smoke_test
echo.
pause
