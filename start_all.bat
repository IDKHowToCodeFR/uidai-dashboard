@echo off
setlocal enabledelayedexpansion
cls

echo ==========================================
echo    UIDAI Server (Unified) Bootstrap
echo ==========================================
echo.

:: 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ and ensure it is added to your PATH.
    pause
    exit /b 1
)

:: 2. Check/Create Virtual Environment
if not exist ".venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment not found. Creating one...
    
    uv --version >nul 2>&1
    if !errorlevel! equ 0 (
        echo [INFO] Detected 'uv'. Using ultra-fast venv creation...
        uv venv
    ) else (
        echo [INFO] Using standard Python venv...
        python -m venv .venv
    )
    
    if not exist ".venv\Scripts\activate.bat" (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: 3. Activate Environment
echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat

:: 4. Resolve Dependencies
echo [INFO] Verifying and installing dependencies...
uv --version >nul 2>&1
if %errorlevel% equ 0 (
    uv pip install -r requirements.txt
) else (
    python -m pip install --upgrade pip
    pip install -r requirements.txt
)

:: 5. Launch Server
echo.
echo ==========================================
echo    Starting Server
echo ==========================================
echo.
.venv\Scripts\python.exe run.py

pause
