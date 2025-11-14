@echo off
REM QUANTUM MIND - Startup Script for Windows

setlocal enabledelayedexpansion

echo.
echo ============================================
echo   QUANTUM MIND v1.0 - Windows Startup
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ and add it to your PATH
    pause
    exit /b 1
)

echo [OK] Python is installed

REM Check if virtual environment exists
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install requirements
echo [INFO] Installing requirements...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install requirements
    pause
    exit /b 1
)

echo [OK] Requirements installed

REM Check for .env file
if not exist ".env" (
    echo [WARNING] .env file not found
    echo [INFO] Creating .env from .env.example...
    copy .env.example .env >nul
    echo [WARNING] Please edit .env and set your GOOGLE_API_KEY
    echo.
    echo Edit .env now? (Y/N)
    set /p choice=
    if /i "!choice!"=="Y" (
        start notepad .env
    )
)

REM Start the application
echo.
echo [INFO] Starting QUANTUM MIND...
echo.
python main.py

pause
