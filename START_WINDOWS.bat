@echo off
title STRIKERS_PROTOCOL RE::INTEL
color 0A

echo.
echo  ⬡  STRIKERS_PROTOCOL RE::INTEL v2.0
echo  =========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install from https://python.org
    pause & exit /b 1
)

:: Create .env if missing
if not exist .env (
    echo  [SETUP] Creating .env from template...
    copy .env.example .env >nul
    echo.
    echo  !! IMPORTANT: Open .env and add your ANTHROPIC_API_KEY !!
    echo  !! Get it from: https://console.anthropic.com           !!
    echo.
    notepad .env
    echo  Press any key after saving your API key...
    pause >nul
)

:: Create virtual environment if missing
if not exist venv (
    echo  [SETUP] Creating virtual environment...
    python -m venv venv
)

:: Activate venv
call venv\Scripts\activate.bat

:: Install dependencies
echo  [SETUP] Installing dependencies...
pip install -r requirements.txt -q --disable-pip-version-check

:: Create directories
if not exist uploads mkdir uploads
if not exist reports mkdir reports
if not exist data    mkdir data

echo.
echo  =========================================
echo  ✓  Starting server at http://localhost:8000
echo  ✓  API docs at   http://localhost:8000/api/docs
echo  =========================================
echo.

:: Open browser after 2 seconds
start "" cmd /c "timeout /t 2 >nul && start http://localhost:8000"

:: Start server
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

pause
