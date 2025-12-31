@echo off
title Windows AI Agent - Setup
echo ==========================================
echo    Windows AI Agent - Setup
echo ==========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)
echo [OK] Python found

REM Install dependencies
echo.
echo Installing dependencies...
pip install requests --quiet
if errorlevel 1 (
    echo [WARNING] Failed to install requests
)

pip install psutil --quiet
if errorlevel 1 (
    echo [INFO] psutil not installed (optional - for process management)
)

pip install pywin32 --quiet 2>nul
if errorlevel 1 (
    echo [INFO] pywin32 not installed (optional - for Windows-specific features)
)

echo.
echo [OK] Core dependencies installed

REM Check Ollama
echo.
echo Checking Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Ollama not running or not installed
    echo.
    echo Please:
    echo   1. Install Ollama from https://ollama.ai
    echo   2. Run: ollama serve
    echo   3. Run: ollama pull llama4
) else (
    echo [OK] Ollama is running
)

echo.
echo ==========================================
echo    Setup Complete!
echo ==========================================
echo.
echo To start the agent, run:
echo   - run_test.bat   (verify everything works)
echo   - run_cli.bat    (command line interface)
echo   - run_gui.bat    (graphical interface - requires PyQt6)
echo.
echo For GUI support, also run:
echo   pip install PyQt6
echo.
pause
