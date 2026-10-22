@echo off
REM MineGuard AI - Phase 1 - startup script (Windows)
REM Usage:
REM   start.bat            start with no camera pre-selected
REM   start.bat webcam      start backend with webcam pre-opened

cd /d "%~dp0"

echo == MineGuard AI: starting backend ==
cd backend
if not exist ".venv" (
    echo Creating Python virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt

if "%1"=="webcam" (
    start "MineGuard Backend" cmd /k python app.py --source webcam
) else (
    start "MineGuard Backend" cmd /k python app.py
)
cd ..

echo == MineGuard AI: starting frontend ==
cd frontend
if not exist "node_modules" (
    echo Installing frontend dependencies...
    call npm install
)
start "MineGuard Frontend" cmd /k npm run dev
cd ..

echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo Two new windows have been opened for backend and frontend.
