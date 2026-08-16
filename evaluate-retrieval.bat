@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Please run start-backend.bat first.
  pause
  exit /b 1
)

echo ========================================
echo   Admissions Retrieval Evaluation
echo ========================================
echo.
".venv\Scripts\python.exe" -m backend.evaluate_retrieval
echo.
pause
