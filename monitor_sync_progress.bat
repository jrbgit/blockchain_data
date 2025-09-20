@echo off
echo.
echo ⚡ GLQ Chain Sync Progress Monitor
echo ==================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found. Please install Python 3.12+ and try again.
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "config\config.yaml" (
    echo ❌ config\config.yaml not found. 
    echo Make sure you're running this from the blockchain_data directory.
    pause
    exit /b 1
)

REM Check if virtual environment is activated
if not defined VIRTUAL_ENV (
    echo 💡 Tip: Consider activating your virtual environment first:
    echo    venv\Scripts\activate
    echo.
)

REM Check if required dependencies are installed
python -c "import rich, psutil, asyncio" 2>nul
if %errorlevel% neq 0 (
    echo ❌ Required dependencies not found.
    echo Installing required packages...
    pip install rich psutil
    if %errorlevel% neq 0 (
        echo ❌ Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo 🚀 Starting sync progress monitor...
echo Press Ctrl+C to stop monitoring
echo.

REM Run the sync progress monitor
python sync_progress_monitor.py

REM If we get here, the script ended normally
echo.
echo 👋 Monitor stopped.
pause