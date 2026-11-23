@echo off
setlocal
set "PROJECT_ROOT=%~dp0"

if not exist "%PROJECT_ROOT%backend\.venv\Scripts\python.exe" (
  echo Backend virtual environment not found.
  echo Create backend\.venv and install backend\requirements.txt first.
  pause
  exit /b 1
)

if not exist "%PROJECT_ROOT%frontend\node_modules" (
  echo Frontend dependencies not found.
  echo Run npm install in the frontend folder first.
  pause
  exit /b 1
)

start "ProjectResearch Backend" /D "%PROJECT_ROOT%backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --reload"
start "ProjectResearch Frontend" /D "%PROJECT_ROOT%frontend" cmd /k "npm run dev -- --host 127.0.0.1"

echo ProjectResearch backend and frontend are starting.
echo Frontend: http://127.0.0.1:5173
echo Backend:  http://127.0.0.1:8000

endlocal
